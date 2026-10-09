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
#   scripts/audit.sh --ios-only      skip the other platforms and non-app directories of a shared repo:
#                                    macos, Mac, mac, watch, Watch, linux, Linux, tvos, vision, android,
#                                    Design, marketing, build-*, Pods, DerivedData, and *Tests* (also
#                                    names ending in Mac, Linux or Watch App), so only the iPhone target is audited
#
# A DEFECT that is legitimate (an orientation policy that must read the idiom) is kept with a
# `// duo-audit:ignore <reason>` comment on the same line or the line above. The reason is required;
# ignored hits are counted and listed by --review but never gate the exit code.
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
IOS_ONLY=0
ROOT="."
EXCLUDES=()
IOS_ONLY_EXCLUDES=(
  macos Mac mac watch Watch linux Linux tvos vision android Design marketing
  'build-*' .build DerivedData Pods '*Tests*' '*Mac' '*Linux' '*Watch App'
)

usage() {
  printf 'usage: audit.sh [--tier 1-5] [--review] [--json] [--ios-only] [--exclude GLOB]... [ROOT]\n' >&2
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tier) TIER_FIL="${2:-}"; shift 2 ;;
    --review) SHOW_REVIEW=1; shift ;;
    --json) JSON_OUT=1; shift ;;
    --ios-only) IOS_ONLY=1; shift ;;
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

if [ "$IOS_ONLY" -eq 1 ]; then
  EXCLUDES+=("${IOS_ONLY_EXCLUDES[@]}")
fi

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

declare -a PATTERN_TIER PATTERN_KIND PATTERN_LABEL PATTERN_REGEX PATTERN_FIX

