---
name: x-reach
description: Optimize X (Twitter) posts for For You algorithmic reach using the open-sourced X algorithm (github.com/xai-org/x-algorithm). Use when asked to write, rewrite, or optimize a tweet/post/thread for reach or views, to judge whether a draft will get reach, or to diagnose why a posted tweet underperformed. Produces a gate audit, a rewritten post, and a launch plan.
---

# x-reach — X For You reach optimizer

Rewrites a draft X post for maximum For You reach, grounded in xAI's open-sourced algorithm code (github.com/xai-org/x-algorithm, main branch). Every rule below cites its source file; file paths are main-branch-relative. Values are production defaults cron-synced by xAI into the repo — they change, so check freshness first.

## Step 0 — Freshness check

`refs/current-weights.md` is a snapshot synced from the repo. If its sync date is more than 30 days old (or the user says X changed the algorithm), run:

```bash
<skill dir>/scripts/sync-weights.sh
```

and use the refreshed values. If it fails (offline), proceed with the snapshot and say so.

## Inputs

- Draft text (required). If the user only gives a topic, write the draft first.
- Media (describe it: subject, tone, any nudity/gore/violence).
- Target audience / niche — ask if unknown and it matters; For You is personalized per viewer.
- Original post or reply — ask if ambiguous. Replies can't reach out-of-network viewers (gate 1).

## Step 1 — Hard gate audit

Each gate is a binary rule in the code. Output PASS / WARN / FAIL with a one-line fix. A FAIL is a near-total loss of non-follower reach; fix before optimizing.

1. **Top-level original** — For You drops out-of-network replies and reposts (`home-mixer/filters/oon_retweet_reply_filter.rs`; `EnablePhoenixOonReplies` defaults false). Replies only reach the thread's own audience. If the draft is a reply, say so and optimize it for the thread, not For You.
2. **Never edit after posting** — a superseded edit is dropped from For You (`StaleTweet` rule, `visibility-filtering/rules/tweet_rules.rs`). If a fix is needed, delete and repost.
3. **48-hour window** — posts older than 48h leave For You entirely (`MAX_POST_AGE`, `home-mixer/params/config.rs`). Only relevant for quoting/reviving old posts.
4. **Not a nullcast.**
5. **Links** — URLs judged LOW_QUALITY/BAD by the link-verdict service label the post `MALICIOUS_URL` / `SPAM_HIGH_RECALL` → dropped for non-followers (`botmaker-rules/scarecrow/bot/Tweet_Spam_High_Recall_RTF_All_BAD_URL_Sources.bot`, `LQ_Tweets_With_LQ_URL_Verdict_At_Mention_To_NonFollower.bot`). The classic trigger (rule 5239): a link + @-mentioning a non-follower in an original. Rules: prefer no link; else own domain or x.com; never link-shorteners/tracker domains; don't combine a link with a non-follower @-mention.
6. **Media** — NSFW (high-precision/high-recall) and gore/high-precision media are dropped for non-followers and shown behind a blur interstitial to followers (`visibility-filtering/rules/tweet_rules.rs`: `oon_nsfw_media_label_drops`, `nsfw_*` interstitials). Adult/gore imagery: drop it or expect the blur + OON loss.
7. **Text safety (FOSNR)** — insults/abuse (level 1) drop the post for non-followers; repeated offenses get the *author* a level-3 label (hateful conduct, violent speech, abuse, civic integrity) which restricts viewer actions — followers can no longer like/reply/RT/quote/share/bookmark/copy-link/DM the post, so engagement and score collapse (death spiral). Adult text, suicide/self-harm, child-safety, illegal/regulated-behavior content are also screened (Gemma PTOS policy list, `grox/flows/ptos/classifier.py`). Write hot takes about ideas and numbers, not about people.
8. **No repeated text** — duplicate-text detection (unigram clustering, CJK-aware) labels recurring phrases `COPYPASTA_SPAM` (`botmaker-rules/scarecrow/bot/BBQDuplicateTextProd.bot`). No signature catchphrases, boilerplate sign-offs, or identical thread intros across posts. (High-cred/gray-verified accounts are exempt — new accounts are not.)
9. **Not AI-sounding** — an LLM/VLM screen (Gemma, `grox/flows/upa/`) scores every post for quality, slop, spam, NSFW/gore/adult; `llm_slop_user` puts `SpamHighRecall` on the whole account for 30 days, `gibberish_post` and `fast_reply_spam_post` label the post (`abuse-enforcement-service/service-lib/rules/enforcement_*.yaml`). The exact prompts are redacted from the repo (anti-gaming), so judge conservatively: concrete specifics, one point of view, no filler ("humbled and honored", "big things coming"), no em-dash/buzzword stacks, no listicle scaffolding, varied structure post-to-post.
10. **Behavior, not just content** — a time-aware transformer (BDSM, `bdsm/`) watches the account's action sequence (FollowBot, LikeBot, EngagementAmplifier, ReplySpamBot, TweetSpamBot, RTBot, MultiActionBot) and punishes bursty/mechanical cadence with `SpamHighRecall` (30 days), captcha, or suspension. Engaging right after posting is fine; 15 replies in 4 minutes is not.

