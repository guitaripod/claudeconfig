export const meta = {
  name: 'kaytetty-best',
  description:
    'Recommend the best USED-market buy in Finland — a specific thing to buy second-hand, the best used model in a category, or a whole multi-part build (e.g. a gaming PC) assembled from used parts — priced live across Tori.fi and Huuto.net, with a fair-price band and scam / overprice flags',
  whenToUse:
    'When you want a "what should I buy second-hand" answer checked against live Finnish used listings. Three modes, auto-detected: a SPECIFIC thing you have decided to buy used ("/kaytetty-best iphone 13 128gb", "/kaytetty-best rtx 3080") finds the best-value live listing plus the fair band; an OPEN category ("/kaytetty-best good used road bike under 800") shortlists models then checks what is for sale used; a BUILD ("/kaytetty-best gaming pc around a 1080 ti", "/kaytetty-best home office setup under 600") scopes a compatible parts/kit list around any anchor and sources every part used, then totals a coherent in-budget build with the used-vs-new saving.',
  phases: [
    { title: 'Scope', detail: 'classify the request and build the used-market search plan' },
    { title: 'Hunt', detail: 'pull live listings from Tori.fi + Huuto.net (+ new-price reference)', model: 'claude-haiku-4-5-20251001' },
    { title: 'Appraise', detail: 'compute the fair band, flag scams, pick the best-value listing / assemble the build' },
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
    'Usage: `/kaytetty-best <thing or category> [constraints]`',
    '',
    'Specific thing to buy used (fair band + best live listing):',
    '- `/kaytetty-best iphone 13 128gb`',
    '- `/kaytetty-best rtx 3080`',
    '- `/kaytetty-best herman miller aeron`',
    '',
    'Open category (shortlist models, then check what is for sale used):',
    '- `/kaytetty-best good used road bike under 800`',
    '- `/kaytetty-best cheap used 55 inch oled tv`',
    '',
    'Whole build / kit (compatible parts, each sourced used, totalled):',
    '- `/kaytetty-best gaming pc around a 1080 ti`',
    '- `/kaytetty-best home office setup under 600`',
    '',
    'Sources: Tori.fi + Huuto.net (Facebook Marketplace needs a login and is not searchable).',
  ].join('\n')
}

