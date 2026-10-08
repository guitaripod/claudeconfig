---
name: iphone-duo
description: Make an iOS app work well on iPhone Duo, Apple's folding iPhone (iOS 27.1). Runs a grep audit, fixes layout in a fixed tier order, decides when system components already adapt versus when to use the new reserved-region, arrangement, vertical-bar and hinge APIs, and verifies every pose. Use for "prepare for iPhone Duo", foldable iPhone, resizable windows, iPhone Split View, content colliding with the fold or cameras, or bars moving to a side edge.
---

# iPhone Duo

iPhone Duo (iOS 27.1) changes four things about layout:

1. **The scene changes displays mid-session**: 466 × 678 pt outer, 669 × 951 pt inner. The window is not the screen, and its size changes while the app runs.
2. **Bars go vertical**: status, navigation, toolbars and tab bars sit on one side edge on the outer display and on the inner display in landscape. Only the inner display in its tall layout keeps horizontal bars.
3. **The fold and the cameras reserve regions** that content must avoid.
4. **Split View and multiple windows arrive on iPhone**, so the app can be half the screen with its bar on either edge.

This is the adaptive-layout discipline iPad already demanded, with every escape hatch removed. Most apps need tiers 1–4 and nothing from the new APIs.

## Workflow

Copy this checklist and work down it. Do not skip a gate.

```
- [ ] 0. SDK: links iOS 27.1, stamped correctly ("SDK first")
- [ ] 1. Baseline: scripts/audit.sh <repo>   (record the counts)
- [ ] 2. Tier 1 fixed, then: scripts/audit.sh --tier 1 reports 0 defects
- [ ] 3. Tier 2 fixed, then: scripts/audit.sh --tier 2 reports 0 defects
- [ ] 4. Tier 3 fixed, then: scripts/audit.sh --tier 3 reports 0 defects
- [ ] 5. Tier 4 reported to the owner (read-only)
- [ ] 6. Tier 5 only for what the system cannot do ("Does the system already do it?")
- [ ] 7. Full audit exits 0 and the app builds against the 27.1 SDK
- [ ] 8. Pose matrix passed ("Verify every pose")
```

### SDK first

Behaviour is stamped by the linked SDK, not the deployment target. An app linked against 27.0 or earlier **never adapts**: it gets a 386 × 678 window beside an 80 pt black rail, horizontal bars and no reserved regions. Nothing errors, so check it:

- `xcodebuild -showsdks` lists an iOS Simulator 27.1 SDK.
- `xcrun vtool -show-build <binary>` reads `sdk 27.1`. A command-line build with `-sdk` but no `SDKROOT` was stamped 27.0 and silently lost the vertical bar and `toolbarVerticalEdge`.
- The Duo simulator runtime is a separate multi-GB download (`xcodebuild -downloadPlatform iOS`).

The audit and every source fix work without the SDK. Only compiling Duo symbols and pose screenshots need it. For Apple's generic half (scene lifecycle, orientation, idiom), also run its `app-resizability` skill: `xcrun agent skills export --output-dir ~/duo-skills` (needs a running Xcode). This skill is the Duo layer on top.

### Audit and fix, in tier order

`scripts/audit.sh <repo>` is grep-based, prints file:line, and exits 1 only on **DEFECT** (wrong on Duo). **REVIEW** hits need judgement and never gate. `--review` lists them, `--json` emits one object per hit, `--exclude '*Tests*'` skips paths. A DEFECT that is genuinely fine (a deliberate `UIScreen.main` in a non-UI utility) gets excluded or rewritten, not ignored.

**Do not reorder.** Each tier assumes the previous one is clean:

| Tier | Fixes | Why it comes here |
|---|---|---|
| 1 | Screen, orientation, idiom, key window | Neither device nor rotation is knowable when the display changes |
| 2 | Safe areas, layout margins, keyboard | A vertical bar puts the whole inset on one edge and zero on the other; iOS 27.1 also zeroed a `UIView`'s default layout margins |
| 3 | Bars | Custom `UIToolbar`/`UINavigationBar`/`UITabBar` and hand-rolled `HStack` toolbars never go vertical; only bars owned by `UINavigationController`, `UITabBarController`, `NavigationStack` or `NavigationSplitView` do |
| 4 | Plumbing | Launch screen, `UIRequiresFullScreen`, scene lifecycle, orientations. **Report, never change silently** |
| 5 | Arrangements, reserved regions | Last. Reaching here early is the most common mistake |

