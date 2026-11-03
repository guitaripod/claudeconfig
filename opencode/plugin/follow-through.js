import { appendFileSync } from "node:fs"

const OFFER_RE =
  /\b(want me to|would you like me to|do you want me to|shall i|should i (go ahead|start|proceed|push|commit|do|run|apply|add|fix|install|deploy|ship|build|make|delete|remove|merge|open|publish|re-?arm|resume|continue)|say the word|say (if|when|whether) you|say "?(resume|go|yes|continue|the word)|tell me (if|when|whether) you(.d)? (want|like|prefer)|let me know if|if you(.d| would)? (like|want|prefer),? (i|i.ll|i can|i could)|ready (to|for me to) (proceed|continue|start|go|implement|build|commit|push)|(continue|proceed)\?|need your go-?ahead|with your (ok|go-?ahead)|your call:)/i
const STALL_RE = /^(let me (?!know)|now,? (let me|i.ll|i will)\b|next,? (i.ll|let me)\b|i.ll now\b|i will now\b)[^?]*$/i

const OFFER_NUDGE =
  "You ended the turn offering work instead of doing it. If it is reversible and follows from my request, do it now and report the result. Keep the question and stop again only if it is a real decision (spending money, prices, a public post or release, deleting my data), needs my hands (sudo, a locked device, a login), or I asked you to wait, plan or only answer."
const STALL_NUDGE = "You announced a next step and stopped before doing it. Do that step now, then finish the task."
const NUDGES = new Set([OFFER_NUDGE, STALL_NUDGE])

const SUCCEEDED_EVENT = "session.execution.succeeded"
const RELAY_PREFIX = "Relay the message below"

function log(line) {
  try {
    appendFileSync(process.env.OPENCODE_FOLLOW_THROUGH_LOG ?? "/tmp/opencode-follow-through.log", `${new Date().toISOString()} ${line}\n`)
  } catch {}
}

/// Whether a final reply ends by offering work ("offer"), by announcing a step it never took ("stall"), or neither.
export function verdict(text) {
  const tail = text.slice(-400)
  const lines = text.split("\n").filter((line) => line.trim() !== "")
  const last = lines.at(-1) ?? ""
  if (OFFER_RE.test(tail)) return "offer"
  const sentence = last.trim().split(/(?<=[.!])\s+/).at(-1) ?? ""
  if (last.length <= 300 && (/:\s*$/.test(last) || STALL_RE.test(sentence))) return "stall"
  return undefined
}

/// The text of a message's text parts.
function textOf(message) {
  if (typeof message?.text === "string") return message.text
  return (message?.content ?? [])
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("\n")
}

/// The prompt a finished turn earns, or undefined when it ended properly or was a relay.
function nudgeFor(messages) {
  const last = messages.findLast((m) => m.type === "assistant")
  if (!last || last.error) return undefined
  const prompt = textOf(messages.findLast((m) => m.type === "user" || m.type === "synthetic"))
  if (prompt.startsWith(RELAY_PREFIX) || NUDGES.has(prompt)) return undefined
  const kind = verdict(textOf(last))
  if (kind === "offer") return OFFER_NUDGE
  if (kind === "stall") return STALL_NUDGE
  return undefined
}

export default {
  id: "follow-through",
  setup: async (ctx) => {
    const nudged = new Set()
    const reviewing = new Set()

    /// Sends one nudge per human prompt to a top-level session whose turn ended on an offer or an unfinished step.
    async function review(sessionID) {
      if (nudged.has(sessionID) || reviewing.has(sessionID)) return
      reviewing.add(sessionID)
      try {
        const nudge = await nudgeOf(sessionID)
        if (!nudge) return
        nudged.add(sessionID)
        log(`nudge session=${sessionID} kind=${nudge === OFFER_NUDGE ? "offer" : "stall"}`)
        await ctx.session.prompt({ sessionID, text: nudge }).catch((e) => log(`prompt failed session=${sessionID} err=${String(e)}`))
      } finally {
        reviewing.delete(sessionID)
      }
    }

    /// The nudge a finished turn of a top-level session earns, if any.
    async function nudgeOf(sessionID) {
      const session = await ctx.session.get({ sessionID }).catch(() => undefined)
      if (!session || session.parentID) return undefined
      const messages = await ctx.session.context({ sessionID }).catch(() => [])
      return nudgeFor(Array.isArray(messages) ? messages : [])
    }

    await ctx.session.hook("prompt", (event) => {
      if (!NUDGES.has(event.prompt?.text ?? "")) nudged.delete(event.sessionID)
    })

    void (async () => {
      try {
        for await (const event of ctx.event.subscribe()) {
          const sessionID = event?.data?.sessionID
          if (sessionID && event.type === SUCCEEDED_EVENT) void review(sessionID)
        }
      } catch {
        return
      }
    })()
  },
}
