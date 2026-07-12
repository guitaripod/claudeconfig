#!/usr/bin/env python3
"""scenes.py <workdir> — Phase 1: slice every src/*.mp4 into single-action clips
+ per-source low-res motion timelines. Writes scenes.json + motion.npz.
Run with the venv python (needs scenedetect + cv2). Optional project.json key
"catalog": {"<srcid>": ["Label", "hero_goal|goal|skills"]} for nicer labels."""
import sys, json, subprocess, glob, os
import numpy as np
from scenedetect import open_video, SceneManager, AdaptiveDetector

ROOT = sys.argv[1]
CFG = json.load(open(f"{ROOT}/project.json"))
SRC = f"{ROOT}/src"
MW, MH, MFPS = 128, 72, 10.0
CATALOG = CFG.get("catalog", {})


def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate", "-show_entries",
        "format=duration", "-of", "json", path], capture_output=True, text=True).stdout)
    s = j["streams"][0]; w, h = int(s["width"]), int(s["height"])
    num, den = s["avg_frame_rate"].split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    dur = float(j["format"].get("duration") or 0)
    return w, h, fps, dur


def motion_timeline(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
        f"fps={MFPS},scale={MW}:{MH},format=gray", "-f", "rawvideo",
        "-pix_fmt", "gray", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8); nf = len(fr) // (MW * MH)
    if nf < 2: return np.zeros(1, np.float32), np.zeros(1, np.float32)
    fr = fr[:nf * MW * MH].reshape(nf, MH, MW).astype(np.float32)
    luma = fr.mean((1, 2)) / 255.0
    diff = np.abs(np.diff(fr, axis=0)).mean((1, 2)) / 255.0
    return np.concatenate([[diff[0]], diff]), luma


def _slice(arr, s, e):
    i0 = min(int(s * MFPS), len(arr) - 1); i1 = max(int(e * MFPS), i0 + 1)
    seg = arr[i0:i1]
    return seg if len(seg) else arr[max(i0 - 1, 0):i0 + 1]


def add(scenes, sid, label, cat, s, e, mot, luma, w, h, fps):
    ms, ls = _slice(mot, s, e), _slice(luma, s, e)
    mm = float(ms.mean()) if len(ms) else 0.0; mx = float(ms.max()) if len(ms) else 0.0
    lm = float(ls.mean()) if len(ls) else 0.0
    scenes.append({"id": len(scenes), "src": sid, "label": label, "cat": cat,
        "start": round(s, 3), "end": round(e, 3), "dur": round(e - s, 3),
        "w": w, "h": h, "fps": round(fps, 3), "motion": round(mm, 5),
        "motion_max": round(mx, 5), "luma": round(lm, 4), "dark": bool(lm < 0.06)})


def main():
    files = sorted(glob.glob(f"{SRC}/*.mp4"))
    print(f"{len(files)} sources")
    scenes, motions = [], {}
    for path in files:
        sid = os.path.splitext(os.path.basename(path))[0]
        label, cat = CATALOG.get(sid, [sid, "goal"])
        try: w, h, fps, dur = probe(path)
        except Exception as e: print(f"  SKIP {sid}: {e}"); continue
        mot, luma = motion_timeline(path); motions[sid] = mot
        sm = SceneManager()
        sm.add_detector(AdaptiveDetector(adaptive_threshold=3.5, min_scene_len=int(round(fps * 0.4))))
        try:
            sm.detect_scenes(open_video(path), show_progress=False); sl = sm.get_scene_list()
        except Exception: sl = []
        kept = 0
        segs = [(a.get_seconds(), b.get_seconds()) for a, b in sl] or [(0.0, dur)]
        for s, e in segs:
            d = e - s
            if d > 12.0:                       # split uncut blobs into ~4s chunks
                t = s
                while t < e - 0.45:
                    ce = min(t + 4.0, e)
                    if ce - t >= 0.45: add(scenes, sid, label, cat, t, ce, mot, luma, w, h, fps); kept += 1
                    t += 4.0
            elif d >= 0.45:
                add(scenes, sid, label, cat, s, e, mot, luma, w, h, fps); kept += 1
        print(f"  {sid[:24]:24s} {w}x{h}@{fps:.0f} {dur:5.0f}s → {kept} clips")
    np.savez(f"{ROOT}/motion.npz", **motions)
    json.dump({"mfps": MFPS, "clips": scenes}, open(f"{ROOT}/scenes.json", "w"), indent=1)
    print(f"\n{len(scenes)} clips → scenes.json, motion.npz")


if __name__ == "__main__":
    main()
