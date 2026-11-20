---
name: ipados
description: Make an iOS app excellent on iPad — layout at every window size (Full Screen Apps splits, Windowed Apps, Stage Manager, Slide Over), both orientations, iPad mini through 13-inch, two-thumb landscape reach, resize/redraw speed, and performance measured on Marcus's real iPads and in the field. Use for any iPad layout, "crushed"/stretched split windows, iPad mini work, thumb reach, iPad performance or hitches, or verifying an app on the iPad. Covers Tailscode, Flaccy and Unrager's existing iPad layers.
---

# iPadOS

An iPad app is judged by its worst window, not its best screenshot. iPadOS 26+ lets every window be any size at any moment, so a layout is a function of the window's size, re-decided on every change, never of the device. And iPadOS shows the app's **last frame stretched into the new tile until the app draws again**: a slow resize *looks* crushed even when the layout is right.

## Devices

| Device | Points | How to reach it |
|---|---|---|
| iPad Pro 11-inch (M1), iPadOS 27.x | 1194 × 834, **usually held in landscape** | Always on, usually wired to the Mac. devicectl `CD771E70-8FB3-5862-B649-CC61B4493A1B` (UDID `00008103-0019349C0ED0801E`). Instruments works (`xctrace --device`). |
| iPad mini (A20 Pro), iPadOS 27.x | 756 × 1158, **usually upright** | Usually wireless. UDID `00008160-00080C6834700036`. When it is wired to arch instead: build/sign on the Mac, `rsync` the `.app`, then `~/.local/share/pmd-venv/bin/pymobiledevice3 apps install <app> --developer --udid <udid>`. |
| iPhone XS, iOS 18.7 | 375 × 812 | Always on, usually wired. devicectl `D6798952-B031-588C-AFFB-FA9B46B061A3`. The oldest iOS for apps that support iOS 18. |
| iPhone Air, iOS 27.x | 420 × 912 | Usually wireless. devicectl `0A19DF7B-F393-5AA6-AD32-F997CC562974`. Whenever it is unlocked and available, every iPhone test runs on it too. |
| Simulators, iOS 27.3 runtime | iPad mini (A20 Pro), iPad Pro 11/13 (M5) | Fresh 27.3 iPad sims boot in **Windowed Apps** mode. Create your own, delete them after. |

Check what is reachable first: `xcrun devicectl list devices`. Test each iPad in the orientation it lives in (the Pro sideways, the mini upright) and optimise for both orientations.

Real hardware is truth for timing, hitches, rotation, real Full Screen Apps splits, keyboard and touch. Simulators are for other sizes, scripted capture matrices and parallel runs. A dev build installed on an iPad replaces the TestFlight build until the next TestFlight install (data stays, same bundle id); never uninstall an app on a device. Tailscode is how Marcus talks to these sessions: installing a dev Tailscode on the iPad he may be holding interrupts him — prefer field logs and the simulator for Tailscode, and say so before replacing it. Several agents share the iPad Pro: wrap every install/launch/profile session in `lockf -k -t 3600 /tmp/ipad-pro-m1.lock bash -c '…'`.

**Window sizes that matter** (11-inch landscape): Full Screen Apps split ≈ 375 (⅓, compact), 592 (½, compact), 834 (⅔, regular); mini: 368 / 575 / 773. Upright: halves ≈ 375–417. Windowed: anything, e.g. 834 × 600 (top half of portrait). Size class flips to compact below ≈ 680 pt.

## Design contract

