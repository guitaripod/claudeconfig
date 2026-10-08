---
name: iphone-duo
description: Get an iOS app working well on iPhone Duo — Apple's folding iPhone. Covers what the device changes about layout, how to audit an app for patterns that break, how to fix them in the right order, when the system handles adaptation for you versus when to reach for the new iOS 27.1 APIs (reserved regions, arrangements, vertical bars, hinge), and how to test every pose. Use when asked to prepare an app for iPhone Duo or the foldable iPhone, make an app resizable or adapt to a resizing window, fix layout breaking on resize or in iPhone Split View, place content around the fold or hinge, or handle bars moving to a vertical edge.
---

# iPhone Duo

iPhone Duo is Apple's first folding iPhone (iOS 27.1). Four things change about how your app lays itself out:

1. **The scene moves between two displays while the app runs** — 466 × 678 pt outer (closed) and 669 × 951 pt inner (open). The window is not always the size of the screen, and the size changes mid-session.
2. **Status, navigation, toolbars and tab bars sit vertically along one edge** on the outer display and on the inner display in landscape. Horizontal bars survive only in the inner display's tall layout.
3. **The fold and two front cameras reserve regions** of the display that content must avoid.
4. **Split View multitasking and multiple app windows** arrive on iPhone, so your app can be half a screen, with its bar on either edge.

Nothing here is special-casing a device. It is the same adaptive-layout discipline that iPad and iPhone Mirroring already demanded — Duo just removes every remaining escape hatch.

## 0. Confirm the build SDK

Every Duo API is **iOS 27.1+**. Behaviour is stamped by the linked SDK, not the deployment target.

| Check | How | Why it matters |
|---|---|---|
| Links the iOS 27.1 SDK | `xcodebuild -showsdks`, or inspect `SDKROOT` / the scheme's base SDK | Builds linked against iOS 27.0 or earlier **do not adapt at all** — see the ladder below |
| `SDKROOT` set, not just `-sdk` | Inspect the build invocation | A `-sdk` link without `SDKROOT` silently stamps the binary 27.0 and none of the behaviour activates |
| Duo simulator runtime present | `xcodebuild -downloadPlatform iOS` — the runtime is a separate multi-GB download, not bundled with Xcode | Without it you cannot measure anything |

**The SDK ladder** — what linking against 27.0 versus 27.1 actually gets you:

| | Linked 27.0 or earlier | Linked 27.1 |
|---|---|---|
| Closed | Window is 386 × 678 beside an 80 pt black rail; **horizontal** bars; **no reserved regions** | Full 466 × 678; **vertical** bars; camera occlusion regions reported |
| Open | Window is 871 × 669 with a rail on the right; no regions | Full 951 × 669; vertical bars; the fold and inner camera reported as reserved regions |

So the first step is always: build against the iOS 27.1 SDK, then look at the app. The audit and source fixes below are valid regardless of the SDK; only compile verification and pose screenshots need the Duo runtime.

## 1. Prefer Apple's own skill for the generic half

Apple ships an **`app-resizability`** skill inside Xcode 27.1 (it replaced `uikit-app-modernization`). Export it with:

```bash
xcrun agent skills export --output-dir ~/duo-skills
```

It requires a running Xcode. It covers the generic modernization — `UIScreen.main`, orientation, idiom, scene lifecycle, safe-area asymmetry — with 13 core principles and five task references, and it is the standard Agent Skills format so it works in any agent. **This skill is the Duo layer on top**, not a replacement. Run Apple's skill for tiers 1, 2 and 4; come here for the rest.

## 2. The procedure

Run `scripts/audit.sh <repo>` from the repo root. Grep-based, no SDK needed, reports file:line, exits non-zero on defects. Patterns are tagged **DEFECT** (wrong on Duo) or **REVIEW** (needs judgement, not necessarily wrong) — the distinction is what lets the exit code gate without false alarms.

**Fix in this order. Do not reorder — each tier assumes the previous one is clean.**

1. **Tier 1 — screen, orientation, idiom.** Any code asking *what device am I on* or *which way am I rotated*. On a device that changes displays and folds mid-session, neither is knowable.
2. **Tier 2 — safe areas and layout margins.** A vertical bar means one horizontal edge carries the whole inset while the opposite edge carries zero, so symmetric-inset code is wrong by default. Includes the iOS 27.1 change where a `UIView`'s default layout margins became zero.
3. **Tier 3 — bars.** Custom `UIToolbar`, `UINavigationBar`, `UITabBar` and hand-rolled `HStack` toolbars **never go vertical**. Only bars owned by `UINavigationController`, `UITabBarController`, `NavigationStack` or `NavigationSplitView` do.
4. **Tier 4 — plumbing.** Launch screen key, `UIRequiresFullScreen`, scene lifecycle, iPad orientations. Read-only: report, never change silently.
5. **Tier 5 — custom layout, last.** Arrangements for two-view relationships, reserved regions for custom edge-to-edge chrome. **Reaching for these before tiers 1–4 is the most common mistake** — the system already handles most of it.

Replacement rules for every tier are in `references/audit-rules.md`.

## 3. The judgement call: when does the system already do it?

This is the part that decides whether an app feels great or merely works.

**Handled for you by standard components** — use them and you inherit Duo behaviour with no new code:

- `NavigationSplitView` / `UISplitViewController` collapse to one column on the outer display, expand on the inner, and adjust column widths around the fold.
- `TabView` / `UITabBarController` lay out tabs vertically when appropriate, and can present as a sidebar on the inner display.
- Sheets, alerts, context menus and popovers reposition themselves away from the fold. A plain `.sheet` already takes the leading panel in book pose and the lower panel in tabletop pose, with zero pose-specific code.
- `.split` arrangements divide evenly across the fold; split views settle into a 50/50 split.