Detection patterns and the replacement for each are in `references/audit-rules.md`. After each tier, re-run that tier's audit and the build before moving on.

## Does the system already do it?

**Inherited with standard components, no code:** `NavigationSplitView`/`UISplitViewController` collapse on the outer display and adjust around the fold. `TabView`/`UITabBarController` go vertical and can become a sidebar on the inner display. Sheets, alerts, menus and popovers move away from the fold (a plain `.sheet` takes the leading panel in book pose, the lower panel in tabletop). `.split` arrangements divide across the fold.

**Yours to handle:**

| Situation | Tool |
|---|---|
| Two views, main–detail | `ArrangementView` with `.split` |
| Two views, foreground over background | `ArrangementView` with `.overlay` |
| Grid that should divide across the fold | Even column count, decided from the *inactive* division region |
| Custom edge-to-edge chrome a container does not move | `reservedRegions(kind:)` |
| Effect that tracks how far it is folded | `onHingeChange`, **never for layout** |
| Camera UI that must follow the user between displays | `AVCaptureDeviceDirectionCoordinator` (`references/camera.md`) |

Move elements by purpose, not geometry: alerts toward the trailing side in book pose, media to the top region and controls to the stable bottom region in tabletop. Scrolling content does not displace; it already scrolls. Audit centred layouts first, since the centre is where the fold lands. Never drop a control in one pose that exists in another.

## Traps that are not in Apple's docs

Measured on the 27.1 simulator unless marked.

- **Never derive posture from the hinge angle.** `status` flips to `partiallyOpen` at ~20° and back to `closed` at 27° or 46° while dragging, but settles by band after a click. Same angle, different pose. Branch on `status`, scene geometry and reserved regions; use the angle only for effects. Apple's framework engineers confirm there is **no guaranteed update frequency**, so smooth with a spring and treat the angle as a target, not a per-frame input.
- **Reserved regions arrive after the first layout pass, and an empty result is not proof.** Read them inside the `GeometryReader` body or `layoutSubviews` on every pass; never cache, never decide once at launch. Even `.includeInactive` has returned `[]` on a Duo in `viewDidAppear` (Apple Developer Forums thread 847902, unanswered). Do not build a "detect Duo at startup" branch; lay out from what you are told.
- **The outer display reported no regions at all** in a live 27.1 probe, not even inactive ones. Empty does not mean "no camera to avoid".
- **`GeometryProxy.size` is already inset.** Subtracting the safe area again counts it twice.
- **`UIScreen.main` stays 466 × 678 on the inner display**, with its own size classes.
- **The vertical bar follows the camera.** A closed device rotated flips the 84 pt column between trailing and leading. A control "on the right" must read the edge. `toolbarVerticalEdge` is `HorizontalEdge?` in SwiftUI (nil = none or unresolved) and `UIVerticalBarEdge` in UIKit (`unspecified`); it resolves leading/trailing while `safeAreaInsets` is physical.
- **In Split View the bar can be on either edge**, and window-to-screen conversion returns `{0,0}` for both halves. A reserved-region frame is clipped to your view, so a narrow sliver at the shared edge tells you the side (`references/audit-rules.md`, tier 2).
- **`.overlay`: the *primary* view floats** top-leading over the secondary; `overlayArrangementZIndex` reads 0 at the root, so read it from a subview. **`.split` can drop the secondary view** when both do not fit along an allowed axis, with no error. **The fold overrides `splitArrangementLayoutRatio`** in book pose.
- **The inner display is landscape-native (270°) and ignores `supportedInterfaceOrientations`.**
- **New windows cannot be created on the outer display**; handle the activation error.
- **Fill-cropped 16:9 media on the inner display wastes about 134 pt**, a fifth of the screen. Pick fill or fit from the current aspect ratio.

## Verify every pose

Only the iPhone Duo simulator (`com.apple.CoreSimulator.SimDeviceType.iPhone-Duo`, created for the 27.1 runtime) shows vertical bars and reserved regions. A resizable simulator or iPhone Mirroring covers general resizing only.

