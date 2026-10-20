# ffmpeg — effects, render knobs, gotchas

## Effect recipes

- **Punch zoom:** `scale=w='OW*(1+a*min(t,DUR)/DUR)':...:eval=frame,crop=OW:OH:(in_w-OW)/2:(in_h-OH)/2`
- **Shake:** `scale=SW:SH,crop=OW:OH:x='(in_w-OW)/2+A*sin(2*PI*11*t)*exp(-t/tau)':y='...cos(2*PI*13*t)...'` — **no `eval=` on crop**
- **Beat/drop flash:** `eq=brightness='if(lt(t,h),b,if(lt(t,h+f),b*(1-(t-h)/f),0))':eval=frame`
- **Freeze:** `trim=0:F,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=...` then zoom + flash over the held frame
- **RGB split:** `rgbashift=rh=4:bh=-4` (static per short cut reads as a pulse; rgbashift has no per-frame expr)
- **Beat-locked in-transition:** segment enters displaced/zoomed/rotated and decays to an exact identity at settle, using only filters that evaluate `t` per-frame (scale with `eval=frame`, crop natively) so NVENC stays on the fast path.

## Render knobs (preset `render`)

- `mode`: `cuts` (segments rendered at normal speed) or `retime` (speed map + interpolation).
- `rotate`: `transpose=1` (90° clockwise) then scale-increase + center-crop to `out_w×out_h`. A 1920×1080 source maps 1:1 onto 1080×1920 with zero pixels lost. Companion `--landscape` render skips the transpose.
- `interpolate`: `rife` uses `rife-ncnn-vulkan` optical flow when the binary is on PATH (`HYPE_RIFE_BIN` / `HYPE_RIFE_MODEL` override, `HYPE_NO_RIFE=1` disables); otherwise `minterpolate`. Any RIFE failure falls back per segment, so the render never breaks on a missing binary. Two RIFE processes max (VRAM).
- `speed`: per-tag retime multipliers (retime mode only).
- `encoder`: `{cq, crf, maxrate, bufsize}`; NVENC `p6` when available, libx264 `medium` otherwise.
- `--draft` is half-res + fast preset; always draft and read the contact sheet before a full render.

Effects are chosen by `effect_plans.py` from `preset.effects.plan`; the plan returns names (`punch`, `beatflash`, `dropflash`, `shake`, `rgbsplit`, `freezeflash`), `render.py` owns the recipes. Intensity overrides: `project.json "flash_gain"`, `"rgb_shift"`.

## Gotchas (hard-won)

1. **`crop` has no `eval=` option** (unlike `scale`/`zoompan`); its x/y already evaluate `t` per-frame. Adding `eval=frame` to a crop makes NVENC fail and silently fall back to CPU, losing effects. Watch the render's fallback count.
2. **`-frames:v nf` guarantees exact output length** regardless of effect frame changes (freeze adds frames via `tpad=clone`, then trims).
3. **`setpts=PTS-STARTPTS` after the grade** so `t` starts at 0 for effect expressions.
4. **Framing is structural, never part of a look.** `render.py` composes `FILL + color_chain(...)`. A per-segment grade used to replace the whole chain including scale/crop, so shot-level coloring silently broke the fill. Keep any ffmpeg chain comma-joined with no leading/trailing comma.
5. **Fast vs accurate seek land on different content** in some downloads, and sources with broken seek indexes can land seconds off. Probe with the renderer's exact shape: `ffmpeg -ss <t> -t <d> -i src.mp4 -frames:v 1`. Never pin an `in_tc` from a probe that used a different seek form.
6. **Sample-exact audio or you drift.** Float `-t` is not sample-exact; use `atrim=end_sample`.
7. **Don't hardcode duration.** It lives in `project.json`; everything reads it.
8. **`-ss` before `-i`** everywhere (fast seek), matching `assign_clips.grab_gray`.

## look.py

Resolution order for a segment: explicit `seg["grade"]` > `look.segments[i]` > `look.sources[src]` > `look.sections[tag]` > `look.base`. `look.tech` is a non-colour prefix that always runs first (denoise/sharpen). `look.drift` adds deterministic per-segment jitter. `look.py preview` renders one real frame through every look into `frames/looks.png` — read that image and choose, don't nudge numbers blind. The library is a vocabulary; any ffmpeg chain is a valid value.

## restore.py (optional, off by default)

SeedVR2 segment restoration. It measurably recovers face/skin/edge detail on compressed sources (~2.9× sharpness on close-ups) but that detail is imperceptible after social re-encode + phone downscale, and it costs ~1hr of exclusive GPU (~10GB VRAM, ~2.7s/frame) per edit. Use only for a rare non-social / large-screen master, after the cut is locked, then re-render + re-run QC.

- Tool root: `/mnt/games-nvme-gen4/tools/seedvr2` (`HYPE_SEEDVR2` overrides).
- Per target segment: extract the render-exact input window (`-ss in_tc -t dur*speed+1.2`) to a crf10 intermediate → restore at native short-side resolution, batch 5, tiled VAE → `src/<id>__srNNN.mp4`, segment repointed (`src=…__srNNN`, `in_tc=0`). `assign.json.presr` is the backup; frame-loss >10% keeps the original.
- It repoints `assign.json` like a hand-patch, so re-running `assign_clips.py` discards it. Failed segments keep their originals; re-runs skip `__sr` segments.
