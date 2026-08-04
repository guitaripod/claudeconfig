#!/bin/bash

INPUT=$(cat)

if [[ -n "$CLAUDE_STATUSLINE_DEBUG" ]]; then
    printf '%s %s\n' "$(date +%s)" "$INPUT" >> /tmp/statusline-debug.log
fi

read -r SESSION_ID TRANSCRIPT MODEL_NAME < <(
    printf '%s' "$INPUT" | jq -r '[(.session_id // "-"), (.transcript_path // "-"), (.model.display_name // "-")] | @tsv' 2>/dev/null
)

git_prompt() {
    git --no-optional-locks rev-parse --git-dir > /dev/null 2>&1 || return

    local branch status upstream ahead behind
    branch=$(git --no-optional-locks branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/')

    [[ $(git --no-optional-locks status --porcelain 2> /dev/null) ]] && status="*"
    git --no-optional-locks diff --cached --quiet 2> /dev/null || status="${status}+"

    upstream=$(git --no-optional-locks rev-parse --abbrev-ref --symbolic-full-name @{u} 2> /dev/null)
    if [[ -n "$upstream" ]]; then
        ahead=$(git --no-optional-locks rev-list @{u}..HEAD --count 2> /dev/null)
        behind=$(git --no-optional-locks rev-list HEAD..@{u} --count 2> /dev/null)
        [[ $ahead -gt 0 ]] && status="${status}↑${ahead}"
        [[ $behind -gt 0 ]] && status="${status}↓${behind}"
    fi

    printf ' \033[35m(%s%s)\033[0m' "$branch" "$status"
}

## Renders "3m12s" / "45s" from a whole-second count.
human_elapsed() {
    local s=$1
    if (( s >= 3600 )); then
        printf '%dh%02dm' $(( s / 3600 )) $(( (s % 3600) / 60 ))
    elif (( s >= 60 )); then
        printf '%dm%02ds' $(( s / 60 )) $(( s % 60 ))
    else
        printf '%ds' "$s"
    fi
}

## Birth time of the run directory, so elapsed does not reset as agents append files.
## Falls back to mtime, then to the caller-supplied now, and covers BSD stat on macOS.
run_started_at() {
    local dir=$1 fallback=$2 t
    t=$(stat -c %W "$dir" 2>/dev/null) || t=$(stat -f %B "$dir" 2>/dev/null)
    if [[ -z "$t" || "$t" == "0" || "$t" == "-" ]]; then
        t=$(stat -c %Y "$dir" 2>/dev/null) || t=$(stat -f %m "$dir" 2>/dev/null)
    fi
    [[ "$t" =~ ^[0-9]+$ ]] || t=$fallback
    printf '%s' "$t"
}

## A run is live until the harness writes its <runId>.json completion record.
workflow_prompt() {
    [[ "$TRANSCRIPT" == "-" || -z "$TRANSCRIPT" ]] && return
    local root="$(dirname "$TRANSCRIPT")/$SESSION_ID"
    local runs_dir="$root/subagents/workflows"
    [[ -d "$runs_dir" ]] || return

    local now=$(date +%s)
    local out="" count=0
    local frames=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
    local spin=${frames[$(( (now * 4) % 10 ))]}

    local run_dir runid started done running name script elapsed bar filled slots i
    for run_dir in "$runs_dir"/wf_*; do
        [[ -d "$run_dir" ]] || continue
        runid=$(basename "$run_dir")
        [[ -f "$root/workflows/$runid.json" ]] && continue

        started=$(grep -c '"type":"started"' "$run_dir/journal.jsonl" 2>/dev/null) || started=0
        done=$(grep -c '"type":"result"' "$run_dir/journal.jsonl" 2>/dev/null) || done=0
        running=$(( started - done ))
        (( running < 0 )) && running=0

        name="workflow"
        for script in "$root/workflows/scripts/"*-"$runid".js \
                      "$HOME/.claude/projects/"*/*/workflows/scripts/*-"$runid".js; do
            [[ -f "$script" ]] || continue
            name=$(basename "$script" "-$runid.js")
            break
        done

        elapsed=$(( now - $(run_started_at "$run_dir" "$now") ))
        (( elapsed < 0 )) && elapsed=0

        bar=""
        slots=$(( started < 3 ? 3 : started ))
        (( slots > 8 )) && slots=8
        filled=$(( done > slots ? slots : done ))
        for (( i = 0; i < slots; i++ )); do
            if (( i < filled )); then bar+="▰"; else bar+="▱"; fi
        done

        out+=$(printf ' \033[36m%s\033[0m \033[1;36m%s\033[0m \033[32m%s\033[0m \033[90m%d✓' \
            "$spin" "$name" "$bar" "$done")
        (( running > 0 )) && out+=$(printf ' %d⟳' "$running")
        out+=$(printf ' %s\033[0m' "$(human_elapsed "$elapsed")")
        count=$(( count + 1 ))
        (( count >= 2 )) && break
    done

    printf '%s' "$out"
}

printf "\033[32m%s@%s\033[0m:\033[34m%s\033[0m%s%s" \
    "$(whoami)" "${HOSTNAME%%.*}" "$(pwd)" "$(git_prompt)" "$(workflow_prompt)"

[[ "$MODEL_NAME" != "-" && -n "$MODEL_NAME" ]] && printf ' \033[90m%s\033[0m' "$MODEL_NAME"
