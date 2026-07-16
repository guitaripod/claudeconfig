#!/usr/bin/env python3
"""contact_sheet.py <workdir> [--draft] [--n 40] [--segs] — visual-QC image builders.

Default: tile N evenly-sampled frames from out/edit.mp4 into frames/contact.png.
--segs: tile one early frame from EVERY rendered segment (seg/seg_*.mp4), labeled
with its segment index, into frames/seggrid.png — the precise way to map a defect
to a segment/clip so it can be banned via project.json "exclude_clips".
Every frame must be real footage — no black, no wipes, no bumpers, no static filler."""
import sys, json, subprocess, os, math, glob

ROOT = os.path.abspath(sys.argv[1])
CFG = json.load(open(f"{ROOT}/project.json"))
DRAFT = "--draft" in sys.argv
N = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 40
os.makedirs(f"{ROOT}/frames", exist_ok=True)


def sheet():
    dur = CFG["dur"]
    vid = f"{ROOT}/out/edit{'_draft' if DRAFT else ''}.mp4"
    out = f"{ROOT}/frames/contact.png"
    cols = 8 if N > 24 else 6
    rows = math.ceil(N / cols)
    step = dur / N
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", vid,
        "-vf", f"fps=1/{step:.3f},scale=340:191,tile={cols}x{rows}:margin=2:padding=2",
        "-frames:v", "1", out], check=True)
    print(f"contact sheet ({N} frames, {cols}x{rows}) → {out}")
    print("Read it as an image. Reject: black frames, broadcast wipes, sponsor/score bumpers,")
    print("static graphics, duplicated shots. Re-tune colorscan thresholds / motion floor if any appear.")


def seggrid():
    segs = sorted(glob.glob(f"{ROOT}/seg/seg_*.mp4"))
    assert segs, "no rendered segments — run render.py first (draft is fine)"
    tmp = f"{ROOT}/frames/segtiles"
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(f"{tmp}/*.jpg"): os.remove(f)
    tall = CFG["out_h"] > CFG["out_w"]
    sw, sh = (126, 224) if tall else (224, 126)
    for f in segs:
        idx = os.path.basename(f)[4:-4]
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f,
            "-vf", f"select=eq(n\\,4),scale={sw}:{sh},"
                   f"drawtext=text='{idx}':fontsize=34:fontcolor=yellow:box=1:boxcolor=black",
            "-frames:v", "1", "-fps_mode", "passthrough", f"{tmp}/f{idx}.jpg"], check=True)
    cols = 10
    rows = math.ceil(len(segs) / cols)
    out = f"{ROOT}/frames/seggrid.png"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-pattern_type", "glob", "-i", f"{tmp}/f*.jpg",
        "-filter_complex", f"tile={cols}x{rows}:padding=3:color=black",
        "-frames:v", "1", out], check=True)
    print(f"segment grid ({len(segs)} segs, {cols}x{rows}) → {out}")
    print("Read it as an image. For each defective index: assign.json segments[i].clip_id →")
    print('append to project.json "exclude_clips", re-run assign_clips.py + render.py --draft.')


if __name__ == "__main__":
    seggrid() if "--segs" in sys.argv else sheet()
