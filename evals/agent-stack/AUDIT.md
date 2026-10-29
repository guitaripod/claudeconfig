# Agent stack audit, 2026-10-29

The yardstick is Anthropic's "Building agents: When to fold subagents into your main agent loop" (Diane Sarkis, 2026-10-22). It finds that a single agent with skills that load on demand usually beats subagent designs on quality, cost and latency. A subagent earns its place only for one of three reasons:

1. truly parallel work in fresh, throwaway context;
2. measured degradation of the single loop from context bloat;
3. tool-selection trouble, or instructions that conflict.

Otherwise procedures become skills and actions or lookups become tools. The article's migration recipe was followed here: build a small end-to-end eval first, then fold one item at a time and compare.

## Evidence

### Production, 90 days to 2026-10-26 (`delegation-report --days 90`)

| | spend | share |
|---|---:|---:|
| total | $5,119 | |
| delegated | $2,919 | 57% |
| `general-purpose` | $2,603 | 51% |
| of which Sonnet or Opus | $2,500 | |
| workflow subagents | $304 | 6% |
| `bulk` | $8 | |
| `Explore` | $3 | |
| `claude-code-guide` | $0.66 | |
| `Plan`, `statusline-setup` | 0 spawns | |

- **Escalation:** 354 of 647 spawns (54.7%) passed `model: sonnet` or `opus`. 43 of them passed `opus`, against CLAUDE.md's "never pass `opus`".
- **Brief size:** the median brief is 3.2 KB.
- **Timing:** the median spawn comes 1,127 transcript lines into its session.
- **What that means:** "delegate to Haiku" in practice meant a second Sonnet loop. The main session re-explains what it already knows, and the delegate re-reads it without the main session's cache.

### Eval: ten tasks, three trials, Sonnet 5.5 at xhigh

| step | variant | score /10 | $ per pass | wall s* | spawns per pass | degraded |
|---|---|---:|---:|---:|---:|---|
| 0 | baseline (stack as of 2026-10-26) | 9.98 | 5.19 | 1036 | 10.3 | |
| 1 | fold `Explore` | 9.98 | 5.46 | 1046 | 11.0 | none |
| 2 | fold `general-purpose` | 9.98 | 5.32 | 1206 | 8.0 | none |
| 3 | fold `Plan` and `statusline-setup` | 9.98 | 5.22 | 1053 | 8.3 | none |
| 4 | fold `bulk` (rejected) | 9.98 | 4.87 | 1261 | 6.7 | none |

\* Sum of per-task median wall time, without T07. T07's `swift build` time tracks machine load, not the variant (150 s to 735 s at equal cost).

No task flipped at any step. The 0.98 on T06 is one hidden semrange test that every variant misses.

- **No delegation on 8 of 10 tasks.** Sonnet ran them in one loop, at $0.15–0.65 and 15–190 s each, even with "Delegate to Haiku by default" loaded.
- **Delegation where it mattered.** It appeared only on the two session-scale tasks: T03 (6–9 `bulk`) and T06.
- **T06 reproduced the production pattern.** The baseline spawned 4 `general-purpose` per run and escalated 2 of them to Sonnet in every run.
- **T06 after folding `general-purpose`.** Same score, $1.37 against $1.73 (−21%) on the runs that stayed in one loop, but 515 s against 362 s (+42%). One run in three fanned out through `fork` at $2.14 and 326 s.
- **T03 after folding `bulk`.** Same score and cost (0.99 against 0.99), but 309 s against 234 s (+32%). Folding `bulk` buys nothing and costs latency.
- **Routing around denials.** With `general-purpose` and `bulk` both denied, T06 fanned out through the `claude` catch-all agent on Haiku: $1.34, 548 s.

## Decisions

