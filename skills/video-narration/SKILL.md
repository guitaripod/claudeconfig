---
name: video-narration
description: Add a voice-over to a music edit — locate exact iconic lines in source clips, isolate the voice with Demucs, and duck the OST under the speech sample-exactly. Use when the brief is a story told by a voice over the OST ("tell the story of X with X narrating"), not for plain montages or spoken-word-only videos.
---

# Narration — voice over the OST

Runs on the `video-edit` engine. The voice is composited into `master.wav` **under** the OST; the music-only analysis WAV is never touched, so the beat grid is unchanged and cuts stay locked.

The edit's direction still comes from its preset. A narrated hype edit keeps the preset's pacing but lets narration ride the lulls and detonates the hook; a `calm` preset works if the story needs room.

## 1. Install once

```bash
bash ~/.claude/skills/video-edit/scripts/setup.sh <workdir> --narration
# adds asr-venv (torch CPU + Whisper + Demucs, ~2 GB, opt-in)
```

## 2. Source authentic voice

Grab the exact iconic lines from YouTube cutscene / quote clips; do not synthesize. A cloned actor is worse and dubious. `narrate.py` downloads the sources.

## 3. Spec the lines in `project.json`

```json
"narration": { "duck_db": -8.5, "lines": [
  {"src": "<yt-id|url|path>", "phrase": "the exact words to locate", "at": 0.3, "gain": 1.0}
] }
```

`at` is where the phrase **starts** on the timeline. To land a word on a beat, set `at = beat − (that word's onset inside the phrase)` — e.g. detonate "WAR!" exactly on the drop/freeze.

## 4. Compose

```bash
<workdir>/py-narrate ~/.claude/skills/video-edit/scripts/narrate.py <workdir>
```

Per source: download → Whisper word timestamps → locate each phrase by difflib token alignment (tolerant of misheard boundary words) → Demucs `--two-stems=vocals` → slice, highpass, peak-normalise, 28ms fades → place at `at` → build a VO-presence duck gate (dilate + gaussian ramp) → `music × gate + voice` → `master.wav` sample-exact. Everything caches under `narration/`, so re-runs are cheap.

## 5. Validate

Re-transcribe `master.wav` with Whisper: every line must still read over the music. Then render as normal; `render.py` muxes `master.wav`.

## Placement

Identity over the intro, deeds over the build, the signature line on the drop/freeze, resolution over the outro; leave a wide VO gap right before the drop so the hook lands clean.

Heroes in a narrated edit must be clean, high-contrast subjects — a low-motion, dark or subtitled cutscene frame black/freeze-flags in QC and reads as a dead spot.
