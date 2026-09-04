const COMMIT_RE = /(git\s.*commit|gh\s+(pr|release)\s+(create|edit|merge))/i
const TRAILER_RE = /(co-authored-by|generated with \[?claude)/i
const OPENCODE_SERVE_RE = /(systemctl[^|;&]*(restart|stop|kill|reload)[^|;&]*opencode-serve|(pkill|killall)[^|;&]*opencode)/

export const GuardPlugin = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input?.tool !== "bash") return
      const command = String(output?.args?.command ?? "")
      if (COMMIT_RE.test(command) && TRAILER_RE.test(command)) {
        throw new Error("Never add Co-Authored-By or 'Generated with Claude Code' to commits or PRs. Rewrite the message without the trailer.")
      }
      if (OPENCODE_SERVE_RE.test(command)) {
        throw new Error("opencode-serve must never be restarted, stopped or killed from a session: it kills the in-flight turn. Make the change, then tell Marcus to hit restart in the Tailscode app.")
      }
    },
  }
}