const SCOPE_SCHEMA = {
  type: 'object',
  properties: {
    mode: {
      type: 'string',
      enum: ['product', 'category', 'build'],
      description:
        "'product' if the request names ONE specific thing to buy used (e.g. 'iphone 13 128gb', 'rtx 3080'). 'category' if it is an open 'what used thing is best' question (e.g. 'good used road bike under 800'). 'build' if the request asks to ASSEMBLE a multi-part system or kit from used parts — a PC/gaming rig, a home-office/desk setup, a camera kit, etc. — usually anchored on one part the user names (e.g. 'gaming pc around a 1080 ti', 'home office setup under 600').",
    },
    category: { type: 'string', description: 'normalized thing/category, e.g. "Apple iPhone 13 128GB" or "used road bike"' },
    interpretation: { type: 'string', description: 'one sentence: what we are buying used + constraints + use-case' },
    searchQuery: {
      type: ['string', 'null'],
      description:
        "PRODUCT mode: the exact string a Finnish used marketplace would match (short, no fluff), e.g. 'iphone 13 128gb', 'rtx 3080', 'aeron'. null in category mode.",
    },
    coreQuery: {
      type: ['string', 'null'],
      description:
        "PRODUCT mode: the BROADEST core words that still name the item, dropping capacity/colour/spec qualifiers, e.g. searchQuery 'iphone 13 128gb' -> 'iphone 13', 'rtx 3080 ti' -> 'rtx 3080'. Used for strict all-words-must-match engines (Huuto.net) where a too-specific query returns nothing. null in category mode.",
    },
    mustMatch: {
      type: 'array',
      items: { type: 'string' },
      description:
        'lowercase tokens a genuine listing of THIS item must contain (defining model/capacity/size), used to keep only true matches, e.g. ["iphone 13","128"] or ["rtx","3080"]. Empty allowed.',
    },
    accessoryTerms: {
      type: 'array',
      items: { type: 'string' },
      description:
        'lowercase terms that mark an ACCESSORY / part / lookalike to DROP for this item, e.g. for a phone ["kuori","suojakuori","case","lasi","laturi","panssarilasi","kaapeli"]. Empty for items with no common accessory noise.',
    },
    budgetEur: { type: ['number', 'null'], description: 'hard max the user will pay, else null' },
    regionHint: { type: ['string', 'null'], description: 'a Finnish city/region the user prefers for pickup, else null (nationwide)' },
    newPriceQuery: {
      type: ['string', 'null'],
      description:
        "PRODUCT mode: a query for the NEW price of this item across Finnish electronics retailers via the `hinta` CLI, if it is the kind of electronics `hinta` covers (phones, GPUs, TVs, SSDs, laptops…). Same short form as searchQuery. null if it is not electronics (bikes, furniture, tools…) or in category mode.",
    },
    candidates: {
      type: 'array',
      description: 'CATEGORY mode only: 4-6 concrete, currently-desirable models to hunt for used. Empty in product mode.',
      items: {
        type: 'object',
        properties: {
          model: { type: 'string', description: 'exact searchable used-market name incl. defining size/spec, e.g. "Trek Domane SL", "LG OLED55C1"' },
          searchQuery: { type: 'string', description: 'short used-market search string for this model' },
          tier: { type: 'string', enum: ['flagship', 'value', 'budget'] },
          why: { type: 'string', description: 'one line: what makes it a strong used buy' },
        },
        required: ['model', 'searchQuery', 'tier', 'why'],
      },
    },
    platform: { type: ['string', 'null'], description: 'BUILD mode: the single coherent platform the parts share, so they are compatible by construction, e.g. "AMD AM4 (DDR4)". null otherwise.' },
    buildRationale: { type: ['string', 'null'], description: 'BUILD mode: one sentence on why this platform/part mix is the right value balance around the anchor. null otherwise.' },
    components: {
      type: 'array',
      description: 'BUILD mode only: the ordered part list for the build (typically 6-9 parts for a PC: gpu, cpu, motherboard, ram, storage, psu, case, and cooler only if the chosen CPU has no boxed cooler). Empty otherwise.',
      items: {
        type: 'object',
        properties: {
          key: { type: 'string', description: 'stable slug, e.g. "gpu", "cpu", "motherboard", "ram", "storage", "psu", "case", "cooler"' },
          label: { type: 'string', description: 'human label, e.g. "GPU", "CPU", "Motherboard"' },
          role: { type: 'string', enum: ['buy', 'owned'], description: '"buy" = source it used; "owned" = the user already has this part, include only for compatibility and do NOT hunt or price it' },
          searchQuery: { type: 'string', description: 'precise used-market search string for the chosen part, e.g. "gtx 1080 ti", "ryzen 5 5600", "b550 tomahawk", "corsair rm650"' },
          coreQuery: { type: 'string', description: 'broad core words for strict-AND engines (Huuto), e.g. "1080 ti", "ryzen 5600", "b550"' },
          mustMatch: { type: 'array', items: { type: 'string' }, description: 'lowercase tokens a real listing of this part must contain' },
          accessoryTerms: { type: 'array', items: { type: 'string' }, description: 'lowercase terms marking accessories/lookalikes to drop for this part' },
          targetSpec: { type: 'string', description: 'one line: what we need + why it fits, e.g. "AM4, 6c/12t, no bottleneck for a 1080 Ti" or "650W 80+ Gold, has the 8+6-pin the 1080 Ti needs"' },
          estBudgetEur: { type: ['number', 'null'], description: 'rough used allocation for this part in EUR, else null' },
          optional: { type: 'boolean', description: 'true if the build works without buying it (e.g. cooler when the CPU is boxed, or a part the user may already own)' },
          newPriceQuery: { type: ['string', 'null'], description: 'query for the NEW price via the hinta CLI if this part is still sold new (RAM/SSD/PSU/case/current CPUs); null for discontinued parts like a GTX 1080 Ti' },
        },
        required: ['key', 'label', 'role', 'searchQuery', 'coreQuery', 'mustMatch', 'accessoryTerms', 'targetSpec', 'estBudgetEur', 'optional', 'newPriceQuery'],
      },
    },
  },
  required: ['mode', 'category', 'interpretation', 'searchQuery', 'coreQuery', 'mustMatch', 'accessoryTerms', 'budgetEur', 'regionHint', 'newPriceQuery', 'candidates', 'platform', 'buildRationale', 'components'],
}

