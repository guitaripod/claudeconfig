#!/usr/bin/env bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="$1"
mkdir -p "$WORKDIR"
cp -R "$HERE/fixture/." "$WORKDIR/"
