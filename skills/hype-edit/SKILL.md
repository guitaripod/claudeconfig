---
name: hype-edit
description: Produce a professional, beat-synced hype/montage video from a song plus a described subject. Use when the user drops a track (file or URL) and asks for a "hype edit", "montage", "beat-synced edit", "AMV/football-edit/highlight reel", or "make a video to this song". The agent sources footage, detects the beat/energy structure, builds a frame-exact editing spine, assigns non-repeating clips locked to the beat, applies restrained effects, QCs numerically + visually, and iterates. Not for trimming a single clip or simple concatenation.
---

# Hype Edit — song → beat-synced montage

You are directing an edit, not running a batch job. The music is the boss: you build the video *to* the song, never the reverse. The whole pipeline is deterministic and resumable — every phase writes state to `<workdir>`, so you can re-run any stage. **`project.json` in the workdir is the single source of truth every script reads.**

## When to use

- "Make a hype edit / montage / highlight reel to this song about <X>"
- "Beat-sync these clips" / "AMV of <anime>" / "football edit of <player/tournament>"
- User provides a song (path or YouTube URL) + a subject/style brief.

Not this skill: trimming one clip, plain concatenation, or a slideshow with no beat sync.

## Clarify first (only if genuinely ambiguous)

Ask 2–4 crisp questions, then go. Good ones: **subject/scope** (which player/team/scene, whole thing vs a slice), **length** (full song vs a section — say `--start/--end`), **look** (default is a punchy teal-orange stadium-night grade; offer alternatives), **output** (default 1920×1080/30/16:9), and **delivery** (file, or send somewhere). If the brief is already clear, don't stall — act.

## Prerequisites

`ffmpeg`/`ffprobe`, `yt-dlp`, `python3`. GPU NVENC is auto-detected and used if present; otherwise it falls back to libx264 (slower, identical result). Put the workdir on a fast disk with plenty of free space (footage + intermediates run tens of GB). **Never use `/tmp`** if it's RAM-backed.

```bash
S=~/.claude/skills/hype-edit/scripts
bash $S/setup.sh <workdir>          # venv + tree + deps; prints which encoder you'll use
PY=<workdir>/.venv/bin/python       # use THIS python for build_spine.py, scenes.py, extract_audio.py
```

## The bar (what "great" means — enforce all of these)

- **Every cut lands on a beat** (≤2 frames). Verified numerically by `qc.py` (target: 0-frame offset).
- **Cadence tracks energy**: long held shots in the lulls (2–3 s), machine-gun cuts in the drops (~0.4 s). Density must be highest in the drops.
- **Best moments on the biggest hits.** Reserve the freeze-frame for the single loudest beat; spread hero moments across the song (~1 per 25 s).
- **Every frame earns its place.** No black frames, no broadcast wipes, no sponsor/score bumpers, no static graphics, no near-duplicates.
- **Diversity + zero reuse.** With a deep pool, no clip repeats and consecutive cuts come from different sources.
- **Restraint reads as quality.** Effects punctuate; they don't smother. Never stack >2–3 on a cut.
- **Zero A/V drift.** One continuous master audio muxed last; sum of segment frames == `total_frames`.

## Workflow

### Phase 0 — Audio is the boss

```bash
$PY $S/extract_audio.py <workdir> "<song file or URL>" [--start S --end E] [--w 1920 --h 1080 --fps 30]
$PY $S/build_spine.py <workdir>
```

`extract_audio.py` downloads/extracts the song, **trims trailing silence**, frame-aligns the timeline, writes **sample-exact** analysis (22.05k mono) + master (44.1k stereo) WAVs, and seeds `project.json`. `build_spine.py` runs octave-corrected tempo detection, a **phase-locked uniform beat grid** (metronomic — no per-beat jitter), an energy curve, drop detection, sections, and a `cutlist` tiled 0→dur on the beat grid with hero slots. Read its printout: BPM/`cv` (want `cv`≈0), drop time, hero placement, and the density gradient (drops should have the most cuts). If tempo looks octave-wrong, that's the thing to fix here.

### Phase 1 — Source the footage (you drive this)

