---
description: Concatenate every episode of a TV show into a single mkv with intros/outros stripped. Use when the user asks to "make one video of the whole show", binge-watch a series as a single file, or remove all intro/outro music across a season/series. Handles mixed NTSC/PAL sources, multi-part super-sized episodes, and works across encoders.
---

# Show → Single MKV

End-to-end pipeline for turning a TV show's episode files into one continuous mkv with theme-song intros and end-credit outros removed. Designed for the cases that defeat naive ffmpeg recipes: mixed framerates, mastering drift across seasons, multi-part DVD rips, long cold opens.

## When to use

User says some variant of:
- "Make me one video file of every episode of <show>"
- "Cut out the intros and outros and concat the whole series"
- "Binge file with no theme music between episodes"

If the request is just "trim the intro of this one episode", that's a single-file edit — don't pull in this skill.

## The hard parts (and how this skill handles them)

A full series is not a single ffmpeg invocation. The traps:

1. **Mixed source formats.** Long-running shows often have NTSC (23.976 fps) early seasons and PAL (25 fps) later seasons (or vice versa). Lossless `-c copy` concat across mismatched fps causes silent A/V drift that you only notice 30 episodes in.
2. **Cold open length is wildly variable.** Theme can land anywhere from 0s to >300s into an episode. A 300s search window misses outliers. Use ≥600s.
3. **Audio mastering drifts across seasons.** Cross-correlation against a single reference scores ~0.99 on its own season but <0.5 on others. You need either per-season references or a visual fallback.
4. **Multi-part episodes (super-sized).** Filenames like `- cd1.mkv`, `- cd2.mkv` are one logical episode split across DVD discs. Only `cd1` has the intro; only the last cd has the outro. Treating each cd independently double-cuts.
5. **ffmpeg traps that waste hours:**
   - Forgetting `-vn` on audio extraction → ffmpeg also decodes video → 5–10× slower.
   - Forgetting `-nostdin` on background ffmpeg → it sits in interactive mode reading nothing forever.
   - Output extension `.mkv.tmp` → ffmpeg can't infer format → fails. Either keep `.mkv` (e.g. `.partial-name.mkv`) or pass `-f matroska`.
   - Multiple ffmpeg jobs on the same HDD → I/O thrashing makes everything slower than serial.

## Workflow

Run these phases in order. Each writes intermediate state to disk, so you can resume after a kill.

### Phase 1 — Inventory & format probe

```bash
find "<show-root>" -type f -name "*.mkv" | wc -l   # episode count
```

Walk every file with `ffprobe` to capture: video codec, resolution, fps, pixel format, audio codec, channels, duration. Look for fps groups (23.976 vs 25) and codec mix (eac3 vs ac3, h264 vs hevc). If you see ≥2 distinct fps values, plan a normalization pass for the minority group (Phase 2). All-uniform = skip Phase 2.

### Phase 2 — Format normalization (PAL ↔ NTSC)

Only needed if fps groups differ. The math is exact, not "approximately 4%":

| from | to | video | audio |
|------|----|-------|-------|
| 25 → 23.976 | NTSC | `setpts=25025/24000*PTS` then `-r 24000/1001` | `atempo=24000/25025` |
| 23.976 → 25 | PAL | `setpts=24000/25025*PTS` then `-r 25` | `atempo=25025/24000` |

`atempo` < 1 slows down (drops pitch). For a show ripped from PAL DVD that was sped up 4% in mastering, slowing back to NTSC restores the original pitch — that's the *correct* direction.

Encoder: NVENC h264 if available (`h264_nvenc -preset p7 -tune hq -rc vbr -cq 19 -maxrate 12M -bufsize 24M`). x264 if not (`libx264 -crf 18 -preset slow`). Audio re-mux to EAC3 5.1 to match the dominant audio codec. See `scripts/pal_to_ntsc.sh` for the canonical invocation. **Always** include `-nostdin` and write to a `.partial-…mkv` file then `mv` on success.

### Phase 3 — Theme detection

Audio cross-correlation against a 30-second theme reference, in mel-spectrogram space (raw PCM xcorr fails across codec re-encodes). See `scripts/find_theme.py`.

**Building the reference:** Pick a known clean episode, find where the theme starts (usually a recognizable iconic shot — Penn Paper for Office, Chevy commercial for Community, etc.), extract that 30s as `theme.wav`:

```bash
ffmpeg -ss <theme_start> -t <theme_dur> -i <ep.mkv> -ac 1 -ar 16000 -vn theme.wav
```

**Search window: 600 seconds.** Some Extended Cut episodes have 5+ minute cold opens. 300s misses them.

**Per-season references.** If audio mastering changed (common between major show eras), build a second reference from a confirmed-correct episode in that era. NTSC ref + PAL ref is typical for shows that ran the boundary.

**Score interpretation:**
- ≥0.95: perfect match (often self-match or same master)
- 0.70–0.95: confident
- 0.55–0.70: probable; offsets usually right, scores low only because mastering differs
- <0.55: suspect; verify visually (Phase 3b)

