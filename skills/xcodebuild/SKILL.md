---
description: Build, test, and archive the A-LIST iOS app using xcodebuild
---

# xcodebuild - A-LIST iOS App

Build the A-LIST project for simulators and physical devices.

## Project

- **Project**: `A-LIST.xcodeproj`
- **Scheme**: `A-LIST`
- **Bundle ID**: `com.protocols.protocols`

## Known Devices

### Simulators

Discover available simulators:
```bash
xcrun simctl list devices available | grep -i "iphone\|ipad"
```

Common simulators (IDs change per machine — always verify with the command above):
- **iPhone Air**: check `xcrun simctl list devices available | grep "iPhone Air"`
- **iPhone 16**: check `xcrun simctl list devices available | grep "iPhone 16 ("`

### Physical Devices

Discover connected physical devices:
```bash
xcrun xctrace list devices 2>&1 | grep -i "iphone"
```

This returns lines like: `Device Name (OS version) (DEVICE_ID)`

## Build Commands

### Build for Simulator

```bash
xcodebuild -project A-LIST.xcodeproj -scheme A-LIST \
  -destination 'platform=iOS Simulator,id=<SIMULATOR_UDID>' \
  build 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

### Build for Physical Device

```bash
xcodebuild -project A-LIST.xcodeproj -scheme A-LIST \
  -destination 'platform=iOS,id=<DEVICE_UDID>' \
  build 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

### Build for Both (Sequential Only)

Never build for two destinations in parallel — they share DerivedData and the build DB will deadlock. Always build sequentially:

```bash
# Build sim first
xcodebuild -project A-LIST.xcodeproj -scheme A-LIST \
  -destination 'platform=iOS Simulator,id=<SIM_UDID>' build 2>&1 | \
  grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"

# Then physical device
xcodebuild -project A-LIST.xcodeproj -scheme A-LIST \
  -destination 'platform=iOS,id=<DEVICE_UDID>' build 2>&1 | \
  grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

## Install & Launch

### Simulator

```bash
xcrun simctl install <SIM_UDID> \
  ~/Library/Developer/Xcode/DerivedData/A-LIST-*/Build/Products/Debug-iphonesimulator/A-LIST.app

xcrun simctl launch <SIM_UDID> com.protocols.protocols
```

Boot the simulator first if it's shut down:
```bash
xcrun simctl boot <SIM_UDID>
```

### Physical Device

```bash
xcrun devicectl device install app \
  --device <DEVICE_UDID> \
  ~/Library/Developer/Xcode/DerivedData/A-LIST-*/Build/Products/Debug-iphoneos/A-LIST.app

xcrun devicectl device process launch \
  --device <DEVICE_UDID> com.protocols.protocols
```

## Locked Build DB

If you get `database is locked`, Xcode or a previous xcodebuild is holding it. Fix:

```bash
pkill -9 -f xcodebuild 2>/dev/null
pkill -9 -f XCBBuildService 2>/dev/null
sleep 1
```

Then verify no process holds the lock:
```bash
lsof ~/Library/Developer/Xcode/DerivedData/A-LIST-*/Build/Intermediates.noindex/XCBuildData/build.db 2>/dev/null
```

If Xcode itself is open and building, the user must close Xcode first or build from Xcode instead.

## Important Rules

- Always discover device IDs dynamically — never hardcode UDIDs
- Build sequentially when targeting multiple destinations
- Use `grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"` to filter output
- Use `timeout` of 300000ms for build commands (builds take 25-170s)
- The DerivedData path glob is: `~/Library/Developer/Xcode/DerivedData/A-LIST-*/Build/Products/`
