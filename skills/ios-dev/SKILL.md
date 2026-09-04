---
name: ios-dev
description: Working in Marcus's iOS/macOS app projects (Xcode, xcodegen project.yml, SwiftUI, xtool on Linux) - the mandatory file-based logger pattern, running on his iPhone Air, manual code signing via the App Store Connect API, building/installing/launching from Linux with xtool and pymobiledevice3, and diagnosing Sign in with Apple failures. Load for any build, run-on-device, signing, logging or auth-debugging task in an app project.
---

# iOS app development

## Logger from day one
Every mobile app persists its own diagnostics, because an agent cannot attach Xcode or Console to a phone. Pattern (reference `~/Dev/ios/golf-coach/golf-coach/Utilities/{AppLogger,LogFileWriter}.swift`, mirrored into psywave): `LogFileWriter` (append-only, size-rotated current+previous file in `Library/Logs/<app>.log`, writes serialized on a utility queue) behind an `AppLogger` facade that fans every call to OSLog **and** the file, with app-specific categories (lifecycle, generation, network, persistence, …). Route real diagnostic points (generation/import errors, lookup failures, SwiftData saves, launch) through it, never `print`/`NSLog`. Add it to any app that lacks it.

## Device: iPhone Air
devicectl name "iPhone Air", identifier `0A19DF7B-F393-5AA6-AD32-F997CC562974`, hostname `iPhone-Air.coredevice.local`. Not a simulator, not the iPhone XS, unless told. Simulator only if the Air is unreachable, and say so.

## From the Mac: manual signing + devicectl
Automatic signing usually has no Xcode account configured. Sign manually via the ASC API: match a keychain `Apple Development` cert by SHA-1, register the device UDID, mint an `IOS_APP_DEVELOPMENT` profile for the bundle (inherits capabilities such as Sign in with Apple), and scope `CODE_SIGN_IDENTITY[sdk=iphoneos*]` + `PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]` to the app target's config only (global xcodebuild overrides break SPM targets like RevenueCat/Lottie). Install + launch with `devicectl`. Pull the app's log with the `ios-device-logs` skill.

## From Linux (Arch): xtool + pymobiledevice3
- `xtool` needs the Swift runtime on the library path or it dies on `libswiftCore.so`: `export LD_LIBRARY_PATH=$(ls -d ~/.local/share/swiftly/toolchains/*/usr/lib/swift/linux | tail -1):$LD_LIBRARY_PATH` before any `xtool devices/dev/launch/install`.
- Check `idevice_id -l` first: `xtool devices` and `xtool dev` hang on "Waiting for device to be connected..." with nothing attached.
- `xtool dev` builds + signs + installs only; launch separately with `xtool launch <XTL-id>`. xtool rewrites the bundle id on device to `XTL-<HASH>.<original.bundle.id>`, `<HASH>` being the uppercased first 8 chars of `~/.config/xtool/data/XTLLocalUserUID`; the plain id fails with "Could not find an installed app". `DebugserverClient.Error.unknown` after "Launching <App>..." is benign (debug attach failed, the app launched, exit code may be 1).
- Most libimobiledevice CLIs are absent (`ideviceinstaller`, `idevicesyslog`, `devicectl`). Use `pymobiledevice3` from a venv (`python3 -m venv /tmp/pmd-venv && /tmp/pmd-venv/bin/pip install pymobiledevice3`; Arch blocks bare `pip install`): `apps list` (JSON keyed by bundle id, find the XTL-prefixed one), `apps pull XTL-<HASH>.<id> Library/Logs/<app>.log /tmp/x.log` (path relative to the data container root; `--documents` only for the Documents subdir), `apps afc/push/rm`.
- xtool builds app extensions, including WidgetKit and ActivityKit Live Activities: a second `.library` product+target for the widget plus a shared `.library` target for the `ActivityAttributes` (the widget cannot depend on the app target: `@main` collision); `xtool.yml` gets `product: <App>` + `extensions: [{product: <Widget>, infoPath: <Widget>-Info.plist}]`; widget Info.plist `NSExtension.NSExtensionPointIdentifier = com.apple.widgetkit-extension`; app Info.plist `NSSupportsLiveActivities = true`; guard widget code with `#if os(iOS) && canImport(ActivityKit)`. ExtensionKit (`EXAppExtensionAttributes`) is unsupported (xtool #138). Background downloads need no extension: background `URLSession` or `BGProcessingTaskRequest` (register in `didFinishLaunchingWithOptions`, list the id in `BGTaskSchedulerPermittedIdentifiers`) plus local notifications.
- xtool signs only the root app's entitlements (xtool #131), so App Groups between app and extension do not work: `containerURL(forSecurityApplicationGroupIdentifier:)` is nil in the extension. Render widgets and Live Activities from `ContentState` text and numbers with an SF Symbol or bundled asset for imagery; write the App-Group plumbing nil-safe so it auto-enables if #131 is fixed, never promise artwork.

## Sign in with Apple failures
Verify the three layers first: entitlement, App ID `APPLE_ID_AUTH` primary-app-consent capability, profile minted after the capability. Then read `idevicesyslog` for `akd`/`AppleIDAuthSupport`/`AuthKit`:
- `SRP authentication … M2 missing (bad password)` / `AKAuthenticationServerError -24000`: stale Apple ID password on the device, not the app, entitlement or profile.
- `AKAuthenticationError -7003` (app sees `ASAuthorizationError 1001` "Sign Up Not Completed") with every local layer correct, often alongside `AKSQLError -6003` "fetching developer team": a stale App ID registration on Apple's auth server. Fix: developer.apple.com → Identifiers → the App ID → Sign in with Apple → toggle OFF, Save, ON, Save. Works immediately, no rebuild or profile re-mint. Repeat per App ID.
