#!/usr/bin/env bash
set -eu
WORKDIR="$1"
LINE="$(grep -n 'db.pool.max_size=0' "$WORKDIR/logs/app.log" | cut -d: -f1)"
if [ "$(printf '%s\n' "$LINE" | grep -c .)" -ne 1 ]; then
  echo "expected exactly one root-cause line" >&2
  exit 1
fi
echo "$LINE"
echo "The 14:31:52 billing-api config reload set db.pool.max_size=0, so every connection acquire timed out from 14:31:55 until the pool was exhausted and billing-api crashed at 14:32:07."
