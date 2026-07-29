#!/usr/bin/env bash
set -uo pipefail

payload=$(cat)

if command -v jq >/dev/null 2>&1; then
  prompt=$(printf '%s' "$payload" | jq -r '.prompt // ""' 2>/dev/null)
else
  prompt=$payload
fi

ELABORATION_RE='(explain|elaborate|in depth|deep dive|walk me through|why |why\?|details|detailed|how does|how do you|teach me|compare|trade-?offs|verbose|thorough|comprehensive|exhaustive|at length|long version|full (breakdown|rundown|writeup|write-up|picture|story|analysis|report)|breakdown|rundown|summar(y|ize|ise)|pros and cons|options|reasoning|rationale|justif|caveats|do(n.?t| not) be (brief|terse|short)|longer|more detail|write.*(doc|readme|guide|essay|post|report))'

if printf '%s' "$prompt" | grep -qiE "$ELABORATION_RE"; then
  directive='BREVITY: depth was requested, so give it — but still no preamble, no narrating what you are about to do, no summary of what you just did, no headers for short answers, no closing offers of help. Substance only.'
else
  directive='BREVITY CONTRACT — overrides every verbosity default, including the urge to be thorough in prose. Give the result and STOP: 1-3 sentences, or a bare list of commands/paths/facts. FORBIDDEN: preamble, restating the request, narrating plans, recapping what you just did, headers/sections on short answers, hedges, unsolicited caveats, closing offers of further help. Do not explain unless explicitly asked. Only exception, kept to one line: a blocking decision the user must make, or a real risk of data loss. When in doubt, cut it.'
fi

if command -v jq >/dev/null 2>&1; then
  jq -n --arg c "$directive" \
    '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$c},suppressOutput:true}'
else
  printf '%s\n' "$directive"
fi
