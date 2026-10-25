import { randomUUID } from "node:crypto";
import type { ExtensionAPI, ExtensionContext } from "@oh-my-pi/pi-coding-agent";
import { toolDescription, ultracodeNotice } from "../../workflow-runtime/instructions.ts";
import {
	type AgentRequest,
	type AgentResult,
	formatResult,
	findWorkflow,
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
type McpManager = NonNullable<ReturnType<(typeof import("@oh-my-pi/pi-coding-agent/mcp"))["MCPManager"]["instance"]>>;
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

type PinStage = "call" | "relay";

/// A command turn in progress: `call` forces the workflow tool with a fixed name and args, `relay` only lets the model repeat a text.
interface Pin {
	name: string;
	args: string | undefined;
	stage: PinStage;
}

interface Instance {
	runs: Set<AbortController>;
	pins: Map<string, Pin>;
	tag: string;
	childCount: number;
	guard: RepeatGuard;
}

const NOTICE_TYPE = "ultracode-notice";
const COMMAND_TYPE = "workflow-command";
const SUBMIT_TOOL = "submit_result";
const TOOL_NAME = "workflow";
const CHILD_HIDDEN_TOOLS = [TOOL_NAME, "task", "ask", "irc"];
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

/// The parent session's MCP manager, which the host registers process-wide; undefined when the parent has none or this omp build does not expose the module.
async function parentMcpManager(): Promise<McpManager | undefined> {
	try {
		const mcp = await import("@oh-my-pi/pi-coding-agent/mcp");
		return mcp.MCPManager.instance();
	} catch {
		return undefined;
	}
}

/// The parent's live MCP connections as proxy tools, the way omp's own task subagents reach them, so no child starts an MCP server of its own.
async function parentMcp(pi: ExtensionAPI): Promise<{ manager: McpManager | undefined; tools: unknown[] }> {
	const manager = await parentMcpManager();
	return { manager, tools: manager ? pi.pi.createMCPProxyTools(manager) : [] };
}

/// Hides the tools that start more agents or wait for a person from a child, which cannot answer them, and keeps the shared MCP tools directly callable: rewriting the active set would otherwise unmount them from the `xd://` devices they start on.
async function trimChild(session: AgentSession, mcpToolNames: string[]): Promise<void> {
	const kept = session.getActiveToolNames().filter(name => !CHILD_HIDDEN_TOOLS.includes(name));
	const shared = mcpToolNames.filter(name => session.getToolByName(name) !== undefined && !kept.includes(name));
	await session.setActiveToolsByName([...kept, ...shared]);
}

/// Starts a child session configured like omp's own task subagents, minus extensions so it cannot orchestrate, and sharing the parent's MCP connections instead of starting its own.
async function createChild(
	pi: ExtensionAPI,
	instance: Instance,
	ctx: ExtensionContext,
	model: ResolvedModel,
	customTools: unknown[],
) {
	const sdk = pi.pi;
	const mcp = await parentMcp(pi);
	const tools = [...mcp.tools, ...customTools];
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
		enableMCP: mcp.manager !== undefined,
		mcpManager: mcp.manager,
		enableLsp: false,
		hasUI: false,
		skills: [],
		rules: [],
		promptTemplates: [],
		slashCommands: [],
		customTools: tools.length > 0 ? (tools as never) : undefined,
	});
	try {
		await trimChild(session, mcp.tools.map(tool => (tool as { name: string }).name));
	} catch (error) {
		await session.dispose().catch(() => undefined);
		throw error;
	}
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

/// The input a tool call runs with: the name and args the user typed when a command turn is waiting for its call, else what the model sent.
function effectiveInput(instance: Instance, sessionId: string, modelInput: ToolInput): ToolInput {
	const pin = instance.pins.get(sessionId);
	if (pin?.stage !== "call") return modelInput;
	pin.stage = "relay";
	return { name: pin.name, args: pin.args };
}

function registerWorkflowTool(pi: ExtensionAPI, instance: Instance): void {
	const z = pi.zod;
	pi.registerTool({
		name: TOOL_NAME,
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
			const sessionId = ctx.sessionManager.getSessionId();
			const input = effectiveInput(instance, sessionId, params as ToolInput);
			const invocation = readInvocation(input);
			if (typeof invocation === "string") return textResult(invocation, true);
			const refusal = instance.guard.refusal(sessionId);
			if (refusal) return textResult(refusal, true);
			const result = await execute(pi, instance, ctx, invocation, signal, text =>
				onUpdate?.({ content: [{ type: "text", text }] }),
			);
			const text = instance.guard.record(sessionId, invocationKey(input), result.ok, formatResult(result));
			return { ...textResult(text, !result.ok), details: { agents: result.agents, failed: result.failed } };
		},
	});
}

/// Aborts every running workflow and reports how many there were.
function stopRuns(instance: Instance): string {
	const count = instance.runs.size;
	for (const controller of instance.runs) controller.abort();
	return count === 0 ? "No workflow is running." : `Stopped ${count} running workflow${count === 1 ? "" : "s"}.`;
}

/// The hidden message of the turn that runs a saved workflow for `/workflow <name> [args]`.
function commandPrompt(name: string, args: string | undefined): string {
	const typed = args === undefined ? "" : ` ${args}`;
	const withArgs = args === undefined ? "" : ` and args ${JSON.stringify(args)}`;
	return `The user ran the command /workflow ${name}${typed}. Call the ${TOOL_NAME} tool now, exactly once, with name ${JSON.stringify(name)}${withArgs}. Do not answer before calling it. When it returns, relay its result to the user as is.`;
}

/// The hidden message that hands a reply of the `/workflow` command to the model for relaying.
function deliveryText(body: string): string {
	return `Relay the message below to the user as is, without calling any tools.\n\n${body}`;
}

