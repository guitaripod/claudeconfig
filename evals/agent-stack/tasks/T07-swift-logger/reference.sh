#!/usr/bin/env bash
set -euo pipefail

WORKDIR="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"

cp "$HERE"/reference/Sources/PhotoJournalCore/*.swift "$WORKDIR/Sources/PhotoJournalCore/"
