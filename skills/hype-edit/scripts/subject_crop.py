#!/usr/bin/env python3
"""subject_crop.py <workdir> — estimate horizontal subject position per assign
segment (0–1), write subject_x into assign.json. Tuned for football: prefer
tall non-pitch blobs (players) over grass / empty stands."""
import sys, json, os
import numpy as np
import cv2

ROOT = sys.argv[1]
CFG = json.load(open(f"{ROOT}/project.json"))
ASS = json.load(open(f"{ROOT}/assign.json"))


def grab(path, t):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
    ok, fr = cap.read()
    cap.release()
    return fr if ok else None


def subject_x(frame):
    """Return 0–1 horizontal subject center, or 0.5 if unsure."""
    if frame is None:
        return 0.5
    h, w = frame.shape[:2]
    sc = 480 / max(w, 1)
    small = cv2.resize(frame, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    pitch = cv2.inRange(hsv, (32, 35, 35), (95, 255, 255))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    fg = (pitch == 0) & (gray > 28) & (gray < 245)
    # ignore stands/sky, boards, and extreme side ad rails
    fg[: int(sh * 0.10), :] = False
    fg[int(sh * 0.92) :, :] = False
    edge = max(4, sw // 18)
    fg[:, :edge] = False
    fg[:, sw - edge :] = False
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 11))
    fg_u8 = cv2.morphologyEx((fg.astype(np.uint8) * 255), cv2.MORPH_OPEN, k)
    fg_u8 = cv2.morphologyEx(fg_u8, cv2.MORPH_CLOSE, k)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(fg_u8, connectivity=8)
    best, best_score = None, 0.0
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if area < (sw * sh) * 0.003 or area > (sw * sh) * 0.50:
            continue
        aspect = bh / max(bw, 1)
        if aspect < 0.6 and area < (sw * sh) * 0.025:
            continue
        cx, cy = cents[i]
        # prefer middle-vertical and not-too-edge horizontally
        vpref = max(0.2, 1.0 - abs((cy / sh) - 0.50) * 1.3)
        hpref = max(0.25, 1.0 - abs((cx / sw) - 0.50) * 0.9)
        ascore = min(aspect, 2.8) / 2.8
        score = float(area) * vpref * hpref * (0.4 + 0.6 * ascore)
        if score > best_score:
            best_score = score
            best = float(cx / sw)
    if best is not None and best_score > (sw * sh) * 0.004:
        # soft pull toward center so we don't over-pan to a weak side blob
        best = 0.72 * best + 0.28 * 0.5
        return float(np.clip(best, 0.12, 0.88))
    col = fg_u8.astype(np.float32).sum(axis=0)
    if col.max() < 1:
        return 0.5
    win = max(11, sw // 22)
    col = np.convolve(col, np.ones(win, np.float32) / win, mode="same")
    # center prior on columns
    xs = np.arange(sw, dtype=np.float32)
    prior = 1.0 - 0.55 * np.abs(xs / sw - 0.5) * 2
    col = col * prior
    peak = int(np.argmax(col))
    lo, hi = max(0, peak - win * 2), min(sw, peak + win * 2)
    wcol = np.zeros(sw, np.float32)
    wcol[lo:hi] = col[lo:hi]
    if wcol.sum() < 1:
        return 0.5
    cx = float((wcol * xs).sum() / wcol.sum())
    cx = 0.7 * (cx / sw) + 0.3 * 0.5
    return float(np.clip(cx, 0.12, 0.88))


def main():
    segs = ASS["segments"]
    cache = {}
    out_dir = f"{ROOT}/frames/subject"
    os.makedirs(out_dir, exist_ok=True)
    for s in segs:
        src = f"{ROOT}/src/{s['src']}.mp4"
        t = float(s["in_tc"]) + min(float(s.get("impact") or 0.25), float(s["dur"]) * 0.45)
        key = (s["src"], round(t, 2))
        if key not in cache:
            fr = grab(src, t)
            cache[key] = subject_x(fr)
            if fr is not None:
                # debug: draw subject line
                h, w = fr.shape[:2]
                x = int(cache[key] * w)
                vis = fr.copy()
                cv2.line(vis, (x, 0), (x, h), (0, 255, 255), 3)
                cv2.putText(vis, f"i={s['i']} x={cache[key]:.2f}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                cv2.imwrite(f"{out_dir}/seg_{s['i']:03d}.jpg",
                            cv2.resize(vis, (640, int(640 * h / w))))
        s["subject_x"] = round(cache[key], 3)
        print(f"seg {s['i']:02d} {s['src'][:12]:12s} @{t:7.2f}s  subject_x={s['subject_x']:.3f}")
    json.dump(ASS, open(f"{ROOT}/assign.json", "w"), indent=1)
    xs = [s["subject_x"] for s in segs]
    print(f"\nwrote subject_x for {len(segs)} segs  mean={np.mean(xs):.3f} "
          f"off-center={sum(1 for x in xs if abs(x-0.5)>0.12)}")


if __name__ == "__main__":
    main()
