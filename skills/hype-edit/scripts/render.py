#!/usr/bin/env python3
"""render.py <workdir> [--draft] — Phase 3b: render each segment (grade+effects),
concat, mux the master audio. Auto-detects NVENC (falls back to libx264).
Writes out/edit.mp4 (or out/edit_draft.mp4). Reads project.json."""
import sys, json, subprocess, os
from concurrent.futures import ThreadPoolExecutor

ROOT = sys.argv[1]
CFG = json.load(open(f"{ROOT}/project.json"))
SEG = f"{ROOT}/seg"
DRAFT = "--draft" in sys.argv
FPS = CFG["fps"]
FW, FH = CFG["out_w"], CFG["out_h"]
OW, OH = (FW // 2, FH // 2) if DRAFT else (FW, FH)
# frame_overscan >1 = tighter center crop (1.06 default landscape; ~1.18–1.25 for vertical)
OVER = float(CFG.get("frame_overscan", 1.06))
SW, SH = int(round(OW * OVER / 2)) * 2, int(round(OH * OVER / 2)) * 2
WORKERS = min(6, (os.cpu_count() or 4))

_enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
NVENC = "h264_nvenc" in _enc
OSW, OSH = int(round(OW * OVER / 2)) * 2, int(round(OH * OVER / 2)) * 2
# Optional vertical bias: crop_y_bias 0=center, + = lower (good for pitch-level players)
YBIAS = float(CFG.get("crop_y_bias", 0.0))
VERTICAL = OH > OW


def grade_chain(sx=0.5):
    """Fill-frame scale then crop so subject_x (0–1) lands at horizontal center."""
    sx = max(0.05, min(0.95, float(sx)))
    # x such that subject is centered: clamp to valid crop range
    xexpr = f"max(0\\,min(in_w-{OW}\\,{sx}*in_w-{OW}/2))"
    yexpr = (f"(in_h-{OH})/2+{YBIAS}*(in_h-{OH})/2" if abs(YBIAS) > 1e-6
             else f"(in_h-{OH})/2")
    return (f"scale={OSW}:{OSH}:force_original_aspect_ratio=increase,"
            f"crop={OW}:{OH}:{xexpr}:{yexpr}," + CFG["grade"])


def zoom(a, d):
    return (f"scale=w='{OW}*(1+{a}*min(t\\,{d})/{d})':h='{OH}*(1+{a}*min(t\\,{d})/{d})':eval=frame,"
            f"crop={OW}:{OH}:(in_w-{OW})/2:(in_h-{OH})/2")


def stomp(a, tau=0.09):
    # Front-loaded slam: max zoom on the cut (the beat), settles fast.
    return (f"scale=w='{OW}*(1+{a}*exp(-t/{tau}))':h='{OH}*(1+{a}*exp(-t/{tau}))':eval=frame,"
            f"crop={OW}:{OH}:(in_w-{OW})/2:(in_h-{OH})/2")


def shake(a, tau):   # crop evaluates t per-frame natively — NO eval= option on crop
    return (f"scale={SW}:{SH},crop={OW}:{OH}:"
            f"x='(in_w-{OW})/2+{a}*sin(2*PI*11*t)*exp(-t/{tau})':"
            f"y='(in_h-{OH})/2+{a}*cos(2*PI*13*t)*exp(-t/{tau})'")


def whip(amp=36, dur=0.055):
    # Directional smear into the cut — reads as a whip pan landing on the beat.
    sw = int(round(OW * 1.12 / 2)) * 2
    sh = int(round(OH * 1.12 / 2)) * 2
    return (f"scale={sw}:{sh},"
            f"crop={OW}:{OH}:"
            f"x='(in_w-{OW})/2+if(lt(t\\,{dur})\\,{amp}*(1-t/{dur})\\,0)':"
            f"y='(in_h-{OH})/2',"
            f"gblur=sigma=10:enable='lt(t\\,{dur})'")


def vf(s):
    d, F, eff = s["dur"], s["impact"], s["effects"]; p = []
    if s.get("crop"): p.append(f"crop={s['crop']}")
    sx = s.get("subject_x", 0.5)
    p.append(grade_chain(sx)); p.append("setpts=PTS-STARTPTS")
    # Vertical needs gentler zoom or the subject gets crushed out of frame
    z_hi, z_mid, z_lo = (0.08, 0.06, 0.03) if VERTICAL else (0.14, 0.09, 0.05)
    z_stomp = 0.09 if VERTICAL else 0.14
    if "freezeflash" in eff:
        Fc = min(max(F, 0.35), max(d - 0.25, 0.35))
        p += [f"trim=0:{Fc:.3f},setpts=PTS-STARTPTS",
              f"tpad=stop_mode=clone:stop_duration={d - Fc + 0.7:.3f}", zoom(z_hi, d),
              f"eq=brightness='if(between(t\\,{Fc:.3f}\\,{Fc + 0.07:.3f})\\,0.95*(1-(t-{Fc:.3f})/0.07)\\,0)':eval=frame"]
        if "shake" in eff: p.append(shake(12 if VERTICAL else 18, 0.28))
    else:
        if "stomp" in eff: p.append(stomp(z_stomp if "dropflash" in eff else z_stomp * 0.85))
        elif "punch" in eff: p.append(zoom(z_mid, d))
        else: p.append(zoom(z_lo, d))
        if "whip" in eff: p.append(whip(28 if VERTICAL else 40 if "dropflash" in eff else 30))
        if "dropflash" in eff:
            p.append("eq=brightness='if(lt(t\\,0.04)\\,0.78\\,if(lt(t\\,0.14)\\,0.78*(1-(t-0.04)/0.10)\\,0))':eval=frame")
        elif "beatflash" in eff:
            p.append("eq=brightness='if(lt(t\\,0.03)\\,0.58\\,if(lt(t\\,0.07)\\,0.58*(1-(t-0.03)/0.04)\\,0))':eval=frame")
        if "rgbsplit" in eff:
            rh = 7 if ("dropflash" in eff or "stomp" in eff) else 4
            p.append(f"rgbashift=rh={rh}:bh={-rh}")
        if "shake" in eff:
            p.append(shake(10 if VERTICAL else 16 if "dropflash" in eff else 12, 0.22))
    p.append(f"setsar=1,fps={FPS},format=yuv420p")
    return ",".join(p)


def enc(preset_draft=False):
    if NVENC:
        return ["-c:v", "h264_nvenc", "-preset", "p1" if preset_draft else "p6", "-tune", "hq",
                "-rc", "vbr", "-cq", "30" if preset_draft else "20", "-b:v", "0",
                "-maxrate", "60M", "-bufsize", "120M", "-spatial-aq", "1", "-temporal-aq", "1"]
    return ["-c:v", "libx264", "-preset", "veryfast" if preset_draft else "medium",
            "-crf", "26" if preset_draft else "18"]


def render_one(s):
    out = f"{SEG}/seg_{s['i']:03d}.mp4"; src = f"{ROOT}/src/{s['src']}.mp4"
    inp = round(s["dur"] + 1.2, 3)
    base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(s["in_tc"]),
            "-t", str(inp), "-i", src, "-vf", vf(s), "-frames:v", str(s["nf"]), "-fps_mode", "cfr",
            *enc(DRAFT), "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", str(FPS * 2),
            "-bf", "3", "-video_track_timescale", str(FPS * 1000), "-an", out]
    r = subprocess.run(base, capture_output=True, text=True)
    if r.returncode == 0: return s["i"], True, "ok"
    vf2 = f"{('crop=' + s['crop'] + ',') if s.get('crop') else ''}{GRADE},setpts=PTS-STARTPTS,setsar=1,fps={FPS},format=yuv420p"
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
    print(f"render {len(segs)} segs {OW}x{OH} {'DRAFT' if DRAFT else 'FULL'} "
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
