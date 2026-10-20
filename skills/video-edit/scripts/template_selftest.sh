#!/usr/bin/env bash
# template_selftest.sh [workdir] — exercise every template capability end to end:
# product (overlays + speed cycle + silence), broadcast (replay speed + wipes),
# stills/photo, documentary (pinned A-roll + B-roll + captions) and compare.
# Each path renders at 320x180 and must pass QC. Prints TEMPLATE SELFTEST PASS.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
W="${1:-$(mktemp -d /tmp/video-edit-tpl.XXXXXX)}"
mkdir -p "$W/fixtures"
F="$W/fixtures"

clip() { ffmpeg -nostdin -v error -y -f lavfi -i "testsrc2=size=640x360:rate=30:duration=$1" \
  -vf "hue=h=$2:s=1.3" -c:v libx264 -preset veryfast -pix_fmt yuv420p -an "$3"; }
tone() { ffmpeg -nostdin -v error -y -f lavfi \
  -i "aevalsrc='0.7*sin(2*PI*60*t)*exp(-45*mod(t\,0.5))':s=44100:d=$1" -c:a pcm_s24le "$2"; }
prep() { bash "$HERE/setup.sh" "$1" >/dev/null; }
generic() { python3 - "$1" <<'PY'
import json, sys
p = sys.argv[1] + "/project.json"; c = json.load(open(p))
c["domain"] = "generic"; c["motion_floor"] = 0.005; c["subject"] = "none"
json.dump(c, open(p, "w"), indent=1)
PY
}

for i in 0 1 2 3; do clip 10 $((i*90)) "$F/c$i.mp4"; done
tone 10 "$F/song.wav"
ffmpeg -nostdin -v error -y -f lavfi -i "testsrc2=size=640x360" -frames:v 1 "$F/a.png"
ffmpeg -nostdin -v error -y -f lavfi -i "testsrc2=size=640x360" -vf "hue=h=120" -frames:v 1 "$F/b.png"

echo "== product: overlays + speed cycle + silence"
P="$W/product"; mkdir -p "$P/src"; cp "$F"/c0.mp4 "$F"/c1.mp4 "$F"/c2.mp4 "$P/src/"; cp "$F/song.wav" "$P/"
prep "$P"; "$P/py" "$HERE/extract_audio.py" "$P" "$P/song.wav" --preset product --w 320 --h 180 >/dev/null
generic "$P"
python3 - "$P" <<'PY'
import json, sys
p = sys.argv[1] + "/project.json"; c = json.load(open(p))
c["overlays"] = [{"text": "NEW DROP: 100%", "start": 0.2, "end": 2.0, "style": "title"}]
c["audio"] = {"silence": [[6.0, 6.5]]}
json.dump(c, open(p, "w"), indent=1)
PY
"$P/py" "$HERE/scenes.py" "$P" >/dev/null; "$P/py" "$HERE/colorscan.py" "$P" >/dev/null
"$P/py" "$HERE/beat_spine.py" "$P" >/dev/null; "$P/py" "$HERE/assign_clips.py" "$P" >/dev/null
python3 "$HERE/render.py" "$P" >/dev/null; python3 "$HERE/qc.py" "$P" >/dev/null
python3 - "$P" <<'PY'
import json, sys
a = json.load(open(sys.argv[1] + "/assign.json"))["segments"]
assert any(abs(s["speed"] - 1.0) > 0.01 for s in a), "speed cycle not applied"
PY

echo "== broadcast: replay speed + wipes"
B="$W/broadcast"; mkdir -p "$B/src"; cp "$F"/c0.mp4 "$F"/c1.mp4 "$F"/c2.mp4 "$B/src/"; cp "$F/song.wav" "$B/"
prep "$B"; "$B/py" "$HERE/extract_audio.py" "$B" "$B/song.wav" --preset broadcast --w 320 --h 180 >/dev/null
generic "$B"
"$B/py" "$HERE/scenes.py" "$B" >/dev/null; "$B/py" "$HERE/colorscan.py" "$B" >/dev/null
"$B/py" "$HERE/beat_spine.py" "$B" >/dev/null; "$B/py" "$HERE/assign_clips.py" "$B" >/dev/null
python3 "$HERE/render.py" "$B" >/dev/null; python3 "$HERE/qc.py" "$B" >/dev/null
python3 - "$B" <<'PY'
import json, sys
a = json.load(open(sys.argv[1] + "/assign.json"))["segments"]
assert min(s["speed"] for s in a) < 0.9, "replay speed not applied"
PY

