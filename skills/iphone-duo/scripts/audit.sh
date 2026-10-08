#!/usr/bin/env bash
# Scan an iOS project for patterns that break on iPhone Duo.
#
# iPhone Duo moves an app's scene between a 466x678 pt outer display and a 669x951 pt inner
# display while it runs, and puts status, navigation, toolbars and tab bars on a vertical edge
# instead of at the top and bottom. This finds the source patterns that break under that,
# grouped into the fix order used by the iphone-duo skill.
#
#   scripts/audit.sh [ROOT]        scan ROOT (default: current directory)
#   scripts/audit.sh --tier 2      only one tier
#   scripts/audit.sh --review      also show the review-only hits, not just counts
#   scripts/audit.sh --json        machine-readable findings
#
# Exit codes: 0 clean, 1 defects found, 2 usage error.
#
# Detection is grep-based and needs no SDK, so it runs before the iOS 27.1 toolchain exists.
# Findings are signals, not verdicts. Each pattern is tagged DEFECT (wrong on Duo) or REVIEW
# (needs a human-sized judgement, not necessarily wrong). Replacement rules live in
# references/audit-rules.md of the iphone-duo skill.
set -euo pipefail

TIER_FIL=""
SHOW_REVIEW=0
JSON_OUT=0
ROOT="."

usage() {
  printf 'usage: audit.sh [--tier 1|2|3|4] [--review] [--json] [ROOT]\n' >&2
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tier) TIER_FIL="${2:-}"; shift 2 ;;
    --review) SHOW_REVIEW=1; shift ;;
    --json) JSON_OUT=1; shift ;;
    -h|--help) usage ;;
    -*) usage ;;
    *) ROOT="$1"; shift ;;
  esac
done

case "$TIER_FIL" in
  ""|1|2|3|4) ;;
  *) usage ;;
esac

[ -d "$ROOT" ] || { printf 'audit.sh: not a directory: %s\n' "$ROOT" >&2; exit 2; }
ROOT="$(cd "$ROOT" && pwd)"

GLOBS=(
  --glob '*.swift'
  --glob '*.m'
  --glob '*.mm'
  --glob '*.h'
  --glob '*.plist'
  --glob '*.xcconfig'
  --glob '!**/.build/**'
  --glob '!**/build/**'
  --glob '!**/DerivedData/**'
  --glob '!**/Pods/**'
  --glob '!**/.git/**'
  --glob '!**/xcuserdata/**'
)

TIER_TITLES=(
  [1]="screen, orientation, idiom"
  [2]="safe areas and layout margins"
  [3]="bars"
  [4]="plumbing"
)

TIER_HINTS=(
  [1]="The question this tier answers is wrong on Duo: what device am I on, and which way is it rotated. Neither is knowable when the display changes and the device folds mid-session."
  [2]="A vertical bar means one horizontal edge carries the whole inset while the opposite edge carries zero. Symmetric-inset code is wrong by default, and iOS 27.1 made a UIView's default layout margins zero."
  [3]="Only bars owned by a navigation container go vertical. Custom UIToolbar, UINavigationBar, UITabBar and hand-rolled HStack toolbars stay horizontal."
  [4]="Read-only checks. Report findings; never delete or add Info.plist keys silently."
)

declare -a PATTERN_TIER PATTERN_KIND PATTERN_LABEL PATTERN_REGEX

add_pattern() {
  PATTERN_TIER+=("$1")
  PATTERN_KIND+=("$2")
  PATTERN_LABEL+=("$3")
  PATTERN_REGEX+=("$4")
}

