#!/usr/bin/env bash
# setup.sh <workdir> [--narration] — create the working tree and a python for the
# pipeline at <workdir>/py. Uses the system interpreter when it already has the
# scene/audio deps; otherwise a shared cached venv (~/.cache/video-edit/venv, so
# repeat edits cost nothing). A workdir that already has .venv keeps it.
# Idempotent. Prints the encoder render.py will pick.
set -euo pipefail
ROOT="${1:?usage: setup.sh <workdir> [--narration]}"
mkdir -p "$ROOT"/{src,seg,work,out,frames}

wrap() { printf '#!/bin/sh\nexec %s "$@"\n' "$1" > "$2"; chmod +x "$2"; }
deps_ok() { "$1" -c "import scenedetect, numpy, soundfile, librosa, cv2" 2>/dev/null; }

CACHE="${VIDEO_EDIT_VENV:-$HOME/.cache/video-edit/venv}"
ASR="${VIDEO_EDIT_ASR_VENV:-$HOME/.cache/video-edit/asr-venv}"

if [ -x "$ROOT/.venv/bin/python" ]; then
  wrap "$ROOT/.venv/bin/python" "$ROOT/py"
elif deps_ok python3; then
  wrap python3 "$ROOT/py"
else
  mkdir -p "$(dirname "$CACHE")"
  exec 9>"$CACHE.lock"; flock 9
  if [ ! -x "$CACHE/bin/python" ] || ! deps_ok "$CACHE/bin/python"; then
    python3 -m venv "$CACHE"
    "$CACHE/bin/pip" -q install --upgrade pip
    "$CACHE/bin/pip" -q install "scenedetect" opencv-python-headless numpy soundfile librosa scipy
  fi
  flock -u 9
  wrap "$CACHE/bin/python" "$ROOT/py"
fi
"$ROOT/py" - <<'PY'
import scenedetect, numpy, soundfile, librosa, cv2
print("deps OK: scenedetect", scenedetect.__version__, "| cv2", cv2.__version__)
PY

for t in yt-dlp ffmpeg ffprobe; do command -v "$t" >/dev/null || echo "WARNING: $t not on PATH"; done
# functional probe, not a listing grep: `-encoders | grep -q` SIGPIPEs ffmpeg under
# `set -o pipefail` (grep exits on first match) → the pipeline reports non-zero on a
# MATCH → false "no NVENC". A test-encode also catches listed-but-non-functional nvenc.
if ffmpeg -hide_banner -loglevel error -f lavfi -i color=c=black:s=256x256:d=0.1 \
     -c:v h264_nvenc -f null - >/dev/null 2>&1; then
  echo "encoder: h264_nvenc (GPU) — functional"
else
  echo "encoder: libx264 (CPU) — NVENC unavailable, render will be slower but identical"
fi
if [[ " ${*} " == *" --narration "* ]]; then
  if [ -x "$ROOT/asr-venv/bin/python" ]; then
    ASR_PY="$ROOT/asr-venv/bin/python"
  else
    mkdir -p "$(dirname "$ASR")"
    exec 8>"$ASR.lock"; flock 8
    if [ ! -x "$ASR/bin/python" ]; then
      python3 -m venv "$ASR"
      "$ASR/bin/pip" -q install --upgrade pip
      "$ASR/bin/pip" -q install torch --index-url https://download.pytorch.org/whl/cpu
      "$ASR/bin/pip" -q install openai-whisper demucs soundfile scipy numpy
    fi
    flock -u 8
    ASR_PY="$ASR/bin/python"
  fi
  wrap "$ASR_PY" "$ROOT/py-narrate"
  "$ROOT/py-narrate" -c "import whisper, demucs, soundfile, scipy; print('narration deps OK')"
fi
echo "workdir ready: $ROOT"
echo "PY=$ROOT/py"
