#!/usr/bin/env bash
set -eu
WORKDIR="$1"
command -v ffmpeg >/dev/null 2>&1 || { echo "error: ffmpeg not found" >&2; exit 1; }
mkdir -p "$WORKDIR"
AUDIO='0.125892541*sin(2*PI*440*t)+0.004*gte(t\,3)*sin(2*PI*660*t)'
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "testsrc2=size=640x360:rate=30:duration=6" \
  -f lavfi -i "aevalsrc=${AUDIO}|${AUDIO}:s=48000:d=6" \
  -map 0:v:0 -map 1:a:0 -t 6 \
  -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -ac 2 \
  -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
  -movflags +faststart \
  "$WORKDIR/clip.mp4"
