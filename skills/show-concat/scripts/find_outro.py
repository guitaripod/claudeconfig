#!/usr/bin/env python3
"""
Locate the start of the closing credits in an episode.

Heuristic: scan the last `tail_dur` seconds for black frames; the longest
black block in that window marks the transition from the final scene into
the credit roll.  Returns the absolute time of `black_start` (the cut point).

Works for shows with silent end-credit cards (early Office) and shows with
closing-theme music (most modern series) — the visual cue is consistent.
"""
import sys
import re
import subprocess


def find_outro_start(path, tail_dur=120.0, min_black=0.5):
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path]).strip())
    ts = max(0.0, dur - tail_dur)
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-ss", str(ts), "-i", path,
        "-vf", f"blackdetect=d={min_black}:pix_th=0.10",
        "-an", "-f", "null", "-",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    blocks = []
    for m in re.finditer(
        r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)",
        p.stderr,
    ):
        s, e, d = float(m.group(1)), float(m.group(2)), float(m.group(3))
        blocks.append((ts + s, ts + e, d))
    if not blocks:
        return None, dur, 0.0
    blocks.sort(key=lambda b: b[2], reverse=True)
    abs_start, _abs_end, dur_block = blocks[0]
    return abs_start, dur, dur_block


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: find_outro.py <target.mkv> [tail_dur] [min_black]",
              file=sys.stderr)
        sys.exit(2)
    target = sys.argv[1]
    tail = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
    minb = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    cut, dur, bdur = find_outro_start(target, tail, minb)
    if cut is None:
        print(f"outro=None\tdur={dur:.3f}\tfile={target}")
    else:
        print(f"outro={cut:.3f}\tdur={dur:.3f}\tblack_block={bdur:.2f}\tfile={target}")
