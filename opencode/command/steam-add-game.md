---
description: Install a DRM-free/scene PC game from an archive set and integrate it fully into Steam on Linux — release triage, extract, wine install, non-Steam shortcut, artwork, verified launch
---

Load the steam-add-game skill and run its full workflow for "$ARGUMENTS". Triage the release type first (scene release vs repack — repacks are a dead end on this box, say so and stop), then execute the phases in order: identify + extract, install under wine, add the non-Steam shortcut with the right Proton + launch-option profile, fetch SteamGridDB artwork and the multi-res icon, then launch and verify the process is actually alive. Use the skill's `scripts/` helpers; every mutating command needs `--apply`.
