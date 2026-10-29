# agent-stack eval

End-to-end eval of the Claude Code stack (CLAUDE.md, rules, subagents, hooks, skills, MCPs) on ten golden tasks that mirror real work. It exists to decide, one change at a time, whether a subagent stays, folds into the main loop or a skill, or becomes a tool, following Anthropic's "Building agents: When to fold subagents into your main agent loop" (2026-10-22).

## Layout

- `tasks/<ID>/`: one golden task
  - `task.json`: `id`, `prompt`, `probe` (the stack element it stresses), `timeout_s`, `budget_usd`, optional `expect_skill`
  - `setup.sh WORKDIR`: fills an empty WORKDIR with the fixture. Deterministic; network only through `$EVAL_CACHE` (cached clones)
  - `grade.py WORKDIR ANSWER_FILE`: prints one JSON line `{"score": 0..1, "checks": {...}}` and never raises. It grades a temp copy, never WORKDIR itself, and runs hidden tests from the task dir
  - `reference.sh WORKDIR`: applies the known-good solution in WORKDIR and prints the reference answer (QA tasks) to stdout
  - `hidden/`, `fixture/`, `reference/`: whatever the three scripts need
- `variants/<name>/`: a stack variant overlaid on the live config (see `lib/variant.py`)
- `lib/validate.py [IDs]`: proves each grader (untouched fixture < 0.5, reference = 1.0)
- `lib/run.py`: runs tasks × trials against a variant in an isolated `CLAUDE_CONFIG_DIR`
- `lib/compare.py`: per-task flips, score, cost and latency between two runs

## Running

```bash
export EVAL_HOME=~/.cache/agent-stack-eval
python3 lib/validate.py
python3 lib/run.py --variant baseline --trials 3 --model sonnet
python3 lib/run.py --variant fold-gp --trials 3 --model sonnet
python3 lib/compare.py baseline fold-gp
```

Runs never touch the live config: each variant is built from scratch under `$EVAL_HOME/cfg/`, auto-memory writes go to a copy of `~/claudememory/global`, `delegate-check.sh` logs to `$EVAL_HOME/xdg`, and transcripts stay out of `~/.claude/projects`, so `delegation-report` is unaffected.

Every variant links `.credentials.json` to `~/.claude/.credentials.json`. A token refresh during a run replaces that link with a file; `run.py` moves the newer token home after each run and relinks, so no copy of the token stays under `EVAL_HOME`. Two invocations running past a token lifetime can still race on the refresh; a run that fails that way is marked `infra_error`.

`EVAL_HOME` defaults to `~/.cache/agent-stack-eval`. Keep it off tmpfs: runs keep their workdirs (build trees, a 25 MB log, a ripgrep checkout) for regrading.

## Degradation rule

A task degrades when its mean score under the candidate falls at least one trial's worth (1/trials) below the base. A degraded task is rerun with the same number of trials under both variants; it counts only if the drop reproduces. Any confirmed degradation stops the fold sequence.
