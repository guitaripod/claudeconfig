#!/bin/bash
set -euo pipefail
project="$1"
music="$2"
outdir="$3"
shift 3
cd "$project"
mkdir -p out "$outdir"
for pair in "$@"; do
  composition="${pair%%:*}"
  name="${pair##*:}"
  npx remotion render src/index.ts "$composition" "out/silent-$name.mp4" \
    --codec=h264 --crf=16 --pixel-format=yuv420p --muted --concurrency="$(nproc)" 2>&1 | tail -1
  ffmpeg -y -v error -i "out/silent-$name.mp4" -i "$music" -map 0:v -map 1:a \
    -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$outdir/$name.mp4"
  echo "== $name"
  ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,pix_fmt,sample_rate \
    -of default=nw=1 "$outdir/$name.mp4" | tr '\n' ' '
  echo
  ffmpeg -nostats -i "$outdir/$name.mp4" -af ebur128=peak=true -f null - 2>&1 \
    | grep -A12 Summary | grep -E "  I:|Peak:" | tr '\n' ' '
  echo
done
