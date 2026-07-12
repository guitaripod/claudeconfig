#!/usr/bin/env python3
"""qc.py <workdir> — Phase 4: numeric QC gates + defect scan on out/edit.mp4.
Frames, format, A/V drift, black frames, unexpected freezes, beat alignment,
cut-density gradient. Exit 1 if any gate fails."""
import sys, json, subprocess
import numpy as np

ROOT = sys.argv[1]
CFG = json.load(open(f"{ROOT}/project.json"))
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


def main():
    spine = json.load(open(f"{ROOT}/spine.json"))
    segs = json.load(open(f"{ROOT}/assign.json"))["segments"]
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
    print(f"[final] {x['width']}x{x['height']} {x['r_frame_rate']} {x['pix_fmt']} frames={fnf} vdur={vd} adur={ad}")
    fnf != WANT and d.append("final frames")
    abs(float(vd) - VDUR) > 0.05 and d.append("final dur")
    ad and abs(float(ad) - float(vd)) > 0.05 and d.append("A/V drift")

    bd = ff(["ffmpeg", "-hide_banner", "-i", FINAL, "-vf", "blackdetect=d=0.05:pic_th=0.98:pix_th=0.10", "-an", "-f", "null", "-"]).stderr
    blk = [l for l in bd.splitlines() if "blackdetect" in l]
    print(f"[black] intervals={len(blk)}"); blk and d.append(f"{len(blk)} black")

    hw = [(h - 0.2, h + 1.4) for h in spine["meta"]["qc"]["hero_times"]]
    fd = ff(["ffmpeg", "-hide_banner", "-i", FINAL, "-vf", "freezedetect=n=0.003:d=0.30", "-map", "0:v", "-f", "null", "-"]).stderr
    fz = []
    for l in fd.splitlines():
        if "freeze_start" in l:
            try: t = float(l.split("freeze_start:")[1].split()[0])
            except Exception: continue
            if not any(a <= t <= b for a, b in hw): fz.append(round(t, 2))
    print(f"[freeze] unexpected={len(fz)} {fz[:8]}"); fz and d.append(f"{len(fz)} freeze")

    cum, worst = 0, 0
    for s in segs: worst = max(worst, abs(cum - round(s["start"] * FPS))); cum += s["nf"]
    print(f"[beats] worst cut-vs-beat offset = {worst} frames"); worst > 2 and d.append("beat align")

    dens = {}
    for s in segs: dens.setdefault(s["tag"], []).append(s["dur"])
    print("[density] " + "  ".join(f"{t}:{len(v)}/{np.mean(v) * 1000:.0f}ms" for t, v in sorted(dens.items())))
    print("\n" + ("✅ ALL GATES PASS" if not d else f"❌ DEFECTS: {d}"))
    return 1 if d else 0


if __name__ == "__main__":
    sys.exit(main())
