# Every iPhone Duo state, and what excellent looks like in each

Apple's wording throughout; "(inferred)" marks a deduction, not a quote. Sources: HIG [Designing for iPhone Duo](https://developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo), [Preparing your app](https://developer.apple.com/documentation/technologyoverviews/preparing-your-app-for-iphone-duo), Tech Talks 111461 to 111466 (prepare, bars, poses, displays and scenes, camera, design). The goal is not "does not break" but "uses what this state offers".

Contents: [State space](#state-space) · [Excellent per state](#excellent-per-state) · [Use-case patterns](#use-case-patterns) · [Optimisation questions](#optimisation-questions) · [Gaps](#gaps)

## State space

A shipped app has to be right in every row. `Scripted` says whether `scripts/capture.py` reaches it.

| State | Apple's name and facts | Scripted |
|---|---|---|
| Outer display, portrait | 5.4", 466 × 678 pt, compact × regular, bar on the side, camera in the corner | yes `outer-portrait` |
| Outer display, landscape | "people may want to set the phone down like a tent"; compact × compact. The outer display honours supported orientations | yes `outer-landscape` |
| Inner display, landscape | 7.6", 951 × 669 pt, regular × regular, landscape-native, bar on the side | yes `inner-landscape` |
| Inner display, portrait | 669 × 951 pt, horizontal bars. The inner display ignores supported orientations | yes `inner-portrait` |
| Book | partially folded "like a book"; vertical fold through the centre of the landscape inner display | yes `book-landscape` (127°) |
| Laptop | "seated on a table like a laptop"; horizontal fold in the portrait inner display. Apple's talks say top region and bottom region; no Apple page says "tabletop" | yes `laptop-portrait` (127°) |
| Tent, standing on edges | Apple names them; no layout rules beyond supporting landscape (StandBy applies when standing) | partly: outer landscape |
| Any angle between | `onHingeChange` / `UIHingeInteraction`: status `closed` / `partiallyOpen` / `fullyOpen` plus the angle | `duoctl hinge N` |
| Split View | 50/50, each half has its bar on its outer edge; insets differ per side | no: drag the home indicator |
| Picture in Picture | video pinned at the top; the app shrinks vertically in real time; half-screen video when partially folded | no |
| Multiple windows | only on the inner display; creating one can fail | no |
| Keyboard up | sizes differ per pose (measured 230 to 350 pt tall); accessory bars stay attached to the keyboard | partly: `duoctl tap` a field |
| Inner camera active | an occlusion region while the camera runs | no: needs a device |
| Camera capture accessory | UI on the outer display while the app is full screen on the inner display with a camera session | no: needs a device |
| Dynamic Island, status column | the camera region expands vertically alongside bars; Live Activities need every presentation | no |
| Dark mode, Dynamic Type, locale | multiplies every row above | yes `--appearance`, `--arg` |

## Excellent per state

| State | The system gives you | Excellent means |
|---|---|---|
| Outer | Compact layout, vertical bar | Same state and functionality as the inner display; single-pane navigation; landscape supported as well as portrait; controls reachable on the bar side. A portrait-only iPhone app is skipped in `outer-landscape`: Apple asks for landscape, so decide on purpose |
| Inner, landscape | Regular width, vertical bar | "A natural extension of its iPad layout", not "a stretched out iPhone app": split view, a sidebar tab bar (Health), a two-column rearrangement (Music), or `ArrangementView`. Do not gate on idiom |
| Inner, portrait | Regular × regular, horizontal bars | Same hierarchy as the other poses; use the height, not extra width |
| Book | Content moves off the fold: text, images, controls, sheets, alerts, menus and toolbar buttons nudge aside; split views rebalance 50/50 | Even column counts so nothing straddles the fold; each half self-sufficient; alerts land trailing; scrolling content may cross the fold, controls may not |
| Laptop | Interactive elements move to the lower half; PiP takes half | Optional special layout: media in the top region, "tappable controls live on a stable base at the bottom"; alerts in the top region; **never tie functionality to a pose**, keep the same controls and hierarchy |
| Partial angle | Nothing automatic | Effects only (a pitch-bend, a parallax). No layout from the angle; no assumption of update rate; smooth with a spring |
| Split View | Standard bars adapt | Each half correct on its own edge; asymmetric insets handled independently; compact behaviour in 469 pt halves |
| PiP | Resizes the window | Layout survives any video height; bars overflow cleanly |
| Keyboard | Bottom-pinned controls move | Use `keyboardLayoutGuide`; the field stays visible in every pose |
| Camera | Virtual front camera follows the user | Start with the virtual camera; individual cameras plus `AVCaptureDeviceDirectionCoordinator` when capture is the product; preview offset or filled via `dynamicAspectRatio`; outer-display accessory for a teleprompter or a subject preview (`references/camera.md`) |
| Games | A full-screen scene | Playable in every pose; "prefer changing the aspect ratio over letterboxing or pillarboxing"; consistent text and control sizes |

Standing rules from Apple: prefer standard containers (split views, tab bars, arrangement views, navigation stacks); size relative to the container; "avoid extreme layout changes… favor small adjustments"; "in a grid-style layout, prefer an even number of columns"; "avoid assuming that insets on opposite sides are equal"; do not write device-specific behaviour (there is no API to detect a Duo, and Apple staff say all apps are expected to be fully adaptive, iPhone-only ones included).

## Use-case patterns

| App type | Inner display | Laptop / book |
|---|---|---|
| Lists and records (inventory, notes, mail) | `UISplitViewController` / `NavigationSplitView`: list and detail side by side, collapse to a stack on the outer display | Detail beside list in book; list top, detail bottom in laptop (arrangement `.split`) |
| Media and playback | Player and transcript or queue as a split arrangement | Media in the top region, controls and queue in the bottom region |
| Reading and documents | Reader with controls overlaid (`.overlay`), or document plus outline | Scrolling text may cross the fold; controls move to a half |
| Camera and capture | Preview offset or filled, controls grouped in the spare space | Outer-display accessory for the subject |
| Games | Fill the screen in every pose; aspect ratio over letterboxing | Controls on the stable half |
| Forms and settings | Centred readable column, not full width | Fields in one half, keyboard in the other |
| Dashboards and grids | Even column counts; more columns, not bigger tiles | Cells sized so none sits on the fold |

## Optimisation questions

Answer each in writing for every screen before editing; a "no change needed" with a reason is a valid answer.

1. **Inner landscape:** is this a phone layout at 951 pt? What would the iPad layout be (split, sidebar, columns, arrangement)?
2. **Grids and rows:** is the column count even in book pose? Is any control or key piece of text on the fold?
3. **Outer:** does it work in landscape? If the app is portrait-only, is that a decision or an omission?
4. **Laptop:** is there a media-or-content and controls split worth making, without removing anything?
5. **Split View halves:** is the 469 pt half usable, and is the bar on either edge handled?
6. **PiP and keyboard:** does the screen survive being 200 pt shorter?
7. **Modals:** sheets, alerts and menus: do they use system presentation so they displace by themselves?
8. **Media:** fill or fit chosen from the aspect ratio, not hard-coded?

## Gaps

- No Apple page defines "optimized for iPhone Duo" or a numbered pose set. The App Store Connect featuring nomination takes a free-text "Helpful Details" field where you can state support for all poses (Apple's [prepare steps](https://developer.apple.com/iphone-duo/prepare/)). A DTS engineer declined to say whether a badge exists.
- Tent, StandBy, external display, always-on and Maps have no Apple layout guidance.
- Whether the Duo screenshot slots show per pose is unspecified: the slots are by display and orientation only, so the pose story is told inside them (`references/capture.md`).
