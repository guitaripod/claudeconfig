---
name: delegate
description: Delegate a bounded coding task to a cheaper model tier via the delegate CLI — write or run a task packet, check delegate runs/stats, or tune tier assignments. Load for any request to delegate work, write/run a packet, inspect delegate runs or history, or adjust which tier a class uses.
---

# delegate

Rust CLI (`~/.cargo/bin/delegate`, fallback `~/Dev/rust/delegate/target/debug/delegate`) that runs a task packet through a ladder of model tiers. Each attempt runs in an isolated git worktree; a verifier command decides pass/fail; failures escalate to the next tier; a passing patch is applied unstaged to the real working tree. Everything logs to SQLite. Models never pick tiers — only packets do, and packets are written by a human, or by Claude when the human asks for one.

## Packet
YAML at `<repo>/.delegate/packets/<ulid>.yml`. Three fields matter most:
- `goal` — what the worker must achieve, written for a reader with no other context (see below).
- `paths` — allowed paths/globs the worker may create or modify. Empty means unrestricted — always set it.
- `verify` — shell command run in the isolated worktree after the worker finishes; exit 0 passes. Leaving it unset (or using a class with `verified: false`) means nothing checks the work.

Other fields: `class` (selects tier/ceiling/verify defaults below), `id` (ULID, auto-assigned), `tier`/`ceiling` (override the class), `mode` (normal/conserve/rush), `effort` (low/medium/high), `timeout` (seconds, worker and verifier each), `attempts` (per tier before escalating), `read` (files the worker should read before starting), `notes` (free-form context appended to the worker prompt), `repo` (defaults to cwd when run). Full JSON schema: `delegate schema`.

## Classes (default tier → ceiling)
| class | tier | ceiling | verify |
|---|---|---|---|
| default | t2 | t3 | — |
| rust-mech | t1 | t2 | `cargo build && cargo test` |
| rust-impl | t1 | t3 | `cargo build && cargo clippy --all-targets -- -D warnings && cargo test` |
| swift-impl | t2 | t3 | — |
| strings | t1 | t2 | — |
| docs | t1 | t2 | unverified |
| review | t3 | t3 | unverified |

Tiers: t1 local (llama-swap Qwen 27B), t2 cheap cloud (ollama-cloud glm-5.3-flash), t3 frontier (openrouter, Claude). `delegate tiers` shows the resolved chain plus live health on this host.

## CLI
- `delegate new --class <c> --goal <text> [--path <p>]... [--verify <cmd>] [--read <file>]... [--notes <text>] [--tier <t>] [--ceiling <t>] [--mode normal|conserve|rush] [--effort low|medium|high] [--timeout <secs>] [--attempts <n>] [--repo <dir>] [-o <file>] [--edit] [--run]` — prints the packet path.
- `delegate run <packet.yml> [--tier t] [--ceiling t] [--mode m] [--attempts n] [--json] [-y]` — streams events: human lines, or with `--json` one JSON object per line (`run_id`, `seq`, `ts`, `kind`, plus per-kind fields). Kinds: `run_started`, `tier_selected`, `tier_skipped`, `attempt_started`, `progress`, `attempt_finished` (tier, attempt, status, verify_exit, duration_ms, tokens_in/out, changed_files, scope_violations, verify_tail, worker_summary), `approval_required`, `approval_resolved`, `escalated` (from, to, reason), `applied` (files, patch_bytes), `run_finished` (status: passed/failed/held/cancelled/error, passed_tier, escalations, duration_ms, summary). Exit 0 passed, 1 failed/held/cancelled, 2 error. Non-TTY runs need `-y`.
- `delegate replay <run-id> [--tier t] ...` — re-run a stored run's packet, optionally on another tier.
- `delegate log [--limit n] [--json]` — recent runs.
- `delegate show <run-id> [--json]` — one run with its attempts.
- `delegate stats [--class c] [--json]` — pass rates per class and tier.
- `delegate tiers [--json]` — resolved tier chains with live health.
- `delegate schema` — packet JSON schema.
- `delegate config init|check|path` — manage `~/.config/delegate/config.yml` (shared, symlinked from `~/claudeconfig/delegate/config.yml`) deep-merged with `~/.config/delegate/host.yml` (per-machine, real file).

## Writing a good goal
The worker sees only the packet's `goal`, `read` files, and `notes` — never this conversation. Name exact files and paths. State the acceptance criteria in the goal itself even though `verify` also gates it, so the model knows what "done" means instead of discovering it from a failing command. Bad: "fix the bug in the parser." Good: "in `src/parser.rs`, `parse_header` panics on an empty input slice; return `Err(ParseError::Empty)` instead, with `paths: [src/parser.rs]` and `verify: cargo test parser::`."

## Manual-first
Only run `delegate` when the user explicitly asks — never opportunistically, as a way to offload work you could just do yourself. Never choose or override `tier`/`ceiling` unless the user says to; tier assignment is a human decision baked into the class, not something a model picks per-task. After a run, report `delegate show <run-id>` output plus the changed files (`git status`/`git diff` in the real repo — a passing patch is already applied there, unstaged). Never commit the applied patch yourself; that's the user's call.

## Stats → promotions
`delegate stats --class <c>` gives a pass rate per tier for that class. A class that fails often at its default `tier` should move `tier` up one rung or get a tighter `verify`/`goal`; a class that passes consistently on the first tier well below its `ceiling` is a candidate to lower `ceiling` — same outcome, cheaper. Only suggest this — the user edits `~/claudeconfig/delegate/config.yml` (shared) or `~/.config/delegate/host.yml` (this machine only) themselves.

## Packets are golden
`.delegate/packets/` inside a repo is committed — it's that repo's regression set for delegate runs, not scratch output. Don't delete it or add it to `.gitignore`.
