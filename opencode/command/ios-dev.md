---
description: Work in Marcus's iOS/macOS app projects — logger pattern, runs on the iPhone Air, xtool builds from Linux, signing, SIWA debugging
---

Load the ios-dev skill and follow it for "$ARGUMENTS". Keep the mandatory file-based logger (AppLogger + LogFileWriter) in place, run on the iPhone Air (`devicectl` name "iPhone Air", id `0A19DF7B-F393-5AA6-AD32-F997CC562974`) and never a simulator, and use xtool + pymobiledevice3 for builds, installs and manual signing from Linux.