add_pattern 1 DEFECT "UIScreen.main" 'UIScreen[[:space:]]*\.[[:space:]]*main|\[UIScreen[[:space:]]+mainScreen\]'
add_pattern 1 DEFECT "interface orientation in layout" 'statusBarOrientation|interfaceOrientation'
add_pattern 1 DEFECT "device orientation" 'UIDevice[[:space:]]*\.[[:space:]]*current[[:space:]]*\.[[:space:]]*orientation'
add_pattern 1 DEFECT "user interface idiom" 'userInterfaceIdiom|UI_USER_INTERACE_IDIOM|UI_USER_INTERFACE_IDIOM'
add_pattern 1 DEFECT "hardcoded display dimension" 'bounds[[:space:]]*\.(height|width)[[:space:]]*==[[:space:]]*[0-9]+'
add_pattern 1 REVIEW  "size class comparisons" 'horizontalSizeClass[[:space:]]*(==|!=)|verticalSizeClass[[:space:]]*(==|!=)'

add_pattern 2 DEFECT "deprecated layout guides" 'topLayoutGuide|bottomLayoutGuide'
add_pattern 2 DEFECT "doubled horizontal inset" 'safeAreaInsets[[:space:]]*\.[[:space:]]*(left|right)[[:space:]]*\*[[:space:]]*2'
add_pattern 2 DEFECT "one edge reused for both" 'safeAreaInsets[[:space:]]*\.[[:space:]]*(left|right).*safeAreaInsets[[:space:]]*\.[[:space:]]*(left|right)|safeAreaInsets[[:space:]]*\.[[:space:]]*top.*safeAreaInsets[[:space:]]*\.[[:space:]]*bottom'
add_pattern 2 DEFECT "inset threshold as a layout gate" 'safeAreaInsets[[:space:]]*\.[[:space:]]*(left|right|top|bottom)[[:space:]]*>[[:space:]]*[0-9]'
add_pattern 2 DEFECT "scroll view refuses inset adjustment" 'contentInsetAdjustmentBehavior[[:space:]]*=[[:space:]]*\.never'
add_pattern 2 DEFECT "hand-rolled keyboard avoidance" 'UIKeyboardWillShow|UIKeyboardWillChangeFrame|UIKeyboardFrameEndUserInfoKey'
add_pattern 2 DEFECT "unscoped ignoresSafeArea" 'ignoresSafeArea\([[:space:]]*\)'
add_pattern 2 DEFECT "system minimum margins disabled" 'viewRespectsSystemMinimumLayoutMargins[[:space:]]*=[[:space:]]*(false|NO)'
add_pattern 2 REVIEW  "inset written into system insets" 'additionalSafeAreaInsets'
add_pattern 2 REVIEW  "layout margins in play" 'layoutMargins|preservesSuperviewLayoutMargins|systemMinimumLayoutMargins'

add_pattern 3 DEFECT "custom bar construction" '(UIToolbar|UINavigationBar|UITabBar)[[:space:]]*\([[:space:]]*\)'
add_pattern 3 REVIEW  "toolbar items to review" 'ToolbarItem[[:space:]]*\(|UIBarButtonItem[[:space:]]*\('
add_pattern 3 REVIEW  "vertical bar API already adopted" 'toolbarVerticalBehavior|preferredVerticalBarBehavior|toolbarVerticalCompressionBehavior|verticalBarCompressionBehavior|toolbarVerticalEdge|verticalBarEdge'
add_pattern 3 REVIEW  "axis and overflow configured" 'axisBehavior|visibilityPriority|additionalOverflowItems|ToolbarOverflowMenu'

add_pattern 4 DEFECT "UIRequiresFullScreen" 'UIRequiresFullScreen'
add_pattern 4 REVIEW  "launch screen declaration" 'UILaunchScreen|UILaunchScreens|UILaunchStoryboardName|UILaunchStoryboards|INFOPLIST_KEY_UILaunchScreen_Generation'
add_pattern 4 REVIEW  "supported interface orientations" 'UISupportedInterfaceOrientations'
add_pattern 4 REVIEW  "app delegate lifecycle" 'UIApplicationDelegate|didFinishLaunchingWithOptions'

