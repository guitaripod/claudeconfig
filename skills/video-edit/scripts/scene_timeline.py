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


def cover_cuts(clips, duration, target, hi, order):
    """One cut per source first, then repeat the cycle until the duration is filled.
    Each cut carries a source hint that assign_clips.py honors, so every ingested
    source appears at least once even when the pool has more sources than cuts."""
    by = {}
    for c in clips:
        by.setdefault(c["src"], []).append(c)
    picks = []
    for src, cs in by.items():
        best = (max(cs, key=lambda c: c["motion_max"]) if order == "motion"
                else max(cs, key=lambda c: (c["dur"], c["motion_max"])))
        shot = min(target, hi, max(best["dur"] - 0.1, 0.6))
        picks.append((src, shot))
    picks.sort()
    cuts, t = [], 0.0
    while t < duration - 1e-6:
        for src, shot in picks:
            if t >= duration - 1e-6:
                break
            d = min(shot, duration - t)
            if d < 0.6 and cuts:
                cuts[-1]["end"] = round(duration, 4)
                cuts[-1]["dur"] = round(cuts[-1]["end"] - cuts[-1]["start"], 4)
                t = duration
                break
            end = round(t + d, 4)
            cuts.append({"i": len(cuts), "start": round(t, 4), "end": end,
                         "dur": round(end - t, 4), "tag": "body", "hero": False,
                         "src": src})
            t = end
        if len(cuts) > 20000:
            raise SystemExit("cover cutlist did not converge")
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
    cover = bool(cfg.get("cover_sources"))
    exc = set(cfg.get("exclude_clips", []))
    exc_src = set(cfg.get("exclude_sources", []))
    base_pool = [c for c in clips if not c.get("dark")
                 and c["id"] not in exc and c["src"] not in exc_src]
    if cover:
        pool = base_pool
    else:
        pool = [c for c in base_pool if c["dur"] >= lo + MARGIN]
        if not pool:
            pool = [c for c in base_pool if c["dur"] >= MARGIN + 0.1]
    if not pool:
        raise SystemExit("no usable scenes — run scenes.py first")
    order = pacing.get("order", "chronological")
    if cover:
        cuts = cover_cuts(pool, dur, target, hi, order)
    else:
        feasible = sorted(c["dur"] - MARGIN for c in pool)
        cap = feasible[int(len(feasible) * 0.75)] if feasible else MARGIN
        target = max(min(target, hi, cap), min(lo, cap))
        lo = min(lo, cap)
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
