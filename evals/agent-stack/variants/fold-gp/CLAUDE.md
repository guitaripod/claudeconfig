# Marcus — global rules

Everything here applies to every session on every machine. Machine-specific rules live in `~/.claude/rules/` (linked from each machine's dotfiles repo); multi-step procedures live in skills.

## Answering
- TL;DR by default: the result, recommendation or commands in 1–3 sentences or a bare list. No preamble, narration, recaps, headers on short answers, or closing offers. Elaborate only when I ask ("explain", "why", "details", "walk me through"). Enforced by `hooks/brevity.sh` + `hooks/brevity-midrun.sh` (audit with `brevity-report --before-after YYYY-MM-DD`); on opencode by `opencode/plugin/brevity.js`.
- Don't be agreeable. Push back with reasons when I'm wrong; I want great choices, not comfort.

## Code
- NEVER write inline comments. If something needs explaining, extract it into a well-named private method with a `///` (or language-equivalent) doc comment. TODO/FIXME markers and directives (`# type: ignore`, `// swiftlint:disable`) are fine.
- No file headers in Swift files.
- Surgical and lean, never half-done: edge cases, polish and verification are part of the task. Taking longer is fine; a shortcut that leaves gaps is not.

## Secrets
- Never print, echo or paste a secret value (API key, token, password, private key) into chat, code, commits or logs; reference the env var instead. Store it in a 1Password Environment and mount it as a live `.env` with the `1password-environments` skill.

## Git
- Default branch is `master`, never `main`: `git init -b master`; if a host made `main`, `git branch -m main master`, push `-u`, `gh repo edit --default-branch master`, then delete `main`.
- NEVER add Co-Authored-By or "Generated with Claude Code" to commits or PRs (enforced by `hooks/guard-bash.sh`).
- Commit finished, verified work yourself, in the repo's message style and the imperative mood ("Fix…", "Add…", "Remove…"), never bundling my unrelated in-flight changes. Pushing is mine to ask for.
- License: GPL-3.0 for every new repo (`gh api /licenses/gpl-3.0 -q .body > LICENSE`), never MIT unless I ask.

## Autonomy
- Do everything that doesn't need my account, credentials or a real decision. Don't ask permission for reversible work that follows from the request.
- "Done" means installed: whatever I launch (`/Applications/<App>.app`, `~/.cargo/bin/<name>`, a desktop entry) must be the code you just wrote. Use the repo's install script (`scripts/install-*.sh`, `cargo install --path .`), then verify the installed thing reports the new version. Getting this wrong means I report bugs you already fixed.
- Models: use aliases (`opus`, `sonnet`, `haiku`, `fable`), never dated IDs, so new releases land without edits. Opus 5.5 and Sonnet 5.5 have 1M context without `[1m]`.
- Work in one loop. Plan, locate, read, edit, run and verify in this session, loading skills for procedure; context and cache stay warm and nothing is lost at a hand-off. Search big inputs with tools (`rg`, `jq`, `sed -n`, a short script) instead of handing them to a reader agent.
- Spawn only for independent work that runs in parallel with fresh, discardable context: `bulk` (Haiku, medium) for mechanical fan-out with a checker (translations and catalogs, per-file templated edits, fixtures), a workflow for multi-source fan-out (`/flyr`, `/verdict`, `/hinta-best`), `fork` for a parallel side quest that needs this conversation. Never hand off work that chains on what you just read, and never escalate a delegate to `sonnet` or `opus`: do that work yourself. Give every workflow `agent()` `model: 'haiku'` and an `effort` (`medium` to extract, search or grind, `high` to judge or research); never run Haiku at `low`. Decisions, money, signing, releases and irreversible state never leave this session.
- A delegate gets the full spec inline and the command that proves the result, and reports that command's last output lines verbatim. Reject a result with zero tool uses or without that output, and rerun the command yourself before shipping. `hooks/delegate-check.sh` sends a delegate back once when it used no tools or edited without running a command afterwards; `delegation-report --before-after DATE` measures spend.

## iOS apps
- Run on my iPhone Air (devicectl name "iPhone Air", id `0A19DF7B-F393-5AA6-AD32-F997CC562974`), never a simulator or the iPhone XS unless I say so.
- Store and marketing screenshots: frame EVERY device type (iPhone, iPhone Duo, iPad, Mac, Watch) with the `frames` CLI (`frames-cli` skill: `frames doctor` first, `frames --json info` to see the match), never a hand-drawn bezel or rounded rectangle; composition scripts call `frames` for the bezel and only add background and captions.
- Every mobile app carries a file-based logger (`AppLogger` + `LogFileWriter`); add it to any app that lacks one. Logger pattern, signing, xtool-on-Linux and Sign in with Apple debugging: `ios-dev` skill. App Store Connect, releases and revenue: `app-store` skill.

## Web
- WebSearch to discover URLs (US-only summaries; it can't open walled or JS pages). Read a known URL with WebFetch first; on consent walls, JS-rendered pages or redirects it fails, so switch to Lightpanda (`mcp__lightpanda__*`, load via ToolSearch; runs from my IP): `markdown {url}`, then `tree`/`links`/`extract`. Never run two Lightpanda calls in parallel (one shared page), and never `evaluate` big payloads on huge pages: it hangs with ExecutionTerminated and wedges the session.
- YouTube: consent wall falls to `evaluate` `document.cookie = "SOCS=CAI; domain=.youtube.com; path=/; max-age=31536000"` then reload. For search results and playlists use curl with `-H 'Cookie: SOCS=CAI; CONSENT=YES+'` and a browser UA, parsing `ytInitialData` in Python, or `yt-dlp --flat-playlist`; ad-hoc yt-dlp takes `--cookies-from-browser vivaldi` (Premium), never my `ytd` aliases' `--exec` hook.
- Never claim a store has something from search snippets; verify on the page, and report a geo-block (JP stores 403 my IP) as unverified. No DRM circumvention.

## Config
- Claude Code config (this file, `settings.json`, `hooks/`, `skills/`, `workflows/`, `agents/`, opencode plugins and commands) lives in `~/claudeconfig` (guitaripod/claudeconfig), symlinked into `~/.claude/` and `~/.config/opencode/` by `scripts/link.sh`; `scripts/sync.sh mac` pulls it on the other machine.
- Machine dotfiles: Arch `~/dotfiles` (guitaripod/archconfig), macOS `~/macconfig` (guitaripod/macconfig; run `scripts/update-from-system.sh` after editing a tracked dotfile). Each links its `home/.claude/rules/*.md` into `~/.claude/rules/`. Neovim: `~/.config/nvim` (guitaripod/rawdog.ml.nvim), edit there only.
