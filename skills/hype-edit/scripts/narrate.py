#!/usr/bin/env python3
"""narrate.py <workdir> — compose a spoken narration track and mix it UNDER the OST,
overwriting master.wav sample-exact (zero A/V drift). Opt-in voice-over for hype edits.

Reads project.json["narration"]:
  {
    "lines": [ {"src":"<yt-id|url|path>", "phrase":"words to locate", "at":0.30, "gain":1.0}, ... ],
    "duck_db": -8.5,         # music level under speech (default -8.5 dB)
    "hp_hz": 90,             # highpass on the voice (default 90)
    "vo_gain": 1.15,         # overall voice gain in the mix (default 1.15)
    "asr_model": "small.en"  # whisper model (default small.en)
  }
Per source: download (yt) → Whisper word-timestamps → Demucs vocal isolation → slice each
phrase from the isolated voice → place on the music timeline at `at` → sidechain-duck the
OST under the voice → master.wav. All intermediates cache under <workdir>/narration/, so
re-runs are cheap. The music-only analysis WAV (song_22k_mono.wav) is untouched, so the beat
grid stays clean; only the mux track (master.wav) gains the voice.

RUN WITH THE NARRATION VENV: `<workdir>/asr-venv/bin/python narrate.py <workdir>`
(create it with `setup.sh <workdir> --narration`). Placement tip: `at` is where the phrase
STARTS; to detonate a word on a beat, set `at = beat - (word_onset_within_phrase)`."""
import sys, os, json, subprocess, glob, re, difflib, shutil
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
from scipy.ndimage import gaussian_filter1d, maximum_filter1d

try:
    import whisper
except ImportError:
    sys.exit("narrate.py needs the narration venv (whisper/demucs). Run:\n"
             "  setup.sh <workdir> --narration\n"
             "  <workdir>/asr-venv/bin/python narrate.py <workdir>")

SR = 44100
ROOT = os.path.abspath(sys.argv[1])
CFG = json.load(open(f"{ROOT}/project.json"))
SPEC = CFG.get("narration") or {}
N = int(round(CFG["dur"] * SR))
ND = f"{ROOT}/narration"
DUCK_DB = SPEC.get("duck_db", -8.5)
HP = SPEC.get("hp_hz", 90)
VO_GAIN = SPEC.get("vo_gain", 1.15)
MODEL = SPEC.get("asr_model", "small.en")


def sh(a): return subprocess.run(a, capture_output=True, text=True)
def norm(s): return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
def key_of(src): return (re.sub(r"[^A-Za-z0-9_-]", "_", os.path.splitext(os.path.basename(src))[0])[:40] or "src")


def ensure_wav(src):
    """44.1k stereo wav for src (yt id / url / local path), cached under narration/wav/."""
    key = key_of(src)
    wav = f"{ND}/wav/{key}.wav"
    if os.path.exists(wav):
        return key, wav
    os.makedirs(f"{ND}/wav", exist_ok=True)
    if os.path.exists(src):
        raw = src
    else:
        url = src if src.startswith("http") else f"https://youtu.be/{src}"
        r = sh(["yt-dlp", "-f", "bestaudio", "--no-playlist", "-o", f"{ND}/wav/{key}.%(ext)s", url])
        if r.returncode != 0:
            sys.exit(f"narrate: download failed for {src}\n{r.stderr[-400:]}")
        raw = next(p for p in glob.glob(f"{ND}/wav/{key}.*") if not p.endswith(".wav"))
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-ar", str(SR), "-ac", "2", wav])
    return key, wav


def asr_words(key, wav, model):
    cache = f"{ND}/asr/{key}.json"
    if os.path.exists(cache):
        return json.load(open(cache))
    os.makedirs(f"{ND}/asr", exist_ok=True)
    r = model.transcribe(wav, word_timestamps=True, language="en")
    words = [[round(w["start"], 3), round(w["end"], 3), w["word"].strip()]
             for s in r["segments"] for w in s.get("words", [])]
    json.dump(words, open(cache, "w"))
    return words


def demucs_vocals(key, wav):
    out = f"{ND}/stems/htdemucs/{key}/vocals.wav"
    if os.path.exists(out):
        return out
    os.makedirs(f"{ND}/stems", exist_ok=True)
    r = sh([sys.executable, "-m", "demucs", "--two-stems=vocals", "-o", f"{ND}/stems", wav])
    if not os.path.exists(out):
        sys.exit(f"narrate: demucs failed for {key}\n{r.stderr[-400:]}")
    return out


