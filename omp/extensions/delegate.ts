import { existsSync } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@oh-my-pi/pi-coding-agent";

interface DelegateEventBase {
	run_id: string;
	seq: number;
	ts: string;
}

type DelegateAttemptStatus = "pass" | "fail" | "timeout" | "scope" | "error";
type DelegateRunStatus = "passed" | "failed" | "held" | "cancelled" | "error";

interface RunStartedEvent extends DelegateEventBase {
	kind: "run_started";
	packet_id: string;
	class: string;
	start_tier: string;
	ceiling: string;
	mode: string;
	host: string;
	repo: string;
}

interface TierSelectedEvent extends DelegateEventBase {
	kind: "tier_selected";
	tier: string;
	label: string;
	runner: string;
	model: string;
	chain_index: number;
}

interface TierSkippedEvent extends DelegateEventBase {
	kind: "tier_skipped";
	tier: string;
	reason: string;
}

interface AttemptStartedEvent extends DelegateEventBase {
	kind: "attempt_started";
	tier: string;
	attempt: number;
	model: string;
}

interface ProgressEvent extends DelegateEventBase {
	kind: "progress";
	tier: string;
	attempt: number;
	text: string;
}

interface AttemptFinishedEvent extends DelegateEventBase {
	kind: "attempt_finished";
	tier: string;
	attempt: number;
	status: DelegateAttemptStatus;
	verify_exit: number | null;
	duration_ms: number;
	tokens_in: number;
	tokens_out: number;
	changed_files: string[];
	scope_violations: string[];
	verify_tail: string;
	worker_summary: string;
}

interface ApprovalRequiredEvent extends DelegateEventBase {
	kind: "approval_required";
	tier: string;
	reason: string;
}

interface ApprovalResolvedEvent extends DelegateEventBase {
	kind: "approval_resolved";
	tier: string;
	approved: boolean;
}

interface EscalatedEvent extends DelegateEventBase {
	kind: "escalated";
	from: string;
	to: string;
	reason: string;
}

interface AppliedEvent extends DelegateEventBase {
	kind: "applied";
	files: string[];
	patch_bytes: number;
}

interface RunFinishedEvent extends DelegateEventBase {
	kind: "run_finished";
	status: DelegateRunStatus;
	passed_tier: string | null;
	escalations: number;
	duration_ms: number;
	summary: string;
}

export type DelegateEvent =
	| RunStartedEvent
	| TierSelectedEvent
	| TierSkippedEvent
	| AttemptStartedEvent
	| ProgressEvent
	| AttemptFinishedEvent
	| ApprovalRequiredEvent
	| ApprovalResolvedEvent
	| EscalatedEvent
	| AppliedEvent
	| RunFinishedEvent;

interface StreamOutcome {
	runId: string | undefined;
	finished: RunFinishedEvent | undefined;
	appliedFiles: string[];
	exitCode: number;
	stderrTail: string;
}

interface ParsedFlags {
	positional: string[];
	flags: Record<string, string>;
}

const HOME_PATH_DIRS = [".bun/bin", ".cargo/bin", ".local/bin"] as const;
const EXTRA_PATH_DIRS = [...HOME_PATH_DIRS.map(rel => path.join(os.homedir(), rel)), "/opt/homebrew/bin"];

const RUN_FLAG_NAMES = ["tier", "ceiling", "mode"] as const;

const SUBCOMMANDS = ["help", "new", "run", "replay", "log", "stats", "tiers", "show"] as const;

const HELP_TEXT = `delegate - run task packets through the local/cheap/frontier tier ladder

/delegate new <class> <goal...>      create a packet, edit it, optionally run it
/delegate run <packet.yml> [--tier t] [--ceiling t] [--mode m]
/delegate replay <run-id> [--tier t] [--ceiling t] [--mode m]
/delegate log                        recent runs
/delegate stats [class]              pass rates per class/tier
/delegate tiers                      resolved tier chains and health
/delegate show <run-id>              one run with its attempts
/delegate help                       this summary

Launch omp with --delegate-tool to also let the model call delegate directly.`;

