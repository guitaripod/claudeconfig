---
name: video-edit
description: Edit video from footage with a resumable, frame-exact pipeline — ingest clips, scan them, build a cut timeline, assign shots, render and QC. Use for any "make / cut / edit a video" request that does not name another skill: assembling footage, cutting to a song, applying effects, producing a reviewable draft. Pacing, effects, canvas, gates and delivery come from the chosen preset, never from this skill. Not for launch films (keynote-video), screen-recording comparisons (video-comparison), series concatenation (show-concat), or loudness-only passes (video-loud).
---

# Video Edit — footage → cut, by preset

Deterministic and resumable: every stage reads `project.json`, writes one file, and can be re-run. `timeline.json` is the contract between the producer and everything downstream, so an edit driven by a song and one driven by scene detection run the same assign → render → QC → review path.

**Direct the edit, don't inherit a genre.** The preset *is* the direction: pacing, effects, canvas, gates, delivery. There is no default.

## 1. Pick the preset — the only real decision

| preset | for | shape |
|---|---|---|
| `hype` | beat-locked montage, fast cuts, dense effects | 1920×1080@30, cut to the song |
| `hype-quality` | the genre's slow-mo variant | 1080×1920@60, RIFE retime, rotated |
| `calm` | footage-led assembly, long holds, no effects | 1920×1080@30, no beat lock |

Read `presets/<name>.json` before starting; it is the direction, not a suggestion. If the brief does not imply one, state the preset you are using and why in one line ("footage-led, no beat lock → calm"), then proceed — don't stall on a style interview.

## 2. Set up

```bash
S=~/.claude/skills/video-edit/scripts
bash $S/setup.sh <workdir>            # tree + python; prints PY=<workdir>/py
PY=<workdir>/py                       # use this for scripts that import numpy/librosa
```

`setup.sh` reuses the system python when it already has the deps, so repeat edits cost nothing. Workdir on a fast disk with tens of GB free; **never `/tmp`** if it is RAM-backed.

## 3. Start the project

With music — the duration comes from the track:

```bash
$PY $S/extract_audio.py <workdir> "<song file or URL>" --preset hype [--start 12 --end 45] [--pitch 1.04]
```

Without music — duration is explicit:

```bash
$PY $S/init.py <workdir> --preset calm --duration 90
```

`--pitch 1.04` shifts pitch +4% with tempo preserved (Content-ID dodge for social); ±3–5% is enough.

## 4. Ingest

```bash
bash $S/ingest.sh <workdir> <file|dir|youtube-id|url> ...
```

Local paths, directories and YouTube sources all land in `src/` and are decode-validated. Downloads are sequential by design. Prefer official/high-bitrate sources; over-collect for diversity. Trap sources that pass every automated filter: sim gameplay (EA FC/PES), fan comps with end-cards mid-file, combo/HUD/QTE overlays, burned-in subtitles, menus and typography. Details and the audit procedure: `reference/ingest.md`.

## 5. Scan

```bash
$PY $S/scenes.py <workdir>        # single-action clips + motion timelines
$PY $S/colorscan.py <workdir>     # promo cards / synthetic graphics → badframes
```

`colorscan.py` uses the preset's domain profile (`scan.profile`): sports keys off pitch and broadcast cards, generic only rejects flat bright cards, screen keeps interfaces. Override with `project.json "domain"`.

## 6. Build the timeline

One producer, depending on where the structure comes from:

```bash
$PY $S/beat_spine.py <workdir>       # song: tempo, sections, drops, cutlist, heroes
$PY $S/scene_timeline.py <workdir>   # footage: shot list at the preset's shot lengths
```

Read the printout. Beat producer: BPM, `cv`≈0 (uniform grid), drop time, hero placement, and the density gradient (drops densest). Shots producer: mean/min/max shot length. `timeline.json` tiles the whole duration with no gaps — `timeline.check` enforces it.

## 7. Assign, draft, review

```bash
$PY $S/assign_clips.py <workdir>                     # clip per cut, effect plan, framing
python3 $S/render.py <workdir> --draft               # cheap direction check
python3 $S/contact_sheet.py <workdir> --draft --n 40 # READ frames/contact.png
python3 $S/contact_sheet.py <workdir> --segs         # READ frames/seggrid.png
```

The segment grid is the precision tool: every defect maps to a segment index → `assign.json segments[i].clip_id` → append the id to `project.json "exclude_clips"` → re-run assign + draft. Loop until the grid is clean. Direct `assign.json` hand-patches do not survive an assign re-run; `exclude_clips` and `hero_overrides` do. Full procedure: `reference/review.md`.

## 8. Render and QC

```bash
python3 $S/render.py <workdir>
python3 $S/qc.py <workdir>
```

QC enforces only what the preset declares (`gates`): structural checks always; beat alignment only when the timeline has beats and the preset asks for it; density only when the preset claims it; exposure threshold from the preset. Green means the edit matches its own direction, not a house standard.

## 9. Deliver

`deliver` in the preset says what ship means. `tiktok` (hype): rotated tall-fill vertical + Taildrop + caption — see the `hype-edit` skill. `master`: hand over `out/edit.mp4`.

## Several edits at once

- **One workdir per edit, one agent per workdir** — never share.
- **Share the source pool:** ingest once, then per extra workdir symlink `src/*` and copy `scenes.json motion.npz badframes.npz` (source-derived; skip scenes/colorscan there).
- **Zero cross-edit clip overlap:** collect every `clip_id` from finished edits' `assign.json` and append to the next edit's `exclude_clips`. Distinct edits sharing the same viral moment read as reposts.
- Different songs/sections per edit: re-run the producer per workdir; the timeline is per-edit state.

## Adding direction

- **New preset:** copy `presets/hype.json`, change pacing/canvas/effects/gates/deliver, name it in `project.json`. No code change.
- **New effects feel:** add a function to `scripts/effect_plans.py` and name it in `preset.effects.plan`.
- **New timeline producer:** write `timeline.json` in the same shape (see `reference/timeline.md`), call `timeline.check`, and every later stage works unchanged.

## Files

`scripts/`: `setup.sh` `init.py` `extract_audio.py` `ingest.sh` `scenes.py` `colorscan.py` `beat_spine.py` `scene_timeline.py` `assign_clips.py` `render.py` `look.py` `qc.py` `contact_sheet.py` `preset.py` `timeline.py` `effect_plans.py` `restore.py` (optional restoration) `narrate.py` (voice-over; see `video-narration`) `ask.py` (send-only phone reach). `presets/`: direction files. `reference/`: `timeline.md` (schemas + math), `ingest.md`, `ffmpeg.md`, `review.md`.
