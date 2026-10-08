---
name: iphone-duo
description: Get an iOS app ready for iPhone Duo (Apple's folding iPhone) — audit and fix layout code for a window that changes displays and size at runtime, adopt vertical side bars, reserved regions for the fold and cameras, and arrangements. Use when asked to prepare an app for iPhone Duo or the foldable iPhone, make an app resizable, fix layout breaking on resize or in iPhone Split View, or place content around the fold/crease, hinge, or vertical toolbar. Also use when shipping Duo screenshots. Not for generic iPad layout, camera work on single-display iPhones, or App Store metadata and submission (use the app-store skill).
---

# iPhone Duo

iPhone Duo is Apple's first folding iPhone (ships October 23, 2026, iOS 27.1). Your app's scene moves between a **466 × 678 pt outer display** (closed) and a **669 × 951 pt inner display** (open) while the app runs, the inner display has a hinge and two front cameras, and bars (status, nav, toolbar, tab) sit **vertically along one edge** instead of top and bottom.

Work in `~/Dev/iOS/<app>` and `~/Dev/embr`. The fleet is overwhelmingly UIKit with some SwiftUI, deployment floor iOS 18.0, scene lifecycle already present in most apps. Build normally goes through `xtool` from Arch — see `ios-dev`.

## 0. Environment gate — run this first, it blocks everything

Every Duo-specific API is **iOS 27.1+**, gated behind `#available`. Before touching code, confirm the toolchain:

| Check | How | If it fails |
|---|---|---|
| iOS 27.1 SDK reachable | `ls /Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/` on the MacBook, or `xtool sdk list` | **Stop.** No 27.1 SDK exists on the Arch box or the MacBook (Mac has Xcode 27.0 / `iPhoneOS27.0.sdk` only). Do not write `#available(iOS 27.1, *)` code that cannot compile. |
| iPhone Duo simulator runtime | `xcodebuild -downloadPlatform iOS` (~7.85 GB, runtime `24A94401`, separate from Xcode) | Sizes and poses cannot be measured. Use the documented numbers in `references/measured.md`. |
| `SDKROOT` set explicitly | Inspect the build invocation | A `-sdk` link without `SDKROOT` silently stamps the binary 27.0 and **none of the Duo behaviour activates**. Always verify the stamp. |
| Mac running Xcode 27.1 | `xcodebuild -version` | Duo simulator unavailable. The iPhone Air is **not** a Duo — it cannot test any of this. |

Once the toolchain exists, the full chain is: Xcode 27.1 RC on the MacBook → download the Duo runtime → `xtool sdk install /path/to/Xcode.app` to expose the 27.1 Darwin SDK to Arch.

**If the gate fails, the source audit and fixes are still valid and should still be done.** Only compile verification and pose screenshots wait.

## 1. Prefer Apple's own skill for the generic half

Apple ships an `app-resizability` skill inside Xcode 27.1 (it replaced `uikit-app-modernization`). Export it with:

```bash
xcrun agent skills export --output-dir ~/duo-skills
```

It requires a **running** Xcode (mcpbridge opens an XPC connection and hangs otherwise). It is the standard Agent Skills format, so it drops straight into `~/.config/opencode/skills/` or `~/.claude/skills/`.

Use it for the generic modernization — `UIScreen.main`, orientation, idiom, scene lifecycle, safe-area asymmetry. It has 13 core principles, an Info.plist prerequisites gate, and five task references. This skill is the **Duo layer on top**, not a replacement.

## 2. The procedure

Run `scripts/audit.sh <repo>` first. It is grep-based, needs no SDK, and reports file:line per tier. Delegate the fleet-wide pass — 13 repos, ~3,800 files — and keep findings in one report.

Patterns are tagged **DEFECT** (wrong on Duo) or **REVIEW** (needs judgement, not necessarily wrong). Exit code is 1 only when defects exist, so it drops straight into a gate. A baseline pass on the fleet today found **50 defects and 241 review hits**, concentrated in `appofthedead` (18), `Tailscode` (13), `master-of-flags` (6) and `Crucible` (5); `Anvil`, `Echo`, `Macro` and `zengolf` are already clean. `contentInsetAdjustmentBehavior = .never` and `UIScreen.main.scale` are the two most common defects, and Tier 3 review counts are dominated by toolbar items — the point of the review tier is to show how much bar work each app carries, not to flag a bug.

**Fix in this order. Do not reorder: each tier assumes the previous one is clean.**

1. **Tier 1 — screen, orientation, idiom.** Any code that asks *what device am I on* or *which way am I rotated*. Replace with available space, size classes, and trait collection. See `references/audit-rules.md`.
2. **Tier 2 — safe areas and layout margins.** Vertical bars make one horizontal inset carry the whole inset while the opposite edge carries zero. Symmetric-inset code is wrong by default. Includes the iOS 27.1 change where a `UIView`'s default layout margins became zero.
3. **Tier 3 — bars.** Custom `UIToolbar`/`UINavigationBar`/`UITabBar` and hand-rolled `HStack` toolbars **never go vertical** — only bars owned by `UINavigationController`/`UITabBarController`/`NavigationStack`/`NavigationSplitView` do. Audit item ordering, overflow priority, and axis behaviour.
4. **Tier 4 — plumbing.** Launch screen key, `UIRequiresFullScreen`, scene lifecycle, iPad orientations.
5. **Tier 5 — custom layout, only where the system cannot help.** Arrangements for two-view relationships, reserved regions for custom edge-to-edge chrome. Reaching for these before tiers 1–4 is the most common mistake.

**Verify each tier by building, then re-running the scanner until it exits clean.**

## 3. Traps that are not in Apple's docs

These are measured on the 27.1 simulator and are the reason this skill exists:

- **Reserved regions arrive *after* the first layout pass.** Read them inside the `GeometryReader` body or `layoutSubviews`. Never cache them.
- **The outer display reports no reserved regions at all** — not even inactive ones. Do not infer a camera cutout from an empty result.
- **Never derive posture from the hinge angle.** While dragging, status flips to `partiallyOpen` at 20° and back to `closed` at 27° or 46°; after a click it settles by band (closed at 36.6/71.2/108.6/123.3°, partially open at 143.1°). Fully open is reported only at 180°. React to `status`, the scene's geometry, and reserved regions — keep the angle for effects.
- **`UIScreen.main` still reports the outer display's 466 × 678 while your app is on the inner display.** It is ambiguous and slated for deprecation.
- **`UIScreen.main`'s size classes are not your scene's size classes.** Read the trait collection or environment.
- **In `.overlay` arrangements the *primary* view floats** in the top leading corner; the secondary fills behind it. `overlayArrangementZIndex` reads 0 at the root — read it from a subview.
- **`.split` can drop the secondary view entirely** when both do not fit along an allowed axis.
- **The fold can override your ratio.** In book pose a split arrangement puts its divider on the fold even if `splitArrangementLayoutRatio` says otherwise.
- **The inner display is landscape-native (270°)** and does not honour `supportedInterfaceOrientations`.
- **New windows cannot be created on the outer display.** Window creation is dynamically available; handle the activation error.
- **Split View on iPhone means your bar can be on *either* edge** depending on which half you are in. See `references/audit-rules.md` for how to tell.

Capture from the Duo simulator with `xcrun simctl io booted screenshot --display=1` (outer) and `--display=3` (inner).

## 4. Testing

The iPhone Duo simulator in Device Hub is the only accurate target. The iPhone Air, the resizable simulator, and iPhone Mirroring are all substitutes that will not show vertical bars.

- Poses: **Closed / Book / Open** + Rotate Right, in every combination. Hold **Option** over the pose buttons for a hidden 0–180° hinge slider.
- Split View: drag your app to each half via the home indicator. The bar moves to the app's outer edge.
- Keyboard up in every pose — sizes differ enough to break bottom-pinned controls.
- Xcode Previews: the canvas overrides picker has a **Display** group for the alternative display, and Resizable Canvas mode.
- Capture from the Duo simulator with `xcrun simctl io booted screenshot --display=1` (outer) and `--display=3` (inner).
- **Known simulator issues:** first launch takes minutes; StandBy unavailable; most app extensions cannot run; screenshots and recordings may be **black for a few minutes after boot** — wait and verify content before capturing; VoiceOver and the Accessibility Inspector cannot convey content in Device Hub, so accessibility needs another route.

## 5. Shipping

**From April 2027 every App Store submission must include iPhone Duo screenshots.** That is the hard deadline driving this work.

Capture from the Duo simulator at 1398 × 2034 (outer) and 2007 × 2853 (inner), portrait and landscape. Framing them is already handled — use the **`frames-cli`** skill; its asset pack knows all four Duo sizes. App Store metadata and submission are the **`app-store`** skill.

## 6. References

| File | Load when |
|---|---|
| `references/api-surface.md` | Writing or reviewing Duo-specific code. Symbol names with version tags and doc links. |
| `references/measured.md` | Needing a number — display sizes, insets, bar widths, region frames, the 27.0-vs-27.1 ladder. |
| `references/audit-rules.md` | Running the audit or triaging findings. Detection patterns and replacements, SwiftUI and UIKit. |
| `references/camera.md` | The app uses AVFoundation. Camera is the one area with no system fallback. |
| `scripts/audit.sh` | Any audit pass. |

Apple's canonical pages, in reading order: [/iphone-duo/prepare/](https://developer.apple.com/iphone-duo/prepare/) → [Preparing your app for iPhone Duo](https://developer.apple.com/documentation/technologyoverviews/preparing-your-app-for-iphone-duo) → [Designing for iPhone Duo](https://developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo). All six Tech Talks (111461–111466) are on disk in `~/Dev/wwdc-sessions/sessions/tech-talks/` with full transcripts — the API detail here comes from them.
