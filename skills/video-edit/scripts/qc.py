#!/usr/bin/env python3
"""qc.py <workdir> — Phase 5: numeric gates + defect scan on out/edit.mp4.

Which gates apply is the preset's call: an edit is judged against the direction
it declared, never a universal house standard. Structural gates (frame totals,
format, duration) always run; beat alignment only exists for a beat-driven
timeline, and density only when the preset claims it.

Exit 1 if any enabled gate fails.
"""
import sys, os, json, subprocess
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preset
import timeline

ROOT = sys.argv[1]
CFG, P = preset.load(ROOT)
GATES = preset.require(P, "gates")
TL = timeline.load(ROOT)
FPS, FW, FH = CFG["fps"], CFG["out_w"], CFG["out_h"]
FINAL = f"{ROOT}/out/edit.mp4"


def ff(a): return subprocess.run(a, capture_output=True, text=True)
def nbf(p):
    o = ff(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
            "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", p]).stdout.strip()
    return int(o) if o.isdigit() else -1
def si(p):
    return json.loads(ff(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,r_frame_rate,pix_fmt", "-of", "json", p]).stdout)["streams"][0]
def on(key): return GATES.get(key) is not None and GATES.get(key) is not False


def main():
    A = json.load(open(f"{ROOT}/assign.json"))
    segs = A["segments"]
    FACE_GATE = A.get("face_gate", True)
    WANT = sum(s["nf"] for s in segs); VDUR = round(WANT / FPS, 3); rate = f"{FPS}/1"
    d = []

    tot, mis, bf = 0, [], []
    for s in segs:
        p = f"{ROOT}/seg/seg_{s['i']:03d}.mp4"; f = nbf(p); tot += f
        if f != s["nf"]: mis.append((s["i"], f, s["nf"]))
        x = si(p)
        if not (x["width"] == FW and x["height"] == FH and x["r_frame_rate"] == rate and x["pix_fmt"] == "yuv420p"):
            bf.append((s["i"], x["width"], x["height"], x["r_frame_rate"], x["pix_fmt"]))
    print(f"[frames] Σ={tot} want={WANT} mismatched={len(mis)} {mis[:6]}")
    print(f"[format] non-conforming={len(bf)} {bf[:6]}")
    tot != WANT and d.append("frame total")
    mis and d.append(f"{len(mis)} seg frame-count")
    bf and d.append(f"{len(bf)} seg format")

    x = si(FINAL); fnf = nbf(FINAL)
    vd = ff(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", FINAL]).stdout.strip()
    ad = ff(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", FINAL]).stdout.strip()
    print(f"[final] {x['width']}x{x['height']} {x['r_frame_rate']} {x['pix_fmt']} frames={fnf} vdur={vd} adur={ad or 'none'}")
    fnf != WANT and d.append("final frames")
    abs(float(vd) - VDUR) > 0.05 and d.append("final dur")
    if on("av_drift"):
        ad and abs(float(ad) - float(vd)) > 0.05 and d.append("A/V drift")

    if on("black"):
        bd = ff(["ffmpeg", "-hide_banner", "-i", FINAL, "-vf", "blackdetect=d=0.05:pic_th=0.98:pix_th=0.10", "-an", "-f", "null", "-"]).stderr
        blk = [l for l in bd.splitlines() if "blackdetect" in l]
        print(f"[black] intervals={len(blk)}"); blk and d.append(f"{len(blk)} black")

    if on("freeze"):
        hw = [(h - 0.2, h + 1.4) for h in TL["meta"]["qc"].get("hero_times", [])]
        fd = ff(["ffmpeg", "-hide_banner", "-i", FINAL, "-vf", "freezedetect=n=0.003:d=0.30", "-map", "0:v", "-f", "null", "-"]).stderr
        fz = []
        for l in fd.splitlines():
            if "freeze_start" in l:
                try: t = float(l.split("freeze_start:")[1].split()[0])
                except Exception: continue
                if not any(a <= t <= b for a, b in hw): fz.append(round(t, 2))
        print(f"[freeze] unexpected={len(fz)} {fz[:8]}"); fz and d.append(f"{len(fz)} freeze")

    # Exposure: a hard grade can clip a bright shot to white (or crush a dark one)
    # in a way no black/freeze gate catches. Beat flashes are deliberate white
    # hits, so the head of every segment is exempt, as are hero freezes.
    if on("exposure_max"):
        seg = json.load(open(f"{ROOT}/assign.json"))["segments"]
        # One-frame tolerance at the head: assign.json stores intended float starts,
        # but rendered frames land on exact frame indices, so a flash can straddle
        # the boundary and read as blown a few ms before its segment nominally begins.
        flash = [(x["start"] - 1.5 / FPS, x["start"] + 0.2) for x in seg]
        hw = [(h - 0.2, h + 1.4) for h in TL["meta"]["qc"].get("hero_times", [])]
        ex = ff(["ffmpeg", "-hide_banner", "-i", FINAL, "-an", "-vf",
                 "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                 "-f", "null", "-"]).stdout
        t, blown, crushed = 0.0, [], []
        for l in ex.splitlines():
            l = l.strip()
            if "pts_time:" in l:
                try: t = float(l.split("pts_time:")[1].split()[0])
                except Exception: pass
            elif "YAVG=" in l:
                try: y = float(l.split("YAVG=")[1])
                except Exception: continue
                if any(a <= t <= b for a, b in flash) or any(a <= t <= b for a, b in hw):
                    continue
                if y >= 247: blown.append(round(t, 2))
                elif y <= 10: crushed.append(round(t, 2))
        limit = int(GATES["exposure_max"])
        print(f"[exposure] blown={len(blown)} {blown[:6]} crushed={len(crushed)} {crushed[:6]} limit={limit}")
        if len(blown) > limit: d.append(f"{len(blown)} blown frames")
        if len(crushed) > limit: d.append(f"{len(crushed)} crushed frames")

    beats = TL.get("beats") or []
    if beats and GATES.get("beat_offset_max") is not None:
        worst = 0; cum = 0
        for s in segs:
            worst = max(worst, abs(cum - round(s["start"] * FPS))); cum += s["nf"]
        limit = int(GATES["beat_offset_max"])
        print(f"[beats] worst cut-vs-beat offset = {worst} frames (limit {limit})")
        worst > limit and d.append("beat align")
    elif GATES.get("beat_offset_max") is not None:
        print("[beats] timeline has no beat grid — gate skipped")

    dens = {}
    for s in segs: dens.setdefault(s["tag"], []).append(s["dur"])
    print("[density] " + "  ".join(f"{t}:{len(v)}/{np.mean(v) * 1000:.0f}ms" for t, v in sorted(dens.items())))
    if GATES.get("density") and "drop" in dens:
        rate = {t: len(v) / max(sum(v), 1e-6) for t, v in dens.items()}
        others = max((r for t, r in rate.items() if t != "drop"), default=0.0)
        print(f"[density] cuts/s drop={rate['drop']:.2f} others_max={others:.2f}")
        floor = others * 0.9
        print(f"[density] drop floor {floor:.2f} (90% of others)")
        rate["drop"] < floor and d.append("density in drops")

    scan = preset.require(P, "scan")
    if scan.get("subject") in ("face", "auto") and FACE_GATE and any("face" in s for s in segs):
        floor = float(scan.get("min_face_frac", 0.0))
        low = [s["i"] for s in segs if s.get("face", 0) < floor]
        print(f"[subject] below face floor {floor}: {len(low)} {low[:10]}")
        if GATES.get("subject") and low:
            d.append(f"{len(low)} segments without a subject")

    print("\n" + ("✅ ALL GATES PASS" if not d else f"❌ DEFECTS: {d}"))
    return 1 if d else 0


if __name__ == "__main__":
    sys.exit(main())
