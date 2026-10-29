#!/usr/bin/env bash
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

READ_THRESHOLD=5
EDIT_THRESHOLD=3

input=$(cat)

batch=$(printf '%s' "$input" | jq -c '
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
  def edit: .tool_name | IN("Edit","Write","NotebookEdit");
  def spawn: .tool_name | IN("Agent","Task","Workflow","SendMessage");
  if (.agent_id // "") != "" then {skip: true}
  else
    [.tool_calls[]?] as $calls
    | {
        skip: false,
        spawn: any($calls[]; spawn),
        acting: any($calls[]; edit or (.tool_name == "Bash" and (bash_read_only | not))),
        reads: [$calls[] | select(read_only)] | length,
        edited: [$calls[] | select(edit) | (.tool_input.file_path // .tool_input.notebook_path // empty)
                 | select(type == "string" and length > 0 and (test("\n") | not))]
      }
  end' 2>/dev/null) || exit 0

[ -n "$batch" ] || exit 0
[ "$(printf '%s' "$batch" | jq -r '.skip')" = "false" ] || exit 0

session=$(printf '%s' "$input" | jq -r '.session_id // ""' 2>/dev/null)
session=${session//[^A-Za-z0-9-]/}
[ -n "$session" ] || exit 0

dir="${TMPDIR:-/tmp}/claude-delegate"
mkdir -p "$dir" 2>/dev/null || exit 0
reads_state="$dir/$session"
edits_state="$dir/$session.edits"

spawn=$(printf '%s' "$batch" | jq -r '.spawn')
acting=$(printf '%s' "$batch" | jq -r '.acting')
batch_reads=$(printf '%s' "$batch" | jq -r '.reads')

reads=$(cat "$reads_state" 2>/dev/null || echo 0)
case "$reads" in ''|*[!0-9]*) reads=0 ;; esac
case "$batch_reads" in ''|*[!0-9]*) batch_reads=0 ;; esac

if [ "$spawn" = "true" ] || [ "$acting" = "true" ]; then
  reads=0
else
  reads=$((reads + batch_reads))
fi

if [ "$spawn" = "true" ]; then
  : > "$edits_state"
else
  printf '%s' "$batch" | jq -r '.edited[]' >> "$edits_state" 2>/dev/null
fi
edited=$(sort -u "$edits_state" 2>/dev/null | grep -c . || true)
case "$edited" in ''|*[!0-9]*) edited=0 ;; esac

notes=()
if [ "$reads" -ge "$READ_THRESHOLD" ]; then
  notes+=("DELEGATE: $reads read-only tool calls in a row in the main session. If more searching, reading, log triage or web research follows, hand it to \`Explore\` (locate code) or \`general-purpose\` (research, logs, multi-file reading) on Haiku in the background with a self-contained brief, and keep only the conclusion. Keep reading yourself only for the file you are about to edit.")
  reads=0
fi
if [ "$edited" -ge "$EDIT_THRESHOLD" ]; then
  notes+=("DELEGATE: you have edited $edited different files yourself since your last hand-off. If more implementation follows, spec the remaining changes (goal, files, the command that proves them) and hand them to \`general-purpose\` or \`bulk\` on Haiku, split into independent pieces in parallel. Keep the review and the final check for yourself.")
  : > "$edits_state"
fi

echo "$reads" > "$reads_state"

[ "${#notes[@]}" -gt 0 ] || exit 0
context=$(printf '%s\n\n' "${notes[@]}")
jq -n --arg c "${context%$'\n\n'}" \
  '{hookSpecificOutput:{hookEventName:"PostToolBatch",additionalContext:$c},suppressOutput:true}'
