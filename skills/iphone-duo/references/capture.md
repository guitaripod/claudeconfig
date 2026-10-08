# Capturing every state, and the App Store Connect slots

Contents: [Tools](#tools) · [The matrix script](#the-matrix-script) · [Reading the result](#reading-the-result) · [What cannot be scripted](#what-cannot-be-scripted) · [App Store Connect](#app-store-connect) · [Simulator quirks](#simulator-quirks)

## Tools

| Tool | Does | Install |
|---|---|---|
| `duoctl` | Fold, unfold, any hinge angle, rotate either display, tap and swipe on the inner display, report state as JSON, screenshot the display that is showing | below |
| `frames` | Applies Apple's real Duo bezels to the four slot sizes (the `frames-cli` skill) | `frames setup`; needs Pillow: `pip3 install --user Pillow` |
| `scripts/capture.py` | Runs the whole matrix with `duoctl`, validates and frames | none |

`simctl` has no pose command and Device Hub is GUI-only, so `duoctl` is the route. It is a third-party tool (github.com/skarol/duoctl, built on the HID event first documented by github.com/artemnovichkov/hinge) that posts private HID events **inside the simulator only**, through `simctl spawn`. It uses undocumented simulator interfaces verified with Xcode 27.1; if a command succeeds but `duoctl state` does not change, the interface has probably changed, so report it rather than retrying. Install a commit you have read (about 700 lines; commit `efd5e3d` was reviewed):

```bash
git clone https://github.com/skarol/duoctl ~/.local/share/duoctl
git -C ~/.local/share/duoctl checkout efd5e3d
ln -sf ~/.local/share/duoctl/skills/duoctl/scripts/duoctl ~/.local/bin/duoctl
```

`duoctl state` shows `activeScreen` (`cover` or `inner`), `orientation` and `sizePoints`. `orientation` names the interface, so the inner display is `landscape` by default. Use `duoctl screenshot out.png`, not `simctl io screenshot` without a display: the latter captures the inner display even while folded (black).

## The matrix script

```bash
scripts/capture.py --udid <udid> --bundle-id <id> --out <dir> \
  --env DEMO=1 --screen items:DEMO_SCREEN=items --screen detail:DEMO_SCREEN=detail
```

- `--screen NAME[:K=V,K=V]` is one screen and the launch variables that route to it (passed as `SIMCTL_CHILD_*`). An app with a launch-argument demo mode makes every screen one flag. Without one, use `--arg` and `duoctl tap`.
- States: `outer-portrait`, `outer-landscape`, `inner-landscape`, `inner-portrait`, `book-landscape` (127°), `laptop-portrait` (127°). `--states a,b` selects, `--list-states` prints them.
- `--appearance light,dark` multiplies the matrix; `--arg` passes launch arguments such as `-AppleLanguages (fi)` for locales.
- Per capture it waits, checks the app is still running (relaunching a dead one), screenshots, and rejects black or wrongly sized images (retrying with a longer wait). A state the app refuses, such as a landscape the app does not support on the outer display, is recorded as **skipped**, never as a pass.
- Writes `raw/`, `framed/` and `manifest.json`; exits 1 on any failure. It restores the simulator to light mode and an open, landscape state.

## Reading the result

Every cell gets looked at. Build a contact sheet per screen so one glance covers all states (Pillow: paste each raw image scaled to a common height). Things to find, from real runs:

- A control hidden under the camera or status column (a Done or close button at the top trailing corner).
- Text clipped by the status column; content running under the vertical bar.
- A column straddling the fold in `book-landscape` (a 3-column grid on a 951 pt display puts the middle column on the fold).
- A phone layout merely stretched on the inner display.
- The home screen where the app should be: the app died. The script catches this, but a demo mode that wipes state at launch can crash on relaunch, so verify.

## What cannot be scripted

Split View halves, Picture in Picture, multiple windows, the software keyboard (partly), the inner camera and the outer-display accessory. Cover them in this order of preference: `duoctl tap`/`swipe` on the inner display (the only tool whose touches reach it; AXe, idb and `simctl` taps hit the cover touchscreen and report success while doing nothing), an XCUITest, then by hand in Device Hub. Mark what was done by hand in the report. Camera, haptics and thermals need a physical Duo; never claim them from the simulator.

## App Store Connect

Apple's [screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications) define four Duo slots, each up to ten screenshots, per localization:

| Slot | Pixels |
|---|---|
| Outer, portrait | 1398 × 2034 |
| Outer, landscape | 2034 × 1398 |
| Inner, portrait | 2007 × 2853 |
| Inner, landscape | 2853 × 2007 |

Optional today; required for submissions built with the iOS 27.1 SDK or later from April 2027. Apple's news of 2026-10-05 says apps optimised for Duo can be submitted now. The slots are by display and orientation only, so there is no separate slot per pose: tell the pose story inside them (flat, book and laptop shots in the inner slots, the bar-side layout in the outer ones). Resizing existing portrait shots does not meet the spec; capture at the exact sizes, which `capture.py` enforces.

Plan the set per locale: at least one shot per slot the app supports, then spend the remaining nine on distinct poses and screens. That multiplies by locales: 4 slots × up to 10 × every locale the listing carries, so script it (`--arg -AppleLanguages`) and upload from the manifest.

**Upload path is unverified.** As of 2026-10-09: `asc` 5.4.0 lists no Duo display type, one forum report says the App Store Connect API's screenshot display-type enum has no Duo case yet, and secondary sources disagree on whether uploads opened on October 5. Before promising a date, check the App Store Connect web UI and `asc screenshots sizes --all`, and keep the framed output ready.

## Simulator quirks

First launch takes several minutes; the first screenshots can be black for a few minutes after boot (the script retries). StandBy and most app extensions are unavailable; VoiceOver and the Accessibility Inspector do not work inside Device Hub. Xcode 27.1 needs macOS 26.6 or later to run.