scan() {
  local regex="$1"
  if command -v rg >/dev/null 2>&1; then
    rg --line-number --no-heading --smart-case "${GLOBS[@]}" -e "$regex" "$ROOT" 2>/dev/null || true
  else
    grep -rnE \
      --include='*.swift' --include='*.m' --include='*.mm' \
      --include='*.h' --include='*.plist' --include='*.xcconfig' \
      --exclude-dir=build --exclude-dir=DerivedData --exclude-dir=.build \
      --exclude-dir=Pods --exclude-dir=.git --exclude-dir=xcuserdata \
      -e "$regex" "$ROOT" 2>/dev/null || true
  fi
}

json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

defect_total=0
review_total=0

printf 'audit.sh: scanning %s\n\n' "$ROOT"

for tier in 1 2 3 4; do
  if [ -n "$TIER_FIL" ] && [ "$TIER_FIL" != "$tier" ]; then
    continue
  fi

  tier_defects=0
  tier_reviews=0
  defect_report=""
  review_report=""
  defect_detail=""
  review_detail=""

  for i in "${!PATTERN_TIER[@]}"; do
    if [ "${PATTERN_TIER[$i]}" != "$tier" ]; then
      continue
    fi

    hits="$(scan "${PATTERN_REGEX[$i]}")"
    if [ -z "$hits" ]; then
      continue
    fi

    count="$(printf '%s\n' "$hits" | grep -c . || true)"
    row="$(printf '%-46s %5s' "${PATTERN_LABEL[$i]}" "$count")"

    if [ "${PATTERN_KIND[$i]}" = "DEFECT" ]; then
      tier_defects=$((tier_defects + count))
      defect_report+="$row"$'\n'
      defect_detail+="-- ${PATTERN_LABEL[$i]}"$'\n'"$hits"$'\n'
    else
      tier_reviews=$((tier_reviews + count))
      review_report+="$row"$'\n'
      review_detail+="-- ${PATTERN_LABEL[$i]}"$'\n'"$hits"$'\n'
    fi
  done

  defect_total=$((defect_total + tier_defects))
  review_total=$((review_total + tier_reviews))

  if [ "$JSON_OUT" -eq 0 ]; then
    printf '## Tier %s — %s\n%s\n\n' "$tier" "${TIER_TITLES[$tier]}" "${TIER_HINTS[$tier]}"

    if [ "$tier_defects" -gt 0 ]; then
      printf 'DEFECTS (%s):\n%-46s %5s\n' "$tier_defects" "pattern" "hits"
      printf '%s' "$defect_report"
      printf '\n%s' "$defect_detail"
    else
      printf 'DEFECTS: none\n'
    fi

    if [ "$tier_reviews" -gt 0 ]; then
      printf '\nREVIEW (%s):\n%-46s %5s\n' "$tier_reviews" "pattern" "hits"
      printf '%s' "$review_report"
      if [ "$SHOW_REVIEW" -eq 1 ]; then
        printf '\n%s' "$review_detail"
      else
        printf '\n(rerun with --review for file:line)\n'
      fi
    fi
    printf '\n'
  else
    for i in "${!PATTERN_TIER[@]}"; do
      if [ "${PATTERN_TIER[$i]}" != "$tier" ]; then
        continue
      fi
      hits="$(scan "${PATTERN_REGEX[$i]}")"
      if [ -z "$hits" ]; then
        continue
      fi
      count="$(printf '%s\n' "$hits" | grep -c . || true)"
      printf '{"tier":%s,"kind":"%s","pattern":"%s","hits":%s}\n' \
        "$tier" "${PATTERN_KIND[$i]}" "$(json_escape "${PATTERN_LABEL[$i]}")" "$count"
    done
  fi
done

printf 'audit.sh: %s defects, %s review hits in %s\n' "$defect_total" "$review_total" "$ROOT"
printf 'Replacement rules: references/audit-rules.md in the iphone-duo skill.\n'

if [ "$defect_total" -gt 0 ]; then
  exit 1
fi
exit 0
