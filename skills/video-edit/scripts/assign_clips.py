#!/usr/bin/env python3
"""assign_clips.py <workdir> — Phase 3: map clips to timeline segments.
Zero reuse, source diversity, quality floor, graphic-aware in-points, effect plan,
motion-centered framing for the output aspect. Preset decides the effect plan,
retime speeds and whether framing is rotated. Writes assign.json.
project.json keys it honors:
  "hero_overrides": [{"src","in_tc","impact"[,"crop"]}...] (hero-time order) — hand-pinned
    marquee moments; empty = motion-driven heroes.
  "exclude_clips": [clip_id...] — banned from the pool (visual-review rejects, or clips
    already used by a sibling edit in a multi-video batch).
  "motion_floor": 0.045 — the quality floor on clip motion_max (default from the
    preset's scan.motion_floor). Sports footage earns the default; a domain whose whole
    frame is synthetic (a UI, a menu, an interface demo) reads an order of magnitude
    lower and needs it dropped or the pool comes back empty.
  "ignore_graphic": false — colorscan's graphic/bumper flag is a sports heuristic (little
    pitch + flat or oversaturated). Set true when the subject IS a rendered interface, or
    every clip is banned as a bumper."""
import sys, json, subprocess, glob, os
from concurrent.futures import ThreadPoolExecutor
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preset
import timeline
import effect_plans

ROOT = os.path.abspath(sys.argv[1])
CFG, P = preset.load(ROOT)
FPS = CFG["fps"]
RENDER = preset.require(P, "render")
RETIME = RENDER["mode"] == "retime"
SPEED = RENDER.get("speed", {})
SPEED_CYCLE = RENDER.get("speed_cycle", {})
PLAN = effect_plans.get(preset.require(P, "effects", "plan"))
NOREPEAT, MARGIN = 8.0, 0.5


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


