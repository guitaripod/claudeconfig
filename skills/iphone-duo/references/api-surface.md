# iPhone Duo API surface

Version tags are the SDK the symbol appears in, not the deployment target. Every Duo symbol needs `#available(iOS 27.1, *)` unless the app's deployment target is already 27.1. Apple's docs pages list only iOS/iPadOS 27.1, but the SDK headers annotate tvOS and visionOS 27.1 as well — gate on iOS/iPadOS and let the compiler report the rest.

**Compile-time gating:** Xcode 27.0 and 27.1 ship the same Swift 6.4, so `compiler(>=6.4)` cannot distinguish them. Use `canImport(SwiftUI, _version: 8.0.85)` or `canImport(UIKit, _version: 9127.0.85)`. Runtime gating is `#available(iOS 27.1, *)`.

---

## Reserved regions

Regions of your view's coordinate space that hardware or the system reserves. Query them; do not compute them.

| SwiftUI | UIKit | Notes |
|---|---|---|
| `GeometryProxy.reservedRegions(kind:options:layoutDirectionBehavior:)` | `UIView.reservedRegions(kind:options:)` | Returns regions that **intersect** your view, active or not |
| `ReservedRegion` | `UIView.ReservedRegion` | — |
| `.frame`, `.margins`, `.isActive`, `.kind`, `.id` | same | `frame` **already includes** margins |
| `ReservedRegion.Kind` | `UIView.ReservedRegion.Kind` | `.division` (the fold), `.occlusion` (cameras) |
| `ReservedRegion.QueryOptions.includeInactive` | `UIView.ReservedRegion.QueryOptions` | Default returns only active |
| `LayoutDirectionBehavior.fixed` | — | Regions are mirrored for RTL by default; pass `.fixed` for physical positions |

