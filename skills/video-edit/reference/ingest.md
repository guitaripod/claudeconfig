# ingest — sourcing, traps, scanning

`S=~/.claude/skills/video-edit/scripts`

Sourcing is judgment, not a script. Do a metadata sweep across several query angles, prefer **official / high-bitrate 1080p** uploads over fan re-ups (they survive Content-ID and aren't watermarked), and over-collect for diversity.

```bash
yt-dlp --flat-playlist --dump-json "ytsearch12:<angle>" | \
  python3 -c "import sys,json;[print(d.get('id'),d.get('duration'),d.get('title','')[:70]) for d in map(json.loads,sys.stdin) if d.get('id')]"
```

Pick sources that are on-subject and high-action — not talk shows, previews, training, or club footage when the brief names a specific tournament. Fast, effect-heavy edits need **iconic, readable** moments: a muddy or ambiguous clip won't survive flashes and shake. 50/60fps sources cut cleaner.

Then ingest (local files, directories, or YouTube ids/URLs):

```bash
bash $S/ingest.sh <workdir> <source...>
```

Downloads are **sequential** — parallel yt-dlp on the same output races and silently corrupts files whose headers still probe fine. Every file is decode-validated and retried once.

## Trap source types that pass every automated filter

- **Sim gameplay** (EA FC / PES): flat lighting, game HUD. Ban the whole source via `exclude_clips`.
- **Fan comps with end-cards**: "WATCH NEXT / SUBSCRIBE" cards mid-file or at the tail — check the last ~15s before trusting a source.
- **Game footage** (AMV / gaming): overlays that appear on only some frames — **combo/hit counters** ("18 HITS"), **QTE prompts / controller glyphs** (L1/R2/△/○), **PlayStation-button HUD**, **burned subtitles / intro text cards** in cutscene rips. These leak into specific clips, not whole sources — catch them on the seg grid and clean single-frame probes, then ban by `clip_id`.
- **Menus, billboards, score graphics, broadcast wipes** — high motion, so they pass a motion filter.

## Audit before trusting

Build a per-source frame montage (`ffmpeg -ss <t> -i src/<id>.mp4 -frames:v 1`) and eyeball kits/scoreboards. Comps titled "Best of <player> <year>" are often *club* footage, not the event asked for — drop off-subject sources. This one check saves a whole wasted render.

## scenes.py

Slices every source into single-action clips via scene detection, splits uncut blobs into ~4s chunks, and records per-source motion/luma timelines (`motion.npz`). Optional `project.json "catalog"` gives nicer labels: `{"<srcid>": ["Label", "goal|skills"]}`.

## colorscan.py — domain profiles

Flags promo cards / synthetic graphics per clip AND per frame (`badframes.npz`), so in-points steer off wipes and bumpers. The heuristic is a **profile**, chosen by `preset.scan.profile` or `project.json "domain"`:

- `sports` (default for hype): little pitch AND (flat OR oversaturated OR big bright graphic), a bright saturated green promo card, or a white replay-card/typography overlay. Thresholds are tuned for football broadcast.
- `generic`: only rejects flat bright cards and white overlay cards. Use for anime, cinema, documentary.
- `screen`: disables the flag entirely — a rendered interface IS the content.

Tuning knobs live in `colorscan.py` (`green` promo card, `pitch` grass, detail/saturation/brightness thresholds). If a domain produces false positives, change the profile before changing numbers.
