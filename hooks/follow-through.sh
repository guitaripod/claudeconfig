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

OFFER_RE='\b(want me to|would you like me to|do you want me to|shall i|should i (go ahead|start|proceed|push|commit|do|run|apply|add|fix|install|deploy|ship|build|make|delete|remove|merge|open|publish|re-?arm|resume|continue)|say the word|say (if|when|whether) you|say "?(resume|go|yes|continue|the word)|tell me (if|when|whether) you(.d)? (want|like|prefer)|let me know if|if you(.d| would)? (like|want|prefer),? (i|i.ll|i can|i could)|ready (to|for me to) (proceed|continue|start|go|implement|build|commit|push)|(continue|proceed)\?|need your go-?ahead|with your (ok|go-?ahead)|your call:)'
STALL_RE='^(let me (?!know)|now,? (let me|i.ll|i will)\b|next,? (i.ll|let me)\b|i.ll now\b|i will now\b)[^?]*$'

tail_text=$(printf '%s' "$text" | tail -c 400)
last_line=$(printf '%s\n' "$text" | sed '/^[[:space:]]*$/d' | tail -n 1)
last_sentence=$(printf '%s' "$last_line" | sed -E 's/^[[:space:]]+//; s/.*[.!][[:space:]]+//')

kind=""
if printf '%s' "$tail_text" | grep -qiE "$OFFER_RE"; then
  kind=offer
  reason="You ended the turn offering work instead of doing it. If it is reversible and follows from my request, do it now and report the result. Keep the question and stop again only if it is a real decision (spending money, prices, a public post or release, deleting my data), needs my hands (sudo, a locked device, a login), or I asked you to wait, plan or only answer."
elif [ "${#last_line}" -le 300 ] && { printf '%s' "$last_line" | grep -qE ':[[:space:]]*$' || printf '%s' "$last_sentence" | grep -qiP "$STALL_RE"; }; then
  kind=stall
  reason="You announced a next step and stopped before doing it. Do that step now, then finish the task."
fi
[ -n "$kind" ] || exit 0

log_dir="${XDG_DATA_HOME:-$HOME/.local/share}/claude-follow-through"
if mkdir -p "$log_dir" 2>/dev/null; then
  printf '%s' "$input" | jq -c --arg k "$kind" --arg t "$tail_text" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{ts: $ts, session_id, cwd, kind: $k, tail: ($t | .[-160:])}' >> "$log_dir/stops.jsonl" 2>/dev/null
fi

jq -n --arg r "$reason" '{decision: "block", reason: $r}'
