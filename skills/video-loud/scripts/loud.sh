#!/usr/bin/env bash
# loud.sh — measure, boost, and verify a video's audio.
# Peak-normalizes or loudness-levels the main audio track; video stream is copied, never re-encoded.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: loud.sh <input> [options]

Boost a video's audio as loud as possible without clipping.

Modes:
  --mode peak    Raise overall gain to hit the true-peak ceiling (default 0 dBTP),
                 preserving dynamics. Use for "boost it", "max it out before it clips",
                 "normalize".
  --mode loud    EBU R128 loudness-level to a target LUFS (two-pass loudnorm) then
                 brick-wall limit. Use for "loud at every moment", "keep it consistent",
                 "make the quiet parts loud too".

Options:
  --target <I>   loud mode only: integrated target in LUFS (default -9, a loud consumer
                 level; -14 is the streaming standard if the user wants restraint).
  --tp <dB>      loud mode only: true-peak ceiling in dBTP (default -1.0).
  --out <path>   Output file (default: <stem> - loud<ext>, auto-suffixed on collision).
  -h, --help     This help.

Requires: ffmpeg, ffprobe, jq. Always pass the ORIGINAL file, not a prior output.
EOF
}

MODE=peak
TARGET=-9
TP=-1.0
OUT=""
INPUT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)   MODE="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --tp)     TP="$2"; shift 2 ;;
    --out)    OUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "unknown option: $1" >&2; usage; exit 2 ;;
    *)  INPUT="$1"; shift ;;
  esac
done

[ -n "$INPUT" ] || { usage; exit 2; }
[ -f "$INPUT" ] || { echo "error: input not found: $INPUT" >&2; exit 1; }

for tool in ffmpeg ffprobe jq; do
  command -v "$tool" >/dev/null 2>&1 || { echo "error: $tool not found" >&2; exit 1; }
done

case "$MODE" in peak|loud) ;; *) echo "error: --mode must be peak or loud" >&2; exit 2 ;; esac

# Output path: <stem> - loud<ext>, auto-suffix on collision
if [ -z "$OUT" ]; then
  stem="${INPUT%.*}"
  ext=".${INPUT##*.}"
  [ "$stem" = "$INPUT" ] && ext=""
  OUT="${stem} - loud${ext}"
  n=2
  while [ -e "$OUT" ]; do
    OUT="${stem} - loud-${n}${ext}"
    n=$((n + 1))
  done
fi

# Source audio properties (bitrate floor 192k; ffprobe reports bits/s)
SRC_BIT=$(ffprobe -v error -select_streams a:0 -show_entries stream=bit_rate \
  -of default=nw=1:nk=1 "$INPUT" 2>/dev/null | head -1)
case "$SRC_BIT" in ''|*[!0-9]*) SRC_BIT=192000 ;; esac
SRC_KB=$(( SRC_BIT / 1000 ))
[ "$SRC_KB" -lt 192 ] && SRC_KB=192
ABIT="${SRC_KB}k"
SR=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate \
  -of default=nw=1:nk=1 "$INPUT" | head -1)
case "$SR" in ''|*[!0-9]*) SR=48000 ;; esac

echo "input : $INPUT"
echo "output: $OUT"
echo "audio : ${ABIT} AAC @ ${SR} Hz, video stream copied"

# loudnorm prints its JSON report to stderr mixed with ffmpeg logs; grab the block only.
measure() {
  local f="$1"
  ffmpeg -hide_banner -nostdin -i "$f" -map 0:a:0 \
    -af "loudnorm=I=-20:TP=-1:LRA=11:print_format=json" -f null - 2>"$f.log"
  local json
  json=$(sed -n '/^{/,/^}/p' "$f.log")
  rm -f "$f.log"
  [ -n "$json" ] || { echo "error: loudnorm reported no JSON for $f" >&2; exit 1; }
  printf '%s' "$json"
}

# Print the dB of attenuation needed so a file's true peak lands at ceiling; empty if OK.
correction_gain() {
  local tp
  tp=$(measure "$1" | jq -r '.input_tp // "N/A"')
  awk -v tp="$tp" -v c="$2" \
    'BEGIN{if (tp ~ /inf/ || tp == "N/A") exit; v=c-tp; if (v < -0.05) printf "%.3f", v}'
}

meas=$(mktemp)
measure "$INPUT" >"$meas"
I0=$(jq -r '.input_i // "N/A"' "$meas")
TP0=$(jq -r '.input_tp // "N/A"' "$meas")
LRA0=$(jq -r '.input_lra // "N/A"' "$meas")
TH0=$(jq -r '.input_thresh // "N/A"' "$meas")
echo "before: I=${I0} LUFS  true-peak=${TP0} dBTP  LRA=${LRA0} LU"

TMP=$(mktemp --suffix="${ext:-.mp4}")
trap 'rm -f "$meas" "$TMP"' EXIT

CEILING=0
if [ "$MODE" = peak ]; then
  # Transparent gain to the ceiling. AAC re-encoding can add inter-sample peak
  # overshoot, so a single correction re-encode (still from the original) covers it.
  GAIN=$(awk -v tp="$TP0" 'BEGIN{if (tp ~ /inf/ || tp == "N/A") print 0; else printf "%.3f", -tp}')
  AF="volume=${GAIN}dB,alimiter=level=false:limit=1.0"
  echo "mode  : peak (gain ${GAIN} dB, ceiling ${CEILING} dBTP)"
else
  # Two-pass dynamic loudnorm: pass 1 measures, pass 2 applies time-varying gain
  # to hit the I/TP targets. loudnorm runs at 192 kHz internally, so resample
  # back to the source rate. AAC can still overshoot the TP ceiling (inter-sample
  # peaks), covered by the same correction re-encode.
  AF="loudnorm=I=${TARGET}:TP=${TP}:LRA=11:measured_I=${I0}:measured_TP=${TP0}:measured_LRA=${LRA0}:measured_thresh=${TH0}:linear=false,alimiter=level=false:limit=1.0,aresample=${SR}"
  CEILING=$TP
  echo "mode  : loud (two-pass EBU R128 → I=${TARGET} LUFS, TP=${TP} dBTP)"
fi

encode() { # $1 = gain suffix applied after loudnorm/limiter (must not be re-normalized)
  ffmpeg -hide_banner -nostdin -y -i "$INPUT" \
    -map 0:v:0 -map 0:a:0 -c:v copy \
    -af "${AF}${1}" -c:a aac -b:a "$ABIT" \
    -movflags +faststart "$TMP"
}
encode ""

# AAC re-encoding adds variable inter-sample overshoot, so iterate: measure the
# encoded file and subtract whatever it landed over by, until under the ceiling.
for pass in 1 2 3; do
  CORR=$(correction_gain "$TMP" "$CEILING") || break
  [ -z "$CORR" ] && break
  echo "correcting: pass $pass landed ${CORR} dB over the ceiling, re-encoding"
  encode ",volume=${CORR}dB"
done

mv "$TMP" "$OUT"
trap - EXIT

# Verify on the actual output
meas2=$(mktemp)
measure "$OUT" >"$meas2"
I1=$(jq -r '.input_i // "N/A"' "$meas2")
TP1=$(jq -r '.input_tp // "N/A"' "$meas2")
rm -f "$meas2"
echo "after : I=${I1} LUFS  true-peak=${TP1} dBTP"
echo "done  : $OUT"