| item | decision | criterion | evidence |
|---|---|---|---|
| `general-purpose` (Haiku high, escalated to Sonnet) | **fold** into the main loop | Not parallel-safe in practice: 55% of spawns are escalated chains. Context is lost at a 3.2 KB hand-off. It is the article's "sprawl" plus "context loss" failure mode | No degradation. T06 −21% cost, +42% latency. 51% of 90-day spend |
| `Explore` (Haiku medium) | **fold**: Grep, Glob and Read are the tools | Mid-conversation lookups belong in tools. The locations it returns are files the main loop reads again | No degradation, and never spawned |
| `Plan` (built-in) | **fold** (deny) | Planning is the main loop's job: it writes and revises the plan. A Haiku planner for a Sonnet or Opus main inverts capability | 0 spawns in 90 days |
| `statusline-setup` (built-in) | **fold** (deny) | The `update-config` skill already covers settings | 0 spawns in 90 days |
| `bulk` (Haiku medium) | **keep** | Truly parallel, mechanical, with a checker and throwaway context | Folding it: equal score and cost, +32% latency on T03 |
| `fork` | **keep** | Parallel side work that needs this conversation; it shares the cache | The fallback the folded T06 runs chose |
| `claude-code-guide` | **keep**: it already behaves as a lookup tool | Called like a tool, returns one answer, keeps documentation dumps out of context | 3 spawns, $0.66 in 90 days |
| `claude` (FleetView default) | **keep**, watch | Needed by FleetView. With `bulk` available the eval never used it. With `bulk` denied it was the escape hatch | Deny it only if `delegation-report` shows it replacing `general-purpose` |
| workflows `flyr`, `hinta-best`, `kaytetty-best`, `verdict` | **keep** as tools | Parallel fan-out over independent sources. The main agent calls them and gets one answer back, the article's "subagent as a tool, not a hand-off". All pin `model: 'haiku'` | |
| workflow `wwdc` | **folded into the `wwdc` skill** | A search, read and synthesize chain over a static knowledge base. The main loop fetches the indexes and READMEs with parallel tool calls | Same score (3/3), 11 s against 63 s median, $0.15 against $0.19 (follow-up below) |
| `delegate` CLI | **keep** as a tool | User-invoked and verifier-gated. Tiers are a human decision | |
| `delegate-midrun.sh` hook | **narrow** | The read-streak nudge ("hand reading to `Explore`/`general-purpose`") is gone. It now suggests `bulk` only after edits to 6 files | |
| `delegate-check.sh`, `guard-bash.sh`, brevity hooks | **keep** | Harness-level quality and write gates are where the article puts hard limits | |

## Skills, tools, MCPs and prompts

