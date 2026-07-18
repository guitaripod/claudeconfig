export const meta = {
  name: 'hinta-best',
  description: 'Recommend the best thing to buy — either the best model in a category, or the best variant/deal for a product you have already chosen — priced live across Finnish electronics retailers',
  whenToUse:
    'When you want a "what should I buy" answer checked against live Finnish prices. Two modes, auto-detected: an OPEN category ("/hinta-best best 4TB NVMe SSD", "/hinta-best 65 inch OLED TV under 2000") shortlists competing models; a SPECIFIC product you have decided on ("/hinta-best rtx 5090", "/hinta-best samsung 990 pro 2TB") finds the best variant and cheapest in-stock deal for it.',
  phases: [
    { title: 'Scope', detail: 'classify the request and build the search plan' },
    { title: 'Price', detail: 'price candidates / variants across Finnish retailers', model: 'claude-haiku-4-5-20251001' },
    { title: 'Recommend', detail: 'weigh quality vs. live price and pick the winners' },
  ],
}

const query =
  typeof args === 'string' && args.trim()
    ? args.trim()
    : args && typeof args === 'object'
      ? JSON.stringify(args)
      : ''

if (!query) {
  return [
    'Usage: `/hinta-best <category or product> [constraints]`',
    '',
    'Open category (shortlists competing models):',
    '- `/hinta-best best 4TB NVMe SSD`',
    '- `/hinta-best 65 inch OLED TV under 2000`',
    '- `/hinta-best wireless gaming mouse`',
    '',
    'Specific product (finds the best variant + cheapest deal):',
    '- `/hinta-best rtx 5090`',
    '- `/hinta-best samsung 990 pro 2TB`',
  ].join('\n')
}

const SCOPE_SCHEMA = {
  type: 'object',
  properties: {
    mode: {
      type: 'string',
      enum: ['category', 'product'],
      description:
        "'product' if the request already names ONE specific product/model the user has decided to buy (e.g. 'rtx 5090', 'samsung 990 pro 2TB', 'sony wh-1000xm5') — then we rank its variants and retailers. 'category' if it's an open 'what's best' question (e.g. 'best 4TB SSD', 'a good OLED TV') — then we shortlist competing models.",
    },
    category: { type: 'string', description: 'normalized category or product, e.g. "4TB NVMe Gen4 SSD" or "GeForce RTX 5090"' },
    interpretation: { type: 'string', description: 'one sentence: what we are buying + constraints + use-case' },
    budgetEur: { type: ['number', 'null'] },
    minInches: { type: ['number', 'null'], description: 'screens only, else null' },
    maxInches: { type: ['number', 'null'], description: 'screens only, else null' },
    searchQuery: {
      type: ['string', 'null'],
      description: "PRODUCT mode only: the exact string to search Finnish retailers, e.g. 'rtx 5090' or 'samsung 990 pro 2tb'. null in category mode.",
    },
    candidates: {
      type: 'array',
      description: 'CATEGORY mode only: 5-8 concrete best-in-class models. Empty in product mode.',
      items: {
        type: 'object',
        properties: {
          model: { type: 'string', description: 'exact searchable name incl. defining size/capacity, e.g. "WD Black SN850X 4TB", "LG OLED65C4"' },
          brand: { type: 'string' },
          tier: { type: 'string', enum: ['flagship', 'value', 'budget'] },
          why: { type: 'string', description: 'one line: what makes it strong' },
        },
        required: ['model', 'brand', 'tier', 'why'],
      },
    },
  },
  required: ['mode', 'category', 'interpretation', 'budgetEur', 'minInches', 'maxInches', 'searchQuery', 'candidates'],
}

phase('Scope')

const scope = await agent(
  `You are scoping a "best thing to buy" request, to be priced against LIVE Finnish electronics retailers.

Request: "${query}"

First run \`date +%F\` (Bash) for today's date; electronics move fast so treat training knowledge as possibly stale.

Decide the MODE:
- 'product' — the request already names ONE specific product/model the user has chosen (e.g. "rtx 5090", "samsung 990 pro 2TB", "sony wh-1000xm5", "lg c4 65"). We will run one retailer search and rank the variants/retailers of THAT product. Set 'searchQuery' to the exact string a Finnish shop would match (short: brand + line + model + defining size, e.g. "rtx 5090", "samsung 990 pro 2tb"). Leave 'candidates' empty.
- 'category' — an open "what's best" question (e.g. "best 4TB SSD", "a good OLED under 2000", "wireless gaming mouse"). Use WebSearch to find the CURRENT best-in-class picks as of today (RTINGS, Tom's Hardware, TechPowerUp, Wirecutter, etc.), then set 'candidates' to 5-8 concrete, currently-buyable models spanning tiers (>=1 flagship, 1-2 value, 1 budget). Each 'model' must be an EXACT searchable name including the defining size/capacity ("WD Black SN850X 4TB", "LG OLED65C4"), never vague. Leave 'searchQuery' null.

For both: respect hard constraints (budget, screen size, form factor, must-haves) and set budgetEur / minInches / maxInches (inches only for screens, else null). 'category' = normalized name, 'interpretation' = one sentence.`,
  { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA }
)

