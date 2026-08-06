export const meta = {
  name: 'verdict',
  description:
    'Find the consensus on a piece of media — game, movie, show, album or book — by fusing live critic scores (OpenCritic, Metacritic, Rotten Tomatoes, Album of the Year, Pitchfork) with audience scores (Steam, IMDb, Letterboxd, Goodreads, OpenLibrary), and present it as a beautiful ASCII verdict card',
  whenToUse:
    'When you want "is it actually good?" answered with real numbers and a clear verdict — e.g. "/verdict elden ring", "/verdict dune part two", "/verdict the bear", "/verdict chromakopia", "/verdict project hail mary". Also for "what should I play/watch/read next" style questions about a named title.',
  phases: [
    { title: 'Scope', detail: 'identify the media, its kind, and the canonical title/year/creator' },
    { title: 'Evidence', detail: 'pull critic + audience + acclaim data from live sources in parallel', model: 'claude-haiku-4-5-20251001' },
    { title: 'Verdict', detail: 'compute the consensus and render the ASCII verdict card' },
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
    'Usage: `/verdict <title> [context]`',
    '',
    'Examples:',
    '- `/verdict elden ring`',
    '- `/verdict dune part two`',
    '- `/verdict the bear (2022)`',
    '- `/verdict chromakopia tyler the creator`',
    '- `/verdict project hail mary`',
    '',
    'Works for games, movies, TV shows, albums and books. Add a year or artist when the title is ambiguous.',
  ].join('\n')
}

const SCOPE_SCHEMA = {
  type: 'object',
  properties: {
    kind: {
      type: 'string',
      enum: ['game', 'movie', 'show', 'album', 'book'],
      description: 'the media kind: game, movie (film), show (TV series), album, or book',
    },
    title: { type: 'string', description: 'canonical title, e.g. "Elden Ring"' },
    creator: { type: 'string', description: 'game studio / director / artist / author, e.g. "FromSoftware", "Denis Villeneuve"' },
    year: { type: ['string', 'null'], description: 'release year as a string if it disambiguates, else null' },
    platform: { type: ['string', 'null'], description: 'games only: the primary platform to price/score (PC, PS5, Xbox…), else null' },
    identity: { type: 'string', description: 'one line: the exact canonical identity we are scoring, with the year so agents pick the right entry' },
  },
  required: ['kind', 'title', 'creator', 'year', 'platform', 'identity'],
}

phase('Scope')

const scope = await agent(
  `You are identifying a piece of media so its consensus scores can be fetched from live sources.

Request: "${query}"

First run \`date +%F\` (Bash) for today's date; media with similar titles (remakes, sequels, re-releases) need the right year to disambiguate.

Return the kind (game/movie/show/album/book), the canonical title, the creator (studio for games, director for films, artist for albums, author for books — best-known name, e.g. "FromSoftware", "Villeneuve", "Tyler, the Creator"), the release year (string, null if truly unknown), the platform for games only (the main platform, e.g. "PC", "PS5"; null otherwise), and a one-line identity statement that pins down the exact entry ("Elden Ring (2022), base game not the DLC", "Dune: Part Two (2024), the Villeneuve film"). Prefer the most-searched/canonical entry when ambiguous — e.g. a film named the same as a book is the film unless the request clearly means the book.`,
  { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA }
)

log(`Verdict on ${scope.identity}`)

const SOURCE_SCHEMA = {
  type: 'object',
  properties: {
    sources: {
      type: 'array',
      description: 'each live source with its normalized 0-100 score; only sources you actually found data for',
      items: {
        type: 'object',
        properties: {
          key: {
            type: 'string',
            enum: ['opencritic', 'metacriticCritic', 'metacriticUser', 'steam', 'rtCritics', 'rtAudience', 'imdb', 'letterboxd', 'aoty', 'aotyUser', 'pitchfork', 'goodreads', 'openlibrary'],
          },
          found: { type: 'boolean', description: 'true only if you actually retrieved a real score for this source' },
          score100: { type: ['number', 'null'], description: 'normalized 0-100, or null if not found' },
          raw: { type: ['string', 'null'], description: 'the score exactly as displayed, e.g. "8.5/10", "97%", "4.21/5"' },
          sampleSize: { type: ['integer', 'null'], description: 'review/rating count if visible, else null' },
          url: { type: ['string', 'null'], description: 'the page the score came from' },
          note: { type: ['string', 'null'] },
        },
        required: ['key', 'found', 'score100', 'raw', 'sampleSize', 'url', 'note'],
      },
    },
    error: { type: ['string', 'null'] },
  },
  required: ['sources', 'error'],
}

