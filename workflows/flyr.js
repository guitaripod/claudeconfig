export const meta = {
  name: 'flyr',
  description: 'Find the cheapest flights by fanning flyr (Google Flights CLI) searches across a window of dates and nearby airports',
  whenToUse: 'When you want the cheapest fare for a trip and date flexibility matters — e.g. "/flyr cheap one-way HEL to ICN in September" or "/flyr return HEL→BKK around 2026-09-10 for ~2 weeks, business".',
  phases: [
    { title: 'Plan', detail: 'parse the request into an explicit date grid + airport set' },
    { title: 'Search', detail: 'one flyr search per date / date-pair, in parallel', model: 'claude-haiku-4-5-20251001' },
    { title: 'Rank', detail: 'collate fares, surface the cheapest options' },
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
    'Usage: `/flyr <where and when>`',
    '',
    'Examples:',
    '- `/flyr cheap one-way HEL to ICN in September`',
    '- `/flyr return HEL→BKK around 2026-09-10 for ~2 weeks, business`',
    '- `/flyr LAX to Tokyo, leave 2026-05-01 ±3 days, nonstop`',
  ].join('\n')
}

const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    from: { type: 'string', description: '3-letter IATA origin' },
    to: {
      type: 'array',
      items: { type: 'string' },
      description: '3-letter IATA destination codes (target + sensible nearby alternates), max 3',
    },
    tripType: { type: 'string', enum: ['one-way', 'round-trip'] },
    seat: { type: 'string', enum: ['economy', 'premium-economy', 'business', 'first'] },
    currency: { type: 'string' },
    adults: { type: 'integer' },
    maxStops: { type: ['integer', 'null'] },
    airlines: { type: ['string', 'null'], description: 'comma-separated IATA airline codes, or null' },
    searches: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          date: { type: 'string', description: 'YYYY-MM-DD departure date' },
          returnDate: { type: ['string', 'null'], description: 'YYYY-MM-DD return date, or null for one-way' },
        },
        required: ['date', 'returnDate'],
      },
    },
    interpretation: { type: 'string' },
  },
  required: ['from', 'to', 'tripType', 'seat', 'currency', 'adults', 'maxStops', 'airlines', 'searches', 'interpretation'],
}

phase('Plan')

const plan = await agent(
  `You are planning a flight-price search. Convert this request into a concrete search grid.

Request: "${query}"

First run \`date +%F\` (Bash) to get today's date, and resolve every relative date ("next month", "September", "in 3 weeks", "this weekend") against it. NEVER search a past date.

Rules:
- Origin: if no origin is given, default to HEL (Helsinki).
- Destination(s): the user's target plus sensible nearby alternates in the same metro, served as comma-separated codes — e.g. Seoul → ICN,GMP; London → LHR,LGW,STN; Tokyo → NRT,HND; Bangkok → BKK,DMK; New York → JFK,EWR,LGA. Cap at 3 codes total. If the user gave an explicit IATA code, you may still add one obvious alternate.
- Defaults: currency EUR, seat economy, adults 1, maxStops null (any), airlines null.
- tripType: round-trip if a return date / "for N weeks" / "round trip" is implied, else one-way.
- Build an explicit "searches" grid that exploits date flexibility (the single biggest lever on price):
  * Exact date given → that date plus and minus a few days (~7 points for one-way).
  * Month or vague window → sample dates spread evenly across it (every 2–3 days), up to ~12 points.
  * Round-trip with a trip length (e.g. "~2 weeks") → pair each departure date with departure+length as returnDate.
  * Round-trip with a fixed return window → a small grid of (depart, return) pairs.
  * Cap the grid at 12 searches UNLESS the user explicitly asks to be exhaustive/thorough — then up to 24.
- Every search entry must be { "date": "YYYY-MM-DD", "returnDate": "YYYY-MM-DD" or null }. For one-way, returnDate is null on every entry.

Set "interpretation" to one plain-English sentence: origin → destinations, window, trip type, cabin, pax, currency.`,
  { label: 'plan', phase: 'Plan', schema: PLAN_SCHEMA }
)

const searches = (plan.searches || []).filter(s => s && s.date).slice(0, 24)
if (!searches.length) {
  return `Couldn't derive any dates to search from: "${query}".\n\n${plan.interpretation || ''}`
}

const toArg = plan.to.join(',')
log(`Plan: ${plan.interpretation}`)
log(`Searching ${searches.length} date${searches.length > 1 ? 's' : ''} · ${plan.from} → ${toArg} · ${plan.tripType} · ${plan.seat} · ${plan.currency}`)

function buildCmd(s) {
  const parts = [
    'flyr search',
    `-f ${plan.from}`,
    `-t ${toArg}`,
    `-d ${s.date}`,
    `--seat ${plan.seat}`,
    `--currency ${plan.currency}`,
    `--adults ${plan.adults || 1}`,
    '--json --top 3 --timeout 45',
  ]
  if (s.returnDate) parts.push(`--return-date ${s.returnDate}`)
  if (plan.maxStops !== null && plan.maxStops !== undefined) parts.push(`--max-stops ${plan.maxStops}`)
  if (plan.airlines) parts.push(`--airlines ${plan.airlines}`)
  return parts.join(' ')
}

