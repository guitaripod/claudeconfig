#!/usr/bin/env bash
# fetch.sh — kept for older notes; ingest.sh is the current entry point.
exec "$(dirname "$0")/ingest.sh" "$@"
