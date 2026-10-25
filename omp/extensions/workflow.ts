import { randomUUID } from "node:crypto";
import type { ExtensionAPI, ExtensionContext } from "@oh-my-pi/pi-coding-agent";
import { toolDescription, ultracodeNotice } from "../../workflow-runtime/instructions.ts";
import {
	type AgentRequest,
	type AgentResult,
	formatResult,
	hasUltracodeKeyword,
	invocationKey,
	listWorkflows,
	RepeatGuard,
	type RunResult,
	runWorkflow,
	type WorkflowEvent,
} from "../../workflow-runtime/runtime.ts";

type AgentSession = Awaited<ReturnType<ExtensionAPI["pi"]["createAgentSession"]>>["session"];
type SessionSettings = NonNullable<Parameters<ExtensionAPI["pi"]["createAgentSession"]>[0]>["settings"];
type ResolvedModel = NonNullable<ExtensionContext["model"]>;
type JsonObject = Record<string, unknown>;

interface ToolInput {
	script?: string;
	name?: string;
	args?: unknown;
}

interface Progress {
	phase: string;
	running: number;
	done: number;
	failed: number;
	agents: number;
}

interface Invocation {
	source?: string;
	name?: string;
	args?: unknown;
}

interface Instance {
	runs: Set<AbortController>;
	tag: string;
	childCount: number;
	guard: RepeatGuard;
}

const NOTICE_TYPE = "ultracode-notice";
const RESULT_TYPE = "workflow-result";
const SUBMIT_TOOL = "submit_result";
const FALLBACK_PARENT_ID = "Main";
const LIST_WORDS = ["", "list"];
const STOP_WORD = "stop";

const SUBAGENT_REFUSAL = "Workflow orchestration is only available in the main agent session. Do this work yourself.";
const SAVED_WORKFLOWS_NOTE =
	"Saved workflows depend on the session's working directory, so none are listed here. The user can run /workflow list to see them, and an ultracode notice names the ones that fit. Call the tool with a saved name only when you were given that name.";
const NO_SAVED_WORKFLOWS = "No saved workflows.";

function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}

function textResult(text: string, isError = false) {
	return { content: [{ type: "text" as const, text }], isError };
}

/// The shared tool description without its saved-workflow list, which depends on the session cwd and so cannot be fixed at registration time.
function registeredDescription(): string {
	const base = toolDescription([]);
	return base.endsWith(NO_SAVED_WORKFLOWS)
		? `${base.slice(0, -NO_SAVED_WORKFLOWS.length)}${SAVED_WORKFLOWS_NOTE}`
		: `${base}\n\n${SAVED_WORKFLOWS_NOTE}`;
}

/// True when the context belongs to a subagent of omp's own `task` tool, which re-binds this extension. Such sessions must not orchestrate.
function isSubagent(ctx: ExtensionContext): boolean {
	const agent = (ctx as { agent?: { kind?: string } }).agent;
	return agent !== undefined && agent.kind !== "main";
}

/// Splits `/workflow` arguments into a workflow name and the remaining argument string.
function parseCommandArgs(raw: string): { name: string; args: string | undefined } {
	const trimmed = raw.trim();
	const match = /^(\S+)(?:\s+([\s\S]*))?$/.exec(trimmed);
	if (!match) return { name: "", args: undefined };
	const rest = match[2]?.trim();
	return { name: match[1], args: rest ? rest : undefined };
}

/// Validates the tool input: exactly one of `script` and `name`.
function readInvocation(input: ToolInput): Invocation | string {
	const hasScript = typeof input.script === "string" && input.script.trim() !== "";
	const hasName = typeof input.name === "string" && input.name.trim() !== "";
	if (hasScript && hasName) return 'Give either "script" or "name", not both.';
	if (!hasScript && !hasName) return 'Give either "script" (JavaScript to run) or "name" (a saved workflow).';
	return hasScript
		? { source: input.script, args: input.args }
		: { name: (input.name as string).trim(), args: input.args };
}

/// One-line progress text for the tool's live update.
function describeProgress(progress: Progress): string {
	const phase = progress.phase ? `${progress.phase}: ` : "";
	return `${phase}${progress.agents} agents started, ${progress.running} running, ${progress.done} done, ${progress.failed} failed`;
}

/// Folds a workflow event into the running progress counters.
function applyEvent(progress: Progress, event: WorkflowEvent): void {
	if (event.type === "phase") progress.phase = event.title;
	if (event.type === "agent_start") {
		progress.agents = Math.max(progress.agents, event.index);
		progress.running = event.running;
	}
	if (event.type === "agent_end") {
		progress.running = event.running;
		progress.done = event.done;
		progress.failed = event.failed;
	}
}

/// Saved workflows as a readable list for the `/workflow` command.
function savedListText(cwd: string): string {
	const saved = listWorkflows(cwd);
	if (saved.length === 0) return "No saved workflows. Save scripts as <name>.js in .claude/workflows or ~/.claude/workflows.";
	const lines = saved.map(w => (w.description ? `- ${w.name}: ${w.description.replace(/\s+/g, " ").trim()}` : `- ${w.name}`));
	return ["Saved workflows (run one with /workflow <name> [args]):", ...lines].join("\n");
}

