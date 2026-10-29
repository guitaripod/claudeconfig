#!/usr/bin/env bash
set -eu
WORKDIR="$1"
grep -q 'fn skip_filesize(' "$WORKDIR/crates/ignore/src/walk.rs"
grep -q 'fn write_exceeded_line(' "$WORKDIR/crates/printer/src/standard.rs"
grep -q 'fn should_decompress(' "$WORKDIR/crates/core/search.rs"
printf '%s\n' \
  '1. crates/ignore/src/walk.rs: skip_filesize' \
  '2. crates/printer/src/standard.rs: write_exceeded_line' \
  '3. crates/core/search.rs: should_decompress'
