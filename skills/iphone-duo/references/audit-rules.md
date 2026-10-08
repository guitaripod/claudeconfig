# Audit rules

Detection patterns and replacements, in fix order. Each tier assumes the previous one is clean. `scripts/audit.sh` automates detection and reports file:line; this file is the replacement guidance.

[Tier 1](#tier-1--screen-orientation-idiom) · [Tier 2](#tier-2--safe-areas-and-layout-margins) · [Tier 3](#tier-3--bars) · [Tier 4](#tier-4--plumbing) · [Tier 5](#tier-5--custom-layout-last) · [SwiftUI](#swiftui-specific) · [Objective-C](#objective-c)

In the script, DEFECT patterns gate the exit code; REVIEW patterns (including `ignoresSafeArea()` with no edges, which is correct for a background, and every Tier 4 check) never do. Tier 5 is review-only.

---

## Tier 1 — screen, orientation, idiom

The question this tier answers is wrong on Duo: *what device am I on, and which way is it rotated*. On a device that changes displays and folds mid-session, neither is knowable or meaningful.

**Detection**

| Pattern | Languages |
|---|---|
| `UIScreen.main`, `[UIScreen mainScreen]` | Swift, ObjC |
| `UIScreen.main.bounds` used for size classes | Swift |
| `UIDevice.current.orientation` | Swift |
| `statusBarOrientation`, `windowScene.effectiveGeometry.interfaceOrientation` | Swift, ObjC |
| `interfaceOrientation` in a layout decision | Swift, ObjC |
| `userInterfaceIdiom`, `UI_USER_INTERACE_IDIOM()`, `UI_USER_INTERFACE_IDIOM()` | Swift, ObjC |
| `horizontalSizeClass == .regular` / `.compact` treated as iPad or iPhone | Swift, ObjC |
| `bounds.height == <literal>` or a list of known iPhone heights | Swift, ObjC |
| `UIApplication.shared.keyWindow` / `.windows` (one-window assumption, wrong with multiple windows and Split View) | Swift, ObjC |
| `UIApplication.shared.statusBarFrame` | Swift, ObjC |

**Replacements**

| Before | After |
|---|---|
| `UIScreen.main.scale` in a view/controller instance method | `traitCollection.displayScale` (Swift) or `self.traitCollection.displayScale` (ObjC) |
| `UIScreen.main.scale` in `layoutSubviews` / `draw(_:)` / `updateConstraints()` / `viewIsAppearing(_:)` | same — no registration needed, UIKit re-calls these on trait change |
| `UIScreen.main.bounds` as a size | `view.bounds` (view controller), `superview.bounds` (view), or `GeometryReader`/`onGeometryChange` (SwiftUI) |
| `UIScreen.main` as a screen | `view.window?.windowScene?.screen` — and prefer not needing a screen at all |
| `UIDevice.current.orientation` / `statusBarOrientation` in layout | compare `view.bounds.width` to `view.bounds.height`, or read size classes |
| `userInterfaceIdiom == .phone` / `== .pad` | size classes, or available space |
| `bounds.height == 844` | nothing — derive from the container |
| `UIApplication.shared.keyWindow` / `.windows.first` | `view.window` or `view.window?.windowScene`; for the active scene's window, iterate `UIApplication.shared.connectedScenes` |
| `statusBarFrame` | the safe area, or `windowScene.statusBarManager` where the frame is genuinely needed |

Two habits matter more than the individual substitutions:

- **Re-read size when it changes.** Reading once at launch or in `viewIsAppearing` is not enough — a fold can resize the app mid-session. Do size-dependent layout in `layoutSubviews` / `viewDidLayoutSubviews`, and use `viewWillTransition(to:with:)` for work that must run on size change.
- **Scale comes from the trait collection**, never from the screen.

**Consuming size in UIKit:** read inside `updateProperties()` (automatic trait tracking re-runs it on change), or register explicitly:

```swift
registerForTraitChanges([UITraitHorizontalSizeClass.self, UITraitVerticalSizeClass.self]) {
    (self: Self, _) in self.view.setNeedsLayout()
}
```

**Monitoring the scene:** `windowScene(_:didUpdateEffectiveGeometry:)` for the coordinate space, `viewDidLayoutSubviews` for available space.

---

## Tier 2 — safe areas and layout margins

Vertical bars mean one horizontal edge carries the whole inset and the opposite edge carries zero. **Symmetric-inset code is wrong by default, and the inset is much larger than any earlier horizontal inset on iPhone.**

**Detection**

| Pattern | Why it breaks |
|---|---|
| `safeAreaInsets.left` applied to leading *and* trailing | collapses an asymmetric pair to one number |
| `max(safeAreaInsets.left, safeAreaInsets.right)` applied to both sides | same |
| `safeAreaInsets.top` used for top and bottom | values vary independently |
| `bounds.width - safeAreaInsets.left * 2` | subtracting a doubled inset from a single width |
| A threshold test such as `safeAreaInsets.left > 0` gating a layout branch | a layout never needs to know *whether* an inset exists; applying a zero inset is already correct |
| An inset stored in a property, ivar, `lazy var`, or `static let` | stale from the first resize onward |
| An inset read in `init`, `viewDidLoad`, `awakeFromNib`, or `viewWillAppear` | runs before the view reaches a window, so it reads zero and caches zero |
| `additionalSafeAreaInsets` set from the current safe area | double-counts; the property adds to system insets, it does not replace them |
| `topLayoutGuide` / `bottomLayoutGuide` | deprecated |
| `contentInsetAdjustmentBehavior = .never` | the scroll view stops adjusting for the bar |
| `contentInset` or `scrollIndicatorInsets` assigned from `safeAreaInsets` | `adjustedContentInset` already contains them |
| Hardcoded bar heights as constraint constants: `20`, `44`, `64`, `88`, `34`, `49`, `83` | cannot follow an inset that appears at runtime |
| `UIKeyboardWillShowNotification` + `UIKeyboardFrameEndUserInfoKey` driving a constraint | screen coordinates, stale on the next resize |
| `ignoresSafeArea()` with no `edges:` argument | extends content under the vertical bar |
| `x.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20)` (same for `trailingAnchor`) on foreground content | Pins to the full view, so it runs under the 84 pt status column. Found in a real app as clipped trailing text, a hidden **Done** button and a hidden paywall **close** button. A zero constant on a background or scroll view is fine; the audit flags only non-zero constants. Replace `view` with `view.safeAreaLayoutGuide`. |
| `layoutMargins.left` applied to leading and trailing | same asymmetry defect |
| `viewRespectsSystemMinimumLayoutMargins = false` | report, do not silently change |
| Subviews relying on **inherited** layout margins | **iOS 27.1 changed a `UIView`'s default layout margins to zero** |

**Replacements**

- Foreground content to `safeAreaLayoutGuide`; background and hero media to the superview's edges or `ignoresSafeArea()` with named edges.
- `bounds.width - safeAreaInsets.left - safeAreaInsets.right` is **correct as written** — it accounts for both edges. Leave it alone.
- `view.keyboardLayoutGuide` for keyboard avoidance. Delete the observer and the stored frame.
- Corners: `view.layoutGuide(for: .safeArea(cornerAdaptation: .horizontal))` or `view.directionalEdgeInsets(for: .safeArea(cornerAdaptation:))` — iOS 26.
- Respond to change with `safeAreaInsetsDidChange()` / `viewSafeAreaInsetsDidChange()`, calling `super`, and invalidate layout — do not recompute a cached copy. `setNeedsUpdateConstraints()` if the read lives in `updateConstraints`.
- **Layout margins (iOS 27.1):** a `UIView`'s default margins are now zero. A view controller still supplies `systemMinimumLayoutMargins`. A subview that must inherit them needs `preservesSuperviewLayoutMargins = true`. This is a silent layout change on upgrade — audit every view that relies on inheriting margins.
- SwiftUI: `safeAreaInset(edge:)` for content, `safeAreaBar(edge:)` (iOS 26) for bars, `safeAreaPadding(edge, length)` only for a margin that is a design value in its own right. Reading insets from a `GeometryProxy` to apply as padding inside the view that reported them counts the inset twice.

**Which edge holds the bar**

Read `traitCollection.verticalBarEdge` (UIKit) or `@Environment(\.toolbarVerticalEdge)` (SwiftUI) — iOS 27.1. In a layout method nothing else is needed; elsewhere pair it with `registerForTraitChanges(UITraitCollection.systemTraitsAffectingVerticalBarEdge)`.

Two limits: it resolves `leading`/`trailing` (follows layout direction) while `safeAreaInsets` is physical; and `unspecified` is ambiguous. Read the inset when you need the size.

**Telling which half of Split View you are in.** Converting the window to screen coordinates returns `{0,0}` for both halves, and `toolbarVerticalEdge` alone is ambiguous. The reliable trick: a reserved-region frame is **clipped to your view**, so a narrow sliver at the shared edge tells you the side. Measured: full-screen fold region x 455.5, w 40; Split View left x 455.5, w 13.5; Split View right x 0, w 13.5; window 469 × 669 per side.

**Physical vs directional.** `safeAreaInsets` describes the physical enclosure — `.left` is physical left in both directions. Constrain to `safeAreaLayoutGuide.leadingAnchor` / `.trailingAnchor` when the code means a direction. The same applies on the write side: `additionalSafeAreaInsets` lands on the opposite side in RTL.

---

## Tier 3 — bars

**Detection**

| Pattern | Problem |
|---|---|
| `UIToolbar()` constructed directly, `UINavigationBar()`, `UITabBar()` | Custom bars are never considered for the vertical axis |
| A SwiftUI `HStack`/`VStack` of buttons standing in for a toolbar | Same |
| `ToolbarItem` placed outside a `NavigationStack`/`NavigationSplitView`/`TabView` | The bar has no owning container to adapt it |
| Fixed or flexible spacers added manually alongside `ToolbarItemGroup` | Groups already space themselves |
| No `visibilityPriority` on any toolbar item | Overflow order is default bottom-to-top |
| Text-only toolbar items | Stay horizontal by design, taking space from the vertical bar |
| Keyboard input accessory view | Must stay attached to the keyboard, not go vertical |
| `preferredVerticalBarBehavior` / `toolbarVerticalBehavior` never set | Cannot opt out where a vertical bar is wrong |

**Replacements**

- Put the content in a navigation container. Set toolbar items on a view controller placed inside a `UINavigationController` or `UITabBarController`; in SwiftUI, pair `.toolbar` with `NavigationStack`/`NavigationSplitView`.
- Item ordering: primary navigation at the top of the vertical axis (`.cancellationAction` / `leftItemsSupplementBackButton = false` + `leadingItemGroups`), then prominent actions (`.topBarPinnedTrailing` / `pinnedTrailingGroup`). Remaining items keep their original groupings; the system inserts a vertical spacer between top and bottom placements.
- Give every item **both a title and a symbol**. The system picks: icon vertical, icon or title horizontal (icon preferred), icon + title in overflow. A title-only item never goes vertical.
- Overflow: consolidate your own menus into `ToolbarOverflowMenu` / `navigationItem.additionalOverflowItems`. Reserve the ellipsis for overflow only.
- Visibility: assign `visibilityPriority` by group first, then within groups. Keep frequently used actions and anything carrying a badge visible longest.
- Compression: `toolbarVerticalCompressionBehavior(.prefersToolbarItems)` (default, navigation-focused) or `.prefersTabBar` (task-oriented).
- Custom views: `.axisBehavior(.verticalPreferred)` to allow it, `.horizontalOnly` to keep it out. Fixed width or a vertically adapted layout is required.
- Read `@Environment(\.toolbarVerticalEdge)` / `traitCollection.verticalBarEdge` inside a custom view to adapt when a vertical bar appears. It is populated only when items *can* be on the vertical axis.
- Opt out with `toolbarVerticalBehavior(.disabled)` / `preferredVerticalBarBehavior` for single-page bottom-heavy layouts (Calculator) and single-item control-heavy sheets.
- Adopt the iOS 26 `.badge(_:)` / `UIBarButtonItem.badge` — a badge turns a text+symbol item into a symbol-only one that fits a vertical bar.
- Vertical bars have no scroll-edge effect by default but do have a background under Reduce Transparency. Flexible spacers are zero-sized on the vertical axis; fixed spacers keep their minimum.

**Contexts where bars stay horizontal:** inspectors; the sidebar and content columns of a split view (only the detail column goes vertical); inner-display sheets for centered or leading placements (trailing placements get a vertical bar); the inner display in the tall layout.

---

## Tier 4 — plumbing

Read-only checks. Report, never change silently.

| Check | Fail action |
|---|---|
| **None** of `UILaunchScreen` / `UILaunchScreens` / `UILaunchStoryboardName` / `UILaunchStoryboards` / `INFOPLIST_KEY_UILaunchScreen_Generation` anywhere | A build linked against the iOS 27 SDK is rejected at upload with `ITMS-90870` (TN3208). At least one key must be present; one is enough. The audit reports the absence as a defect. |
| `UISupportedInterfaceOrientations~ipad` lists all four | Name what is missing. A controller-level `supportedInterfaceOrientations` override can still lock the scene. |
| `UIRequiresFullScreen` | Report it. **Never delete it** — deletion makes the app resizable immediately and the layouts may not be ready. **Never add `UIRequiresFullScreenIgnoredStartingWithVersion`** — its value decides which releases keep the old behaviour, which is the developer's call. See TN3192. |
| `UIApplicationDelegate` instead of scene lifecycle | Migrate; apps built with the latest SDK must adopt the scene-based life cycle. |
| Portrait-only iPhone declaration | Normal — leave it. |
| `UISupportedInterfaceOrientations` restricting an iPad target | iOS 27 treats it as non-continuously-resizable. |

Read `Info.plist`, the project file, and any `.xcconfig` — the build merges all of them, and the project file wins on conflict.

---

## Tier 5 — custom layout, last

Only when the system genuinely cannot do it.

1. **Audit centred layouts first.** A centred element is the thing that lands in the fold. Ask whether it should become a two-column layout, or what displacement pattern fits. Displacement moves elements by purpose: alerts and contextual overlays toward the trailing side in book pose; media toward the top region and controls toward the bottom in tabletop pose.
2. **Prefer standard containers.** `NavigationSplitView` / `UISplitViewController` collapse on the outer display and adjust column widths around the fold. Alerts, context menus, sheets and menus already move away from the fold.
3. **Arrangements for two-view relationships.** An existing `HStack`/`VStack` pair becomes `.split`; a `ZStack` pair becomes `.overlay`. `.split` for main-detail where neither may be obscured; `.overlay` for foreground/background where the background may be partly hidden.
4. **Reserved regions for custom edge-to-edge chrome only.** Not for content a system container already handles.
5. **Grids: prefer an even number of columns** so content divides cleanly across the fold. Use the *inactive* division region for that decision — it is present whether or not the device is folded.

**Never:** an `ArrangementView` inside a `NavigationSplitView`, `List`, or `ScrollView`; a navigation container inside an `ArrangementView`; a hinge angle in a layout decision; a pose-specific layout that drops controls available in other poses.

---

## SwiftUI-specific

- `GeometryReader` for insets used in a layout decision — stop needing the number. `proxy.size` is fine; it is already inset. Subtracting insets from it counts them twice.
- A bar in a `ZStack` or `overlay` — move it to `safeAreaBar(edge:)` so its space is reserved, not just its position.
- Full-bleed media with `.scaleAspectFill` / `.aspectRatio(contentMode: .fill)` — choose fill vs fit from the current size class or aspect ratio, or set a focal point. A 16:9 frame on the inner display leaves ~134 pt letterboxed, a fifth of the screen.
- Hardcoded horizontal padding standing in for a side inset — delete it; no padding is the correct result.

## Objective-C

Every rule applies. `UIScreen.mainScreen`, `UI_USER_INTERFACE_IDIOM()`, and `topLayoutGuide`/`bottomLayoutGuide` all have direct mappings. Note that ObjC has no equivalent for `axisBehavior`'s SwiftUI form — set `UIBarButtonItem.axisBehavior` directly.
