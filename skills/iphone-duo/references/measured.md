# iPhone Duo — measured values

Nothing here is published as an Apple spec sheet. Provenance is mixed and marked inline: rows verified on a live iPhone Duo simulator running the 27.1 runtime are labelled as such; rows still sourced from community probes are named. **Simulator values until hardware ships October 23, 2026.**

## Displays

| | Portrait | Landscape | Scale | Native orientation |
|---|---|---|---|---|
| Outer | **466 × 678 pt** | 678 × 466 | @3x | 0° |
| Inner | **669 × 951 pt** | 951 × 669 pt | @3x | **270° (landscape-native)** |

Scale is @3x and this is arithmetically forced, not guessed: 1398/3 = 466, 2034/3 = 678, 2007/3 = 669, 2853/3 = 951 are all integers; at @2x the inner display would be 1003.5 × 1426.5 pt, which is impossible.

Pixel sizes are Apple's App Store Connect screenshot specifications, and were **re-measured on a live iPhone Duo simulator** on the 27.1 runtime — outer captured at 1398 × 2034, inner at 2007 × 2853, matching the point math exactly.

| Display | Portrait px | Landscape px |
|---|---|---|
| Outer | 1398 × 2034 | 2034 × 1398 |
| Inner | 2007 × 2853 | 2853 × 2007 |

**Closed pose, measured on the live Duo simulator with a 27.1-linked app:**

| Reported | Value |
|---|---|
| Scene (window) size | 466 × 678 |
| `GeometryReader` size | **382 × 644** — already inset: 466 − 84 (vertical bar) by 678 − 34 (home indicator) |
| `horizontalSizeClass` / `verticalSizeClass` | compact / regular |
| `toolbarVerticalEdge` | `trailing` |
| `displayScale` | 3.0 |
| Hinge | `status == .closed`, `angle == 0°` |
| Reserved regions | **none at all** — the outer display reports no division and no occlusion region, not even inactive ones |

The 84/34 inset arithmetic is why `GeometryProxy.size` is already inset — subtracting insets from it again double-counts. The `GeometryReader` size matching the community probe's closed-pose window is the confirmation that the probe was measuring the same thing.

Simulator device profile, single source — treat as reliable but not Apple-published: model `iPhone19,4`, product class `V68`, `A3447`, `minRuntimeVersion 27.1`, corner radius 59 outer / 55 inner, both displays P3, 460 ppi / 60 Hz (probe flags the last two as simulator placeholders), compatible-device fallback `iPhone18,3`. The inner framebuffer is a plain rounded rectangle with **no camera cutout** — the camera's occlusion comes from the reserved-region API at runtime.

## Scene sizes and size classes

| State | Size | Horizontal × Vertical size class |
|---|---|---|
| Closed, portrait | 466 × 678 | compact × regular |
| Closed, landscape | 678 × 466 | compact × compact |
| Open, tall | 669 × 951 | regular × regular |
| Open, wide | 951 × 669 | regular × regular |

The outer display's size classes change when you rotate a closed device, exactly like any other iPhone. Do not assume they are fixed.

## Safe area insets and the vertical bar

| Configuration | Inset values |
|---|---|
| Closed | top 82, bottom 34, **trailing 84** |
| Open, wide | **trailing 84** |
| Open, tall | top 82, bottom 83 (bars horizontal) |

The vertical bar strip is **84 pt** on the edge that carries the front camera. Rotate the closed device and the column follows the camera: trailing in portrait and in landscape-left, **leading** in landscape-right. So a control placed "on the right" must read the edge, not assume it.

Single-source probe measurement; not an Apple spec. Treat as a sanity check, never as a constant to hardcode.

## The fold

| Property | Value |
|---|---|
| Division region frame | **40 pt** wide, with **20 pt** margins on the fold axis |
| Position | 455.5 pt from the edge of the 951 pt side; frame is constant in every pose |
| Active | Only while partially folded. Flat: inactive, zero-width fold line |
| Book pose | `status == .partiallyOpen`, hinge ~127° |

The `isActive` flag does **not** switch as a function of angle in a predictable way — across four continuous sweeps it turned on at 98, 132.5, 132.5 and 172.6°. Query on every layout pass and lay out from what you are told.

Inner camera occlusion region while active: ~58 × 37 pt. Status-column occlusion region: 84 × 120 pt.

## Hinge status vs angle

| Interaction | Reported status |
|---|---|
| Drag | `partiallyOpen` from 20.0–20.8°; back to `closed` at 27.0° or 45.9°; `fullyOpen` only at 180.0° |
| Click | Settles by band: `closed` at 36.6, 71.2, 108.6, 123.3°; `partiallyOpen` at 143.1° |

Same angle, different pose, depending on how it was reached. **Never derive posture from the angle.** React to `status` and scene geometry; use the angle only for continuous effects.

## Keyboard

