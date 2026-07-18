#!/usr/bin/env python3
"""extract_audio.py <workdir> <song_path_or_url> [--style classic|remaster]
   [--fps N] [--w N] [--h N] [--start 0] [--end 0] [--keep-tail] [--pitch 1.0]

--style picks the art direction and its canvas defaults (overridable with
--fps/--w/--h): classic = 1920x1080@30 teal-orange montage; remaster =
1080x1920@60 full-bleed 90deg-rotated landscape with a 4K-remaster grade and
slow-mo interpolation (the TikTok "quality edit" genre).

--pitch shifts pitch by the given ratio (e.g. 1.04 = +4%) with rubberband, tempo
unchanged — use to dodge platform Content-ID matching. Applied before analysis so
the beat grid and both WAVs stay sample-consistent.

Downloads/extracts the song, trims trailing silence, frame-aligns the timeline, and
writes sample-exact analysis (22.05k mono) + master (44.1k stereo) WAVs. Emits
project.json — the single config every other script reads. Run with the venv python.
"""
import sys, os, json, subprocess, argparse
import numpy as np
import soundfile as sf
import librosa

SR_A = 22050

GRADES = {
    # teal-orange stadium-night montage
    "classic":
        "eq=contrast=1.12:saturation=1.14:brightness=-0.02:gamma=0.96,"
        "colorbalance=rs=-0.06:gs=-0.02:bs=0.08:rm=0.02:bm=-0.02:rh=0.10:gh=0.03:bh=-0.08,"
        "curves=master='0/0 0.10/0.03 0.5/0.5 0.9/0.97 1/1',vignette=angle=PI/6",
    # AI-remaster look: clean painterly base, oversharpened detail, HDR-ish pop
    "remaster":
        "hqdn3d=1.5:1.0:2.5:2.5,unsharp=5:5:0.9:5:5:0.35,cas=0.55,"
        "eq=contrast=1.09:saturation=1.30:gamma=0.99,vibrance=intensity=0.22,"
        "curves=master='0/0 0.12/0.08 0.5/0.53 0.9/0.95 1/1'",
}
CANVAS = {"classic": (1920, 1080, 30), "remaster": (1080, 1920, 60)}


def sh(a): return subprocess.run(a, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("song")
    ap.add_argument("--style", choices=("classic", "remaster"), default="classic")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--w", type=int, default=None); ap.add_argument("--h", type=int, default=None)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=0.0, help="hard end (s); 0 = whole song")
    ap.add_argument("--keep-tail", action="store_true", help="don't trim trailing silence")
    ap.add_argument("--pitch", type=float, default=1.0,
                    help="pitch ratio, tempo preserved (1.04 = +4%%; anti-Content-ID)")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    cw, ch, cfps = CANVAS[a.style]
    a.w = a.w or cw; a.h = a.h or ch; a.fps = a.fps or cfps

    song = a.song
    if song.startswith("http"):
        out = f"{root}/song_src.%(ext)s"
        r = sh(["yt-dlp", "-f", "bestaudio", "--no-playlist", "-o", out, song])
        if r.returncode != 0:
            sys.exit("yt-dlp failed:\n" + r.stderr[-500:])
        song = subprocess.run(["bash", "-c", f"ls {root}/song_src.*"],
                              capture_output=True, text=True).stdout.split("\n")[0].strip()
    assert os.path.exists(song), f"song not found: {song}"

    if a.pitch != 1.0:
        pitched = f"{root}/song_pitched.wav"
        r = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", song,
                "-vn", "-af", f"rubberband=pitch={a.pitch}:transients=crisp",
                "-c:a", "pcm_s24le", pitched])
        if r.returncode != 0:
            sys.exit("pitch shift failed (ffmpeg needs librubberband):\n" + r.stderr[-500:])
        song = pitched
        print(f"pitch x{a.pitch} → song_pitched.wav")

    total = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", song]).stdout.strip())
    start = max(0.0, a.start)
    end = a.end if a.end > 0 else total

    # trim trailing silence: find last frame whose short-term RMS is clearly audible
    if not a.keep_tail:
        y, _ = librosa.load(song, sr=SR_A, mono=True, offset=start,
                            duration=max(end - start, 0.1))
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        tf = librosa.frames_to_time(np.arange(len(rms)), sr=SR_A, hop_length=512)
        thr = 0.06 * float(rms.max() + 1e-9)
        loud = np.where(rms > thr)[0]
        if len(loud):
            end = start + min(end - start, float(tf[loud[-1]]) + 0.4)

    dur = np.floor((end - start) * a.fps) / a.fps         # frame-aligned
    na, nm = int(round(dur * SR_A)), int(round(dur * 44100))
    ss = f"{start}"
    af_a = f"aresample={SR_A}:resampler=soxr,atrim=end_sample={na},apad=whole_len={na},asetpts=N/SR/TB"
    af_m = f"aresample=44100:resampler=soxr,atrim=end_sample={nm},apad=whole_len={nm},asetpts=N/SR/TB"
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", ss, "-i", song,
        "-t", str(dur + 1), "-vn", "-af", af_a, "-ac", "1", "-ar", str(SR_A),
        "-c:a", "pcm_s16le", f"{root}/song_22k_mono.wav"])
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", ss, "-i", song,
        "-t", str(dur + 1), "-vn", "-af", af_m, "-ac", "2", "-ar", "44100",
        "-c:a", "pcm_s24le", f"{root}/master.wav"])
    ia, im = sf.info(f"{root}/song_22k_mono.wav"), sf.info(f"{root}/master.wav")
    assert ia.frames == na and im.frames == nm, (ia.frames, na, im.frames, nm)

    cfg = {}
    if os.path.exists(f"{root}/project.json"):
        cfg = json.load(open(f"{root}/project.json"))
    grade = cfg.get("grade") if cfg.get("style") == a.style and cfg.get("grade") else GRADES[a.style]
    cfg.update({
        "root": root, "fps": a.fps, "dur": round(float(dur), 4),
        "total_frames": int(round(dur * a.fps)),
        "out_w": a.w, "out_h": a.h, "sr_analysis": SR_A,
        "audio_analysis": "song_22k_mono.wav", "audio_master": "master.wav",
        "style": a.style,
        "grade": grade,
        "hero_overrides": cfg.get("hero_overrides", []),
        "pitch": a.pitch,
    })
    json.dump(cfg, open(f"{root}/project.json", "w"), indent=1)
    print(f"style={a.style} dur={dur:.3f}s ({cfg['total_frames']} frames @ {a.fps}fps "
          f"{a.w}x{a.h}) analysis={na} master={nm} samples → project.json")


if __name__ == "__main__":
    main()
