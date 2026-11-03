import type { ExtensionAPI, ExtensionContext } from "@oh-my-pi/pi-coding-agent";

const OFFER_RE =
	/\b(want me to|would you like me to|do you want me to|shall i|should i (go ahead|start|proceed|push|commit|do|run|apply|add|fix|install|deploy|ship|build|make|delete|remove|merge|open|publish|re-?arm|resume|continue)|say the word|say (if|when|whether) you|say "?(resume|go|yes|continue|the word)|tell me (if|when|whether) you(.d)? (want|like|prefer)|let me know if|if you(.d| would)? (like|want|prefer),? (i|i.ll|i can|i could)|ready (to|for me to) (proceed|continue|start|go|implement|build|commit|push)|(continue|proceed)\?|need your go-?ahead|with your (ok|go-?ahead)|your call:)/i;
const STALL_RE = /^(let me (?!know)|now,? (let me|i.ll|i will)\b|next,? (i.ll|let me)\b|i.ll now\b|i will now\b)[^?]*$/i;

const OFFER_NUDGE =
	"You ended the turn offering work instead of doing it. If it is reversible and follows from my request, do it now and report the result. Keep the question and stop again only if it is a real decision (spending money, prices, a public post or release, deleting my data), needs my hands (sudo, a locked device, a login), or I asked you to wait, plan or only answer.";
const STALL_NUDGE = "You announced a next step and stopped before doing it. Do that step now, then finish the task.";
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
	if (last.length <= 300 && (/:\s*$/.test(last) || STALL_RE.test(sentence))) return "stall";
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
