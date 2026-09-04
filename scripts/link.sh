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

# Like link(), but for destinations outside ~/.claude/: src and dest are
# given as full paths instead of a name relative to REPO_DIR/CLAUDE_DIR.
link_abs() {
    local src="$1"
    local dest="$2"

    if [ ! -e "$src" ]; then
        echo "  skip $dest (not in repo yet)"
        return
    fi

    if [ -L "$dest" ]; then
        local current
        current="$(readlink "$dest")"
        if [ "$current" = "$src" ]; then
            echo "  ok   $dest"
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
    echo "  link $dest"
}

echo "=== Linking ~/claudeconfig -> ~/.claude/ ==="
link CLAUDE.md
link settings.json
link statusline-command.sh
link hooks
link skills
link workflows

OPENCODE_DIR="$HOME/.config/opencode"
if [ -d "$OPENCODE_DIR" ]; then
    rel="../../claudeconfig"
    [ "$REPO_DIR" = "$HOME/claudeconfig" ] || rel="$REPO_DIR"
    ln -sfn "$rel/CLAUDE.md" "$OPENCODE_DIR/AGENTS.md"
    ln -sfn "$rel/opencode/plugin" "$OPENCODE_DIR/plugin"
    ln -sfn "$rel/opencode/tools" "$OPENCODE_DIR/tools"
    ln -sfn "$rel/opencode/command" "$OPENCODE_DIR/command"
    echo "  link $OPENCODE_DIR/{AGENTS.md,plugin,tools,command}"
fi

echo "=== Linking delegate config ==="
link_abs "$REPO_DIR/delegate/config.yml" "$HOME/.config/delegate/config.yml"

echo "=== Linking omp delegate extension ==="
link_abs "$REPO_DIR/omp/extensions/delegate.ts" "$HOME/.omp/agent/extensions/delegate.ts"

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
ln -sfn "$REPO_DIR/scripts/brevity-report.py" "$BIN_DIR/brevity-report"
echo "  link $BIN_DIR/brevity-report"
echo "=== Done ==="