/// The text that tells the user a command turn ended without the tool being called.
function notRunText(name: string): string {
	return `The workflow "${name}" did not run: the model answered without calling the ${TOOL_NAME} tool, so nothing ran. /workflow ${name} can be tried again.`;
}

/// The tool input schema of a command turn: the model can only emit the exact name and args the user typed.
function pinnedSchema(pin: Pin): JsonObject {
	const properties: Record<string, JsonObject> = { name: { const: pin.name } };
	if (pin.args !== undefined) properties.args = { const: pin.args };
	return { type: "object", properties, required: Object.keys(properties), additionalProperties: false };
}

/// The name of a tool entry in a provider request body, in the chat, responses or messages wire format.
function wireToolName(tool: JsonObject): unknown {
	return (tool.function as JsonObject | undefined)?.name ?? tool.name;
}

/// The request body of a command turn: only the workflow tool, forced before it ran and switched off after, with the pinned input schema. Undefined when the body has no workflow tool to force.
function narrowRequest(payload: unknown, pin: Pin): JsonObject | undefined {
	if (typeof payload !== "object" || payload === null) return undefined;
	const body = payload as JsonObject;
	const tools = Array.isArray(body.tools) ? (body.tools as JsonObject[]) : [];
	const found = tools.find(tool => wireToolName(tool) === TOOL_NAME);
	if (!found) return undefined;
	const entry = structuredClone(found);
	const pinned = pin.name === "" ? undefined : pinnedSchema(pin);
	const forced = pin.stage === "call";
	let choice: unknown = forced ? "required" : "none";
	if (entry.function) {
		if (pinned) (entry.function as JsonObject).parameters = pinned;
	} else if (entry.input_schema) {
		if (pinned) entry.input_schema = pinned;
		choice = { type: forced ? "any" : "none" };
	} else if (pinned) {
		entry.parameters = pinned;
	}
	return { ...body, tools: [entry], tool_choice: choice };
}

/// Starts a hidden model turn for a command. The bridge shows no custom messages, so the model's reply is how the user hears anything.
function startTurn(pi: ExtensionAPI, text: string): void {
	pi.sendMessage({ customType: COMMAND_TYPE, content: text, display: false, attribution: "user" }, { triggerTurn: true });
}

/// Has the model say `body` to the user in a turn that cannot call tools.
function deliver(pi: ExtensionAPI, instance: Instance, sessionId: string, body: string): void {
	instance.pins.set(sessionId, { name: "", args: undefined, stage: "relay" });
	startTurn(pi, deliveryText(body));
}

/// Handles `/workflow`: lists saved workflows, stops running ones, or starts a model turn that calls the workflow tool for a saved name, so the harness's own stop reaches the run.
function handleCommand(pi: ExtensionAPI, instance: Instance, ctx: ExtensionContext, raw: string): void {
	const sessionId = ctx.sessionManager.getSessionId();
	const { name, args } = parseCommandArgs(raw);
	instance.guard.reset(sessionId);
	if (LIST_WORDS.includes(name.toLowerCase())) return deliver(pi, instance, sessionId, savedListText(ctx.cwd));
	if (name.toLowerCase() === STOP_WORD) return deliver(pi, instance, sessionId, stopRuns(instance));
	if (findWorkflow(name, ctx.cwd) === undefined) {
		return deliver(pi, instance, sessionId, `No saved workflow named "${name}".\n\n${savedListText(ctx.cwd)}`);
	}
	instance.pins.set(sessionId, { name, args, stage: "call" });
	startTurn(pi, commandPrompt(name, args));
}

/// True when the model finished its last reply on its own, as opposed to the user stopping it or the request failing.
function endedNormally(messages: readonly unknown[]): boolean {
	const last = [...messages].reverse().find(message => (message as { role?: string }).role === "assistant") as
		| { stopReason?: string }
		| undefined;
	return last?.stopReason === "stop";
}

/// Says plainly, through a tool-less model turn, that a command turn ended with the tool never called.
function reportNotRun(pi: ExtensionAPI, instance: Instance, sessionId: string, pin: Pin): void {
	deliver(pi, instance, sessionId, notRunText(pin.name));
}

export default function workflowExtension(pi: ExtensionAPI): void {
	const instance: Instance = {
		runs: new Set(),
		pins: new Map(),
		tag: randomUUID().slice(0, 8),
		childCount: 0,
		guard: new RepeatGuard(),
	};
	registerWorkflowTool(pi, instance);

	pi.registerCommand("workflow", {
		description: "Run a saved multi-agent workflow: /workflow <name> [args], /workflow list, or /workflow stop",
		handler: async (args, ctx) => {
			handleCommand(pi, instance, ctx, args);
		},
	});

	pi.on("before_agent_start", async (event, ctx) => {
		if (isSubagent(ctx)) return;
		const sessionId = ctx.sessionManager.getSessionId();
		instance.pins.delete(sessionId);
		instance.guard.reset(sessionId);
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

	pi.on("before_provider_request", async (event, ctx) => {
		if (isSubagent(ctx)) return undefined;
		const pin = instance.pins.get(ctx.sessionManager.getSessionId());
		return pin ? narrowRequest(event.payload, pin) : undefined;
	});

	pi.on("agent_end", async (event, ctx) => {
		if (isSubagent(ctx)) return;
		const sessionId = ctx.sessionManager.getSessionId();
		const pin = instance.pins.get(sessionId);
		if (!pin) return;
		if (pin.stage === "call" && endedNormally(event.messages)) reportNotRun(pi, instance, sessionId, pin);
		else instance.pins.delete(sessionId);
	});

	pi.on("session_shutdown", async () => {
		for (const controller of instance.runs) controller.abort();
		instance.pins.clear();
	});
}
