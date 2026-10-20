#!/usr/bin/env python3
"""init.py <workdir> --preset <name> [--duration S] [--w N] [--h N] [--fps N]

Create project.json for an edit that has no song: footage-led cuts, a scripted
voice-over, or a silent master. A music edit starts at extract_audio.py instead,
which also writes project.json but derives the duration from the track.

The preset is what decides pacing, effects, geometry, gates and delivery, so it
is required and there is no default.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--preset", required=True)
    ap.add_argument("--duration", type=float, help="seconds; required for a new project")
    ap.add_argument("--w", type=int)
    ap.add_argument("--h", type=int)
    ap.add_argument("--fps", type=int)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    os.makedirs(root, exist_ok=True)
    for d in ("src", "seg", "work", "out", "frames"):
        os.makedirs(f"{root}/{d}", exist_ok=True)

    cfg = {}
    if os.path.exists(f"{root}/project.json"):
        with open(f"{root}/project.json") as f:
            cfg = json.load(f)
    name = a.preset
    path = os.path.join(preset.PRESETS, f"{name}.json")
    if not os.path.exists(path):
        raise preset.PresetError(f'unknown preset "{name}".\n' + preset.list_text())
    p = preset.read(path)

    dur = a.duration if a.duration is not None else cfg.get("dur")
    if not dur:
        sys.exit("--duration is required for a new project (no song to derive it from)")
    fps = a.fps or cfg.get("fps") or p["canvas"]["fps"]
    dur = int(dur * fps) / fps  # frame-aligned
    cfg.update({
        "root": root,
        "preset": name,
        "fps": fps,
        "dur": round(dur, 4),
        "total_frames": int(round(dur * fps)),
        "out_w": a.w or cfg.get("out_w") or p["canvas"]["w"],
        "out_h": a.h or cfg.get("out_h") or p["canvas"]["h"],
        "sr_analysis": cfg.get("sr_analysis", 22050),
        "audio_master": "master.wav" if os.path.exists(f"{root}/master.wav") else "",
        "hero_overrides": cfg.get("hero_overrides", []),
    })
    cfg.pop("style", None)
    if "look" not in cfg:
        base = p["grade"]["base"]
        if not base and p["grade"]["seed"] == "random":
            import random
            from look import LOOKS
            base = random.choice([k for k in LOOKS if k != "neutral"])
        cfg["look"] = {"base": base or "neutral", "sections": {}, "sources": {}, "segments": {},
                       "drift": 0.0, "tech": p["render"].get("tech", "")}
    with open(f"{root}/project.json", "w") as f:
        json.dump(cfg, f, indent=1)
    print(f"preset={name} dur={cfg['dur']}s ({cfg['total_frames']} frames @ {fps}fps "
          f"{cfg['out_w']}x{cfg['out_h']}) look={cfg['look']['base']} → project.json")


if __name__ == "__main__":
    main()
