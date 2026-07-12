#!/usr/bin/env bash
# setup.sh <workdir> — create the working tree + a python venv with scene/audio deps.
# Idempotent. Prints the encoder that render.py will use.
set -euo pipefail
ROOT="${1:?usage: setup.sh <workdir>}"
mkdir -p "$ROOT"/{src,seg,work,out,frames}

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" -q install --upgrade pip
  "$ROOT/.venv/bin/pip" -q install "scenedetect" opencv-python-headless numpy soundfile librosa scipy
fi
"$ROOT/.venv/bin/python" - <<'PY'
import scenedetect, numpy, soundfile, librosa, cv2
print("venv OK: scenedetect", scenedetect.__version__, "| cv2", cv2.__version__)
PY

for t in yt-dlp ffmpeg ffprobe; do command -v "$t" >/dev/null || echo "WARNING: $t not on PATH"; done
if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q h264_nvenc; then
  echo "encoder: h264_nvenc (GPU) available"
else
  echo "encoder: libx264 (CPU) — no NVENC, render will be slower but works"
fi
echo "workdir ready: $ROOT"
