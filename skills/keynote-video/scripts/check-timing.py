"""Verify a render: cut transitions land on beats and nothing freezes.

usage: check-timing.py <video.mp4> <music.wav> <cut_frame> [<cut_frame> ...]
"""

import itertools
import subprocess
import sys

import librosa
import numpy as np

FPS = 30


def frame_diffs(video: str) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video, "-vf", "scale=96:54,format=gray", "-f", "rawvideo", "-"],
        capture_output=True,
    ).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, 54, 96).astype(np.float32)
    return np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))


def main() -> None:
    video, music = sys.argv[1], sys.argv[2]
    cuts = [int(c) for c in sys.argv[3:]]
    diffs = frame_diffs(video)
    y, sr = librosa.load(music, sr=22050)
    _, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", start_bpm=140)
    beats = np.array(beats)
    print(f"frames {len(diffs) + 1}")
    for cut in cuts:
        window = diffs[cut - 2 : cut + 20]
        error_ms = 1000 * float(np.min(np.abs(beats - cut / FPS)))
        print(f"cut {cut}: motion peak at +{int(np.argmax(window)) - 2}f, nearest beat {error_ms:.0f} ms")
    still_run = max((len(list(g)) for k, g in itertools.groupby(diffs < 0.02) if k), default=0)
    print(f"longest still run: {still_run} frames")


main()
