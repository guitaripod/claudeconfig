# Camera on iPhone Duo

Load only when the app uses AVFoundation. Camera is the one area with **no system fallback** — on a single-display iPhone every rule here is a no-op, so all of it is `#available`-gated and must be tested on a Duo.

## The three cameras

An app that requests `.front` gets a new **Virtual Front Camera** that automatically switches between the two physical front cameras as the device opens and closes. It is capped at **1080p60** with the intersection of both cameras' capabilities, and **no depth**.

| Camera | Device type | Max video |
|---|---|---|
| Outer ultrawide | `.builtInOuterUltraWideCamera` | 4K120 |
| Inner ultrawide | `.builtInInnerUltraWideCamera` | 1080p60 |
| Virtual front | discovered via `.front` + `.ultraWide`/`.builtInUltraWideCamera` | 1080p60 |

The inner camera is behind the display and hidden until active; the outer camera is always visible in the corner. Depth requires addressing an individual camera.

**Decision:** the virtual front camera is the right default and costs one line. Drop to individual cameras only when the app needs 4K120 or depth — and then the app owns the switch.

## `position` is not direction

`AVCaptureDevice.position` has only ever been `back` / `front` / `unspecified`, and both front cameras report `.front`. On Duo, displays can face opposite directions, so a front camera is not always looking at the user: you can be viewing the inner display while streaming from the outer front camera.

Use **`AVCaptureDeviceDirectionCoordinator`** (AVKit, iOS 27.1). It takes the view showing your preview as its frame of reference and groups the cameras you capture from into forward-facing and backward-facing.

```swift
coordinator = AVCaptureDeviceDirectionCoordinator(
    view: previewView,
    deviceTypes: [
        .builtInOuterUltraWideCamera,
        .builtInInnerUltraWideCamera,
        .builtInDualWideCamera,
    ],
    changeHandler: { [weak self] map in
        self?.updateCameraSession(map)
    }
)
```

Rules:

- List **every** built-in camera the app captures from, including rear — a rear camera can face forward on Duo. External, Continuity Camera and Desk View cameras are ignored. The virtual front camera is excluded because the system moves it.
- Create and handle updates on the **main actor**. Hold a strong reference for as long as the view is onscreen.
- One coordinator per view. An app showing a preview on both displays creates two, and the same rear camera then comes back forward-facing from one and backward-facing from the other.
- The handler fires soon after creation with the starting configuration, then on every change. Before the first call, `deviceDirections` is empty.
- The handler receives `AVCaptureDeviceDirectionMap` with `forwardFacingDeviceDescriptors` and `backwardFacingDeviceDescriptors` — both `AVCaptureDeviceDescriptor`, a main-actor-safe, sendable representation. **Do not call AVFoundation from the handler**; hand the descriptor to the capture actor.

**Change handler:**

```swift
let forwardFacing = map.forwardFacingDeviceDescriptors
if let active = activeDescriptor, forwardFacing.contains(active) { return }
guard let replacement = forwardFacing.first else { return }
activeDescriptor = replacement
```

Compare the active camera against the forward-facing array rather than assuming it still points the right way. Reconfigure the session to keep streaming from a forward-facing camera, then update the UI.

## Mirroring

Decide mirroring from the direction map, not from `position`. When a rear camera faces forward, mirror the preview so the selfie looks natural; when a front camera faces backward, leave it unmirrored.

Set `automaticallyAdjustsVideoMirroring = false` **before** assigning `isVideoMirrored` — assigning while the connection adjusts mirroring itself raises an exception. Call it again after connecting a new device, because adding an input creates a preview connection that does not carry the override.

## Rotation and sensor compensation

Adopt the rotation coordinator so the preview and photos stay upright; on Duo it updates when the app moves displays. Then **disable camera-sensor-orientation compensation** — it is enabled on all of Duo's front cameras and costs performance once the rotation coordinator owns orientation:

```swift
photoOutput.isCameraSensorOrientationCompensationEnabled = false
```

## Preview layout

- Rear camera full field of view on the inner display leaves extra space around the preview. Either offset the preview and group controls in the remainder, or fill the display. Use `AVCaptureVideoPreviewLayer.videoGravity`.
- The square sensor lets you fill the display: `AVCaptureDevice.dynamicAspectRatio` selects a landscape aspect ratio on the inner display.

## Showing content on the outer display

`CameraCaptureAccessory` pairs UI on the outer display with the capture UI on the inner display — a teleprompter, or content for the person being photographed. Available when the app is full screen on the inner display with an active camera session, and it presents only while foregrounded.

SwiftUI:

```swift
CameraView()
    .sceneAccessory {
        CameraCaptureAccessory(isEnabled: $model.isEnabled) {
            TeleprompterView(model: model)
        }
        .onAvailabilityChange { model.isAvailable = $0 }
    }
```

UIKit: `UISceneAccessory.cameraCapture(sceneConfiguration:userInfo:)`, registered with `registerSceneAccessory(_:)`. Identify the accessory scene by comparing the session role against `UISceneSession.Role.windowCameraCaptureAccessory`. Share state via `UIScene.ConnectionOptions.sceneAccessoryUserInfo`.

Register the accessory on the **same view as the capture UI** so it is only present when the camera view is. Disable any control that toggles it while `isAvailable` is false — e.g. when the device is closed.

## Not available

The simulator cannot test any of this realistically — no camera hardware. Verify on a physical Duo. Given none is owned, mark camera work as requiring hardware and do not claim verification from the simulator.
