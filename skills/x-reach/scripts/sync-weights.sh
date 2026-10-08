#!/usr/bin/env bash
# Re-pull production-synced defaults from xai-org/x-algorithm into refs/current-weights.md.
# Keeps the old sync timestamp when values are unchanged; prints a diff of changed rows.
set -euo pipefail
mkdir -p refs
cd "$(dirname "$0")/.."

REPO="${X_ALGO_REPO:-https://raw.githubusercontent.com/xai-org/x-algorithm/main}"
OUT="refs/current-weights.md"
PREV="$(mktemp)"

cp "$OUT" "$PREV" 2>/dev/null || true

python3 - "$REPO" "$OUT" "$PREV" <<'PY'
import re
import sys
import urllib.request
from datetime import datetime, timezone

base, out, prev = sys.argv[1], sys.argv[2], sys.argv[3]
PARAM = re.compile(r'param!\(\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*,\s*"([^"]+)"\s*,\s*(.*?)\)\s*;', re.S)

# name -> reach-relevant defaults worth tracking
keep = {
    "FavoriteWeight", "ReplyWeight", "RetweetWeight", "PhotoExpandWeight", "VideoOpenWeight",
    "ClickWeight", "OpenLinkWeight", "ProfileClickWeight", "VqvWeight", "ShareWeight",
    "ShareViaDmWeight", "ShareViaCopyLinkWeight", "DwellWeight", "QuoteWeight",
    "QuotedClickWeight", "QuotedVqvWeight", "FollowAuthorWeight", "PostUnexploredWeight",
    "ContDwellTimeWeight", "ContClickDwellTimeWeight", "VideoContinuationWeight",
    "UserVideoContinuationWeight", "ProfileVisitSecsWeight", "NotInterestedWeight",
    "BlockAuthorWeight", "MuteAuthorWeight", "ReportWeight", "NotDwelledWeight",
    "MinVideoDurationMs", "EnableQuotedVqvDurationCheck",
    "BidirectionalFollowReplyWeightBoost", "BidirectionalFollowDwellWeightBoost",
    "EnableAuthorDiversity", "AuthorDiversityDecay", "AuthorDiversityFloor",
    "EnableOonRescoreForInNetworkRepliesRetweets", "OonWeightFactor", "TopicOonWeightFactor",
    "NewUserOonWeightFactor", "WeightPerturbationSigma",
    "ColdStartImpressionThreshold", "ColdStartSlotMin", "ColdStartSlotMax",
    "ColdStartFollowerCap", "ColdStartMaxPostAgeSecs", "LowImpressionsMaxPositionRatio",
    "EnableViewerColdStart", "EnableColdStartThompsonSampling", "ColdStartBetaAlpha0",
    "ColdStartBetaBeta0", "ColdStartTsTopK", "ColdStartImpressionScale",
    "DppEnabled", "DppTheta", "DppMaxSelectedRank",
    "EnablePopularPostsSource", "PopularPostsMaxResults", "SimclustersMaxCandidateAgeHours",
    "EnablePhoenixOonReplies",
}

rows = {}
for path in ("vm-ranker/params.rs", "home-mixer/params/param.rs"):
    src = urllib.request.urlopen(f"{base}/{path}", timeout=30).read().decode()
    for name, ty, flag, default in PARAM.findall(src):
        if name in keep and name not in rows:
            rows[name] = (path, ty, flag, default.strip())

body = [
    "| param | type | default | source |",
    "|---|---|---|---|",
]
for name in sorted(rows, key=lambda n: (rows[n][0], n)):
    path, ty, flag, default = rows[name]
    body.append(f"| `{name}` | {ty} | {default} | `{path}` |")
body += [
    "",
    "Other fixed facts (re-verify in-repo before quoting):",
    "- MAX_POST_AGE = 48h (`home-mixer/params/config.rs`)",
    "- Popular-posts pool: 24h window, 8h view half-life, 5 per author, 500 budget, refreshed hourly, seeded from top 0.005% of active posters by followers (`home-mixer/util/popular_posts.rs`, `util/popular_authors.rs`)",
    "- User-cred: score = clamp(165.2 + 7.07·ln(mass), 0, 100); >= 50 or is_high skips most enforcement (`user-cred-v2/UserCredV2.scala`)",
    "- PTOS high-fav screen threshold: 128 favs (`grox/flows/ptos/constants.py`)",
]

ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
old = ""
try:
    old = open(prev).read()
except FileNotFoundError:
    old = ""
old_body = old.split("\n", 3)[3] if old else None
if old_body == "\n".join(body) + "\n":
    print(f"unchanged ({len(rows)} params); keeping sync timestamp")
else:
    doc = f"# X For You — synced production defaults\nsynced: {ts} UTC from xai-org/x-algorithm@main\n" + "\n".join(body) + "\n"
    open(out, "w").write(doc)
    print(f"wrote {out} ({len(rows)} params)")
PY

if [ -s "$PREV" ]; then
    echo "--- diff (old -> new) ---"
    diff "$PREV" "$OUT" | grep -E '^[<>]' | grep -vE '^[<>] synced:' || echo "(no changes)"
fi
rm -f "$PREV"
