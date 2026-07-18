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

Ask 2–4 crisp questions, then go. Good ones: **subject/scope** (which player/team/scene, whole thing vs a slice), **length** (full song vs a section — say `--start/--end`), **style** (see Styles below), and **delivery** (file, or send somewhere). If the brief is already clear, don't stall — act.

## Styles (`extract_audio.py --style …`)

Two art directions, chosen at Phase 0; `project.json "style"` drives every later stage.

- **`remaster` — the TikTok default.** The "4K quality edit" genre (reference: 9s Messi edit, 5.5M views): the **full landscape broadcast frame rotated 90° clockwise** to fill 1080×1920 edge-to-edge — zero pixels cropped away, content runs under the TikTok UI, the viewer rotates their phone. On top: a **4K-remaster grade** (denoise → oversharpen → cas → saturation/vibrance → HDR-ish curve), **slow motion everywhere** (heroes 0.5×, drops/peaks 0.65×, builds 0.75×, lulls 0.85×) synthesized to **buttery 60fps** by motion-compensated interpolation on the full render, and **near-zero effects** — a soft flash on drop entries and occasional downbeats, a 3% drift zoom, nothing else. The detail and the slow-mo ARE the effect. Cadence is deliberate: ~2.2s+ opening hold, then ~1s beat-locked cuts, heroes held 3–4 beats. Short totals fit the genre (9–20s); every clip must be an **iconic moment** of the subject.
- **`classic`** — the original 1920×1080@30 (or vertical-cropped) punchy montage: teal-orange grade, energy-mapped machine-gun cuts, punch zooms/flashes/shake/RGB-split, freeze-frame hero. Use for landscape deliveries, YouTube, or when the brief asks for aggressive effect-driven editing.

Canvas defaults come from the style (remaster 1080×1920@60, classic 1920×1080@30); `--w/--h/--fps` override. **Remaster always ships two files**: the portrait master AND `render.py --landscape` — the same edit on a 1920×1080 canvas without the rotation.

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
- **The subject never leaves the frame.** A vertical crop must hold the player for the segment's full duration — verified start/mid/end on the seg grid, not at a single instant.
- **Diversity + zero reuse.** With a deep pool, no clip repeats and consecutive cuts come from different sources.
- **Restraint reads as quality.** Effects punctuate; they don't smother. Never stack >2–3 on a cut.
- **Zero A/V drift.** One continuous master audio muxed last; sum of segment frames == `total_frames`.

## Workflow

### Phase 0 — Audio is the boss

```bash
$PY $S/extract_audio.py <workdir> "<song file or URL>" [--style remaster] [--start S --end E] [--pitch 1.04]
$PY $S/build_spine.py <workdir>
```

`extract_audio.py` downloads/extracts the song, optionally **pitch-shifts it** (`--pitch 1.04` = +4% via rubberband, tempo preserved — use when the edit is bound for TikTok/IG/YT and the track would trip Content-ID; ±3–5% is enough), **trims trailing silence**, frame-aligns the timeline, writes **sample-exact** analysis (22.05k mono) + master (44.1k stereo) WAVs, and seeds `project.json`. `build_spine.py` runs octave-corrected tempo detection, a **phase-locked uniform beat grid** (metronomic — no per-beat jitter), an energy curve, drop detection, sections, and a `cutlist` tiled 0→dur on the beat grid with hero slots. Read its printout: BPM/`cv` (want `cv`≈0), drop time, hero placement, and the density gradient (drops should have the most cuts). If tempo looks octave-wrong, that's the thing to fix here.

### Phase 1 — Source the footage (you drive this)

