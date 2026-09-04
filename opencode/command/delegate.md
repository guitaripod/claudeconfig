---
description: Run the delegate tool with a packet path or explicit class/goal/paths/verify parsed from the arguments
---

The user wrote a packet in "$ARGUMENTS" — either a path to a packet YAML file, or free text like "class: <c>, goal: <g>, paths: <p>, verify: <v>". Call the `delegate` tool with exactly those values (`packet` set to the path if one was given, otherwise `class`/`goal`/`paths`/`verify`/`read`/`notes`/`tier`/`ceiling`/`mode` parsed straight from the text) — do not reinterpret, expand, or improve the goal. Then report the tool's summary output verbatim.
