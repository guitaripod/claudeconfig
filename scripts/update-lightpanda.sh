#!/bin/bash
# Installs the latest Lightpanda release into ~/.cargo/bin when it is newer than
# the installed one. Run daily by the timer link.sh installs, and by link.sh itself.
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

INSTALL_DIR="$HOME/.cargo/bin"
BIN="$INSTALL_DIR/lightpanda"
REPO="lightpanda-io/browser"
RELEASE_API="https://api.github.com/repos/$REPO/releases/latest"

# GitHub answers anonymous API calls from this network with 504s, so the gh
# login goes first and anonymous curl is the fallback when gh is missing or fails.
latest_release_json() {
    gh api "repos/$REPO/releases/latest" 2>/dev/null \
        || curl -fsSL --retry 3 --max-time 60 -H 'Accept: application/vnd.github+json' "$RELEASE_API"
}

download_asset() {
    local tag="$1" asset="$2" url="$3" dest="$4"
    gh release download "$tag" -R "$REPO" -p "$asset" -O "$dest" --clobber 2>/dev/null \
        || curl -fsSL --retry 3 --max-time 600 -o "$dest" "$url"
}

asset_name() {
    case "$(uname -s)-$(uname -m)" in
        Linux-x86_64) echo lightpanda-x86_64-linux ;;
        Linux-aarch64 | Linux-arm64) echo lightpanda-aarch64-linux ;;
        Darwin-arm64 | Darwin-aarch64) echo lightpanda-aarch64-macos ;;
        Darwin-x86_64) echo lightpanda-x86_64-macos ;;
        *) echo "unsupported platform $(uname -s)-$(uname -m)" >&2; return 1 ;;
    esac
}

sha256_of() {
    if command -v sha256sum >/dev/null; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

# A release only replaces the installed binary once it reports its own tag and
# renders a page, so a broken build never reaches the MCP servers.
smoke_test() {
    local candidate="$1" tag="$2"
    [ "$("$candidate" version 2>/dev/null)" = "$tag" ] || return 1
    timeout 30 "$candidate" fetch --dump markdown 'data:text/html,<h1>lightpandasmoke</h1>' 2>/dev/null \
        | grep -q 'lightpandasmoke'
}

main() {
    local asset release tag url digest installed tmp
    asset="$(asset_name)"
    release="$(latest_release_json)"
    tag="$(jq -r '.tag_name' <<<"$release")"
    url="$(jq -r --arg a "$asset" '.assets[] | select(.name == $a) | .browser_download_url' <<<"$release")"
    digest="$(jq -r --arg a "$asset" '.assets[] | select(.name == $a) | .digest' <<<"$release")"
    digest="${digest#sha256:}"
    if [ -z "$tag" ] || [ "$tag" = null ] || [ -z "$url" ] || [ -z "$digest" ] || [ "$digest" = null ]; then
        echo "lightpanda: release $tag has no $asset with a digest" >&2
        exit 1
    fi

    installed="$("$BIN" version 2>/dev/null || true)"
    if [ "$installed" = "$tag" ]; then
        echo "lightpanda $tag is current"
        return
    fi

    mkdir -p "$INSTALL_DIR"
    tmp="$(mktemp "$INSTALL_DIR/.lightpanda.XXXXXX")"
    trap 'rm -f "$tmp"' EXIT
    download_asset "$tag" "$asset" "$url" "$tmp"
    if [ "$(sha256_of "$tmp")" != "$digest" ]; then
        echo "lightpanda: $tag checksum mismatch, keeping ${installed:-nothing}" >&2
        exit 1
    fi
    chmod 755 "$tmp"
    if ! smoke_test "$tmp" "$tag"; then
        echo "lightpanda: $tag failed its smoke test, keeping ${installed:-nothing}" >&2
        exit 1
    fi
    mv -f "$tmp" "$BIN"
    trap - EXIT
    echo "lightpanda ${installed:-none} -> $tag"
}

main "$@"