const ACCLAIM_SCHEMA = {
  type: 'object',
  properties: {
    awards: { type: 'array', description: 'the 2-4 most significant wins (not minor nominations), e.g. "TGA Game of the Year 2022", "Best Picture Oscar 2024"', items: { type: 'string' } },
    praise: { type: ['string', 'null'], description: 'one line: what critics most consistently praise' },
    criticism: { type: ['string', 'null'], description: 'one line: what people most consistently criticize, null if nothing meaningful' },
  },
  required: ['awards', 'praise', 'criticism'],
}

const enc = s => encodeURIComponent(String(s || '').trim())

const fetchRecipes = {
  game: {
    critics: `CRITIC SOURCES for the game "${scope.identity}":
1. OpenCritic — run: curl -s "https://opencritic-api.p.datacamp.com/game/search?criteria=${enc(scope.title)}" (if that fails, try https://api.opencritic.com/game/search?criteria=${enc(scope.title)}, then WebFetch https://opencritic.com/browse/all?search=${enc(scope.title)} with an extraction prompt). It returns games with id, name, criticScore (0-100), firstReleaseDate. Pick the entry matching the identity (right title + year); report criticScore as score100 with url https://opencritic.com/game/<id>/<slug>.
2. Metacritic critic — WebSearch "metacritic ${scope.title} ${scope.year || ''} critic reviews". The search results show the Metascore (e.g. "Metascore 96", "Based on 95 Critic Reviews"). Only report a number you actually see attributed to Metacritic; url https://www.metacritic.com/game/<slug>.`,
    users: `AUDIENCE SOURCES for the game "${scope.identity}":
1. Steam — run: curl -s "https://store.steampowered.com/api/storesearch/?term=${enc(scope.title)}&l=en&cc=US" → items [{id, name}]. Pick the matching base game (right title; skip DLC/editions). Then run: curl -s "https://store.steampowered.com/appreviews/<appid>?json=1&language=all&purchase_type=all&num_per_page=0" → query_summary {total_positive, total_negative}. score100 = total_positive/(total_positive+total_negative)*100, sampleSize = their sum, url https://store.steampowered.com/app/<appid>. If the game is not on Steam, found=false.
2. Metacritic users — WebSearch "metacritic ${scope.title} ${scope.year || ''} user score" → "User Score 7.4" → score100 = value*10; sampleSize from "Rated by N Users" if visible.`,
  },
  movie: {
    critics: `CRITIC SOURCES for the film "${scope.identity}":
1. Rotten Tomatoes — WebSearch "rottentomatoes ${scope.title} ${scope.year || ''}" to find the film's page url (https://www.rottentomatoes.com/m/<slug>), then WebFetch that page with extraction prompt: "Extract from this page: the tomatometer percentage (critics), the top-critics percentage, and the audience percentage. Return numbers only." Report the tomatometer as rtCritics score100 (url = the page).
2. Metacritic critic — WebSearch "metacritic ${scope.title} ${scope.year || ''} metascore" → the Metascore, only if actually seen.`,
    users: `AUDIENCE SOURCES for the film "${scope.identity}":
1. RT audience — WebSearch "rottentomatoes ${scope.title} ${scope.year || ''}" → the film's page url, WebFetch it with extraction prompt "Extract the audience percentage from this page." → rtAudience score100.
2. IMDb — WebSearch "imdb ${scope.title} ${scope.year || ''} rating" → the search results show the rating (e.g. "IMDb 8.8/10" or "8.8/10 (1.4M)"). score100 = rating*10; sampleSize = votes if visible. If the film is too obscure to have an IMDb rating, found=false.
3. Letterboxd — WebFetch "https://letterboxd.com/search/films/${enc(scope.title)}/" with an extraction prompt "List the top matching films with their URLs and average ratings." Pick the right film, WebFetch its page, extract the average rating (e.g. "4.08") and the rating count. score100 = rating*20; sampleSize = count; url = the film page.`,
  },
  album: {
    critics: `CRITIC SOURCES for the album "${scope.identity}":
1. Album of the Year — WebFetch "https://www.albumoftheyear.org/search.php?q=${enc(`${scope.creator} ${scope.title}`)}" with extraction prompt "List the matching albums with their URLs and overall scores." Pick the right album page, WebFetch it, extract the "Overall" score (critic average, 0-100) → aoty score100, url = the album page.
2. Metacritic critic — WebSearch "metacritic ${scope.title} ${scope.creator}" → the Metascore if actually seen.
3. Pitchfork — WebSearch "pitchfork review ${scope.title} ${scope.creator}" → their score (e.g. "Pitchfork: 8.5") → score100 = value*10. If no Pitchfork review exists, found=false.`,
    users: `AUDIENCE SOURCES for the album "${scope.identity}":
1. AOTY user score — on the same album page found via WebFetch "https://www.albumoftheyear.org/search.php?q=${enc(`${scope.creator} ${scope.title}`)}", extract the "User Score" (0-100) → aotyUser score100, url = the album page.`,
  },
  book: {
    critics: null,
    users: `AUDIENCE SOURCES for the book "${scope.identity}":
1. Goodreads — WebFetch "https://www.goodreads.com/search?q=${enc(scope.title)}" with extraction prompt "List the top matching books with their URLs, average ratings and rating counts." Pick the right edition/work (right title + author), WebFetch its page, extract "avg rating" (e.g. 4.21) and "ratings" (e.g. 3,456,789). score100 = rating*20; sampleSize = count; url = the book page.
2. OpenLibrary — run: curl -s "https://openlibrary.org/search.json?title=${enc(scope.title)}&fields=title,author_name,first_publish_year,ratings_average,ratings_count" → pick the entry with the right title+author and ratings_count>0 → score100 = ratings_average*20, sampleSize = ratings_count, url = https://openlibrary.org/search?title=${enc(scope.title)}.`,
  },
}

