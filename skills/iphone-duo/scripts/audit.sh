#!/usr/bin/env bash
# Scan an iOS project for patterns that break on iPhone Duo.
#
# iPhone Duo moves an app's scene between a 466x678 pt outer display and a 669x951 pt inner
# display while it runs, and puts status, navigation, toolbars and tab bars on a vertical edge
# instead of at the top and bottom. This finds the source patterns that break under that,
# grouped into the fix order used by the iphone-duo skill.
#
#   scripts/audit.sh [ROOT]          scan ROOT (default: current directory)
#   scripts/audit.sh --tier N        only tier N (1-5)
#   scripts/audit.sh --review        also list every review-only hit, not just counts
#   scripts/audit.sh --json          one JSON object per hit on stdout, summary on stderr
#   scripts/audit.sh --exclude GLOB  skip a path or directory glob (repeatable), e.g. '*Tests*'
#
# Exit codes: 0 no defects, 1 defects found, 2 usage error.
#
# Detection is grep-based and needs no SDK, so it runs before the iOS 27.1 toolchain exists.
# Findings are signals, not verdicts. DEFECT is wrong on Duo and gates the exit code; REVIEW
# needs a judgement and never does. Replacement rules live in references/audit-rules.md.
set -euo pipefail

TIER_FIL=""
SHOW_REVIEW=0
JSON_OUT=0
ROOT="."
EXCLUDES=()

usage() {
  printf 'usage: audit.sh [--tier 1-5] [--review] [--json] [--exclude GLOB]... [ROOT]\n' >&2
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tier) TIER_FIL="${2:-}"; shift 2 ;;
    --review) SHOW_REVIEW=1; shift ;;
    --json) JSON_OUT=1; shift ;;
    --exclude) [ -n "${2:-}" ] || usage; EXCLUDES+=("$2"); shift 2 ;;
    -h|--help) usage ;;
    -*) usage ;;
    *) ROOT="$1"; shift ;;
  esac
done

case "$TIER_FIL" in
  ""|1|2|3|4|5) ;;
  *) usage ;;
esac

[ -d "$ROOT" ] || { printf 'audit.sh: not a directory: %s\n' "$ROOT" >&2; exit 2; }
ROOT="$(cd "$ROOT" && pwd)"

RG_ARGS=(
  --glob '*.swift' --glob '*.m' --glob '*.mm' --glob '*.h'
  --glob '*.plist' --glob '*.xcconfig' --glob '*.pbxproj' --glob '*.yml' --glob '*.yaml'
  --glob '!**/.build/**' --glob '!**/build/**' --glob '!**/DerivedData/**'
  --glob '!**/Pods/**' --glob '!**/Carthage/**' --glob '!**/.git/**' --glob '!**/xcuserdata/**'
)
GREP_ARGS=(
  --include='*.swift' --include='*.m' --include='*.mm' --include='*.h'
  --include='*.plist' --include='*.xcconfig' --include='*.pbxproj' --include='*.yml' --include='*.yaml'
  --exclude-dir=.build --exclude-dir=build --exclude-dir=DerivedData
  --exclude-dir=Pods --exclude-dir=Carthage --exclude-dir=.git --exclude-dir=xcuserdata
)
if [ "${#EXCLUDES[@]}" -gt 0 ]; then
  for glob in "${EXCLUDES[@]}"; do
    RG_ARGS+=(--glob "!$glob" --glob "!**/$glob/**")
    GREP_ARGS+=(--exclude="$glob" --exclude-dir="$glob")
  done
fi

TIER_TITLES=(
  [1]="screen, orientation, idiom, windows"
  [2]="safe areas and layout margins"
  [3]="bars"
  [4]="plumbing"
  [5]="custom layout, hinge, camera"
)

