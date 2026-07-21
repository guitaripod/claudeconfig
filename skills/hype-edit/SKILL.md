---
name: hype-edit
description: Produce a professional, beat-synced hype/montage video from a song plus a described subject. Use when the user drops a track (file or URL) and asks for a "hype edit", "montage", "beat-synced edit", "AMV/football-edit/highlight reel", or "make a video to this song". The agent sources footage, detects the beat/energy structure, builds a frame-exact editing spine, assigns non-repeating clips to relentless aggressive pacing, applies beat-locked effects, QCs numerically + visually, and iterates. Not for trimming a single clip or simple concatenation.
---

# Hype Edit — song → beat-synced montage

You are directing an edit, not running a batch job. The music is the boss: you build the video *to* the song, never the reverse. The whole pipeline is deterministic and resumable — every phase writes state to `<workdir>`, so you can re-run any stage. **`project.json` in the workdir is the single source of truth every script reads.**

## When to use

- "Make a hype edit / montage / highlight reel to this song about <X>"
- "Beat-sync these clips" / "AMV of <anime>" / "football edit of <player/tournament>"
- User provides a song (path or YouTube URL) + a subject/style brief.

Not this skill: trimming one clip, plain concatenation, or a slideshow with no beat sync.

## Clarify first (only if genuinely ambiguous)

Ask 2–4 crisp questions, then go. Good ones: **subject/scope** (which player/team/scene, whole thing vs a slice) and **length** (full song vs a section — say `--start/--end`). **Never ask about style, format, or delivery — they are fixed, not choices:** there is one style (§*The style* — aggressive, effect-driven, built landscape) and it *always* delivers as the immersive **tall-fill vertical (~1080×2340)** — the full-res, descriptively-named file **Taildropped to the phone** (Marcus posts to TikTok from the phone), with the caption sent as its own message on the hypebot Telegram bot (Phase 5). Do not surface a format/style/delivery picker. If the brief is already clear, don't stall — act.

**Surface every question to the phone, not just the terminal.** Marcus posts from his phone and is often away from the keyboard, so any clarifying question must also reach the hypebot bot: `python3 $S/ask.py "<the questions — and tell him to reply in the terminal>"`, paired with `AskUserQuestion` for the terminal side. It is **send-only**: the hypebot bot already runs its own Telegram `getUpdates` poller, so a second consumer 409-conflicts with it and can't read replies back — he reads on his phone and answers in the terminal. `ask.py` no-ops when the secrets are absent (terminal-only still works), and doubles as a status heads-up: `ask.py "rendering, ~5 min"`.

## The style — aggressive pacing, your artistic direction

There is nothing to pick, and **one thing above all is fixed: relentless aggressive pacing so the viewer's attention never drops.** Everything about the *look* is yours to direct.

**Fixed on every edit:**
- **Pacing — the non-negotiable.** Fast, tight, energy-mapped **machine-gun cuts** locked to the beat (`qc.py` 0-frame offset), density tracking the song and leaning dense, hitting hard from frame one and never coasting — no limp or draggy stretch. This is what holds attention; it is not optional. Normal speed, fast cuts (no slow-mo).
- **Output geometry.** Built on a **1920×1080 landscape canvas — the full frame, no cropping** — then delivered as the **immersive vertical**: the finished landscape rotated 90° and scaled to fill a tall phone screen (~**1080×2340**; iPhone Air = 1080×2346) edge-to-edge, running *behind* the notch and TikTok UI (viewer rotates their phone; ref: the 9s Messi edit). No portrait-crop; the tall canvas trims only ~9% off the source's top/bottom.

**Yours to direct (artistic — decide per edit, and it may vary clip-to-clip):**
- **Coloring / grade.** A default teal-orange preset seeds `project.json "grade"`, but the look is your call — restyle it, push it, or set a per-segment `"grade"` so coloring differs shot to shot (`render.py` honors a per-segment grade, falling back to the global one). Colour consistency is *not* required; a point of view is.
- **Effects.** `assign_clips.py` bakes a dense, beat-keyed plan by default (punch/flash/shake/RGB on ~every cut, freeze on the biggest beat) and `render.py` carries cranked intensities — a strong aggressive baseline. Flavor and dial it to the piece; the density serves the pacing, so keep it hot.