1. **Columns from what each needs.** Give every column a minimum readable width; when the window cannot give all of them their minimum, a column steps back (overlay, bar, sheet) instead of all shrinking. Decide with a pure, unit-tested function of width *and* height (a phone on its side is short and wide; a 2/3 tile is square).
2. **Content in the middle, controls at the hands.** Held sideways in both hands each thumb reaches ~300 pt in on an 11-inch and ~400 pt on a mini, from about a third of the height down. Frequent actions go in those wells: navigation under the left thumb, the primary action under the right. A window sharing the screen meets one side edge — that is the reachable side for its floating controls (convert the window's bounds to `windowScene.screen.coordinateSpace`; re-read on `windowScene(_:didUpdateEffectiveGeometry:)`, and on the pre-26 coordinate-space callback). Upright, a mini is held like a large phone: keep bottom placement.
3. **Redraw fast.** Measure resize-to-first-frame with realistic data; anything over ~100 ms on device shows a stretched frame. Never measure every row at a new width — measure what is on screen, estimate the rest, settle it in idle slices, keep the reader's position. Don't do appearance work (reloads, first-responder grabs, network refreshes) when a view controller is only being carried between columns.
4. **Every state.** Empty, loading, error, long content, sheets and popovers, keyboard up, Dynamic Type large, light and dark, RTL, and a resize while something is open (scroll, selection and drafts survive).
5. **No iPhone or Duo regression.** Gate on size, never idiom, and check an iPhone simulator.

## Verification loop

1. Capture a matrix: each main screen × {11-inch landscape, 11-inch upright, ⅔, ½, ⅓, 834 × 600, mini both ways} × {light, dark}. Use the app's DEBUG window hook (below) for exact sizes and real windowed resizes with `axe drag` on the bottom-right grabber for live behaviour. `axe describe-ui` frames are window-relative; when a windowed sim gets into a state you can't undo, `simctl erase` it.
2. Look at every capture (Read the PNG; compose contact sheets with PIL). At least three render → look → fix passes.
3. Unit-test every layout decision; run the app's tests.
4. Ask a review workflow (haiku, high effort, finder + adversarial verifier per finding) to read the diff for regressions before shipping.

## Performance

- **Field data first.** Pull the installed app's logs from the device: `xcrun devicectl device copy from --device <id> --domain-type appDataContainer --domain-identifier <bundle> --source Library/Logs --destination <dir>` (works on TestFlight builds). Tailscode writes `stall ms=` lines (`MainStallMonitor`, main queue answering late) with the surrounding lines saying what the app was doing, `journey open/revealed/firstAnswer` timings, and MetricKit payloads in `Library/Logs/diagnostics/*.json` (crashes with the extension's bundle id, CPU and disk-write exceptions). Group stalls into bursts and read the lines before each.
- **Profile.** Simulator: `xcrun xctrace record --template 'Time Profiler' --device <sim udid> --attach <pid> --time-limit 40s --output x.trace` (the pid from `simctl launch`), then `xcrun xctrace export --input x.trace --xpath '/trace-toc/run[@number="1"]/data/table[@schema="time-profile"]'` and rank frames: rows carry `tagged-backtrace` with `frame` elements (`ref` attributes reuse earlier ids); main-thread samples are the stacks that contain `UIApplicationMain`. Build profiling binaries as Debug with `SWIFT_OPTIMIZATION_LEVEL=-O SWIFT_COMPILATION_MODE=wholemodule` so DEBUG hooks stay. Device: same `xctrace` with `--device <id>`, which needs a development-signed (get-task-allow) build.
- The Mac is usually loaded (load 50+), so simulator milliseconds are relative; an M1 iPad was ~2–3× slower than the simulator for the same carry.

## The apps' iPad layers

- **Tailscode** (`~/Dev/ios/Tailscode`, worktrees must sit at `~/Dev/ios/<name>` so `../../swift/CodingAgentKit` resolves): `WorkspaceSplitViewController` + `WorkspaceColumns` (Core: all three columns from 1280 pt, list beside from 940 / 820 when short-and-wide, else conversation alone) and `HandReach` (Core; `HandReach.read(for:)`, `primarySide`). DEBUG: `TAILSCODE_WINDOW=WxH` (turned a quarter when wider than the screen; under 680 pt gets compact), `TAILSCODE_REACH=leading|trailing`, `TAILSCODE_WORKSPACE_WALK=8:sidebar,…`, `TAILSCODE_OPEN_SESSION=demo-c3`, `--demo`, `TAILSCODE_BENCH_OPEN=300x1 TAILSCODE_BENCH_SCENARIO=resize`. Notes: `docs/agent-notes.md` ("The iPad is a workspace", "A tablet held sideways"). Parity capability `twoThumbReach`.
- **Flaccy** (`~/Dev/midgar/apps/flaccy`, never `~/Dev/ios/flaccy`): `App/Pad/`, `AdaptiveLayout` (column vs sidebar turns, `landscapeSplit`, side-by-side only when its cover beats the portrait cover), `RootContainerViewController`. DEBUG: `FLACCY_WINDOW_SIZE`, `FLACCY_SIDEBAR`, `FLACCY_ROUTE`, `FLACCY_COLUMN`, `FLACCY_HIDE_COLUMN_LATER`. Build with the release-candidate Xcode (`DEVELOPER_DIR=/Applications/Xcode-27.1.0-Release.Candidate.app/Contents/Developer`); the 27.3 beta fails its asset catalog.
- **Unrager** (`~/Dev/rust/unrager/ios`): `PadLayout`, `PadTabsController`, `PadReach`, `DetailDock`, `MasonryLayout` (seam layout after a resize), `ResizeTimer`. DEBUG: `UNRAGER_WINDOW_SIZE=WxH[@left|@right]`, `UNRAGER_SCREEN`, `UNRAGER_RESIZE_BENCH`, `UNRAGER_BENCH_DEPTH`; mock server `python3 demos/app/mock_server.py --long-feed 400 --page 400` on your own port. Not an App Store app: install with `ios/scripts/install-device.sh` (iPad Pro, iPhone Air) and the arch route for the mini.

## Shipping

Commit atomically, push, level the other machine. App Store apps get an internal TestFlight build only when Marcus asks (`app-store` skill; `midgar ship <slug> --platform ios --dir <worktree> --version X --build N --until upload` with the release-candidate Xcode, one archive at a time, tell the other sessions shipping the same app). Delete simulators, DerivedData, traces, archives and scratch captures.
