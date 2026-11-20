#!/usr/bin/env bash
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

cmd=$(cat | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -n "$cmd" ] || exit 0

rules="$(dirname "$0")/guard-rules.json"
[ -r "$rules" ] || exit 0

count=$(jq '.rules | length' "$rules")
for ((index = 0; index < count; index++)); do
  flags=-qE
  [ "$(jq -r ".rules[$index].ignoreCase" "$rules")" = "true" ] && flags=-qiE
  matched=yes
  while IFS= read -r pattern; do
    printf '%s' "$cmd" | grep $flags -- "$pattern" || { matched=no; break; }
  done < <(jq -r ".rules[$index].all[]" "$rules")
  [ "$matched" = yes ] || continue
  jq -n --arg r "$(jq -r ".rules[$index].refusal" "$rules")" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
done

exit 0
