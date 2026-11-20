import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@oh-my-pi/pi-coding-agent";

/// The patterns and the words, read from the one file the Claude Code hook reads too, so the three agents can never
/// disagree about what an offer is or what Marcus says about it.
const RULES = JSON.parse(readFileSync(join(homedir(), "claudeconfig", "hooks", "follow-through.json"), "utf8"));
const OFFER_RE = new RegExp(RULES.offer, "i");
const STALL_RE = new RegExp(RULES.stall, "i");
const STALL_EXCEPT = new RegExp(RULES.stallExcept, "i");
const OFFER_NUDGE: string = RULES.offerNudge;
const STALL_NUDGE: string = RULES.stallNudge;
const NUDGE_TYPE = "follow-through";
const WORKFLOW_TYPE = "workflow-command";

type Kind = "offer" | "stall";

/// Whether a final reply ends by offering work ("offer"), by announcing a step it never took ("stall"), or neither.
export function verdict(text: string): Kind | undefined {
	const tail = text.slice(-400);
	const lines = text.split("\n").filter(line => line.trim() !== "");
	const last = lines.at(-1) ?? "";
	if (OFFER_RE.test(tail)) return "offer";
	const sentence = last.trim().split(/(?<=[.!])\s+/).at(-1) ?? "";
	if (last.length <= 300 && (/:\s*$/.test(last) || (STALL_RE.test(sentence) && !STALL_EXCEPT.test(sentence)))) return "stall";
	return undefined;
}

/// The final reply of a run that stopped on its own, or undefined when it ended any other way.
function finalReply(messages: readonly unknown[]): string | undefined {
	const last = [...messages].reverse().find(message => (message as { role?: string }).role === "assistant") as
		| { stopReason?: string; content?: Array<{ type?: string; text?: string }> }
		| undefined;
	if (last?.stopReason !== "stop") return undefined;
	return (last.content ?? [])
		.filter(part => part.type === "text")
		.map(part => part.text ?? "")
		.join("\n");
}

/// True when the run answered a nudge or a workflow command, which never earn a nudge of their own.
function isInjectedRun(messages: readonly unknown[]): boolean {
	return messages.some(message => {
		const { role, customType } = message as { role?: string; customType?: string };
		return role === "custom" && (customType === NUDGE_TYPE || customType === WORKFLOW_TYPE);
	});
}

/// True inside a sub-agent run, which reports to its parent rather than to Marcus.
function isSubagent(ctx: ExtensionContext): boolean {
	const agent = (ctx as { agent?: { kind?: string } }).agent;
	return agent !== undefined && agent.kind !== "main";
}

export default function followThroughExtension(pi: ExtensionAPI): void {
	const nudged = new Set<string>();

	pi.on("before_agent_start", async (event, ctx) => {
		if (isSubagent(ctx)) return;
		const prompt = (event as { prompt?: string }).prompt ?? "";
		if (prompt !== OFFER_NUDGE && prompt !== STALL_NUDGE) nudged.delete(ctx.sessionManager.getSessionId());
	});

	pi.on("agent_end", async (event, ctx) => {
		if (isSubagent(ctx) || event.willContinue) return;
		const sessionId = ctx.sessionManager.getSessionId();
		if (nudged.has(sessionId) || isInjectedRun(event.messages)) return;
		const reply = finalReply(event.messages);
		const kind = reply === undefined ? undefined : verdict(reply);
		if (!kind) return;
		nudged.add(sessionId);
		pi.sendMessage(
			{ customType: NUDGE_TYPE, content: kind === "offer" ? OFFER_NUDGE : STALL_NUDGE, display: true, attribution: "user" },
			{ triggerTurn: true },
		);
	});
}
