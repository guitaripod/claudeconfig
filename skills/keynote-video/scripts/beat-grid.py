"""Print the beat grid of an audio excerpt as the constants timing.ts needs.

usage: beat-grid.py <audio> <start_seconds> <duration_seconds> [start_bpm]

FIRST_BEAT is seconds after the excerpt start. librosa often reports half time
for fast tracks; that is fine, cuts only need a grid they can land on.
"""

import sys

import librosa
import numpy as np


def main() -> None:
    path, start, duration = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    start_bpm = float(sys.argv[4]) if len(sys.argv) > 4 else 120.0
    pad = 6.0
    offset = max(0.0, start - pad)
    y, sr = librosa.load(path, sr=22050, offset=offset, duration=duration + 2 * pad)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", start_bpm=start_bpm)
    beats = np.array(beats) + offset
    inside = beats[(beats >= start - 2) & (beats <= start + duration + 2)]
    period = float(np.mean(np.diff(inside)))
    first = (float(inside[inside >= start][0]) - start) % period
    print(f"tempo {float(np.atleast_1d(tempo)[0]):.1f} bpm (librosa)")
    print(f"BEAT_SECONDS = {period:.5f}")
    print(f"FIRST_BEAT = {first:.3f}")
    print(f"beats in excerpt: {len(inside)}")


main()
