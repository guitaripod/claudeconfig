---
description: Reliably pull iOS app logs from a physical device via devicectl. Use this whenever `log stream` / `log show` / `idevicesyslog` aren't working (common on iOS 17+ / 26) and the app writes to a file-based logger inside its sandbox.
---

# iOS Device Logs

The reliable way to get logs out of a physical iPhone/iPad for an app you're actively debugging.

## When to use this

Reach for this the moment any of these are true:

- `log stream` / `log show` over paired device returns nothing, silently exits, or is privacy-filtered to uselessness
- `idevicesyslog` is broken (it's been unreliable since iOS 17 and returns nothing on iOS 26)
- `xcrun devicectl device process launch --console` shows no app output (it only streams stdout/stderr, not `os_log`)
- Xcode isn't attached and you don't want it to be
- The user is testing on their daily-driver device and can't tether the whole debug session

What you need: the app must write a log file to somewhere inside its own sandbox container (commonly `tmp/` or `Library/Caches/`). Most well-instrumented apps already have this as a companion to their `os.log` wrapper — look for a `LogFileWriter`, `FileLogger`, or similar.

## Core technique

`xcrun devicectl device copy from` reads files out of any app's sandbox container over the paired USB/Wi-Fi connection. No Xcode, no `log stream`, no crash-report round-trip.

```bash
xcrun devicectl device copy from \
  --device <DEVICE_UDID> \
  --domain-type appDataContainer \
  --domain-identifier <BUNDLE_ID> \
  --source "<path-inside-sandbox>" \
  --destination <local-path>
```

Where:

- `<DEVICE_UDID>` — find via `xcrun devicectl list devices`
- `<BUNDLE_ID>` — the app's bundle identifier, e.g. `com.example.myapp`
- `<path-inside-sandbox>` — path relative to the container root. `tmp/foo.log` means `<container>/tmp/foo.log`. No leading slash.
- `<local-path>` — where to write the copy on your machine

Domain types for other use cases:

| Use                             | `--domain-type`        | Notes                                                                 |
| ------------------------------- | ---------------------- | --------------------------------------------------------------------- |
| App's sandbox (Documents, tmp)  | `appDataContainer`     | Needs `--domain-identifier <BUNDLE_ID>`                               |
| App Group shared container      | `appGroupDataContainer`| Needs `--domain-identifier <GROUP_ID>`                                |
| System crash reports (`.ips`)   | `systemCrashLogs`      | `--source "/"` pulls the directory; grep for your bundle ID           |
| Temporary client-private space  | `temporary`            | `--domain-identifier <any-string>`                                    |

## Making the log file actually up-to-date

`FileHandle.write(_:)` in Swift buffers in userspace — data isn't necessarily on disk by the time `devicectl copy from` runs. To guarantee freshness, the app should call `synchronize()` (or `fsync`) after each write at the log levels you care about.

Recommended pattern in the app's logger:

```swift
func write(level: LogLevel, line: String) {
    queue.async { [self] in
        fileHandle.write(Data(line.utf8))
        if level == .info || level == .error || level == .fault {
            try? fileHandle.synchronize()   // flush to disk immediately
        }
    }
}
```

Only `synchronize()` the levels you need immediately. `.debug` / `.trace` can skip the sync to avoid IO pressure from chatty loops.

If the app you're debugging doesn't `synchronize()` on write, your pulled log will be missing the most recent few hundred ms of entries. The fix is to edit the logger to sync on the important levels — a one-line change you'll want anyway.

## Workflow (active debugging on a physical device)

1. **Know the app's log path.** Grep its source for the file extension or logger class (`.log`, `LogFileWriter`, `FileLogger`). Note the full path inside the sandbox.
2. **Make sure it syncs.** If `.info`/`.error` lines aren't reaching the pulled file, add `try? fileHandle.synchronize()` after writes for those levels.
3. **Add rich breadcrumbs** at the decision points relevant to the bug — state transitions, branch decisions, error codes, IDs. `.info` is usually the right level for device debugging because that's what ships to crash/Shake-style reporters and what the user sees from this transport.
4. **Build & install** via your normal `xcodebuild` + `devicectl install` flow. Always terminate the existing process first (`devicectl device process terminate --device <UDID> --app <BUNDLE_ID>`), otherwise the install can leave a ghost process holding the old log handle.
5. **Guide the user** ("open screen X, tap Y, wait 5 seconds"). Don't poll — let the user tell you when to pull.
6. **Pull + grep** in one line:
   ```bash
   xcrun devicectl device copy from \
     --device <DEVICE_UDID> \
     --domain-type appDataContainer \
     --domain-identifier <BUNDLE_ID> \
     --source "tmp/<log-file>" \
     --destination /tmp/<log-file> 2>&1 | tail -1 \
     && grep -Ei "<keyword>" /tmp/<log-file> | tail -40
   ```
7. **Iterate** — adjust log placement based on findings, rebuild, re-test. Strip temporary `.debug`/`.trace` probes before merging; `.info`/`.error`/`.fault` are meant to ship.

**CRITICAL: always pull BEFORE you install.** Installing a new build relaunches the app, which rotates the current log to `*-previous.log` and starts a fresh file with only startup lines. If the user just reproduced a bug and you install before pulling, the reproduction evidence is pushed to `*-previous.log` — and if you install *twice* (e.g. a fix attempt that doesn't build), it's gone entirely. The correct loop is:

```
user reproduces → PULL LOG → analyze → add/adjust logs → build → install → user reproduces → PULL LOG → ...
```

Never `build → install → pull`. The install is what destroys the evidence.

Pulling is cheap and non-destructive (it's just a file copy). Pull as many times as you want — there's no lock, no cooldown, no side effect on the device. If in doubt, pull.

## Pulling crash reports

When the app crashes, there's usually no log entry to find. Pull the `.ips` crash report instead:

```bash
mkdir -p /tmp/crashlogs && xcrun devicectl device copy from \
  --device <DEVICE_UDID> \
  --domain-type systemCrashLogs \
  --source "/" \
  --destination /tmp/crashlogs

ls /tmp/crashlogs | grep -i <app-name> | tail -3
head -c 8000 /tmp/crashlogs/<App>-<timestamp>.ips
```

The `.ips` file is JSON with a symbolicated `lastExceptionBacktrace` array at the top — that's the Swift frame that threw, and usually all you need to localize the bug.

## Session rotation and the "empty log" trap

Many logger implementations rotate on app launch: the current session's file is renamed to e.g. `foo-previous.log` and a fresh `foo.log` begins. This is the single most common source of "I pulled the log and it only has 12 lines of startup — where's my data?"

The answer is almost always: you installed a new build between the user's reproduction and your pull. The install relaunched the app, which rotated the reproduction session into `*-previous.log` and started a blank file.

**If you pull and see only startup lines:**
1. Pull `*-previous.log` — your data is probably there
2. If `*-previous.log` also looks wrong, you may have installed twice (two rotations), and the reproduction is gone — ask the user to reproduce again

**If the app crashed**, the crashed session's log is in `*-previous.log` the *next* time the app starts. Pull it on the next launch.

```bash
xcrun devicectl device copy from ... --source "tmp/foo-previous.log" --destination /tmp/foo-previous.log
```

## What NOT to use on physical devices

- `idevicesyslog` — broken for iOS 17+ and iOS 26 devices; returns nothing or dies
- `xcrun devicectl device process launch --console` — does not stream `os_log`, only stdout/stderr
- `log stream` / `log show` via paired-device sysdiagnose — unreliable, privacy-filtered, often empty
- Pasting `Console.app` output back into chat — the privacy redaction destroys payloads you need

## Debugging the transport itself

If `devicectl copy from` is silent or errors:

- `xcrun devicectl list devices` — confirm the device is paired and awake
- Unlock the device — sandbox access requires the device be unlocked
- Check the bundle ID matches exactly (`com.example.app` vs `com.example.app.dev` bite)
- Check the source path — it's relative to the container root, no leading `/`, and case-sensitive
- Trust relationship — if the device was recently reset, you may need to re-trust the host
