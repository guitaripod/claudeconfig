#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${1:?usage: setup.sh WORKDIR}"
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$WORKDIR"
if [ -n "$(ls -A "$WORKDIR")" ]; then
  echo "setup.sh: WORKDIR must be empty: $WORKDIR" >&2
  exit 1
fi

cp -R "$HERE/fixture/." "$WORKDIR/"
cd "$WORKDIR"
git init -q -b master \
  && git add -A \
  && GIT_AUTHOR_DATE="2026-01-01T00:00:00Z" GIT_COMMITTER_DATE="2026-01-01T00:00:00Z" \
     git -c user.name=eval -c user.email=eval@example.com commit -qm init
