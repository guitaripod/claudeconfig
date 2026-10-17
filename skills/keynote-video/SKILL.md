---
name: keynote-video
description: Build an Apple-keynote-style launch video for an app (dark background, huge type, slow reveals, real UI as hero shots, cuts locked to a supplied track) with Remotion, headless on Arch, as a 16:9 H.264 MP4 plus a 1:1 cut for X. Use for "launch video", "promo video", "keynote style video", "product film". Not for footage hype edits (hype-edit) or narrated tours.
---

# Keynote launch video

Full reference build: `~/Dev/film/tailscode-launch` (8 scenes: device swap, row of four clients, SVG diagram, square layouts). `template/` is the lean starter: open, title, one device scene with a highlight ring, end card.

## Flow

1. **Research.** Reuse an installed Remotion (`~/Dev/film/*/edit`). Verify devices and price on the live store listing, take copy from shipped store captions, never invent stats or quotes. Run the tooling and repo surveys as parallel agents.
2. **Brief and storyboard.** Fill audience, one-sentence message, 3 to 5 features, end card, colors (app icon SVG) and font (Inter; SF is not redistributable) yourself. Show a table of time, shot, burned-in text, asset. STOP for approval. Text is burned in, no voiceover.
3. **Build and verify** with the commands below. Look at every sheet in 16:9 and 1:1 before trusting numbers.
4. **Deliver** `./launch/video.mp4` and `video-1x1.mp4` relative to the session cwd.

```
S=~/.claude/skills/keynote-video/scripts
bash $S/new-project.sh ~/Dev/film/<name> <icon.svg>
bash $S/frame-devices.sh <proj>/public/framed Silver <masters...>
bash $S/cut-music.sh <track> <start_s> <dur_s> <proj>/audio/music.wav
python3 $S/beat-grid.py <track> <start_s> <dur_s> 140
bash $S/stills.sh <proj> Launch g <frames...>
bash $S/render.sh <proj> <proj>/audio/music.wav <outdir> Launch:video LaunchSquare:video-1x1
bash $S/qa-sheet.sh <outdir>/video.mp4 <sheet.jpg> 3 <seconds...>
python3 $S/check-timing.py <outdir>/video.mp4 <music.wav> <cut frames...>
```

`frame-devices.sh` writes `<name>_framed.png` (rename to what the scene references). `beat-grid.py` prints `BEAT_SECONDS` and `FIRST_BEAT` for `timing.ts`; scenes start at `beatFrame(k)` and reveals use `local(beats)`. `render.sh` type-checks, renders muted at `nproc` concurrency, muxes AAC with `+faststart`, prints ffprobe and LUFS. The untouched template with silent audio renders both cuts in about 2 min: run it first to learn whether the toolchain broke.

## Craft

- Background `#06070B` with two slow-drifting glows, Inter 900, one gradient accent line per shot. Reveals bezier(0.16, 1, 0.3, 1) over about 30 frames, devices rise and push in 1.00 to 1.05, scenes crossfade 14 frames.
- Apple devices go through `frames` only (Silver reads on dark). Desktop screenshots get a plain rounded window (`WindowShot`), never a drawn bezel.
- Every scene needs a 1:1 branch through `useLayout()` (`u = 0.62`).
- Bleed phones off the bottom (height 1120, top 50) so UI is legible in a feed; keep a Lock Screen shot unbled because its notification sits low.
- Cuts land on beats: expect every cut within about 30 ms of the grid. librosa often reports half time on fast tracks; use it as is.

## Lessons

- Static hero shots die after 3 s: add beat-timed `Callout` rings. Read boxes off a 921x2000 view of a 1320x2868 master; the component converts (x 1320/921, bezel offset 75,66 in the 1470x3000 framed PNG).
- Crossfading two devices ghosts them: fade the outgoing one in 12 frames ending on the beat, start the incoming 6 to 8 frames later.
- SVG lines of zero height render nothing with gradients or filters in the default units: use `userSpaceOnUse` for both.
- Contact sheets caught every real bug (clipped 1:1 row, invisible link line, cropped device). `ffmpeg fps=1/3` samples are offset about 1.2 s: use explicit `-ss` (`qa-sheet.sh`) or `remotion still` for exact frames.
- Run these scripts with plain `python3`, not `-I`: librosa lives in user site-packages.
- Music: Marcus usually supplies a track from `/mnt/nvme8tb/Music`; use it and say once that X may mute a commercial recording. Scripted no-attribution sources are scarce: Freesound CC0 only (check each licence page); Pixabay bars scripted download; Incompetech needs attribution.
- App repos' own marketing docs go stale (Tailscode's `LAUNCH.md` said Mac and iPad were not on the store): trust the README and the live listing.
- X allows 512 MB and 140 s; a 54 s CRF 16 render is about 22 MB.
