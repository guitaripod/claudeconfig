# Templates — directions that ship

A template is a preset: pacing, effects, canvas, gates, delivery. Some need a
producer or a project field beyond the preset; those are called out.

| preset | producer | input | shape |
|---|---|---|---|
| `lookbook` | shots | footage | 1080×1350, 2.5s holds, bleach |
| `travel` | shots | footage | 1920×1080, 4s holds, sunbleach |
| `recap` | shots | footage | 1920×1080, 1.6s holds |
| `slow-burn` | beat | song + footage | 1920×1080, 4–16 beat cuts |
| `ambient-loop` | shots | footage | 1080×1920, 6–12s holds |
| `product` | beat | song + footage | 1080×1350, speed cycle + text |
| `broadcast` | beat | song + footage | 1920×1080, wipes + replays |
| `trailer` | shots | footage + track | 1920×1080, titles + silences |
| `documentary` | doc | A-roll + B-roll + SRT | 1920×1080, captions |
| `talking-head` | doc | A-roll + SRT | 1080×1920, captions |
| `photo` | stills → shots | images | 1080×1350, Ken Burns |
| `compare` | compare → shots | pairs | 1920×1080, side-by-side |

The existing `hype`, `hype-rapid`, `hype-quality` and `calm` are unchanged.

## Subject pass

Run `faces.py` after `colorscan.py`; it annotates every clip with face area, centre
and sharpness, and writes `faces.npz`. Presets choose:

- `face` — hard filter at `scan.min_face_frac`; used by `lookbook`, `documentary`, `talking-head`.
- `auto` — filter only when at least a third of usable clips have a face; the rest.
- `none` — `product`, `broadcast`, `compare`.

It finds **a** face, not a specific person: a stranger in frame still passes, so
the segment grid is still the identity check. Re-run `faces.py` after `scenes.py`
if the source set changes.

`pacing.source_gap_s` stops a source reappearing too soon (lookbook 25s, ambient
20s); without it, two clips from the same continuous shot can land 10s apart.
`pacing.dupe_distance` rejects a clip whose sampled frame hashes are within N bits
of a recent shot (72-bit block hash from `colorscan.py`), which catches the same
moment in two different files; it is off for hype and on for the slow templates.

## Footage-led

```bash
$PY $S/init.py <wd> --preset lookbook --duration 30
bash $S/ingest.sh <wd> <files|dir>
$PY $S/scenes.py <wd> && $PY $S/colorscan.py <wd>
$PY $S/scene_timeline.py <wd>
$PY $S/assign_clips.py <wd>
python3 $S/render.py <wd> && python3 $S/qc.py <wd>
```

`cover_sources: true` in `project.json` puts every source in before repeating;
`exclude_sources` bans a whole bad file. `travel` and `recap` want
`"pacing": {"order": "chronological"}`; the presets already set it.

`ambient-loop` is built to replay: long holds, no effects, and a song looped with
`extract_audio.py --loop N` if there is music. It is not a seamless visual loop —
the last shot does not match the first; use a one-shot or crossfade by hand if the
seam matters.

## Beat-led

```bash
$PY $S/extract_audio.py <wd> "<song>" --preset product [--loop N]
# ingest / scenes / colorscan / beat_spine
$PY $S/assign_clips.py <wd>
```

`product` uses `render.speed_cycle` (`{"body": [1.0, 1.5, 1.0, 0.65]}`) and the
`product` effect plan; add `overlays` for text beats.
`broadcast` uses `render.speed` for replays (hero 0.4, drop 0.5, peak 0.65) and
the `broadcast` plan for wipes; add a `score` overlay for a score bug.
`slow-burn` is the same beat path with long cadence and the `slow` plan.

Speed changes are **per shot**, not intra-shot ramps. A shot can run 1.5× or
0.65×; it cannot ease from one to the other.

## Stills

```bash
$PY $S/init.py <wd> --preset photo --duration 30
bash $S/ingest.sh <wd> <image files|dir>     # lands in assets/
$PY $S/stills.py <wd> [--duration 8]         # Ken Burns → src/
$PY $S/scenes.py <wd> && $PY $S/colorscan.py <wd>
$PY $S/scene_timeline.py <wd> && $PY $S/assign_clips.py <wd>
```

Each image becomes an 8s centre-zoom clip at the preset canvas. `cover_sources`
makes every photo appear once. Replace a generated clip by hand if a still needs
a different move.

## Documentary / talking-head

```bash
$PY $S/init.py <wd> --preset documentary            # or extract_audio from the A-roll
bash $S/ingest.sh <wd> <aroll> <broll...>
$PY $S/extract_audio.py <wd> <wd>/src/<aroll>.mp4 --preset documentary
$PY $S/scenes.py <wd> && $PY $S/colorscan.py <wd>
$PY $S/doc_timeline.py <wd> --aroll <aroll-id> --srt cues.srt \
    [--chunk 8] [--broll-every 2] [--lower-third "Name, role"]
$PY $S/assign_clips.py <wd>
python3 $S/render.py <wd> && python3 $S/qc.py <wd>
```

The A-roll is pinned to its absolute timeline position (`in_tc = cut start`), so
the one master audio track stays in sync while B-roll covers selected chunks.
Captions and the lower third are written to `project.json.overlays` and burned at
render. `--broll-every 0` is the talking-head case.

There is no automatic transcription in the producer: supply an SRT. Generate one
with the narration venv (`py-narrate` + Whisper) or an editor. The SRT times must
match the A-roll.

## Compare

```bash
$PY $S/init.py <wd> --preset compare --duration 12
$PY $S/compare.py <wd> left1.mp4:right1.mp4 left2.mp4:right2.mp4 --duration 6
$PY $S/scenes.py <wd> && $PY $S/colorscan.py <wd>
$PY $S/scene_timeline.py <wd> && $PY $S/assign_clips.py <wd>
```

`compare.py` writes `src/cmpNN.mp4` into a workdir whose `src/` holds only the
comparison clips; it is side-by-side, not a wipe or a slider. For a moving
wipe/slider, use the `video-comparison` skill instead.

## Overlays

```json
"overlays": [
  {"text": "NEW DROP", "start": 0.2, "end": 2.0, "style": "title"},
  {"text": "it's the one: 100%", "start": 2.0, "end": 4.0, "style": "caption"},
  {"text": "Ana, founder", "start": 1.0, "end": 6.0, "style": "lower_third"},
  {"text": "2 – 1", "start": 0.0, "end": 90.0, "style": "score"}
]
```

Styles are `title`, `lower_third`, `caption`, `score`; sizes and positions scale
with the canvas. Text is read from a file, so apostrophes, colons and `%` are
literal. One line per overlay — captions are not wrapped.

## Audio ranges

```json
"audio": {"silence": [[10.0, 11.2]], "duck": [[12.0, 14.0, -8]]}
```

`silence` mutes a window (trailer beats); `duck` lowers it by dB. Applied at mux,
so the source track and the WAV stay untouched.

## Limits worth knowing

- Speed is per shot; no intra-shot ramps.
- Trailers do not synthesize risers; use a track that already has them.
- Documentary cuts need an SRT; there is no ASR in the producer.
- Compare is side-by-side only.
- `ambient-loop` is not a seamless visual loop.
