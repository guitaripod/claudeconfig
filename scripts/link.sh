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
link agents

echo "=== Linking enabled Claude plugin skills ==="
bash "$REPO_DIR/scripts/link-plugin-skills.sh"

OPENCODE_DIR="$HOME/.config/opencode"
if [ -d "$OPENCODE_DIR" ]; then
    rel="../../claudeconfig"
    [ "$REPO_DIR" = "$HOME/claudeconfig" ] || rel="$REPO_DIR"
    ln -sfn "$rel/CLAUDE.md" "$OPENCODE_DIR/AGENTS.md"
    ln -sfn "$rel/opencode/plugin" "$OPENCODE_DIR/plugin"
    [ -L "$OPENCODE_DIR/tools" ] && rm "$OPENCODE_DIR/tools"
    ln -sfn "$rel/opencode/command" "$OPENCODE_DIR/command"
    echo "  link $OPENCODE_DIR/{AGENTS.md,plugin,command}"
fi

echo "=== Linking memory stores (private repo ~/claudememory) ==="
if [ ! -d "$HOME/claudememory/.git" ]; then
    memory_url="$(git -C "$REPO_DIR" remote get-url origin | sed 's/claudeconfig/claudememory/')"
    git clone -q "$memory_url" "$HOME/claudememory" && echo "  clone $memory_url" \
        || echo "  skip (cannot clone $memory_url; needs GitHub access to the private repo)"
fi
[ -x "$HOME/claudememory/scripts/link.sh" ] && "$HOME/claudememory/scripts/link.sh"

echo "=== Linking delegate config ==="
link_abs "$REPO_DIR/delegate/config.yml" "$HOME/.config/delegate/config.yml"

echo "=== Linking omp delegate extension ==="
link_abs "$REPO_DIR/omp/extensions/delegate.ts" "$HOME/.omp/agent/extensions/delegate.ts"
link_abs "$REPO_DIR/omp/mcp.json" "$HOME/.omp/agent/mcp.json"

echo "=== Linking workflow shims into omp commands ==="
mkdir -p "$HOME/.omp/agent/commands"
for shim in flyr hinta-best kaytetty-best; do
    link_abs "$REPO_DIR/opencode/command/$shim.md" "$HOME/.omp/agent/commands/$shim.md"
done

LIGHTPANDA_VERSION="1.0.0"

ensure_lightpanda() {
    if [ "$("$HOME/.cargo/bin/lightpanda" version 2>/dev/null)" = "$LIGHTPANDA_VERSION" ]; then
        echo "  ok   lightpanda $LIGHTPANDA_VERSION"
        return
    fi
    curl -fsSL https://pkg.lightpanda.io/install.sh | LIGHTPANDA_DIR="$HOME/.cargo/bin" bash -s "$LIGHTPANDA_VERSION" >/dev/null \
        && echo "  inst lightpanda $LIGHTPANDA_VERSION" \
        || echo "  WARN: lightpanda install failed"
}

register_lightpanda_mcp() {
    command -v claude >/dev/null || { echo "  skip lightpanda MCP (claude not installed)"; return; }
    if claude mcp get lightpanda >/dev/null 2>&1; then
        echo "  ok   lightpanda MCP (Claude Code)"
    else
        claude mcp add -s user lightpanda -- "$HOME/.cargo/bin/lightpanda" mcp >/dev/null && echo "  add  lightpanda MCP (Claude Code)"
    fi
}

echo "=== Ensuring lightpanda (headless browser MCP) ==="
ensure_lightpanda
register_lightpanda_mcp

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
ln -sfn "$REPO_DIR/scripts/brevity-report.py" "$BIN_DIR/brevity-report"
echo "  link $BIN_DIR/brevity-report"
ln -sfn "$REPO_DIR/scripts/delegation-report.py" "$BIN_DIR/delegation-report"
echo "  link $BIN_DIR/delegation-report"
ln -sfn "$REPO_DIR/scripts/memory-lint.py" "$BIN_DIR/memory-lint"
echo "  link $BIN_DIR/memory-lint"
echo "=== Done ==="
