#!/bin/bash
set -euo pipefail
project="$1"
composition="$2"
prefix="$3"
shift 3
cd "$project"
mkdir -p out/stills
printf "%s\n" "$@" | xargs -P5 -I{} sh -c \
  "npx remotion still src/index.ts $composition out/stills/${prefix}\$(printf %04d {}).png --frame={} >/dev/null 2>&1"
files=()
for frame in "$@"; do files+=("out/stills/${prefix}$(printf %04d "$frame").png"); done
magick montage "${files[@]}" -tile 2x -geometry 960x540+6+6 -background '#222' "out/sheet-${prefix}.jpg"
echo "$project/out/sheet-${prefix}.jpg"