TIER_HINTS=(
  [1]="Wrong on Duo: what device am I on, which way is it rotated, which window is key. None is knowable when the display changes and the device folds mid-session."
  [2]="A vertical bar puts the whole inset on one horizontal edge and zero on the other. Symmetric-inset code is wrong by default, and iOS 27.1 made a UIView's default layout margins zero."
  [3]="Only bars owned by a navigation container go vertical. Custom UIToolbar, UINavigationBar, UITabBar and hand-rolled HStack toolbars stay horizontal."
  [4]="Read-only. Report findings; never delete or add Info.plist keys silently."
  [5]="Only after tiers 1-4. Review-only: these mark places that may need arrangements, reserved regions or the camera direction API."
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
add_pattern 1 DEFECT "status bar frame" 'statusBarFrame'
add_pattern 1 DEFECT "single-window assumption" 'UIApplication[[:space:]]*\.[[:space:]]*shared[[:space:]]*\.[[:space:]]*(keyWindow|windows)|\[UIApplication[[:space:]]+sharedApplication\][[:space:]]*\.[[:space:]]*(keyWindow|windows)'
add_pattern 1 REVIEW  "device model checks" 'UIDevice[[:space:]]*\.[[:space:]]*current[[:space:]]*\.[[:space:]]*(model|name)'
add_pattern 1 REVIEW  "size class comparisons" 'horizontalSizeClass[[:space:]]*(==|!=)|verticalSizeClass[[:space:]]*(==|!=)'

add_pattern 2 DEFECT "deprecated layout guides" 'topLayoutGuide|bottomLayoutGuide'
add_pattern 2 DEFECT "doubled horizontal inset" 'safeAreaInsets[[:space:]]*\.[[:space:]]*(left|right)[[:space:]]*\*[[:space:]]*2'
add_pattern 2 DEFECT "one edge reused for both" 'safeAreaInsets[[:space:]]*\.[[:space:]]*(left|right).*safeAreaInsets[[:space:]]*\.[[:space:]]*(left|right)|safeAreaInsets[[:space:]]*\.[[:space:]]*top.*safeAreaInsets[[:space:]]*\.[[:space:]]*bottom'
add_pattern 2 DEFECT "inset threshold as a layout gate" 'safeAreaInsets[[:space:]]*\.[[:space:]]*(left|right|top|bottom)[[:space:]]*>[[:space:]]*[0-9]'
add_pattern 2 DEFECT "inset cached in stored property" '(lazy[[:space:]]+var|static[[:space:]]+(let|var))[^=]*=.*safeAreaInsets'
add_pattern 2 DEFECT "scroll view refuses inset adjustment" 'contentInsetAdjustmentBehavior[[:space:]]*=[[:space:]]*\.never'
add_pattern 2 DEFECT "hand-rolled keyboard avoidance" 'UIKeyboardWillShow|UIKeyboardWillChangeFrame|UIKeyboardFrameEndUserInfoKey|keyboardWillShowNotification|keyboardWillChangeFrameNotification'
add_pattern 2 DEFECT "system minimum margins disabled" 'viewRespectsSystemMinimumLayoutMargins[[:space:]]*=[[:space:]]*(false|NO)'
add_pattern 2 REVIEW  "unscoped ignoresSafeArea" 'ignoresSafeArea\([[:space:]]*\)|edgesIgnoringSafeArea'
add_pattern 2 DEFECT "foreground pinned to view edge, not safe area" '(leading|trailing)Anchor\.constraint\(equalTo:[[:space:]]*(self\.)?view\.(leading|trailing)Anchor,[[:space:]]*constant:[[:space:]]*[^0 )]'
add_pattern 2 REVIEW  "bar height as a top or bottom constraint constant" '(top|bottom)Anchor\.constraint\([^)]*constant:[[:space:]]*-?(20|34|44|49|64|83|88)\b'
add_pattern 2 REVIEW  "inset written into system insets" 'additionalSafeAreaInsets'
add_pattern 2 REVIEW  "layout margins in play" 'layoutMargins|preservesSuperviewLayoutMargins|systemMinimumLayoutMargins'

add_pattern 3 DEFECT "custom bar construction" '(UIToolbar|UINavigationBar|UITabBar)[[:space:]]*\([[:space:]]*\)'
add_pattern 3 REVIEW  "toolbar items to review" 'ToolbarItem[[:space:]]*\(|UIBarButtonItem[[:space:]]*\('
add_pattern 3 REVIEW  "vertical bar API already adopted" 'toolbarVerticalBehavior|preferredVerticalBarBehavior|toolbarVerticalCompressionBehavior|verticalBarCompressionBehavior|toolbarVerticalEdge|verticalBarEdge'
add_pattern 3 REVIEW  "axis and overflow configured" 'axisBehavior|visibilityPriority|additionalOverflowItems|ToolbarOverflowMenu'

add_pattern 4 REVIEW  "UIRequiresFullScreen (report, never delete)" 'UIRequiresFullScreen'
add_pattern 4 REVIEW  "supported interface orientations" 'UISupportedInterfaceOrientations'
add_pattern 4 REVIEW  "app delegate lifecycle" 'UIApplicationDelegate|didFinishLaunchingWithOptions'

add_pattern 5 REVIEW  "reserved regions in use" 'reservedRegions'
add_pattern 5 REVIEW  "arrangement views in use" 'ArrangementView|UIArrangementViewController'
add_pattern 5 REVIEW  "hinge angle read" 'onHingeChange|UIHingeInteraction|DeviceHinge'
add_pattern 5 REVIEW  "capture device position as direction" 'AVCaptureDevice[[:space:]]*\.[[:space:]]*Position|\.position[[:space:]]*==|AVCaptureDevice\.default\('
add_pattern 5 REVIEW  "full-bleed fill media" 'scaledToFill|aspectRatio\([^)]*\.fill|scaleAspectFill'

LAUNCH_SCREEN_REGEX='UILaunchScreen|UILaunchScreens|UILaunchStoryboardName|UILaunchStoryboards|INFOPLIST_KEY_UILaunchScreen_Generation'
UIKIT_APP_REGEX='UIApplicationSceneManifest|UIApplicationDelegate|UIViewController|UIHostingController'

scan() {
  if command -v rg >/dev/null 2>&1; then
    rg --line-number --no-heading --smart-case "${RG_ARGS[@]}" -e "$1" "$ROOT" 2>/dev/null || true
  else
    grep -rnE "${GREP_ARGS[@]}" -e "$1" "$ROOT" 2>/dev/null || true
  fi
}

filter_hits() {
  local label="$1" hits="$2" line file
  if [ "$label" != "custom bar construction" ]; then
    printf '%s' "$hits"
    return
  fi
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    file="${line%%:*}"
    grep -q 'inputAccessoryView' "$file" 2>/dev/null || printf '%s\n' "$line"
  done <<<"$hits"
}

json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/	/ /g'
}

