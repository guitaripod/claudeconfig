#!/usr/bin/env bash
set -euo pipefail
WORKDIR="$1"
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$WORKDIR"
cp -R "$TASK_DIR/fixture/." "$WORKDIR/"
cd "$WORKDIR"
git init -q -b master
git add -A
git -c user.name=eval -c user.email=eval@example.com commit -qm init
