---
name: video-loud
description: Boost a video's audio to maximum loudness without clipping — peak normalization ("as loud as possible before it clips") or EBU R128 loudness leveling ("peak at every moment", "make the quiet parts loud too"). Use when the user asks to make a video's audio louder, normalize its loudness, or max it out. Video stream is copied untouched; audio is re-encoded to AAC.
---

# Video Loud — max loudness without clipping

Single-purpose pipeline: measure the audio's true peak and integrated loudness, boost, re-encode with a correction loop so the encoded file actually lands under the ceiling, and verify.

## When to use

- "Boost the volume as much as possible before it clips" → `--mode peak`
- "Peak at every moment", "make the quiet parts loud too", "keep it loud and consistent" → `--mode loud`

Not this: audio repair (de-click, denoise), resampling, or changing the mix.

## Run it

```bash
~/.claude/skills/video-loud/scripts/loud.sh <input.mp4> [--mode peak|loud] [--target -9] [--tp -1.0] [--out path]
```

- **peak** (default): one transparent gain to 0 dBTP + brick-wall limiter. Dynamics preserved. Use this for trailers, clips, and anything the user just wants louder.
- **loud**: two-pass dynamic loudnorm to `-9 LUFS` (loud consumer target; use `--target -14` for the streaming standard) at `-1.0 dBTP`, then limiter. Compresses the quiet parts up. Use this when the user wants loud *everywhere*.
- Default output: `<stem> - loud<ext>`, auto-suffixed `- loud-2` etc. on collision. Pass `--out` to control the name.
- Printout includes before/after LUFS + true-peak — report those numbers to the user, not just "done".

**Always run on the original file, never on a prior `- loud` output** — a second pass stacks another AAC generation and eats dynamics. If the user iterates on taste ("louder", "too squashed"), re-run from the original with different flags.

## Why the correction loop (pitfalls found the hard way)

1. **AAC adds inter-sample peak overshoot.** The encoder pushes true peaks 0.4–1.2 dB above the sample peak, and the amount varies with the material. A single "measure source, apply gain" pass silently overshoots the ceiling. The script re-measures the *encoded* file and subtracts whatever it landed over by (max 3 iterations, each re-encoding from the original — cheap, video is stream-copied).
2. **Corrections must sit after loudnorm.** loudnorm re-normalizes to its target, so any gain applied *before* it gets cancelled. The correction `volume=` filter is appended after the loudnorm/limiter chain.
3. **loudnorm prints its JSON to stderr** mixed with ffmpeg's log lines. The script extracts the `^{…}^$` block; a naive `jq` over the raw log fails.
4. **FFmpeg ≥7 loudnorm has no `resampling_freq`** — it always processes at 192 kHz internally. The loud chain ends with `aresample=<source rate>` or the output comes out 192 kHz.
5. **loudnorm `I=0` is out of range** (valid -70…-5). The measurement pass uses placeholder values `I=-20:TP=-1:LRA=11` and only reads back the `input_*` fields.
6. **ffprobe `bit_rate` is bits/s, not kbps.** The script floors output AAC at 192 kbps to avoid downgrading a good source.
7. **An already-mastered file can't reach the LUFS target.** If the source already peaks near 0 dBFS (e.g. I=-12, TP≈0), the TP ceiling limits the gain and the result lands short of `--target` (e.g. -13 instead of -9). That's physics, not a bug — the before/after printout shows it, and the user's "loud at every moment" request is satisfied up to the ceiling.
8. Digital clipping is impossible by construction (sample peaks clamped before encoding); the reported true peak guards DAC-level overshoot on playback hardware.
