---
name: mbench
description: Benchmark a local model that llama-swap serves on the Arch box with the mbench CLI and rank it on the leaderboard - speed (decode, concurrency, long-prompt prefill) plus quality (MMLU-Pro, AIME 2025, LiveCodeBench, needle retrieval, tool calls), optional localmaxxing submissions. Load when asked to benchmark, compare or rank local models, add a new model to the leaderboard, or check benchmark progress.
---

# mbench

`mbench` (source `~/Dev/python/mbench`, public at github.com/guitaripod/mbench; installed here with `uv tool install --editable`, so edits are live) runs a fixed suite against any llama-swap model and writes results to `~/.local/share/mbench/bench.db`. It then rebuilds `~/.local/share/mbench/leaderboard.html`.

## Running

```
mbench run <llama-swap id> --detach          full suite (1–4 h); returns immediately
mbench run <id> --quick --detach             30–60 min, ranked as provisional
mbench run <id> --smoke                      ~5 min pipeline check, never ranked
mbench run <id> --effort max --detach        the model's highest declared effort; ranked separately from medium
mbench run <id> --submit [all|speed|evals]   also localmaxxing: verified speed runs and/or GSM8K/HellaSwag shards
mbench status   ·   mbench logs -f   ·   mbench cancel   ·   mbench resume <run>
mbench ls       ·   mbench board --open   ·   mbench profile <id>
```

- From an agent session, always pass `--detach` and check back with `mbench status`. The worker is a transient systemd unit (`mbench-<run>`), so it survives the session. Never wrap it in a backgrounded shell or a polling loop.
- One run at a time. A run swaps the model into the GPU through llama-swap, which unloads whatever else was loaded. Tell Marcus before starting a full run: it occupies the GPU for hours.
- The run waits up to 30 minutes for other GPU work (ComfyUI) before measuring speed. It stops itself and unloads the model if free RAM falls under 4 GB.

## Adding a model

1. Add the model to `~/.config/llama-swap/config.yaml`. Add an override in `~/.omp/agent/models.yml` with `compat.thinkingFormat` and `contextWindow`; that is where mbench learns how to pass a thinking level.
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
- The board ranks each effort level separately, by each model's newest complete full run at that effort. Quick and legacy runs stand in, marked provisional. Smoke runs are never shown.
- `mbench -h` and `mbench run -h` list every option with examples.
