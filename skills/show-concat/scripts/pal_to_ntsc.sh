#!/usr/bin/env bash
# Convert PAL (25 fps + AC3) sources to NTSC (23.976 fps + EAC3) with proper
# speed correction (slowdown factor 24000/25025 ≈ 0.95904).  Uses NVENC h264
# for speed; swap to libx264 if no NVIDIA GPU.
#
# Configure SRC_DIRS and DST below.  Skips files already present in DST.
# Always passes -nostdin (background ffmpeg without it gets stuck reading
# interactive commands), and writes to .partial-…mkv (NOT .mkv.tmp — ffmpeg
# can't infer format from .tmp).
set -euo pipefail

# ────────── CONFIGURE ──────────
SRC_DIRS=(
  "/path/to/show/Season 7"
  "/path/to/show/Season 8"
  "/path/to/show/Season 9"
)
DST="/path/to/output/pal"
# ───────────────────────────────

mkdir -p "$DST"

SLOWDOWN="25025/24000"     # video PTS multiplier (slows 25 → 23.976)
ATEMPO="24000/25025"       # audio tempo (matches video slowdown)

count=0
total=$(find "${SRC_DIRS[@]}" -type f -name "*.mkv" 2>/dev/null | wc -l)
echo "PAL→NTSC conversion: $total files → $DST" >&2

while IFS= read -r -d '' f; do
  count=$((count + 1))
  base=$(basename "$f")
  out="$DST/$base"
  partial="$DST/.partial-$base"
  if [[ -s "$out" ]]; then
    echo "[$count/$total] skip (exists): $base" >&2
    continue
  fi
  echo "[$count/$total] converting: $base" >&2
  rm -f "$partial"
  if ffmpeg -hide_banner -loglevel warning -nostdin -y \
        -i "$f" \
        -filter:v "setpts=${SLOWDOWN}*PTS" \
        -filter:a "atempo=${ATEMPO}" \
        -r 24000/1001 \
        -c:v h264_nvenc -preset p7 -tune hq -profile:v high \
        -rc vbr -cq 19 -b:v 0 -maxrate 12M -bufsize 24M \
        -pix_fmt yuv420p \
        -c:a eac3 -b:a 384k -ac 6 \
        -map 0:v:0 -map 0:a:0 \
        -f matroska "$partial"; then
    mv "$partial" "$out"
  else
    rm -f "$partial"
    echo "[$count/$total] FAILED: $base" >&2
    exit 1
  fi
done < <(find "${SRC_DIRS[@]}" -type f -name "*.mkv" -print0 2>/dev/null | sort -z)

echo "DONE: $count files in $DST" >&2
