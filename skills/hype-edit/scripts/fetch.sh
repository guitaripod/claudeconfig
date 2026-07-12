#!/usr/bin/env bash
# fetch.sh <workdir> <youtube_id_or_url> [more...]
# Robust SEQUENTIAL downloader → <workdir>/src/. Sequential on purpose: parallel
# yt-dlp on the same output races and silently corrupts files. Validates every
# download by fully decoding it; auto-retries corrupt/failed ones once.
set -uo pipefail
ROOT="${1:?usage: fetch.sh <workdir> <id...>}"; shift
mkdir -p "$ROOT/src"

dl() {  # id -> src/<id>.mp4  (<=1080p, avc1 preferred so it's edit-friendly)
  local id="$1"; local url="$id"
  [[ "$id" == http* ]] || url="https://youtu.be/$id"
  local base; base=$(basename "$id"); base="${base##*=}"
  yt-dlp --no-playlist -N 1 \
    -f "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]" \
    --merge-output-format mp4 -o "$ROOT/src/${base}.%(ext)s" "$url" >/dev/null 2>&1
}
ok() {  # returns 0 if file decodes clean (few NAL/errors)
  local f="$1"; [ -f "$f" ] || return 1
  local e; e=$(ffmpeg -v error -i "$f" -map 0:v:0 -f null - 2>&1 | grep -icE "NAL|error|invalid")
  [ "${e:-99}" -le 5 ]
}

for id in "$@"; do
  base=$(basename "$id"); base="${base##*=}"; f="$ROOT/src/${base}.mp4"
  dl "$id"
  if ok "$f"; then echo "OK   $base"; else
    rm -f "$f"; dl "$id"
    if ok "$f"; then echo "OK   $base (retry)"; else echo "FAIL $base"; rm -f "$f"; fi
  fi
done
echo "--- src inventory ---"
for f in "$ROOT"/src/*.mp4; do
  [ -e "$f" ] || continue
  r=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$f")
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  printf "%-16s %s %.0fs\n" "$(basename "$f" .mp4)" "$r" "${d:-0}"
done
