#!/usr/bin/env bash
set -euo pipefail
WORKDIR="$1"
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES="PhotoJournal/Resources"
mkdir -p "$WORKDIR/$RESOURCES"
cp "$TASK_DIR/reference/$RESOURCES/Localizable.xcstrings" "$WORKDIR/$RESOURCES/Localizable.xcstrings"
cp "$TASK_DIR/reference/$RESOURCES/InfoPlist.xcstrings" "$WORKDIR/$RESOURCES/InfoPlist.xcstrings"