/// Looks up `provider/id` in the model registry, or explains why it is unusable.
function resolveRequestedModel(ctx: ExtensionContext, requested: string): ResolvedModel {
	const slash = requested.indexOf("/");
	const found = ctx.modelRegistry.find(requested.slice(0, slash), requested.slice(slash + 1));
	if (!found) throw new Error(`model "${requested}" is not in the model registry`);
	return found as ResolvedModel;
}

/// The model a sub-agent runs on: the explicit provider/id request, else the calling session's own model.
function chooseModel(ctx: ExtensionContext, requested: string | undefined): ResolvedModel {
	if (requested?.includes("/")) return resolveRequestedModel(ctx, requested);
	if (!ctx.model) throw new Error("the calling session has no active model");
	return ctx.model;
}

/// The user's real settings narrowed for a subagent, the way omp's own task path derives them; undefined when this omp build exposes something else under that name.
function deriveSubagentSettings(pi: ExtensionAPI): SessionSettings | undefined {
	const sdk = pi.pi;
	try {
		const derived = sdk.createSubagentSettings(sdk.Settings.instance);
		return derived instanceof sdk.Settings ? derived : undefined;
	} catch {
		return undefined;
	}
}

/// Settings for a child session: derived from the user's real settings, else a bare in-memory set with approval prompts off because nobody can answer them.
function childSettings(pi: ExtensionAPI): SessionSettings {
	return deriveSubagentSettings(pi) ?? pi.pi.Settings.isolated({ "tools.approvalMode": "yolo" });
}

/// The tool a child calls to hand back structured data; the arguments land in `captured`.
function submitResultTool(pi: ExtensionAPI, schema: object, captured: { data?: unknown }) {
	return {
		name: SUBMIT_TOOL,
		label: "Submit result",
		loadMode: "essential" as const,
		description: "Call this exactly once, as your last action, with your final structured answer as the arguments.",
		parameters: pi.typebox.Type.Unsafe(schema as JsonObject),
		async execute(_toolCallId: string, params: unknown) {
			captured.data = params;
			return { content: [{ type: "text" as const, text: "Result recorded. Stop now." }] };
		},
	};
}

/// Appends the instruction to finish through `submit_result`, with a plain JSON reply as the fallback.
function withSubmitInstruction(prompt: string): string {
	return `${prompt}\n\nWhen you are done, call the ${SUBMIT_TOOL} tool exactly once with your final answer as its arguments. If you cannot call it, reply with ONLY a JSON object with the same fields, with no other text.`;
}

/// The error text of a child's last assistant message when the model request failed.
function failedReply(session: AgentSession): string | undefined {
	const last = [...session.messages].reverse().find(message => message.role === "assistant") as
		| { stopReason?: string; errorMessage?: string }
		| undefined;
	if (last?.stopReason !== "error") return undefined;
	return last.errorMessage ?? "the model request failed";
}

/// Starts a child session configured like omp's own task subagents, minus extensions so it cannot orchestrate.
async function createChild(
	pi: ExtensionAPI,
	instance: Instance,
	ctx: ExtensionContext,
	model: ResolvedModel,
	customTools: unknown[],
) {
	const sdk = pi.pi;
	instance.childCount += 1;
	const agentId = `wf-${process.pid}-${instance.tag}-${instance.childCount}`;
	const { session } = await sdk.createAgentSession({
		cwd: ctx.cwd,
		agentId,
		agentDisplayName: agentId,
		parentAgentId: sdk.MAIN_AGENT_ID ?? FALLBACK_PARENT_ID,
		taskDepth: 1,
		model,
		modelRegistry: ctx.modelRegistry,
		authStorage: ctx.modelRegistry.authStorage,
		sessionManager: sdk.SessionManager.inMemory(ctx.cwd),
		settings: childSettings(pi),
		thinkingLevel: pi.getThinkingLevel(),
		disableExtensionDiscovery: true,
		enableMCP: false,
		enableLsp: false,
		hasUI: false,
		skills: [],
		rules: [],
		promptTemplates: [],
		slashCommands: [],
		customTools: customTools.length > 0 ? (customTools as never) : undefined,
	});
	return session;
}

/// Runs one prompt in a fresh child session and returns its final text and any submitted data.
async function runChild(pi: ExtensionAPI, instance: Instance, ctx: ExtensionContext, req: AgentRequest): Promise<AgentResult> {
	const captured: { data?: unknown } = {};
	const customTools = req.schema ? [submitResultTool(pi, req.schema, captured)] : [];
	const model = chooseModel(ctx, req.model);
	if (req.signal.aborted) throw new Error("aborted");
	const session = await createChild(pi, instance, ctx, model, customTools);
	const onAbort = () => void session.abort();
	req.signal.addEventListener("abort", onAbort, { once: true });
	try {
		if (req.signal.aborted) throw new Error("aborted");
		await session.prompt(req.schema ? withSubmitInstruction(req.prompt) : req.prompt);
		const failure = failedReply(session);
		if (failure) throw new Error(failure);
		const text = session.getLastAssistantText() ?? "";
		if (text === "" && captured.data === undefined) throw new Error("the sub-agent produced no reply");
		return { text, data: captured.data };
	} finally {
		req.signal.removeEventListener("abort", onAbort);
		await session.dispose().catch(() => undefined);
	}
}

