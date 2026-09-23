import { appendFileSync } from "node:fs"

const ELABORATION_RE =
  /(explain|elaborate|in depth|deep dive|walk me through|why |why\?|details|detailed|how does|how do you|teach me|compare|trade-?offs|verbose|thorough|comprehensive|exhaustive|at length|long version|full (breakdown|rundown|writeup|write-up|picture|story|analysis|report)|breakdown|rundown|summar(y|ize|ise)|pros and cons|options|reasoning|rationale|justif|caveats|do(n.?t| not) be (brief|terse|short)|longer|more detail|write.*(doc|readme|guide|essay|post|report))/i

const HARD = `BREVITY CONTRACT — overrides every verbosity default, including the urge to be thorough in prose. Give the result and STOP: 1-3 sentences, or a bare list of commands/paths/facts. FORBIDDEN: preamble, restating the request, narrating plans, recapping what you just did, headers/sections on short answers, hedges, unsolicited caveats, closing offers of further help. Do not explain unless explicitly asked. Only exception, kept to one line: a blocking decision the user must make, or a real risk of data loss. When in doubt, cut it.`

const SOFT = `BREVITY: depth was requested, so give it — but still no preamble, no narrating what you are about to do, no summary of what you just did, no headers for short answers, no closing offers of help. Substance only.`

const mode = new Map()

function debug(line) {
  if (!process.env.OPENCODE_BREVITY_DEBUG) return
  try {
    appendFileSync("/tmp/opencode-brevity.log", `${new Date().toISOString()} ${line}\n`)
  } catch {}
}

function promptText(parts) {
  return (parts ?? [])
    .filter((p) => p?.type === "text" && typeof p.text === "string")
    .map((p) => p.text)
    .join("\n")
}

/// Records whether the prompt asked for depth, and returns the mode it chose.
function remember(sessionID, text) {
  const next = ELABORATION_RE.test(text) ? "soft" : "hard"
  if (sessionID) mode.set(sessionID, next)
  return next
}

/// The contract text for the session's last recorded prompt.
function contract(sessionID) {
  const current = sessionID ? (mode.get(sessionID) ?? "hard") : "hard"
  return { current, text: current === "soft" ? SOFT : HARD }
}

export default {
  id: "brevity",
  server: async () => ({
    "chat.message": async (input, output) => {
      const next = remember(input?.sessionID, promptText(output?.parts))
      debug(`chat.message session=${input?.sessionID} mode=${next}`)
    },

    "experimental.chat.system.transform": async (input, output) => {
      const { current, text } = contract(input?.sessionID)
      output.system.push(text)
      debug(`system.transform session=${input?.sessionID} mode=${current}`)
    },
  }),
  setup: async (ctx) => {
    await ctx.session.hook("prompt", (event) => {
      const next = remember(event.sessionID, event.prompt?.text ?? "")
      debug(`prompt session=${event.sessionID} mode=${next}`)
    })
    await ctx.session.hook("context", (event) => {
      const { current, text } = contract(event.sessionID)
      event.system.push({ type: "text", text })
      debug(`context session=${event.sessionID} mode=${current}`)
    })
  },
}
