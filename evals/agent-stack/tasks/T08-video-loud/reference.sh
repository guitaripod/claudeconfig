#!/usr/bin/env bash
set -eu
WORKDIR="$1"
bash "$HOME/.claude/skills/video-loud/scripts/loud.sh" "$WORKDIR/clip.mp4" --mode peak 1>&2