**Yours to handle:**

| Situation | Tool |
|---|---|
| Two views with a main–detail relationship | `ArrangementView` with `.split` |
| Two views with a foreground/background relationship | `ArrangementView` with `.overlay` |
| A grid that should divide cleanly across the fold | Reserved regions — prefer an even column count from the inactive division region |
| Custom edge-to-edge chrome, or content a system container does not move | `reservedRegions(kind:)` |
| An effect driven by how far the device is folded | `onHingeChange` — **never for layout** |
| Camera UI that must follow the user between displays | `AVCaptureDeviceDirectionCoordinator` |

Displacement — moving an element by its purpose rather than its geometry — is the pattern to internalise: alerts move to the trailing side in book pose (closer to where they land when the device closes), media to the top region and controls to the stable bottom region in tabletop pose. Continuous scrolling content does **not** displace; it already adapts by scrolling.

## 4. Traps that are not in Apple's docs

Measured on the 27.1 simulator; these are the reason the audit exists.

- **Reserved regions arrive *after* the first layout pass.** Read them inside the `GeometryReader` body or `layoutSubviews`. Never cache them.
- **The outer display reports no reserved regions at all** — not even inactive ones. An empty result does not mean "no camera cutout to worry about."
- **Never derive posture from the hinge angle.** While dragging, status flips to `partiallyOpen` at 20° and back to `closed` at 27° or 46°; after a click it settles by band (closed at 36.6/71.2/108.6/123.3°, partially open at 143.1°). Fully open is reported only at 180°. Same angle, different pose, depending on how it was reached. React to `status`, the scene's geometry and reserved regions; keep the angle for effects.
- **`UIScreen.main` still reports the outer display's 466 × 678 while your app is on the inner display**, and its size classes are not the scene's size classes.
- **In `.overlay` arrangements the *primary* view floats** in the top leading corner while the secondary fills behind it. `overlayArrangementZIndex` reads 0 at the root — read it from a subview.
- **`.split` can drop the secondary view entirely** when both do not fit along an allowed axis.
- **The fold overrides your ratio.** In book pose a split arrangement puts its divider on the fold even if `splitArrangementLayoutRatio` says otherwise.
- **The inner display is landscape-native (270°)** and does not honour `supportedInterfaceOrientations`.
- **New windows cannot be created on the outer display.** Availability is dynamic — handle the activation error.
- **In Split View your bar can be on *either* edge** depending on which half you are in. Converting the window to screen coordinates returns `{0,0}` for both halves. The reliable signal is that a reserved-region frame is clipped to your view, so a narrow sliver at the shared edge tells you the side — see `references/audit-rules.md`.
- **The vertical bar follows the camera.** Rotate a closed device and the column moves between trailing and leading. A control placed "on the right" must read the edge.

## 5. Test every pose

Only the iPhone Duo simulator shows vertical bars and reserved regions. A resizable simulator, iPhone Mirroring or a resizable iPad window are useful substitutes for general resize behaviour but will not surface these.

- **Poses: Closed, Book, Open, plus Rotate Right** — in every combination. Hold **Option** over the pose buttons in Device Hub for a hidden 0–180° hinge slider, which is the only way to exercise the between-poses behaviour.
- **Split View:** drag the app to each half of the inner display. The bar moves to the app's outer edge, so the same screen must be correct on both sides.
- **Keyboard up in every pose.** Sizes differ enough to break bottom-pinned controls.
- **Previews:** the canvas overrides picker has a **Display** group for previewing the alternative display, and a Resizable Canvas mode for arbitrary sizes.
- **Known simulator issues:** first launch takes several minutes; StandBy is unavailable; most app extensions cannot be run or debugged; screenshots and recordings may be **black for a few minutes after boot**, so wait and verify before capturing; VoiceOver and the Accessibility Inspector cannot convey content inside Device Hub, so accessibility needs a different route.

Capture with `xcrun simctl io booted screenshot --display=1` (outer) and `--display=3` (inner).

The simulator device type is `com.apple.CoreSimulator.SimDeviceType.iPhone-Duo` (alias `V68`, `iPhone19,4`), auto-created for the 27.1 runtime. Booting it requires Xcode's first-launch package install to have completed — see `references/measured.md`.

## 6. Shipping

**From April 2027 every App Store submission must include iPhone Duo screenshots.** That is the deadline driving all of this.

Capture four sizes from the Duo simulator: 1398 × 2034 and 2034 × 1398 (outer), 2007 × 2853 and 2853 × 2007 (inner). Frame them with your device-frame tool of choice, then submit through App Store Connect, where a preview tool shows how assets look on Duo. A featuring nomination can flag the app as optimised for all poses.

## 7. References

| File | Load when |
|---|---|
| `references/api-surface.md` | Writing or reviewing Duo code — every symbol, version-tagged, with doc links |
| `references/measured.md` | Needed a number — display sizes, insets, fold geometry, the 27.0-vs-27.1 ladder, keyboard sizes |
| `references/audit-rules.md` | Running the audit or triaging findings — detection patterns and replacements, SwiftUI and UIKit |
| `references/camera.md` | The app uses AVFoundation — the one area with no system fallback |
| `scripts/audit.sh` | Any audit pass |

Apple's canonical pages, in reading order: [/iphone-duo/prepare/](https://developer.apple.com/iphone-duo/prepare/) → [Preparing your app for iPhone Duo](https://developer.apple.com/documentation/technologyoverviews/preparing-your-app-for-iphone-duo) → [Designing for iPhone Duo](https://developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo). The six Tech Talks that the API detail here comes from: 111461 (prepare), 111462 (bars), 111463 (adaptive layouts), 111464 (displays and scenes), 111465 (camera), 111466 (design).
