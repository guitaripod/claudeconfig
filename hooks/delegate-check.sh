#!/usr/bin/env bash
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)

agent_type=$(printf '%s' "$input" | jq -r '.agent_type // ""' 2>/dev/null)
transcript=$(printf '%s' "$input" | jq -r '.agent_transcript_path // ""' 2>/dev/null)
retry=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ -n "$transcript" ] && [ -r "$transcript" ] || exit 0

facts=$(jq -sc '
  [.[] | select(.type == "assistant")] as $msgs
  | [$msgs[] | .message.content[]? | select(type == "object" and .type == "tool_use")]
  | reduce .[] as $t ({seen: {}, list: []};
      if .seen[$t.id] then . else .seen[$t.id] = true | .list += [$t] end)
  | .list as $tools
  | ([$tools | to_entries[] | select(.value.name | IN("Edit","Write","NotebookEdit")) | .key] | last) as $last_edit
  | {
      model: ([$msgs[] | .message.model // empty | select(. != "<synthetic>")] | last // ""),
      tool_uses: ($tools | length),
      edits: ([$tools[] | select(.name | IN("Edit","Write","NotebookEdit"))] | length),
      checked: (if $last_edit == null then null
                else ([$tools | to_entries[] | select(.key > $last_edit and .value.name == "Bash")] | length > 0) end)
    }' "$transcript" 2>/dev/null) || exit 0
[ -n "$facts" ] || exit 0

tool_uses=$(printf '%s' "$facts" | jq -r '.tool_uses')
checked=$(printf '%s' "$facts" | jq -r '.checked')

reason=""
if [ "$retry" != "true" ] && [ "$agent_type" != "workflow-subagent" ]; then
  if [ "$tool_uses" = "0" ]; then
    reason="You returned without using a single tool, so nothing you reported was checked. Do the task with your tools (search, read, edit, run the check from your brief), then report."
  elif [ "$checked" = "false" ] && { [ "$agent_type" = "bulk" ] || [ "$agent_type" = "general-purpose" ]; }; then
    reason="You changed files but ran no command after your last edit. Run the check from your brief (or the project's build or tests) now and paste the last lines of its output verbatim in your report. If no check can run here, say which one and why."
  fi
fi

log_dir="${XDG_DATA_HOME:-$HOME/.local/share}/claude-delegation"
if mkdir -p "$log_dir" 2>/dev/null; then
  printf '%s' "$input" | jq -c --argjson f "$facts" --arg r "$reason" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '{
      ts: $ts,
      session_id, agent_id, agent_type, cwd,
      retry: (.stop_hook_active // false),
      model: $f.model, tool_uses: $f.tool_uses, edits: $f.edits, checked: $f.checked,
      sent_back: ($r != "")
    }' >> "$log_dir/subagents.jsonl" 2>/dev/null
fi

[ -n "$reason" ] || exit 0
jq -n --arg r "$reason" '{decision: "block", reason: $r}'