/**
 * Prepends the directories delegate's own `omp` runner needs (bun, cargo,
 * local installs, Homebrew) onto PATH, once, so every child process this
 * extension spawns - and every `pi.exec` call, which inherits `process.env`
 * with no per-call override - can find `bun` and `delegate` regardless of
 * the shell that launched omp.
 */
function ensureAugmentedPath(): void {
	const current = (process.env.PATH ?? "").split(path.delimiter).filter(Boolean);
	const seen = new Set<string>();
	const merged: string[] = [];
	for (const dir of [...EXTRA_PATH_DIRS, ...current]) {
		if (seen.has(dir)) continue;
		seen.add(dir);
		merged.push(dir);
	}
	process.env.PATH = merged.join(path.delimiter);
}

/**
 * Resolves the delegate binary: an explicit override, then PATH, then the
 * two well-known install locations, in that order. Returns undefined rather
 * than throwing so callers can report a clean error.
 */
function resolveDelegateBin(): string | undefined {
	const fromEnv = process.env.DELEGATE_BIN;
	if (fromEnv) return fromEnv;
	const onPath = Bun.which("delegate");
	if (onPath) return onPath;
	const cargoBin = path.join(os.homedir(), ".cargo/bin/delegate");
	if (existsSync(cargoBin)) return cargoBin;
	const devBin = path.join(os.homedir(), "Dev/rust/delegate/target/debug/delegate");
	if (existsSync(devBin)) return devBin;
	return undefined;
}

function notifyMissingBinary(ctx: ExtensionContext): void {
	ctx.ui.notify(
		"delegate binary not found. Set DELEGATE_BIN, install it to ~/.cargo/bin/delegate, or build ~/Dev/rust/delegate.",
		"error",
	);
}

function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}

function tailLines(text: string, maxLines: number): string {
	const lines = text.split("\n").filter(line => line.length > 0);
	return lines.slice(-maxLines).join("\n");
}

function truncate(text: string, maxLen: number): string {
	if (text.length <= maxLen) return text;
	return `${text.slice(0, maxLen).trimEnd()}...`;
}

function resolvePath(cwd: string, target: string): string {
	return path.isAbsolute(target) ? target : path.join(cwd, target);
}

function fence(body: string): string {
	return `\`\`\`\n${body}\n\`\`\``;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}

export function parseDelegateEventLine(line: string): DelegateEvent | undefined {
	let parsed: unknown;
	try {
		parsed = JSON.parse(line);
	} catch {
		return undefined;
	}
	if (!isRecord(parsed) || typeof parsed.kind !== "string" || typeof parsed.run_id !== "string") return undefined;
	return parsed as unknown as DelegateEvent;
}

function renderAttemptFinished(event: AttemptFinishedEvent): string {
	if (event.status === "pass") {
		return `${event.tier} ✓ attempt ${event.attempt} ${event.changed_files.length} file(s)`;
	}
	const durationSec = (event.duration_ms / 1000).toFixed(1);
	const reason = event.verify_exit !== null ? `verify exit ${event.verify_exit}` : event.status;
	return `${event.tier} ✗ attempt ${event.attempt} ${reason} (${durationSec}s)`;
}

export function renderEventLine(event: DelegateEvent): string | undefined {
	switch (event.kind) {
		case "run_started":
			return `▶ ${event.class} starting at ${event.start_tier} (ceiling ${event.ceiling}, mode ${event.mode})`;
		case "tier_selected":
			return `${event.tier} ${event.label}: ${event.model}`;
		case "tier_skipped":
			return `${event.tier} skipped (${event.reason})`;
		case "attempt_started":
			return `${event.tier} attempt ${event.attempt} started (${event.model})`;
		case "progress":
			return `${event.tier} attempt ${event.attempt}: ${event.text}`;
		case "attempt_finished":
			return renderAttemptFinished(event);
		case "approval_required":
			return `⚠ approval required at ${event.tier}: ${event.reason}`;
		case "approval_resolved":
			return `${event.approved ? "✓" : "✗"} approval ${event.approved ? "granted" : "denied"} at ${event.tier}`;
		case "escalated":
			return `${event.from} → ${event.to}`;
		case "applied":
			return `applied ${event.files.length} file(s)`;
		case "run_finished":
			return `■ ${event.status}${event.passed_tier ? ` (tier ${event.passed_tier})` : ""}`;
		default:
			return undefined;
	}
}