## Step 2 — Rewrite for the weight table

Scoring is `Σ weightᵢ × P(actionᵢ)` where P is the *predicted probability each viewer takes the action* — weights do NOT multiply raw counts (README explicitly warns against "1 report = 468 likes"). The table below is the 2026-10-08 default snapshot; if `refs/current-weights.md` was synced more recently, it takes precedence over this table.

| action | weight |
|---|---|
| share via copy link | +20.0 |
| reply (mutual-follow viewer, original) | 5.0 + 15.0 |
| reply | +5.0 |
| quote | +5.0 |
| share via DM | +5.0 |
| follow author | +4.0 |
| share | +2.0 |
| retweet | +1.0 |
| favorite | +0.5 |
| click post | +0.3 |
| open link | +0.2 |
| video open | +0.07 |
| dwell | +0.05 |
| photo expand | +0.05 |
| dwell time (seconds) | +0.004 |
| click dwell time (seconds) | +0.4 |
| not dwelled | −0.02 |
| not interested | −47.5 |
| block author | −31.2 |
| mute author | −58.8 |
| report | −234.0 |

Rewrite implications (this is the core of the skill):

- **Optimize for replies and quotes, not likes.** Reply/quote/DM-share are 10–40× a like. End with a question a stranger can answer in one sentence, or a concrete claim someone will fact-check in the quote box ("X is wrong about Y, here's the number"). Generic engagement bait ("agree?") trains "not interested" (−47.5) — the worst positive-negative ratio.
- **Make it forwardable.** Copy-link share is the single heaviest weight (20). A self-contained, quotable, screenshot-able one-line core (a number, a verdict, a list) is what gets DM'd and copied.
- **Be worth following** (4×). Put the account's topic + stance in the post, not just the payload of this one fact.
- **Links cost nothing but risk everything.** open_link = 0.2, click = 0.3: links barely contribute to score while being the main `MALICIOUS_URL`/spam trigger. Put the substance in the post; link only when the link IS the point.
- **Avoid negative-signal bait.** Content that invites "not interested" / mute / report (identity attacks, outrage aimed at people, engagement-farming hot takes) costs 60–470× a like per instance in the score.
- **Video/image help retrieval, not scoring.** Media goes into the post's multimodal embedding (semantic ID) that retrieval matches against viewer history, and drives the safety labels. A sharp, on-topic, SFW image/video is a retrieval + relevance signal; the video continuation weights default to 0.0. Put the payload in the first line of text regardless.

Keep the user's voice, stance, and factual claims. Rewrite structure and framing, never invent facts. Show each change with a one-line reason mapped to a rule above.

## Step 3 — Cadence and timing (multipliers on the score)

