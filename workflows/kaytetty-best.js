export const meta = {
  name: 'kaytetty-best',
  description:
    'Recommend the best USED-market buy in Finland — a specific thing to buy second-hand, or the best used model in a category — priced live across Tori.fi and Huuto.net, with a fair-price band and scam / overprice flags',
  whenToUse:
    'When you want a "what should I buy second-hand" answer checked against live Finnish used listings. Two modes, auto-detected: a SPECIFIC thing you have decided to buy used ("/kaytetty-best iphone 13 128gb", "/kaytetty-best rtx 3080", "/kaytetty-best herman miller aeron") finds the best-value live listing plus the fair price band and flags the scams; an OPEN category ("/kaytetty-best good used road bike under 800", "/kaytetty-best cheap used oled tv") shortlists models then checks what is actually for sale used right now.',
  phases: [
    { title: 'Scope', detail: 'classify the request and build the used-market search plan' },
    { title: 'Hunt', detail: 'pull live listings from Tori.fi + Huuto.net (+ new-price reference)', model: 'claude-haiku-4-5-20251001' },
    { title: 'Appraise', detail: 'compute the fair band, flag scams, pick the best-value listing' },
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
    'Sources: Tori.fi + Huuto.net (Facebook Marketplace needs a login and is not searchable).',
  ].join('\n')
}

const SCOPE_SCHEMA = {
  type: 'object',
  properties: {
    mode: {
      type: 'string',
      enum: ['product', 'category'],
      description:
        "'product' if the request already names ONE specific thing the user has decided to buy used (e.g. 'iphone 13 128gb', 'rtx 3080', 'herman miller aeron', 'canon 6d'). 'category' if it is an open 'what used thing is best' question (e.g. 'good used road bike under 800', 'cheap used oled tv') — then we shortlist competing models and check each on the used market.",
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
  },
  required: ['mode', 'category', 'interpretation', 'searchQuery', 'coreQuery', 'mustMatch', 'accessoryTerms', 'budgetEur', 'regionHint', 'newPriceQuery', 'candidates'],
}

phase('Scope')

const scope = await agent(
  `You are scoping a "best thing to buy SECOND-HAND in Finland" request, to be priced against LIVE listings on Tori.fi (general classifieds) and Huuto.net (auctions + buy-now).

Request: "${query}"

First run \`date +%F\` (Bash) for today's date; the used market and what is desirable move fast, so treat training knowledge as possibly stale.

Decide the MODE:
- 'product' — the request already names ONE specific thing to buy used (e.g. "iphone 13 128gb", "rtx 3080", "herman miller aeron"). Set 'searchQuery' to the short exact string a used marketplace would match, and 'coreQuery' to the broadest core words that still name it with capacity/colour/spec qualifiers dropped (searchQuery "iphone 13 128gb" -> coreQuery "iphone 13") — some engines match all words strictly, so a specific query returns nothing and the broad one is filtered down later. Set 'mustMatch' to the defining tokens (model + capacity/size) and 'accessoryTerms' to the noise terms to drop (cases/screens/chargers/cables for a phone, etc.). Leave 'candidates' empty. If the item is electronics that new-goods shops carry, set 'newPriceQuery' so we can show the used-vs-new saving; else null.
- 'category' — an open "what used thing is best" question (e.g. "good used road bike under 800", "cheap used oled tv"). Use WebSearch to find the CURRENT well-regarded picks as of today, then set 'candidates' to 4-6 concrete, currently-buyable-used models spanning tiers. Each 'model' is an EXACT name incl. defining size/spec, each 'searchQuery' a short used-market string. Leave 'searchQuery'/'coreQuery'/'newPriceQuery' null.

For both: respect hard constraints. Set 'budgetEur' to the user's max (else null) and 'regionHint' to a preferred Finnish city/region for pickup if the user named one (else null). 'category' = normalized name, 'interpretation' = one sentence.`,
  { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA }
)

log(`${scope.mode === 'product' ? 'Product' : 'Category'}: ${scope.interpretation}`)

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

phase('Hunt')

let newPrice = null
let listings = []

if (scope.mode === 'product') {
  const sq = scope.searchQuery || scope.category
  log(`Hunting "${sq}" across Tori.fi + Huuto.net…`)

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

  const tasks = [() => huntListings(sq, scope.coreQuery || sq, scope.mustMatch || [], scope.accessoryTerms || [], 'product')]
  if (scope.newPriceQuery) {
    tasks.push(() =>
      agent(
        `Run EXACTLY this command (new-goods price across Finnish electronics retailers) and parse its JSON stdout:

\`\`\`
hinta compare "${String(scope.newPriceQuery).replace(/"/g, '\\"')}" --enrich --devices-only --json
\`\`\`

It returns a "groups" array; each group has "attributes" (brand, capacity_gb…) and "offers" [{ source, price_euro, in_stock, url }] cheapest first. Pick the ONE group that best matches "${scope.newPriceQuery}" (right capacity/variant, plain not bundle). Report the cheapest in-stock offer as the NEW reference price: foundInFinland, cheapestNewEur, retailer, url. If the command errors or nothing matches, foundInFinland=false and the rest null. NEVER invent a price.`,
        { label: `new-ref:${sq}`, phase: 'Hunt', schema: NEW_SCHEMA, model: 'claude-haiku-4-5-20251001' }
      )
    )
  }

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
