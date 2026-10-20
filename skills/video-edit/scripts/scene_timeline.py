#!/usr/bin/env python3
"""scene_timeline.py <workdir> — footage-led timeline: long holds, no beat grid.

The second producer of timeline.json. Reads scenes.json + project.json and tiles
the project duration with shots drawn from the scene list, so an edit with no
music (or one that should not cut to it) still runs through the same assign,
render and QC stages. Pacing comes from the preset: target/min/max shot seconds.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preset
import timeline

MARGIN = 0.5


def choose_order(clips, order):
    if order == "motion":
        return sorted(clips, key=lambda c: (-c["motion_max"], c["src"], c["start"]))
    return sorted(clips, key=lambda c: (c["src"], c["start"]))


def make_cuts(duration, target, lo, hi, pool):
    cuts, t, k, last = [], 0.0, 0, None
    while t < duration - 1e-6:
        remaining = duration - t
        shot = min(target, remaining)
        if cuts and remaining < lo:
            cuts[-1]["end"] = round(duration, 4)
            cuts[-1]["dur"] = round(cuts[-1]["end"] - cuts[-1]["start"], 4)
            break
        shot = max(min(shot, hi), min(lo, remaining))
        shot = min(shot, remaining)
        end = round(min(t + shot, duration), 4)
        src = next((c["src"] for c in pool if c["src"] != last), pool[k % len(pool)]["src"])
        cuts.append({"i": k, "start": round(t, 4), "end": end,
                     "dur": round(end - t, 4), "tag": "body", "hero": False,
                     "source": src})
        last, k, t = src, k + 1, end
        if k > 20000:
            raise SystemExit("cutlist did not converge")
    return cuts


def main():
    root = os.path.abspath(sys.argv[1])
    cfg, p = preset.load(root)
    if p.get("timeline") != "shots":
        raise SystemExit(f'preset "{p["name"]}" declares timeline "{p.get("timeline")}" — '
                         "this producer is for footage-led edits; run beat_spine.py instead")
    with open(f"{root}/scenes.json") as f:
        clips = json.load(f)["clips"]
    fps, dur = cfg["fps"], cfg["dur"]

    pacing = preset.require(p, "pacing")
    lo = float(pacing["min_shot_s"])
    hi = float(pacing["max_shot_s"])
    target = float(pacing["target_shot_s"])
    pool = [c for c in clips if not c.get("dark") and c["dur"] >= lo + MARGIN]
    if not pool:
        pool = [c for c in clips if c["dur"] >= MARGIN + 0.1]
    if not pool:
        raise SystemExit("no usable scenes — run scenes.py first")
    feasible = max(c["dur"] for c in pool) - MARGIN
    target = max(min(target, hi, feasible), min(lo, feasible))
    lo = min(lo, feasible)

    order = pacing.get("order", "chronological")
    cuts = make_cuts(dur, target, lo, hi, choose_order(pool, order))
    sections = [{"start": 0.0, "end": dur, "label": "body"}]
    tl = {
        "producer": "shots",
        "preset": p["name"],
        "bpm": None,
        "beats": [], "downbeats": [], "drops": [], "onsets": [],
        "sections": sections,
        "cutlist": cuts,
        "meta": {"duration": dur, "fps": fps,
                 "qc": {"n_cuts": len(cuts), "beat_count": 0,
                        "hero_times": [], "drop_confidence": "none"}},
    }
    timeline.check(tl)
    timeline.write(root, tl)
    d = np.array([c["dur"] for c in cuts])
    print(f"{len(cuts)} cuts  mean {d.mean():.2f}s  min {d.min():.2f}s  max {d.max():.2f}s "
          f"→ timeline.json (producer=shots, target {target:.2f}s)")


if __name__ == "__main__":
    main()
