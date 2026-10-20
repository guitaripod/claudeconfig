# review — the visual loop

`S=~/.claude/skills/video-edit/scripts`

The numeric gates catch mechanics; the images catch meaning. Budget for both, and always read the images as images — do not infer "it probably looks fine".

## Draft first

```bash
python3 $S/render.py <workdir> --draft
python3 $S/contact_sheet.py <workdir> --draft --n 40
```

`frames/contact.png` tiles N evenly-sampled frames of the draft. Reject: black frames, broadcast wipes, sponsor/score bumpers, menus, typography, static graphics, duplicated shots, near-empty frames, the wrong subject. If any appear, fix the pool (drop sources, tighten `colorscan` thresholds, raise the motion floor) and re-run — not the frame.

## Segment grid — precision review

```bash
python3 $S/contact_sheet.py <workdir> --segs
```

`frames/seggrid.png` has labeled frames for every rendered segment: one early frame for short cuts, start/mid/end (`a/b/c`) for holds ≥1s. This is what maps a defect to something actionable:

1. Read the grid; note the defective indices.
2. `assign.json segments[i].clip_id` tells you which clip it was.
3. Append that id to `project.json "exclude_clips"`.
4. Re-run `assign_clips.py` + `render.py --draft`; repeat until clean.

`exclude_clips` is the audit trail: it survives re-runs and records why a clip was rejected. Never edit `scenes.json` flags for this.

Direct `assign.json` hand-patches (crop, a specific in-point, a hero) do **not** survive an `assign_clips.py` re-run. Prefer `exclude_clips` and `hero_overrides`; if you must hand-patch, do it last.

## Holds

For any hold ≥1s the subject must be in frame in **all three** tiles. A crop that loses the subject by `b` or `c` is a defect like any other: hand-patch that segment's `crop`, or exclude the clip.

## Heroes

Verify heroes from their own segment files, not from the concatenated output — output-timestamp sampling can miss the hero window:

```bash
ffmpeg -i seg/seg_<i>.mp4 -frames:v 1 -ss <offset> -f image2 out.png
```

The frame must be the brief's subject, in frame, at the peak moment. If the auto-pick is a teammate, an empty pitch, or a close-up of a boot, pin `hero_overrides` with `{src, in_tc, impact}` and re-run.

## When to stop

Stop when QC is green **and** the grid is clean. Pass counts are not the goal; a fixed "iterate twice" ritual burns renders without improving the edit, and a single pass usually leaves one bad cut per fifty.