const kindMeta = kind => {
  if (kind === 'game') return { label: 'Video Game', weights: { opencritic: 0.35, metacriticCritic: 0.25, steam: 0.25, metacriticUser: 0.15 }, critics: ['opencritic', 'metacriticCritic'], users: ['steam', 'metacriticUser'] }
  if (kind === 'movie' || kind === 'show') return { label: kind === 'movie' ? 'Film' : 'TV Series', weights: { rtCritics: 0.3, metacriticCritic: 0.2, imdb: 0.2, rtAudience: 0.15, letterboxd: 0.15 }, critics: ['rtCritics', 'metacriticCritic'], users: ['imdb', 'rtAudience', 'letterboxd'] }
  if (kind === 'album') return { label: 'Album', weights: { metacriticCritic: 0.4, aoty: 0.3, aotyUser: 0.2, pitchfork: 0.1 }, critics: ['metacriticCritic', 'aoty', 'pitchfork'], users: ['aotyUser'] }
  return { label: 'Book', weights: { goodreads: 0.6, openlibrary: 0.4 }, critics: [], users: ['goodreads', 'openlibrary'] }
}

phase('Evidence')

const meta = kindMeta(scope.kind)

const sourceAgents = []
if (fetchRecipes[scope.kind].critics) {
  sourceAgents.push(() =>
    agent(
      `Fetch LIVE consensus scores for a piece of media. Never guess or invent a score — if a source cannot be reached or shows nothing, found=false with a one-line note.

Identity being scored: ${scope.identity} (${scope.kind}).

${fetchRecipes[scope.kind].critics}

Return one entry per source you tried, found=true only with a real score. Normalize everything to score100 (0-100): percentages pass through, 0-10 ratings ×10, 0-5 ratings ×20. Round to integers.`,
      { label: 'critics', phase: 'Evidence', schema: SOURCE_SCHEMA, model: 'claude-haiku-4-5-20251001' }
    )
  )
}
sourceAgents.push(() =>
  agent(
    `Fetch LIVE audience/player consensus scores for a piece of media. Never guess or invent a score — if a source cannot be reached or shows nothing, found=false with a one-line note.

Identity being scored: ${scope.identity} (${scope.kind}).

${fetchRecipes[scope.kind].users}

Return one entry per source you tried, found=true only with a real score. Normalize everything to score100 (0-100): percentages pass through, 0-10 ratings ×10, 0-5 ratings ×20. Round to integers.`,
    { label: 'users', phase: 'Evidence', schema: SOURCE_SCHEMA, model: 'claude-haiku-4-5-20251001' }
  )
)
sourceAgents.push(() =>
  agent(
    `Find the acclaim and buzz around a piece of media. Identity: ${scope.identity} (${scope.kind}).

WebSearch for its most significant awards:
- game: "GOTY awards ${scope.title}" — TGA / BAFTA / GDC / DICE game-of-the-year wins.
- movie: "oscars golden globes bafta ${scope.title}" — wins only, e.g. "Best Picture Oscar 2024".
- show: "emmys ${scope.title}" — Outstanding Series/limited wins.
- album: "grammy ${scope.title}" — Album of the Year / Best New Artist wins.
- book: "${scope.title} awards" — Booker / Hugo / Nebula / National Book Award wins.
Include at most 4, only real wins you can attribute, in the form "TGA Game of the Year 2022". If nothing notable, return an empty array.

Then distill, from what reviewers/readers actually say in the search snippets: praise = one line on what is most consistently praised; criticism = one line on what is most consistently criticized (null if there is none). Be concrete, not generic ("deep combat, brutal difficulty and a staggeringly dense world", not "it is good").`,
    { label: 'acclaim', phase: 'Evidence', schema: ACCLAIM_SCHEMA, model: 'claude-haiku-4-5-20251001' }
  )
)