| Pose | Size |
|---|---|
| Open, tall | 669 × 350 |
| Open, wide | 951 × 264 |
| Closed, landscape | 678 × 230 |
| Closed, portrait | 466 × 289 |

## What linking against iOS 27.0 vs 27.1 actually gets you

Measured by building the same source twice. This is the whole argument for the SDK bump.

| | Linked 27.0 | Linked 27.1 |
|---|---|---|
| Closed | window 386 × 678 with an 80 pt black rail; **horizontal** bars; `toolbarVerticalEdge` nil; **no reserved regions** | full 466 × 678; **vertical** bars on trailing; `toolbarVerticalEdge` = trailing; two active occlusions |
| Open | window 871 × 669, rail on the right, 34 pt insets each side, no regions | 951 × 669, regular × regular, vertical bars, one inactive division (40 pt, full height, x 455–495, 20 pt margins) + inactive inner-camera occlusion + active status-column occlusion |
| Open, rotated right | 80 pt band across the top | 669 × 951, **horizontal** bars, same three regions rotated |

Apple's guard: *"Build your app with the latest version of Xcode to use all of the available screen space on iPhone Duo. When you build with Xcode 26 and earlier, your app doesn't extend under the status bar and camera."*

`UIScreen.main` still reports the outer display's 466 × 678 while the app is on the inner display, and its size classes are not the scene's.

## Cameras

Both front cameras are square ultrawide sensors.

| Camera | Max video | Notes |
|---|---|---|
| Outer ultrawide | **4K120** | Always visible, corner of the outer display |
| Inner ultrawide | **1080p60** | Under-display, hidden until active |
| Virtual Front Camera | 1080p60 | Intersection of both cameras' capabilities; no depth |

Depth is only available when addressing an individual camera, not the virtual one. See `camera.md`.

## Device identity — verified from the Xcode 27.1 RC simulator profile

Extracted from `iPhone Duo.simdevicetype` in Xcode 27.1's `XcodeSystemResources.pkg`. These are Apple's own values, not a probe.

| Field | Value |
|---|---|
| Simulator device type | `com.apple.CoreSimulator.SimDeviceType.iPhone-Duo` |
| Alias | `com.apple.CoreSimulator.SimDeviceType.V68` |
| `modelIdentifier` / `representedModelIdentifiers` | `iPhone19,4` |
| `productClass` | `V68` |
| `minRuntimeVersion` | 27.1 |
| `createByDefaultForRuntimeVersions` | 27.1 and later — so it is created automatically once the 27.1 runtime is present |
| `supportedProductFamilyIDs` | 1 (iPhone) |
| `supportedArchs` | arm64, x86_64 |
| `springBoardConfigName` | `iPhone4Simulator` |

Relevant `supportedFeatures`: `com.apple.display.integrated`, `com.apple.display.supports-external`, `com.apple.display.aot`, `com.apple.hid.staccato`. Conditional on runtime: **`com.apple.CoreSimulator.display.resizableScene`** — the resizable scene machinery is what makes Split View and the resizable window work.

`com.apple.CoreSimulator.EnhancedMultitasking` is absent, which is the simulator-profile confirmation that there is no Stage Manager on Duo.

## Simulator

Creating and booting the Duo works once the package install has completed — `xcrun simctl create "iPhone Duo" com.apple.CoreSimulator.SimDeviceType.iPhone-Duo com.apple.CoreSimulator.SimRuntime.iOS-27-1` then `xcrun simctl boot <udid>`, confirmed on the RC.

- Exactly three pose buttons — **Closed, Book, Open** — plus Rotate Right. Hold **Option** over them for a hidden 0–180° hinge slider.
- **No `simctl` pose command, confirmed:** `xcrun simctl ui` only sets appearance (dark mode, increase contrast, content size). Poses come from Device Hub. Driving its buttons additionally needs macOS Accessibility permission, so it cannot be automated from an SSH session.
- Capture: `xcrun simctl io <udid> screenshot --display=1` (outer), `--display=3` (inner). Both sizes verified on a live device.
- **Creating the Duo device needs admin authorization.** The device type ships inside `XcodeSystemResources.pkg`. Copying `iPhone Duo.simdevicetype` into `~/Library/Developer/CoreSimulator/Profiles/DeviceTypes/` makes `simctl list devicetypes` show it, but `simctl create` then fails with `Authorization is required to install the packages` — the authorization is for the *package*, not the file. Fix: `sudo installer -pkg <Xcode>/Contents/Resources/Packages/XcodeSystemResources.pkg -target /`.

**Known issues that affect testing:** first launch takes several minutes; StandBy unavailable; most app extensions cannot be run or debugged; screenshots and recordings may be **black for a few minutes after boot**; VoiceOver and the Accessibility Inspector cannot convey content inside Device Hub; Device Hub resize mode with a pre-iOS-27-linked app is unsupported and may show a black screen; exiting resize mode other than through the toolbar leaves content mis-sized until reboot.