phase('Scope')

const scope = await agent(
  `You are scoping a "best thing to buy SECOND-HAND in Finland" request, to be priced against LIVE listings on Tori.fi (general classifieds) and Huuto.net (auctions + buy-now).

Request: "${query}"

First run \`date +%F\` (Bash) for today's date; the used market and what is desirable move fast, so treat training knowledge as possibly stale.

Decide the MODE:
- 'product' — the request already names ONE specific thing to buy used (e.g. "iphone 13 128gb", "rtx 3080", "herman miller aeron"). Set 'searchQuery' to the short exact string a used marketplace would match, and 'coreQuery' to the broadest core words that still name it with capacity/colour/spec qualifiers dropped (searchQuery "iphone 13 128gb" -> coreQuery "iphone 13") — some engines match all words strictly, so a specific query returns nothing and the broad one is filtered down later. Set 'mustMatch' to the defining tokens (model + capacity/size) and 'accessoryTerms' to the noise terms to drop (cases/screens/chargers/cables for a phone, etc.). Leave 'candidates' empty. If the item is electronics that new-goods shops carry, set 'newPriceQuery' so we can show the used-vs-new saving; else null.
- 'category' — an open "what used thing is best" question (e.g. "good used road bike under 800", "cheap used oled tv"). Use WebSearch to find the CURRENT well-regarded picks as of today, then set 'candidates' to 4-6 concrete, currently-buyable-used models spanning tiers. Each 'model' is an EXACT name incl. defining size/spec, each 'searchQuery' a short used-market string. Leave 'searchQuery'/'coreQuery'/'newPriceQuery' null and 'components' empty.
- 'build' — assemble a multi-part SYSTEM/kit from used parts (a gaming PC, a home-office setup, a camera kit…), usually anchored on one part the user named. Design ONE coherent, compatible, non-bottlenecked build and express it as 'components':
  * Pick a single 'platform' so the parts are compatible by construction (for a PC that means one CPU socket + matching motherboard chipset + right RAM generation — e.g. AMD AM4 with DDR4 is the used-market value sweet spot). Put the reasoning in 'buildRationale'.
  * Respect the ANCHOR: if the user names a specific part ("around a 1080 Ti"), that part IS in the build. If the wording says they already OWN it, set its role='owned' (include for compatibility, do not hunt/price). Otherwise role='buy' (source it used too) — and say which you assumed in 'interpretation'.
  * Choose parts that MATCH the anchor's level (do not pair a flagship CPU with a mid GPU) and that satisfy real constraints: the PSU must have the connectors + wattage the GPU needs (a GTX 1080 Ti draws ~250W and needs 8+6-pin, so ~650W+); the case must fit the motherboard form factor and the GPU length; skip a separate 'cooler' if the chosen CPU ships with a boxed cooler.
  * For each component set key/label/role/searchQuery/coreQuery/mustMatch/accessoryTerms/targetSpec/estBudgetEur/optional, and 'newPriceQuery' when the part is still sold new (RAM/SSD/PSU/case/current CPUs) or null for discontinued parts (a 1080 Ti has no new price). If the user gave a total budget, allocate estBudgetEur across parts to fit it.
  * Leave the product/category fields ('searchQuery','coreQuery','mustMatch','accessoryTerms','newPriceQuery','candidates') null/empty at the TOP level — the per-part queries live inside 'components'.

For all modes: respect hard constraints. Set 'budgetEur' to the user's max total (else null) and 'regionHint' to a preferred Finnish city/region for pickup if named (else null). 'category' = normalized name of the thing/build, 'interpretation' = one sentence (for a build, state the platform + anchor + whether the anchor is being bought or is owned). In product/category modes leave 'platform'/'buildRationale' null and 'components' empty.`,
  { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA }
)

log(`${scope.mode === 'product' ? 'Product' : scope.mode === 'build' ? 'Build' : 'Category'}: ${scope.interpretation}`)

const enc = s => encodeURIComponent(String(s || '').trim())

