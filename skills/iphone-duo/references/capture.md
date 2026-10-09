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
- `--states fold-cycle` is the continuity test: each screen is launched once on the open inner display, the device is folded closed and opened again without relaunching, and all three moments are captured (`fold-open`, `fold-closed`, `fold-reopen`). Compare them: the same item or screen should survive the fold, and the split layout should return. Verified on a real app: an item open beside its list stayed open on the outer display and the split came back on reopening.
- `--appearance light,dark` multiplies the matrix; `--arg` passes launch arguments such as `-AppleLanguages (fi)` for locales.
- Per capture it waits, checks the app is still running (relaunching a dead one), screenshots, and rejects black or wrongly sized images (retrying with a longer wait), and fails a capture identical to another screen in the same state. A state the app refuses, such as a landscape the app does not support on the outer display, is recorded as **skipped**, never as a pass.
- Writes `raw/`, `framed/` and `manifest.json`; exits 1 on any failure. It restores light mode and the display and orientation the simulator started on. `outer-landscape` tries the opposite landscape when the first is refused.

## Mock data for the shots

Seed it in a DEBUG-only mode switched by launch variables (`SIMCTL_CHILD_*`), never in release code. Checklist:

- **Volume:** enough rows and cards that every display, including inner landscape (951 × 669 pt), is full, not half empty. Keep under any free-tier cap or paywall threshold so the shot does not show an upsell.
- **Diversity:** several categories or groups; names of mixed length with at least one that truncates; prices or counts from small to large; every status the UI can show, in proportion; imagery that varies (different symbols, palettes or real artwork), not one repeated tile.
- **Realism:** documents and details that read as real (store, date, itemised lines, tax, order number), in the device locale's currency and date format; no lorem ipsum, no "Test 1".
- **Distinct shots:** route each screen to a different record with variables (`DEMO_CATEGORY`, `DEMO_ITEM` by name), so a gallery of detail screens shows a camera, a long-name appliance, an expiring item and an expired one, not the first row five times. `capture.py` fails a capture that is perceptually identical to another screen in the same state, which is the usual sign that routing failed.
- **Forms:** pre-fill the add or edit flow with plausible values instead of showing it empty.
- **Safe:** deterministic, no network, no real personal data, and wiping and reseeding inside `performAndWait` so relaunching cannot crash.

## Reading the result

`scripts/sheet.py --manifest <run>/manifest.json [--manifest ...] --out sheet.png` builds one PNG of every permutation in its device frame: rows are screens, columns are states, empty cells labelled `none`. Later manifests patch earlier ones, so a re-run of a few cells fixes a full run. Look at it first: columns and rows expose what single shots hide (a column where every title sits under the camera, a row that never changed).

Every cell gets looked at. Build a contact sheet per screen so one glance covers all states (Pillow: paste each raw image scaled to a common height). Things to find, from real runs:

- **Outer landscape facing the wrong way.** Closed, the camera and bar column are on the left in `landscape-flipped`, which is where Apple's frame artwork draws the camera. The other direction puts the bar on the right, so the frame's camera lands on the nav title. `capture.py` uses `landscape-flipped` for `outer-landscape` for that reason.
- A control hidden under the camera or status column (a Done or close button at the top trailing corner).
- Text clipped by the status column; content running under the vertical bar.
- A column straddling the fold in `book-landscape` (a 3-column grid on a 951 pt display puts the middle column on the fold).
- A phone layout merely stretched on the inner display.
- The home screen where the app should be: the app died. The script catches this, but a demo mode that wipes state at launch can crash on relaunch, so verify.

## What cannot be scripted

Split View halves, Picture in Picture, multiple windows, the software keyboard (partly), the inner camera and the outer-display accessory. Cover them in this order of preference: `duoctl tap`/`swipe` on the inner display (the only tool whose touches reach it; AXe, idb and `simctl` taps hit the cover touchscreen and report success while doing nothing), an XCUITest, then by hand in Device Hub. Mark what was done by hand in the report. Camera, haptics and thermals need a physical Duo; never claim them from the simulator.

## App Store Connect

Needs `asc` 5.12 or later (Duo support landed in 5.12.0; `asc version`, upgrade with the installer in the `app-store` skill). Read Apple's current numbers first, never from memory: `scripts/asc-specs.py` prints them from `asc asset-library specs`. As of 2026-10-09:

| Placement | Group | Max | Accepts |
|---|---|---|---|
| Duo screenshots (`APP_SCREENSHOT`, display type `APP_IPHONE_DUO`) | `IPHONE_DUO_PROFILE` | **10 in total** | 2034 × 1398, 1398 × 2034, 2853 × 2007, 2007 × 2853; PNG or JPEG; **no alpha** |
| Duo previews (`APP_PREVIEW`) | `IPHONE_DUO_PROFILE` | 3 | video 1920 × 886 or 886 × 1920, 23 fps, 15 to 30 s, **audio required** |
| Product page **Header** (`PRODUCT_PAGE_HEADER_ASSET`) | `DEFAULT_PROFILE` | 1 | image 5244 × 2950 PNG (16:9, universal) or 3840 × 1646 PNG (21:9); or video 3840 × 1646, 5 to 30 s |
| **Search Results** (`APP_STORE_SEARCH_RESULTS_ASSET`) | `DEFAULT_PROFILE` | 1 | image 5244 × 2950 PNG (universal) or 3:2 from 1920 × 1280 to 3840 × 2560, PNG or JPEG; or video 3:2, 5 to 30 s |

