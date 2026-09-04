#!/usr/bin/env bash
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

cmd=$(cat | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -n "$cmd" ] || exit 0

deny() {
  jq -n --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

COMMIT_RE='(git[[:space:]].*commit|gh[[:space:]]+(pr|release)[[:space:]]+(create|edit|merge))'
TRAILER_RE='(co-authored-by|generated with \[?claude)'
OPENCODE_SERVE_RE='(systemctl[^|;&]*(restart|stop|kill|reload)[^|;&]*opencode-serve|(pkill|killall)[^|;&]*opencode)'

if printf '%s' "$cmd" | grep -qiE "$COMMIT_RE" && printf '%s' "$cmd" | grep -qiE "$TRAILER_RE"; then
  deny "Never add Co-Authored-By or 'Generated with Claude Code' to commits or PRs. Rewrite the message without the trailer."
fi

if printf '%s' "$cmd" | grep -qE "$OPENCODE_SERVE_RE"; then
  deny "opencode-serve must never be restarted, stopped or killed from a session: it kills the in-flight turn. Make the change, then tell Marcus to hit restart in the Tailscode app."
fi

exit 0