emit_json_hits() {
  local tier="$1" kind="$2" label="$3" hits="$4" line file rest num text
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    file="${line%%:*}"
    rest="${line#*:}"
    num="${rest%%:*}"
    text="${rest#*:}"
    printf '{"tier":%s,"kind":"%s","pattern":"%s","file":"%s","line":%s,"text":"%s"}\n' \
      "$tier" "$kind" "$(json_escape "$label")" "$(json_escape "${file#"$ROOT"/}")" "$num" "$(json_escape "$text")"
  done <<<"$hits"
}

human() {
  if [ "$JSON_OUT" -eq 1 ]; then
    printf "$@" >&2
  else
    printf "$@"
  fi
}

defect_total=0
review_total=0

human 'audit.sh: scanning %s\n\n' "$ROOT"

for tier in 1 2 3 4 5; do
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

    hits="$(filter_hits "${PATTERN_LABEL[$i]}" "$(scan "${PATTERN_REGEX[$i]}")")"
    if [ -z "$hits" ]; then
      continue
    fi

    count="$(printf '%s\n' "$hits" | grep -c . || true)"
    row="$(printf '%-52s %5s' "${PATTERN_LABEL[$i]}" "$count")"

    if [ "$JSON_OUT" -eq 1 ]; then
      emit_json_hits "$tier" "${PATTERN_KIND[$i]}" "${PATTERN_LABEL[$i]}" "$hits"
    fi

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

  if [ "$tier" = "4" ] && [ -z "$(scan "$LAUNCH_SCREEN_REGEX")" ] && [ -n "$(scan "$UIKIT_APP_REGEX")" ]; then
    tier_defects=$((tier_defects + 1))
    defect_report+="$(printf '%-52s %5s' "no launch screen declaration (ITMS-90870)" 1)"$'\n'
    defect_detail+="-- no launch screen declaration (ITMS-90870)"$'\n'"none of UILaunchScreen, UILaunchScreens, UILaunchStoryboardName, UILaunchStoryboards or INFOPLIST_KEY_UILaunchScreen_Generation found; iOS 27 SDK uploads are rejected without one"$'\n'
    if [ "$JSON_OUT" -eq 1 ]; then
      printf '{"tier":4,"kind":"DEFECT","pattern":"no launch screen declaration (ITMS-90870)","file":"","line":0,"text":""}\n'
    fi
  fi

  defect_total=$((defect_total + tier_defects))
  review_total=$((review_total + tier_reviews))

  if [ "$JSON_OUT" -eq 0 ]; then
    printf '## Tier %s — %s\n%s\n\n' "$tier" "${TIER_TITLES[$tier]}" "${TIER_HINTS[$tier]}"

    if [ "$tier_defects" -gt 0 ]; then
      printf 'DEFECTS (%s):\n%-52s %5s\n' "$tier_defects" "pattern" "hits"
      printf '%s' "$defect_report"
      printf '\n%s' "$defect_detail"
    else
      printf 'DEFECTS: none\n'
    fi

    if [ "$tier_reviews" -gt 0 ]; then
      printf '\nREVIEW (%s):\n%-52s %5s\n' "$tier_reviews" "pattern" "hits"
      printf '%s' "$review_report"
      if [ "$SHOW_REVIEW" -eq 1 ]; then
        printf '\n%s' "$review_detail"
      else
        printf '\n(rerun with --review for file:line)\n'
      fi
    fi
    printf '\n'
  fi
done

human 'audit.sh: %s defects, %s review hits in %s\n' "$defect_total" "$review_total" "$ROOT"
human 'Replacement rules: references/audit-rules.md in the iphone-duo skill.\n'

if [ "$defect_total" -gt 0 ]; then
  exit 1
fi
exit 0
