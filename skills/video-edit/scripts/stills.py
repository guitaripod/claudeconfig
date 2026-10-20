#!/usr/bin/env python3
"""stills.py <workdir> [--duration 8] — turn assets/ images into Ken Burns clips.

Images land in assets/ (ingest.sh copies them there). Each becomes a smooth
zoom video at src/<stem>.mp4, sized to the preset canvas, so scenes.py,
assign_clips.py and the rest of the shots path work unchanged. The motion is a
slow centre zoom; a still that needs a different move can be replaced by hand.
"""
import argparse
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preset

IMG = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.PNG")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--duration", type=float, default=8.0)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    cfg, p = preset.load(root)
    w, h, fps = cfg["out_w"], cfg["out_h"], cfg["fps"]
    os.makedirs(f"{root}/src", exist_ok=True)
    images = sorted({f for pat in IMG for f in glob.glob(f"{root}/assets/{pat}")})
    if not images:
        sys.exit("no images in assets/ — copy stills there first")
    made = 0
    for path in images:
        stem = os.path.splitext(os.path.basename(path))[0]
        out = f"{root}/src/{stem}.mp4"
        if os.path.exists(out):
            continue
        frames = int(round(a.duration * fps))
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
              f"zoompan=z='min(zoom+0.0007,1.15)':x='iw/2-(iw/zoom/2)':"
              f"y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},format=yuv420p")
        r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                            "-y", "-loop", "1", "-i", path, "-t", str(a.duration),
                            "-vf", vf, "-frames:v", str(frames), "-an",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"{stem}: {r.stderr.strip()[-300:]}")
        made += 1
        print(f"  {stem} → {a.duration:.1f}s Ken Burns")
    print(f"{made} stills → src/ ({len(images)} in assets/)")


if __name__ == "__main__":
    main()
