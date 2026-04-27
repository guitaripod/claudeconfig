#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"

mkdir -p "$CLAUDE_DIR"

link() {
    local rel="$1"
    local src="$REPO_DIR/$rel"
    local dest="$CLAUDE_DIR/$rel"

    if [ ! -e "$src" ]; then
        echo "  skip $rel (not in repo)"
        return
    fi

    if [ -L "$dest" ]; then
        local current
        current="$(readlink "$dest")"
        if [ "$current" = "$src" ]; then
            echo "  ok   $rel"
            return
        fi
        rm "$dest"
    elif [ -e "$dest" ]; then
        local backup="$dest.bak.$(date +%s)"
        echo "  back $dest -> $backup"
        mv "$dest" "$backup"
    fi

    mkdir -p "$(dirname "$dest")"
    ln -s "$src" "$dest"
    echo "  link $rel"
}

echo "=== Linking ~/claudeconfig -> ~/.claude/ ==="
link CLAUDE.md
link settings.json
link statusline-command.sh
link skills
echo "=== Done ==="
