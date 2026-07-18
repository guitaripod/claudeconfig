#!/usr/bin/env python3
"""contact_sheet.py <workdir> [--draft] [--n 40] [--segs] — visual-QC image builders.

Default: tile N evenly-sampled frames from out/edit.mp4 into frames/contact.png.
--segs: tile labeled frames from EVERY rendered segment (seg/seg_*.mp4) into
frames/seggrid.png — one early frame per short segment, start/mid/end (a/b/c)
for holds ≥1s so a subject drifting out of a vertical crop mid-segment is
visible, not just its first instant. The precise way to map a defect to a
segment/clip so it can be banned via project.json "exclude_clips".
Every frame must be real footage — no black, no wipes, no bumpers, no static filler."""
import sys, json, subprocess, os, math, glob

ROOT = os.path.abspath(sys.argv[1])
CFG = json.load(open(f"{ROOT}/project.json"))
DRAFT = "--draft" in sys.argv
N = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 40
ROT = "transpose=2," if CFG.get("style") == "remaster" else ""
os.makedirs(f"{ROOT}/frames", exist_ok=True)


def sheet():
    dur = CFG["dur"]
    vid = f"{ROOT}/out/edit{'_draft' if DRAFT else ''}.mp4"
    out = f"{ROOT}/frames/contact.png"
    cols = 8 if N > 24 else 6
    rows = math.ceil(N / cols)
    step = dur / N
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", vid,
        "-vf", f"fps=1/{step:.3f},{ROT}scale=340:191,tile={cols}x{rows}:margin=2:padding=2",
        "-frames:v", "1", out], check=True)
    print(f"contact sheet ({N} frames, {cols}x{rows}) → {out}")
    print("Read it as an image. Reject: black frames, broadcast wipes, sponsor/score bumpers,")
    print("static graphics, duplicated shots. Re-tune colorscan thresholds / motion floor if any appear.")


def seggrid():
    segs = sorted(glob.glob(f"{ROOT}/seg/seg_*.mp4"))
    assert segs, "no rendered segments — run render.py first (draft is fine)"
    nf = {s["i"]: s["nf"] for s in json.load(open(f"{ROOT}/assign.json"))["segments"]}
    tmp = f"{ROOT}/frames/segtiles"
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(f"{tmp}/*.jpg"): os.remove(f)
    tall = CFG["out_h"] > CFG["out_w"] and not ROT
    sw, sh = (126, 224) if tall else (224, 126)
    tiles = 0
    for f in segs:
        idx = os.path.basename(f)[4:-4]
        n = nf.get(int(idx), 12)
        picks = [(min(4, n - 1), "")] if n < 30 else [
            (min(4, n - 1), "a"), (n // 2, "b"), (max(n - 2, 0), "c")]
        for k, sub in picks:
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f,
                "-vf", f"select=eq(n\\,{k}),{ROT}scale={sw}:{sh},"
                       f"drawtext=text='{idx}{sub}':fontsize=34:fontcolor=yellow:box=1:boxcolor=black",
                "-frames:v", "1", "-fps_mode", "passthrough", f"{tmp}/f{idx}{sub}.jpg"], check=True)
            tiles += 1
    cols = 9
    rows = math.ceil(tiles / cols)
    out = f"{ROOT}/frames/seggrid.png"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-pattern_type", "glob", "-i", f"{tmp}/f*.jpg",
        "-filter_complex", f"tile={cols}x{rows}:padding=3:color=black",
        "-frames:v", "1", out], check=True)
    print(f"segment grid ({len(segs)} segs, {tiles} frames, {cols}x{rows}) → {out}")
    print("Read it as an image. a/b/c = start/mid/end of every hold ≥1s — the subject must be")
    print("in frame in EVERY tile, not just the first. For each defective index:")
    print('assign.json segments[i].clip_id → append to project.json "exclude_clips"')
    print("(or hand-patch that segment's crop), re-run assign_clips.py + render.py --draft.")


if __name__ == "__main__":
    seggrid() if "--segs" in sys.argv else sheet()