Sourcing is judgment, not a script. Do a **metadata sweep** across several query angles, prefer **official / high-bitrate 1080p** uploads over fan re-ups (they survive Content-ID and aren't watermarked), and over-collect for diversity:

```bash
yt-dlp --flat-playlist --dump-json "ytsearch12:<angle>" | \
  python3 -c "import sys,json;[print(d.get('id'),d.get('duration'),d.get('title','')[:70]) for d in map(json.loads,sys.stdin) if d.get('id')]"
```

Pick sources on-subject and high-action (goals/skills/celebrations/moments — not talk-shows, previews, training, or club footage when the brief says a specific tournament). Then download **robustly** (sequential — parallel yt-dlp on the same file corrupts it):

```bash
bash $S/fetch.sh <workdir> <id1> <id2> ...     # validates each by decoding; retries corrupt ones
$PY  $S/scenes.py    <workdir>                  # slice into single-action clips + motion timelines
python3 $S/colorscan.py <workdir>              # flag promo cards + synthetic graphics
```

**Audit the sources before trusting them.** Build a per-source frame montage (`contact_sheet.py` logic, or `ffmpeg -ss <t> -i src/<id>.mp4 -frames:v 1`) and eyeball kits/scoreboards. Comps titled "Best of <player> <year>" are often *club* footage, not the event you asked for — drop off-subject sources. This one check saves an entire wasted render.

### Phase 2/3 — Assign + render

```bash
$PY $S/assign_clips.py <workdir>            # zero reuse, diversity, quality floor, graphic-aware in-points
python3 $S/render.py   <workdir> --draft    # fast 540p pass to inspect the DIRECTION cheaply
python3 $S/contact_sheet.py <workdir> --draft --n 40   # then READ frames/contact.png as an image
```

`assign_clips.py` maps a distinct, on-energy clip to every segment, picks each in-point on a **motivated, graphic-free** high-motion window, and writes an effect plan. **Always draft-render + read the contact sheet before the full render** — this is where you catch off-subject footage, leaked graphics, and weak frames for pennies. Fix (drop sources, tighten `colorscan.py` thresholds, raise the motion floor, hand-pick heroes) and re-run. Only then:

```bash
python3 $S/render.py <workdir>              # full-res NVENC/libx264 render → out/edit.mp4
python3 $S/qc.py     <workdir>             # numeric gates — must be ALL GATES PASS
python3 $S/contact_sheet.py <workdir> --n 48   # full-res visual pass
```

### Phase 4 — Iterate (at least twice; this is what makes it hype)

Between passes, actually inspect. `qc.py` must be green (frames, format, zero A/V drift, no black/unexpected-freeze, 0-frame beat offset, density-in-drops). Then read the contact sheet: any bumper/wipe/dupe/weak frame is a defect → fix and re-render. Verify heroes landed on the real subject at full res (`ffmpeg -ss <hero_time> -i out/edit.mp4 -frames:v 1`).

### Phase 5 — Deliver

Write `out/director_note.md` (choices + what you fixed between passes). Deliver as asked — e.g. Taildrop to a phone: `tailscale file cp out/edit.mp4 <device>:` (check `tailscale status` for an online device first).

## Effect catalog (restraint > quantity)

Baked per-segment by `assign_clips.py`/`render.py`, keyed to energy: **punch-in zoom** (driving beats), **beat-flash** (white hit on downbeats), **drop-flash** (bigger flash on drop entries), **camera shake** (decaying, on key hits), **RGB split** (chromatic aberration on the hardest), **freeze-frame + zoom + flash + shake** (reserved for the single biggest moment). Tune intensity in `render.py`; tune *when they fire* in `assign_clips.py`. To hand-pick hero moments, set `project.json` `hero_overrides` (see `reference/pipeline.md`).

## Anti-patterns (do not ship)

Metronomic cuts that ignore energy · every effect on every cut · black/frozen frames · audio drift by the end · a clip repeated too soon · the best moment anywhere but a peak · off-subject or club footage in a tournament edit · broadcast wipes/bumpers/score-graphics left in · declaring done without reading the render.

## The hard parts (hard-won — read `reference/pipeline.md` for detail)

1. **Sample-exact audio or you drift.** Float `-t` isn't sample-exact; `extract_audio.py` uses `atrim=end_sample`. All timing is frame-derived; segments carry an exact `nf` that telescopes to `total_frames`.
2. **Corrupt downloads are silent.** Parallel yt-dlp on one output, or two agents in one dir, race and corrupt files whose headers still probe fine. `fetch.sh` is sequential and decode-validates. If footage looks broken, decode-test every source (`ffmpeg -v error -i f -f null -`).
3. **Graphics masquerade as action.** Sponsor bumpers/score-numbers/wipes have high motion and pass a motion filter. `colorscan.py` flags them per-clip AND per-frame; the assigner steers in-points off graphic frames. Thresholds are tuned for sports — re-tune for other domains.
4. **Grass is green, so are promo cards.** The promo-card detector needs bright+saturated green, not just green, or it eats the pitch.
5. **`crop` has no `eval=` option** (unlike `scale`/`zoompan`); its x/y already evaluate `t` per-frame. Adding `eval=frame` to a crop makes NVENC fail and silently fall back to CPU (losing effects). Watch the render's fallback count.
6. **Don't hardcode duration.** It's derived from the (silence-trimmed) audio and lives in `project.json`; everything reads it.
7. **One workdir, one agent.** If two agent runs share a workdir they clobber each other's scripts/state — check `ps` for a stale run before diagnosing "impossible" mismatches.

## Files

`scripts/`: `setup.sh` `extract_audio.py` `fetch.sh` `build_spine.py` `scenes.py` `colorscan.py` `assign_clips.py` `render.py` `qc.py` `contact_sheet.py`. `reference/pipeline.md`: data-flow, `project.json` schema, tuning knobs, hero overrides, ffmpeg recipe details.
