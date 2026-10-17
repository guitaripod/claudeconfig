#!/bin/bash
set -euo pipefail
video="$1"
out="$2"
cols="$3"
shift 3
tmp="$(mktemp -d)"
i=0
for t in "$@"; do
  ffmpeg -y -v error -ss "$t" -i "$video" -frames:v 1 "$tmp/$(printf %03d $i).png"
  i=$((i + 1))
done
magick montage "$tmp"/*.png -tile "${cols}x" -geometry 640x+4+4 -background '#222' "$out"
rm -rf "$tmp"
echo "$out"
