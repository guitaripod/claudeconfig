---
description: Search the WWDC session knowledge base (guitaripod/wwdc-sessions) and answer questions about Apple frameworks and APIs
---

Answer "$ARGUMENTS" (default: what's new) from the WWDC session knowledge base, repo `guitaripod/wwdc-sessions` (branch master).

Note whether the query is about RECENT content ("new", "latest", "wwdc 2X", "this year") — then strongly prefer wwdc2026 sessions — and whether it's a DETAIL query (how do/to/can, show me, example, code, implement, use).

## Find the sessions (up to 5)

1. **Topic index lookup (preferred)**: fetch the curated topic index files relevant to the query, in parallel:
   - https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/topics/swift.md
   - https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/topics/app-services.md
   - https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/topics/developer-tools.md
   - https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/topics/essentials.md
   - https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/events/wwdc2026/index.md

   Extract up to 5 session paths (format: sessions/wwdcYEAR/ID-slug) relevant to the query.
2. **Full-text fallback** (only if the topic files have nothing relevant): Bash `gh search code "<query>" --repo guitaripod/wwdc-sessions --limit 30`, extract unique session directory paths from lines matching `sessions/wwdcYEAR/ID-slug/`.

Derive each title from its slug (e.g. "274-what-s-new-in-swiftdata" → "What's New in SwiftData"). If nothing is found, say so plainly.

## Read the sessions (in parallel)

For each session, fetch `https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/<path>/README.md`. For a detail query (code/implementation), or when the README is very thin (under ~200 words), ALSO fetch `<path>/transcript.md` and append it.

## Synthesize

Write a clear, well-organized markdown answer grounded ONLY in the fetched content: concrete API changes, new features, and code examples where present. Cite which sessions you're drawing from. Be factual and tight — don't pad what the sources don't say.
