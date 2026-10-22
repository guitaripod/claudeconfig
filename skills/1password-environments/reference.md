# 1Password Environments — reference

Supplement to [SKILL.md](SKILL.md). Use for setup and mount problems. Adapted
from 1Password's `1password-claude-plugin` (MIT) for the hand-wired setup below.

## Local setup

| Piece | Where |
|-------|-------|
| MCP server binary | `/opt/1Password/1password-mcp`, symlinked to `~/.local/bin/1password-mcp` |
| opencode MCP entry | `~/.config/opencode/opencode.local.json`, server name `1password` |
| Claude Code MCP entry | user scope in `~/.claude.json`, server name `1password` |

Requirements: 1Password desktop app v8 running and unlocked, **Settings >
Developer > Integrate with MCP clients** on, Developer Environments available on
the account. macOS and Linux only; Windows has no MCP server and no local mounts.

## Official documentation

Fetch hosted docs for product context, security boundaries or edge cases beyond
this skill's workflow. Index: [llms.txt](https://www.1password.dev/llms.txt)

| Topic | Doc |
|-------|-----|
| Local `.env` mounts (FIFO, git conflicts, dotenv compatibility) | [local-env-file.md](https://www.1password.dev/environments/local-env-file.md) |
| MCP server (setup, auth prompts, security model) | [mcp-server.md](https://www.1password.dev/environments/mcp-server.md) |

## When things fail

- Authentication or environment access fails — the 1Password desktop app needs unlocking or approval
- MCP server unavailable — check **Integrate with MCP clients** under **Settings > Developer**. A missing checkbox means the account lacks the `ai-local-mcp-server` feature flag (update 1Password). Enterprise admins can disable it under **Policies > Sharing and permissions > Agentic permissions > Local MCP server**
- MCP client can't launch the server — use the absolute path `/opt/1Password/1password-mcp`; `~/.local/bin` is not on every non-interactive `PATH`
- A mount is missing or disabled — see **Mount problems**

## Mount problems

If `list_local_env_files` shows a mount that is missing or disabled:

1. Check whether 1Password already has a destination for the same path (`list_local_env_files`, or the app's Destinations tab)
2. Fix the mount in 1Password (enable the destination, or remove it until migration finishes)

The import itself needs no shell — Read the `.env` directly for its keys and
values, then use the MCP tools per [SKILL.md](SKILL.md).
