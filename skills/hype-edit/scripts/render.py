#!/usr/bin/env python3
"""render.py <workdir> [--draft] — Phase 3b: render each segment (grade+effects),
concat, mux the master audio. Auto-detects NVENC (falls back to libx264).
Writes out/edit.mp4 (or out/edit_draft.mp4). Reads project.json."""
import sys, json, subprocess, os
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(sys.argv[1])
CFG = json.load(open(f"{ROOT}/project.json"))
SEG = f"{ROOT}/seg"
DRAFT = "--draft" in sys.argv
FPS = CFG["fps"]
FW, FH = CFG["out_w"], CFG["out_h"]
OW, OH = (FW // 2, FH // 2) if DRAFT else (FW, FH)
SW, SH = int(round(OW * 1.06 / 2)) * 2, int(round(OH * 1.06 / 2)) * 2
WORKERS = min(6, (os.cpu_count() or 4))

_enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
NVENC = "h264_nvenc" in _enc
STYLE = CFG.get("style", "classic")
OSW, OSH = int(round(OW * 1.06 / 2)) * 2, int(round(OH * 1.06 / 2)) * 2
if STYLE == "remaster":
    GRADE = (f"transpose=1,scale={OW}:{OH}:force_original_aspect_ratio=increase,"
             f"crop={OW}:{OH}," + CFG["grade"])
else:
    GRADE = (f"scale={OSW}:{OSH}:force_original_aspect_ratio=increase,crop={OW}:{OH}," + CFG["grade"])
MCI = f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"


def zoom(a, d):
    return (f"scale=w='{OW}*(1+{a}*min(t\\,{d})/{d})':h='{OH}*(1+{a}*min(t\\,{d})/{d})':eval=frame,"
            f"crop={OW}:{OH}:(in_w-{OW})/2:(in_h-{OH})/2")


def shake(a, tau):   # crop evaluates t per-frame natively — NO eval= option on crop
    return (f"scale={SW}:{SH},crop={OW}:{OH}:"
            f"x='(in_w-{OW})/2+{a}*sin(2*PI*11*t)*exp(-t/{tau})':"
            f"y='(in_h-{OH})/2+{a}*cos(2*PI*13*t)*exp(-t/{tau})'")


def slowmo(speed):
    """Slow the graded stream to output tempo, then synthesize the missing frames:
    motion-compensated interpolation on the full render (the butter), plain fps
    duplication on drafts (minterpolate is far too slow for a direction check)."""
    p = []
    if speed < 0.999: p.append(f"setpts=PTS/{speed}")
    p.append(f"fps={FPS}" if DRAFT else MCI)
    return p


def vf(s):
    d, F, eff = s["dur"], s["impact"], s["effects"]; p = []
    if s.get("crop"): p.append(f"crop={s['crop']}")
    p.append(GRADE); p.append("setpts=PTS-STARTPTS")
    if STYLE == "remaster":
        p += slowmo(s.get("speed", 1.0))
        p.append(zoom(0.03, d))
        if "beatflash" in eff: p.append("eq=brightness='if(lt(t\\,0.04)\\,0.35\\,0)':eval=frame")
        if "dropflash" in eff:
            p.append("eq=brightness='if(lt(t\\,0.06)\\,0.6\\,if(lt(t\\,0.18)\\,0.6*(1-(t-0.06)/0.12)\\,0))':eval=frame")
        p.append(f"setsar=1,fps={FPS},format=yuv420p")
        return ",".join(p)
    if "freezeflash" in eff:
        Fc = min(max(F, 0.35), max(d - 0.25, 0.35))
        p += [f"trim=0:{Fc:.3f},setpts=PTS-STARTPTS",
              f"tpad=stop_mode=clone:stop_duration={d - Fc + 0.7:.3f}", zoom(0.12, d),
              f"eq=brightness='if(between(t\\,{Fc:.3f}\\,{Fc + 0.06:.3f})\\,0.85*(1-(t-{Fc:.3f})/0.06)\\,0)':eval=frame"]
        if "shake" in eff: p.append(shake(16, 0.30))
    else:
        if "punch" in eff: p.append(zoom(0.08, d))
        else: p.append(zoom(0.06, d))
        if "beatflash" in eff: p.append("eq=brightness='if(lt(t\\,0.04)\\,0.5\\,0)':eval=frame")
        if "dropflash" in eff:
            p.append("eq=brightness='if(lt(t\\,0.06)\\,0.85\\,if(lt(t\\,0.18)\\,0.85*(1-(t-0.06)/0.12)\\,0))':eval=frame")
        if "rgbsplit" in eff: p.append("rgbashift=rh=4:bh=-4")
        if "shake" in eff: p.append(shake(13, 0.26))
    p.append(f"setsar=1,fps={FPS},format=yuv420p")
    return ",".join(p)


def enc(preset_draft=False):
    cq, crf = ("17", "16") if STYLE == "remaster" else ("20", "18")
    if NVENC:
        return ["-c:v", "h264_nvenc", "-preset", "p1" if preset_draft else "p6", "-tune", "hq",
                "-rc", "vbr", "-cq", "30" if preset_draft else cq, "-b:v", "0",
                "-maxrate", "90M" if STYLE == "remaster" else "60M", "-bufsize", "180M",
                "-spatial-aq", "1", "-temporal-aq", "1"]
    return ["-c:v", "libx264", "-preset", "veryfast" if preset_draft else "medium",
            "-crf", "26" if preset_draft else crf]


def render_one(s):
    out = f"{SEG}/seg_{s['i']:03d}.mp4"; src = f"{ROOT}/src/{s['src']}.mp4"
    inp = round(s["dur"] * s.get("speed", 1.0) + 1.2, 3)
    base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(s["in_tc"]),
            "-t", str(inp), "-i", src, "-vf", vf(s), "-frames:v", str(s["nf"]), "-fps_mode", "cfr",
            *enc(DRAFT), "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", str(FPS * 2),
            "-bf", "3", "-video_track_timescale", str(FPS * 1000), "-an", out]
    r = subprocess.run(base, capture_output=True, text=True)
    if r.returncode == 0: return s["i"], True, "ok"
    sm = ",".join(slowmo(s.get("speed", 1.0))) + "," if STYLE == "remaster" else ""
    vf2 = f"{('crop=' + s['crop'] + ',') if s.get('crop') else ''}{GRADE},setpts=PTS-STARTPTS,{sm}setsar=1,fps={FPS},format=yuv420p"
    fb = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(s["in_tc"]),
          "-t", str(inp), "-i", src, "-vf", vf2, "-frames:v", str(s["nf"]), "-fps_mode", "cfr",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
          "-video_track_timescale", str(FPS * 1000), "-an", out]
    r2 = subprocess.run(fb, capture_output=True, text=True)
    return (s["i"], True, "fallback") if r2.returncode == 0 else (s["i"], False, r.stderr.strip()[-160:])