const inchArgs =
  (scope.minInches ? ` --min-inches ${scope.minInches}` : '') +
  (scope.maxInches ? ` --max-inches ${scope.maxInches}` : '')

log(`${scope.mode === 'product' ? 'Product' : 'Category'}: ${scope.interpretation}`)

let options = []

phase('Price')

if (scope.mode === 'product') {
  const q = (scope.searchQuery || scope.category || query).replace(/"/g, '\\"')
  log(`Pricing variants of "${q}" across Finnish retailers…`)

  const PRODUCT_SCHEMA = {
    type: 'object',
    properties: {
      variants: {
        type: 'array',
        description: 'the distinct real variants of this product, cheapest in-stock first, max 10',
        items: {
          type: 'object',
          properties: {
            name: { type: 'string', description: 'the group/product name as listed (e.g. the specific board-partner card)' },
            cheapestPriceEur: { type: 'number' },
            inStock: { type: 'boolean' },
            retailer: { type: 'string' },
            url: { type: 'string' },
            retailerCount: { type: 'integer' },
          },
          required: ['name', 'cheapestPriceEur', 'inStock', 'retailer', 'url', 'retailerCount'],
        },
      },
      error: { type: ['string', 'null'] },
    },
    required: ['variants', 'error'],
  }

  const res = await agent(
    `Run EXACTLY this command (searches Finnish electronics retailers and groups the same product across them) and parse its JSON stdout:

\`\`\`
hinta compare "${q}" --enrich --devices-only${inchArgs} --json
\`\`\`

The JSON has a "groups" array. Each group is one distinct product variant carried by one or more retailers:
- "name", "cheapest_price_euro", "matched_on" ("ean" = certain), "confidence".
- "attributes": { brand, capacity_gb, screen_inches?, qualifiers?, kind }.
- "offers": [{ source (retailer), name, price_euro, in_stock, url }], cheapest first.

Keep ONLY groups that are genuinely the product "${scope.category}" (right brand and, if the query implied a capacity/size, that capacity/size). Drop accessories, unrelated items, and clearly-different-tier products. For each kept group, report the best BUYABLE offer: the cheapest in_stock offer; if the group has none in stock, its cheapest offer with inStock=false. Deduplicate near-identical variants. Return up to 10 variants, cheapest-in-stock first:
- name, cheapestPriceEur, inStock, retailer (offer source), url (offer url), retailerCount (offers in the group).

If the command errors or nothing matches, return an empty "variants" and a one-line "error". NEVER invent a price or URL.`,
    { label: `price:${q}`, phase: 'Price', schema: PRODUCT_SCHEMA, model: 'claude-haiku-4-5-20251001' }
  )

  options = (res?.variants || [])
    .filter(v => v && v.cheapestPriceEur != null)
    .map(v => ({
      label: v.name,
      tier: null,
      why: null,
      cheapestPriceEur: v.cheapestPriceEur,
      inStock: !!v.inStock,
      retailer: v.retailer,
      url: v.url,
      retailerCount: v.retailerCount || 1,
      foundInFinland: true,
      note: null,
    }))

  if (!options.length) {
    return `No in-stock Finnish listings matched **${scope.category}**.\n\n${scope.interpretation}${res?.error ? `\n\nSearch reported: ${res.error}` : ''}\n\nTry \`hinta compare "${q}"\` directly, or broaden the query.`
  }
} else {
  const candidates = (scope.candidates || []).filter(c => c && c.model).slice(0, 8)
  if (!candidates.length) return `Couldn't derive candidate models for: "${query}".\n\n${scope.interpretation || ''}`
  log(`Pricing ${candidates.length} candidate model${candidates.length > 1 ? 's' : ''} across Finnish retailers…`)

  const CAND_SCHEMA = {
    type: 'object',
    properties: {
      foundInFinland: { type: 'boolean' },
      cheapestPriceEur: { type: ['number', 'null'] },
      inStock: { type: 'boolean' },
      retailer: { type: ['string', 'null'] },
      url: { type: ['string', 'null'] },
      retailerCount: { type: 'integer' },
      note: { type: ['string', 'null'] },
    },
    required: ['foundInFinland', 'cheapestPriceEur', 'inStock', 'retailer', 'url', 'retailerCount', 'note'],
  }

  const priced = await parallel(
    candidates.map(c => () =>
      agent(
        `Run EXACTLY this command and parse its JSON stdout:

\`\`\`
hinta compare "${c.model.replace(/"/g, '\\"')}" --enrich --devices-only${inchArgs} --json
\`\`\`

It returns a "groups" array; each group is a product across retailers, with "attributes" (brand, capacity_gb, screen_inches?, qualifiers?) and "offers" [{ source, price_euro, in_stock, url }] cheapest first.

Pick the ONE group that best matches "${c.model}" (brand "${c.brand}") — match the implied capacity/size, prefer the plain variant over add-ons/bundles. From it report the best BUYABLE offer (cheapest in_stock; else cheapest with inStock=false):
- foundInFinland (false if nothing matches, then null/0/false elsewhere), cheapestPriceEur, inStock, retailer, url, retailerCount, note (one short line only if something's off, else null).

If the command errors or nothing matches, foundInFinland=false with the reason in note. NEVER invent a price or URL.`,
        { label: `price:${c.model}`, phase: 'Price', schema: CAND_SCHEMA, model: 'claude-haiku-4-5-20251001' }
      )
    )
  )

  options = candidates.map((c, i) => {
    const p = priced[i] || { foundInFinland: false, note: 'pricing agent failed' }
    return {
      label: c.model,
      tier: c.tier,
      why: c.why,
      cheapestPriceEur: p.cheapestPriceEur ?? null,
      inStock: !!p.inStock,
      retailer: p.retailer ?? null,
      url: p.url ?? null,
      retailerCount: p.retailerCount ?? 0,
      foundInFinland: !!p.foundInFinland,
      note: p.note ?? null,
    }
  })

  if (!options.some(o => o.foundInFinland && o.cheapestPriceEur != null)) {
    const misses = options.map(o => `- ${o.label}${o.note ? ` — ${o.note}` : ' — not found'}`).join('\n')
    return `None of the best-in-class candidates for **${scope.category}** turned up at a Finnish retailer.\n\n${scope.interpretation}\n\nChecked:\n${misses}\n\nThe strong models may not be stocked in Finland — try \`hinta compare "<exact model>"\` for a specific one.`
  }
}

phase('Recommend')

return await agent(
  `You are giving a "best thing to buy" recommendation, grounded in LIVE Finnish retail prices.

Request: "${query}"
${scope.mode === 'product' ? 'Mode: a specific product the user has chosen — pick the best VARIANT and cheapest good deal.' : 'Mode: an open category — pick the best MODEL to buy.'}
Scope: ${scope.interpretation}
${scope.budgetEur ? `Budget ceiling: ${scope.budgetEur} EUR.` : 'No explicit budget.'}

Options with live Finnish pricing (JSON):
${JSON.stringify(options, null, 2)}

Write a concise markdown recommendation using ONLY these facts:
1. **Top pick** — best overall balance of quality and live price (NOT merely the cheapest). Give the name, price in EUR, retailer, in-stock status, and the buy URL, plus one line on why it wins${scope.mode === 'product' ? ' (cooling/noise/warranty/price for a variant)' : ''}.
2. **Best value** and **Cheapest good option** — one line each (name, price, retailer, in-stock, URL). Skip a bucket the top pick already fills.
${scope.mode === 'category' ? '3. If a genuinely best-in-class model was NOT found in Finland (foundInFinland=false), note it in one line so the user knows it exists but is not stocked here — do NOT recommend buying it.\n' : ''}${scope.budgetEur ? `4. Flag any pick over the ${scope.budgetEur} EUR budget.\n` : ''}5. Prefer in-stock; if the best option is out of stock, say so and point at the best in-stock alternative. If prices cluster, say the market is tight so any reputable in-stock one is fine.

Rules: prices are EUR and live. Never invent a price, retailer, or URL not in the JSON. Never recommend an item with foundInFinland=false as a buy. Be factual and tight — the buyer should know exactly what to click.`,
  { label: 'recommend', phase: 'Recommend' }
)
