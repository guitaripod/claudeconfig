import { readFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

/// What may not run and why, read from the one file the Claude Code guard reads too.
const RULES = JSON.parse(readFileSync(join(homedir(), "claudeconfig", "hooks", "guard-rules.json"), "utf8")).rules.map(
  (rule) => ({
    all: rule.all.map((pattern) => new RegExp(pattern, rule.ignoreCase ? "i" : "")),
    refusal: rule.refusal,
  }),
)

/// Why `command` must not run, or undefined when it may.
function refusal(command) {
  return RULES.find((rule) => rule.all.every((pattern) => pattern.test(command)))?.refusal
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