`extract_audio.py --style classic` selects the pipeline (`project.json "style"` drives every stage); canvas 1920×1080@30 (`--w/--h/--fps` override). The landscape render is the working master on disk; the deliverable is always the rotated tall-fill vertical (Phase 5).

## Prerequisites

`ffmpeg`/`ffprobe`, `yt-dlp`, `python3`. GPU NVENC is auto-detected and used if present; otherwise it falls back to libx264 (slower, identical result). Put the workdir on a fast disk with plenty of free space (footage + intermediates run tens of GB). **Never use `/tmp`** if it's RAM-backed.

```bash
S=~/.claude/skills/hype-edit/scripts
bash $S/setup.sh <workdir>          # venv + tree + deps; prints which encoder you'll use
PY=<workdir>/.venv/bin/python       # use THIS python for build_spine.py, scenes.py, extract_audio.py
```

## The bar (what "great" means — enforce all of these)

- **Aggressive pacing is the non-negotiable — it's what holds attention.** Fast, tight, energy-mapped cuts locked to the beat; density leans dense; the edit **hits hard from the first frame and never coasts** — no limp or draggy stretch, end to end. The *look* (coloring/grade, effect flavor and intensity) is your artistic call and may even vary clip-to-clip — but the relentless pacing must hold, whatever the subject.
- **Every cut lands on a beat** (≤2 frames). Verified numerically by `qc.py` (target: 0-frame offset).
- **Cadence tracks energy**: long held shots in the lulls (2–3 s), machine-gun cuts in the drops (~0.4 s). Density must be highest in the drops.
- **Best moments on the biggest hits.** Reserve the freeze-frame for the single loudest beat; spread hero moments across the song (~1 per 25 s).
- **The edit exploits the song's main hook.** Window the track so its signature drop/hook is the centerpiece — entering around the middle (≈7–8s of a 15s edit), never a tail-end afterthought — and detonate the single most iconic moment exactly on the hook's entry, with the build visibly building TO it. If the best moment isn't on the hook, the edit is wrong.
- **The subject opens the video.** Segment 0 shows the subject clearly in view from the first frames — face/name/identity unmistakable, no establishing wides, no gear-only shots. Viewer retention is decided in the first second.
- **Every frame earns its place.** No black frames, no broadcast wipes, no sponsor/score bumpers, no static graphics, no near-duplicates.
- **Key action stays clear of the trim margins.** The build is the full 1920×1080 frame (no per-segment crop); the tall-fill vertical trims only ~9% off the top/bottom at delivery, so don't rely on content living in those edges.
- **Diversity + zero reuse.** With a deep pool, no clip repeats and consecutive cuts come from different sources.
- **Keep every cut clean.** Fire effects densely on the hits, but rarely stack more than ~3 at once, and never let them muddy the footage or blow out detail — density should energize the pacing, not smear the frame.
- **Zero A/V drift.** One continuous master audio muxed last; sum of segment frames == `total_frames`.

## Workflow

### Phase 0 — Audio is the boss

```bash
$PY $S/extract_audio.py <workdir> "<song file or URL>" --style classic [--start S --end E] [--pitch 1.04]
$PY $S/build_spine.py <workdir>
```

`extract_audio.py` downloads/extracts the song, optionally **pitch-shifts it** (`--pitch 1.04` = +4% via rubberband, tempo preserved — use when the edit is bound for TikTok/IG/YT and the track would trip Content-ID; ±3–5% is enough), **trims trailing silence**, frame-aligns the timeline, writes **sample-exact** analysis (22.05k mono) + master (44.1k stereo) WAVs, and seeds `project.json`. `build_spine.py` runs octave-corrected tempo detection, a **phase-locked uniform beat grid** (metronomic — no per-beat jitter), an energy curve, drop detection, sections, and a `cutlist` tiled 0→dur on the beat grid with hero slots. Read its printout: BPM/`cv` (want `cv`≈0), drop time, hero placement, and the density gradient (drops should have the most cuts). If tempo looks octave-wrong, that's the thing to fix here.

