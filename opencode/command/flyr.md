---
description: Find the cheapest flights by fanning flyr (Google Flights) searches across a window of dates and nearby airports
---

Find the cheapest fares for "$ARGUMENTS" using the flyr MCP tools (they query Google Flights).

## Plan first

Run `date +%F` (Bash) for today, and resolve every relative date ("next month", "September", "in 3 weeks", "this weekend") against it. NEVER search a past date. Then decide:

- Origin: default HEL (Helsinki) if not given.
- Destination(s): the user's target plus sensible nearby alternates in the same metro, comma-separated — Seoul → ICN,GMP; London → LHR,LGW,STN; Tokyo → NRT,HND; Bangkok → BKK,DMK; New York → JFK,EWR,LGA. Cap at 3 codes total.
- Defaults: currency EUR, seat economy, adults 1, maxStops none (any), airlines none.
- Round-trip if a return date / "for N weeks" / "round trip" is implied, else one-way.
- Build an explicit search grid that exploits date flexibility (the single biggest lever on price): exact date → that date ± a few days (~7 points one-way); month/vague window → dates every 2–3 days (up to ~12); round-trip with a length ("~2 weeks") → pair each departure with departure+length as return; fixed return window → a small (depart, return) grid. Cap at 12 searches unless the user asks to be exhaustive — then up to 24.

## Search in parallel

One `flyr_search` call per grid point (issue them all in parallel), with the same from/to/seat/currency/adults (+ return_date, max_stops, airlines if planned). Ask for top 3.

Each result's flights have: `price`, `airlines` (array), and `segments` (each with `from_airport.code`, `to_airport.code`, `departure`/`arrival` {year,month,day,hour,minute}, `duration_minutes`). The OUTBOUND journey is the run of segments from the origin up to and including the first segment whose `to_airport.code` is one of the destinations; segments after that are the return leg — ignore them for stops/times/duration (price is the total round-trip price; keep it as-is). For each of the 3 cheapest per search record: price, destination (outbound final code), airlines joined with " + ", stops (outbound segments − 1), departTime/arriveTime as zero-padded HH:MM, durationHours (sum of outbound duration_minutes / 60, 1 decimal), itinerary string like "HEL→IST→ICN · 1 stop · 19.7h · Turkish Airlines". If a search errors or returns nothing, record that as an error line — never invent fares.

## Rank

Dedupe (same price+itinerary+dates), sort cheapest first, take the top 8. Answer concisely:

1. **Headline**: the cheapest fare — price + currency, route, date(s), airline, stops, total duration.
2. Up to 5 best options: **<price> <currency>** — route · N stop(s) · ~Xh · airline · departs <date>[, returns <date>] · <departTime>→<arriveTime>.
3. One line of judgment: is the cheapest also the best value, or does a slightly pricier option win on much shorter time / fewer stops? If a particular departure date is clearly cheaper, say so — flexibility is the main lever.
4. Offer to open the cheapest in Google Flights: call `flyr_get_url` with the cheapest fare's from/to/dates/seat/currency, then `open_url` on the returned URL.

If nothing was found, say which searches failed and why, and suggest a different window or broader airports. Be factual and tight.
