#!/usr/bin/env python3
"""
Locate an iconic title-sequence frame inside the first N seconds of a target.

Use this as a fallback when audio cross-correlation (find_theme.py) gives
low confidence — common for PAL re-encodes or seasons with re-mastered audio.
The visual signature of the theme song is consistent across audio masterings,
so a single frame template usually nails the offset within ~0.5s.

Method: extract one frame per second (downscaled, grayscale), compute MAE
against the reference frame, return offset of minimum MAE and similarity.

Reference frame must be:
  • a fixed-position shot inside the theme sequence (so intro_end =
    match_offset + theme_duration is consistent across episodes), and
  • visually distinctive (avoid plain interiors / generic exteriors).
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


THUMB_W = 240
THUMB_H = 135  # 16:9


def load_thumb(path: Path) -> np.ndarray:
    img = Image.open(path).convert("L").resize((THUMB_W, THUMB_H))
    return np.asarray(img, dtype=np.float32)


def extract_frames(video: Path, dur: float, fps: float = 2.0):
    """Decode `dur` seconds of video at `fps` to grayscale thumbnails."""
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-i", str(video),
        "-t", str(dur),
        "-vf", f"fps={fps},scale={THUMB_W}:{THUMB_H}:flags=area,format=gray",
        "-f", "rawvideo", "-",
    ]
    p = subprocess.run(cmd, capture_output=True, check=True)
    raw = np.frombuffer(p.stdout, dtype=np.uint8).astype(np.float32)
    n = raw.size // (THUMB_W * THUMB_H)
    return raw[: n * THUMB_W * THUMB_H].reshape(n, THUMB_H, THUMB_W)


def find_best(video: Path, ref: np.ndarray, dur: float = 600.0, fps: float = 2.0):
    frames = extract_frames(video, dur, fps)
    if len(frames) == 0:
        return None, float("inf")
    diffs = np.mean(np.abs(frames - ref), axis=(1, 2))
    idx = int(np.argmin(diffs))
    return idx / fps, float(diffs[idx])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_image")
    ap.add_argument("video")
    ap.add_argument("--dur", type=float, default=600.0)
    ap.add_argument("--fps", type=float, default=2.0)
    args = ap.parse_args()

    ref = load_thumb(Path(args.ref_image))
    t, score = find_best(Path(args.video), ref, args.dur, args.fps)
    if t is None:
        print(f"no match\tfile={args.video}")
        sys.exit(1)
    sim = max(0.0, 1.0 - score / 255.0)
    print(f"match_at={t:.2f}\tmae={score:.2f}\tsimilarity={sim:.3f}\tfile={args.video}")


if __name__ == "__main__":
    main()
