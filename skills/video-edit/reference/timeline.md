# timeline — data flow, schemas, math

## Data flow

```
song ──extract_audio.py──► song_22k_mono.wav (analysis)  master.wav (mux)  project.json
                                  │
                                  └─ beat_spine.py ──┐
                                                     ├──► timeline.json (cuts, sections, beats)
local/YT footage ──ingest.sh──► src/*.mp4             │
                                   │                  │
                     scenes.py ──► scenes.json + motion.npz
                 colorscan.py ──► scenes.json flags + badframes.npz
                     scene_timeline.py ───────────────┘

timeline + scenes + motion + badframes ──assign_clips.py──► assign.json
assign ──render.py──► seg/seg_###.mp4 → work/video.mp4 → out/edit.mp4
out ──qc.py / contact_sheet.py──► gates + visual proof
```

Every stage is idempotent and reads `project.json`. Re-run any stage after editing inputs.

## project.json

```jsonc
{
  "root": "/abs/workdir",
  "preset": "hype",            // REQUIRED. no default; see presets/
  "fps": 30, "out_w": 1920, "out_h": 1080,
  "dur": 17.2,                 // frame-aligned (set by extract_audio.py or init.py)
  "total_frames": 516,         // dur*fps — the invariant render/qc enforce
  "sr_analysis": 22050,
  "audio_analysis": "song_22k_mono.wav",   // beat producer only
  "audio_master": "master.wav",            // empty = silent render
  "look": {                    // colour direction — see look.py
    "base": "inkwash",                         // library name OR raw ffmpeg chain
    "sections": {"drop": "solar", "peak": "ice"},
    "sources": {"<src_id>": "arctic"},
    "segments": {"10": "mono_steel"},
    "drift": 0.3,                              // 0..1 per-shot deterministic jitter
    "tech": ""                                 // non-colour prefix, always first
  },
  "hero_overrides": [{"src": "<srcid>", "in_tc": 96.7, "impact": 0.7}],
  "exclude_clips": [811, 972],       // banned clip ids (review rejects)
  "motion_floor": 0.045,             // quality floor on clip motion_max; default from preset scan.motion_floor
  "ignore_graphic": false,           // ignore colorscan's graphic flag
  "domain": "sports",                // overrides preset scan.profile
  "source_crop": "crop=iw:ih*0.92:0:ih*0.04",  // optional pre-framing crop (reel UI)
  "cover_sources": false,            // one cut per source before any repeats
  "exclude_sources": ["<srcid>"],    // ban every clip from these files
  "flash_gain": 1.0, "rgb_shift": 7, // override preset effect intensities
  "grade": "",                       // legacy; only used where no look resolves
  "narration": {"duck_db": -8.5, "lines": [
    {"src": "<yt-id|url|path>", "phrase": "the exact words", "at": 0.3, "gain": 1.0}
  ]}
}
```

## presets/<name>.json

The direction file. `preset.py` merges the project's canvas and effect intensities over it.

```jsonc
{
  "name": "hype",
  "summary": "one line for the preset list",
  "canvas": {"w": 1920, "h": 1080, "fps": 30},
  "timeline": "beat",                       // expected producer: beat | shots
  "pacing": {
    "steps": {"low": 8, "build": [4,2,1], "peak": 2, "drop": [1,1,1,2]},
    "first_cut_min_s": 0.0,
    "halfbeat_window": 1.5,                 // beats before a hero at 0.5-beat steps; 0 = off
    "hero_beats": [3, 2],                   // primary, others
    "max_cuts": 8000, "min_cut_s": 0.15
  },
  "effects": {"plan": "aggressive", "flash_gain": 1.0, "rgb_shift": 7},
  "render": {
    "mode": "cuts",                         // cuts | retime
    "rotate": false,                        // 90deg full-bleed portrait
    "interpolate": "none",                  // none | rife
    "base_zoom": 0.0,                       // slow push on every cut; 0 = none
    "speed": {"hero": 1.0},                 // retime only
    "tech": "",                             // technical look prefix
    "encoder": {"cq": 20, "crf": 18, "maxrate": "60M", "bufsize": "180M"}
  },
  "grade": {"seed": "random", "base": null, "tech": ""},
  "scan": {"profile": "sports", "motion_floor": 0.045},  // sports | generic | screen
  "gates": {"beat_offset_max": 2, "density": true, "black": true,
            "freeze": true, "exposure_max": 3, "av_drift": true},
  "deliver": "tiktok",                      // tiktok | master
  "delivery": {"canvas": {"w": 1080, "h": 2340}, "bitrate": "18M"}
}
```

`beat_offset_max: null` disables the beat gate. There is no per-gate default: what is not in `gates` is not enforced.

## timeline.json

```jsonc
{
  "producer": "beat" | "shots",
  "preset": "hype",
  "bpm": 128.0, "beat_period": 0.469,
  "beats": [...], "downbeats": [...], "onsets": [...],
  "sections": [{"start": 0, "end": 8.4, "label": "build"}],
  "drops": [{"time": 8.4, "strength": 0.4}],
  "energy_curve": {"hz": 20, "t": [...], "e": [...]},
  "cutlist": [{"i": 0, "start": 0.0, "end": 1.2, "dur": 1.2, "tag": "build", "hero": false}],
  "meta": {"duration": 17.2, "fps": 30,
           "qc": {"n_cuts": 34, "beat_count": 72, "hero_times": [8.4]}}
}
```

A `shots` timeline has empty beats/downbeats/drops and one `body` section. `timeline.check` asserts the cutlist starts at 0, reaches the duration, has no gaps and no empty cuts.

## Timeline math (why it is frame-exact)

- `dur = floor(song_dur * fps) / fps` after trimming trailing silence → integer `total_frames`.
- Analysis WAV: exactly `round(dur*22050)` samples; master: exactly `round(dur*44100)`. Enforced with `atrim=end_sample=N,apad=whole_len=N` (float `-t` is not sample-exact).
- Each segment's frame count `nf = round(end*fps) - round(start*fps)`. Because `start[k+1]==end[k]`, the sum telescopes to `round(dur*fps) == total_frames`. Cut points land on exact frames; no rounding drift.
- Audio is muxed once over the concatenated silent video → drift is structurally impossible.

## Resume / recover

- **Corrupt sources:** `for f in src/*.mp4; do ffmpeg -v error -i "$f" -map 0:v:0 -f null - 2>&1 | grep -icE 'NAL|error'; done` → re-ingest any nonzero.
- **Mismatched frames after render:** a segment's `nf` did not materialize (usually a bad effect string forcing CPU fallback that still under-produced) — read `render.py`'s fallback list, fix the filter, delete just those `seg_###.mp4`, re-run.
- **Tempo looks octave-wrong:** fix it in `beat_spine.py` (band folding via tempogram salience) before sourcing footage.
- **One workdir, one agent.** Two runs in one dir clobber each other's state — check `ps` for a stale run before diagnosing "impossible" mismatches.
- **Legacy workdirs:** a `project.json` with `style` and no `preset` maps `classic → hype`, `remaster → hype-quality`, and `spine.json` is accepted where `timeline.json` is missing.