export function buildResultMarkdown(runId: string, finished: RunFinishedEvent, appliedFiles: string[]): string {
	const durationSec = (finished.duration_ms / 1000).toFixed(1);
	const filesLine = appliedFiles.length > 0 ? appliedFiles.join(", ") : "none";
	return [
		`**delegate run \`${runId}\`** — ${finished.status}`,
		`- passed tier: ${finished.passed_tier ?? "none"}`,
		`- escalations: ${finished.escalations}`,
		`- duration: ${durationSec}s`,
		`- changed files: ${filesLine}`,
		"",
		truncate(finished.summary, 600),
		"",
		`Run \`delegate show ${runId}\` for the full attempt history.`,
	].join("\n");
}

function splitVerb(args: string): { verb: string; rest: string } {
	const trimmed = args.trim();
	if (!trimmed) return { verb: "", rest: "" };
	const spaceIndex = trimmed.search(/\s/);
	if (spaceIndex === -1) return { verb: trimmed.toLowerCase(), rest: "" };
	return { verb: trimmed.slice(0, spaceIndex).toLowerCase(), rest: trimmed.slice(spaceIndex + 1).trim() };
}

function splitClassAndGoal(rest: string): { klass: string | undefined; goal: string | undefined } {
	const trimmed = rest.trim();
	if (!trimmed) return { klass: undefined, goal: undefined };
	const spaceIndex = trimmed.search(/\s/);
	if (spaceIndex === -1) return { klass: trimmed, goal: undefined };
	return { klass: trimmed.slice(0, spaceIndex), goal: trimmed.slice(spaceIndex + 1).trim() };
}

function parseFlags(rest: string, names: readonly string[]): ParsedFlags {
	const tokens = rest.split(/\s+/).filter(Boolean);
	const positional: string[] = [];
	const flags: Record<string, string> = {};
	for (let i = 0; i < tokens.length; i += 1) {
		const token = tokens[i];
		const name = token.startsWith("--") ? token.slice(2) : undefined;
		if (name && names.includes(name) && i + 1 < tokens.length) {
			flags[name] = tokens[i + 1];
			i += 1;
			continue;
		}
		positional.push(token);
	}
	return { positional, flags };
}

function flagsToArgs(flags: Record<string, string>): string[] {
	return Object.entries(flags).flatMap(([name, value]) => [`--${name}`, value]);
}

function extractPacketId(yamlText: string): string | undefined {
	const match = yamlText.match(/^id:\s*(\S+)/m);
	return match ? match[1] : undefined;
}

/**
 * Runs a delegate `run`/`replay` invocation to completion, rendering each
 * JSON event line into the rolling widget and status line, and returning the
 * parsed outcome. UI state is always cleared on the way out, whether the
 * process finished normally or reading its output threw.
 */
async function streamDelegateProcess(ctx: ExtensionContext, bin: string, args: string[]): Promise<StreamOutcome> {
	const proc = Bun.spawn([bin, ...args], {
		cwd: ctx.cwd,
		env: process.env,
		stdout: "pipe",
		stderr: "pipe",
	});

	const widgetLines: string[] = [];
	let runId: string | undefined;
	let finished: RunFinishedEvent | undefined;
	let appliedFiles: string[] = [];

	const pushLine = (line: string): void => {
		widgetLines.push(line);
		if (widgetLines.length > 8) widgetLines.shift();
		ctx.ui.setWidget("delegate", [...widgetLines]);
	};

	const handleEvent = (event: DelegateEvent): void => {
		runId = event.run_id;
		const rendered = renderEventLine(event);
		if (rendered) pushLine(rendered);
		if (event.kind === "attempt_started") {
			ctx.ui.setStatus("delegate", `${event.tier} attempt ${event.attempt} running (${event.model})`);
		} else if (event.kind === "progress") {
			ctx.ui.setStatus("delegate", `${event.tier} attempt ${event.attempt}: ${event.text}`);
		} else if (event.kind === "escalated") {
			ctx.ui.setStatus("delegate", `escalating ${event.from} → ${event.to}`);
		} else if (event.kind === "applied") {
			appliedFiles = event.files;
		} else if (event.kind === "run_finished") {
			finished = event;
		}
	};

	const processLine = (line: string): void => {
		const trimmed = line.trim();
		if (!trimmed) return;
		const event = parseDelegateEventLine(trimmed);
		if (event) handleEvent(event);
	};

	try {
		const decoder = new TextDecoder();
		let buffer = "";
		const reader = proc.stdout.getReader();
		try {
			while (true) {
				const { value, done } = await reader.read();
				if (done) break;
				buffer += decoder.decode(value, { stream: true });
				let newlineIndex = buffer.indexOf("\n");
				while (newlineIndex >= 0) {
					processLine(buffer.slice(0, newlineIndex));
					buffer = buffer.slice(newlineIndex + 1);
					newlineIndex = buffer.indexOf("\n");
				}
			}
			if (buffer.trim()) processLine(buffer);
		} finally {
			reader.releaseLock();
		}

		const stderrText = await new Response(proc.stderr).text().catch(() => "");
		const exitCode = await proc.exited;

		return { runId, finished, appliedFiles, exitCode, stderrTail: tailLines(stderrText, 10) };
	} finally {
		ctx.ui.setStatus("delegate", undefined);
		ctx.ui.setWidget("delegate", undefined);
	}
}

