#!/usr/bin/env bash
set -eu
WORKDIR="$1"
CACHE="${EVAL_CACHE:?EVAL_CACHE must be set}"
SRC="$CACHE/ripgrep-14.1.1"
if [ ! -d "$SRC" ]; then
  mkdir -p "$CACHE"
  TMP="$CACHE/ripgrep-14.1.1.tmp.$$"
  rm -rf "$TMP"
  git clone --depth 1 --branch 14.1.1 https://github.com/BurntSushi/ripgrep "$TMP"
  mv "$TMP" "$SRC"
fi
mkdir -p "$WORKDIR"
tar -C "$SRC" --exclude=.git -cf - . | tar -C "$WORKDIR" -xf -