const LISTING_SCHEMA = {
  type: 'object',
  properties: {
    listings: {
      type: 'array',
      description: 'genuine listings of the target item only, accessories/parts/lookalikes dropped, max 25',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          priceEur: { type: ['number', 'null'], description: 'the price to actually pay: asking price (Tori) or buy-now price; for a pure auction with no buy-now use the current bid' },
          auction: { type: 'boolean', description: 'true only for a Huuto auction with bidding (not a fixed-price buy-now)' },
          buyNowEur: { type: ['number', 'null'] },
          currentBidEur: { type: ['number', 'null'] },
          location: { type: ['string', 'null'] },
          url: { type: 'string' },
          closingTime: { type: ['string', 'null'], description: 'ISO close time for Huuto auctions, else null' },
          bidderCount: { type: ['integer', 'null'] },
          condition: { type: ['string', 'null'], description: 'condition read from the title if stated (e.g. "like new", "boxed"), else null' },
          warrantyMonths: { type: ['integer', 'null'], description: 'months of warranty if the title says so (e.g. "TAKUU 12kk" -> 12), else null' },
          sellerType: { type: ['string', 'null'], enum: ['dealer', 'private', null], description: '"dealer" if it reads like a reseller/refurbisher (bulk identical listings, ALE/TAKUU branding), "private" if a normal one-off seller, else null' },
        },
        required: ['title', 'priceEur', 'auction', 'buyNowEur', 'currentBidEur', 'location', 'url', 'closingTime', 'bidderCount', 'condition', 'warrantyMonths', 'sellerType'],
      },
    },
    error: { type: ['string', 'null'] },
  },
  required: ['listings', 'error'],
}

function toriAgent(searchQuery, mustMatch, accessoryTerms, label) {
  const url = `https://www.tori.fi/recommerce/forsale/search?q=${enc(searchQuery)}`
  return agent(
    `Use the WebFetch tool on this Tori.fi used-marketplace search URL:

${url}

Pass WebFetch this extraction prompt: "This is a Finnish used-goods marketplace search page. Extract every for-sale listing: title, price in euros (number), location (city/region), and the absolute https listing url under tori.fi/recommerce/forsale/item/. Return a JSON array of up to 30, ONLY real listings that show a price."

Then from what WebFetch returns, keep ONLY genuine listings of the target item "${scope.category}"${mustMatch.length ? ` (the title must be consistent with all of: ${mustMatch.join(', ')})` : ''}. DROP accessories, parts, spares, cases and lookalikes${accessoryTerms.length ? ` (titles containing any of: ${accessoryTerms.join(', ')})` : ''}, and drop clearly-different variants/capacities than asked.

For each kept listing return: title, priceEur (the asking price), auction=false, buyNowEur=null, currentBidEur=null, location, url, closingTime=null, bidderCount=null, condition (from the title if stated, else null), warrantyMonths (e.g. a title saying "TAKUU 12kk" -> 12, else null), sellerType ("dealer" if the title looks like a reseller e.g. repeated "ALE …/ TAKUU 12kk" branding, else "private" for a normal seller). Max 25, cheapest first. NEVER invent a listing, price or url. If WebFetch fails or nothing matches, return empty listings and a one-line error.`,
    { label, phase: 'Hunt', schema: LISTING_SCHEMA, model: 'claude-haiku-4-5-20251001' }
  )
}

function huutoAgent(coreQuery, mustMatch, accessoryTerms, label) {
  const api = `https://api.huuto.net/1.1/items?words=${enc(coreQuery)}&status=open`
  return agent(
    `Run EXACTLY these commands (Huuto.net public JSON API, two pages) and parse the JSON stdout:

\`\`\`
curl -sL "${api}&page=1"
curl -sL "${api}&page=2"
\`\`\`

Huuto's "words" search matches ALL given words strictly, so this query is intentionally BROAD ("${coreQuery}") to avoid a zero-result search — do NOT add words to it; instead filter the results down to true matches using the criteria below.

Each response has an "items" array. Each item has: title, currentPrice, buyNowPrice, saleMethod ("buy-now" | "auction" | "buy-now-and-auction"), location, closingTime, bidderCount, offerCount, and links.alternative (the human https url on www.huuto.net — use THIS as url).

Keep ONLY genuine listings of the target item "${scope.category}"${mustMatch.length ? ` (title consistent with all of: ${mustMatch.join(', ')})` : ''}. DROP accessories, parts, cases and lookalikes${accessoryTerms.length ? ` (titles containing any of: ${accessoryTerms.join(', ')})` : ''}, and drop different variants than asked.

For each kept item:
- If saleMethod includes "buy-now": auction=false, buyNowEur=buyNowPrice, priceEur=buyNowPrice, currentBidEur=(currentPrice if there is also bidding else null).
- If it is a pure "auction": auction=true, buyNowEur=null, currentBidEur=currentPrice, priceEur=currentPrice (the current bid).
- location, url=links.alternative, closingTime, bidderCount. condition/warrantyMonths from the title if stated (else null). sellerType usually "private" on Huuto.

Max 25, cheapest first. NEVER invent data. If curl errors or nothing matches, return empty listings and a one-line error.`,
    { label, phase: 'Hunt', schema: LISTING_SCHEMA, model: 'claude-haiku-4-5-20251001' }
  )
}