async function runAndReport(pi: ExtensionAPI, ctx: ExtensionContext, bin: string, args: string[]): Promise<void> {
	let outcome: StreamOutcome;
	try {
		outcome = await streamDelegateProcess(ctx, bin, args);
	} catch (error) {
		ctx.ui.notify(`Failed to run delegate: ${errorMessage(error)}`, "error");
		return;
	}
	if (!outcome.finished) {
		const suffix = outcome.stderrTail ? `: ${outcome.stderrTail}` : "";
		ctx.ui.notify(`delegate exited with code ${outcome.exitCode} before finishing${suffix}`, "error");
		return;
	}
	const markdown = buildResultMarkdown(outcome.runId ?? "unknown", outcome.finished, outcome.appliedFiles);
	pi.sendMessage(
		{ customType: "delegate-result", content: markdown, display: true, details: outcome.finished },
		{ triggerTurn: false, deliverAs: "nextTurn" },
	);
}

async function postInfo(pi: ExtensionAPI, ctx: ExtensionContext, bin: string, args: string[]): Promise<void> {
	const result = await pi.exec(bin, args, { cwd: ctx.cwd });
	if (result.code !== 0) {
		ctx.ui.notify(`delegate ${args.join(" ")} failed (exit ${result.code}): ${tailLines(result.stderr || result.stdout, 10)}`, "error");
		return;
	}
	const body = result.stdout.trim() || "(no output)";
	pi.sendMessage(
		{ customType: "delegate-info", content: fence(body), display: true },
		{ triggerTurn: false, deliverAs: "nextTurn" },
	);
}

async function handleNew(pi: ExtensionAPI, ctx: ExtensionContext, rest: string): Promise<void> {
	const bin = resolveDelegateBin();
	if (!bin) {
		notifyMissingBinary(ctx);
		return;
	}
	const { klass, goal } = splitClassAndGoal(rest);
	if (!klass || !goal) {
		ctx.ui.notify("Usage: /delegate new <class> <goal...>", "error");
		return;
	}
	const created = await pi.exec(bin, ["new", "--class", klass, "--goal", goal, "--repo", ctx.cwd], { cwd: ctx.cwd });
	if (created.code !== 0) {
		ctx.ui.notify(`delegate new failed (exit ${created.code}): ${tailLines(created.stderr || created.stdout, 10)}`, "error");
		return;
	}
	const packetPath = created.stdout.trim();
	if (!packetPath || !existsSync(packetPath)) {
		ctx.ui.notify(`delegate new did not report a packet path: ${created.stdout.trim()}`, "error");
		return;
	}
	const original = await Bun.file(packetPath).text();
	const packetId = extractPacketId(original) ?? path.basename(packetPath, path.extname(packetPath));
	const edited = await ctx.ui.editor(`Packet ${packetId}`, original);
	if (typeof edited === "string" && edited !== original) {
		await Bun.write(packetPath, edited);
	}
	const shouldRun = await ctx.ui.confirm("Run packet?", packetPath);
	if (!shouldRun) {
		ctx.ui.notify(packetPath, "info");
		return;
	}
	await runAndReport(pi, ctx, bin, ["run", packetPath, "--json", "-y"]);
}

