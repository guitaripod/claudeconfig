#!/usr/bin/env bash
set -eu
WORKDIR="$1"
test -f "$WORKDIR/config/llama-swap.yaml"
test -f "$WORKDIR/config/models.toml"
printf '%s\n' \
  'pickerless: brisk-7b, hollow-22b, marl-8b, nettle-3b' \
  'drift: coral-12b, corvid-27b, sable-32b'
