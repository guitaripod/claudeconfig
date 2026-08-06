---
description: Reliably pull iOS app logs from a physical device via devicectl, including from the app's file-based logger in its sandbox
---

Load the ios-device-logs skill and use it for "$ARGUMENTS". Pull the app's logs from the physical device, preferring the file-based logger inside the app sandbox when `log stream` / `log show` / `idevicesyslog` aren't working.