def nbf(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip()
    return int(o) if o.isdigit() else -1


def main():
    segs = json.load(open(f"{ROOT}/assign.json"))["segments"]
    want = sum(s["nf"] for s in segs); os.makedirs(SEG, exist_ok=True)
    print(f"render {len(segs)} segs {OW}x{OH} {STYLE} {'DRAFT' if DRAFT else 'FULL'} "
          f"enc={'nvenc' if NVENC else 'libx264'} x{WORKERS}")
    fails, fb = [], []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, ok, m in ex.map(render_one, segs):
            if not ok: fails.append((i, m))
            elif m == "fallback": fb.append(i)
    if fb: print(f"  {len(fb)} CPU-fallback segments: {fb[:12]}")
    if fails: print(f"  !! FAILED {len(fails)}: {fails[:8]}"); return 1
    tot = sum(nbf(f"{SEG}/seg_{s['i']:03d}.mp4") for s in segs)
    print(f"Σframes={tot} (want {want})" + (" ✓" if tot == want else " !! MISMATCH"))
    with open(f"{ROOT}/work/concat.txt", "w") as f:
        for s in segs: f.write(f"file '{SEG}/seg_{s['i']:03d}.mp4'\n")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
        "-safe", "0", "-i", f"{ROOT}/work/concat.txt", "-c", "copy",
        "-video_track_timescale", str(FPS * 1000), f"{ROOT}/work/video.mp4"], check=True)
    out = f"{ROOT}/out/edit{'_draft' if DRAFT else ''}.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f"{ROOT}/work/video.mp4",
        "-i", f"{ROOT}/{CFG['audio_master']}", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", out], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
    print(f"\n✅ {out}  dur={dur}s  size={os.path.getsize(out) / 1048576:.1f}MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