| Axis | Cases |
|---|---|
| Pose | Closed, Book, Open, each also Rotate Right |
| Between poses | Hold **Option** over the pose buttons for the 0–180° hinge slider; look for content under the fold at partial angles |
| Mid-session | Launch closed, navigate deep, open it; fold while a sheet, alert or keyboard is up; selection and scroll state survive |
| Split View | Drag the app to **each** half of the inner display; the bar sits on the app's outer edge, so test both sides |
| Keyboard | Up in every pose (230–350 pt tall); bottom-pinned controls break first |
| Previews | Canvas overrides **Display** group; Resizable Canvas for arbitrary sizes |

**Closed pose needs no Device Hub.** Build, `simctl install`, `simctl launch`, then `simctl io <udid> screenshot --display=1`: the outer display is the default view. That alone catches most defects, so run it on every screen before touching poses. Look for controls hidden under the camera (a Done or close button at the top trailing corner), text clipped by the status column, and content running under the vertical bar. If the app has a launch-argument demo mode, use it to reach each screen; pass its variables as `SIMCTL_CHILD_<NAME>=…`. Use `--terminate-running-process` when relaunching.

Screenshots: `xcrun simctl io booted screenshot --display=1` (outer), `--display=3` (inner). The inner display is black while the device is closed. They can be **black for a few minutes after boot**, and first launch takes several minutes; wait and check the file before judging. `simctl` has no pose command, so poses are driven from Device Hub (which needs Accessibility permission, so it cannot be scripted over SSH). Most app extensions cannot run, and VoiceOver and the Accessibility Inspector do not work inside Device Hub.

**Frame every shot with `frames`** (the `frames-cli` skill), both the ones you inspect and the ones you ship: `frames -o <dir> <shots>`. It auto-detects the four Duo sizes and applies the real bezel and camera, so a control under the camera is obvious, and the output is the deliverable. Run `frames doctor` first; it needs Pillow (`pip3 install --user Pillow`) and, for video only, ffmpeg.

**Not verifiable in the simulator**: camera switching between displays and cameras, haptics, thermals. Say so rather than claiming a pass. Camera work needs a physical Duo.

Done means the SDK checks pass, the full audit exits 0, and each cell above has been looked at, not assumed.

## Shipping

**From April 2027 every App Store submission must include iPhone Duo screenshots.** Capture from the simulator at the exact sizes below; resizing existing portrait screenshots does not meet the spec.

| Display | Portrait | Landscape |
|---|---|---|
| Outer | 1398 × 2034 | 2034 × 1398 |
| Inner | 2007 × 2853 | 2853 × 2007 |

**Build host.** The Duo adaptation exists only in a binary linked against the iOS 27.1 SDK, so the build host must run Xcode 27.1 (needs macOS 26.6 or later) **and** be a stable macOS: a beta host stamps `BuildMachineOSBuild` and the upload is rejected (ITMS-90111). A host or VM still on Xcode 26.x produces a binary that never adapts. Tart guests cannot update their own macOS (`softwareupdate` fails with "Failed to find SFR recovery volume"), so a new guest has to be created from an IPSW. Check all three before starting the release: `xcodebuild -version`, `sw_vers -buildVersion`, `xcrun vtool -show-build <archive binary>` reads `sdk 27.1`.

As of 2026-10-09, `asc` 5.4.0 lists no Duo screenshot display type and a third-party guide reports App Store Connect upload support as "later this year". Confirm your upload path before planning around the deadline. A featuring nomination can flag an app as optimised for all poses.

## References

| File | Load when |
|---|---|
| `references/audit-rules.md` | Triaging audit findings: patterns and replacements per tier, SwiftUI and UIKit |
| `references/api-surface.md` | Writing Duo code: every symbol, version-tagged, with gating recipes |
| `references/measured.md` | Needing a number: displays, insets, fold geometry, keyboards, device identity |
| `references/camera.md` | The app uses AVFoundation, the one area with no system fallback |

Apple, in reading order: [Prepare](https://developer.apple.com/iphone-duo/prepare/) → [Preparing your app for iPhone Duo](https://developer.apple.com/documentation/technologyoverviews/preparing-your-app-for-iphone-duo) → [Designing for iPhone Duo](https://developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo). Tech Talks 111461 (prepare), 111462 (bars), 111463 (adaptive layouts), 111464 (displays and scenes), 111465 (camera), 111466 (design). Apple's doc pages need JavaScript; swap `developer.apple.com` for `sosumi.ai` to fetch them as Markdown.