const [criticsRes, usersRes, acclaim] = await parallel(sourceAgents)

const byKey = {}
for (const res of [criticsRes, usersRes]) {
  if (!res || !Array.isArray(res.sources)) continue
  for (const s of res.sources) {
    if (!s || !s.found || s.score100 == null) continue
    const v = Number(s.score100)
    if (!Number.isFinite(v) || v < 0 || v > 100) continue
    if (s.sampleSize === 0) continue
    if (!meta.weights[s.key]) continue
    byKey[s.key] = { score: v, raw: s.raw ?? null, sampleSize: s.sampleSize ?? null, url: s.url ?? null, note: s.note ?? null }
  }
}

const keys = Object.keys(byKey)
if (!keys.length) {
  return `Couldn't reach any score source for **${scope.identity}**.\n\n${criticsRes?.error ? `Critic sources: ${criticsRes.error}` : ''}${usersRes?.error ? `\nAudience sources: ${usersRes.error}` : ''}\n\nTry again later, or check the title is right — \`/verdict ${query}\` (add a year/artist if ambiguous).`
}

const totalW = keys.reduce((s, k) => s + meta.weights[k], 0)
const consensus = Math.round(keys.reduce((s, k) => s + byKey[k].score * meta.weights[k], 0) / totalW)
const weightedMean = arr => {
  const ws = arr.map(k => meta.weights[k])
  const tw = ws.reduce((a, b) => a + b, 0)
  return arr.reduce((s, k, i) => s + byKey[k].score * ws[i], 0) / tw
}

const criticKeys = keys.filter(k => meta.critics.includes(k))
const userKeys = keys.filter(k => meta.users.includes(k))
const criticAvg = criticKeys.length ? Math.round(weightedMean(criticKeys) * 10) / 10 : null
const userAvg = userKeys.length ? Math.round(weightedMean(userKeys) * 10) / 10 : null
let gap = null
let agreement = null
if (criticAvg != null && userAvg != null) {
  gap = Math.round(Math.abs(criticAvg - userAvg) * 10) / 10
  agreement = gap < 4 ? 'UNANIMOUS' : gap < 10 ? 'ALIGNED' : gap < 18 ? 'DIVIDED' : 'POLARIZED'
}

const verdict =
  consensus >= 90 ? 'MASTERPIECE' : consensus >= 85 ? 'ESSENTIAL' : consensus >= 78 ? 'EXCELLENT' : consensus >= 70 ? 'GOOD' : consensus >= 60 ? 'MIXED' : consensus >= 45 ? 'WEAK' : 'POOR'

