#!/usr/bin/env bash
set -eu
WORKDIR="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$WORKDIR/logs"
python3 "$HERE/hidden/gen_log.py" "$WORKDIR"
cat > "$WORKDIR/README.md" <<'EOF'
# Payments platform logs

One synthetic day of logs, 2026-04-14, 13:00:00 to 14:33:00, from five services:

- gateway: public HTTP edge; routes /v1 requests to the backend services.
- billing-api: charges and invoices; uses a PostgreSQL connection pool.
- ledger-worker: writes ledger entries from a write-ahead log on /data/ledger.
- auth: issues and verifies access tokens.
- search: queries index shards.

Everything is in `logs/app.log`, one file ordered by time. Each line is `timestamp LEVEL service message`.
EOF
