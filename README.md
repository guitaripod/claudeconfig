# claudeconfig

Single source of truth for global Claude Code (and shared opencode) configuration, synced across machines.

## What's tracked

- `CLAUDE.md` — global instructions, kept short: only what applies to every session on every machine
- `settings.json` — preferences, hooks, enabled plugins, marketplaces, statusline
- `statusline-command.sh` — statusline renderer
- `hooks/` — `brevity.sh` + `brevity-midrun.sh` (answer length), `guard-bash.sh` (blocks Co-Authored-By trailers and opencode-serve restarts)
- `skills/` — custom user skills (procedures that load on demand: `ios-dev`, `app-store`, `kontu`, …)
- `workflows/` — Claude Code workflow scripts
- `opencode/plugin/`, `opencode/command/`, `opencode/tools/` — opencode equivalents of the hooks, workflows and skills, linked into `~/.config/opencode/`
- `delegate/config.yml` — shared `delegate` CLI config (tiers, classes), linked to `~/.config/delegate/config.yml`; `~/.config/delegate/host.yml` stays a real per-machine file
- `scripts/` — `link.sh` (symlinks), `sync.sh` (cross-machine pull), `brevity-report.py`

Machine-specific rules are **not** here: each machine's dotfiles repo (`guitaripod/archconfig` → `~/dotfiles`, `guitaripod/macconfig` → `~/macconfig`) keeps them in `home/.claude/rules/*.md` and links them into `~/.claude/rules/`, which Claude Code loads alongside `CLAUDE.md`. opencode picks them up through `instructions` in that machine's `~/.config/opencode/opencode.local.json`.

`settings.local.json`, runtime caches, sessions, projects, plans, tasks, history, and plugin install state stay machine-local in `~/.claude/` and are not tracked here.

## Setup on a new machine

```bash
git clone https://github.com/guitaripod/claudeconfig.git ~/claudeconfig
~/claudeconfig/scripts/link.sh
```

`link.sh` symlinks each tracked path from `~/claudeconfig/` into `~/.claude/` (and the opencode plugin/command dirs into `~/.config/opencode/`). Existing files are backed up to `<file>.bak.<epoch>` before being replaced. The dotfiles repos' `link.sh` call it for you.

## Workflow

Edits go directly into `~/claudeconfig/` (the live `~/.claude/` files are symlinks). Commit and push from the repo. `scripts/sync.sh mac arch` pulls on the other machines; `sync.sh --push` pushes first.

## delegate integration

The `delegate` CLI (tiered task dispatcher, `~/Dev/rust/delegate`) is wired into both harnesses from here:

- `skills/delegate/SKILL.md` — Claude Code skill: packet fields, class table, CLI reference, manual-first rule
- `opencode/tools/delegate.ts` — opencode custom tool (`delegate`), linked to `~/.config/opencode/tools/delegate.ts`
- `opencode/command/delegate.md` — opencode `/delegate` slash command, linked via `~/.config/opencode/command/`
- `delegate/config.yml` — shared tier/class config, linked to `~/.config/delegate/config.yml`
- `omp/extensions/delegate.ts` — omp agent extension, linked to `~/.omp/agent/extensions/delegate.ts` (owned by the omp integration work, not this repo's `opencode/` tree)

All four links are created by `scripts/link.sh`. `~/.config/delegate/host.yml` (per-machine tier overrides) is never linked from here.

## Machines

- **macbook** — macOS
- **arch** — main desktop, native Arch
- **g14** — Arch laptop
- **steamdeck** — SteamOS
