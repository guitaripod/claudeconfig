const COMMIT_RE = /(git\s.*commit|gh\s+(pr|release)\s+(create|edit|merge))/i
const TRAILER_RE = /(co-authored-by|generated with \[?claude)/i
const OPENCODE_SERVE_RE = /(systemctl[^|;&]*(restart|stop|kill|reload)[^|;&]*opencode-serve|(pkill|killall)[^|;&]*opencode|opencode\s+service\s+(stop|restart|set|unset))/

const TRAILER_REFUSAL = "Never add Co-Authored-By or 'Generated with Claude Code' to commits or PRs. Rewrite the message without the trailer."
const SERVE_REFUSAL = "opencode-serve must never be restarted, stopped or killed from a session: it kills the in-flight turn. Make the change, then tell Marcus to hit restart in the Tailscode app."

/// Why `command` must not run, or undefined when it may.
function refusal(command) {
  if (COMMIT_RE.test(command) && TRAILER_RE.test(command)) return TRAILER_REFUSAL
  if (OPENCODE_SERVE_RE.test(command)) return SERVE_REFUSAL
}

/// A shell command that prints `message` to stderr and fails, so the model reads the refusal as the tool's result.
function refusingCommand(message) {
  return `printf '%s\\n' '${message.replaceAll("'", `'\\''`)}' >&2; exit 1`
}

export default {
  id: "guard",
  setup: async (ctx) => {
    await ctx.tool.hook("execute.before", (event) => {
      if (event.tool !== "shell" || typeof event.input?.command !== "string") return
      const reason = refusal(event.input.command)
      if (reason) event.input = { ...event.input, command: refusingCommand(reason), background: false }
    })
  },
}
