#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${1:?usage: reference.sh WORKDIR}"
HERE="$(cd "$(dirname "$0")" && pwd)"

cp -R "$HERE/reference/src/." "$WORKDIR/src/"
