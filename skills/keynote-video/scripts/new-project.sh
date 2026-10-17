#!/bin/bash
set -euo pipefail
dest="$1"
icon="${2:-}"
skill="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$dest/public/framed" "$dest/audio" "$dest/out"
cp -r "$skill/template/." "$dest/"
if [ -n "$icon" ]; then
  cp "$icon" "$dest/public/AppIcon.svg"
else
  printf '%s' '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4C8DFF"/><stop offset="1" stop-color="#6D28D9"/></linearGradient></defs><rect width="1024" height="1024" fill="url(#g)"/></svg>' > "$dest/public/AppIcon.svg"
fi
(cd "$dest" && pnpm install --silent 2>&1 | grep -v "ignored build\|approve-builds" || true)
echo "next: frame shots into $dest/public/framed/shot1.png, cut music to $dest/audio/music.wav, edit src/scenes.tsx and src/timing.ts"
