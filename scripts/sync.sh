#!/usr/bin/env bash
# Sync shared agent config repos across Marcus's machines.
#   sync.sh                pull + prune junk on THIS machine
#   sync.sh mac arch x1    also sync those hosts (must be in ~/.ssh/config)
#   sync.sh --push         commit nothing; just push pending commits here first
set -euo pipefail

REPOS=(~/claudeconfig ~/.config/opencode)

prune_junk() {
    find "$1" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
    find "$1" -name .DS_Store -delete 2>/dev/null || true
}

sync_local() {
    local dirty=0
    for r in "${REPOS[@]}"; do
        [ -d "$r/.git" ] || { echo "skip: $r (no repo)"; continue; }
        echo "== $r"
        if ! git -C "$r" pull --ff-only --autostash -q 2>/dev/null; then
            echo "   WARN: pull failed (local changes?)"
        fi
        [ -n "$(git -C "$r" status --porcelain)" ] && dirty=1
        git -C "$r" status --porcelain | sed 's/^/   /'
        prune_junk "$r"
    done
    if [ "$dirty" -eq 1 ]; then echo "NOTE: dirty repos above — check before pushing"; fi
}

main() {
    local push=0
    local hosts=()
    for a in "$@"; do
        if [ "$a" = "--push" ]; then push=1; else hosts+=("$a"); fi
    done
    if [ "$push" -eq 1 ]; then
        for r in "${REPOS[@]}"; do
            [ -d "$r/.git" ] || continue
            [ -n "$(git -C "$r" status --porcelain)" ] && { echo "skip push: $r is dirty"; continue; }
            git -C "$r" push -q && echo "pushed: $r"
        done
    fi
    sync_local
    for h in "${hosts[@]}"; do
        echo "== $h"
        ssh -o ConnectTimeout=8 "$h" 'bash -s' <<'EOF'
set -euo pipefail
for r in ~/claudeconfig ~/.config/opencode; do
    [ -d "$r/.git" ] || continue
    echo "== $r"
    git -C "$r" pull --ff-only --autostash -q 2>/dev/null || echo "   WARN: pull failed"
    git -C "$r" status --porcelain | sed 's/^/   /'
done
find ~/claudeconfig -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
find ~/claudeconfig -name .DS_Store -delete 2>/dev/null || true
EOF
    done
}

main "$@"
