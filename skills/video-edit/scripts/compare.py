#!/usr/bin/env python3
"""compare.py <workdir> <left:right> [...] [--duration 6] — side-by-side clips.

Reads the project canvas, writes src/cmpNN.mp4 from each pair (first --duration
seconds of each side, scaled to half the canvas), and leaves the normal shots
pipeline to sequence them. Run it in a workdir whose src/ holds only the
comparison clips, so the originals don't join the pool.
"""
import argparse
import json
import os
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("pairs", nargs="+", help="left.mp4:right.mp4")
    ap.add_argument("--duration", type=float, default=6.0)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    cfg = json.load(open(f"{root}/project.json"))
    w, h, fps = cfg["out_w"], cfg["out_h"], cfg["fps"]
    hw = (w // 2) // 2 * 2
    os.makedirs(f"{root}/src", exist_ok=True)
    for k, pair in enumerate(a.pairs, 1):
        if ":" not in pair:
            sys.exit(f'pair {k} is not left:right → "{pair}"')
        left, right = pair.split(":", 1)
        out = f"{root}/src/cmp{k:02d}.mp4"
        half = (f"scale={hw}:{h}:force_original_aspect_ratio=increase,crop={hw}:{h},"
                f"setsar=1,fps={fps}")
        fc = f"[0:v]{half}[l];[1:v]{half}[r];[l][r]hstack=inputs=2[o]"
        r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                            "-y", "-i", left, "-i", right, "-filter_complex", fc,
                            "-map", "[o]", "-t", str(a.duration), "-an", "-frames:v",
                            str(int(round(a.duration * fps))), "-c:v", "libx264",
                            "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"pair {k}: {r.stderr.strip()[-300:]}")
        print(f"  {os.path.basename(left)} | {os.path.basename(right)} → src/cmp{k:02d}.mp4")
    print(f"{len(a.pairs)} comparison clips → src/")


if __name__ == "__main__":
    main()