add_pattern() {
  PATTERN_TIER+=("$1")
  PATTERN_KIND+=("$2")
  PATTERN_LABEL+=("$3")
  PATTERN_REGEX+=("$4")
  PATTERN_FIX+=("${5:-}")
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
add_pattern 2 DEFECT "multi-line pin to view edge, not safe area" '@scan_multiline_pins' "pin foreground content to view.safeAreaLayoutGuide.leadingAnchor / trailingAnchor; a zero constant on a background is fine"
add_pattern 2 DEFECT "SnapKit pin to view, not safe area" '@scan_snapkit_pins' "pin foreground content to view.safeAreaLayoutGuide, as in .equalTo(view.safeAreaLayoutGuide).inset(20); a plain .edges.equalToSuperview() on a background is fine"
add_pattern 2 DEFECT "bare readableContentGuide as a horizontal pin" '@scan_readable_bare' "iOS 27.1 readable margins are zero: add the margin as a constant, or pair it with a >= pin to safeAreaLayoutGuide"
add_pattern 2 REVIEW  "readableContentGuide pin with a margin fallback" '@scan_readable_fallback'
add_pattern 2 REVIEW "compositional section without contentInsetsReference" '@scan_section_insets' "rows under the vertical bar on the capture mean it is a defect (Master of Flags Settings and Tip Jar); a scroll view already inset by the bar is fine (Solar Beam grids): set section.contentInsetsReference = .safeArea (or .layoutMargins) when the capture shows it"
add_pattern 2 DEFECT "full-width item repeated in a multi-column group" '@scan_repeating_full_width' "give the item .fractionalWidth(1.0 / CGFloat(count)) so the columns share the group width; fractionalWidth(1) per column pushes the second off screen"

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

# Perl program behind the multi-line scanners: reads whole files, so a pin split over several lines is one match.
# Prints file:line:text like grep does. Modes: pins, snapkit, readable-bare, readable-fallback, sections, repeating.
PERL_SCANNER='use strict;
use warnings;

my $mode = shift @ARGV;

sub line_of {
    my ($text, $pos) = @_;
    return 1 + (substr($text, 0, $pos) =~ tr/\n//);
}

sub report {
    my ($file, $text, $start, $end) = @_;
    my $line_start = $start > 0 ? rindex($text, "\n", $start - 1) + 1 : 0;
    my $line_end = index($text, "\n", $end);
    $line_end = length($text) if $line_end < 0;
    my $snippet = substr($text, $line_start, $line_end - $line_start);
    $snippet =~ s/\s*\n\s*/ /g;
    printf "%s:%d:%s\n", $file, line_of($text, $start), $snippet;
}

sub balanced_end {
    my ($text, $open_pos, $open, $close) = @_;
    my $depth = 0;
    for (my $i = $open_pos; $i < length($text); $i++) {
        my $c = substr($text, $i, 1);
        if ($c eq $open) {
            $depth++;
        } elsif ($c eq $close) {
            $depth--;
            return $i if $depth == 0;
        }
    }
    return length($text) - 1;
}

sub has_safe_side_pin {
    my ($text) = @_;
    foreach my $line (split /\n/, $text) {
        next unless $line =~ /safeAreaLayoutGuide/;
        return 1 if $line =~ /\b(?:leading|trailing|left|right|horizontalEdges|edges)/;
    }
    return 0;
}

sub scan_pins {
    my ($file, $text) = @_;
    my $anchor_pin = qr/\b(?:leading|trailing|left|right)Anchor\s*\.\s*constraint\(\s*equalTo:\s*(?:self\.)?view[!?]?\s*\.\s*(?:leading|trailing|left|right)Anchor\s*,\s*constant:\s*[^0\s)]/;
    my $item_pin = qr/NSLayoutConstraint\(\s*item:[^)]*?toItem:\s*(?:self\.)?view\s*,\s*attribute:\s*\.(?:leading|trailing|left|right)\b[^)]*?constant:\s*[^0\s)]/;
    my $single_line = qr/(?:leading|trailing)Anchor\.constraint\(equalTo:[ \t]*(?:self\.)?view\.(?:leading|trailing)Anchor,[ \t]*constant:[ \t]*[^0 )]/;
    foreach my $re ($anchor_pin, $item_pin) {
        while ($text =~ /$re/g) {
            my ($start, $end) = ($-[0], $+[0]);
            my $match = substr($text, $start, $end - $start);
            next if $match !~ /\n/ && $match =~ $single_line;
            report($file, $text, $start, $end);
        }
    }
}