const compact = n => (n == null ? null : n >= 1e6 ? (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'k' : String(n))
const stars = s => {
  const full = Math.max(0, Math.min(5, Math.round(s / 20)))
  return '★'.repeat(full) + '☆'.repeat(5 - full)
}
const bar = (score, width) => {
  const unit = 100 / width
  const full = Math.floor(score / unit)
  const rem = score - full * unit
  const half = rem >= unit / 2 ? 1 : 0
  return '█'.repeat(full) + (half ? '▌' : '') + '░'.repeat(width - full - half)
}

const SRC_NAMES = {
  opencritic: 'OpenCritic',
  metacriticCritic: 'Metacritic',
  metacriticUser: 'Metacritic Users',
  steam: 'Steam',
  rtCritics: 'RT Critics',
  rtAudience: 'RT Audience',
  imdb: 'IMDb',
  letterboxd: 'Letterboxd',
  aoty: 'AOTY',
  aotyUser: 'AOTY Users',
  pitchfork: 'Pitchfork',
  goodreads: 'Goodreads',
  openlibrary: 'OpenLibrary',
}

function renderCard() {
  const meta_ = meta
  const lines = []
  const titleLine = `${(scope.title || 'Media').toUpperCase()}${scope.year ? ` (${scope.year})` : ''}`
  const sub = [scope.creator, meta_.label, scope.platform].filter(Boolean).join(' · ')
  lines.push(titleLine)
  if (sub) lines.push(sub)
  lines.push('─'.repeat(1))
  const left = `${stars(consensus)}  CONSENSUS ${consensus}/100`
  const bigBar = `[${bar(consensus, 30)}] ${consensus}%`
  lines.push(`${left}   ${verdict}`)
  lines.push(bigBar)
  lines.push('─'.repeat(1))
  const row = k => {
    const d = byKey[k]
    const sample = compact(d.sampleSize)
    return `${(SRC_NAMES[k] || k).padEnd(17)}${String(Math.round(d.score)).padStart(3)}  ${bar(d.score, 22)}${sample ? `  n=${sample}` : ''}`
  }
  if (criticKeys.length) {
    lines.push('CRITICS')
    criticKeys.forEach(k => lines.push(row(k)))
  }
  if (userKeys.length) {
    if (criticKeys.length) lines.push('')
    lines.push(agreement || criticKeys.length ? 'PLAYERS' : 'READERS')
    userKeys.forEach(k => lines.push(row(k)))
  }
  lines.push('─'.repeat(1))
  if (criticAvg != null && userAvg != null && agreement) {
    lines.push(`Critics ${criticAvg} · Players ${userAvg} · gap ${gap} → ${agreement}`)
  } else if (criticAvg != null) {
    lines.push(`Critics-only consensus (no player source available)`)
  } else if (userAvg != null) {
    lines.push(`Reader consensus · no critic-score aggregator covers this`)
  }
  if (acclaim && Array.isArray(acclaim.awards) && acclaim.awards.length) lines.push(acclaim.awards.slice(0, 3).join(' · '))
  const praise = acclaim && acclaim.praise ? `"${acclaim.praise}"` : null
  if (praise) lines.push(praise)

  const w = Math.max(...lines.map(l => l.length)) + 4
  const contentW = w - 4
  const row_ = l => `│ ${l.padEnd(contentW)} │`
  const out = []
  out.push('┌' + '─'.repeat(w - 2) + '┐')
  lines.forEach(l => out.push(row_(l)))
  out.push('└' + '─'.repeat(w - 2) + '┘')
  return out.join('\n')
}

const card = renderCard()

log(`${consensus}/100 ${verdict} · ${criticKeys.length} critic + ${userKeys.length} player source(s) · ${agreement ? agreement.toLowerCase() : 'no gap'}`)

phase('Verdict')

return await agent(
  `You are presenting the consensus verdict on a piece of media. The scores below are LIVE — never alter them.

Identity: ${scope.identity}
Consensus: ${consensus}/100 → ${verdict}
${criticAvg != null && userAvg != null ? `Critic avg ${criticAvg} vs player avg ${userAvg} (gap ${gap}) → ${agreement} — ${agreement === 'UNANIMOUS' ? 'critics and players fully agree' : agreement === 'ALIGNED' ? 'critics and players broadly agree' : agreement === 'DIVIDED' ? 'players are noticeably harsher/nicer than critics' : 'critics and players strongly disagree'}` : ''}
${criticKeys.length ? `Critic sources: ${criticKeys.map(k => `${SRC_NAMES[k]} ${Math.round(byKey[k].score)}${byKey[k].raw ? ` (${byKey[k].raw})` : ''}`).join(', ')}` : ''}
${userKeys.length ? `Player sources: ${userKeys.map(k => `${SRC_NAMES[k]} ${Math.round(byKey[k].score)}${byKey[k].raw ? ` (${byKey[k].raw})` : ''}${byKey[k].sampleSize ? ` · n=${compact(byKey[k].sampleSize)}` : ''}`).join(', ')}` : ''}
${acclaim && acclaim.praise ? `What critics say: ${acclaim.praise}` : ''}${acclaim && acclaim.criticism ? `\nWhat people criticize: ${acclaim.criticism}` : ''}

Your reply MUST begin with this verdict card in a fenced code block, reproduced EXACTLY character-for-character (keep every │ ─ █ ░ ★ ☆ and every space — do not re-format, re-align, or trim it):

${card}

After the card, no headers, at most 5 short lines:
1. One line: what this is (title, kind, creator, year) in plain words.
2. The consensus: one line — where the score comes from (which sources, how many reviews/ratings), and what the critic-vs-player split says (or that it is reader-only). Use the gap: unanimous/aligned/divided/polarized.
3. What people praise — one line, concrete.
4. What people criticize — one line if there is anything meaningful, else omit.
5. Who it's for / who should skip it — one line each if you can infer it from the split and buzz (e.g. "for genre die-hards; skip if you want a short game").

Rules: never invent or round differently a score that is in the card; never add sources that are not in the card; keep the whole reply tight — the card does the showing, the text only explains.`,
  { label: 'verdict', phase: 'Verdict' }
)
