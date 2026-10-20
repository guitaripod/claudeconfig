#!/usr/bin/env python3
"""extract_audio.py <workdir> <song_path_or_url> --preset <name>
   [--fps N] [--w N] [--h N] [--start 0] [--end 0] [--keep-tail] [--pitch 1.0]

The song producer's entry point: downloads/extracts the song, trims trailing
silence, frame-aligns the timeline, writes sample-exact analysis (22.05k mono)
and master (44.1k stereo) WAVs, and writes project.json naming the preset. The
preset supplies the canvas and the starting grade; --fps/--w/--h override it.

--pitch shifts pitch by the given ratio (e.g. 1.04 = +4%) with rubberband, tempo
unchanged — use to dodge platform Content-ID matching. Applied before analysis so
the beat grid and both WAVs stay sample-consistent.

Run with the venv python (needs librosa/soundfile).
"""
import sys, os, json, subprocess, argparse, random
import numpy as np
import soundfile as sf
import librosa

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preset
from look import LOOKS, CHARACTER

SR_A = 22050
VIDEO_EXT = (".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".ts")


def sh(a): return subprocess.run(a, capture_output=True, text=True)


def audio_source(path, root):
    """librosa cannot decode most video containers; extract the audio first."""
    if not path.lower().endswith(VIDEO_EXT):
        return path
    out = f"{root}/song_from_video.wav"
    r = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", path,
            "-vn", "-c:a", "pcm_s24le", out])
    if r.returncode != 0:
        sys.exit("could not extract audio from the video:\n" + r.stderr[-500:])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("song")
    ap.add_argument("--preset", required=True)
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--w", type=int, default=None); ap.add_argument("--h", type=int, default=None)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=0.0, help="hard end (s); 0 = whole song")
    ap.add_argument("--keep-tail", action="store_true", help="don't trim trailing silence")
    ap.add_argument("--pitch", type=float, default=1.0,
                    help="pitch ratio, tempo preserved (1.04 = +4%%; anti-Content-ID)")
    ap.add_argument("--loop", type=int, default=1,
                    help="repeat the (silence-trimmed) track N times; duration scales with N")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    ppath = os.path.join(preset.PRESETS, f"{a.preset}.json")
    if not os.path.exists(ppath):
        raise preset.PresetError(f'unknown preset "{a.preset}".\n' + preset.list_text())
    p = preset.read(ppath)
    a.w = a.w or p["canvas"]["w"]; a.h = a.h or p["canvas"]["h"]; a.fps = a.fps or p["canvas"]["fps"]

    song = a.song
    if song.startswith("http"):
        out = f"{root}/song_src.%(ext)s"
        r = sh(["yt-dlp", "-f", "bestaudio", "--no-playlist", "-o", out, song])
        if r.returncode != 0:
            sys.exit("yt-dlp failed:\n" + r.stderr[-500:])
        song = subprocess.run(["bash", "-c", f"ls {root}/song_src.*"],
                              capture_output=True, text=True).stdout.split("\n")[0].strip()
    assert os.path.exists(song), f"song not found: {song}"
    song = audio_source(song, root)

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

    if a.loop > 1:
        base, looped = f"{root}/song_loop_base.wav", f"{root}/song_loop.wav"
        seg = max(end - start, 0.1)
        r = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{start:.6f}", "-t", f"{seg:.6f}", "-i", song,
                "-vn", "-c:a", "pcm_s24le", base])
        if r.returncode != 0:
            sys.exit("could not cut the loop segment:\n" + r.stderr[-500:])
        r = sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-stream_loop", str(a.loop - 1), "-i", base,
                "-c:a", "pcm_s24le", looped])
        if r.returncode != 0:
            sys.exit("could not loop the track:\n" + r.stderr[-500:])
        song, start, end = looped, 0.0, seg * a.loop
        print(f"loop x{a.loop} → {seg:.3f}s × {a.loop} = {end:.3f}s")

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
    # A preset pins its grade or asks for a roll. A fresh workdir under a
    # "random" preset opens on a different look each time; an authored look
    # (look.py set/shuffle) always wins.
    look = cfg.get("look")
    if not look:
        spec = p["grade"]
        base = spec.get("base") or random.choice([k for k in LOOKS if k != "neutral"])
        look = {"base": base, "sections": {}, "sources": {}, "segments": {}, "drift": 0.0}
    if p["render"].get("tech"):
        look["tech"] = p["render"]["tech"]
    cfg.update({
        "root": root, "fps": a.fps, "dur": round(float(dur), 4),
        "total_frames": int(round(dur * a.fps)),
        "out_w": a.w, "out_h": a.h, "sr_analysis": SR_A,
        "audio_analysis": "song_22k_mono.wav", "audio_master": "master.wav",
        "preset": p["name"],
        "grade": cfg.get("grade", ""),
        "look": look,
        "hero_overrides": cfg.get("hero_overrides", []),
        "pitch": a.pitch,
    })
    cfg.pop("style", None)
    json.dump(cfg, open(f"{root}/project.json", "w"), indent=1)
    print(f"preset={p['name']} dur={dur:.3f}s ({cfg['total_frames']} frames @ {a.fps}fps "
          f"{a.w}x{a.h}) analysis={na} master={nm} samples → project.json")
    b = look.get("base")
    print(f"look={b} — {CHARACTER.get(b, 'custom chain')}\n"
          f"  Change it after seeing this edit's footage:\n"
          f"    python3 $S/look.py {root} preview      # every look on one real frame\n"
          f"    python3 $S/look.py {root} set base=<name> peak=<name> drift=0.3")


if __name__ == "__main__":
    main()
