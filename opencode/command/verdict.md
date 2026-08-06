---
description: Consensus verdict on a piece of media — game, movie, show, album or book — fusing live critic and audience scores into one score and a beautiful ASCII verdict card
---

Render a consensus verdict card for the media in "$ARGUMENTS".

First run `date +%F` (Bash). Classify the media: kind (game/movie/show/album/book), canonical title, creator (studio/director/artist/author), release year, and platform for games. If the title is ambiguous (remake, sequel, same name as a book), use WebSearch to pin the exact entry — score the right one.

## Gather LIVE scores — never invent one; skip a source you cannot reach

- **game**: OpenCritic — `curl -s "https://opencritic-api.p.datacamp.com/game/search?criteria=<title>"`, pick the entry matching title+year, use `criticScore` (0-100), url `https://opencritic.com/game/<id>/<slug>` (fallback: WebFetch the opencritic.com search page). Metacritic critic — WebSearch "metacritic <title> <year> critic reviews" for the Metascore. Steam — `curl -s "https://store.steampowered.com/api/storesearch/?term=<title>&l=en&cc=US"` for the appid, then `curl -s "https://store.steampowered.com/appreviews/<appid>?json=1&language=all&purchase_type=all&num_per_page=0"`; score = total_positive/(total_positive+total_negative)*100, n = their sum. Metacritic users — WebSearch "metacritic <title> user score" (×10, e.g. 7.4 → 74).
- **movie/show**: Rotten Tomatoes — WebSearch "rottentomatoes <title> <year>" for the URL, WebFetch it with an extraction prompt for the tomatometer % and audience %. Metacritic — WebSearch. IMDb — WebSearch "imdb <title> <year> rating" (×10, votes as n). Letterboxd — WebFetch `https://letterboxd.com/search/films/<title>/`, then the film page for the avg rating (×20) and rating count.
- **album**: Album of the Year — WebFetch `https://www.albumoftheyear.org/search.php?q=<artist> <album>`, then the album page for "Overall" and "User Score" (both 0-100). Metacritic — WebSearch. Pitchfork — WebSearch "pitchfork review <album> <artist>" (×10).
- **book**: Goodreads — WebFetch `https://www.goodreads.com/search?q=<title>`, then the book page for "avg rating" (×20) and "ratings" count. OpenLibrary — `curl -s "https://openlibrary.org/search.json?title=<title>&fields=title,author_name,first_publish_year,ratings_average,ratings_count"`, ratings_average ×20, n = ratings_count.

Normalize everything to 0-100: percentages pass through, 0-10 ×10, 0-5 ×20. Round to integers.

## Compute the consensus (deterministic — do this arithmetic yourself, show the numbers)

Weights by kind (renormalize over the sources you actually found, then consensus = round(weighted mean)):

- game: OpenCritic .35 · MetacriticCritic .25 · Steam .25 · MetacriticUsers .15
- movie/show: RTCritics .30 · MetacriticCritic .20 · IMDb .20 · RTAudience .15 · Letterboxd .15
- album: MetacriticCritic .40 · AOTY .30 · AOTYUsers .20 · Pitchfork .10
- book: Goodreads .60 · OpenLibrary .40

Critic avg = weighted mean of critic-type sources; player avg = weighted mean of audience-type sources; gap = |criticAvg − playerAvg|, rounded to 1 decimal. Agreement: gap < 4 → UNANIMOUS, < 10 → ALIGNED, < 18 → DIVIDED, else POLARIZED. Label: ≥ 90 MASTERPIECE, ≥ 85 ESSENTIAL, ≥ 78 EXCELLENT, ≥ 70 GOOD, ≥ 60 MIXED, ≥ 45 WEAK, else POOR.

## Render the ASCII card

Output the card in a fenced code block, exactly in this shape (box-drawing borders, 30-char consensus bar, 22-char source bars; `█` full, `▌` half, `░` empty; sample counts compacted like 420k / 1.2M; the verdict label right-aligned on the consensus line):

```
┌──────────────────────────────────────────────────┐
│ ELDEN RING (2022)                                │
│ FromSoftware · Video Game · PC                   │
├──────────────────────────────────────────────────┤
│ ★★★★☆  CONSENSUS 89/100              ESSENTIAL  │
│ [█████████████████████████████░░] 89%            │
├──────────────────────────────────────────────────┤
│ CRITICS                                          │
│ OpenCritic       89  ████████████████████░░      │
│ Metacritic       96  ██████████████████████      │
│ PLAYERS                                          │
│ Steam · n=420k   93  █████████████████████▌      │
├──────────────────────────────────────────────────┤
│ Critics 92 · Players 89 · gap 3 → ALIGNED        │
│ TGA Game of the Year 2022 · "a landmark world"   │
└──────────────────────────────────────────────────┘
```

Stars = consensus/20 rounded to the nearest whole star, ★ filled / ☆ empty. Include an awards line (WebSearch GOTY/Oscars/Emmys/Grammys/Booker wins — max 3, real wins only) and one quoted line of what critics praise. If there is no critic coverage (books), the footer says "Reader consensus · no critic-score aggregator covers this" and the section is labeled READERS instead of PLAYERS. If fewer than two sources resolve, say so plainly under the card instead of forcing a number.

## Below the card — at most 5 tight lines, no headers

1. What it is, in plain words.
2. Where the score comes from (sources + review counts) and what the critic-vs-player split says (unanimous / aligned / divided / polarized).
3. What people praise — one line, concrete.
4. What people criticize — one line, only if there is something meaningful.
5. Who it's for / who should skip it.

Rules: every number must be traceable to a source you actually fetched — never invent a score, sample size, award, or URL. Keep the reply tight; the card does the showing, the text only explains.
