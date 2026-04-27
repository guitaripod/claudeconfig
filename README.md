# claudeconfig

Single source of truth for global Claude Code configuration, synced across machines.

## What's tracked

- `CLAUDE.md` — global instructions
- `settings.json` — preferences, enabled plugins, marketplaces, statusline
- `statusline-command.sh` — statusline renderer
- `skills/` — custom user skills

`settings.local.json`, runtime caches, sessions, projects, plans, tasks, history, and plugin install state stay machine-local in `~/.claude/` and are not tracked here.

## Setup on a new machine

```bash
git clone https://github.com/guitaripod/claudeconfig.git ~/claudeconfig
~/claudeconfig/scripts/link.sh
```

`link.sh` symlinks each tracked path from `~/claudeconfig/` into `~/.claude/`. Existing files are backed up to `<file>.bak.<epoch>` before being replaced.

## Workflow

Edits go directly into `~/claudeconfig/` (the live `~/.claude/` files are symlinks). Commit and push from the repo. Other machines `git pull` to sync.

## Machines

- **macbook** — macOS
- **arch** — main desktop, native Arch
- **g14** — Arch laptop
- **steamdeck** — SteamOS