async function huntListings(searchQuery, coreQuery, mustMatch, accessoryTerms, tag) {
  const results = await parallel([
    () => toriAgent(searchQuery, mustMatch, accessoryTerms, `tori:${tag}`),
    () => huutoAgent(coreQuery || searchQuery, mustMatch, accessoryTerms, `huuto:${tag}`),
  ])
  const merged = []
  const seen = new Set()
  results.filter(Boolean).forEach((r, idx) => {
    const source = idx === 0 ? 'Tori' : 'Huuto'
    ;(r.listings || []).forEach(l => {
      if (!l || !l.url || l.priceEur == null) return
      const key = l.url.trim()
      if (seen.has(key)) return
      seen.add(key)
      merged.push({ source, ...l })
    })
  })
  return merged
}

function priceBand(listings) {
  const fixed = listings.filter(l => !l.auction && l.priceEur != null).map(l => l.priceEur).sort((a, b) => a - b)
  if (!fixed.length) return null
  const q = p => {
    const i = (fixed.length - 1) * p
    const lo = Math.floor(i)
    const hi = Math.ceil(i)
    return fixed[lo] + (fixed[hi] - fixed[lo]) * (i - lo)
  }
  return { count: fixed.length, min: fixed[0], p25: Math.round(q(0.25)), median: Math.round(q(0.5)), p75: Math.round(q(0.75)), max: fixed[fixed.length - 1] }
}

function flagOutliers(listings, band) {
  if (!band) return listings.map(l => ({ ...l, flag: null }))
  return listings.map(l => {
    let flag = null
    if (!l.auction && l.priceEur != null) {
      if (l.priceEur < band.median * 0.55) flag = 'suspicious-low'
      else if (l.priceEur > band.median * 1.6) flag = 'overpriced'
    }
    return { ...l, flag }
  })
}

const NEW_SCHEMA = {
  type: 'object',
  properties: {
    foundInFinland: { type: 'boolean' },
    cheapestNewEur: { type: ['number', 'null'] },
    retailer: { type: ['string', 'null'] },
    url: { type: ['string', 'null'] },
  },
  required: ['foundInFinland', 'cheapestNewEur', 'retailer', 'url'],
}

function newRefAgent(newPriceQuery, label) {
  return agent(
    `Run EXACTLY this command (new-goods price across Finnish electronics retailers) and parse its JSON stdout:

\`\`\`
hinta compare "${String(newPriceQuery).replace(/"/g, '\\"')}" --enrich --devices-only --json
\`\`\`

It returns a "groups" array; each group has "attributes" (brand, capacity_gb…) and "offers" [{ source, price_euro, in_stock, url }] cheapest first. Pick the ONE group that best matches "${newPriceQuery}" (right capacity/variant, plain not bundle). Report the cheapest in-stock offer as the NEW reference price: foundInFinland, cheapestNewEur, retailer, url. If the command errors or nothing matches, foundInFinland=false and the rest null. NEVER invent a price.`,
    { label, phase: 'Hunt', schema: NEW_SCHEMA, model: 'claude-haiku-4-5-20251001' }
  )
}

phase('Hunt')

