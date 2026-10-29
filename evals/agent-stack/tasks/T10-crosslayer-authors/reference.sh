#!/usr/bin/env bash
set -euo pipefail
WORKDIR="$1"
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
cp -R "$TASK_DIR/reference/." "$WORKDIR/"