async function handleRun(pi: ExtensionAPI, ctx: ExtensionContext, rest: string): Promise<void> {
	const bin = resolveDelegateBin();
	if (!bin) {
		notifyMissingBinary(ctx);
		return;
	}
	const { positional, flags } = parseFlags(rest, RUN_FLAG_NAMES);
	const packetArg = positional[0];
	if (!packetArg) {
		ctx.ui.notify("Usage: /delegate run <packet.yml> [--tier t] [--ceiling t] [--mode m]", "error");
		return;
	}
	const packetPath = resolvePath(ctx.cwd, packetArg);
	if (!existsSync(packetPath)) {
		ctx.ui.notify(`Packet not found: ${packetPath}`, "error");
		return;
	}
	await runAndReport(pi, ctx, bin, ["run", packetPath, "--json", "-y", ...flagsToArgs(flags)]);
}

async function handleReplay(pi: ExtensionAPI, ctx: ExtensionContext, rest: string): Promise<void> {
	const bin = resolveDelegateBin();
	if (!bin) {
		notifyMissingBinary(ctx);
		return;
	}
	const { positional, flags } = parseFlags(rest, RUN_FLAG_NAMES);
	const runId = positional[0];
	if (!runId) {
		ctx.ui.notify("Usage: /delegate replay <run-id> [--tier t] [--ceiling t] [--mode m]", "error");
		return;
	}
	await runAndReport(pi, ctx, bin, ["replay", runId, "--json", "-y", ...flagsToArgs(flags)]);
}

async function handleLog(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	const bin = resolveDelegateBin();
	if (!bin) {
		notifyMissingBinary(ctx);
		return;
	}
	await postInfo(pi, ctx, bin, ["log"]);
}

async function handleStats(pi: ExtensionAPI, ctx: ExtensionContext, rest: string): Promise<void> {
	const bin = resolveDelegateBin();
	if (!bin) {
		notifyMissingBinary(ctx);
		return;
	}
	const klass = rest.trim().split(/\s+/)[0];
	await postInfo(pi, ctx, bin, klass ? ["stats", "--class", klass] : ["stats"]);
}

async function handleTiers(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	const bin = resolveDelegateBin();
	if (!bin) {
		notifyMissingBinary(ctx);
		return;
	}
	await postInfo(pi, ctx, bin, ["tiers"]);
}

async function handleShow(pi: ExtensionAPI, ctx: ExtensionContext, rest: string): Promise<void> {
	const bin = resolveDelegateBin();
	if (!bin) {
		notifyMissingBinary(ctx);
		return;
	}
	const runId = rest.trim().split(/\s+/)[0];
	if (!runId) {
		ctx.ui.notify("Usage: /delegate show <run-id>", "error");
		return;
	}
	await postInfo(pi, ctx, bin, ["show", runId]);
}

async function dispatchDelegateCommand(pi: ExtensionAPI, ctx: ExtensionContext, args: string): Promise<void> {
	const { verb, rest } = splitVerb(args);
	switch (verb) {
		case "":
		case "help":
			ctx.ui.notify(HELP_TEXT, "info");
			return;
		case "new":
			await handleNew(pi, ctx, rest);
			return;
		case "run":
			await handleRun(pi, ctx, rest);
			return;
		case "replay":
			await handleReplay(pi, ctx, rest);
			return;
		case "log":
			await handleLog(pi, ctx);
			return;
		case "stats":
			await handleStats(pi, ctx, rest);
			return;
		case "tiers":
			await handleTiers(pi, ctx);
			return;
		case "show":
			await handleShow(pi, ctx, rest);
			return;
		default:
			ctx.ui.notify(`Unknown /delegate subcommand "${verb}".\n\n${HELP_TEXT}`, "error");
	}
}