if (scope.mode === 'build') {
  const comps = (scope.components || []).filter(c => c && c.searchQuery)
  const toBuy = comps.filter(c => c.role !== 'owned')
  const owned = comps.filter(c => c.role === 'owned')
  if (!toBuy.length) return `Couldn't derive a parts list for: "${query}".\n\n${scope.interpretation || ''}`
  log(`Sourcing ${toBuy.length} part${toBuy.length > 1 ? 's' : ''} for a ${scope.platform || 'used'} build across Tori.fi + Huuto.net…`)

  const built = await parallel(
    toBuy.map(c => async () => {
      const [ls, newRef] = await parallel([
        () => huntListings(c.searchQuery, c.coreQuery || c.searchQuery, c.mustMatch || [], c.accessoryTerms || [], `part:${c.key}`),
        () => (c.newPriceQuery ? newRefAgent(c.newPriceQuery, `new-ref:${c.key}`) : Promise.resolve(null)),
      ])
      const band = priceBand(ls || [])
      const flagged = flagOutliers(ls || [], band).sort((a, b) => (a.priceEur ?? Infinity) - (b.priceEur ?? Infinity))
      const legit = flagged.filter(l => l.flag !== 'suspicious-low')
      const suspicious = flagged.filter(l => l.flag === 'suspicious-low')
      return {
        key: c.key,
        label: c.label,
        targetSpec: c.targetSpec,
        estBudgetEur: c.estBudgetEur,
        optional: !!c.optional,
        band,
        newRef: newRef && newRef.foundInFinland ? { eur: newRef.cheapestNewEur, retailer: newRef.retailer, url: newRef.url } : null,
        listings: [...legit.slice(0, 6), ...suspicious.slice(0, 2)].map(l => ({
          title: l.title,
          priceEur: l.priceEur,
          source: l.source,
          location: l.location,
          url: l.url,
          condition: l.condition,
          warrantyMonths: l.warrantyMonths,
          auction: l.auction,
          closingTime: l.closingTime,
          flag: l.flag,
        })),
      }
    })
  )

  const parts = built.filter(Boolean)
  const foundCount = parts.filter(p => p.listings.some(l => l.flag !== 'suspicious-low')).length
  const cheapestLegit = p => p.listings.find(l => l.flag !== 'suspicious-low' && l.priceEur != null) || null
  const cheapestLegitTotal = Math.round(parts.reduce((s, p) => s + (cheapestLegit(p)?.priceEur || 0), 0))
  const newTotalKnown = Math.round(parts.reduce((s, p) => s + (p.newRef?.eur || 0), 0))
  const partsWithNew = parts.filter(p => p.newRef).map(p => p.label)

  log(`Found live listings for ${foundCount}/${toBuy.length} parts${owned.length ? ` · ${owned.length} owned` : ''} · cheapest-legit build ≈ ${cheapestLegitTotal} €`)

  phase('Appraise')

  return await agent(
    `You are assembling the best-value USED gaming/PC-style build for Finland from LIVE Tori.fi + Huuto.net listings.

Request: "${query}"
Platform: ${scope.platform || '(unspecified)'} — ${scope.buildRationale || ''}
Scope: ${scope.interpretation}
${scope.budgetEur ? `Total budget ceiling: ${scope.budgetEur} EUR.` : 'No explicit total budget — target a balanced, non-bottlenecked build and report the total.'}
${scope.regionHint ? `Preferred pickup region: ${scope.regionHint}.` : ''}
${owned.length ? `Parts the user ALREADY OWNS (do not buy; assume present for compatibility): ${owned.map(o => o.label + (o.targetSpec ? ` (${o.targetSpec})` : '')).join(', ')}.` : ''}

Deterministic anchors (already computed — use, do not recompute):
- Cheapest-legit-per-part total ≈ ${cheapestLegitTotal} EUR (a FLOOR; you may pick a slightly pricier listing for better condition/warranty).
${newTotalKnown ? `- Sum of NEW prices for the parts still sold new (${partsWithNew.join(', ')}) ≈ ${newTotalKnown} EUR — use for the used-vs-new saving on those parts.` : '- No new-price references resolved (mostly discontinued parts) — describe the saving qualitatively.'}

Per-part live data (JSON; each part has its fair band, an optional new-price newRef, and up to 8 listings. flag="suspicious-low" = far under the part's median, likely broken/parts/scam — NEVER pick one; "overpriced" = far over; auction=true = live Huuto bid that can still climb):
${JSON.stringify(parts, null, 2)}

On the Finnish used market, loose PC components (CPU, motherboard, RAM, PSU, case) are often scarce — sellers flip WHOLE computers instead. So a part's "listings" may actually be entire PCs that merely CONTAIN that part: treat those as a GAP for the loose part (don't pretend you can buy just the CPU out of a 400 € PC), but DO harvest them for the donor route below.

Assemble the build and pick the better of two routes:
1. **The build (component route)** — pick EXACTLY ONE listing per buyable part: the best VALUE that is (a) a genuine loose part, NOT a whole PC, (b) NOT suspicious-low, and (c) compatible with the other picks and the platform. One line per part: **<Label>** — <title>, **<price> €**, <source>, <location> — <listing URL> · one clause on why. Mark 'optional' parts, list owned parts as "you provide", and mark any part with no loose listing as a **GAP** with its new-price fallback (cite newRef price + retailer).
2. **Donor route** — if several parts are gaps, look in the data for ONE whole used PC on the SAME platform that already bundles most of them (CPU+board+RAM+storage+PSU+case), and add the anchor part to it (swapping/reselling any GPU it already has). Give the donor listing + the anchor listing with URLs.
3. **Total & recommendation** — state the EUR total of BOTH routes (component route = used loose parts + gaps bought new; donor route = donor PC + anchor), the saving vs new for each${newTotalKnown ? ` (the new-covered parts new-sum ≈ ${newTotalKnown} EUR)` : ''}${scope.budgetEur ? `, and whether each fits the ${scope.budgetEur} EUR budget` : ''}, then **recommend the lower coherent total**. If loose parts were plentiful, the component route may simply win — say so.
4. **Compatibility check** — in 2-3 lines confirm the recommended route's picks fit together: CPU socket = motherboard socket, RAM generation matches the board, the PSU has the wattage + PCIe connectors the GPU needs, and the case fits the board form factor + GPU length. For a donor PC, verify its PSU wattage/connectors and case clearance actually accept the anchor GPU. If your picks would MISMATCH, swap to compatible listings from the data and say so.
5. **Watch out** — name any suspicious-low listings you rejected and why, any whole-PC listings you excluded from the component route, and any live auction whose current bid understates the real cost.
6. **Buyer advice** — 1-2 lines specific to used PC parts: stress-test the GPU for artifacts and check for mining wear/repaste, inspect the CPU socket/pins, confirm PSU age (avoid 7+ yr units), and test-boot before paying; meet in person.

Rules: prices are EUR and live. Never invent a listing, price, seller, or URL not in the JSON. Never pick a suspicious-low listing. Keep every pick compatible. Coverage is Tori.fi + Huuto.net only (Facebook Marketplace is not searchable). Be factual and tight — the buyer should know exactly which listings to open and what it totals.`,
    { label: 'assemble-build', phase: 'Appraise' }
  )
}