sub scan_snapkit {
    my ($file, $text) = @_;
    my $edge = qr/(?:leading|trailing|left|right|horizontalEdges|edges)/;
    my $any_edge = qr/(?:leading|trailing|left|right|top|bottom|horizontalEdges|verticalEdges|edges)/;
    my $to_view = qr/\.$edge(?:\s*\.\s*$any_edge)*\s*\.equalTo\(\s*(?:self\.)?view(?:\.snp\.\w+)?\s*\)\s*\.(?:inset|insets|offset)\(\s*[^0\s)]/;
    while ($text =~ /$to_view/g) {
        report($file, $text, $-[0], $+[0]);
    }
    my %on_view;
    my @blocks;
    while ($text =~ /(?<![\w.])(?:self\.)?view\.add\w*Subview\(\s*(?:self\.)?(\w+)\s*\)(\s*\{)?/g) {
        $on_view{$1} = 1;
        push @blocks, $+[0] - 1 if defined $2;
    }
    while ($text =~ /(?<![\w.])(?:self\.)?(\w+)\.snp\.(?:makeConstraints|remakeConstraints|updateConstraints)\s*\{/g) {
        push @blocks, $+[0] - 1 if $on_view{$1};
    }
    foreach my $open (@blocks) {
        my $close = balanced_end($text, $open, "{", "}");
        my $body = substr($text, $open, $close - $open);
        while ($body =~ /[\w\$]+\s*\.\s*((?:\w+\s*\.\s*)*)equalToSuperview\(\)\s*\.(?:inset|insets|offset)\(\s*[^0\s)]/g) {
            my ($start, $end, $attrs) = ($-[0], $+[0], $1);
            next unless $attrs =~ /\b$edge\b/;
            report($file, $text, $open + $start, $open + $end);
        }
    }
}

sub scan_readable {
    my ($file, $text, $want_fallback) = @_;
    my $readable = qr/\breadableContentGuide\s*\.\s*(?:leading|trailing|left|right)Anchor/;
    my $margin_word = qr/layoutMargins|safeAreaLayoutGuide|systemMinimumLayoutMargins|max\(|constant:\s*[^0\s)]/;
    my $paired_floor = $text =~ /greaterThanOrEqualTo:\s*(?:[\w.]+\.)?(?:safeAreaLayoutGuide|layoutMarginsGuide)\s*\.\s*(?:leading|trailing|left|right)Anchor/;
    while ($text =~ /$readable/g) {
        my ($start, $end) = ($-[0], $+[0]);
        my $statement = substr($text, $start, $end - $start);
        my $call = rindex($text, "constraint(", $start);
        if ($call >= 0 && $start - $call < 200) {
            my $call_end = balanced_end($text, $call + length("constraint"), "(", ")");
            $statement = substr($text, $call, $call_end - $call + 1) if $call_end >= $end;
        }
        my $has_fallback = $paired_floor || $statement =~ $margin_word;
        report($file, $text, $start, $end) if ($has_fallback ? 1 : 0) == $want_fallback;
    }
}

sub scan_sections {
    my ($file, $text) = @_;
    return if $text =~ /contentInsetsReference/;
    return if has_safe_side_pin($text);
    while ($text =~ /\bNSCollectionLayoutSection\s*(?:\(\s*group\s*:|\.\s*list\s*\()/g) {
        report($file, $text, $-[0], $+[0]);
    }
}

sub full_width {
    my ($dimension) = @_;
    return $dimension =~ /^\.fractionalWidth\(\s*1(?:\.0*)?\s*\)$/ ? 1 : 0;
}

sub item_width {
    my ($window, $item) = @_;
    return undef unless $window =~ /.*\b(?:let|var)\s+\Q$item\E\s*=\s*NSCollectionLayoutItem\(\s*layoutSize:\s*(?:(\w+)\b(?!\()|(?:NSCollectionLayoutSize|\.init)\(\s*widthDimension:\s*(\.fractionalWidth\([^)]*\)))/s;
    return $2 if defined $2;
    my $size = $1;
    return undef unless defined $size;
    return undef unless $window =~ /.*\b(?:let|var)\s+\Q$size\E\s*=\s*(?:NSCollectionLayoutSize|\.init)\(\s*widthDimension:\s*(\.fractionalWidth\([^)]*\))/s;
    return $1;
}

sub scan_repeating {
    my ($file, $text) = @_;
    while ($text =~ /repeatingSubitem:\s*(\w+)\s*,\s*count:\s*([\w.]+)/g) {
        my ($start, $end, $item, $count) = ($-[0], $+[0], $1, $2);
        next if $count =~ /^1$/;
        my $from = $start > 3000 ? $start - 3000 : 0;
        my $width = item_width(substr($text, $from, $start - $from), $item);
        next unless defined $width && full_width($width);
        report($file, $text, $start, $end);
    }
}

foreach my $file (@ARGV) {
    open(my $handle, "<", $file) or next;
    local $/;
    my $text = <$handle>;
    close $handle;
    scan_pins($file, $text) if $mode eq "pins";
    scan_snapkit($file, $text) if $mode eq "snapkit";
    scan_readable($file, $text, 0) if $mode eq "readable-bare";
    scan_readable($file, $text, 1) if $mode eq "readable-fallback";
    scan_sections($file, $text) if $mode eq "sections";
    scan_repeating($file, $text) if $mode eq "repeating";
}
'

# Swift files under ROOT with at least one line matching the regex, honouring the same excludes as scan.
scan_files() {
  scan "$1" | cut -d: -f1 | grep '\.swift$' | sort -u || true
}

# Runs one PERL_SCANNER mode over the files that mention the anchor regex.
run_scanner() {
  local mode="$1" anchor="$2" file
  local files=()
  while IFS= read -r file; do
    if [ -n "$file" ]; then
      files+=("$file")
    fi
  done < <(scan_files "$anchor")
  if [ "${#files[@]}" -gt 0 ]; then
    perl -e "$PERL_SCANNER" "$mode" "${files[@]}" 2>/dev/null || true
  fi
}

scan_multiline_pins() { run_scanner pins 'Anchor|toItem'; }
scan_snapkit_pins() { run_scanner snapkit 'snp\.|equalToSuperview'; }
scan_readable_bare() { run_scanner readable-bare 'readableContentGuide'; }
scan_readable_fallback() { run_scanner readable-fallback 'readableContentGuide'; }
scan_section_insets() { run_scanner sections 'NSCollectionLayoutSection'; }
scan_repeating_full_width() { run_scanner repeating 'repeatingSubitem'; }

# Hits for pattern index $1: a grep regex, or a scanner function when the regex starts with @.
pattern_hits() {
  local regex="${PATTERN_REGEX[$1]}"
  case "$regex" in
    @*) "${regex#@}" ;;
    *) scan "$regex" ;;
  esac
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
  local tier="$1" kind="$2" label="$3" hits="$4" fix="$5" line file rest num text
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    file="${line%%:*}"
    rest="${line#*:}"
    num="${rest%%:*}"
    text="${rest#*:}"
    printf '{"tier":%s,"kind":"%s","pattern":"%s","fix":"%s","file":"%s","line":%s,"text":"%s"}\n' \
      "$tier" "$kind" "$(json_escape "$label")" "$(json_escape "$fix")" "$(json_escape "${file#"$ROOT"/}")" "$num" "$(json_escape "$text")"
  done <<<"$hits"
}

IGNORE_REGEX='duo-audit:ignore[[:space:]]+[^[:space:]*/]'

# True when a hit carries a `duo-audit:ignore <reason>` directive on its own line or in a comment on the line above.
is_ignored() {
  local file="$1" num="$2" text="$3" previous
  if printf '%s' "$text" | grep -Eq "$IGNORE_REGEX"; then
    return 0
  fi
  case "$num" in
    ''|*[!0-9]*|1) return 1 ;;
  esac
  previous="$(sed -n "$((num - 1))p" "$file" 2>/dev/null || true)"
  printf '%s' "$previous" | grep -Eq "^[[:space:]]*(//|/\*|#).*$IGNORE_REGEX"
}

# Splits hits into ACTIVE_HITS and IGNORED_HITS by the `duo-audit:ignore` directive.
split_ignored() {
  local hits="$1" line file rest num text
  ACTIVE_HITS=""
  IGNORED_HITS=""
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    file="${line%%:*}"
    rest="${line#*:}"
    num="${rest%%:*}"
    text="${rest#*:}"
    if is_ignored "$file" "$num" "$text"; then
      IGNORED_HITS+="$line"$'\n'
    else
      ACTIVE_HITS+="$line"$'\n'
    fi
  done <<<"$hits"
  ACTIVE_HITS="${ACTIVE_HITS%$'\n'}"
  IGNORED_HITS="${IGNORED_HITS%$'\n'}"
}

# A heading line for a hit group, followed by the replacement when the pattern names one.
detail_heading() {
  local label="$1" fix="$2"
  printf -- '-- %s\n' "$label"
  if [ -n "$fix" ]; then
    printf '   fix: %s\n' "$fix"
  fi
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
ignored_total=0

human 'audit.sh: scanning %s\n\n' "$ROOT"

for tier in 1 2 3 4 5; do
  if [ -n "$TIER_FIL" ] && [ "$TIER_FIL" != "$tier" ]; then
    continue
  fi

  tier_defects=0
  tier_reviews=0
  tier_ignored=0
  defect_report=""
  review_report=""
  ignored_report=""
  defect_detail=""
  review_detail=""
  ignored_detail=""

  for i in "${!PATTERN_TIER[@]}"; do
    if [ "${PATTERN_TIER[$i]}" != "$tier" ]; then
      continue
    fi

    hits="$(filter_hits "${PATTERN_LABEL[$i]}" "$(pattern_hits "$i")")"
    if [ -z "$hits" ]; then
      continue
    fi

    if [ "${PATTERN_KIND[$i]}" = "DEFECT" ]; then
      split_ignored "$hits"
      hits="$ACTIVE_HITS"
      if [ -n "$IGNORED_HITS" ]; then
        ignored_count="$(printf '%s\n' "$IGNORED_HITS" | grep -c . || true)"
        tier_ignored=$((tier_ignored + ignored_count))
        ignored_report+="$(printf '%-52s %5s' "${PATTERN_LABEL[$i]}" "$ignored_count")"$'\n'
        ignored_detail+="$(detail_heading "${PATTERN_LABEL[$i]}" "")"$'\n'"$IGNORED_HITS"$'\n'
        if [ "$JSON_OUT" -eq 1 ]; then
          emit_json_hits "$tier" IGNORED "${PATTERN_LABEL[$i]}" "$IGNORED_HITS" "${PATTERN_FIX[$i]}"
        fi
      fi
      if [ -z "$hits" ]; then
        continue
      fi
    fi

    count="$(printf '%s\n' "$hits" | grep -c . || true)"
    row="$(printf '%-52s %5s' "${PATTERN_LABEL[$i]}" "$count")"

    if [ "$JSON_OUT" -eq 1 ]; then
      emit_json_hits "$tier" "${PATTERN_KIND[$i]}" "${PATTERN_LABEL[$i]}" "$hits" "${PATTERN_FIX[$i]}"
    fi

    if [ "${PATTERN_KIND[$i]}" = "DEFECT" ]; then
      tier_defects=$((tier_defects + count))
      defect_report+="$row"$'\n'
      defect_detail+="$(detail_heading "${PATTERN_LABEL[$i]}" "${PATTERN_FIX[$i]}")"$'\n'"$hits"$'\n'
    else
      tier_reviews=$((tier_reviews + count))
      review_report+="$row"$'\n'
      review_detail+="$(detail_heading "${PATTERN_LABEL[$i]}" "${PATTERN_FIX[$i]}")"$'\n'"$hits"$'\n'
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
  ignored_total=$((ignored_total + tier_ignored))

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

    if [ "$tier_ignored" -gt 0 ]; then
      printf '\nIGNORED by duo-audit:ignore (%s):\n%-52s %5s\n' "$tier_ignored" "pattern" "hits"
      printf '%s' "$ignored_report"
      if [ "$SHOW_REVIEW" -eq 1 ]; then
        printf '\n%s' "$ignored_detail"
      fi
    fi
    printf '\n'
  fi
done

human 'audit.sh: %s defects, %s review hits in %s\n' "$defect_total" "$review_total" "$ROOT"
if [ "$ignored_total" -gt 0 ]; then
  human 'audit.sh: %s hits ignored by duo-audit:ignore (rerun with --review to list them)\n' "$ignored_total"
fi
unexplained="$(scan 'duo-audit:ignore[[:space:]]*(\*/)?[[:space:]]*$' | grep -c . || true)"
if [ "$unexplained" -gt 0 ]; then
  human 'audit.sh: %s duo-audit:ignore directive(s) have no reason and suppress nothing\n' "$unexplained"
fi
human 'Replacement rules: references/audit-rules.md in the iphone-duo skill.\n'

if [ "$defect_total" -gt 0 ]; then
  exit 1
fi
exit 0