def find_span(words, phrase, pad=0.15):
    """Locate a phrase in whisper word-timestamps via difflib token alignment, extending the
    span over unmatched boundary words (whisper mishears edges, e.g. 'zoos' for 'Zeus')."""
    T = [(norm(w[2]) or [""])[0] for w in words]
    P = norm(phrase)
    if not P or not words:
        return None
    blocks = [b for b in difflib.SequenceMatcher(None, T, P, autojunk=False).get_matching_blocks()
              if b.size > 0]
    matched = sum(b.size for b in blocks)
    if not blocks or matched / len(P) < 0.5:
        return None
    lo = min(b.a for b in blocks) - blocks[0].b                       # reach back over misheard lead
    hi = max(b.a + b.size for b in blocks) - 1 + (len(P) - (blocks[-1].b + blocks[-1].size))
    lo, hi = max(0, lo), min(len(words) - 1, hi)
    return max(0.0, words[lo][0] - pad), words[hi][1] + pad, matched / len(P)


def main():
    lines = SPEC.get("lines")
    if not lines:
        sys.exit("narrate: project.json has no narration.lines")
    model = whisper.load_model(MODEL)
    hp = butter(4, HP, "highpass", fs=SR, output="sos")
    vo = np.zeros((N, 2), np.float32)
    cache, missed = {}, []
    for ln in lines:
        key, wav = ensure_wav(ln["src"])
        if key not in cache:
            words = asr_words(key, wav, model)
            y, sr = sf.read(demucs_vocals(key, wav))
            if y.ndim == 1:
                y = np.stack([y, y], 1)
            cache[key] = (words, y.astype(np.float32), sr)
        words, y, sr = cache[key]
        span = find_span(words, ln["phrase"])
        if not span:
            print(f"  !! phrase not found: '{ln['phrase']}' in {key} — SKIPPED")
            missed.append(ln["phrase"])
            continue
        a, b, sc = span
        seg = sosfiltfilt(hp, y[int(a * sr):int(b * sr)].copy(), axis=0).astype(np.float32)
        seg = seg / (np.abs(seg).max() + 1e-9) * 0.92 * ln.get("gain", 1.0)
        f = int(0.028 * sr)
        if len(seg) > 2 * f:
            seg[:f] *= np.linspace(0, 1, f)[:, None]
            seg[-f:] *= np.linspace(1, 0, f)[:, None]
        off = int(ln["at"] * SR)
        end = min(off + len(seg), N)
        vo[off:end] += seg[:end - off]
        print(f"  {ln['at']:6.2f}s  +{b-a:.2f}s  match={sc:.2f}  {ln['phrase'][:46]}")

    env = np.abs(vo).max(1)
    gate = gaussian_filter1d(maximum_filter1d((env > 0.02).astype(np.float32),
                                              int(0.18 * SR)), int(0.05 * SR))
    duck = 10 ** (DUCK_DB / 20.0)
    music_gain = 1.0 - (1.0 - duck) * np.clip(gate, 0, 1)

    mm = f"{ROOT}/music_master.wav"
    if not os.path.exists(mm):
        shutil.copyfile(f"{ROOT}/{CFG['audio_master']}", mm)   # preserve the untouched OST master
    music, _ = sf.read(mm, dtype="float32")
    if music.ndim == 1:
        music = np.stack([music, music], 1)
    music = music[:N]
    if len(music) < N:
        music = np.pad(music, ((0, N - len(music)), (0, 0)))
    final = music * music_gain[:, None] + vo * VO_GAIN
    final = (final / (np.abs(final).max() + 1e-9) * 0.985).astype(np.float32)
    sf.write(f"{ROOT}/{CFG['audio_master']}", final, SR, subtype="PCM_24")
    sf.write(f"{ND}/vo_full.wav", vo, SR, subtype="PCM_16")
    info = sf.info(f"{ROOT}/{CFG['audio_master']}")
    assert info.frames == N, (info.frames, N)
    print(f"\nmaster.wav rebuilt: {info.frames} samples ({info.frames/SR:.3f}s) | "
          f"VO {int((env>0.02).sum())/SR:.1f}s | duck {DUCK_DB}dB"
          + (f" | MISSED {len(missed)}: {missed}" if missed else ""))
    print("validate: re-transcribe master.wav — the lines should still be intelligible over the music.")


if __name__ == "__main__":
    main()
