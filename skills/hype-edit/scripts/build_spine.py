#!/usr/bin/env python3
"""build_spine.py <workdir> — Phase 0: audio-driven editing spine. Deterministic.
Reads project.json; writes spine.json (beats, downbeats, energy curve, sections,
cutlist with hero slots). Run with the venv python (needs librosa/scipy)."""
import sys, json
import numpy as np
import librosa
import scipy.stats
from scipy.ndimage import gaussian_filter1d

ROOT = sys.argv[1]
CFG = json.load(open(f"{ROOT}/project.json"))
STYLE = CFG.get("style", "classic")
SR, HOP, N_FFT = CFG["sr_analysis"], 512, 2048
DUR, FPS_OUT = CFG["dur"], CFG["fps"]
FPS = SR / HOP
TEMPO_BAND = (70.0, 200.0)                 # wide; octave-corrected below
WAV = f"{ROOT}/{CFG['audio_analysis']}"


def fold(b, lo, hi):
    while b < lo: b *= 2
    while b > hi: b /= 2
    return b


def pct(x, lo=5, hi=95):
    a, b = np.percentile(x, [lo, hi]); return np.clip((x - a) / (b - a + 1e-9), 0, 1)


def main():
    y, _ = librosa.load(WAV, sr=SR, mono=True)
    oenv = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP, aggregate=np.median)
    n = len(oenv); tf = librosa.frames_to_time(np.arange(n), sr=SR, hop_length=HOP)

    # tempo (octave-corrected into a sane band via tempogram salience)
    prior = scipy.stats.lognorm(loc=0, scale=130, s=0.9)
    try:
        raw = float(np.atleast_1d(librosa.beat.tempo(onset_envelope=oenv, sr=SR,
                    hop_length=HOP, start_bpm=130, std_bpm=1.0, prior=prior))[0])
    except Exception:
        raw = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=oenv, sr=SR,
                    hop_length=HOP, start_bpm=130))[0])
    tg = librosa.feature.tempogram(onset_envelope=oenv, sr=SR, hop_length=HOP)
    tfr = librosa.tempo_frequencies(tg.shape[0], hop_length=HOP, sr=SR)
    sal = np.nan_to_num(tg).mean(1)
    band = (90.0, 180.0)
    def sl(b): return float(sal[np.argmin(np.abs(tfr - b))])
    BPM = max({round(fold(raw * r, *band), 4) for r in (0.5, 2/3, 1, 1.5, 2)}, key=sl)
    period = 60.0 / BPM

    # phase-locked uniform grid aligned to the kick (metronomic; no per-beat jitter)
    def gscore(ph):
        b = np.arange(ph, DUR, period)
        fr = np.clip(librosa.time_to_frames(b, sr=SR, hop_length=HOP), 0, n - 1)
        return float(oenv[fr].sum())
    ph = max(np.linspace(0, period, 200, endpoint=False), key=gscore)
    beats = np.round(np.arange(ph, DUR + 1e-9, period), 5)
    beats = beats[(beats >= 0) & (beats <= DUR)]
    onsets = librosa.onset.onset_detect(onset_envelope=oenv, sr=SR, hop_length=HOP, units='time')

    # energy features (structural smoothing so periodic kicks don't fragment sections)
    S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
    fhz = librosa.fft_frequencies(sr=SR, n_fft=N_FFT)
    rms = librosa.feature.rms(S=S, frame_length=N_FFT, hop_length=HOP)[0]
    low, high = S[fhz < 150].mean(0), S[fhz > 6000].mean(0)
    rms_n, flux_n, low_n, high_n = map(pct, (rms, oenv, low, high))
    sig = 1.5 * FPS
    E = pct(gaussian_filter1d(0.5 * rms_n + 0.25 * flux_n + 0.25 * low_n, sig), 2, 98)
    def fi(t): return int(np.clip(librosa.time_to_frames(t, sr=SR, hop_length=HOP), 0, n - 1))

    def bar_e(p):
        fr = np.clip(librosa.time_to_frames(beats[p::4], sr=SR, hop_length=HOP), 0, n - 1)
        return float(oenv[fr].sum() + rms[fr].sum())
    bar_phase = max(range(4), key=bar_e)

    # drops: sustained forward energy jump on downbeats, non-max-suppressed
    W = int(round(2.0 * FPS))
    def jump(t):
        f = fi(t)
        before = E[max(0, f - W):f].mean() if f - W >= 0 else E[:f + 1].mean()
        after = E[f:min(n, f + W)].mean()
        dip = rms_n[max(0, f - int(0.3 * FPS)):f]
        return after - before + 0.25 * (1 - dip.min() if len(dip) else 0), after
    db0 = beats[bar_phase::4]
    scored = [(t, *jump(t)) for t in db0 if 4 <= t <= DUR - 3]
    drops, conf = [], "high"
    for t, j, af in sorted([(t, j, af) for t, j, af in scored if af > 0.5 and j > 0.28],
                           key=lambda x: -x[1]):
        if all(abs(t - d['time']) > 8 for d in drops):
            bi = int(np.argmin(np.abs(beats - t)))
            drops.append({"time": round(float(beats[bi]), 4), "beat_index": bi,
                          "strength": round(float(j), 3), "after_level": round(float(af), 3)})
    if not drops:
        t = max(scored, key=lambda x: x[1])[0]; bi = int(np.argmin(np.abs(beats - t)))
        drops.append({"time": round(float(beats[bi]), 4), "beat_index": bi,
                      "strength": 0.0, "after_level": round(float(jump(t)[1]), 3)}); conf = "low"
    bar_phase = drops[0]["beat_index"] % 4
    downbeats = beats[bar_phase::4]

    # sections via hysteresis + rising highs before drops; snap to downbeats, merge short
    lab = np.where(E > 0.62, "peak", np.where(E < 0.33, "low", "build"))
    slope = gaussian_filter1d(np.gradient(high_n), sig)
    for d in drops:
        f = fi(d["time"]); a = max(0, f - int(6 * FPS)); seg = lab[a:f]
        seg[slope[a:f] > 0] = "build"; lab[a:f] = seg
    runs, s0 = [], 0
    for i in range(1, n + 1):
        if i == n or lab[i] != lab[s0]:
            runs.append([tf[s0], (tf[i - 1] if i < n else DUR), lab[s0]]); s0 = i
    def snapdb(t): return float(downbeats[np.argmin(np.abs(downbeats - t))]) if len(downbeats) else t
    sec = []
    for st, en, lb in runs:
        st = 0.0 if st < tf[1] else snapdb(st); en = DUR if en >= tf[-1] else snapdb(en)
        if en - st < 8 * period and sec: sec[-1][1] = en
        else: sec.append([st, en, lb])
    for d in drops:
        for s in sec:
            if s[0] <= d["time"] < s[1]: s[2] = "drop"; break
    msec = [sec[0]]
    for st, en, lb in sec[1:]:
        if lb == msec[-1][2]: msec[-1][1] = en
        else: msec.append([st, en, lb])
    sec = msec; sec[0][0] = 0.0; sec[-1][1] = DUR
    for i in range(1, len(sec)): sec[i][0] = sec[i - 1][1]
    def sat(t):
        for st, en, lb in sec:
            if st <= t < en: return lb
        return sec[-1][2]
    def sfrac(t):
        for st, en, lb in sec:
            if st <= t < en: return lb, (t - st) / max(en - st, 1e-6)
        return sec[-1][2], 1.0

    # heroes: main drop + strongest peak/drop downbeat per zone (~1 per 25s)
    dstr = oenv[np.clip(librosa.time_to_frames(downbeats, sr=SR, hop_length=HOP), 0, n - 1)]
    prim = drops[0]["time"]; heroes = [prim]
    nz = max(3, round(DUR / 25))
    for z0, z1 in zip(np.linspace(0, DUR, nz + 1)[:-1], np.linspace(0, DUR, nz + 1)[1:]):
        c = [(float(downbeats[k]), dstr[k]) for k in range(len(downbeats))
             if z0 <= downbeats[k] < z1 and sat(float(downbeats[k])) in ("peak", "drop")]
        if c:
            t = max(c, key=lambda x: x[1])[0]
            if all(abs(t - h) > 6 for h in heroes): heroes.append(t)
    heroes = sorted(set(heroes))
    hb_prim, hb_rest = (4, 3) if STYLE == "remaster" else (3, 2)
    hero_dur = {round(h, 5): (hb_prim * period if abs(h - prim) < 1e-3 else hb_rest * period)
                for h in heroes}

    # cutlist: tile 0..DUR on the beat grid; cadence tracks energy
    half = np.unique(np.round(np.concatenate([beats, (beats[:-1] + beats[1:]) / 2]), 5))
    def nb(t, step):
        grid = half if step < 1 else beats; tgt = t + step * period
        j = min(np.searchsorted(grid, t + period * 0.25), len(grid) - 1)
        while j < len(grid) - 1 and grid[j] < tgt - 1e-6: j += 1
        return float(min(grid[j], DUR))
    def hwin(t): return any(abs(t - h) <= 1.5 * period for h in heroes)
    B = [0.0, float(beats[0]) if beats[0] > 1e-6 else nb(0.0, 8)]
    t, g, first = B[1], 0, True
    while t < DUR - 1e-6 and g < 8000:
        g += 1; lb, fr = sfrac(t)
        if STYLE == "remaster":
            if lb == "low": step = 8
            elif lb == "build": step = {0: 4, 1: 4, 2: 2}[min(int(fr * 3), 2)]
            elif lb == "peak": step = 2
            else:
                bi = int(round((t - beats[0]) / period)); step = 4 if bi % 4 == 3 else 2
            if first: step = max(step, int(np.ceil(2.2 / period)))
        elif lb == "low": step = 8
        elif lb == "build": step = {0: 4, 1: 2, 2: 1}[min(int(fr * 3), 2)]
        elif lb == "peak": step = 2
        else:
            if hwin(t) and not any(abs(t - h) < 1e-3 for h in heroes): step = 0.5
            else:
                bi = int(round((t - beats[0]) / period)); step = 2 if bi % 4 == 3 else 1
        first = False
        x = nb(t, step)
        if x <= t + 1e-6: x = nb(t, max(step, 1) + 1)
        if x >= DUR - 1e-6: break
        B.append(x); t = x
    B.append(DUR)
    B = [b for b in B if not any(h + 1e-3 < b < h + hd - 1e-3 for h, hd in hero_dur.items())]
    for h, hd in hero_dur.items(): B += [h, min(h + hd, DUR)]
    B = np.unique(np.clip(np.round(np.array(B), 5), 0, DUR))
    m = [B[0]]
    for b in B[1:]:
        if b - m[-1] < 0.15: m[-1] = b
        else: m.append(b)
    m[-1] = DUR; B = np.array(m); B[0] = 0.0
    hset = set(np.round(heroes, 3))
    cut = [{"i": k, "start": round(float(B[k]), 4), "end": round(float(B[k + 1]), 4),
            "dur": round(float(B[k + 1] - B[k]), 4), "tag": sat(float(B[k])),
            "hero": round(float(B[k]), 3) in hset} for k in range(len(B) - 1)]
    for k in range(len(cut) - 1):
        assert abs(cut[k]["end"] - cut[k + 1]["start"]) < 1e-6 and cut[k]["dur"] > 0
    assert abs((cut[-1]["end"] - cut[0]["start"]) - DUR) < 1e-3

    d = np.diff(beats); cv = float(np.std(d) / np.mean(d)) if len(d) else 0.0
    ec = {"hz": 20.0, "t": [round(float(x), 3) for x in np.arange(0, DUR, 0.05)],
          "e": [round(float(np.interp(x, tf, E)), 4) for x in np.arange(0, DUR, 0.05)]}
    spine = {"meta": {"duration": DUR, "fps": FPS_OUT, "sr": SR,
                      "qc": {"beat_cv": round(cv, 4), "beat_count": len(beats),
                             "drop_confidence": conf, "n_cuts": len(cut),
                             "hero_times": [round(h, 3) for h in heroes]}},
             "bpm": round(BPM, 3), "beat_period": round(period, 4),
             "beats": [round(float(b), 4) for b in beats],
             "downbeats": [round(float(b), 4) for b in downbeats],
             "onsets": [round(float(o), 4) for o in onsets],
             "sections": [{"start": round(s, 4), "end": round(e, 4), "label": l} for s, e, l in sec],
             "drops": drops, "energy_curve": ec, "cutlist": cut}
    json.dump(spine, open(f"{ROOT}/spine.json", "w"), indent=1)
    dens = {}
    for c in cut: dens.setdefault(c["tag"], []).append(c["dur"])
    print(f"BPM={BPM:.1f} cv={cv:.3f} beats={len(beats)} cuts={len(cut)} "
          f"drop@{drops[0]['time']:.1f}s conf={conf}")
    print("heroes:", [round(h, 1) for h in heroes])
    print("sections:", " | ".join(f"{l}[{s:.0f}-{e:.0f}]" for s, e, l in sec))
    for tg in ("low", "build", "peak", "drop"):
        v = dens.get(tg, [])
        if v: print(f"  {tg:5s} {len(v):3d} cuts  mean {np.mean(v) * 1000:.0f}ms")


if __name__ == "__main__":
    main()