/// Runs an invocation to completion under a controller that session shutdown and the tool's own signal can abort.
async function execute(
	pi: ExtensionAPI,
	instance: Instance,
	ctx: ExtensionContext,
	invocation: Invocation,
	outer: AbortSignal | undefined,
	onProgress: ((text: string) => void) | undefined,
): Promise<RunResult> {
	const controller = new AbortController();
	const forward = () => controller.abort();
	if (outer?.aborted) controller.abort();
	outer?.addEventListener("abort", forward, { once: true });
	instance.runs.add(controller);
	const progress: Progress = { phase: "", running: 0, done: 0, failed: 0, agents: 0 };
	try {
		return await runWorkflow({
			...invocation,
			cwd: ctx.cwd,
			signal: controller.signal,
			runner: { nativeSchema: true, run: req => runChild(pi, instance, ctx, req) },
			onEvent: event => {
				applyEvent(progress, event);
				onProgress?.(describeProgress(progress));
			},
		});
	} finally {
		instance.runs.delete(controller);
		outer?.removeEventListener("abort", forward);
	}
}

function registerWorkflowTool(pi: ExtensionAPI, instance: Instance): void {
	const z = pi.zod;
	pi.registerTool({
		name: "workflow",
		label: "Workflow",
		loadMode: "essential",
		description: registeredDescription(),
		parameters: z.object({
			script: z.string().optional().describe("JavaScript workflow script to run. Give this or name."),
			name: z.string().optional().describe("Name of a saved workflow to run. Give this or script."),
			args: z.any().optional().describe("Value passed to the script as args."),
		}),
		async execute(_toolCallId, params, signal, onUpdate, ctx) {
			if (isSubagent(ctx)) return textResult(SUBAGENT_REFUSAL, true);
			const invocation = readInvocation(params as ToolInput);
			if (typeof invocation === "string") return textResult(invocation, true);
			const sessionId = ctx.sessionManager.getSessionId();
			const refusal = instance.guard.refusal(sessionId);
			if (refusal) return textResult(refusal, true);
			const result = await execute(pi, instance, ctx, invocation, signal, text =>
				onUpdate?.({ content: [{ type: "text", text }] }),
			);
			const text = instance.guard.record(sessionId, invocationKey(params as ToolInput), result.ok, formatResult(result));
			return { ...textResult(text, !result.ok), details: { agents: result.agents, failed: result.failed } };
		},
	});
}

/// Aborts every running workflow and reports how many there were. A command handler has no abort signal of its own, so this is how a `/workflow` run is interrupted.
function stopRuns(instance: Instance): string {
	const count = instance.runs.size;
	for (const controller of instance.runs) controller.abort();
	return count === 0 ? "No workflow is running." : `Stopped ${count} running workflow${count === 1 ? "" : "s"}.`;
}

/// Handles `/workflow`: lists saved workflows, stops running ones, or runs one by name and posts the formatted result into the session.
async function handleCommand(pi: ExtensionAPI, instance: Instance, ctx: ExtensionContext, raw: string): Promise<void> {
	const { name, args } = parseCommandArgs(raw);
	if (LIST_WORDS.includes(name.toLowerCase())) {
		pi.sendMessage({ customType: RESULT_TYPE, content: savedListText(ctx.cwd), display: true });
		return;
	}
	if (name.toLowerCase() === STOP_WORD) {
		pi.sendMessage({ customType: RESULT_TYPE, content: stopRuns(instance), display: true });
		return;
	}
	const result = await execute(pi, instance, ctx, { name, args }, undefined, undefined);
	pi.sendMessage({ customType: RESULT_TYPE, content: formatResult(result), display: true });
}

export default function workflowExtension(pi: ExtensionAPI): void {
	const instance: Instance = { runs: new Set(), tag: randomUUID().slice(0, 8), childCount: 0, guard: new RepeatGuard() };
	registerWorkflowTool(pi, instance);

	pi.registerCommand("workflow", {
		description: "Run a saved multi-agent workflow: /workflow <name> [args], /workflow list, or /workflow stop",
		handler: async (args, ctx) => {
			await handleCommand(pi, instance, ctx, args);
		},
	});

	pi.on("before_agent_start", async (event, ctx) => {
		if (isSubagent(ctx)) return;
		instance.guard.reset(ctx.sessionManager.getSessionId());
		if (!hasUltracodeKeyword(event.prompt)) return;
		return {
			message: {
				customType: NOTICE_TYPE,
				content: ultracodeNotice(listWorkflows(ctx.cwd)),
				display: false,
				attribution: "user",
			},
		};
	});

	pi.on("session_shutdown", async () => {
		for (const controller of instance.runs) controller.abort();
	});
}
