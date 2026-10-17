#!/bin/bash
set -euo pipefail
src="$1"
start="$2"
duration="$3"
out="$4"
tail_fade="${5:-3}"
fade_start=$(python3 -c "print($duration - $tail_fade)")
ffmpeg -y -v error -ss "$start" -t "$duration" -i "$src" -vn \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.5,afade=t=out:st=${fade_start}:d=${tail_fade}" \
  -ar 48000 -ac 2 "$out"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out"