- **Fixed prompt.** About 60k tokens per request, against 31k with `--safe-mode`. Measured with Haiku `pong` probes, noise ±1.7k. Of the roughly 29k that the customizations add:
  - user MCPs, about 8k (mostly Lightpanda's server instructions);
  - CLAUDE.md plus rules, about 5k;
  - the RevenueCat plugin, about 4k.
- **The skill listing is saturated.**
  - Removing all 30 user skills frees only about 0.4k tokens, and removing the asc plugin about 0.1k. The listing has a fixed budget.
  - 38 of about 115 listed skills show no description: 14 RevenueCat, 16 asc and 8 anthropic-skills entries. Routing to them is blind, the article's tool-selection failure.
- **Deferred MCP tools are already progressive disclosure.** About 250 tool names are listed and full schemas load only through ToolSearch. Keep that.
- **Frankenprompt.**
  - CLAUDE.md said "Delegate to Haiku by default" while the harness's own Agent tool guidance says "when in doubt, don't spawn".
  - `delegate-midrun.sh` injected hand-off nudges in the middle of runs.
  - opencode's `AGENTS.md` is a symlink to CLAUDE.md, so opencode was reading routing rules for Claude Code agent types it does not have.
  - The new CLAUDE.md autonomy section removes the conflict.
- **Oversized skill bodies.**
  - `r-roms` is a 76.7 KB SKILL.md (about 19k tokens) that loads whole.
  - `frames-cli`, `wrangler`, `iphone-duo` and `steam-add-game` are each 16–24 KB.

## Migration plan, by priority

1. **Done:** deny `Explore`, `general-purpose`, `Plan` and `statusline-setup`, drop the `Explore` and `general-purpose` overrides from `agents/`, rewrite the CLAUDE.md autonomy section for one loop, narrow `delegate-midrun.sh`.
2. **Open, 2026-11-12:** run `delegation-report --before-after 2026-10-29 --days 14`.
   - Expected: the `general-purpose` line (about $29 a day) moves into main-loop spend at roughly 20% less for the same work.
   - Watch for `fork` or `claude` spawns climbing to replace it, and for longer wall time on large parallel builds.
   - If `claude` absorbs the old `general-purpose` traffic on Sonnet, deny it too.
3. **Done for Opus, dropped for replays.** The Opus pass is in the follow-up below. Production replays are dropped: the sessions worth replaying live in private repos, and this eval ships in a public one. The step 2 check covers production instead.
4. **Done:** the `wwdc` workflow became the `wwdc` skill. opencode's `/wwdc` now loads that skill, so one procedure serves both harnesses.
5. **Evaluated and rejected: raising the skill listing budget.** `skillListingBudgetFraction: 0.02` shows every description (40 blank down to 0) for +4.5k tokens per request. On the routing suite it changed nothing and cost 12% more: the asc skills route on name alone, and `revenuecat-troubleshoot` never loads either way. Scoping the plugins per project is also rejected: the RevenueCat MCP ran 21 times in 90 days, 7 of them from `~/agentapi-workdir`.
6. **Done for `r-roms`, declined for the rest.**
   - `r-roms` went from a 77 KB SKILL.md to a 5.5 KB index plus nine category files under `references/`, with all 470 links kept. `settings.json` now allows Read, Grep and Glob in the skill directories; without that, default permission mode blocked the skill from reading its own files.
   - The 16–24 KB skills stay whole. They load only when used, at 4–6k tokens, and nothing showed them doing harm.
7. **Done:** one CLAUDE.md sentence names the `workflow` tool as the fan-out in opencode and omp, which have no `bulk` or `fork`.

## Follow-up, 2026-10-30

Every run in this pass uses the folded live config, or a variant one change away from it. `baseline` is now an explicit variant that restores the pre-fold files (CLAUDE.md, the `Explore` and `general-purpose` agents, the old hook, no denies), so the comparison can be reproduced after the fold.

| suite | variants | score | $ per pass | wall s | verdict |
|---|---|---:|---:|---:|---|
| Opus main loop: T03, T04, T06, T10 × 3 | pre-fold → live | 3.97 → 3.98 | 7.83 → 7.55 | 1443 → 1574 | fold holds on Opus |
| routing: 4 prompts for skills that had no listed description × 3 | live → `skillListingBudgetFraction: 0.02` | 4.00 → 4.00, skill hits unchanged | 0.60 → 0.67 | 111 → 106 | rejected |
| wwdc: 3 knowledge-base questions × 3 | workflow → skill | 3.00 → 3.00 | 0.57 → 0.46 | 178 → 32 | folded |

- **Opus barely delegates.** On T06 the pre-fold rules spawned no subagents at all; Opus ran it in one loop. Both variants fanned T03 out to `bulk`. One pre-fold T06 run lost its OAuth session mid-run and is excluded as `infra_error`.
  - Cause: a token refresh had replaced one variant's credentials symlink with a private copy.
  - Fix: `run.py` now moves the newer token back to `~/.claude/.credentials.json` after each run and restores the link.
- **Routing failures are not about descriptions.** `revenuecat-troubleshoot` was never loaded even with its description in the listing; the model answered from what it knew.
- **The wwdc skill is about 5× faster than the workflow.** The workflow's search, read and synthesize hand-offs took about 60 s. The skill's parallel fetches in the main loop took about 11 s.
- **r-roms split checked.** A Haiku probe in default permission mode loaded `r-roms`, read only `references/sony.md`, and returned the PS2 route and Minerva mirror. Before the new Read, Grep and Glob allow rules, that read was denied.
- **Cleanup.**
  - The eval moved off the 8 GB tmpfs. Run workdirs and variant configs were deleted after grading; results and logs stay in `~/.cache/agent-stack-eval` (5 MB).
  - Raw rows stay out of the repo because they carry local paths and session ids.

## Limits

- **Model.** The full ten-task sequence ran on Sonnet. Opus covered only the four tasks most prone to delegation, in the follow-up.
- **Task size.** Single-prompt headless tasks are smaller than production sessions. T03 and T06 were scaled up after the first baseline showed no delegation on smaller versions; those runs are kept in `baseline-retired-small.jsonl` locally.
- **Ceiling.** Eight tasks sit at 1.0, so the eval detects regressions well and improvements poorly.
- **Memory.** Auto-memory is not loaded in eval runs.
- **Usage limit.** One fold-gp batch hit the weekly usage limit. `lib/run.py` now marks API-error runs `infra_error`, stops scheduling, and `compare.py` ignores them. The 13 affected runs were rerun after the reset.
