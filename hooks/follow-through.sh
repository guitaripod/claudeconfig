#!/usr/bin/env bash
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)

retry=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null)
mode=$(printf '%s' "$input" | jq -r '.permission_mode // ""' 2>/dev/null)
if [ "$retry" = "true" ] || [ "$mode" = "plan" ]; then
  exit 0
fi

text=$(printf '%s' "$input" | jq -r '.last_assistant_message // ""' 2>/dev/null)
if [ -z "$text" ]; then
  transcript=$(printf '%s' "$input" | jq -r '.transcript_path // ""' 2>/dev/null)
  [ -n "$transcript" ] && [ -r "$transcript" ] || exit 0
  text=$(tail -n 400 "$transcript" | jq -rs '
    [.[] | select(.type == "assistant" and (.isSidechain | not))
         | .message.content[]? | select(type == "object" and .type == "text") | .text]
    | last // ""' 2>/dev/null)
fi
[ -n "$text" ] || exit 0

rules="$(dirname "$0")/follow-through.json"
[ -r "$rules" ] || exit 0
OFFER_RE=$(jq -r '.offer' "$rules")
STALL_RE=$(jq -r '.stall' "$rules")
STALL_EXCEPT=$(jq -r '.stallExcept' "$rules")

tail_text=$(printf '%s' "$text" | tail -c 400)
last_line=$(printf '%s\n' "$text" | sed '/^[[:space:]]*$/d' | tail -n 1)
last_sentence=$(printf '%s' "$last_line" | sed -E 's/^[[:space:]]+//; s/.*[.!][[:space:]]+//')

kind=""
if printf '%s' "$tail_text" | grep -qiE "$OFFER_RE"; then
  kind=offer
  reason=$(jq -r '.offerNudge' "$rules")
elif [ "${#last_line}" -le 300 ] && { printf '%s' "$last_line" | grep -qE ':[[:space:]]*$' || { printf '%s' "$last_sentence" | grep -qiE "$STALL_RE" && ! printf '%s' "$last_sentence" | grep -qiE "$STALL_EXCEPT"; }; }; then
  kind=stall
  reason=$(jq -r '.stallNudge' "$rules")
fi
[ -n "$kind" ] || exit 0

log_dir="${XDG_DATA_HOME:-$HOME/.local/share}/claude-follow-through"
if mkdir -p "$log_dir" 2>/dev/null; then
  printf '%s' "$input" | jq -c --arg k "$kind" --arg t "$tail_text" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{ts: $ts, session_id, cwd, kind: $k, tail: ($t | .[-160:])}' >> "$log_dir/stops.jsonl" 2>/dev/null
fi

jq -n --arg r "$reason" '{decision: "block", reason: $r}'