### Phase 1 — Source the footage (you drive this)

Sourcing is judgment, not a script. Do a **metadata sweep** across several query angles, prefer **official / high-bitrate 1080p** uploads over fan re-ups (they survive Content-ID and aren't watermarked), and over-collect for diversity:

```bash
yt-dlp --flat-playlist --dump-json "ytsearch12:<angle>" | \
  python3 -c "import sys,json;[print(d.get('id'),d.get('duration'),d.get('title','')[:70]) for d in map(json.loads,sys.stdin) if d.get('id')]"
```

Pick sources on-subject and high-action (goals/skills/celebrations/moments — not talk-shows, previews, training, or club footage when the brief says a specific tournament). Because every cut carries heavy effects and fast pacing, favor **iconic, high-action, readable** moments — a muddy or ambiguous clip won't survive the flashes and shake; 50/60fps sources (fetch.sh already prefers them) cut cleaner. Watch for trap source types that pass every automated filter: **EA FC/PES sim gameplay** (flat lighting, game HUD — ban the whole source via exclude_clips); **fan comps with WATCH NEXT / SUBSCRIBE end-cards mid-file or at the tail** (check the last ~15s before trusting); and — for **game footage** (AMV / gaming edits) — in-game overlays that appear on only some frames and sail through the motion/graphic filters: **combo/hit counters** ("18 HITS"), **QTE button prompts / controller-glyph overlays** (L1/R2/△/○), **PlayStation-button HUD**, and **burned subtitles / intro text cards** in cutscene rips. These leak into specific clips, not whole sources — catch them on the seg grid + clean single-frame probes and ban by `clip_id`. Then download **robustly** (sequential — parallel yt-dlp on the same file corrupts it):

```bash
bash $S/fetch.sh <workdir> <id1> <id2> ...     # validates each by decoding; retries corrupt ones
$PY  $S/scenes.py    <workdir>                  # slice into single-action clips + motion timelines
python3 $S/colorscan.py <workdir>              # flag promo cards + synthetic graphics
```

**Audit the sources before trusting them.** Build a per-source frame montage (`contact_sheet.py` logic, or `ffmpeg -ss <t> -i src/<id>.mp4 -frames:v 1`) and eyeball kits/scoreboards. Comps titled "Best of <player> <year>" are often *club* footage, not the event you asked for — drop off-subject sources. This one check saves an entire wasted render.

### Phase 2/3 — Assign + render

```bash
$PY $S/assign_clips.py <workdir>            # zero reuse, diversity, graphic-aware in-points, motion-centered framing
python3 $S/render.py   <workdir> --draft    # fast 540p pass to inspect the DIRECTION cheaply
python3 $S/contact_sheet.py <workdir> --draft --n 40   # READ frames/contact.png as an image
python3 $S/contact_sheet.py <workdir> --segs           # READ frames/seggrid.png — labeled frames per segment (start/mid/end for holds ≥1s)
```

The **segment grid is the precision review tool**: every defect maps to a segment index → `assign.json segments[i].clip_id` → append that id to `project.json "exclude_clips"` → re-run assign + draft. Loop until the grid is clean (typically 2–3 passes; ban billboards/typography/black/blur/refs/near-empty frames). Holds ≥1s show three tiles (`a/b/c` = start/mid/end): the subject must be in frame in **all three** — a crop that loses the player by `b` or `c` is a defect like any other (hand-patch that segment's `crop`, or exclude the clip). Never edit scenes.json flags for this — `exclude_clips` is the audit trail.

**Seg-grid review = icon-worthiness, not crop-framing.** The build is the full 1920×1080 frame — there's **no per-segment vertical crop**, so the "subject lost in the crop" defect class doesn't exist. What you review is quality: reject anything that isn't a clean, readable, on-subject moment (billboards/typography/menus/HUD/black/blur/refs/near-empty frames), and keep the key action out of the extreme top/bottom ~9% (the tall-fill trims those at delivery). When hand-picking any in-point, probe with the **renderer's exact seek shape** (`ffmpeg -ss <t> -t <d> -i src.mp4 -frames:v 1`) — on some downloads fast and accurate seek land on different content, and sources with broken seek indexes can land several seconds off a plain-strip probe. Never pin an in_tc from a probe that used a different seek form.

**Openers are the retention gate — the subject must be clearly in view from frame one (hard requirement, any subject domain).** Low-energy song intros make the assigner hold low-motion clips, and low-motion pool clips are usually static wides — a 5s distant wide opener kills TikTok retention. After the first draft, always check segments 0–2: segment 0 must show the subject unmistakably (face/helmet/name/kit — a viewer who knows the subject recognizes them instantly); if the opener is a wide, gear-only, or ambiguous shot, hand-patch it (edit assign.json directly post-assign: set src/in_tc/crop to a subject close-up hold — celebration, face, name-shirt, aura walk — validated with a render-exact probe). Re-patch after every re-assign; direct assign.json edits don't survive assign_clips.py re-runs. **Watch the opener's own effects:** a `dropflash` (the seg-0 default) over a very short segment 0 whites out the subject for most of its length — clear seg 0 to `["punch"]` and, if it's only a few frames, hand-hold the same shot across seg 0–1 (continuous `in_tc`) so the face registers before the machine-gun starts.

**No AI restoration by default (dropped 2026-07-19).** SeedVR2 detail restoration is OFF the standard path. It measurably recovers face/skin/edge detail on compressed sources (~2.9× sharpness on close-ups, verified), but that detail is imperceptible after TikTok's upload re-encode + phone downscale, and it costs ~1hr of exclusive GPU (~10GB VRAM, ~2.7s/frame) per edit — a bad trade for social delivery. Critically, restoration does **not** create the look — the grade and dense beat-locked effects (in `render.py`) do. `restore.py` is retained only for a rare non-social / large-screen master — run it after the cut is locked, then re-render + re-run qc — never as a default step. See `reference/pipeline.md → restore.py`.

`assign_clips.py` maps a distinct, on-energy clip to every segment, picks each in-point on a **motivated, graphic-free** high-motion window, computes vertical framing, and writes an effect plan. It honors `project.json "exclude_clips"` (banned ids) and `"hero_overrides"` (`{src,in_tc,impact[,crop]}`). **Always draft-render + read the contact sheet before the full render** — this is where you catch off-subject footage, leaked graphics, and weak frames for pennies. Fix (drop sources, tighten `colorscan.py` thresholds, raise the motion floor, hand-pick heroes) and re-run. Only then:

```bash
python3 $S/render.py <workdir>              # full-res NVENC/libx264 render → out/edit.mp4 (landscape working master)
python3 $S/qc.py     <workdir>             # numeric gates on the landscape master — must be ALL GATES PASS
# deliverable = rotate + tall-fill to immersive vertical (Phase 5)
python3 $S/contact_sheet.py <workdir> --n 48   # full-res visual pass
```

### Phase 4 — Iterate (at least twice; this is what makes it hype)

Between passes, actually inspect. `qc.py` must be green (frames, format, zero A/V drift, no black/unexpected-freeze, 0-frame beat offset, density-in-drops). Then read the seg grid + contact sheet: any bumper/wipe/dupe/weak frame is a defect → `exclude_clips` → re-render. **Verify heroes from their segment files** (`ffmpeg -i seg/seg_<i>.mp4 -frames:v 1` at a few offsets — output-timestamp sampling can miss the hero window): the subject must be THE subject of the brief, in frame, at peak moment. If the auto-pick is a keeper/teammate/empty grass, pin `hero_overrides` and re-run.

### Phase 5 — Deliver

Write `out/director_note.md` (choices + what you fixed between passes). **Deliver the video by Taildrop, the caption by Telegram.** Marcus posts to TikTok from his phone, so the phone needs the *full-res* file — and the Telegram Bot API hard-caps `sendVideo` at 50MB, which would force a downscaled preview (TikTok re-encodes on upload, so a lower-bitrate source compounds into worse final quality). Taildrop has no such cap.

1. **Name the deliverable descriptively** so the phone's received-files list is unambiguous (which edit + that it's the TikTok vertical): `out/<subject-song-slug>_vertical.mp4`, e.g. `harry-potter-hedwig-dnb_vertical.mp4` — **never** the generic `edit_vertical.mp4`.
2. **Build the immersive tall-fill vertical.** **It is the landscape render rotated 90° and scaled to fill a tall phone screen — footage runs edge-to-edge behind the notch/TikTok UI (viewer rotates the phone). NEVER a cropped-to-portrait composition, and NEVER a 9:16 that letterboxes on tall phones.** Recipe from the finished landscape master: `ffmpeg -i out/edit.mp4 -vf 'transpose=1,scale=-2:2340,crop=1080:2340' -c:v h264_nvenc -b:v 18M -pix_fmt yuv420p -c:a copy out/<slug>_vertical.mp4` (rotation keeps the whole frame; the tall canvas trims only ~9% off the source's top/bottom — sky/foreground). Use `2340` for a generic 19.5:9 tall iPhone, or `2346` to match the iPhone Air exactly.
3. **Taildrop the full-res vertical to the phone:** `tailscale file cp out/<slug>_vertical.mp4 iphone-air:` (device name from `tailscale status`; the iPhone Air is `iphone-air`). Tell Marcus to accept the incoming Taildrop.
4. **Send the caption as its own message on the hypebot Telegram bot** (token/chat in `~/.config/hypebot/secrets.env`, `sendMessage`) — a ready-to-paste TikTok caption (hook + hashtags), so it copy-pastes clean on the phone.

Keep both the landscape master and the vertical full-res on disk under `~/Videos/hype/<date>/`. **Fallback only if the phone is offline** (`tailscale status` shows `iphone-air` offline/unreachable): send a ~44MB preview encode (`-b:v 11M`) via Telegram `sendVideo` instead, and say so.

## Narration / voice-over edits (opt-in)

When the brief is a *story told by a voice* over the OST ("tell the story of X with X narrating"), keep the aggressive pacing but let the narration ride the lulls and detonate the hook. The voice is composited into `master.wav` **under** the OST; the music-only analysis WAV stays untouched, so the beat grid is unaffected and cuts stay locked.

1. **Install once:** `bash $S/setup.sh <workdir> --narration` (adds `asr-venv` — torch CPU + Whisper + Demucs, ~2 GB, opt-in).
2. **Source authentic voice** (don't synthesize — a cloned actor is worse and dubious): grab the exact iconic lines from YouTube cutscene / quote clips. `narrate.py` downloads them.
3. **Spec the lines** in `project.json` (this is the source of truth `narrate.py` reads):
   ```json
   "narration": { "duck_db": -8.5, "lines": [
     {"src": "<yt-id|url|path>", "phrase": "the exact words to locate", "at": 0.3, "gain": 1.0}
   ] }
   ```
   `at` = where the phrase STARTS on the timeline. To land a word on a beat, set `at = beat − (the word's onset within the phrase)` — e.g. detonate "WAR!" exactly on the drop/freeze.
4. **Compose:** `<workdir>/asr-venv/bin/python $S/narrate.py <workdir>` — per source it downloads → Whisper word-timestamps → locates each phrase (difflib alignment, tolerant of misheard boundary words) → Demucs isolates the voice → slices, highpasses, ducks the OST under the speech → rewrites `master.wav` **sample-exact**. Everything caches under `narration/`, so re-runs are cheap.
5. **Validate:** re-transcribe `master.wav` (Whisper) — every line must still read over the music. Then render as normal; `render.py` muxes `master.wav`.

**Placement:** identity over the intro, deeds over the build, the signature line on the drop/freeze, resolution over the outro; leave a wide VO gap right before the drop so the hook lands clean. **Heroes in a narrated edit must be clean, high-contrast subjects** — a low-motion / dark / subtitled cutscene frame black- or freeze-flags in qc and reads as a dead-spot.

## Effect catalog (density is the point)

Baked per-segment by `assign_clips.py` (dense plan, automatic) and `render.py` (cranked intensities), locked to the beat: **punch-in zoom** (every cut), **beat-flash** (white hit, most cuts), **drop-flash** (bigger flash on downbeats / drop entries), **camera shake** (section entries + ~⅓ of cuts), **RGB-split** (~⅓ of cuts), **freeze-frame + zoom + flash + shake** (the single biggest beat only). Effects fire on ~every cut by design — that density serves the relentless pacing; the opener detonates (`punch+drop-flash+shake`). This is the aggressive baseline, not a mandate on the *look*: tune strength in `render.py`, when-they-fire in `assign_clips.py`, and set the grade (global or per-segment `seg["grade"]`) however the piece wants — the pacing is the constant, the styling is yours. To hand-pick hero moments, set `project.json` `hero_overrides` (see `reference/pipeline.md`).

## Batch mode (N edits in one brief)

- **One workdir per edit, one agent per workdir** — never share. If all edits draw on the same source pool, download once, then per extra workdir: symlink `src/*` and copy `scenes.json motion.npz badframes.npz` (they're source-derived; skip scenes.py/colorscan.py there).
- **Zero cross-edit clip overlap**: build edits sequentially or cascade after parallel drafts — collect every `clip_id` from finished edits' `assign.json` and append to the next edit's `exclude_clips`. Distinct edits sharing the same viral moment read as reposts.
- Different songs/sections per edit: re-run Phase 0 per workdir; the beat grid is per-edit state.

## Anti-patterns (do not ship)

Metronomic cuts that ignore energy · all effects stacked on one cut (muddy — cap ~3) · a limp/draggy stretch that stops banging · black/frozen frames · audio drift by the end · a clip repeated too soon · the best moment anywhere but a peak · off-subject or wrong-game/wrong-event footage · menus/HUD/typography/wipes/bumpers/score-graphics left in · declaring done without reading the render · hero unverified at segment level · shipping landscape or a cropped/letterboxed vertical instead of the rotated tall-fill · **[gaming]** combo/hit counters, QTE prompts, or controller-glyph overlays left in · a flash-washed opener (dropflash hides a short seg 0) · a hero **freeze on a low-motion, dark, or subtitled cutscene frame** (it black/freeze-flags in qc and reads as a pacing dead-spot — freeze on a clean high-contrast subject).

## The hard parts (hard-won — read `reference/pipeline.md` for detail)

1. **Sample-exact audio or you drift.** Float `-t` isn't sample-exact; `extract_audio.py` uses `atrim=end_sample`. All timing is frame-derived; segments carry an exact `nf` that telescopes to `total_frames`.
2. **Corrupt downloads are silent.** Parallel yt-dlp on one output, or two agents in one dir, race and corrupt files whose headers still probe fine. `fetch.sh` is sequential and decode-validates. If footage looks broken, decode-test every source (`ffmpeg -v error -i f -f null -`).
3. **Graphics masquerade as action.** Sponsor bumpers/score-numbers/wipes have high motion and pass a motion filter. `colorscan.py` flags them per-clip AND per-frame; the assigner steers in-points off graphic frames. Thresholds are tuned for sports — re-tune for other domains.
4. **Grass is green, so are promo cards.** The promo-card detector needs bright+saturated green, not just green, or it eats the pitch.
5. **`crop` has no `eval=` option** (unlike `scale`/`zoompan`); its x/y already evaluate `t` per-frame. Adding `eval=frame` to a crop makes NVENC fail and silently fall back to CPU (losing effects). Watch the render's fallback count.
6. **Don't hardcode duration.** It's derived from the (silence-trimmed) audio and lives in `project.json`; everything reads it.
7. **One workdir, one agent.** If two agent runs share a workdir they clobber each other's scripts/state — check `ps` for a stale run before diagnosing "impossible" mismatches.

## Files

`scripts/`: `setup.sh` `extract_audio.py` `fetch.sh` `build_spine.py` `scenes.py` `colorscan.py` `assign_clips.py` `render.py` `restore.py` `qc.py` `contact_sheet.py` `ask.py` (surface questions/status to Telegram, send-only) `narrate.py` (opt-in voice-over). `reference/pipeline.md`: data-flow, `project.json` schema, tuning knobs, hero overrides, narration spec, ffmpeg recipe details.
