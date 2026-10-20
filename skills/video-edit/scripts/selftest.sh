#!/usr/bin/env bash
# selftest.sh [workdir] — end-to-end regression check on synthetic fixtures.
# Builds a tiny 14s song + three synthetic sources, runs the beat path (hype)
# and the footage-led path (calm, no audio), and asserts QC is green on both.
# Also asserts a project without a preset is refused. Prints SELFTEST PASS.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
W="${1:-$(mktemp -d /tmp/video-edit-selftest.XXXXXX)}"
mkdir -p "$W/music/src" "$W/calm/src"

echo "== fixtures"
for i in 0 1 2; do
  ffmpeg -nostdin -v error -y -f lavfi -i "testsrc2=size=640x360:rate=30:duration=10" \
    -vf "hue=h=$((i*110)):s=1.3" -c:v libx264 -preset veryfast -pix_fmt yuv420p -an \
    "$W/music/src/src$i.mp4"
  cp "$W/music/src/src$i.mp4" "$W/calm/src/"
done
ffmpeg -nostdin -v error -y -f lavfi \
  -i "aevalsrc='0.7*sin(2*PI*60*t)*exp(-45*mod(t\,0.5))':s=44100:d=14" \
  -c:a pcm_s24le "$W/song.wav"

echo "== setup"
bash "$HERE/setup.sh" "$W/music" >/dev/null
bash "$HERE/setup.sh" "$W/calm" >/dev/null
PY="$W/music/py"
domain() { python3 - "$1" <<'PY'
import json, sys
p = sys.argv[1] + "/project.json"
c = json.load(open(p)); c["domain"] = "generic"; c["motion_floor"] = 0.01
json.dump(c, open(p, "w"), indent=1)
PY
}

echo "== beat path (hype)"
"$PY" "$HERE/extract_audio.py" "$W/music" "$W/song.wav" --preset hype --w 640 --h 360 --fps 30 >/dev/null
domain "$W/music"
"$PY" "$HERE/scenes.py" "$W/music" >/dev/null
"$PY" "$HERE/colorscan.py" "$W/music" >/dev/null
"$PY" "$HERE/beat_spine.py" "$W/music" >/dev/null
"$PY" "$HERE/assign_clips.py" "$W/music" >/dev/null
python3 "$HERE/render.py" "$W/music" --draft >/dev/null
python3 "$HERE/render.py" "$W/music" >/dev/null
python3 "$HERE/qc.py" "$W/music" >/dev/null
python3 "$HERE/deliver.py" "$W/music" --name selftest >/dev/null
test -s "$W/music/out/selftest_vertical.mp4"

echo "== footage path (calm, no audio)"
"$PY" "$HERE/init.py" "$W/calm" --preset calm --duration 12 --w 640 --h 360 --fps 30 >/dev/null
domain "$W/calm"
"$PY" "$HERE/scenes.py" "$W/calm" >/dev/null
"$PY" "$HERE/colorscan.py" "$W/calm" >/dev/null
"$PY" "$HERE/scene_timeline.py" "$W/calm" >/dev/null
"$PY" "$HERE/assign_clips.py" "$W/calm" >/dev/null
python3 "$HERE/render.py" "$W/calm" >/dev/null
python3 "$HERE/qc.py" "$W/calm" >/dev/null
test -s "$W/calm/out/edit.mp4"

echo "== preset guard"
mkdir -p "$W/bad"
echo '{}' > "$W/bad/project.json"
if "$PY" "$HERE/assign_clips.py" "$W/bad" >/dev/null 2>&1; then
  echo "FAIL: a project without a preset was accepted"; exit 1
fi

echo "SELFTEST PASS ($W)"
