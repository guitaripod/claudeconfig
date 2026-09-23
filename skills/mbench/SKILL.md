---
name: mbench
description: Benchmark a local model that llama-swap serves on the Arch box with the mbench CLI and rank it on the leaderboard - speed (decode, concurrency, long-prompt prefill) plus quality (MMLU-Pro, AIME 2025, LiveCodeBench, needle retrieval, tool calls), optional localmaxxing submissions. Load when asked to benchmark, compare or rank local models, add a new model to the leaderboard, or check benchmark progress.
---

# mbench

`mbench` (source `~/Dev/python/mbench`, public at github.com/guitaripod/mbench; installed here with `uv tool install --editable`, so edits are live) runs a fixed suite against any llama-swap model and writes results to `~/.local/share/mbench/bench.db`. It then rebuilds `~/.local/share/mbench/leaderboard.html`.

## Running

```
mbench run <llama-swap id> --detach          full suite (3–6 h, 10+ for a slow or rambling model); returns immediately
mbench run <id> --quick --detach             30–60 min, ranked as provisional
mbench run <id> --smoke                      ~5 min pipeline check, never ranked
mbench run <id> --effort max --detach        the model's highest declared effort; ranked separately from medium
mbench run <id> --submit [all|speed|evals]   also localmaxxing: verified speed runs and/or GSM8K/HellaSwag shards
mbench status   ·   mbench wait [run]   ·   mbench logs -f   ·   mbench cancel   ·   mbench resume <run>
mbench ls       ·   mbench board --open   ·   mbench profile <id>
```

- From an agent session, always pass `--detach`. The worker is a transient systemd unit (`mbench-<run>`), so it survives the session; never wrap the run itself in a backgrounded shell.
- To hear when it ends, run `mbench wait <run>` as a background shell, not a loop over `mbench status`: status says "No run in progress" while a run is parked after giving way, which ends such a loop early. `wait` prints a line on each phase change and every 5 minutes (so claude-bridge never ends it as silent) and exits 0 on complete, 1 on failed or cancelled. `mbench status` shows the current task's time left at this session's pace and the tasks still to come.
- One run at a time. A run swaps the model into the GPU through llama-swap, which unloads whatever else was loaded. Tell Marcus before starting a full run: it occupies the GPU for hours.
- The run waits up to 30 minutes for other GPU work (ComfyUI) before measuring speed. After that it still gives the GPU away whenever another process holds 25% of it or 4 GB for a minute (ComfyUI with models loaded counts even when idle): it unloads and retries every ten minutes, so each yield costs 10–15 minutes. `--keep-gpu` turns that off. It stops itself and unloads the model if free RAM falls under 4 GB.
- `at effort max (medium)` in the launch line means max resolves to the same level as medium: the chat template only switches thinking on or off. The two runs would answer identically, so `mbench run <id> --effort max --reuse` carries the medium run's answers over instead of measuring again.

## Adding a model

1. Add the model to `~/.config/llama-swap/config.yaml`. Add an override in `~/.omp/agent/models.yml` with `compat.thinkingFormat` and `contextWindow`; that is where mbench learns how to pass a thinking level.
   For llama.cpp, the slot count sets how long quality takes. Use `--parallel 8 --kv-unified` with `--ctx-size` 160k or more: each question holds its prompt plus 16k of the shared pool, and measured here llama.cpp's throughput climbs to about 8 requests at once (3.7× one request) and stays flat after that. A `--kv-unified` pool too small for two questions runs every question alone, which is how the 16k phone twins ran. Give a twin `--ctx-size` = slots × its window without `--kv-unified`, so each slot keeps the phone's window. The doctor line `questions run N at a time` (from `mbench doctor <id>`, or at the top of each run's log) confirms it.
2. Optional: add `[<id>]` to `~/.config/mbench/models.toml` with `hf_id` and `quantization` (both required for `--submit`), `spec = { method, draft, tokens_per_step, window }` and `engine = { repository, commit, version }`.
3. Run `mbench profile <id>` to see what was resolved and from where, then `mbench run <id> --detach`.

## Phone runs (iPhone Air)

A phone row is two runs: the phone measures speed, thermals and battery, its quality comes from a desktop twin of the
same `.gguf`. Set `twin = "<twin id>"` in the phone entry and the board links the twin's newest complete full run by
itself — `--quality-from` is only for naming a specific run.

1. Download the `.gguf` into `/mnt/nvme8tb/Downloads/phone-models/`, then `mbench phone push <path>` (minutes for a GB).
2. `~/.config/llama-swap/config.yaml`: a `<id>-gguf` twin entry pointing at that same file, added to the `phone-twins`
   group. llama-swap runs with `--watch-config`, so it reloads on its own.
3. `~/.config/mbench/models.toml`: `["<id>-air"]` with `twin`, `hf_id`, `quantization` and
   `phone = { file, n_ctx, parallel = 4, flash_attn = "on", cache_type_k = "q8_0", cache_type_v = "q8_0", extra_args = ["-kvu"] }`.
4. Port forwards must already be up, and they must outlive the session:
   `systemd-run --user --unit=mbench-forward-8080 --collect ~/.local/bin/pymobiledevice3 usbmux forward 18080 8080`
   (and 18081 → 8081). A run never sets them up itself.
5. `mbench phone launch` then `mbench phone health`; the app must stay foreground with the screen on.
6. `mbench run <id>-air --detach`, and the twin on the GPU. The two devices are separate, so both can run at once.

- A phone run yields to the desktop's RAM floor like any other run, so a GPU run starting can park it for ten minutes.
- `mbench phone logs` pulls both `mbenchd.log` and `llama-server.log`; the llama-server one is appended across runs and
  its timestamps are elapsed, not wall clock.
- The app restarting mid-run is reported as "iOS killed the app", but that is inferred from uptime going backwards.
  Confirm it with `pymobiledevice3 crash ls`: a real kill leaves a `JetsamEvent-*.ips`, a real crash an `mbenchd-*.ips`.

## Comparability

- Datasets are pinned by sha256; subsets and needle prompts use seed 0.
- Speed runs are greedy. Quality runs use each model's recommended sampling, with repeats and 95% intervals.
- llama.cpp servers get per-question seeds. SGLang servers never do: its FlashInfer sampler asserts on seeded top-k/top-p requests and would stop the server.
- The suite version lives in `mbench/suite.py`. Changing a budget, a sample count or a dataset pin means bumping `VERSION`, because runs under different versions are not comparable.
- Most of a slow run's tokens go to answers that loop until they hit the 32k/64k cap and score nothing: 84% of SuperGPQA's tokens for MiMo-V2.6-Distill 9B, and 50–75% for the small models. A cutoff for repetitive loops was simulated on 13k stored answers (September 2026). It saved about 5% of tokens and would have taken away about 20 answers that scored, so the budgets stay whole.
- The board ranks each effort level separately, by each model's newest complete full run at that effort. Quick and legacy runs stand in, marked provisional. Smoke runs are never shown.
- `mbench -h` and `mbench run -h` list every option with examples.