let newPrice = null
let listings = []

if (scope.mode === 'product') {
  const sq = scope.searchQuery || scope.category
  log(`Hunting "${sq}" across Tori.fi + Huuto.net…`)

  const tasks = [() => huntListings(sq, scope.coreQuery || sq, scope.mustMatch || [], scope.accessoryTerms || [], 'product')]
  if (scope.newPriceQuery) tasks.push(() => newRefAgent(scope.newPriceQuery, `new-ref:${sq}`))

  const [hunted, newRef] = await parallel(tasks)
  listings = hunted || []
  newPrice = newRef && newRef.foundInFinland ? newRef : null

  if (!listings.length) {
    return `No live Tori.fi or Huuto.net listings matched **${scope.category}**.\n\n${scope.interpretation}\n\nThe item may not be for sale used right now — try a broader query, e.g. \`/kaytetty-best ${scope.searchQuery || scope.category}\` without the extra constraints, or search Tori.fi directly.`
  }
} else {
  const candidates = (scope.candidates || []).filter(c => c && c.searchQuery).slice(0, 6)
  if (!candidates.length) return `Couldn't derive candidate models for: "${query}".\n\n${scope.interpretation || ''}`
  log(`Checking the used market for ${candidates.length} candidate model${candidates.length > 1 ? 's' : ''}…`)

  const perModel = await parallel(
    candidates.map(c => () =>
      huntListings(c.searchQuery, c.searchQuery, [], scope.accessoryTerms || [], `cand:${c.model}`).then(ls => ({ model: c, listings: ls }))
    )
  )
  perModel.filter(Boolean).forEach(pm => {
    pm.listings.forEach(l => listings.push({ ...l, model: pm.model.model, tier: pm.model.tier, whyModel: pm.model.why }))
  })
  if (!listings.length) {
    const misses = candidates.map(c => `- ${c.model}`).join('\n')
    return `None of the shortlisted models for **${scope.category}** turned up on Tori.fi or Huuto.net right now.\n\n${scope.interpretation}\n\nChecked:\n${misses}\n\nTry a specific one, e.g. \`/kaytetty-best ${candidates[0].searchQuery}\`.`
  }
}

