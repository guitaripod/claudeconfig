---
description: Boost a video's audio to maximum loudness without clipping — peak normalization or EBU R128 loudness leveling
---

Load the video-loud skill and run its full pipeline for "$ARGUMENTS". Measure true peak and integrated loudness, boost, re-encode audio to AAC with the correction loop so the encode lands under the ceiling, and verify — the video stream is copied untouched. Pick peak normalization when the ask is "as loud as possible before it clips", EBU R128 when it is "make the quiet parts loud too".
