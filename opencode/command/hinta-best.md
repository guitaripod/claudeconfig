---
description: Recommend the best thing to buy — best model in a category, or best variant/deal for a chosen product — priced live across Finnish electronics retailers
---

Give a "best thing to buy" recommendation grounded in LIVE Finnish retail prices for "$ARGUMENTS".

Run `date +%F` (Bash) for today; electronics move fast, so treat training knowledge as possibly stale.

## Scope — decide the mode

- **product**: the request names ONE specific product/model the user has decided to buy (e.g. "rtx 5090", "samsung 990 pro 2TB", "sony wh-1000xm5", "lg c4 65"). We rank its variants/retailers. Derive the exact search string a Finnish shop would match (brand + line + model + defining size, e.g. "rtx 5090", "samsung 990 pro 2tb").
- **category**: an open "what's best" question (e.g. "best 4TB SSD", "a good OLED under 2000", "wireless gaming mouse"). Use WebSearch to find the CURRENT best-in-class picks (RTINGS, Tom's Hardware, TechPowerUp, Wirecutter…), then shortlist 5-8 concrete, currently-buyable models spanning tiers (≥1 flagship, 1-2 value, 1 budget). Each model name must be EXACT and searchable, including the defining size/capacity ("WD Black SN850X 4TB", "LG OLED65C4"), never vague.

Respect hard constraints (budget, screen size, form factor, must-haves).

## Price it — one `hinta compare` per candidate/variant

Run, for the product string or each candidate model:

```
hinta compare "<model>" --enrich --devices-only [--min-inches N] [--max-inches N] --json
```

The JSON has a "groups" array; each group is one distinct product variant with `attributes` (brand, capacity_gb, screen_inches, qualifiers) and `offers` [{source, price_euro, in_stock, url}] cheapest first.

- product mode: keep ONLY groups that genuinely are the chosen product (right brand and, if implied, capacity/size); drop accessories, unrelated items, different tiers. Dedupe near-identical variants. For each kept variant, record the best BUYABLE offer: cheapest in_stock offer, else the cheapest with in_stock=false. Up to 10 variants, cheapest-in-stock first.
- category mode: per candidate, pick the ONE group that best matches the model (implied capacity/size, plain variant over bundles) and record the best buyable offer; if nothing matches, mark it not-found-in-Finland with a reason.

Issue the searches in parallel. Never invent a price or URL — only report what the CLI actually returned. If it errors, say so.

## Recommend

- **product mode** — pick the best VARIANT and cheapest good deal: 1. **Top pick** (best overall balance of quality and live price, NOT merely cheapest — weigh cooling/noise/warranty/price for variants): name, price EUR, retailer, in-stock status, buy URL, one line why. 2. **Best value** and **Cheapest good option** — one line each (name, price, retailer, in-stock, URL); skip a bucket the top pick already fills.
- **category mode** — pick the best MODEL: same structure, plus: if a genuinely best-in-class model was NOT found in Finland, note it in one line (it exists, just not stocked here — do NOT recommend buying it).

Rules: prices are EUR and live. Never invent a price, retailer, or URL. Never recommend an item not found in Finland as a buy. Prefer in-stock; if the best is out of stock, say so and point at the best in-stock alternative. If prices cluster, say the market is tight so any reputable in-stock one is fine. Flag any pick over the user's budget. Be factual and tight — the buyer should know exactly what to click.
