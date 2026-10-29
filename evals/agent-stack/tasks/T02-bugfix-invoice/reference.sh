#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${1:?usage: reference.sh WORKDIR}"
HERE="$(cd "$(dirname "$0")" && pwd)"

cp "$HERE/reference/invoicer/discounts.py" "$WORKDIR/invoicer/discounts.py"
cp "$HERE/reference/invoicer/tax.py" "$WORKDIR/invoicer/tax.py"
