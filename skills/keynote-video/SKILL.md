---
name: keynote-video
description: Build an Apple-keynote-style launch video for an app (dark background, huge type, slow reveals, real UI as hero shots, beat-locked cuts to a supplied track) with Remotion, rendered headless on Arch to a 16:9 H.264 MP4 plus a 1:1 cut for X. Use for "launch video", "promo video for X", "keynote style video", "product film for the app". Not for hype edits from footage (hype-edit) or narrated tours.
---

# Keynote launch video

Working example: `~/Dev/film/tailscode-launch` (Tailscode launch, 54 s, 2026-10-17). `template/` here is a copy of its `src/` and `package.json`; `scenes.tsx` is the brand-specific part to rewrite, everything else is reusable.

## Flow

1. **Research, don't assume.** Check `~/Dev/film/*/edit/package.json` first: Remotion with chrome-headless-shell is already installed on this box. Verify any store claim (devices, price) on the live listing, and take copy from shipped store captions (`marketing/captions/en-US.json` in app repos). Never invent stats or quotes. Parallelise: one agent for tooling facts, one for the repo survey, while you read brand assets.
2. **Fill the brief yourself** (audience, one-sentence message, 3 to 5 features, end card, brand colors from the app icon SVG, font) and show it with the storyboard. Marcus decides; do not interrogate him.
3. **Storyboard table** (time, shot, burned-in text, asset), then STOP for approval. Burned-in text only, no voiceover.
4. **Build**: copy `template/` to `~/Dev/film/<name>/`, `pnpm install`, frame the devices, cut the music, derive the beat grid, write scenes, QA, render.
5. **Verify** with real frames and numbers (below), iterate until clean.
6. **Deliver** `./launch/video.mp4` and `./launch/video-1x1.mp4` (relative to the session cwd).

## Commands

```
S=~/.claude/skills/keynote-video/scripts
bash $S/frame-devices.sh <out> Silver shot1.png shot2.png
bash $S/cut-music.sh <track> <start_s> <dur_s> <audio/music.wav>
python3 $S/beat-grid.py <track> <start_s> <dur_s> 140
bash $S/stills.sh <project> Launch g 360 469 618
bash $S/render.sh <project> <project>/audio/music.wav <outdir> Launch:video LaunchSquare:video-1x1
python3 $S/check-timing.py <outdir>/video.mp4 <project>/audio/music.wav <cut frames...>
```

`render.sh` takes `CompositionId:outputName` pairs, renders muted (concurrency = nproc, 54 s in about 35 s), muxes AAC 192k with `+faststart`, then prints ffprobe and integrated loudness.

## Look

- Background `#06070B` with two slow-drifting radial glows (brand blue, violet). Inter 900 for headlines (`@remotion/google-fonts/Inter`; SF is not redistributable on Linux), brand gradient on the one accent line per shot.
- Reveals: bezier(0.16, 1, 0.3, 1), about 30 frames, rise 34 px, blur 14 to 0. Devices rise and push in 1.00 to 1.05 over the shot. Crossfade scenes 14 frames.
- Apple devices are framed with the `frames` CLI only (Silver bezel reads against a dark background; `frames --json info` shows the match). Linux gets a plain rounded window with a hairline border and shadow, never a drawn bezel.
- Text sizes shrink by `u = 0.62` for 1:1 through `useLayout()`; every scene needs a square branch.

## Beat lock

`timing.ts` holds `BEAT_SECONDS` and `FIRST_BEAT` from `beat-grid.py`; scene starts are `beatFrame(k)` and in-scene reveals are `local(beats)`. `beat-grid.py` reports the first beat modulo the period, so an excerpt that starts mid-beat is still right. librosa reports half time on fast tracks; use it as is. `check-timing.py` should show every cut within about 30 ms of a beat.

## Lessons learned

- Static hero shots die after 3 s. Beat-timed highlight rings (`Callout`) on the real UI keep 8 s shots alive. Read target boxes off a 921x2000 view of the 1320x2868 master and convert: units x 1320/921, plus bezel offset (75, 66) in the framed PNG, scaled by device height / 3000 (iPhone 18 Pro Max frame is 1470x3000).
- Bleed phones off the bottom edge (height 1120 at top 50 on a 1080 frame) so UI text is legible in a feed; keep the Lock Screen shot unbled because its notification sits low.
- SVG gotchas: gradients and filters on a zero-height line render nothing with the default objectBoundingBox units. Use `gradientUnits="userSpaceOnUse"` and `filterUnits="userSpaceOnUse"`.
- Crossfading two devices ghosts them. Fade the outgoing one in 12 frames ending on the beat and start the incoming one 6 to 8 frames later.
- `ffmpeg -vf fps=1/3` samples are offset by about 1.2 s. For QA use explicit `-ss` lists, and `remotion still` for exact frames (first still bundles in about 14 s, later ones reuse the cache; run 5 in parallel with `xargs -P5`).
- Viewing contact sheets caught every real bug here (missing link line, device cropped at top, row overflowing in 1:1, ghosted crossfade). Always look at 1:1 as well as 16:9.
- Use the typographic apostrophe in burned-in text. Name all agents a product supports where any is named.
- `python3 -I` hides user-site packages, so librosa is missing under it; these scripts read your own files, so run them plainly.
- pnpm prints an esbuild ignored-build warning; Remotion works anyway.
- Keep `npx tsc --noEmit` green before every render; unused-variable diagnostics mean dead code was left behind.
- Music: scripted no-attribution sources are scarce. Freesound CC0 is the only one verified (check each track's licence page); the Pixabay licence forbids scripted bulk download; Incompetech needs attribution. Marcus often supplies a commercial track from `/mnt/nvme8tb/Music`: use it, state once that X may mute or flag it, and do not argue.
- X limits: 512 MB, 140 s. A 54 s 1080p CRF 16 render is about 22 MB, so size is never the constraint.
- Check app repos' own marketing docs for stale "claims fence" lines (Tailscode's `LAUNCH.md` still said Mac and iPad were not on the store); trust the README and the live listing.
