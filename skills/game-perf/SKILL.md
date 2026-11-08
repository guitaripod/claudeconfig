---
name: game-perf
description: Diagnose and fix poor performance or low GPU usage in a Steam/Proton game on the arch desktop (i7-14700K hybrid CPU, RTX PRO 6000, KDE Wayland, LG C5 144 Hz without VRR) - live per-thread diagnosis, a headless benchmark rig that loads Marcus's save in a hidden gamescope and measures each tweak, the levers that worked (P/E-core thread placement, vkd3d descriptor heap, newest DLSS preset, DLSS frame generation locked to 144), applying them to Steam launch options and the prefix registry, and one verified real launch. Use for "game X runs badly", "only uses N% of my GPU", "stutters", "get more fps / GPU usage", "tune this game", or "make it smooth on the TV".
---

# Game performance on arch (Proton, NVIDIA, hybrid Intel)

Worked end to end on Marvel's Spider-Man Remastered on 2026-11-08 (memory
`spiderman-remastered-linux-perf`): GPU at 50% and juddering became a locked 144 fps with
1% lows of 130. The method transfers; the numbers do not. Measure every lever on the game
in front of you.

Scope: Windows games through Proton. For a native Linux game `bench.py` does not apply. Use
`diagnose.py --pid PID`, MangoHud logs by hand, and `game-cores` (it works on any process tree).

    S=~/.claude/skills/game-perf/scripts
    python3 $S/steamtools.py info APPID   # name, install dir, prefix, Proton, current launch options

The appid is in the store URL or `steamapps/appmanifest_*.acf` (libraries:
`~/.local/share/Steam` and `/mnt/nvme8tb/SteamLibrary`). The game must have run once
through Steam so `compatdata/APPID/pfx` exists.

## Ground rules

- Marcus may be playing. Diagnosis is read-only and fine during play. Never stop, relaunch or
  pin a game he is playing without saying so first. `bench.py start`, `bench.py stop` and
  `steamtools.py set` refuse while any Steam game runs.
- His MangoHud setup and the `hdr-game ... mangohud obs-gamecapture` wrapper chain are his
  (memory `feedback-dont-change-mangohud-config`). Insert new wrappers into the chain; never drop his.
- VRR is off on the C5 for good (memory `hdr-off-on-arch`, `lg-c5-tv-setup`). Never suggest it.
  Below 144 fps without VRR judders, which is why a locked 144 beats a higher uncapped average.
- Content-reducing settings (crowd, traffic, draw distance, LOD, render resolution, RT) are his
  call: measure and report the gain, do not apply.
- Anti-cheat (EAC, BattlEye, Vanguard…): check PCGamingWiki first. No headless rig, injected
  input or registry edits on online builds; offline and single-player modes only, and if unsure, don't.

## 1. Diagnose live

    python3 $S/diagnose.py --seconds 8        # or --pid PID

