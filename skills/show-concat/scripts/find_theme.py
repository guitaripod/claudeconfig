#!/usr/bin/env python3
"""
Locate a known theme song clip inside a target video file.

Strategy: log-magnitude mel-spectrogram of the reference is slid across the
log-mag mel-spectrogram of the target's first N seconds; we report the
hop position with the highest normalized correlation.  This is robust to
mastering / encoder differences that defeat raw PCM cross-correlation.

Pure numpy. No scipy/librosa.
"""
import sys
import subprocess
import numpy as np

SR = 16000
N_FFT = 2048
HOP = 512                # ~31 ms / 32 ms windows at 16 kHz, ~31 frames/sec
N_MELS = 64
F_MIN = 50.0
F_MAX = 7500.0


def hz_to_mel(f):
    return 2595.0 * np.log10(1.0 + f / 700.0)


def mel_to_hz(m):
    return 700.0 * (10.0 ** (m / 2595.0) - 1.0)


def mel_filterbank(sr=SR, n_fft=N_FFT, n_mels=N_MELS, fmin=F_MIN, fmax=F_MAX):
    mels = np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), n_mels + 2)
    hz = mel_to_hz(mels)
    bin_freqs = np.linspace(0, sr / 2, n_fft // 2 + 1)
    fb = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for i in range(n_mels):
        l, c, r = hz[i], hz[i + 1], hz[i + 2]
        left = (bin_freqs - l) / max(c - l, 1e-9)
        right = (r - bin_freqs) / max(r - c, 1e-9)
        fb[i] = np.clip(np.minimum(left, right), 0.0, 1.0)
    return fb


_MEL_FB = mel_filterbank()
_HANN = np.hanning(N_FFT).astype(np.float32)


def stft_logmel(x):
    """Return log-mel spectrogram as (n_mels, n_frames) float32."""
    if len(x) < N_FFT:
        x = np.pad(x, (0, N_FFT - len(x)))
    n_frames = 1 + (len(x) - N_FFT) // HOP
    out = np.empty((N_MELS, n_frames), dtype=np.float32)
    for i in range(n_frames):
        seg = x[i * HOP : i * HOP + N_FFT] * _HANN
        spec = np.abs(np.fft.rfft(seg))
        mel = _MEL_FB @ (spec * spec)
        out[:, i] = np.log1p(mel)
    return out


def decode_to_pcm(path, start=0.0, duration=None, sr=SR):
    """Decode a span of audio to mono 16 kHz PCM.  -vn is critical: without it
    ffmpeg also decodes video, ~5–10× slower on h264 1080p sources."""
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", str(start), "-i", path,
        "-vn", "-map", "0:a:0",
    ]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    p = subprocess.run(cmd, capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def normalized_xcorr_2d(target_spec, ref_spec):
    """Slide ref_spec along the time axis of target_spec; return Pearson
    correlation at every valid offset (one value per hop)."""
    T = target_spec.shape[1]
    R = ref_spec.shape[1]
    if T < R:
        return np.array([])
    tgt = target_spec - target_spec.mean(axis=0, keepdims=True)
    ref = ref_spec - ref_spec.mean(axis=0, keepdims=True)
    L = 1 << (T + R - 1).bit_length()
    R_F = np.fft.rfft(ref[:, ::-1], L, axis=1)
    T_F = np.fft.rfft(tgt, L, axis=1)
    corr = np.fft.irfft(T_F * R_F, L, axis=1).sum(axis=0)
    corr = corr[R - 1 : R - 1 + (T - R + 1)]
    sq = (tgt * tgt).sum(axis=0)
    cs = np.concatenate(([0.0], np.cumsum(sq)))
    win_sq = cs[R:] - cs[:-R]
    tgt_norms = np.sqrt(np.maximum(win_sq, 1e-12))
    return corr / (tgt_norms * (np.linalg.norm(ref) + 1e-9))


def find_theme(target_path, ref_path, search_start=0.0, search_dur=600.0):
    """Return (offset_seconds, score). offset is where the reference best
    aligns inside [search_start, search_start+search_dur] of the target."""
    ref_pcm = decode_to_pcm(ref_path)
    tgt_pcm = decode_to_pcm(target_path, start=search_start, duration=search_dur)
    if len(tgt_pcm) < len(ref_pcm):
        return None, 0.0
    ref_spec = stft_logmel(ref_pcm)
    tgt_spec = stft_logmel(tgt_pcm)
    corr = normalized_xcorr_2d(tgt_spec, ref_spec)
    if len(corr) == 0:
        return None, 0.0
    idx = int(np.argmax(corr))
    score = float(corr[idx])
    offset_sec = search_start + idx * HOP / SR
    return offset_sec, score


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: find_theme.py <ref.wav> <target.mkv> [search_start] [search_dur]",
              file=sys.stderr)
        sys.exit(2)
    ref_path = sys.argv[1]
    target_path = sys.argv[2]
    search_start = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    search_dur = float(sys.argv[4]) if len(sys.argv) > 4 else 600.0
    offset, score = find_theme(target_path, ref_path, search_start, search_dur)
    print(f"offset={offset:.3f}\tscore={score:.4f}\tfile={target_path}")
