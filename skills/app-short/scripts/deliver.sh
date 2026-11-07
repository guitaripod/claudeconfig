#!/usr/bin/env bash
# Send finished shorts to Marcus's Telegram through the hypebot bot, each with its caption.
# Usage: deliver.sh video.mp4 [video2.mp4 ...]   (caption = the same path with .txt instead of .mp4)
set -euo pipefail

set -a
source "$HOME/.config/hypebot/secrets.env"
set +a

for video in "$@"; do
    caption_file="${video%.mp4}.txt"
    [[ -f "$caption_file" ]] || { echo "missing caption $caption_file" >&2; exit 1; }
    curl -sS --fail-with-body \
        -F chat_id="$HYPEBOT_CHAT_ID" \
        -F video=@"$video" \
        -F caption="$(cat "$caption_file")" \
        -F supports_streaming=true \
        -F width=1080 -F height=1920 \
        "https://api.telegram.org/bot${HYPEBOT_TOKEN}/sendVideo" \
        | python3 -I -c 'import json,sys; r=json.load(sys.stdin); print("sent" if r.get("ok") else r)'
done