### Phase 3b — Visual fallback for low-confidence detections

When audio scores stay <0.55 even with the right reference, use frame-template matching against an iconic title-sequence shot. See `scripts/find_pennpaper.py` (rename and replace the reference image for any show).

The technique: extract one frame per second of the first 10 minutes, downscale to 240×135 grayscale, compute MAE against a reference frame of one iconic theme shot, return the offset of the minimum. Office's Penn Paper tower hits similarity ~0.88–0.96 across all 9 seasons regardless of audio mastering.

For each show, capture a frame from the title sequence that:
- Appears at a fixed position in the theme (so `intro_end = match_offset + theme_duration` is consistent)
- Is visually distinctive (avoid plain office interiors, generic exteriors)

### Phase 4 — Outro detection

Scan the last 120s of each file, find the longest black block (≥0.5s, pixel threshold 0.10). That's the scene→credits transition. See `scripts/find_outro.py`. Works for shows with silent credits (early Office) and music credits — the visual cue is consistent.

### Phase 5 — Multi-part handling

Group files by `(season, episode)`. For groups of size > 1:
- First part: cut intro, **don't** cut outro (continues into next part)
- Middle parts: cut neither
- Last part: **don't** cut intro, cut outro

Naming convention to detect: `… - cd1.mkv`, `… - cd2.mkv`. Already implemented in `scripts/detect_all.py`.

### Phase 6 — Cut and concat

For each segment: `ffmpeg -ss <start> -to <end> -i <src> -c copy -map 0:v:0 -map 0:a:0 -avoid_negative_ts make_zero <seg.mkv>`. Keyframe-aligned (±1s tolerance). Lossless.

Then concat: build a list file (`file '/abs/path/seg.mkv'` per line), run `ffmpeg -f concat -safe 0 -i list.txt -c copy out.mkv`.

**Codec compatibility check:** before kicking off concat, verify all segments share `(codec, width, height, fps, pix_fmt)` and audio `(codec, channels, sample_rate)`. Do a small 2-segment test concat first; if it succeeds, the full one will too. If not, you have residual format drift from Phase 2 — fix that, don't `--strict experimental` your way through.

### Phase 7 — Verify

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 out.mkv
```

Compare reported duration to `sum(content_dur)` from the cut plan; should match within 1s per episode boundary (keyframe rounding). Spot-check 5 random points: open at e.g. 10%, 30%, 50%, 70%, 90% of total duration in mpv and confirm content (not theme music, not credits).

## Resource planning

Rough estimates for a 200-episode 1080p show on an HDD source + RTX-class GPU:

| phase | time | output size |
|-------|------|-------------|
| inventory | 5 min | text only |
| format normalize (78 PAL eps via NVENC) | 3–4 hr | ~130 GB |
| audio + visual detection | 1–2 hr | text only |
| cut all segments (-c copy) | 4–6 hr | ~300 GB |
| concat | 6–7 hr (HDD bottleneck) | ~300 GB |
| **total** | **~16–20 hr** | **~600 GB peak** |

Disk: peak usage is ~3× the source (sources + PAL conversions + segments + final). Do this on the largest free volume; `/home` will not fit. The concat itself is the I/O bottleneck — it reads N segments and writes 1 file on the same HDD.

## Failure modes seen in the wild

- **Detection finds the wrong offset on PAL files** → audio cross-correlation locks onto a dialog match instead of a degraded theme. Fix: visual fallback (Phase 3b).
- **ffmpeg sits forever on a single file** at 99% CPU, no output growth → missing `-nostdin`, ffmpeg is blocked reading interactive commands.
- **Concat output has audio sync drift after season N** → Phase 2 was skipped or the speed-correction direction was inverted.
- **Cuts land mid-dialog** → keyframe-only seek with `-c copy`. Acceptable for binge files (off by ≤1s); for frame-accurate, re-encode the leading GOP only.
- **Segments cut fine but concat fails** with codec parameter mismatch → encoder differences (NVENC SPS/PPS ≠ x264). Re-encode the offending group with the dominant encoder, or do a full re-encode pass on concat.

## Reference scripts

All in this skill's `scripts/` directory; copy into a working dir and adapt paths.

- `find_theme.py` — mel-spectrogram-based audio theme finder. Pure numpy, no librosa.
- `find_outro.py` — longest-black-block detector for the credits transition.
- `find_visual.py` — frame-template visual matcher for the audio-fallback case.
- `detect_all.py` — orchestrator that produces a CSV of all cuts.
- `refine_visual.py` — overrides low-confidence audio detections with visual matches.
- `pal_to_ntsc.sh` — NVENC speed-correction encode for PAL→NTSC normalization.
- `cut_concat.py` — cuts segments lossless and concats to single mkv.

The CSV that flows between detection and cutting is the source of truth; review it (and the spot-check frames) before kicking off the multi-hour concat.
