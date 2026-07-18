---
name: hinta
description: Find and compare the current price of consumer electronics across Finnish retailers (Verkkokauppa, Power, Datatronic, Jimms, Multitronic, Proshop) using the agent-native `hinta` CLI. Use when the user wants the cheapest price for a specific product, to compare a product across shops, to check stock, or to build a parts list by price — e.g. "cheapest 7800X3D in Finland", "is a Samsung 990 Pro 2TB cheaper anywhere", "65-inch OLED TV under 1500€ in stock". Not for non-Finnish shops or non-electronics.
---

# hinta — Finnish electronics deal-finder

`hinta` fans one query out to six Finnish retailers and returns the **same product grouped across them, cheapest first, at live prices**. The fan-out and cross-retailer matching happen inside the binary — you run one command and read the groups. It is query-driven on purpose: prices are volatile, so a fresh search per question beats any cached catalogue.

The binary is on PATH (`hinta`). If PATH resolution fails, use `~/Dev/hinta/target/release/hinta` (repo `~/Dev/hinta`). **Always pass `--json`** — data goes to stdout, diagnostics to stderr, so piping into `jq` is safe.

## Decide the shape of the request first

- **Specific product** ("7800X3D", "Samsung 990 Pro 2TB", "LG C4 55 inch") → just run `compare`. Don't interrogate the user.
- **Vague** ("a good GPU", "a cheap TV", "a gaming PC") → ask **2–3 clarifying questions** before searching: budget ceiling, key spec (size/capacity/model tier), must-haves (in stock now? brand?), and any deal-breaker. Encode the answers as filters. Guessing wastes fan-out requests on the wrong product.

## The one command that does the work

```bash
hinta compare "<query>" --enrich --json
```

- `compare` searches every searchable retailer and groups identical products. Cheapest offer per group is surfaced first.
- `--enrich` spends up to 12 product-page fetches to fill in missing EANs, which upgrades a fuzzy `sku` match to a certain `ean` match and can pull in retailers that couldn't otherwise be grouped confidently (`matched_on` goes `sku`→`ean`, `confidence` `0.9`→`1.0`). It costs requests and Proshop throttles per IP, so **enrich for a real buying decision; skip it for a quick ballpark**.
- Add `--multi-only` to keep only products at least two retailers carry (drops single-shop noise). `--threshold F` (default sensible) tightens/loosens grouping — rarely needed.

`search` is the raw, ungrouped variant against one or all retailers (`--source S`, `--limit N`) — use it only when the user wants a specific retailer's own listing, not a cross-shop comparison.

## Filters (both `search` and `compare`)

Applied **before** grouping, so an excluded listing can't drag an unrelated product into a group and the reported cheapest price always refers to something that passed.

| Flag | Meaning |
|---|---|
| `--min-price` / `--max-price` | euro bounds |
| `--in-stock` | only confirmed-in-stock; **unknown stock is treated as failing** (never promise availability the tool can't confirm) |
| `--min-inches` / `--max-inches` | screen size, for TVs/monitors |
| `--brand <b>` | brand match (lowercase, e.g. `amd`, `samsung`) |
| `--devices-only` | drop accessories/services — wall mounts, cables, assembly services that pollute category queries like `televisio` |

`--devices-only` is essential for broad category searches; unnecessary for a specific model number.

## Reading the output

```jsonc
{
  "group_count": 22,
  "enriched": 0,
  "filtered_out": 0,          // listings dropped by filters (distinguishes "filter matched nothing" from "retailers have nothing")
  "errors": [],               // per-source failures — one blocked retailer never masks the rest; report these if a shop is missing
  "groups": [
    {
      "name": "...",
      "cheapest_price_euro": 327.9,
      "highest_price_euro": 365.99,
      "matched_on": "sku",     // "ean" = certain, "sku"/"name" = fuzzy
      "confidence": 0.9,       // 1.0 only when matched on validated EAN
      "attributes": { "brand": "amd", "capacity_gb": 0, "kind": "device" },
      "offers": [ { "source", "name", "price_euro", "in_stock", "url", "ean" }, ... ]  // cheapest first
    }
  ]
}
```

- **Lead with the cheapest in-stock offer**, name the retailer and price, and give the user the URL. If the cheapest is out of stock, say so and point at the cheapest *available* one — `--in-stock` up front avoids this.
- **`matched_on: "ean"` / `confidence: 1.0` is a certain match.** A `sku`/`name` match at lower confidence is probable, not proven — if it matters, re-run with `--enrich` to confirm.
- **A single-offer group is often real, not a bug.** The matcher deliberately **prefers a false split to a false merge** — a false split shows one offer too few; a false merge advertises a cheapest price that doesn't exist. So don't assume a lone group means the other shops lack it; they may carry a variant (different capacity / screen size / qualifier like `Ti`, `Pro`, `Super`) that correctly did **not** merge. Check the `attributes` and offer names before claiming "only one retailer has it".
- **`errors` is not fatal** — surface which retailer failed if the user expected it, but still answer from the rest.

Hand off a browser link with `hinta open <id|url> [--source S]`.

## Robots posture — respect it

`hinta sources --json` reports per-retailer capabilities and a `robots` field. Search is **disallowed** by robots.txt for Jimms, Multitronic and Gigantti; permitted for the rest. `compare`/`search` are **interactive, user-initiated** actions, which is the intended use. Do **not** wrap them in a polling loop or cron against a disallowed source — that crosses from "a user asked a question" into crawling. Product-detail lookups (`product`, and what `refresh` uses) are permitted everywhere.

## Watching a price (not just a one-shot lookup)

```bash
hinta alert <product_id> --source S --below <PRICE>   # implies track
hinta refresh                                          # re-fetch tracked products; reports alerts_triggered
hinta alerts --json                                    # list alerts and whether reached
```

There is **no daemon** — alerts are evaluated only when `refresh` runs. If the user wants ongoing monitoring, they need a cron entry calling `hinta refresh` plus something acting on `alerts_triggered`; say so rather than implying it watches on its own.

## Gigantti is out of scope

Gigantti can't be searched live (Vercel bot challenge + client-rendered results). Don't try to route around it. Product lookup by id works only when the origin is reachable. The other six cover the market.

## Recipes

```bash
# Cheapest confirmed-in-stock, ready to buy:
hinta compare "ryzen 7 7800x3d" --enrich --in-stock --json

# Specific capacity/variant — let the matcher keep variants apart, then read attributes:
hinta compare "samsung 990 pro 2tb" --enrich --json

# Broad category, devices only, size + budget bounded:
hinta compare "televisio" --devices-only --min-inches 65 --max-price 1500 --in-stock --json

# Only products multiple shops carry (kills single-listing noise):
hinta compare "rtx 4070 super" --multi-only --json

# One retailer's own listing:
hinta search "logitech mx master" --source verkkokauppa --json

# What each retailer supports + its robots status:
hinta sources --json
```

Full command reference and design notes live in `~/Dev/hinta/CLAUDE.md`. `hinta --help` and `hinta <cmd> --help` are authoritative for flags.