echo "== stills: photo"
H="$W/photo"; mkdir -p "$H"; prep "$H"
"$H/py" "$HERE/init.py" "$H" --preset photo --duration 12 --w 320 --h 180 >/dev/null
python3 - "$H" <<'PY'
import json, sys
p = sys.argv[1] + "/project.json"; c = json.load(open(p)); c["subject"] = "none"
json.dump(c, open(p, "w"), indent=1)
PY
bash "$HERE/ingest.sh" "$H" "$F/a.png" "$F/b.png" >/dev/null
"$H/py" "$HERE/stills.py" "$H" >/dev/null
"$H/py" "$HERE/scenes.py" "$H" >/dev/null; "$H/py" "$HERE/colorscan.py" "$H" >/dev/null
"$H/py" "$HERE/scene_timeline.py" "$H" >/dev/null; "$H/py" "$HERE/assign_clips.py" "$H" >/dev/null
python3 "$HERE/render.py" "$H" >/dev/null; python3 "$HERE/qc.py" "$H" >/dev/null
test -s "$H/out/edit.mp4"

echo "== documentary: pinned A-roll + B-roll + captions"
D="$W/doc"; mkdir -p "$D/src"
ffmpeg -nostdin -v error -y -f lavfi -i "testsrc2=size=640x360:rate=30:duration=10" \
  -f lavfi -i "sine=frequency=440:duration=10" -c:v libx264 -preset veryfast \
  -pix_fmt yuv420p -c:a aac -shortest "$D/src/aroll.mp4"
clip 10 90 "$D/src/broll0.mp4"; clip 10 180 "$D/src/broll1.mp4"
prep "$D"; "$D/py" "$HERE/extract_audio.py" "$D" "$D/src/aroll.mp4" --preset documentary --w 320 --h 180 >/dev/null
generic "$D"
cat > "$D/cues.srt" <<'SRT'
1
00:00:00,000 --> 00:00:03,000
Hello and welcome to the test.

2
00:00:03,000 --> 00:00:06,000
This chunk should be covered by b-roll.

3
00:00:06,000 --> 00:00:09,800
And back to the speaker to finish.
SRT
"$D/py" "$HERE/scenes.py" "$D" >/dev/null; "$D/py" "$HERE/colorscan.py" "$D" >/dev/null
"$D/py" "$HERE/doc_timeline.py" "$D" --aroll aroll --srt "$D/cues.srt" --chunk 2.5 --broll-every 2 >/dev/null
"$D/py" "$HERE/assign_clips.py" "$D" >/dev/null
python3 "$HERE/render.py" "$D" >/dev/null; python3 "$HERE/qc.py" "$D" >/dev/null
python3 - "$D" <<'PY'
import json, sys
d = sys.argv[1]
t = json.load(open(d + "/timeline.json")); c = json.load(open(d + "/project.json"))
a = json.load(open(d + "/assign.json"))["segments"]
assert t["producer"] == "doc" and len(c["overlays"]) >= 3, "doc overlays missing"
pins = [x["in_tc"] for x in t["cutlist"] if "in_tc" in x]
assert pins == sorted(pins) and pins, "A-roll cuts are not pinned"
PY

echo "== compare: side-by-side"
C="$W/compare"; mkdir -p "$C"; prep "$C"
"$C/py" "$HERE/init.py" "$C" --preset compare --duration 12 --w 320 --h 180 >/dev/null
"$C/py" "$HERE/compare.py" "$C" "$F/c0.mp4:$F/c1.mp4" "$F/c2.mp4:$F/c3.mp4" --duration 5 >/dev/null
"$C/py" "$HERE/scenes.py" "$C" >/dev/null; "$C/py" "$HERE/colorscan.py" "$C" >/dev/null
"$C/py" "$HERE/scene_timeline.py" "$C" >/dev/null; "$C/py" "$HERE/assign_clips.py" "$C" >/dev/null
python3 "$HERE/render.py" "$C" >/dev/null; python3 "$HERE/qc.py" "$C" >/dev/null
test -s "$C/out/edit.mp4"

echo "TEMPLATE SELFTEST PASS ($W)"
