#!/usr/bin/env python3
"""assign_clips.py <workdir> — Phase 3a: map clips to cutlist segments.
Zero reuse, source diversity, quality floor, graphic-aware in-points, effect plan,
motion-centered framing for vertical output. Writes assign.json.
project.json keys it honors:
  "hero_overrides": [{"src","in_tc","impact"[,"crop"]}...] (hero-time order) — hand-pinned
    marquee moments; empty = motion-driven heroes.
  "exclude_clips": [clip_id...] — banned from the pool (visual-review rejects, or clips
    already used by a sibling edit in a multi-video batch)."""
import sys, json, subprocess, glob, os
from concurrent.futures import ThreadPoolExecutor
import numpy as np

ROOT = os.path.abspath(sys.argv[1])
CFG = json.load(open(f"{ROOT}/project.json"))
FPS = CFG["fps"]
STYLE = CFG.get("style", "classic")
NOREPEAT, MARGIN = 8.0, 0.5
SPEED = {"hero": 0.5, "drop": 0.65, "peak": 0.65, "build": 0.75, "low": 0.85}


def probe_dur(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip()
    return float(o) if o else 0.0


def detect_crop(p, dur):
    votes = {}
    for fr in (0.2, 0.5, 0.8):
        o = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(round(dur * fr, 1)), "-i", p,
            "-vf", "cropdetect=limit=24:round=2:reset=0", "-frames:v", "60", "-an",
            "-f", "null", "-"], capture_output=True, text=True).stderr
        for ln in o.splitlines():
            if "crop=" in ln:
                c = ln.split("crop=")[1].split()[0]; votes[c] = votes.get(c, 0) + 1
    if not votes: return None
    c = max(votes, key=votes.get); w, h, x, y = (int(v) for v in c.split(":"))
    return c if (x > 4 or y > 4) else None


