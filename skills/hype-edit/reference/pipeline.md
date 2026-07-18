# hype-edit — pipeline reference

## Data flow

```
song ──extract_audio.py──► song_22k_mono.wav (analysis)  master.wav (mux)  project.json
                                     │
src/*.mp4 ──scenes.py──► scenes.json (clips) + motion.npz (per-source motion @10fps)
                                     │
          ──colorscan.py──► scenes.json (+green/graphic flags) + badframes.npz (@5fps)
                                     │
song analysis ──build_spine.py──► spine.json (beats, sections, drops, cutlist, heroes)
                                     │
spine + scenes + motion + badframes ──assign_clips.py──► assign.json (segment→clip+in_tc+effects)
                                     │
          ──render.py──► seg/seg_###.mp4 → work/video.mp4 → out/edit.mp4
                                     │
          ──qc.py / contact_sheet.py──► gates + visual proof
```

Every stage is idempotent and reads `project.json`. Re-run any stage after editing inputs.

## project.json schema

```jsonc
{
  "root": "/abs/workdir",
  "style": "classic",           // or "remaster" — set by extract_audio.py --style; drives
                                // cadence (build_spine), speed/effects/framing (assign_clips),
                                // rotation+interpolation (render), tile rotation (contact_sheet)
  "fps": 30, "out_w": 1920, "out_h": 1080,
  "dur": 174.0,                 // frame-aligned, silence-trimmed (set by extract_audio.py)
  "total_frames": 5220,         // dur*fps — the invariant render/qc enforce
  "sr_analysis": 22050,
  "audio_analysis": "song_22k_mono.wav",
  "audio_master": "master.wav",
  "grade": "eq=...,colorbalance=...,curves=...,vignette=...",   // ffmpeg filter chain
  "catalog": { "<srcid>": ["Nice Label", "hero_goal|goal|skills"] },   // optional
  "hero_overrides": [ {"src":"<srcid>", "in_tc": 96.7, "impact": 0.7}, ... ]  // optional
}
```

## Timeline math (why it's frame-exact)

- `dur = floor(song_dur * fps) / fps` after trimming trailing silence → integer `total_frames`.
- Analysis WAV: exactly `round(dur*22050)` samples; master: exactly `round(dur*44100)`. Enforced with `atrim=end_sample=N,apad=whole_len=N` (float `-t` is not sample-exact).
- Each segment's frame count `nf = round(end*fps) - round(start*fps)`. Because `start[k+1]==end[k]`, the sum telescopes to `round(dur*fps) == total_frames`. So cut points land on exact frames and there's no rounding drift.
- Audio is muxed once over the concatenated silent video → drift is structurally impossible.

## build_spine.py knobs