Sourcing is judgment, not a script. Do a **metadata sweep** across several query angles, prefer **official / high-bitrate 1080p** uploads over fan re-ups (they survive Content-ID and aren't watermarked), and over-collect for diversity:

```bash
yt-dlp --flat-playlist --dump-json "ytsearch12:<angle>" | \
  python3 -c "import sys,json;[print(d.get('id'),d.get('duration'),d.get('title','')[:70]) for d in map(json.loads,sys.stdin) if d.get('id')]"
```

Pick sources on-subject and high-action (goals/skills/celebrations/moments — not talk-shows, previews, training, or club footage when the brief says a specific tournament). For **remaster**, be pickier still: every segment is a slow-mo hold on the full frame, so only iconic, tightly-framed follow-cam moments earn a slot — and 50/60fps sources (fetch.sh already prefers them) are what make the slow-mo butter. Watch for two trap source types that pass every automated filter: **EA FC/PES sim gameplay** (flat lighting, game HUD — ban the whole source via exclude_clips) and **fan comps with WATCH NEXT / SUBSCRIBE end-cards mid-file or at the tail** (check the last ~15s before trusting). Then download **robustly** (sequential — parallel yt-dlp on the same file corrupts it):

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

**Vertical output framing** (classic style only — **remaster keeps the whole rotated frame and never crops**, so this entire defect class disappears there; on remaster seg grids the tiles are auto counter-rotated upright, and what you review instead is *icon-worthiness*: reject anything that isn't a clean, tight, iconic moment): when `out_w/out_h` is taller than the source, the assigner auto-computes a motion-centered crop per segment (pan-compensated, so tracking-camera shots frame the player, not the streaming background). Motion is a proxy, not a subject detector — a static crop centered on aggregate motion can lose a player who crosses the frame or stands still while the background moves, which is exactly what the `a/b/c` seg-grid tiles exist to catch. (A min-coverage-across-pairs scorer was A/B-tested against real footage 2026-07 and framed persistent background motion — bench staff, crowd — over the subject; don't re-derive it. The review loop is the framing guarantee.) Known miss: full-frame close-ups may frame a moving limb — catch on the seg grid and hand-patch that segment's `crop` in assign.json (or `hero_overrides[].crop`). When hand-picking any crop/in-point, probe with the **renderer's exact command shape** (`ffmpeg -ss <t> -t <d> -i src.mp4 -vf 'crop=<the crop>' -frames:v 1`) — on some downloads fast and accurate seek land on different content, and sources with broken seek indexes can land several seconds off a plain-strip probe. Never pin an in_tc from a probe that used a different seek form.

**Openers are the retention gate.** Low-energy song intros make the assigner hold low-motion clips, and low-motion pool clips are usually static wides — a 5s distant wide opener kills TikTok retention. After the first draft, always check segments 0–2: if they're wides, hand-patch them (edit assign.json directly post-assign: set src/in_tc/crop to a subject close-up hold — celebration, face, name-shirt, aura walk — validated with a render-exact probe). Re-patch after every re-assign; direct assign.json edits don't survive assign_clips.py re-runs.

`assign_clips.py` maps a distinct, on-energy clip to every segment, picks each in-point on a **motivated, graphic-free** high-motion window, computes vertical framing, and writes an effect plan. It honors `project.json "exclude_clips"` (banned ids) and `"hero_overrides"` (`{src,in_tc,impact[,crop]}`). **Always draft-render + read the contact sheet before the full render** — this is where you catch off-subject footage, leaked graphics, and weak frames for pennies. Fix (drop sources, tighten `colorscan.py` thresholds, raise the motion floor, hand-pick heroes) and re-run. Only then:

```bash
python3 $S/render.py <workdir>              # full-res NVENC/libx264 render → out/edit.mp4
python3 $S/render.py <workdir> --landscape  # remaster: MANDATORY 1920x1080 companion (same edit, un-rotated) → out/edit_landscape.mp4
python3 $S/qc.py     <workdir>             # numeric gates — must be ALL GATES PASS
python3 $S/contact_sheet.py <workdir> --n 48   # full-res visual pass
```

### Phase 4 — Iterate (at least twice; this is what makes it hype)

Between passes, actually inspect. `qc.py` must be green (frames, format, zero A/V drift, no black/unexpected-freeze, 0-frame beat offset, density-in-drops). Then read the seg grid + contact sheet: any bumper/wipe/dupe/weak frame is a defect → `exclude_clips` → re-render. **Verify heroes from their segment files** (`ffmpeg -i seg/seg_<i>.mp4 -frames:v 1` at a few offsets — output-timestamp sampling can miss the hero window): the subject must be THE subject of the brief, in frame, at peak moment. If the auto-pick is a keeper/teammate/empty grass, pin `hero_overrides` and re-run.

### Phase 5 — Deliver

Write `out/director_note.md` (choices + what you fixed between passes). **Default delivery is the hypebot Telegram bot** (token/chat in `~/.config/hypebot/secrets.env`): send each video (`sendVideo`; files ≥49MB get a ~46MB preview encode first — full-res stays on disk under `~/Videos/hype/<date>/`), then the TikTok caption as its **own separate message** so it copy-pastes clean. Never Taildrop unless explicitly asked.

## Effect catalog (restraint > quantity)

Baked per-segment by `assign_clips.py`/`render.py`, keyed to energy. **Classic**: **punch-in zoom** (driving beats), **beat-flash** (white hit on downbeats), **drop-flash** (bigger flash on drop entries), **camera shake** (decaying, on key hits), **RGB split** (chromatic aberration on the hardest), **freeze-frame + zoom + flash + shake** (reserved for the single biggest moment). **Remaster**: soft drop-flash on drop entries and heroes, soft beat-flash on every 4th downbeat, a 3% drift zoom — shake/RGB-split/freeze are off by design; the slow-mo detail carries it. Tune intensity in `render.py`; tune *when they fire* in `assign_clips.py`. To hand-pick hero moments, set `project.json` `hero_overrides` (see `reference/pipeline.md`).

## Batch mode (N edits in one brief)

- **One workdir per edit, one agent per workdir** — never share. If all edits draw on the same source pool, download once, then per extra workdir: symlink `src/*` and copy `scenes.json motion.npz badframes.npz` (they're source-derived; skip scenes.py/colorscan.py there).
- **Zero cross-edit clip overlap**: build edits sequentially or cascade after parallel drafts — collect every `clip_id` from finished edits' `assign.json` and append to the next edit's `exclude_clips`. Distinct edits sharing the same viral moment read as reposts.
- Different songs/sections per edit: re-run Phase 0 per workdir; the beat grid is per-edit state.

## Anti-patterns (do not ship)

Metronomic cuts that ignore energy · every effect on every cut · black/frozen frames · audio drift by the end · a clip repeated too soon · the best moment anywhere but a peak · off-subject or club footage in a tournament edit · broadcast wipes/bumpers/score-graphics left in · declaring done without reading the render · hero framing unverified at segment level · a vertical crop that loses the subject mid-segment.

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
