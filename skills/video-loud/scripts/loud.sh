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

# Output path: <stem> - loud<ext>, auto-suffix on collision. ext always follows the
# input: ffmpeg picks the muxer from the temp file's suffix, so a --out run must not
# leave ext unset or the AVI sources come out as MP4 wearing an .avi name.
stem="${INPUT%.*}"
if [ "$stem" != "$INPUT" ]; then ext=".${INPUT##*.}"; else ext=""; fi

if [ -z "$OUT" ]; then
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
  local log
  log=$(mktemp)
  ffmpeg -hide_banner -nostdin -err_detect ignore_err -i "$f" -map 0:a:0 \
    -af "loudnorm=I=-20:TP=-1:LRA=11:print_format=json" -f null - 2>"$log" || true
  local json
  json=$(sed -n '/^{/,/^}/p' "$log")
  rm -f "$log"
  [ -n "$json" ] || { echo "error: loudnorm reported no JSON for $f" >&2; exit 1; }
  printf '%s' "$json"
}

# Print how many dB a file's true peak sits over the ceiling; empty when at or under it.
# An unmeasurable file exits non-zero so the loop stops and the final check errors out.
overshoot() {
  local tp
  tp=$(measure "$1" | jq -r '.input_tp // "N/A"') || return 1
  awk -v tp="$tp" -v c="$2" \
    'BEGIN{if (tp == "N/A" || tp ~ /inf/) exit 1; v=tp-c; if (v > 0.01) printf "%.3f", v}'
}

meas=$(mktemp)
measure "$INPUT" >"$meas"
I0=$(jq -r '.input_i // "N/A"' "$meas")
TP0=$(jq -r '.input_tp // "N/A"' "$meas")
LRA0=$(jq -r '.input_lra // "N/A"' "$meas")
TH0=$(jq -r '.input_thresh // "N/A"' "$meas")
echo "before: I=${I0} LUFS  true-peak=${TP0} dBTP  LRA=${LRA0} LU"

# The muxer follows the final output name, whatever the input was called.
out_tail="${OUT##*/}"
case "$out_tail" in
  *.*) tmp_ext=".${out_tail##*.}" ;;
  *)   tmp_ext="${ext:-.mp4}" ;;
esac
TMP=$(mktemp --suffix="$tmp_ext")
trap 'rm -f "$meas" "$TMP"' EXIT

CEILING=0
LTP=$TP
if [ "$MODE" = peak ]; then
  # Transparent gain to the ceiling. AAC re-encoding can add inter-sample peak
  # overshoot, so correction re-encodes (still from the original) cover it.
  GAIN=$(awk -v tp="$TP0" 'BEGIN{if (tp ~ /inf/ || tp == "N/A") print 0; else printf "%.3f", -tp}')
  echo "mode  : peak (gain ${GAIN} dB, ceiling ${CEILING} dBTP)"
else
  CEILING=$TP
  echo "mode  : loud (two-pass EBU R128 → I=${TARGET} LUFS, TP=${TP} dBTP)"
fi

# Two-pass dynamic loudnorm (pass 1 measures, pass 2 applies time-varying gain to hit
# the I/TP targets; loudnorm runs at 192 kHz internally, so resample back to the source
# rate). Rebuilt per correction pass: loud mode re-targets loudnorm's TP instead of
# appending volume, so re-holding I costs nothing; peak mode's gain never changes.
build_af() {
  if [ "$MODE" = peak ]; then
    AF="volume=${GAIN}dB,alimiter=level=false:limit=1.0"
  else
    AF="loudnorm=I=${TARGET}:TP=${1}:LRA=11:measured_I=${I0}:measured_TP=${TP0}:measured_LRA=${LRA0}:measured_thresh=${TH0}:linear=false,alimiter=level=false:limit=1.0,aresample=${SR}"
  fi
}
build_af "$LTP"

encode() { # $1 = gain suffix applied after loudnorm/limiter (must not be re-normalized)
  local rc=0
  ffmpeg -hide_banner -nostdin -err_detect ignore_err -y -i "$INPUT" \
    -map 0:v:0 -map 0:a:0 -c:v copy \
    -af "${AF}${1}" -c:a aac -b:a "$ABIT" \
    -movflags +faststart "$TMP" || rc=$?
  if [ "$rc" -ne 0 ]; then
    # Concat'd mkvs can trip a spurious EOF "Conversion failed!" (exit 69) after all
    # frames are written. Tolerate it only when the output is actually complete.
    local in_dur out_dur
    in_dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$INPUT" 2>/dev/null)
    out_dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$TMP" 2>/dev/null)
    awk -v a="$in_dur" -v b="$out_dur" 'BEGIN{exit !((a+0)>0 && (b+0)>0 && (a-b)<3 && (b-a)<3)}' \
      || { echo "error: ffmpeg encode failed (rc=$rc, in=${in_dur}s out=${out_dur}s)" >&2; exit 1; }
  fi
}
encode ""

# AAC re-encoding adds variable inter-sample overshoot, so iterate until the encode
# lands under the ceiling. Loud mode re-targets loudnorm's TP (it re-holds I on
# target; a trailing volume would drag I down with it) and everything falls back to
# accumulating trailing volume. The temp file only becomes $OUT if it verifies.
VOL=0
for pass in 1 2 3 4 5; do
  OVER=$(overshoot "$TMP" "$CEILING") || break
  [ -z "$OVER" ] && break
  if [ "$MODE" = loud ] && [ "$pass" -le 3 ]; then
    LTP=$(awk -v t="$LTP" -v o="$OVER" 'BEGIN{printf "%.2f", t-o}')
    echo "correcting: pass $pass landed ${OVER} dB over the ceiling, re-encoding (TP=${LTP})"
    build_af "$LTP"
    encode ""
  else
    VOL=$(awk -v v="$VOL" -v o="$OVER" 'BEGIN{printf "%.3f", v-o}')
    echo "correcting: pass $pass landed ${OVER} dB over the ceiling, re-encoding (volume=${VOL} dB)"
    encode ",volume=${VOL}dB"
  fi
done

final=$(measure "$TMP")
TP1=$(jq -r '.input_tp // "N/A"' <<<"$final")
I1=$(jq -r '.input_i // "N/A"' <<<"$final")
case "$TP1" in
  ''|N/A|*[Ii]nf*)
    echo "error: cannot verify true peak of the output (measured ${TP1})" >&2
    exit 1 ;;
esac
awk -v tp="$TP1" -v c="$CEILING" 'BEGIN{exit !(tp <= c + 0.01)}' || {
  echo "error: output landed at ${TP1} dBTP, over the ${CEILING} dBTP ceiling" >&2
  exit 1
}

mv "$TMP" "$OUT"
rm -f "$meas"
trap - EXIT
echo "after : I=${I1} LUFS  true-peak=${TP1} dBTP"
echo "done  : $OUT"