Header and Search Results are creative assets, one per localization, not Duo-specific and not screenshots: they are composed marketing images. The universal 5244 × 2950 PNG satisfies both. The Duo group is one set with a cap of 10 per localization, shared by all four sizes (the dry run accepts mixed sizes in one upload), so spend the ten deliberately; Duo screenshots are optional now and required for submissions built with the iOS 27.1 SDK from April 2027; optimised apps can be submitted today. The screenshot slots are by display and orientation, not pose, so tell the pose story inside them (flat, book and laptop shots in the inner slots, the bar-side layout in the outer ones). Resizing existing shots does not meet the spec.

Produce and place:

```bash
scripts/capture.py ... --spec spec.json                    # screenshots, all four sizes enforced
scripts/compose.py --out <dir> --hero <inner framed> --second <outer framed>   # Header and Search images
asc asset-library images upload --library-id <id> --file <png> --category CREATIVE_ASSETS
asc localizations placements create --localization-id <id> --image-id <id> \
    --placement-type PRODUCT_PAGE_HEADER_ASSET            # or APP_STORE_SEARCH_RESULTS_ASSET
asc screenshots upload --app <id> --version-id <v> --locale en-US --path <dir of RAW captures> \
    --device-type IPHONE_DUO [--dry-run | --replace --confirm]   # Duo screenshots, display type APP_IPHONE_DUO
```

`asc localizations placements create` takes `--placement-group IPHONE_DUO_PROFILE` for screenshots and previews, and `DEFAULT_PROFILE` for Header and Search. It never removes an existing placement and does not submit for review. The coverage spec for `capture.py --spec` is the four Duo sizes with the count you plan per locale, so none is forgotten:

```json
{"cells": [{"name": "inner landscape", "size": [2853, 2007], "min": 4,
            "states": ["inner-landscape", "book-landscape"]}]}
```

Plan per locale (ten shots in all, numbered so they sort in show order): lead with the inner landscape list-and-detail hero, then the book pose, inner portrait and laptop poses, then the outer portrait and landscape layouts; plus one Header and one Search image and, if wanted, previews. Multiply by every locale on the listing, and script it (`--arg -AppleLanguages`). Uploading changes the draft listing, so stage and review the files before placing them.

## Submitting

Order that worked end to end (Inventory 2.1.0, 2026-10-09): build and upload with `buildvm` on a stable Xcode 27.1 host, wait for the build to be `VALID`, `asc versions attach-build`, set What's New for every locale and read it back, upload the Duo sets and place Header and Search, `asc validate`, then create the review submission, add the app version, and submit.

- **`asc validate` first, fix every error.** It caught two newly required age-rating fields, `socialMedia` and `socialMediaAgeRestricted`; set them with `asc age-rating edit --app <id> --social-media false --social-media-age-restricted false` only when the app genuinely has no social features. It also flagged a copyright without a year and a locale description missing the Terms of Use link (a past rejection cause); fix those too.
- **Placed Header and Search images are reviewed with the version.** Adding them to the submission as separate items fails with "Asset is locked by an embedded review submission"; leave them out.
- **Submit:** `asc review submissions-create --app <id> --platform IOS`, `asc review items add --submission <id> --item-type appStoreVersions --item-id <version>`, `asc review submissions-submit --id <id> --confirm`; the version then reads `WAITING_FOR_REVIEW`.
- **Fan-out screenshot uploads can stop mid-run** with "Can't Add/Remove Relationship when reorder Set". Do not trust the exit text: list every locale (`asc screenshots list --version-id <v> --locale <l>`), check ten per locale, in order, no duplicates, all four sizes and `COMPLETE`. `--resume` once produced a duplicate and a wrong order; the reliable repair is one locale at a time with `--replace --confirm`, retrying after a pause.
- **Capture per locale with `--only`** (screen and state pairs) and `--arg=-AppleLanguages --arg="(<lang>)"`: ten captures take about a minute and a half per locale.

## Simulator quirks

Simulator screenshots carry an **alpha channel**, and App Store Connect rejects them ("image has an alpha channel or transparency"). `capture.py` rewrites every capture as opaque RGB; upload the raw captures, not the framed images (framed images have other dimensions and are for review and the Header and Search compositions). 
The active display decides what coordinates mean: `duoctl state` before any manual `tap`, because the cover display and the inner display have different sizes and `simctl launch` opens the app on whichever is active. The outer display can wedge (every rotate refused, the app launching without ever getting a scene); `simctl shutdown` then `boot` clears it. 
First launch takes several minutes; the first screenshots can be black for a few minutes after boot (the script retries). StandBy and most app extensions are unavailable; VoiceOver and the Accessibility Inspector do not work inside Device Hub. Xcode 27.1 needs macOS 26.6 or later to run.
