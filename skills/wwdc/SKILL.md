---
name: wwdc
description: Answer questions about Apple frameworks and APIs from the WWDC session knowledge base (guitaripod/wwdc-sessions, WWDC 2014-2026 plus Tech Talks) - which session covers a topic, what's new in a framework, session numbers and titles, code from a session. Use for any WWDC or "what did Apple announce for X" question.
---

# WWDC session lookup

Repo `guitaripod/wwdc-sessions`, branch `master`, raw base `https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/`. Every session lives at `sessions/<event>/<id>-<slug>/` with `README.md` (summary, code snippets, doc links) and `transcript.md`. Never derive a path from an id; take it from an index.

A query is RECENT when it says new, latest, this year, or WWDC 26 (prefer `wwdc2026`), and DETAIL when it asks how to, for an example, code, or implementation (read transcripts too).

## Find up to 5 sessions

Fetch the indexes relevant to the query in parallel (WebFetch or `curl -sf`):
- `events/<event>/index.md` for a named year (`wwdc2026`, `wwdc2025`, ..., `tech-talks`), grouped by topic with links
- `topics/swift.md`, `topics/app-services.md`, `topics/developer-tools.md`, `topics/essentials.md`, and the other files under `topics/`

When the indexes have nothing relevant, search full text: `gh search code "<terms>" --repo guitaripod/wwdc-sessions --limit 30` and keep the unique `sessions/<event>/<id>-<slug>/` paths. Say plainly when nothing matches.

## Read and answer

Fetch each session's `README.md` in parallel; add `transcript.md` for DETAIL queries or when the README is under about 200 words. Answer only from what you fetched: session number and title for every claim, concrete API names, and code where the sources have it.