def frame_for_output(assign, face_tracks=None, ffps=0.0, face_on=False):
    if RENDER.get("rotate"):
        print("rotated preset: full-bleed landscape, no per-segment crop framing")
        return
    ar = CFG["out_w"] / CFG["out_h"]

    def center(sid, t, d):
        if not (face_on and face_tracks is not None and sid in face_tracks.files):
            return None
        tr = face_tracks[sid]
        i0, i1 = int(t * ffps), max(int((t + d) * ffps), int(t * ffps) + 1)
        seg = tr[i0:i1]
        if not len(seg) or seg[:, 0].sum() <= 0:
            return None
        w = seg[:, 0]
        return (float((seg[:, 1] * w).sum() / w.sum()),
                float((seg[:, 2] * w).sum() / w.sum()))

    todo = [a for a in assign if not a["_manual_crop"] and not a["crop"]
            and a["_w"] and a["_h"] and abs(a["_w"] / a["_h"] / ar - 1) > 0.05]
    if not todo: return
    def one(a):
        src_ar = a["_w"] / a["_h"]
        fc = center(a["src"], a["in_tc"], a["dur"])
        if src_ar > ar:
            ww = int(round(a["_h"] * ar / 2)) * 2
            x = (int(round(fc[0] * a["_w"] - ww / 2)) if fc else
                 motion_window_x(a["src"], a["in_tc"], a["dur"], a["_w"], a["_h"], ww))
            a["crop"] = f"{ww}:{a['_h']}:{max(0, min(x, a['_w'] - ww))}:0"
        else:
            hh = int(round(a["_w"] / ar / 2)) * 2
            y = (int(round(fc[1] * a["_h"] - hh / 2)) if fc else (a["_h"] - hh) // 2)
            a["crop"] = f"{a['_w']}:{hh}:0:{max(0, min(y, a['_h'] - hh))}"
    with ThreadPoolExecutor(8) as ex: list(ex.map(one, todo))
    mode = "face" if face_on else "motion"
    print(f"output framing: {mode}-centered crop on {len(todo)} segments")


def main():
    tl = timeline.load(ROOT)
    scenes = json.load(open(f"{ROOT}/scenes.json"))
    mot = np.load(f"{ROOT}/motion.npz")
    badf = np.load(f"{ROOT}/badframes.npz"); BFPS = float(badf["cfps"][0])
    HF = {k[5:]: badf[k] for k in badf.files if k.startswith("hash_")}
    MFPS = scenes["mfps"]; clips = scenes["clips"]; cut = tl["cutlist"]
    drop_t = {round(d["time"], 2) for d in tl["drops"]}
    db_set = {round(b, 2) for b in tl["downbeats"]}
    OV = CFG.get("hero_overrides", [])

    srcs = sorted(glob.glob(f"{ROOT}/src/*.mp4"))
    sdur = {os.path.splitext(os.path.basename(p))[0]: probe_dur(p) for p in srcs}
    dims = {c["src"]: (c["w"], c["h"]) for c in clips}
    scrop = {s: detect_crop(f"{ROOT}/src/{s}.mp4", d) for s, d in sdur.items()}
    for c in clips: c["srcdur"] = sdur.get(c["src"], 0)
    EXC = set(CFG.get("exclude_clips", []))
    EXC_SRC = set(CFG.get("exclude_sources", []))
    SCAN = preset.require(P, "scan")
    FLOOR = float(CFG.get("motion_floor", SCAN.get("motion_floor", 0.045)))
    GRAPHIC_OK = bool(CFG.get("ignore_graphic", False))
    COVER = bool(CFG.get("cover_sources", False))
    SRC_GAP = float((P.get("pacing") or {}).get("source_gap_s", 0.0))
    DUPE = int((P.get("pacing") or {}).get("dupe_distance", 0))
    SUBJECT = CFG.get("subject") or SCAN.get("subject", "none")
    MINFACE = float(CFG.get("min_face_frac", SCAN.get("min_face_frac", 0.0)))
    faces, FFPS = None, 0.0
    if SUBJECT in ("face", "auto"):
        fp = f"{ROOT}/faces.npz"
        if not os.path.exists(fp):
            if SUBJECT == "face":
                raise SystemExit("preset asks for a face subject but faces.npz is missing — "
                                 "run faces.py after scenes.py")
            print("auto subject: no faces.npz — face pass off"); SUBJECT = "none"
        else:
            faces = np.load(fp); FFPS = float(faces["cfps"][0])
    base_usable = [c for c in clips if not c["dark"] and c.get("green", 0) <= 0.25
                   and (GRAPHIC_OK or not c.get("graphic", False))
                   and c["motion_max"] >= FLOOR and c["srcdur"] > 0
                   and c["id"] not in EXC and c["src"] not in EXC_SRC]
    FACE = SUBJECT in ("face", "auto") and faces is not None
    if FACE:
        with_face = [c for c in base_usable if c.get("face_max", 0) >= MINFACE]
        if SUBJECT == "auto" and len(with_face) < 0.35 * max(len(base_usable), 1):
            print(f"auto subject: {len(with_face)}/{len(base_usable)} clips have a face — "
                  "face gate off")
            FACE, usable = False, base_usable
        else:
            if not with_face:
                raise SystemExit(f"no clips with a face >= {MINFACE} of frame area — "
                                 "lower min_face_frac or rerun faces.py")
            usable = with_face
            print(f"subject: face >= {MINFACE} on {len(with_face)}/{len(base_usable)} clips")
    else:
        usable = base_usable
    if EXC: print(f"exclude_clips: {len(EXC)} banned")
    if EXC_SRC: print(f"exclude_sources: {len(EXC_SRC)} banned")
    if FLOOR != 0.045 or GRAPHIC_OK:
        print(f"quality floor: motion_max>={FLOOR}"
              + (" graphic flag ignored" if GRAPHIC_OK else ""))
    print(f"usable pool: {len(usable)} clips / {len(set(c['src'] for c in usable))} sources")
    if not usable:
        raise SystemExit(
            "no usable clips. Lower project.json \"motion_floor\" (synthetic/interface footage "
            "reads an order of magnitude lower than sports), set \"domain\" for the scan "
            f"profile, or clear {len(EXC)} exclude_clips.")
    hero_pool = sorted([c for c in usable if c["dur"] >= 0.9], key=lambda c: -c["motion_max"])
    high = sorted(usable, key=lambda c: -c["motion"])
    med = float(np.median([x["motion"] for x in usable]))
    mid = sorted(usable, key=lambda c: abs(c["motion"] - med))
    low = sorted(usable, key=lambda c: c["motion"])
    fps_map = {c["src"]: c["fps"] for c in clips}; lab_map = {c["src"]: c["label"] for c in clips}
    lu, uc, su, src_lu, hused, recent = {}, {}, {}, {}, set(), []
    hashes = []

    def mslice(sid, a, b):
        arr = mot[sid] if sid in mot.files else np.zeros(1)
        i0, i1 = int(a * MFPS), max(int(b * MFPS), int(a * MFPS) + 1)
        return arr[i0:i1] if i1 <= len(arr) else arr[i0:]

    def face_mean(sid, t, d):
        if not (FACE and sid in faces.files):
            return 0.0
        tr = faces[sid]
        i0, i1 = int(t * FFPS), max(int((t + d) * FFPS), int(t * FFPS) + 1)
        seg = tr[i0:i1]
        return float(seg[:, 0].mean()) if len(seg) else 0.0

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
            def fscore(t):
                if not (FACE and c["src"] in faces.files):
                    return 0.0, 0.0
                tr = faces[c["src"]]
                f0, f1 = int(t * FFPS), max(int((t + d) * FFPS), int(t * FFPS) + 1)
                seg = tr[f0:f1]; ar = seg[:, 0]
                if not len(seg) or ar.sum() <= 0:
                    return 0.0, 0.0
                return float(ar.mean()), float(seg[:, 1].std() + seg[:, 2].std())
            for t in np.arange(s, hi, 1.0 / MFPS):
                i0 = int(t * MFPS)
                if i0 + w <= len(a):
                    fa, st = fscore(t)
                    sc.append((bf(t) > 0.02, -fa, st,
                               -float(a[i0:i0 + w].sum()), float(t)))
            sc.sort(); picks = []
            for _, _, _, _, t in sc:
                if all(abs(t - p) > d * 0.8 for p in picks): picks.append(t)
                if len(picks) > nth: break
            it = picks[min(nth, len(picks) - 1)] if picks else s
        seg = mslice(c["src"], it, it + d)
        return round(it, 3), round(min(float(np.argmax(seg)) / MFPS if len(seg) else d * 0.5, d), 3)

    def pick(pool, out_t, d, want_long, exclude=(), avoid=()):
        def lok(c):
            if c["srcdur"] < d + 0.1:
                return False
            return (c["dur"] + MARGIN) >= d or not want_long
        def src_ok(c):
            return SRC_GAP <= 0 or src_lu.get(c["src"], -1e9) <= out_t - SRC_GAP
        def hash_ok(c):
            if DUPE <= 0 or not hashes:
                return True
            arr = HF.get(c["src"])
            if arr is None or not len(arr):
                h = c.get("hash")
                return h is None or all((h ^ x).bit_count() > DUPE for x in hashes[-8:])
            i0 = int(c["start"] * BFPS)
            i1 = max(int(c["end"] * BFPS), i0 + 1)
            idx = np.unique(np.linspace(i0, min(i1 - 1, len(arr) - 1), 5).astype(int))
            for k in idx:
                h = int.from_bytes(arr[k].tobytes(), "big")
                if any((h ^ x).bit_count() <= DUPE for x in hashes[-8:]):
                    return False
            return True
        free = lambda c: lu.get(c["id"], -99) <= out_t - NOREPEAT and src_ok(c)
        fresh = [c for c in pool if c["id"] not in exclude and uc.get(c["id"], 0) == 0
                 and lok(c) and src_ok(c) and hash_ok(c)]
        if fresh:
            base = [c for c in fresh if su.get(c["src"], 0) == 0] if COVER else fresh
            if not base: base = fresh
            div = [c for c in base if c["src"] not in avoid]; return (div or base)[0]
        cand = [c for c in pool if c["id"] not in exclude and free(c) and lok(c) and hash_ok(c)]
        if cand:
            base = [c for c in cand if su.get(c["src"], 0) == 0] if COVER else cand
            if not base: base = cand
            div = [c for c in base if c["src"] not in avoid] or base
            return min(div, key=lambda c: uc.get(c["id"], 0))
        cand = [c for c in pool if lok(c)]
        if not cand:
            raise SystemExit(
                f"no clip can fill a {d:.2f}s cut: every source window is shorter. "
                "Lower the preset's shot/beat length or ingest longer sources.")
        return min(cand, key=lambda c: (uc.get(c["id"], 0), lu.get(c["id"], -99)))

    assign, hidx, hero_srcs = [], 0, set()
    for c in cut:
        i, tag, d, ot = c["i"], c["tag"], c["dur"], c["start"]
        nf = round(c["end"] * FPS) - round(c["start"] * FPS)
        entry = round(c["start"], 2) in drop_t; db = round(c["start"], 2) in db_set
        skey = "hero" if c["hero"] else tag
        cyc = SPEED_CYCLE.get(skey) or SPEED_CYCLE.get("*")
        speed = (float(cyc[i % len(cyc)]) if cyc
                 else float(SPEED.get(skey, 1.0)))
        if not (RETIME or SPEED or SPEED_CYCLE):
            speed = 1.0
        de = d * speed
        manual, prim = None, False
        hint = c.get("src")
        pin = c.get("in_tc")
        hinted = [x for x in usable if x["src"] == hint] if hint else []
        if hinted:
            clip = pick(hinted, ot, de, False, avoid=recent)
            if pin is not None:
                manual = (float(pin), 0.5)
        elif c["hero"]:
            prim = bool(drop_t) and abs(c["start"] - min(drop_t, key=lambda x: abs(x - c["start"]))) < 0.6 and d > 1.0
            ov = OV[hidx] if hidx < len(OV) else None; hidx += 1
            if ov:
                clip = {"src": ov["src"], "id": -1 - hidx, "fps": fps_map.get(ov["src"], FPS),
                        "label": lab_map.get(ov["src"], ov["src"]), "crop_ov": ov.get("crop")}
                manual = (round(ov["in_tc"], 3), round(ov.get("impact", 0.6), 3))
            else:
                clip = pick(hero_pool, ot, de, True, exclude=hused, avoid=hero_srcs)
                hused.add(clip["id"])
            hero_srcs.add(clip["src"])
        elif tag == "low":
            clip = pick(low, ot, de, True, avoid=recent)
        elif tag == "build":
            clip = pick(mid, ot, de, False, avoid=recent)
        elif tag == "body":
            clip = pick(mid, ot, de, False, avoid=recent)
        else:
            clip = pick(high, ot, de, False, avoid=recent)
        eff = PLAN(i, c["hero"], prim, entry, db, tag)
        recent = (recent + [clip["src"]])[-3:]
        su[clip["src"]] = su.get(clip["src"], 0) + 1
        src_lu[clip["src"]] = ot
        if "hash" in clip:
            hashes = (hashes + [clip["hash"]])[-8:]
        nth = uc.get(clip["id"], 0); uc[clip["id"]] = nth + 1; lu[clip["id"]] = ot
        win = de + MARGIN if clip.get("srcdur", 0) >= de + MARGIN else de
        it, imp = manual if manual else inpoint(clip, win, nth)
        assign.append({"i": i, "start": round(c["start"], 4), "dur": round(d, 4), "nf": nf,
            "tag": tag, "hero": c["hero"], "src": clip["src"], "clip_id": clip["id"],
            "in_tc": it, "impact": imp, "speed": speed,
            "face": round(face_mean(clip["src"], it, de), 4),
            "crop": clip.get("crop_ov") or scrop.get(clip["src"]),
            "effects": eff, "label": clip["label"],
            "_w": clip.get("w") or dims.get(clip["src"], (0, 0))[0],
            "_h": clip.get("h") or dims.get(clip["src"], (0, 0))[1],
            "_manual_crop": bool(clip.get("crop_ov"))})

    frame_for_output(assign, faces, FFPS, FACE)
    for a in assign: a.pop("_w", None); a.pop("_h", None); a.pop("_manual_crop", None)

    tot = sum(a["nf"] for a in assign)
    exp = round(cut[-1]["end"] * FPS) - round(cut[0]["start"] * FPS)
    assert tot == exp, f"{tot} != {exp}"
    reuse = len(assign) - len(set(a["clip_id"] for a in assign))
    adj = sum(1 for a, b in zip(assign, assign[1:]) if a["src"] == b["src"])
    json.dump({"fps": FPS, "face_gate": FACE, "segments": assign}, open(f"{ROOT}/assign.json", "w"), indent=1)
    print(f"{len(assign)} segments Σframes={tot} reuse={reuse} consecutive-same-source={adj}")
    if COVER:
        allsrc = {c["src"] for c in clips}; cov = {a["src"] for a in assign}
        print(f"cover_sources: {len(cov)}/{len(allsrc)} sources")
        if allsrc - cov: print("  missing:", sorted(allsrc - cov))
    print("heroes:", [(a["i"], a["label"], a["effects"]) for a in assign if a["hero"]])


if __name__ == "__main__":
    main()