- Tempo band folding: `(90,180)` BPM via tempogram salience. For very slow/fast genres widen the fold set / band.
- `sig = 1.5 * FPS` — structural smoothing so periodic kicks don't fragment sections. Raise for busier tracks.
- Section thresholds: `peak >0.62`, `low <0.33` (hysteresis on the normalized energy `E`).
- Drop detection: sustained forward energy jump on downbeats (`after>0.5`, `jump>0.28`), 8 s non-max-suppression.
- Cadence by tag (classic): `low`=8 beats/cut, `build`=4→2→1 ramp, `peak`=2 beats, `drop`=1 beat (`1,1,1,2` for breath), half-beat machine-gun in a ±1.5-beat window before heroes.
- Cadence (remaster): `low`=8, `build`=4→4→2, `peak`=2, `drop`=2 (`2,2,2,4` for breath), no machine-gun window, first cut floored at 2.2 s (the genre's opening hold).
- Heroes: main drop + strongest peak/drop downbeat per zone (`nz = max(3, dur/25)`), ≥6 s apart. Primary (nearest main drop) gets 3 beats + freeze-frame; others 2 beats. Remaster: 4/3 beats, no freeze.

## assign_clips.py knobs

- `usable` filter: not dark, `green≤0.25`, not `graphic`, `motion_max≥0.045`. Raise the motion floor to be stricter about "every frame good"; lower if the pool is thin.
- Pools: `hero` (by motion_max, dur≥0.9), `high` (peak/drop, by motion), `mid` (build, near median), `low` (lulls, calmest). All drawn **fresh-first** → zero reuse from a deep pool.
- `avoid_src` (last 3 sources) spreads consecutive cuts across sources — that's the diversity lever.
- In-point: highest-motion window whose bad-frame fraction is ~0 (graphic-aware); `nth` picks a different window if a clip is ever reused. `impact` = motion peak within the window (drives freeze/flash timing).
- `hero_overrides` (in hero-time order) bypass the pool for hand-picked marquee moments — the reliable way to guarantee a specific shot lands on a specific hit (e.g. a known goal at a known timestamp). Find timestamps by browsing a source with a labeled frame strip, then set `{src,in_tc,impact}`.

## remaster style (full-bleed rotated "4K quality edit")

- Geometry: `transpose=1` (90° clockwise — source bottom edge lands on the portrait LEFT edge, matching the genre reference) then scale-increase + center-crop to out_w×out_h. A 1920×1080 source maps 1:1 onto 1080×1920 with zero pixels lost. Letterbox `scrop` still applies BEFORE the transpose (bars would otherwise run down the sides).
- Assigner: no vertical crop framing; per-segment `"speed"` (hero 0.5, drop/peak 0.65, build 0.75, low 0.85); source in-point windows and clip-length checks use `dur*speed` (real footage consumed).
- Renderer interpolation (full render): **RIFE optical flow** when `rife-ncnn-vulkan` is on PATH (`~/.local/opt/rife-ncnn-vulkan-*/`, model `rife-v4.6` auto-resolved next to the real binary; `HYPE_RIFE_BIN`/`HYPE_RIFE_MODEL` override, `HYPE_NO_RIFE=1` disables). Per segment: graded frames extracted at source fps (same fast-seek `-ss`, so pinned in_tcs hold) → `rife -n nf` retimes slow-mo + 60fps synthesis in one uniform resample (frame-exact by construction) → output-timeline zoom/flash + encode. Two RIFE processes max at a time (VRAM); any failure falls back per-segment to the legacy `setpts=PTS/speed` + `minterpolate` chain — the render never breaks on a missing binary. RIFE beats minterpolate exactly where it hurts: fast-moving objects tear/ghost under block-matching, stay coherent under optical flow. Drafts use plain `fps=` (interpolation only checks direction there).
- Encoder bumped for the detail-porn look: nvenc cq17 maxrate 90M (libx264 crf16). Uploading fat bitrate is the point — platform re-encodes eat sharpening first.
- `render.py --landscape` (remaster only, mandatory deliverable): same assign/spine on a swapped 1920×1080 canvas without the transpose → `out/edit_landscape.mp4`, segments in `seg_ls/`. qc.py gates the portrait master; the landscape render's Σframes printout is its check.
- contact_sheet auto-prepends `transpose=2` so review tiles read upright; grade lives in project.json like any style (`extract_audio.py` seeds the remaster preset: hqdn3d → unsharp → cas → eq/vibrance → curves).
- Re-running `extract_audio.py` with a different `--style` resets `grade` to the new style's preset; same style preserves a hand-tuned grade.

## render.py knobs

- Encoder auto-detected: `h264_nvenc` (preset p6, cq20) if present, else `libx264` (medium, crf18). Draft uses half-res + p1/veryfast.
- `-frames:v nf` guarantees exact output length regardless of effect frame changes (freeze adds frames via `tpad=clone`, then trims).
- Effects reference `DUR=seg.dur` and `F=impact`. `setpts=PTS-STARTPTS` after the grade so `t` starts at 0 for effect expressions.
- Grade override: set `project.json.grade` to any ffmpeg filter chain (it's appended after the fill/scale). Keep it a comma-joined chain with no leading/trailing comma.

## colorscan.py knobs (per-domain tuning)

- Promo card: bright saturated green `g>140 & g>1.55r & g>1.55b`.
- Grass pitch: `50<g<205 & g>1.08r & g>1.12b`.
- Per-frame graphic (bad): little pitch (`<0.10`) AND (flat `detail<20` OR oversaturated `sat>0.5` OR big bright graphic `bright>0.20`), or a promo card. Clip flagged `graphic` if >45% of its frames are bad; the per-frame mask (`badframes.npz`) steers in-points.
- For non-sports domains (anime, gaming, cinema), the "pitch" heuristic won't apply — replace it with a domain cue (dominant scene color, edge density) or disable graphic exclusion and rely on the motion floor + manual source curation.

## Effect ffmpeg recipes

- Punch zoom: `scale=w='OW*(1+a*min(t,DUR)/DUR)':...:eval=frame,crop=OW:OH:(in_w-OW)/2:(in_h-OH)/2`.
- Shake: `scale=SW:SH,crop=OW:OH:x='(in_w-OW)/2+A*sin(2*PI*11*t)*exp(-t/tau)':y='...cos(2*PI*13*t)...'` — **no `eval=` on crop**.
- Beat/drop flash: `eq=brightness='if(lt(t,h),b,if(lt(t,h+f),b*(1-(t-h)/f),0))':eval=frame`.
- Freeze: `trim=0:F,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=...` then zoom + flash over the held frame.
- RGB split: `rgbashift=rh=4:bh=-4` (static per short cut reads as a pulse; rgbashift has no per-frame expr).

## Resume / recover

- Corrupt sources: `for f in src/*.mp4; do ffmpeg -v error -i "$f" -map 0:v:0 -f null - 2>&1 | grep -icE 'NAL|error'; done` → re-`fetch.sh` any nonzero.
- Mismatched frames after render: a segment's `nf` didn't materialize (usually a bad effect string forcing CPU fallback that still under-produced) — check `render.py`'s fallback list, fix the filter, re-run (only changed segments re-encode if you delete just those `seg_###.mp4`).
- Two agents in one workdir: `ps -eo pid,cmd | grep 'claude -p'` — kill the stale one before it clobbers scripts/state.
