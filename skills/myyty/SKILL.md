---
name: myyty
description: Query Marcus's local App Store Connect sales warehouse with the myyty CLI - units, downloads, updates, IAP, proceeds and subscriptions for any app, country, device, version or window, plus the browser dashboard. Load for any question about how the apps are selling or performing, any revenue or download number, or any request to refresh, slice or chart App Store data.
---

# myyty — the App Store sales warehouse

`myyty` keeps every App Store Connect report Apple has issued in a local DuckDB file, so slicing the data is a query instead of a download. Repo `~/Dev/python/myyty` (guitaripod/myyty), installed with `uv tool install --editable .` as `~/.local/bin/myyty`. Warehouse `~/.local/share/myyty/myyty.duckdb`, raw reports `~/.local/share/myyty/raw/`.

Prefer `myyty` over raw `asc analytics sales` for anything read-only: `asc` fetches one period per call, `myyty` has them all already. Use `asc` (see the `app-store` skill) for everything that is not sales data.

## Refresh first, then query

```
myyty sync                      # fills the gap since the last stored day (idempotent)
myyty sync --last 90d --force   # refetch a window, e.g. after Apple restates it
myyty coverage                  # which periods are stored, per report
```

Apple publishes yesterday's daily report, keeps dailies for ~365 days and restates the last few days, so `sync` always re-pulls the newest two days. Nothing is refetched twice otherwise; `myyty rebuild` replays the raw files with no network.

## Reading the data

```
myyty overview --last 7d                       # daily totals, apps, revenue in one screen
myyty apps --last 30d --metric units
myyty top --by country --last 30d              # any dimension: country device platform kind version client category product type
myyty app tailscode --last 90d                 # one app: daily, kinds, countries, devices, versions, products
myyty compare --last 7d                        # window vs the window before it, per app
myyty revenue --last 30d [--detail]            # proceeds grouped per currency
myyty settled                                  # Apple's monthly financial reports
myyty subs --last 30d [--app "solar beam"]     # active subscriptions by state and country
myyty agg --dims app,country --metrics units,proceeds --last 30d --limit 50
myyty sql "SELECT device, sum(units) FROM sales WHERE report_date >= '2026-09-01' GROUP BY 1 ORDER BY 2 DESC"
myyty schema                                   # tables, views, dimensions, metrics, filters
```

Every reading command takes `--last 7d|4w|6m|1y` or `--from`/`--to`, the filters `--app --country --device --kind --currency --product`, and `--output table|json|csv|markdown`. Use `--output json` when you need to compute on the result, `markdown` when the answer goes into a message.

`myyty serve --host 0.0.0.0 --port 8787` runs the browser dashboard (same data, macro row → app table → per-app drilldown → arbitrary slice → SQL). It is reachable over Tailscale from the phone.

## What the numbers mean

- `kind` buckets Apple's Product Type Identifier: `download` (first-time), `redownload`, `update`, `iap`. Apple's raw identifiers encode platform too (`1`/`1F` iOS, `F1` Mac, `F7` Mac update, `IA1` IAP) — the `device` and `platform` dimensions are the readable version.
- An app is keyed by its Apple ID; its store name changes over time, so `app_name` is always the most recent title Apple reported (that is why "Solar Beam: James Webb Images" and "Solar Beam" are one row, and why iOS and Mac builds of the same product appear as separate apps with separate Apple IDs, e.g. `flaccy-ios` vs `flaccy-macos`).
- IAP rows carry the parent app's SKU, not its Apple ID; `myyty` resolves them so an IAP's units and proceeds land under its app, with the IAP name in `product`. Never filter IAPs by app title.
- Money is never converted. Any table with a `money` column shows each currency separately ("89.83 PLN + 2.54 USD"); the numeric `proceeds` metric is only meaningful with `--currency` set or `currency` as a dimension. Real EUR figures come from Apple's payments, not from these reports — say so instead of adding currencies up.
- `units` counts app units, so it mixes first downloads with updates and redownloads. Quote `downloads` when asked "how many downloads", and mention updates separately; a release day inflates `units` massively.
- Proceeds are Apple's developer proceeds (after its cut), dated by the sales day, not by when the money settles. `myyty settled` is the settlement view and is keyed by Apple's fiscal months, which do not line up with calendar months.

## Gotchas

- `myyty sql` is read-only (SELECT/WITH/DESCRIBE/SUMMARIZE only) and runs against the `sales` view plus `sales_rows`, `subscription_rows`, `finance_rows`, `apps`, `products`, `daily_app`, `daily_totals`, `proceeds_by_currency`, `active_subscriptions`, `coverage`. Run `myyty schema` before writing a query rather than guessing column names.
- A day with no sales at all is a real "no report" from Apple, logged as unavailable — not a sync failure. `myyty coverage` distinguishes them.
- `SUBSCRIPTION_EVENT` and `SUBSCRIBER` reports only exist on days with events, so subscription history is sparse by design.
- `myyty doctor` checks the vendor number, the warehouse and `asc auth` in one call when something looks empty.
