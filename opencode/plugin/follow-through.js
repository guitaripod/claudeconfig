import { appendFileSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

/// The patterns and the words, read from the one file the Claude Code hook reads too, so the three agents can never
/// disagree about what an offer is or what Marcus says about it.
const RULES = JSON.parse(readFileSync(join(homedir(), "claudeconfig", "hooks", "follow-through.json"), "utf8"))
const OFFER_RE = new RegExp(RULES.offer, "i")
const STALL_RE = new RegExp(RULES.stall, "i")
const STALL_EXCEPT = new RegExp(RULES.stallExcept, "i")
const OFFER_NUDGE = RULES.offerNudge
const STALL_NUDGE = RULES.stallNudge
const NUDGE_PREFIXES = ["You ended the turn offering work", "You announced a next step"]

const SUCCEEDED_EVENT = "session.execution.succeeded"
const RELAY_PREFIX = "Relay the message below"
const STATE = Symbol.for("opencode.follow-through")

function log(line) {
  try {
    appendFileSync(process.env.OPENCODE_FOLLOW_THROUGH_LOG ?? "/tmp/opencode-follow-through.log", `${new Date().toISOString()} ${line}\n`)
  } catch {}
}

/// The state every setup in this server shares. opencode sets a plugin up again for each request, so per-instance
/// bookkeeping would let a second instance send the same turn a second nudge.
function shared() {
  globalThis[STATE] ??= { nudged: new Set(), reviewing: new Set() }
  return globalThis[STATE]
}

/// Whether a prompt is one of this plugin's own nudges rather than something Marcus typed.
function isNudge(text) {
  return NUDGE_PREFIXES.some((prefix) => text.startsWith(prefix))
}

/// Whether a final reply ends by offering work ("offer"), by announcing a step it never took ("stall"), or neither.
export function verdict(text) {
  const tail = text.slice(-400)
  const lines = text.split("\n").filter((line) => line.trim() !== "")
  const last = lines.at(-1) ?? ""
  if (OFFER_RE.test(tail)) return "offer"
  const sentence = last.trim().split(/(?<=[.!])\s+/).at(-1) ?? ""
  if (last.length <= 300 && (/:\s*$/.test(last) || (STALL_RE.test(sentence) && !STALL_EXCEPT.test(sentence)))) return "stall"
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
  if (prompt.startsWith(RELAY_PREFIX) || isNudge(prompt)) return undefined
  const kind = verdict(textOf(last))
  if (kind === "offer") return OFFER_NUDGE
  if (kind === "stall") return STALL_NUDGE
  return undefined
}

export default {
  id: "follow-through",
  setup: async (ctx) => {
    const state = shared()

    /// Sends one nudge per human prompt to a top-level session whose turn ended on an offer or an unfinished step.
    async function review(sessionID) {
      if (state.nudged.has(sessionID) || state.reviewing.has(sessionID)) return
      state.reviewing.add(sessionID)
      try {
        const nudge = await nudgeOf(sessionID)
        if (!nudge) return
        state.nudged.add(sessionID)
        log(`nudge session=${sessionID} kind=${nudge === OFFER_NUDGE ? "offer" : "stall"}`)
        await ctx.session.prompt({ sessionID, text: nudge }).catch((e) => log(`prompt failed session=${sessionID} err=${String(e)}`))
      } finally {
        state.reviewing.delete(sessionID)
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
      if (!isNudge(event.prompt?.text ?? "")) state.nudged.delete(event.sessionID)
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
