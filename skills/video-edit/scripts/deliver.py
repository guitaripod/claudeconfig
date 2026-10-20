#!/usr/bin/env python3
"""deliver.py <workdir> [--name slug] — turn the master into the preset's deliverable.

Reads preset.deliver:
  master  -> out/edit.mp4 is the deliverable.
  tiktok  -> out/<slug>_vertical.mp4. A portrait master (native or rotated build) is
             the deliverable; a landscape master is rotated 90deg and scaled to the
             delivery canvas (default 1080x2340), never cropped to a portrait
             composition.

Taildrop and the caption stay in the hype-edit skill: publishing is personal,
shaping the file is not.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preset

HERE = os.path.dirname(os.path.abspath(__file__))


def nvenc():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                         capture_output=True, text=True).stdout
    return "h264_nvenc" in out


def probe(path):
    j = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", path],
        capture_output=True, text=True).stdout)
    s = j["streams"][0]
    return int(s["width"]), int(s["height"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--name", help="output slug (default: workdir name)")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    cfg, p = preset.load(root)
    master = f"{root}/out/edit.mp4"
    if not os.path.exists(master):
        sys.exit("no out/edit.mp4 — render first")
    slug = a.name or os.path.basename(root.rstrip("/"))
    action = p.get("deliver", "master")

    if action == "master":
        print(master)
        return 0
    if action != "tiktok":
        sys.exit(f'unknown deliver action "{action}" (master | tiktok)')

    out = f"{root}/out/{slug}_vertical.mp4"
    w0, h0 = probe(master)
    if h0 >= w0:
        shutil.copy2(master, out)
        print(f"{out}\n(master is already portrait {w0}x{h0} — not rotated)")
        return 0

    d = p.get("delivery", {})
    w = int(d.get("canvas", {}).get("w", 1080))
    h = int(d.get("canvas", {}).get("h", 2340))
    bitrate = d.get("bitrate", "18M")
    vf = f"transpose=1,scale=-2:{h},crop={w}:{h}"
    enc = (["-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr",
            "-cq", "19", "-b:v", "0", "-maxrate", bitrate, "-bufsize", "2M"]
           if nvenc() else ["-c:v", "libx264", "-preset", "medium", "-crf", "18"])
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", master, "-vf", vf, *enc,
                        "-pix_fmt", "yuv420p", "-c:a", "copy", out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr.strip()[-400:])
    print(f"{out}\n({vf})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
