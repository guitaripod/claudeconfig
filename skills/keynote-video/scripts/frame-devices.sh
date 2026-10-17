#!/bin/bash
set -euo pipefail
out="$1"
color="$2"
shift 2
mkdir -p "$out"
frames doctor >/dev/null
for f in "$@"; do
  frames --json info "$f" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['name'], '->', d['device'], d['width'], 'x', d['height'])"
done
if [ "$color" = "default" ]; then
  frames frame --output "$out" "$@" >/dev/null
else
  frames frame --color "$color" --output "$out" "$@" >/dev/null
fi
ls "$out"
