---
description: Answer an App Store sales or analytics question from the local myyty warehouse — units, downloads, IAP, proceeds, subscriptions, any app, country, device or window
---

Answer "$ARGUMENTS" about Marcus's App Store apps using the `myyty` CLI (`~/.local/bin/myyty`), a local DuckDB warehouse of every App Store Connect report. Never hand-roll `asc analytics sales` downloads for read-only questions; the data is already stored.

## Steps

1. `myyty sync` first (idempotent, fills the gap since the last stored day; Apple restates the newest days). If it reports no vendor, run `myyty doctor` and say what is missing instead of guessing.
2. Pick the command that matches the question, always with an explicit window:

```
myyty overview --last 7d                    # daily totals + apps + revenue
myyty apps --last 30d                       # per-app table
myyty top --by country --last 30d           # rank country device platform kind version client category product
myyty app "tailscode" --last 90d            # one app from every angle
myyty compare --last 7d                     # this window vs the previous one
myyty revenue --last 30d [--detail]         # proceeds per currency
myyty subs --last 30d [--app "solar beam"]  # active subscriptions
myyty agg --dims app,country --metrics units,proceeds --last 30d
myyty sql "SELECT ..."                      # anything else; run `myyty schema` first
```

Windows: `--last 7d|4w|6m|1y` or `--from YYYY-MM-DD --to YYYY-MM-DD`. Filters: `--app --country --device --kind --currency --product`. Output: `--output table|json|csv|markdown`.

3. Present the answer as a markdown table (`--output markdown`, or rebuild it from `--output json`), smallest table that answers the question, with the date range stated once.

## Reading the numbers correctly

- `units` mixes first downloads, redownloads and updates. Quote `downloads` for "how many downloads", and call out updates separately — a release day inflates `units`.
- `money` columns list each currency separately ("89.83 PLN + 2.54 USD"). Never add currencies together and never invent an exchange rate; if asked for one total, say that only Apple's payments give a real EUR figure.
- IAP rows belong to their parent app and carry the IAP name in `product`; subscription revenue shows up there, not under a separate app.
- One app = one Apple ID with its latest store name; iOS and Mac builds of the same product are separate apps.
- A day Apple reports nothing for is a real zero-sales day, not a failed sync (`myyty coverage` proves which).

`myyty serve --host 0.0.0.0` starts the browser dashboard if the question is better answered by charts; tell Marcus the URL rather than describing the page.
