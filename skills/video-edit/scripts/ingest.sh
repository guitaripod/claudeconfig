#!/usr/bin/env bash
# ingest.sh <workdir> <source...> — local file, local directory, or YouTube id/URL.
# Everything lands in <workdir>/src/<id>.mp4 and is decode-validated. Downloads are
# SEQUENTIAL on purpose: parallel yt-dlp on the same output races and silently
# corrupts files; local copies are sequential for the same reason.
set -uo pipefail
ROOT="${1:?usage: ingest.sh <workdir> <file|dir|youtube-id|url>...}"; shift
mkdir -p "$ROOT/src"

ok() {  # returns 0 if file decodes clean (few NAL/errors)
  local f="$1"; [ -f "$f" ] || return 1
  local e; e=$(ffmpeg -nostdin -v error -i "$f" -map 0:v:0 -f null - 2>&1 | grep -icE "NAL|error|invalid")
  [ "${e:-99}" -le 5 ]
}

to_mp4() {  # local path -> src/<stem>.mp4 (remux when it is already a video)
  local p="$1" stem out
  stem=$(basename -- "$p"); stem="${stem%.*}"
  out="$ROOT/src/$stem.mp4"
  [ -f "$out" ] && return 0
  if [ "${p##*.}" = "mp4" ]; then
    cp -- "$p" "$out"
  else
    ffmpeg -nostdin -hide_banner -loglevel error -y -i "$p" -map 0:v:0 -map 0:a? -c copy \
      -movflags +faststart "$out" || return 1
  fi
}

dl() {  # id -> src/<id>.mp4  (<=1080p; 50/60fps then avc1 preferred)
  local id="$1" url="$id" base
  [[ "$id" == http* ]] || url="https://youtu.be/$id"
  base=$(basename -- "$id"); base="${base##*=}"
  yt-dlp --no-playlist -N 1 \
    -f "bv*[height<=1080][fps>=50][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]" \
    --merge-output-format mp4 -o "$ROOT/src/${base}.%(ext)s" "$url" >/dev/null 2>&1
}

for arg in "$@"; do
  if [ -d "$arg" ]; then
    while IFS= read -r f; do
      f="${f%$'\r'}"
      if to_mp4 "$f" && ok "$ROOT/src/$(basename -- "${f%.*}").mp4"; then
        echo "OK   $(basename -- "${f%.*}")"
      else
        echo "FAIL $f (copy/remux or decode)"
      fi
    done < <(find "$arg" -maxdepth 2 -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.mkv' -o -iname '*.webm' \) | sort)
    continue
  fi
  if [ -f "$arg" ]; then
    if to_mp4 "$arg" && ok "$ROOT/src/$(basename -- "${arg%.*}").mp4"; then
      echo "OK   $(basename -- "${arg%.*}")"
    else
      echo "FAIL $arg (copy/remux or decode)"
    fi
    continue
  fi
  base=$(basename -- "$arg"); base="${base##*=}"; f="$ROOT/src/${base}.mp4"
  dl "$arg"
  if ok "$f"; then echo "OK   $base"; else
    rm -f "$f"; dl "$arg"
    if ok "$f"; then echo "OK   $base (retry)"; else echo "FAIL $base"; rm -f "$f"; fi
  fi
done
echo "--- src inventory ---"
for f in "$ROOT"/src/*.mp4; do
  [ -e "$f" ] || continue
  r=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,avg_frame_rate -of csv=p=0 "$f")
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  printf "%-24s %s %.0fs\n" "$(basename "$f" .mp4)" "$r" "${d:-0}"
done
