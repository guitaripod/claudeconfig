#!/usr/bin/env python3
"""timeline.py — the one contract between producers and the rest of the pipeline.

A timeline is a list of cuts covering 0..duration exactly. A song producer
(beat_spine.py) writes it from a beat grid; a footage producer
(scene_timeline.py) writes it from scene detection. assign_clips.py, qc.py and
contact_sheet.py read only this file, so nothing downstream assumes music.
"""
import json
import os

NAMES = ("timeline.json", "spine.json")  # spine.json: pre-preset workdirs


def path(root):
    return os.path.join(root, "timeline.json")


def load(root):
    for name in NAMES:
        p = os.path.join(root, name)
        if os.path.exists(p):
            with open(p) as f:
                tl = json.load(f)
            tl.setdefault("producer", "beat")
            tl.setdefault("beats", [])
            tl.setdefault("downbeats", [])
            tl.setdefault("drops", [])
            tl.setdefault("sections", [])
            return tl
    raise SystemExit("no timeline.json — run beat_spine.py or scene_timeline.py first")


def write(root, tl):
    with open(path(root), "w") as f:
        json.dump(tl, f, indent=1)


def check(tl):
    """Cuts must tile the duration with no gap, overlap or empty shot."""
    cuts = tl["cutlist"]
    assert cuts, "empty cutlist"
    assert abs(cuts[0]["start"]) < 1e-6, "timeline does not start at 0"
    assert abs(cuts[-1]["end"] - tl["meta"]["duration"]) < 1e-3, "timeline does not reach duration"
    for a, b in zip(cuts, cuts[1:]):
        assert abs(a["end"] - b["start"]) < 1e-6, f"gap after cut {a['i']}"
        assert a["dur"] > 0, f"empty cut {a['i']}"
