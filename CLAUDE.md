# Marcus — global rules

Everything here applies to every session on every machine. Machine-specific rules live in `~/.claude/rules/` (linked from each machine's dotfiles repo); multi-step procedures live in skills.

## Answering
- TL;DR by default: the result, recommendation or commands in 1–3 sentences or a bare list. No preamble, narration, recaps, headers on short answers, or closing offers. Elaborate only when I ask ("explain", "why", "details", "walk me through"). Enforced by `hooks/brevity.sh` + `hooks/brevity-midrun.sh` (audit with `brevity-report --before-after YYYY-MM-DD`); on opencode by `opencode/plugin/brevity.js`.
- Don't be agreeable. Push back with reasons when I'm wrong; I want great choices, not comfort.

## Code
- NEVER write inline comments. If something needs explaining, extract it into a well-named private method with a `///` (or language-equivalent) doc comment. TODO/FIXME markers and directives (`# type: ignore`, `// swiftlint:disable`) are fine.
- No file headers in Swift files.
- Surgical and lean, never half-done: edge cases, polish and verification are part of the task. Taking longer is fine; a shortcut that leaves gaps is not.

## Git
- Default branch is `master`, never `main`: `git init -b master`; if a host made `main`, `git branch -m main master`, push `-u`, `gh repo edit --default-branch master`, then delete `main`.
- NEVER add Co-Authored-By or "Generated with Claude Code" to commits or PRs (enforced by `hooks/guard-bash.sh`).
- Commit finished, verified work yourself, in the repo's message style, never bundling my unrelated in-flight changes. Pushing is mine to ask for.
- License: GPL-3.0 for every new repo (`gh api /licenses/gpl-3.0 -q .body > LICENSE`), never MIT unless I ask.

## Autonomy
- Do everything that doesn't need my account, credentials or a real decision. Don't ask permission for reversible work that follows from the request.
- "Done" means installed: whatever I launch (`/Applications/<App>.app`, `~/.cargo/bin/<name>`, a desktop entry) must be the code you just wrote. Use the repo's install script (`scripts/install-*.sh`, `cargo install --path .`), then verify the installed thing reports the new version. Getting this wrong means I report bugs you already fixed.
- Models: the session default is set in `settings.json`; inherit it for `Agent`, `Workflow` and hook model fields unless a stage needs otherwise. Opus 5 high effort is `claude-opus-5[1m]`; Fable is `claude-fable-5` (no `[1m]` variant).
- Delegate by default: self-contained, checkable work (translations and string catalogs, bulk metadata or screenshots, build/test/lint loops, log triage, per-file edits from a template, fixtures, first-draft docs) goes to a background `Agent` with `model: "sonnet"` (`"haiku"` for mechanical work), in parallel, while you keep going. Keep product, pricing and architecture decisions, StoreKit/entitlement/signing logic, money, releases, irreversible state, and the final review on the strong model. Give delegates the full spec inline, make them verify, and check their output before shipping.

## iOS apps
- Run on my iPhone Air (devicectl name "iPhone Air", id `0A19DF7B-F393-5AA6-AD32-F997CC562974`), never a simulator or the iPhone XS unless I say so.
- Every mobile app carries a file-based logger (`AppLogger` + `LogFileWriter`); add it to any app that lacks one. Logger pattern, signing, xtool-on-Linux and Sign in with Apple debugging: `ios-dev` skill. App Store Connect, releases and revenue: `app-store` skill.

## Config
- Claude Code config (this file, `settings.json`, `hooks/`, `skills/`, `workflows/`, opencode plugins and commands) lives in `~/claudeconfig` (guitaripod/claudeconfig), symlinked into `~/.claude/` and `~/.config/opencode/` by `scripts/link.sh`; `scripts/sync.sh mac` pulls it on the other machine.
- Machine dotfiles: Arch `~/dotfiles` (guitaripod/archconfig), macOS `~/macconfig` (guitaripod/macconfig; run `scripts/update-from-system.sh` after editing a tracked dotfile). Each links its `home/.claude/rules/*.md` into `~/.claude/rules/`. Neovim: `~/.config/nvim` (guitaripod/rawdog.ml.nvim), edit there only.
