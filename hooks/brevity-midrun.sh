#!/usr/bin/env bash
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

session=$(cat | jq -r '.session_id // ""' 2>/dev/null)
session=${session//[^A-Za-z0-9-]/}

state="${TMPDIR:-/tmp}/claude-brevity/$session"
if [ -n "$session" ] && [ -r "$state" ] && [ "$(cat "$state" 2>/dev/null)" = "soft" ]; then
  exit 0
fi

jq -n --arg c 'BREVITY still in force. The tool work is not the answer — when you stop calling tools, give the result only: 1-3 sentences or a bare list. No recap of the steps you just took, no headers, no closing offer of help.' \
  '{hookSpecificOutput:{hookEventName:"PostToolBatch",additionalContext:$c},suppressOutput:true}'