[SwiftUI](https://developer.apple.com/documentation/swiftui/reservedregion) · [UIKit](https://developer.apple.com/documentation/uikit/uiview/reservedregion)

Division is active only while partially folded — flat it is inactive with a zero-width fold line. The inner camera is an occlusion region, active only while the camera is active. Arrive after the first layout pass; never cache.

## Arrangements

A container that holds a primary and a secondary view and lays them out from the environment — size, size class, and hardware features. Choose by the relationship you already have: an `HStack`/`VStack` becomes `.split`, a `ZStack` becomes `.overlay`.

| SwiftUI | UIKit | Version |
|---|---|---|
| `ArrangementView` | `UIArrangementViewController` | 27.1 |
| `View.arrangementViewStyle(_:)` | `updateArrangement(_:animated:)` | 27.1 |
| `.split`, `.overlay`, `.automatic` (defaults to split) | `UISplitArrangement`, `UIOverlayArrangement` | 27.1 |
| `SplitArrangementViewStyle.axes(_:)` | `UISplitArrangement.axes(_:)` | 27.1 |
| `OverlayArrangementViewStyle.axes(_:)` | `UIOverlayArrangement.axes(_:)` | 27.1 |
| `splitArrangementLayoutRatio(_:)` | — | 27.1 |
| `splitArrangementLayoutRatio(minHorizontal:idealHorizontal:maxHorizontal:…)` | — | 27.1 |
| `splitArrangementLayoutSize(minWidth:idealWidth:maxWidth:…)` | — | 27.1 |
| `splitArrangementFixedLayoutSize(horizontal:vertical:)` | — | 27.1 |
| `overlayArrangementEdge(_:)` | — | 27.1 |
| `EnvironmentValues.overlayArrangementZIndex` | `state(for:)` → `ViewState.zIndex` | 27.1 |
| `ArrangementViewStyle` protocol | `UIArrangementViewController.Arrangement` | 27.1 |

`UIArrangementViewController` also exposes `ViewPlacement`, `ViewState` (`.isHidden`, `.splitAxis`, `.zIndex`), `setViewController(_:for:animated:)`, `viewController(for:)`, `placement(for:)`.

[SwiftUI](https://developer.apple.com/documentation/swiftui/arrangementview) · [UIKit](https://developer.apple.com/documentation/uikit/uiarrangementviewcontroller)

**Do not** put a navigation container inside an arrangement, or an arrangement inside a `List`/`ScrollView`. Navigation goes *around* it.

## Vertical bars

Bars move to a side edge on the outer display and on the inner display in landscape. Horizontal only in the inner display's tall layout, and in inspectors and split-view sidebar/content columns.

| SwiftUI | UIKit | Version |
|---|---|---|
| `EnvironmentValues.toolbarVerticalEdge` | `UITraitCollection.verticalBarEdge` → `UIVerticalBarEdge` (`.leading`/`.trailing`/`unspecified`) | 27.1 |
| `View.toolbarVerticalBehavior(_:)` | `UIViewController.preferredVerticalBarBehavior` | 27.1 |
| `View.toolbarVerticalCompressionBehavior(_:)` | `UINavigationItem.verticalBarCompressionBehavior` | 27.1 |
| `ToolbarVerticalCompressionBehavior` (`.automatic`, `.prefersTabBar`, `.prefersToolbarItems`) | `UIVerticalBarCompressionBehavior` (`.automatic`, `.prefersTabBar`, `.prefersBarItems`) | 27.1 |
| `ToolbarContent.axisBehavior(_:)` (`.verticalPreferred`, `.horizontalOnly`) | `UIBarButtonItem.axisBehavior` | 27.1 |
| `ToolbarContent.visibilityPriority(_:)` | `UIBarButtonItem.visibilityPriority` | SwiftUI 27.1 / UIKit 27.0 |
| `ToolbarItemVisibilityPriority` (`.low`, `.high`, `.automatic`, `init(lowerThan:)`, `init(higherThan:)`) | `UIBarButtonItemVisibilityPriority` | — |
| `ToolbarItemPlacement.topBarPinnedTrailing` | `UINavigationItem.pinnedTrailingGroup` | 27.0 |
| `ToolbarItemPlacement.cancellationAction` | `UINavigationItem.leadingItemGroups` | 27.0 |
| `ToolbarOverflowMenu` | `UINavigationItem.additionalOverflowItems` | 27.1 |
| `View.presentationPlacement(_:)` | `UISheetPresentationController.preferredPlacement` | 27.0 |

`verticalBarEdge` resolves `leading`/`trailing` (follows layout direction) while `safeAreaInsets` uses physical edges. `unspecified` is ambiguous — it covers both "no bar possible" and "bar allowed but edge unresolved". Read the inset when you need the size.

Only bars owned by a navigation container go vertical. A bare `UIToolbar`, `UINavigationBar`, `UITabBar`, or a SwiftUI `HStack` of buttons does not.

## Hinge

| SwiftUI | UIKit | Version |
|---|---|---|
| `View.onHingeChange(isEnabled:_:)` | `UIHingeInteraction` | 27.1 |
| `DeviceHingeContext.hinge` | `UIHingeInteraction` | 27.1 |
| `DeviceHinge.angle` (`Angle`, 180° flat) | same | 27.1 |
| `DeviceHinge.status` (`.closed`, `.partiallyOpen`, `.fullyOpen`) | same | 27.1 |

`hinge` is `nil` on devices without one — check rather than assume. Effects and interaction only; layout comes from reserved regions and arrangements.

## Scenes and multiple displays

| SwiftUI | UIKit | Version |
|---|---|---|
| `View.sceneAccessory(content:)` | `UIViewController.registerSceneAccessory(_:)` / `unregisterSceneAccessory(_:)` | 27.1 |
| `CameraCaptureAccessory` | `UISceneAccessory.cameraCapture(sceneConfiguration:userInfo:)` | 27.1 |
| `SceneAccessoryContent.onAvailabilityChange(perform:)` | observation tracking | 27.1 |
| — | `UISceneAccessoryRegistration` | 27.1 |
| — | `UISceneSession.Role.windowCameraCaptureAccessory` | 27.1 |
| — | `UIScene.ConnectionOptions.sceneAccessoryUserInfo` | 27.1 |
| `UIWindowSceneActivation` | same | — |

All apps participate in Split View multitasking. New windows can only be created on the inner display, and availability is dynamic — handle the activation error. `UIWindowSceneActivation` hides itself when window creation is unavailable.

## Container margins

| SwiftUI | UIKit | Version |
|---|---|---|
| `View.contentMargins(for:)` | `view.directionalLayoutMargins` / `systemMinimumLayoutMargins` | 27.1 |
| `GeometryProxy.contentMargins(for:)` | — | 27.1 |

`.container` is the variant to use. Relevant because of the iOS 27.1 change where a `UIView`'s default layout margins became zero — see `audit-rules.md` tier 2.

## Camera

Full detail in `camera.md`. Summary: two physical front cameras, a **Virtual Front Camera** that follows the app across displays, and `AVCaptureDeviceDirectionCoordinator` to learn which way each camera faces.

| Symbol | Version |
|---|---|
| `AVCaptureDevice.DeviceType.builtInOuterUltraWideCamera` | 27.1 |
| `AVCaptureDevice.DeviceType.builtInInnerUltraWideCamera` | 27.1 |
| `AVCaptureDevice.isVirtualDevice`, `.activePrimaryConstituent` | 27.1 |
| `AVCaptureDevice.dynamicAspectRatio` | 27.1 |
| `AVKit.AVCaptureDeviceDirectionCoordinator` | 27.1 |
| `AVCaptureDeviceDescriptor`, `AVCaptureDeviceDirectionMap` | 27.1 |
| `AVCaptureConnection.automaticallyAdjustsVideoMirroring`, `.isVideoMirrored` | — |
| `AVCapturePhotoOutput.isCameraSensorOrientationCompensationEnabled` | — |

## Concentricity and corners

From iOS 26, called out in the Duo Tech Talk because the screen shapes are new.

| SwiftUI | UIKit | Version |
|---|---|---|
| `ConcentricRectangle` | `UICornerConfiguration` | 26 |
| `GeometryProxy.concentricCornerRadii`, `concentricCornerRadii(in:)` | — | 27 |
| `UIView.layoutGuide(for: .safeArea(cornerAdaptation: .horizontal))` | — | 26 |
| `UIView.directionalEdgeInsets(for: .safeArea(cornerAdaptation:))` | — | 26 |

## Adjacent APIs the Duo work depends on

- `View.backgroundExtensionEffect()` / `UIBackgroundExtensionView` (iOS 26) — fills the gutter under a vertical bar with mirrored, blurred content instead of a hard edge.
- `.defaultTabBarPlacement(.sidebar)` / `UITabBarController.sidebar.preferredPlacement` (iOS 27) — a sidebar on the inner display. Check `sidebar.isAvailable`.
- `UINavigationItem.navigationBarMinimization` (iOS 27) — replaces `barMinimizeBehavior` / `barMinimizationSafeAreaAdjustment`.
- `UIView.updateProperties()` — the UIKit trait-tracking entry point; automatic trait tracking re-runs it on size-class change.
- `UIView.registerForTraitChanges(_:)` with `UITraitCollection.systemTraitsAffectingVerticalBarEdge`.

## Not available

No Stage Manager on Duo (`DeviceSupportsEnhancedMultitasking` is false). No Slide Over — do not write or test for it; no Apple source documents it. `splitArrangementAxis` reads `nil` in every simulator configuration tested.
