#!/usr/bin/env python3
"""contact_sheet.py <workdir> [--draft] [--n 40] — tile N evenly-sampled frames
from out/edit.mp4 into frames/contact.png for visual QC (read it as an image).
Every frame must be real footage — no black, no wipes, no bumpers, no static filler."""
import sys, json, subprocess, os, math

ROOT = sys.argv[1]
CFG = json.load(open(f"{ROOT}/project.json"))
DRAFT = "--draft" in sys.argv
N = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 40
DUR = CFG["dur"]
VID = f"{ROOT}/out/edit{'_draft' if DRAFT else ''}.mp4"
OUT = f"{ROOT}/frames/contact.png"
os.makedirs(f"{ROOT}/frames", exist_ok=True)

cols = 8 if N > 24 else 6
rows = math.ceil(N / cols)
step = DUR / N
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", VID,
    "-vf", f"fps=1/{step:.3f},scale=340:191,tile={cols}x{rows}:margin=2:padding=2",
    "-frames:v", "1", OUT], check=True)
print(f"contact sheet ({N} frames, {cols}x{rows}) → {OUT}")
print("Read it as an image. Reject: black frames, broadcast wipes, sponsor/score bumpers,")
print("static graphics, duplicated shots. Re-tune colorscan thresholds / motion floor if any appear.")