- **Author diversity decay 0.5, floor 0.25** (enabled): your 2nd post in a viewer's candidate set scores ×0.625, 3rd ×0.4375, … (`vm-ranker/params.rs`: `AuthorDiversityDecay/Floor`). One strong post per day beats a burst.
- **Out-of-network discount ×0.75** (×0.5 on topic feeds); in-network replies/retweets are also discounted 0.75. Originals to followers are the only un-discounted unit.
- **Cold-start window (accounts <50k followers):** an original (not reply/RT) with <200 home impressions and <2h old gets lifted to ~rank 15 in eligible viewers' feeds — exactly one such lift per feed request, the lifted post chosen by Thompson sampling over up to 2 candidates, only if it already ranks in the top ~97% of nonzero-scoring candidates (`home-mixer/scorers/author_cold_start.rs`; `ColdStart*` params). The first 2 hours are free distribution: be online to answer early replies, which seed P(reply) for everyone else.
- **Post age is a ranker input** (hourly buckets, `phoenix/xrex/models/recsys_feature_prep.py`) on top of the 48h filter — freshness is a direct scoring feature.
- **Hour-of-day and timezone are ranker inputs** — post when the target audience is active. Ask the user for their audience's timezone if unknown.
- **DPP dedup (θ=0.65, top-150 pool, `vm-ranker/dpp.rs`)** reorders the feed to suppress near-identical items — writing the genre's stock template competes against the entire niche's template. Pick the angle you're the most specific person on.

## Step 4 — Flat reach diagnosis (asked "why didn't it work", or account ≥ a few weeks old)

1. Check https://x.com/i/jf/under_the_hood — the label transparency report for the account and its posts (incl. country legal takedowns). Map each visible label to the gate list above.
2. Likely causes, in order: `SpamHighRecall`/spam labels (duplicate text, link+mention, bot-like cadence), FOSNR author level 3 (viewer actions restricted — stop arguing, 2–4 quiet weeks), NSFW/gore media (blur + OON drop), high report/block ratio (`agatha/` computes 30-day blocks/favs, reports/favs, spam-reports/favs), `DO_NOT_AMPLIFY` (controversy), low user credibility (`user-cred-v2/` PageRank; score = clamp(165.2 + 7.07·ln(mass), 0, 100), ≥50 skips most enforcement — built by steady follow/follow-back and replies over time).
3. If no labels: it's retrieval, not suppression — the post didn't match viewer histories. Fix by narrowing to the niche's vocabulary (semantic ID matching), adding a sharp SFW image/video (retrieval embeddings include media), and posting at audience-active hours.

## Output format

1. **Verdict** — 2–4 lines: does the draft have a reach problem, and the two biggest levers.
2. **Gate audit** — table, PASS/WARN/FAIL + fix per gate (skip gates that are trivially PASS, say so in one line).
3. **Rewritten post** — under 280 chars where possible (copy-link-shareable); voice and claims preserved; one line per change with the rule it implements.
4. **Launch plan** — post time (audience TZ), no-edit reminder, first-2-hours plan, spacing from next post.

## Limits (state once, then stop)

- Phoenix's trained weights are not in the repo (code + synthetic data only), and Grox prompts + some botmaker rules are deliberately redacted — per-viewer P(action) is a black box. You're optimizing the known structure (gates, weights, multipliers, timing), not simulating the model.
- Reach is per-viewer-personalized; "max reach" means maximizing the weighted action mix for the stated audience, not a universal score.
- Some enforcement thresholds (BDSM operating points) are redacted sentinels; the directions above hold, exact cutoffs don't.

## Maintenance

- `scripts/sync-weights.sh` — re-pulls the production-synced param defaults into `refs/current-weights.md` and prints a diff of changed reach-relevant values. Re-run after any x-algorithm release if the user cares about exact numbers.
- If a cited file/param no longer exists on re-sync, search the repo fresh (`grep -rn` in a clone) before quoting a rule.