def grab_gray(src, t, gw, gh):
    """Fast-seek (-ss before -i) EXACTLY like render.py — on some downloads fast and
    accurate seek land on different content, so framing must be computed under the
    same seek semantics the renderer will use."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(t, 0):.3f}", "-i",
        f"{ROOT}/src/{src}.mp4", "-frames:v", "1", "-vf", f"scale={gw}:{gh}",
        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    if len(raw) < gw * gh: return None
    return np.frombuffer(raw[:gw * gh], np.uint8).reshape(gh, gw).astype(np.float32)


def motion_window_x(src, it, d, w, h, ww):
    """Pick the x-offset of a ww-wide crop window over the local motion peak, so
    vertical output keeps the action in frame. Each frame pair is first aligned by
    the dominant horizontal shift (1D cross-correlation of column profiles): a
    tracking camera keeps the subject frame-static while the background streams,
    so uncompensated energy would frame the background instead of the player.
    Known miss: full-frame close-ups can frame a moving limb instead of the face —
    catch those on the --segs grid and hand-patch the segment crop."""
    gw, gh = 192, 108
    fr = [grab_gray(src, it + k * d / 3.0, gw, gh) for k in range(4)]
    fr = [f for f in fr if f is not None]
    if len(fr) < 2: return (w - ww) // 2
    en = np.zeros(gw, np.float32)
    for a, b in zip(fr, fr[1:]):
        pa, pb = a.mean(0), b.mean(0)
        pa, pb = pa - pa.mean(), pb - pb.mean()
        cor = []
        for sh in range(-24, 25):
            v = (pa[sh:] * pb[:gw - sh]).sum() if sh >= 0 else (pa[:gw + sh] * pb[-sh:]).sum()
            cor.append(v)
        sh = int(np.argmax(cor)) - 24
        if sh > 0: da = np.abs(a[:, sh:] - b[:, :-sh]); lo, hi = sh, gw
        elif sh < 0: da = np.abs(a[:, :sh] - b[:, -sh:]); lo, hi = 0, gw + sh
        else: da = np.abs(a - b); lo, hi = 0, gw
        e = np.zeros(gw, np.float32); e[lo:hi] = da.sum(0); en += e
    en = np.maximum(en - np.median(en), 0)
    if en.sum() < 1e-6: return (w - ww) // 2
    en *= 0.9 + 0.1 * np.hanning(gw)
    win = max(int(round(ww / w * gw)), 4)
    sums = np.convolve(en, np.ones(win, np.float32), "valid")
    x = int(round(int(np.argmax(sums)) / gw * w))
    return max(0, min(x, w - ww))


def frame_segments_for_vertical(assign):
    if STYLE == "remaster":
        print("remaster: full-bleed rotated landscape — no vertical crop framing")
        return
    ar = CFG["out_w"] / CFG["out_h"]
    todo = [a for a in assign if not a["_manual_crop"] and not a["crop"]
            and a["_w"] and a["_h"] and a["_w"] / a["_h"] > ar * 1.05]
    if not todo: return
    def one(a):
        ww = int(round(a["_h"] * ar / 2)) * 2
        x = motion_window_x(a["src"], a["in_tc"], a["dur"], a["_w"], a["_h"], ww)
        a["crop"] = f"{ww}:{a['_h']}:{x}:0"
    with ThreadPoolExecutor(8) as ex: list(ex.map(one, todo))
    print(f"vertical framing: motion-centered crop on {len(todo)} segments")


def main():
    spine = json.load(open(f"{ROOT}/spine.json"))
    scenes = json.load(open(f"{ROOT}/scenes.json"))
    mot = np.load(f"{ROOT}/motion.npz")
    badf = np.load(f"{ROOT}/badframes.npz"); BFPS = float(badf["cfps"][0])
    MFPS = scenes["mfps"]; clips = scenes["clips"]; cut = spine["cutlist"]
    drop_t = {round(d["time"], 2) for d in spine["drops"]}
    db_set = {round(b, 2) for b in spine["downbeats"]}
    OV = CFG.get("hero_overrides", [])

    srcs = sorted(glob.glob(f"{ROOT}/src/*.mp4"))
    sdur = {os.path.splitext(os.path.basename(p))[0]: probe_dur(p) for p in srcs}
    dims = {c["src"]: (c["w"], c["h"]) for c in clips}
    scrop = {s: detect_crop(f"{ROOT}/src/{s}.mp4", d) for s, d in sdur.items()}
    for c in clips: c["srcdur"] = sdur.get(c["src"], 0)
    EXC = set(CFG.get("exclude_clips", []))
    usable = [c for c in clips if not c["dark"] and c.get("green", 0) <= 0.25
              and not c.get("graphic", False) and c["motion_max"] >= 0.045 and c["srcdur"] > 0
              and c["id"] not in EXC]
    if EXC: print(f"exclude_clips: {len(EXC)} banned")
    print(f"usable pool: {len(usable)} clips / {len(set(c['src'] for c in usable))} sources")
    hero_pool = sorted([c for c in usable if c["dur"] >= 0.9], key=lambda c: -c["motion_max"])
    high = sorted(usable, key=lambda c: -c["motion"])
    med = float(np.median([x["motion"] for x in usable]))
    mid = sorted(usable, key=lambda c: abs(c["motion"] - med))
    low = sorted(usable, key=lambda c: c["motion"])
    fps_map = {c["src"]: c["fps"] for c in clips}; lab_map = {c["src"]: c["label"] for c in clips}
    lu, uc, hused, recent = {}, {}, set(), []

    def mslice(sid, a, b):
        arr = mot[sid] if sid in mot.files else np.zeros(1)
        i0, i1 = int(a * MFPS), max(int(b * MFPS), int(a * MFPS) + 1)
        return arr[i0:i1] if i1 <= len(arr) else arr[i0:]

    def inpoint(c, d, nth=0):
        s, se = c["start"], min(c["end"] + MARGIN, c["srcdur"]); hi = max(se - d, s)
        if hi <= s + 1e-3:
            it = max(0.0, min(s, c["srcdur"] - d))
        else:
            a = mot[c["src"]] if c["src"] in mot.files else np.zeros(1)
            bad = badf[c["src"]] if c["src"] in badf.files else np.zeros(1, np.uint8)
            w = max(int(d * MFPS), 1)
            def bf(t):
                j0, j1 = int(t * BFPS), max(int((t + d) * BFPS), int(t * BFPS) + 1)
                seg = bad[j0:j1]; return float(seg.mean()) if len(seg) else 1.0
            sc = []
            for t in np.arange(s, hi, 1.0 / MFPS):
                i0 = int(t * MFPS)
                if i0 + w <= len(a): sc.append((bf(t) > 0.02, -float(a[i0:i0 + w].sum()), float(t)))
            sc.sort(); picks = []
            for _, _, t in sc:
                if all(abs(t - p) > d * 0.8 for p in picks): picks.append(t)
                if len(picks) > nth: break
            it = picks[min(nth, len(picks) - 1)] if picks else s
        seg = mslice(c["src"], it, it + d)
        return round(it, 3), round(min(float(np.argmax(seg)) / MFPS if len(seg) else d * 0.5, d), 3)

    def pick(pool, out_t, d, want_long, exclude=(), avoid=()):
        lok = lambda c: (c["dur"] + MARGIN) >= d
        free = lambda c: lu.get(c["id"], -99) <= out_t - NOREPEAT
        fresh = [c for c in pool if c["id"] not in exclude and uc.get(c["id"], 0) == 0
                 and (not want_long or lok(c))]
        if fresh:
            div = [c for c in fresh if c["src"] not in avoid]; return (div or fresh)[0]
        cand = [c for c in pool if c["id"] not in exclude and free(c) and (not want_long or lok(c))]
        if cand:
            div = [c for c in cand if c["src"] not in avoid] or cand
            return min(div, key=lambda c: uc.get(c["id"], 0))
        cand = [c for c in pool if lok(c)] or pool
        return min(cand, key=lambda c: (uc.get(c["id"], 0), lu.get(c["id"], -99)))

    assign, hidx = [], 0
    for c in cut:
        i, tag, d, ot = c["i"], c["tag"], c["dur"], c["start"]
        nf = round(c["end"] * FPS) - round(c["start"] * FPS)
        entry = round(c["start"], 2) in drop_t; db = round(c["start"], 2) in db_set
        speed = SPEED["hero" if c["hero"] else tag] if STYLE == "remaster" else 1.0
        de = d * speed
        eff, manual = [], None
        if c["hero"]:
            prim = abs(c["start"] - min(drop_t, key=lambda x: abs(x - c["start"]))) < 0.6 and d > 1.0
            ov = OV[hidx] if hidx < len(OV) else None; hidx += 1
            if ov:
                clip = {"src": ov["src"], "id": -1 - hidx, "fps": fps_map.get(ov["src"], FPS),
                        "label": lab_map.get(ov["src"], ov["src"]), "crop_ov": ov.get("crop")}
                manual = (round(ov["in_tc"], 3), round(ov.get("impact", 0.6), 3))
            else:
                clip = pick(hero_pool, ot, de, True, exclude=hused); hused.add(clip["id"])
            eff = ["freezeflash", "shake"] if prim else ["punch", "shake", "rgbsplit"]
        elif tag == "low":
            clip = pick(low, ot, de, True, avoid=recent); eff = ["punch"] if i == 0 else []
        elif tag == "build":
            clip = pick(mid, ot, de, False, avoid=recent)
            eff = ["punch", "beatflash"] if (db and i % 4 == 0) else (["punch"] if i % 2 == 0 else [])
        else:
            clip = pick(high, ot, de, False, avoid=recent)
            if entry: eff = ["dropflash", "shake", "punch"]
            elif db:
                eff = ["punch", "shake"] if i % 2 == 0 else ["punch", "beatflash"]
                if tag == "drop" and clip["motion_max"] > 0.15 and i % 6 == 0: eff = [eff[0], "rgbsplit"]
            else: eff = ["punch"] if (tag == "drop" or i % 2 == 0) else []
        if STYLE == "remaster":
            if c["hero"]: eff = ["dropflash"] if prim else ["beatflash"]
            elif entry: eff = ["dropflash"]
            elif db and i % 4 == 0: eff = ["beatflash"]
            else: eff = []
        elif not c["hero"]:
            eff = ["punch", "dropflash" if db else "beatflash"]
            if entry or i % 3 == 0: eff.append("shake")
            if i % 3 == 1: eff.append("rgbsplit")
            if i == 0: eff = ["punch", "dropflash", "shake"]
        recent = (recent + [clip["src"]])[-3:]
        nth = uc.get(clip["id"], 0); uc[clip["id"]] = nth + 1; lu[clip["id"]] = ot
        it, imp = manual if manual else inpoint(clip, de + MARGIN, nth)
        assign.append({"i": i, "start": round(c["start"], 4), "dur": round(d, 4), "nf": nf,
            "tag": tag, "hero": c["hero"], "src": clip["src"], "clip_id": clip["id"],
            "in_tc": it, "impact": imp, "speed": speed,
            "crop": clip.get("crop_ov") or scrop.get(clip["src"]),
            "effects": eff, "label": clip["label"],
            "_w": clip.get("w") or dims.get(clip["src"], (0, 0))[0],
            "_h": clip.get("h") or dims.get(clip["src"], (0, 0))[1],
            "_manual_crop": bool(clip.get("crop_ov"))})

    frame_segments_for_vertical(assign)
    for a in assign: a.pop("_w", None); a.pop("_h", None); a.pop("_manual_crop", None)

    tot = sum(a["nf"] for a in assign)
    exp = round(cut[-1]["end"] * FPS) - round(cut[0]["start"] * FPS)
    assert tot == exp, f"{tot} != {exp}"
    reuse = len(assign) - len(set(a["clip_id"] for a in assign))
    adj = sum(1 for a, b in zip(assign, assign[1:]) if a["src"] == b["src"])
    json.dump({"fps": FPS, "segments": assign}, open(f"{ROOT}/assign.json", "w"), indent=1)
    print(f"{len(assign)} segments Σframes={tot} reuse={reuse} consecutive-same-source={adj}")
    print("heroes:", [(a["i"], a["label"], a["effects"]) for a in assign if a["hero"]])


if __name__ == "__main__":
    main()