function registerDelegateTool(pi: ExtensionAPI): void {
	const z = pi.zod;

	pi.registerTool({
		name: "delegate",
		label: "Delegate",
		description:
			"Runs a scoped coding subtask through delegate's tiered worker ladder (local model, then cheap cloud, then frontier), each attempt checked by a verifier command before being applied. Use it to hand off a well-defined, independently-verifiable piece of work to a cheaper model instead of doing it yourself; it returns a summary of what changed and which tier passed.",
		parameters: z.object({
			class: z.string().describe("Task class key selecting defaults (tier, ceiling, verifier) from delegate's config, e.g. docs, rust-mech, strings."),
			goal: z.string().describe("What the worker must achieve, written for a reader with no other context."),
			paths: z.array(z.string()).optional().describe("Paths or globs the worker may create or modify. Omit for unrestricted."),
			verify: z.string().optional().describe("Shell command run after the worker finishes; exit 0 passes."),
			read: z.array(z.string()).optional().describe("Files the worker should read before starting."),
			notes: z.string().optional().describe("Free-form context appended to the worker prompt."),
			tier: z.string().optional().describe("Start tier override, e.g. t1, t2, t3."),
			ceiling: z.string().optional().describe("Highest tier escalation may reach."),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const bin = resolveDelegateBin();
			if (!bin) {
				return {
					content: [{ type: "text", text: "delegate binary not found (set DELEGATE_BIN, or install to ~/.cargo/bin)." }],
					isError: true,
				};
			}

			const newArgs = ["new", "--class", params.class, "--goal", params.goal, "--repo", ctx.cwd];
			for (const p of params.paths ?? []) newArgs.push("--path", p);
			if (params.verify) newArgs.push("--verify", params.verify);
			for (const r of params.read ?? []) newArgs.push("--read", r);
			if (params.notes) newArgs.push("--notes", params.notes);
			if (params.tier) newArgs.push("--tier", params.tier);
			if (params.ceiling) newArgs.push("--ceiling", params.ceiling);

			const created = await pi.exec(bin, newArgs, { cwd: ctx.cwd });
			if (created.code !== 0) {
				return {
					content: [{ type: "text", text: `delegate new failed (exit ${created.code}): ${tailLines(created.stderr || created.stdout, 10)}` }],
					isError: true,
				};
			}
			const packetPath = created.stdout.trim();
			if (!packetPath || !existsSync(packetPath)) {
				return {
					content: [{ type: "text", text: `delegate new did not report a packet path: ${created.stdout.trim()}` }],
					isError: true,
				};
			}

			let outcome: StreamOutcome;
			try {
				outcome = await streamDelegateProcess(ctx, bin, ["run", packetPath, "--json", "-y"]);
			} catch (error) {
				return {
					content: [{ type: "text", text: `Failed to run delegate: ${errorMessage(error)}` }],
					isError: true,
				};
			}
			if (!outcome.finished) {
				const suffix = outcome.stderrTail ? `: ${outcome.stderrTail}` : "";
				return {
					content: [{ type: "text", text: `delegate run exited with code ${outcome.exitCode} before finishing${suffix}` }],
					isError: true,
				};
			}

			const markdown = buildResultMarkdown(outcome.runId ?? "unknown", outcome.finished, outcome.appliedFiles);
			return {
				content: [{ type: "text", text: markdown }],
				details: {
					run_id: outcome.runId,
					status: outcome.finished.status,
					passed_tier: outcome.finished.passed_tier,
					files: outcome.appliedFiles,
				},
			};
		},
	});
}

export default function delegateExtension(pi: ExtensionAPI): void {
	ensureAugmentedPath();

	pi.registerCommand("delegate", {
		description: "Run and manage delegate task packets (local/cheap/frontier tier ladder)",
		getArgumentCompletions(argumentPrefix) {
			if (argumentPrefix.includes(" ")) return null;
			const lower = argumentPrefix.toLowerCase();
			const matches = SUBCOMMANDS.filter(name => name.startsWith(lower)).map(name => ({
				value: `${name} `,
				label: name,
			}));
			return matches.length > 0 ? matches : null;
		},
		handler: async (args, ctx) => {
			await dispatchDelegateCommand(pi, ctx, args);
		},
	});

	pi.registerFlag("delegate-tool", {
		type: "boolean",
		default: false,
		description: "Expose a delegate model tool that runs a verified worker on a cheaper tier and returns a summary",
	});

	pi.on("session_start", async () => {
		if (pi.getFlag("delegate-tool") === true) {
			registerDelegateTool(pi);
		}
	});
}