if (scope.budgetEur) {
  const under = listings.filter(l => l.priceEur == null || l.priceEur <= scope.budgetEur * 1.15)
  if (under.length) listings = under
}

const band = priceBand(listings)
listings = flagOutliers(listings, band).sort((a, b) => (a.priceEur ?? Infinity) - (b.priceEur ?? Infinity))
const forModel = listings.slice(0, 30)

log(`${listings.length} listing${listings.length > 1 ? 's' : ''} found${band ? ` · typical ${band.p25}–${band.p75} € (median ${band.median} €)` : ''}`)

phase('Appraise')

return await agent(
  `You are giving a "best thing to buy SECOND-HAND" recommendation for Finland, grounded in LIVE Tori.fi + Huuto.net listings.

Request: "${query}"
Mode: ${scope.mode === 'product' ? 'a specific item the user wants to buy used — appraise the market and pick the best listing to buy.' : 'an open category — pick the best MODEL to buy used, then the best live listing for it.'}
Scope: ${scope.interpretation}
${scope.budgetEur ? `Budget ceiling: ${scope.budgetEur} EUR.` : 'No explicit budget.'}
${scope.regionHint ? `Preferred pickup region: ${scope.regionHint}.` : ''}
${newPrice ? `New-price reference (for savings math): ${newPrice.cheapestNewEur} EUR new at ${newPrice.retailer} (${newPrice.url}).` : ''}
${band ? `Fair-price band computed from the fixed-price listings: min ${band.min}, 25th ${band.p25}, median ${band.median}, 75th ${band.p75}, max ${band.max} EUR (n=${band.count}).` : 'Too few fixed-price listings to compute a reliable band.'}

Listings with live prices (JSON; flag="suspicious-low" = far under median, likely broken/parts/scam; "overpriced" = far over; auction=true = live Huuto bid, price can still rise):
${JSON.stringify(forModel, null, 2)}

Write a concise markdown recommendation using ONLY these facts:
1. **Top pick** — the best-VALUE listing to actually buy (not merely the cheapest): weigh price vs. condition, warranty (takuu), seller type (a dealer with warranty is safer but pricier; a private seller is cheaper but buyer-beware), location vs. any preferred region, and auction risk. Give title, price EUR, source (Tori/Huuto), location, and the listing URL, plus one line on why it wins.${scope.mode === 'category' ? ' Say which MODEL it is and one line on why that model is the right used pick.' : ''}
2. **Fair price band** — state the typical used range and the median in one line, so the buyer knows what "a good price" is${newPrice ? ', and the saving vs. buying new (used median vs. the new reference, as a % and EUR)' : ''}.
3. **Cheapest legit option** — the lowest-priced listing that is NOT flagged suspicious-low (title, price, source, URL), one line.
4. **Watch out** — call out any flag="suspicious-low" listings as likely scams / broken / parts-only (never recommend buying one), and any live auction whose current bid is deceptively low because it can still climb.
5. One line of buyer advice fit to THIS item (e.g. for a phone: check IMEI / iCloud lock / battery health and meet in person; for a bike: check frame/serial; for furniture: inspect wear) — grounded and short, no boilerplate lecture.
${scope.budgetEur ? `6. Flag anything recommended that sits over the ${scope.budgetEur} EUR budget.\n` : ''}
Rules: prices are EUR and live. Never invent a listing, price, seller, or URL not in the JSON. Never recommend a suspicious-low listing as a buy. Note that coverage is Tori.fi + Huuto.net only (Facebook Marketplace is not searchable). Be factual and tight — the buyer should know exactly which listing to open.`,
  { label: 'appraise', phase: 'Appraise' }
)
