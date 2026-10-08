#!/usr/bin/env bash
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

THRESHOLD=5

input=$(cat)

verdict=$(printf '%s' "$input" | jq -r '
  def segment_read_only:
    . as $s
    | ($s | capture("^(?<w>[A-Za-z0-9_.-]+)").w // "") as $w
    | ($s | sub("^git\\s+((-C|-c)\\s+\\S+\\s+|--no-pager\\s+)*"; "git ") | capture("^git (?<sub>[a-z-]+)").sub // "") as $git
    | ($w | IN("cd","cat","head","tail","rg","grep","ls","find","wc","jq","stat","file","tree","du","readlink","realpath",
               "which","sort","uniq","cut","tr","column","diff","basename","dirname","echo","printf","pwd","date","nl","tac"))
      or ($w == "sed" and ($s | test("^sed\\s+-n")))
      or ($w == "git" and ($git | IN("log","show","diff","status","blame","grep","ls-files","rev-parse","branch")));
  def bash_read_only:
    (.tool_input.command // "")
    | gsub("[0-9]?>&[0-9]|[0-9]?>\\s*/dev/null"; "")
    | (test(">") | not)
      and ([splits("\\s*(;|&&|\\|\\||\\||\\n)\\s*")] | map(sub("^\\s+"; "")) | map(select(length > 0))
           | length > 0 and all(.[]; segment_read_only));
  def read_only:
    (.tool_name | IN("Read","Grep","Glob","WebFetch","WebSearch","LS","NotebookRead"))
    or (.tool_name | startswith("mcp__lightpanda__"))
    or (.tool_name == "Bash" and bash_read_only);
  def acting:
    (.tool_name | IN("Edit","Write","NotebookEdit","Agent","Task","Workflow","SendMessage"))
    or (.tool_name == "Bash" and (bash_read_only | not));
  if (.agent_id // "") != "" then "skip"
  elif any(.tool_calls[]?; acting) then "reset"
  else ([.tool_calls[]? | select(read_only)] | length | tostring)
  end' 2>/dev/null) || exit 0

[ "$verdict" = "skip" ] && exit 0

session=$(printf '%s' "$input" | jq -r '.session_id // ""' 2>/dev/null)
session=${session//[^A-Za-z0-9-]/}
[ -n "$session" ] || exit 0

dir="${TMPDIR:-/tmp}/claude-delegate"
mkdir -p "$dir" 2>/dev/null || exit 0
state="$dir/$session"

if [ "$verdict" = "reset" ]; then
  echo 0 > "$state"
  exit 0
fi

count=$(cat "$state" 2>/dev/null || echo 0)
case "$count" in ''|*[!0-9]*) count=0 ;; esac
case "$verdict" in ''|*[!0-9]*) exit 0 ;; esac
count=$((count + verdict))

if [ "$count" -lt "$THRESHOLD" ]; then
  echo "$count" > "$state"
  exit 0
fi

echo 0 > "$state"
jq -n --arg c "DELEGATE: $count read-only tool calls in a row in the main session. If more searching, reading, log triage or web research follows, hand it to \`Explore\` (locate code) or \`general-purpose\` (research, logs, multi-file reading) on Haiku in the background with a self-contained brief, and keep only the conclusion. Keep reading yourself only for the file you are about to edit." \
  '{hookSpecificOutput:{hookEventName:"PostToolBatch",additionalContext:$c},suppressOutput:true}'
