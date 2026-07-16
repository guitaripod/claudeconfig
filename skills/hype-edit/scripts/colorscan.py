#!/usr/bin/env python3
"""colorscan.py <workdir> — Phase 1b: flag promo cards + synthetic graphics.
Adds green/graphic flags to scenes.json and writes badframes.npz (per-frame
graphic mask) so the assigner can steer in-points off wipes/bumpers/score-numbers.
This tuning is for sports broadcast footage; adjust thresholds for other domains."""
import sys, json, subprocess, glob, os
import numpy as np

ROOT = sys.argv[1]
CW, CH, CFPS = 64, 36, 5.0


def features(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
        f"fps={CFPS},scale={CW}:{CH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8); nf = len(a) // (CW * CH * 3)
    if nf < 1: return (np.zeros(1),) * 5
    a = a[:nf * CW * CH * 3].reshape(nf, CH, CW, 3).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]; mx, mn = a.max(3), a.min(3)
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    greencard = ((g > 140) & (g > r * 1.55) & (g > b * 1.55)).mean((1, 2))   # promo card
    pitch = ((g > 50) & (g < 205) & (g > r * 1.08) & (g > b * 1.12)).mean((1, 2))  # grass
    sat = ((mx - mn) / (mx + 1.0) > 0.45).mean((1, 2))
    detail = gray.std((1, 2)); bright = (gray > 210).mean((1, 2))
    white = ((mx > 200) & ((mx - mn) / (mx + 1.0) < 0.16)).mean((1, 2))
    return greencard, pitch, sat, detail, bright, white


def main():
    scenes = json.load(open(f"{ROOT}/scenes.json")); clips = scenes["clips"]
    by = {}
    for c in clips: by.setdefault(c["src"], []).append(c)
    ng, ngr, bad_masks = 0, 0, {}
    for path in sorted(glob.glob(f"{ROOT}/src/*.mp4")):
        sid = os.path.splitext(os.path.basename(path))[0]
        if sid not in by: continue
        gc, pit, sat, det, bri, wht = features(path)
        # per-frame "graphic": little pitch AND (flat OR oversaturated OR big bright logo/number),
        # a green promo card, or a white replay-card / typography overlay
        bad = ((pit < 0.10) & ((det < 20) | (sat > 0.50) | (bri > 0.20))) | (gc > 0.6) | (wht > 0.30)
        bad_masks[sid] = bad.astype(np.uint8)
        def sl(arr, s, e):
            i0, i1 = int(s * CFPS), max(int(e * CFPS), int(s * CFPS) + 1)
            seg = arr[i0:i1] if i1 <= len(arr) else arr[i0:]
            return seg if len(seg) else arr[max(i0 - 1, 0):i0 + 1]
        for c in by[sid]:
            c["green"] = round(float((sl(gc, c["start"], c["end"]) > 0.7).mean()), 3)
            c["graphic"] = bool(sl(bad, c["start"], c["end"]).mean() > 0.45
                               or (sl(wht, c["start"], c["end"]) > 0.30).mean() > 0.34)
            ng += c["green"] > 0.25; ngr += c["graphic"]
    np.savez(f"{ROOT}/badframes.npz", cfps=np.array([CFPS]), **bad_masks)
    json.dump(scenes, open(f"{ROOT}/scenes.json", "w"), indent=1)
    print(f"green promo-card clips: {ng} | graphic/bumper clips: {ngr} | badframes.npz saved")


if __name__ == "__main__":
    main()
