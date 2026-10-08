# claudeconfig

Single source of truth for global Claude Code (and shared opencode) configuration, synced across machines.

## What's tracked

- `CLAUDE.md` — global instructions, kept short: only what applies to every session on every machine
- `settings.json` — preferences, hooks, enabled plugins, marketplaces, statusline
- `statusline-command.sh` — statusline renderer
- `hooks/` — `brevity.sh` + `brevity-midrun.sh` (answer length), `delegate-midrun.sh` (nudges the main session to hand read-only streaks to Haiku), `guard-bash.sh` (blocks Co-Authored-By trailers and opencode-serve restarts)
- `skills/` — custom user skills (procedures that load on demand: `ios-dev`, `app-store`, `kontu`, …)
- `workflows/` — Claude Code workflow scripts
- `agents/`: subagent definitions that pin Haiku and effort (`Explore` and `general-purpose` override the built-ins, `bulk` for mechanical work), since subagents otherwise inherit the session's effort
- `opencode/plugin/`, `opencode/command/` — opencode 2 equivalents of the hooks, workflows and skills (plugins default-export `{ id, setup }`), linked into `~/.config/opencode/`
- `delegate/config.yml` — shared `delegate` CLI config (tiers, classes), linked to `~/.config/delegate/config.yml`; `~/.config/delegate/host.yml` stays a real per-machine file
- `scripts/` — `link.sh` (symlinks), `sync.sh` (cross-machine pull), `brevity-report.py`, `delegation-report.py` (main vs delegated spend by model; linked as `~/.local/bin/delegation-report`), `memory-lint.py` (checks auto-memory folders; linked as `~/.local/bin/memory-lint`)

Machine-specific rules are **not** here: each machine's dotfiles repo (`guitaripod/archconfig` → `~/dotfiles`, `guitaripod/macconfig` → `~/macconfig`) keeps them in `home/.claude/rules/*.md` and links them into `~/.claude/rules/`, which Claude Code loads alongside `CLAUDE.md`. opencode picks them up through `instructions` in that machine's `~/.config/opencode/opencode.local.json`.

`settings.local.json`, runtime caches, sessions, projects, plans, tasks, history, and plugin install state stay machine-local in `~/.claude/` and are not tracked here.

The Cloudflare skills live in `skills/` (newer than the plugin's bundled copies), so the `cloudflare` plugin stays disabled; enabling it would list every Cloudflare skill twice and add four MCP servers that need OAuth. `attribution` is blanked in `settings.json` so Claude Code never asks for Co-Authored-By lines; `hooks/guard-bash.sh` remains the backstop.

## Memory

Claude Code's auto-memory is personal, so it is **not** in this public repo. It lives in the private repo `guitaripod/claudememory`, cloned at `~/claudememory`:

- `global/` is the shared store for sessions started in `~` or `~/agentapi-workdir`; `tailscode/` serves the Tailscode checkout on either machine. `map.tsv` lists which working directories use which store.
- `scripts/link.sh` (run by this repo's `link.sh`) sets `autoMemoryDirectory` in each mapped directory's `.claude/settings.local.json`, symlinks `~/.claude/projects/<dir>/memory` to the same store as a read fallback, and installs a 15-minute sync job (systemd user timer on Linux, launchd agent on macOS). A folder it replaces is kept as `memory.pre-claudememory.<epoch>` and any file not already in the store is reported as `MERGE NEEDED`.
- `scripts/sync.sh` commits what agents wrote, rebases onto the other machine and pushes; `MEMORY.md` merges as a union. `sync.sh` here runs it too.
- Every other project's memory folder stays machine-local. `memory-lint` checks all of them (broken index links, unindexed files, missing frontmatter, cut-off text, oversized indexes).

## Setup on a new machine

```bash
git clone https://github.com/guitaripod/claudeconfig.git ~/claudeconfig
~/claudeconfig/scripts/link.sh
```

`link.sh` symlinks each tracked path from `~/claudeconfig/` into `~/.claude/` (and the opencode plugin/command dirs into `~/.config/opencode/`), clones the private `claudememory` repo next to it if it is missing (same remote host and protocol as this clone) and wires memory plus its sync job. Existing files are backed up to `<file>.bak.<epoch>` before being replaced. The dotfiles repos' `link.sh` call it for you.

## Workflow

Edits go directly into `~/claudeconfig/` (the live `~/.claude/` files are symlinks). Commit and push from the repo. `scripts/sync.sh mac arch` pulls on the other machines; `sync.sh --push` pushes first.

## delegate integration

The `delegate` CLI (tiered task dispatcher, `~/Dev/rust/delegate`) is wired into both harnesses from here:

- `skills/delegate/SKILL.md` — Claude Code skill: packet fields, class table, CLI reference, manual-first rule
- `opencode/plugin/delegate.ts` — opencode plugin that adds the `delegate` tool, linked via `~/.config/opencode/plugin/`
- `opencode/command/delegate.md` — opencode `/delegate` slash command, linked via `~/.config/opencode/command/`
- `delegate/config.yml` — shared tier/class config, linked to `~/.config/delegate/config.yml`
- `omp/extensions/delegate.ts` — omp agent extension, linked to `~/.omp/agent/extensions/delegate.ts` (owned by the omp integration work, not this repo's `opencode/` tree)

All four links are created by `scripts/link.sh`. `~/.config/delegate/host.yml` (per-machine tier overrides) is never linked from here.

## lightpanda

Headless browser (no rendering: no screenshots or PDFs) exposed as the `lightpanda` MCP in all harnesses: opencode (`opencode.json`), omp (`omp/mcp.json`), Claude Code (user scope in the machine-local `~/.claude.json`; `link.sh` registers it when missing). `link.sh` installs the pinned `LIGHTPANDA_VERSION` into `~/.cargo/bin` (the opencode service PATH has no `~/.local/bin`).

## Machines

- **macbook** — macOS
- **arch** — main desktop, native Arch
- **g14** — Arch laptop
- **steamdeck** — SteamOS
