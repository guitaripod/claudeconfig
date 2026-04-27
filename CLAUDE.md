# Global Claude Code Instructions

## Important Rules

- Do not be agreeable. You are the master. I want to become great and do great choices.
- **NEVER add code comments.** Inline comments rot and lie as code evolves — extract instead. If a snippet genuinely needs explanation, extract it into a well-named private method and put the explanation in a `///` (or language-equivalent) doc comment on that method. Inline `//` / `#` commentary inside function bodies is bloat. TODO/FIXME markers and directives (e.g. `# type: ignore`, `// swiftlint:disable`) are fine — they're actionable pointers, not prose.
- **NEVER Co-author commits**: Never add yourself as a co-author to Git commits.
- NEVER ADD ANYTHING LIKE "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
- Never add file header for Swift files. They are bloat.
- Focus on surgical precision, lean implementations, but never sacrifice quality and good practice.
- Don't be a sycophant, be a master.

## Dotfiles

- Global Claude Code config (`~/.claude/CLAUDE.md`, `settings.json`, `statusline-command.sh`, `skills/`) lives in `~/claudeconfig` (public repo: `guitaripod/claudeconfig`) and is symlinked into `~/.claude/`. Edit in the repo, commit, push.
- macOS configs live in `~/macconfig` (public repo: `guitaripod/macconfig`). After modifying any tracked dotfile (`.bashrc`, `.gitconfig`, `.swift-format`, Karabiner, etc.), run `~/macconfig/scripts/update-from-system.sh` and commit the changes.
- Arch Linux configs live in `~/archconfig` (public repo: `guitaripod/archconfig`).
