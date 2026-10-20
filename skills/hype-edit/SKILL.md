---
name: hype-edit
description: Produce a beat-synced hype/montage edit from a song plus a subject — "hype edit", "montage", "beat-synced edit", "AMV", "football edit", "highlight reel", "make a video to this song". Runs the video-edit engine with the hype preset: energy-mapped fast cuts, dense beat-locked effects, TikTok vertical delivery. Use hype-rapid for rapid-fire portrait montages and hype-quality for the slow-mo interpolated variant. Not for calm, documentary, product or footage-led edits — those use video-edit's calm preset.
---

# Hype Edit — the preset

This skill is `video-edit` + the `hype` preset. The direction is a file, not prose: `~/.claude/skills/video-edit/presets/hype.json` (pacing steps, effect plan, canvas, gates, delivery). Read it before starting. If the brief wants a different *kind* of video, switch preset — don't bend this one.

```bash
S=~/.claude/skills/video-edit/scripts
bash $S/setup.sh <workdir>                 # prints PY=<workdir>/py
PY=<workdir>/py
$PY $S/extract_audio.py <workdir> "<song or URL>" --preset hype [--start 12 --end 45] [--pitch 1.04]
bash $S/ingest.sh <workdir> <id|file|dir> ...
$PY $S/scenes.py <workdir> && $PY $S/colorscan.py <workdir>
$PY $S/beat_spine.py <workdir>
$PY $S/assign_clips.py <workdir>
python3 $S/render.py <workdir> --draft
python3 $S/contact_sheet.py <workdir> --draft --n 40
python3 $S/contact_sheet.py <workdir> --segs
python3 $S/render.py <workdir> && python3 $S/qc.py <workdir>
```

## Ask

Only about **subject/scope** and **length** — the preset answers style, format and delivery. If the brief is already clear, don't stall. Surface questions to the phone too: `python3 $S/ask.py "<questions — reply in the terminal>"` (send-only; hypebot runs its own poller). Also useful as a heads-up: `ask.py "rendering, ~5 min"`.

## What great means here

- **Pacing is the preset's contract.** Energy-mapped cuts on the beat, dense in drops, never a limp stretch; QC's beat gate fails past 2 frames off, target 0.
- **Cadence tracks energy** (8 beats in lulls → 1 in drops) and density peaks in the drops.
- **Best moments on the biggest hits.** Freeze-frame only on the single loudest beat; hero moments spread ~1 per 25s.
- **The hook is the centerpiece.** Window the track so its signature drop lands around the middle, detonate the most iconic moment exactly on its entry, and build visibly toward it.
- **The subject opens the video.** Segments 0–2 must show them unmistakably — face/helmet/name/kit, no establishing wides, no gear-only shots. A flash over a very short seg 0 whites out the face: clear seg 0 to `["punch"]`, or hold the same shot across seg 0–1.
- **Every cut clean.** Dense effects, but rarely >3 at once and never muddy or blown. Hard looks can clip a bright shot to white — soften the look or exclude the shot.
- **Diversity, zero reuse**, consecutive cuts from different sources.
- **The look is chosen with your eyes.** `look.py <wd> preview` renders every look on one real frame; read `frames/looks.png`, then `look.py <wd> set base=… drop=…`. The seeded roll is a prompt, not a decision.

Full review procedure: `video-edit/reference/review.md`.

## Deliver

The preset decides the shape; `deliver.py` builds the file.

```bash
python3 $S/deliver.py <workdir> --name <subject-song-slug>
```

- **`hype`** (landscape master): rotates 90° and scales to the delivery canvas (1080×2340; `2346` matches the iPhone Air exactly). Rotation keeps the whole frame; the tall canvas trims ~9% off the top/bottom. Never a cropped-to-portrait composition, never a letterboxed 9:16.
- **`hype-rapid`** (already portrait): `out/<slug>_vertical.mp4` is the master.
- **`hype-quality`** (already rotated portrait): same, no second rotation.

Then:

1. Taildrop the full-res file: `tailscale file cp out/<slug>_vertical.mp4 iphone-air:` and tell Marcus to accept it.
2. Caption as its own message on the hypebot Telegram bot (`~/.config/hypebot/secrets.env`): a ready-to-paste TikTok caption, hook + hashtags.
3. Keep the master and vertical under `~/Videos/hype/<date>/`. If the phone is offline, send a ~44MB preview (`-b:v 11M`) via Telegram `sendVideo` and say so.

Narrated story version: `video-narration` skill (`narrate.py`), same preset, voice under the OST.