Classify first (memory `gaming-rig-4k-profile`):
- **Engine cap**: fps pinned at a round number (30/60/120, or the game's own limiter) while GPU and
  every thread sit well under their limits. Look for a frame-rate limit in the game's config
  (PCGamingWiki) before anything else; no lever here moves it.
- **GPU-bound**: GPU near 100%, or power/thermal clock-event reasons active (`Reliability` alone
  is normal boost). CPU levers do nothing. Only upscaling, frame generation, render resolution
  and RT settings help, and those are his settings calls: measure and report.
- **CPU wall**: GPU well under 100% with no cap. This is the usual case at 4K on this GPU, and
  everything below is for it.

Reading the output:
- Per-thread CPU split into user and kernel time, plus how often each hot thread sat on an E-core
  (CPUs 16-27). Pause the game and re-run: a thread still at ~100% user while paused is a
  spin-wait (Spider-Man's `NxStorage Command`), not the bottleneck.
- GPU idle with no thread near 100% = a latency-bound chain (main → jobs → render → submit).
  Thread placement and per-frame CPU cost are the levers, not upscaling.
- `mangohud-nvidia` kernel time ~20% = unpatched MangoHud 0.8.4 polling NVML's process list
  every 25 ms. That costs about 6% GPU throughput with ~19 GPU processes (llama-servers, ComfyUI)
  on the card. Needs 0.8.4-1.1 (the local build with upstream `065cc9f67`) or ≥ 0.8.5.
- Background contention: llama-swap POSTs (an omp/opencode session or shotcaller running local
  inference), `fossilize_replay` (Steam or `prebake` shader pre-caching, 27 workers when the
  desk looks idle), load average and PSI. Any of these invalidates benchmark numbers.
- The API decides which env levers exist. Check PCGamingWiki's API row, or the loaded DLLs:
  `grep -oE 'd3d12core|vkd3d|dxvk|d3d11' /proc/PID/maps | sort -u`.
  - DX12 runs on vkd3d-proton: `VKD3D_*` levers apply.
  - DX11 runs on DXVK: `VKD3D_*` does nothing. DXVK's own options (`DXVK_FRAME_RATE`, `dxvk.conf`) apply instead.
  - Native Vulkan gets neither.
  - DLSS levers need a game that ships DLSS: look for `nvngx_dlss.dll` in the install dir.

## 2. Benchmark headless (the rig)

A hidden gamescope (`--backend headless`) runs the game at 3840x2160 with MangoHud logging
every frame. Nothing appears on Marcus's screens and audio goes to a null sink. Steam must
be running.

    B="python3 $S/bench.py"
    $B exes APPID                                   # pick the real exe
    $B start APPID --exe Game.exe --label base --args=-nolauncher --env VKD3D_CONFIG=descriptor_heap
    $B shot s1        # prints ~/.local/state/game-perf/s1.png; Read it: launcher? menu? in game?
    $B keys Return    # sleep:2  mouse:40,0,60  Return@0.5 (hold)  Shift_L+F2
    $B measure base-1 # 33 s window: avg fps, 1% low, frame-time jitter, GPU %, W, load
    $B stop
    $B restore        # ALWAYS before Marcus plays (see below)

- Output goes to `~/.local/state/game-perf/`: screenshots there, logs in `logs/LABEL/`
  (MangoHud CSVs, gamescope.log), session state in `bench.json`.
- Key names are single characters or `Return Escape space Tab BackSpace Up Down Left Right
  Shift_L Control_L Alt_L F1 F2 F10 F11`. Anything else is rejected. Screenshot after each step.
- Games drop input sent before a menu is interactive: a `Return` sent during the splash was
  silently lost and the run measured the main menu. Wait until a screenshot shows the menu, then send keys.
- Get to a repeatable scene: load the latest save ("Continue"), then turn the camera a fixed
  amount with `mouse:` so it looks down a busy street. The same keys land in nearly the same view
  after every launch, but his saves move, so verify with a screenshot every run.
- Thread placement can be A/B'd live: `start --launcher none`, then `$B place all|p|p+helpers`
  between `measure` calls (the same patterns as `game-cores`). Everything else needs a relaunch per
  variant: env vars, registry values, and `--launcher game-cores|taskset`.
- Launch-to-launch noise was ±5%, so interleave (A B A B …) with two windows per launch. Discard
  runs where `load` in the result line is high or llama-swap shows POSTs.
- The headless display is SDR, so games rewrite HDR settings in user.reg. `start` backs up user.reg
  once; `restore` copies it back. If Marcus played between a bench and the restore, diff first
  (`diff ~/.local/state/game-perf/user.reg.APPID.orig PREFIX/pfx/user.reg`) and keep his changes.
- In-game menus work over XTest. Spider-Man's "Apply changes?" dialog needs `Left` then `Return`
  or it reverts after 25 s. Expect similar confirm dialogs elsewhere.
- The real path (Wine's Wayland driver + HDR on KWin) cannot be reproduced headless:
  gamescope `--expose-wayland` hung before the window appeared. Benchmark on the X11 path, then
  verify the winners once for real (step 4).

## 3. Levers, in the order they paid off

The first question for any game with frame generation is whether it presents uncapped into the
non-VRR TV. FF7 Rebirth (~187 fps) and Ragnarök (FG on, vsync off) did: forcing FIFO turned that
into a locked 144 before any CPU lever mattered. Results per game live in the per-game memories
(`spiderman-remastered-linux-perf`, `game-perf-round2-2026-11-08`).

| Lever | How | Measured on Spider-Man |
|---|---|---|
| Thread placement | `/home/marcus/.local/bin/game-cores` in the launch chain (dotfiles `scripts/game-cores.py`). All threads go on P-cores. Helper threads and helper processes go on E-cores: streaming, audio, shader compiles, Wine plumbing, overlays, crash reporter, Proton's steam.exe. The default thread regex was tuned on Spider-Man (it names `NxStorage`). For a new game, read the hot thread names in `diagnose.py` and set `GAME_CORES_HELPERS` if the game's helpers are named differently. | all cores ~102 → P-only ~111 → game-cores ~114 fps, better 1% lows |
| vkd3d descriptor heap (DX12 only) | `VKD3D_CONFIG=descriptor_heap` (vkd3d-proton 3.1 in GE-Proton11-12; default-on in later builds, opt out with `no_descriptor_heap`) | 119 → 127 fps avg over 6 launches each. Check characters for skinned-mesh corruption in a full-res crop (`shot NAME --crop 1500x1000+X+Y`); one 615.x report of this in another game. Game-specific: FF7 Rebirth no change, Uncharted 99 → 80 fps. Games with their own PSO cache (FF7 Rebirth "Preparing shaders", Uncharted "Building Shaders", ~10 min) rebuild it on every toggle, so test it last and switch back before restoring |
| Newest DLSS model (DLSS games only) | `DXVK_NVAPI_DRS_SETTINGS=ngx_dlss_sr_override=on,ngx_dlss_sr_override_render_preset_selection=render_preset_latest,ngx_dlss_rr_override=on,ngx_dlss_fg_override=on` with `PROTON_DLSS_UPGRADE=1`. GE's default keeps the game's own preset (Spider-Man: CNN preset E, Witcher 3: CNN preset A). Add `ngx_dlss_rr_override_render_preset_selection=render_preset_latest` for ray reconstruction. `ngx_dlss_sr_mode=dlaa\|quality\|balanced\|performance` forces the mode, even DLAA in a DLSS 2 game that lacks it (Uncharted: DLAA K 95 fps vs native TAA 99.5); a mode change is his image call, so measure and report | preset K, no fps cost while CPU-bound. "Latest" resolves per mode: M for Performance, K for Quality and DLAA |
| DLSS Frame Generation + vsync (DLSS-G games only) | Enable FG in the game. Spider-Man's registry has `FrameGen=2` (1 is FSR FG). For DX12, force FIFO with `VKD3D_SWAPCHAIN_PRESENT_MODE=FIFO`, because games grey out their own vsync with FG | uncapped ~200 fps juddered on the non-VRR C5. Locked: 144.0 fps, 1% low 130, jitter 0.35 ms (vs ~120 / ~85 without FG) |
| CPU-cost settings | crowd/traffic density, LOD, RT object range | his call; report numbers only |
| Not worth it | `force_static_cbv` (noise, one hitchy run); DLSS upscaling on a CPU-bound game (no fps); SMT-off pinning (0,2,…,14: no better); RT reflections when CPU-bound (more CPU work); helper threads on E-cores in UE4 (FF7 Rebirth 1% lows 102 → 85: its streaming threads matter); an engine fps cap under FIFO (no change); custom `WINE_CPU_TOPOLOGY` for Uncharted (8 cores 75 fps, 8P+8E 101: protonfixes' 16-CPU limit already lands on CPUs 0-15, the P-cores) | |

Check DLSS state with `PROTON_DLSS_INDICATOR=1`: bottom-left shows preset and version, and the
top `DLSSG` line shows `2x` when FG runs. Take it out again before the final options.

## 4. Apply, verify once for real, record

1. **Registry** (game closed, no wineserver for that prefix):
   - Copy `PREFIX/pfx/user.reg` to a dated backup.
   - Find the game's key with `grep -n 'Software\\\\<Publisher>' PREFIX/pfx/user.reg`. Spider-Man's is
     `[Software\\Insomniac Games\\Marvel's Spider-Man Remastered\\Graphics]`.
   - Find what a value means by changing that setting once in the in-game menu (headless rig) and
     diffing user.reg.
   - Edit with a short script that asserts the old `"Name"=dword:...` line occurs exactly once inside that key.
2. **Launch options:**
   - `python3 $S/steamtools.py set APPID 'OPTIONS'`. It validates first, then stops Steam, backs up
     localconfig.vdf (`*.bak-gameperf-*`), writes atomically, starts Steam through systemd and reads
     the line back.
   - Order: env vars, then `/home/marcus/.local/bin/hdr-game /home/marcus/.local/bin/game-cores
     mangohud obs-gamecapture %command%`, then game args.
   - Rollback: `steamtools.py backups APPID`, then `steamtools.py restore BACKUP`.
3. **One real launch**, only when Marcus is away or says so:
   - Run `steam steam://rungameid/APPID` and wait for GPU > 30%.
   - Take `spectacle -b -n -f -o /tmp/claude-1000/…/scratchpad/real.png` (an absolute scratch path).
     The screenshot is at 2x the logical layout. Take DP-1's logical geometry from
     `kscreen-doctor -o` and double it for the crop box.
   - Confirm HDR colours, the DLSS indicator, and `game-cores` placement (`Cpus_allowed_list` in
     `/proc/PID/task/*/status`).
   - If Marcus takes over the session, let him play. Run a background loop that waits on
     `steamtools.game_running()` to go False (30 s grace), then runs `steamtools.py set` with the
     final options (indicator removed).
4. **Record** the game's facts in a per-game memory: registry keys, what helped and by how much,
   final options, the rollback backup. Note anything new about the rig in this skill.

## Traps

- The agent shell blocks SIGTERM and children inherit it (memory `claude-bash-signal-mask`).
  - Use `timeout -s KILL` for samplers like `nvidia-smi -lms`.
  - Use `cleanmask` or `systemd-run` for long-lived programs.
  - The scripts clear the mask themselves.
- `pgrep -f Game.exe` also matches gamescope's own command line and Proton's python. Match the
  Wine form (`[A-Z]:\\...Game.exe`) or read `/proc/PID/cmdline`.
- Wine double-forks the game. `game-cores` is a subreaper, so placement still finds it, and it
  forwards TERM/INT/HUP to the whole tree because Proton's script does not relay them.
- Steam rewrites localconfig.vdf on exit, so never edit it with Steam running. `steamtools.py set`
  handles this.
- GE-Proton's `PROTON_DLSS_UPGRADE=1` swaps in the newest DLSS DLLs but keeps the game's default
  preset. Check the indicator before assuming you are on the transformer model.
- Scripted launches need the game's launcher skipped:
  - Nixxes and PlayStation ports take `-nolauncher`.
  - For other games, check PCGamingWiki for the launcher-skip argument.
- `bench.py stop` kills only processes that carry its session's `GAMEPERF_BENCH` environment
  marker, and it refuses while a Steam-launched game runs, because that game would share the
  prefix's wineserver.
  - This matters: Marcus once launched the game through Steam seconds after a bench run ended.
  - A killed Wine game leaves `explorer.exe` and other prefix processes holding VRAM, so make sure `stop` reports nothing left alive.
- `prebake` starts 28 `fossilize_replay` workers when the desk looks idle, which is exactly when a
  bench runs, and they cut fps by 80%. Run `prebake pause --for 3h` before the first `start`; it
  resumes by itself.
- A game the rig starts outside a Steam launch gets its environment from the Steam client, which
  includes `LC_ALL=C`, so Wine cannot resolve non-ASCII paths: Ragnarök failed to open
  `Saved Games\God of War Ragnarök` ("Path not found", then first-run setup with no saves). Real
  Steam launches are fine. For such a game, skip the rig and verify the levers with one real launch.
- Back up the game's own settings and save folders before the first `start` (`cp -a --reflink=auto`
  to `/mnt/nvme8tb/gameperf-backup/`), and diff and restore them afterwards: the rig's SDR display,
  first-run prompts (telemetry, GPU-changed dialogs, gift notices) and autosaves all write there.
- Proton or protonfixes may already set a CPU topology (`WINE_CPU_TOPOLOGY` in `/proc/PID/environ`;
  Uncharted gets `16:0-15`). `PROTON_CPU_TOPOLOGY` loses to protonfixes, set `WINE_CPU_TOPOLOGY`
  to override.