const FARE_SCHEMA = {
  type: 'object',
  properties: {
    fares: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          price: { type: 'number' },
          currency: { type: 'string' },
          destination: { type: 'string', description: 'final outbound airport IATA code' },
          airlines: { type: 'string' },
          stops: { type: 'integer', description: 'outbound stops = outbound segments - 1' },
          departDate: { type: 'string' },
          returnDate: { type: ['string', 'null'] },
          departTime: { type: 'string', description: 'HH:MM' },
          arriveTime: { type: 'string', description: 'HH:MM' },
          durationHours: { type: 'number' },
          itinerary: { type: 'string' },
        },
        required: ['price', 'currency', 'destination', 'airlines', 'stops', 'departDate', 'returnDate', 'itinerary'],
      },
    },
    error: { type: ['string', 'null'] },
  },
  required: ['fares', 'error'],
}

phase('Search')

const batches = await parallel(
  searches.map(s => () =>
    agent(
      `Run EXACTLY this command (it queries Google Flights) and parse its JSON stdout:

\`\`\`
${buildCmd(s)}
\`\`\`

The JSON has a top-level "flights" array, already cheapest-first. Each flight object:
- "price": number, "airlines": array of airline names.
- "segments": array of legs. Each segment has "from_airport".code, "to_airport".code, "departure" and "arrival" objects ({year,month,day,hour,minute}), and "duration_minutes".

The OUTBOUND journey is the run of segments from "${plan.from}" up to and including the first segment whose to_airport.code is one of [${plan.to.join(', ')}]. ${plan.tripType === 'round-trip' ? 'Segments after that are the return leg — IGNORE them for stops/times/duration. "price" is the TOTAL round-trip price; keep it as-is.' : 'There is no return leg.'}

Return up to the 3 cheapest fares. For each:
- price (number), currency = "${plan.currency}".
- destination = the outbound final to_airport.code.
- airlines = the airline names joined with " + ".
- stops = (outbound segment count) - 1.
- departDate = "${s.date}", returnDate = ${s.returnDate ? `"${s.returnDate}"` : 'null'}.
- departTime = first outbound segment's departure as "HH:MM" (zero-padded), arriveTime = outbound final segment's arrival as "HH:MM".
- durationHours = sum of outbound segments' duration_minutes / 60, rounded to 1 decimal (this is air time; it's fine if it omits layovers).
- itinerary = compact string like "HEL→IST→ICN · 1 stop · 19.7h · Turkish Airlines".

If the command errors, times out, or returns zero flights, return an empty "fares" array and put a one-line reason in "error". NEVER invent fares or prices — only report what the command actually returned.`,
      {
        label: `search:${plan.from}→${toArg}@${s.date}${s.returnDate ? '/' + s.returnDate : ''}`,
        phase: 'Search',
        schema: FARE_SCHEMA,
        model: 'claude-haiku-4-5-20251001',
      }
    )
  )
)

const allFares = batches.filter(Boolean).flatMap(b => (Array.isArray(b.fares) ? b.fares : []))

if (!allFares.length) {
  const errs = [...new Set(batches.filter(Boolean).map(b => b.error).filter(Boolean))].slice(0, 3)
  return (
    `No fares found for ${plan.from} → ${toArg} across ${searches.length} date(s).` +
    (errs.length ? `\n\nflyr reported:\n- ${errs.join('\n- ')}` : '\n\nThe searches returned nothing — try a different window or broaden the airports.')
  )
}

phase('Rank')

const sorted = [...allFares].sort((a, b) => a.price - b.price)
const seen = new Set()
const unique = sorted.filter(f => {
  const k = `${f.price}|${f.itinerary}|${f.departDate}|${f.returnDate || ''}`
  if (seen.has(k)) return false
  seen.add(k)
  return true
})
const top = unique.slice(0, 8)
const cheapest = unique[0]

const openCmd = (() => {
  const parts = [
    'flyr search',
    `-f ${plan.from}`,
    `-t ${cheapest.destination}`,
    `-d ${cheapest.departDate}`,
    `--seat ${plan.seat}`,
    `--currency ${plan.currency}`,
  ]
  if (cheapest.returnDate) parts.push(`--return-date ${cheapest.returnDate}`)
  parts.push('--open')
  return parts.join(' ')
})()

return await agent(
  `You searched flights for the request: "${query}".
Interpretation: ${plan.interpretation}
Scanned ${searches.length} departure date(s) across ${plan.from} → ${toArg}.

Fares found (already deduped and sorted cheapest-first), JSON:
${JSON.stringify(top, null, 2)}

Write a concise markdown answer for the user using ONLY these fares:
1. **Headline**: the cheapest fare — price + ${plan.currency}, route, date(s), airline, stops, total duration.
2. A list of up to 5 best options. Each line: **<price> ${plan.currency}** — route · N stop(s) · ~Xh · airline · departs <date>${cheapest.returnDate ? ', returns <date>' : ''} · <departTime>→<arriveTime>.
3. One line of judgment: is the cheapest also the best value, or does a slightly pricier option win on much shorter time / fewer stops? If a particular departure date is clearly cheaper, say so — flexibility is the main lever.
4. Final line, verbatim: To open it in Google Flights: \`${openCmd}\`

Be factual and tight. Currency is ${plan.currency}. Do not add fares that aren't in the JSON.`,
  { label: 'rank', phase: 'Rank' }
)
