---
name: iphone-duo
description: Take an iOS app from "works" to excellent on every iPhone Duo state (iOS 27.1, Apple's folding iPhone). Audits the code, fixes layout in a fixed tier order, scripts the simulator through every display, orientation and fold pose to capture and inspect each, optimises the app for each state instead of just surviving it, and produces the framed App Store screenshots for all four Duo slots. Use for "prepare for iPhone Duo", foldable iPhone, Duo screenshots, resizable windows, iPhone Split View, content colliding with the fold or cameras, or bars moving to a side edge.
---

# iPhone Duo

iPhone Duo (iOS 27.1) changes four things about layout:

1. **The scene changes displays mid-session**: 466 × 678 pt outer, 669 × 951 pt inner. The window is not the screen, and its size changes while the app runs.
2. **Bars go vertical**: status, navigation, toolbars and tab bars sit on one side edge on the outer display and on the inner display in landscape. Only the inner display in its tall layout keeps horizontal bars.
3. **The fold and the cameras reserve regions** that content must avoid.
4. **Split View and multiple windows arrive on iPhone**, so the app can be half the screen with its bar on either edge.

This is the adaptive-layout discipline iPad already demanded, with every escape hatch removed. The target is not "does not break" but excellent in every state: the inner display is an iPad-class canvas, the fold and laptop poses reward a deliberate layout, and App Store Connect wants screenshots for all four display slots. Most apps need tiers 1–4 for correctness and then a per-state optimisation pass.

## Workflow

Copy this checklist and work down it. Do not skip a gate.

```
- [ ] 0. SDK: links iOS 27.1, stamped correctly ("SDK first")
- [ ] 1. Baseline: scripts/audit.sh <repo>   (record the counts)
- [ ] 2. Tier 1 fixed, then: scripts/audit.sh --tier 1 reports 0 defects
- [ ] 3. Tier 2 fixed, then: scripts/audit.sh --tier 2 reports 0 defects
- [ ] 4. Tier 3 fixed, then: scripts/audit.sh --tier 3 reports 0 defects
- [ ] 5. Tier 4 reported to the owner (read-only)
- [ ] 6. Baseline matrix: scripts/capture.py over every screen and state, every cell looked at
- [ ] 7. Optimise: answer the questions in references/states.md per screen, then implement
- [ ] 8. Tier 5 only for what the system cannot do ("Does the system already do it?")
- [ ] 9. Full audit exits 0, builds against 27.1, matrix re-run: 0 failed, every cell reviewed
- [ ] 10. Ship: every placement App Store Connect lists (read it, then enforce it with `capture.py --spec`), every locale, build host verified ("Shipping")
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

**Inherited with standard components, no code:** `NavigationSplitView`/`UISplitViewController` collapse on the outer display and adjust around the fold. `TabView`/`UITabBarController` go vertical and can become a sidebar on the inner display. Sheets, alerts, menus and popovers move away from the fold (a plain `.sheet` takes the leading panel in book pose, the lower panel in the laptop pose). `.split` arrangements divide across the fold.

**Yours to handle:**

| Situation | Tool |
|---|---|
| Two views, main–detail | `ArrangementView` with `.split` |
| Two views, foreground over background | `ArrangementView` with `.overlay` |
| Grid that should divide across the fold | Even column count, decided from the *inactive* division region |
| Custom edge-to-edge chrome a container does not move | `reservedRegions(kind:)` |
| Effect that tracks how far it is folded | `onHingeChange`, **never for layout** |
| Camera UI that must follow the user between displays | `AVCaptureDeviceDirectionCoordinator` (`references/camera.md`) |

Move elements by purpose, not geometry: alerts toward the trailing side in book pose, media to the top region and controls to the stable bottom region in the laptop pose (Apple's name for a portrait inner display with a horizontal fold). Scrolling content does not displace; it already scrolls. Audit centred layouts first, since the centre is where the fold lands. Never drop a control in one pose that exists in another.

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

## Cover every state

Only the iPhone Duo simulator shows vertical bars, reserved regions and the fold. The state space is large: two displays, both orientations, flat, book and laptop poses, any angle between, Split View halves, Picture in Picture, windows, keyboard, camera, dark mode, Dynamic Type, locales. `references/states.md` lists every state with Apple's wording, what the system does, and what excellent means; `references/capture.md` has the tools.

**Fill every view with diverse, realistic data first.** A shot of an empty or uniform view is a failed shot. Seed enough content to fill the largest display (inner landscape is 951 × 669 pt: a dozen or more rows, several grid rows), with varied names including one long enough to truncate, a spread of magnitudes, every badge and state the UI can show (fine, expiring, expired, unread, error), varied imagery rather than one tile style, and believable documents (an itemised receipt, not a placeholder). Route different shots to different records through launch variables so no two screens show the same item, keep currency and dates in the device locale, use fictional people and no third-party platform names, and make the seeding deterministic, offline and safe to relaunch. `references/capture.md` has the checklist.

**Script the matrix, then look at it.** Install `duoctl` (`references/capture.md`; no GUI permission needed), then:

```bash
scripts/capture.py --udid <udid> --bundle-id <id> --out <dir> --env <K=V> \
  --screen items:<K=V> --screen detail:<K=V> --screen settings:<K=V>
```

It folds, unfolds, sets 127° and rotates through six states (outer portrait and landscape, inner landscape and portrait, book, laptop), launches each screen, rejects black, mis-sized or dead-app captures, frames the rest with `frames`, and writes a manifest. Skipped is not passed: a state the app refuses (landscape on the outer display of a portrait-only app) is a decision to make, not a gap to hide. If the app has a launch-argument demo mode, each screen is one flag; otherwise add one in DEBUG, with its seeding made safe to relaunch.

**Then inspect every cell** (a contact sheet per screen shows all states at once). Look for controls under the camera or status column (a Done or close button at the top trailing corner), clipped text, content under the vertical bar, a grid column on the fold, a phone layout stretched across the inner display, and a launcher screen where the app should be.

**Optimise, do not just repair.** For each screen answer the questions in `references/states.md` and implement the answers: the inner display wants an iPad-class layout (split view, sidebar, columns), book pose wants an even column count, the laptop pose can split content above controls below without removing anything, Apple asks for landscape on the outer display. Re-run the matrix after.

**Not scriptable:** Split View halves, Picture in Picture, windows, the inner camera and the outer-display accessory. Drive what `duoctl tap`/`swipe` can reach, do the rest by hand, and say which cells were manual. Camera, haptics and thermals need a physical Duo; never claim them from the simulator.

**Frame every shot with `frames`** (the `frames-cli` skill); the script does it and the framed output is the deliverable. Run `frames doctor` first; it needs Pillow (`pip3 install --user Pillow`).

Done means the SDK checks pass, the full audit exits 0, the matrix has 0 failed, and each cell has been looked at, not assumed.

## Shipping

App Store Connect has **four Duo screenshot slots**, each up to ten images per localization: outer 1398 × 2034 and 2034 × 1398, inner 2007 × 2853 and 2853 × 2007. Optional now; required for submissions built with the 27.1 SDK from April 2027; optimised apps can be submitted today. The slots are by display and orientation, not by pose, so tell the pose story inside them: flat, book and laptop shots in the inner slots, the bar-side layout in the outer ones. Resizing existing shots does not meet the spec. The UI can list more placements than these four sizes (product page Header, Search Results, each with outer and inner variants): Apple's public pages do not, so read the real list from App Store Connect, write it as a coverage spec and run `capture.py --spec` so no permutation is missed. Run the matrix per locale (`--arg -AppleLanguages`, `--appearance`) and upload from the manifest. Details and the upload-path caveat are in `references/capture.md`.

**Build host.** The Duo adaptation exists only in a binary linked against the iOS 27.1 SDK, so the build host must run Xcode 27.1 (needs macOS 26.6 or later) **and** be a stable macOS: a beta host stamps `BuildMachineOSBuild` and the upload is rejected (ITMS-90111). A host or VM still on Xcode 26.x produces a binary that never adapts. Tart guests cannot update their own macOS (`softwareupdate` fails with "Failed to find SFR recovery volume"), so a new guest has to be created from an IPSW. Check all three before starting the release: `xcodebuild -version`, `sw_vers -buildVersion`, `xcrun vtool -show-build <archive binary>` reads `sdk 27.1`.

Upload support is unverified (`references/capture.md`): confirm the path before promising a date. A featuring nomination's free-text Helpful Details can state support for all poses.

## References

| File | Load when |
|---|---|
| `references/audit-rules.md` | Triaging audit findings: patterns and replacements per tier, SwiftUI and UIKit |
| `references/api-surface.md` | Writing Duo code: every symbol, version-tagged, with gating recipes |
| `references/states.md` | Planning the optimisation: every state, Apple's rules, use-case patterns, per-screen questions |
| `references/capture.md` | Capturing: duoctl install, the matrix script, the four App Store slots, what cannot be scripted |
| `references/measured.md` | Needing a number: displays, insets, fold geometry, keyboards, device identity |
| `references/camera.md` | The app uses AVFoundation, the one area with no system fallback |

Apple, in reading order: [Prepare](https://developer.apple.com/iphone-duo/prepare/) → [Preparing your app for iPhone Duo](https://developer.apple.com/documentation/technologyoverviews/preparing-your-app-for-iphone-duo) → [Designing for iPhone Duo](https://developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo). Tech Talks 111461 (prepare), 111462 (bars), 111463 (adaptive layouts), 111464 (displays and scenes), 111465 (camera), 111466 (design). Apple's doc pages need JavaScript; swap `developer.apple.com` for `sosumi.ai` to fetch them as Markdown.
