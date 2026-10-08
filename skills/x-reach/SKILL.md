---
name: x-reach
description: Turn a draft X (Twitter) post into a reach-optimized one, using the open-sourced X algorithm (github.com/xai-org/x-algorithm). Use when asked to write, rewrite, or optimize a tweet/post/thread for reach or views, to judge whether a draft will get reach, or to diagnose why a posted tweet underperformed. Returns the rewritten post, the few changes that mattered, and posting timing.
---

# x-reach — turn a draft X post into a reach-optimized one

Default mode: the user hands you their own draft (or "a tweet about X") and you return the improved post. Never invent facts, never overwrite their voice or stance — rewrite structure and framing only. If you only have a topic, write the post first as they would have, then run the pipeline on it.

Weights are xAI's production defaults, synced from `xai-org/x-algorithm` main. The full parameter table lives in `refs/current-weights.md`; check its `synced:` date and re-run `scripts/sync-weights.sh` if it is more than 30 days old or the user says the algorithm changed.

## Pipeline

1. **Draft.** If you only have a topic, write the post first, in the user's voice.
2. **Gates.** Run all ten below. A FAIL is near-total loss of non-follower reach; fix it before touching anything else. Report only the gates that are not PASS.
3. **Rewrite.** Weight order: copy-link share (+20) > reply (+5, or +20 from a mutual-follow viewer) = quote (+5) = DM share (+5) > follow (+4) > like (+0.5). Negatives swamp every positive: report −234, mute −58.8, not interested −47.5, block −31.2.
4. **Ship.** Time, first-two-hours, spacing — three bullets.

## Gates (each is a binary rule in the code)

1. **Top-level original** — For You drops out-of-network replies and reposts (`EnablePhoenixOonReplies=false`). If the draft is a reply, say so and optimize for the thread, not For You.
2. **No edit after posting** — a superseded edit is dropped from For You (`StaleTweet`). A fix means delete and repost.
3. **Under 48h old** — `MAX_POST_AGE`. Only matters when quoting or reviving.
4. **Not a nullcast.**
5. **Links** — a LOW_QUALITY/BAD URL verdict labels the post `MALICIOUS_URL`/`SPAM_HIGH_RECALL` and drops it for non-followers; the classic trigger is a link plus @-mentioning a non-follower. Prefer no link, else the site's own domain, never shorteners or tracker domains.
6. **Media** — NSFW/gore is blurred for followers and dropped off-network. A sharp SFW image or video buys a retrieval signal through the multimodal embedding; it buys no score.
7. **Text safety (FOSNR)** — abuse drops the post, and a repeat gets the *author* a level-3 label that stops followers from liking/reply/RT/quoting it. Aim at numbers and ideas, never at people.
8. **No repeated text** — recurring phrasing is labeled `COPYPASTA_SPAM`. No catchphrases, sign-offs, or identical thread intros across posts.
9. **Not AI-sounding** — a Gemma screen flags slop and gibberish, and `llm_slop_user` puts `SpamHighRecall` on the whole account for 30 days. Concrete specifics, one point of view, no filler, no em-dash or buzzword stacks, no listicle scaffolding, varied structure post to post.
10. **Behavior** — BDSM watches cadence; bursty reply/like/RT patterns cost `SpamHighRecall`, captcha, or suspension. Answering your own comments is fine. Fifteen replies in four minutes is not.

## Rewrite rules

- **One forwardable core.** Copy-link share is the heaviest weight by 4x. Make the first line a self-contained number, verdict, or list that screenshots and DMs well.
- **Earn a reply or a quote.** End on a question a stranger answers in one sentence, or a claim someone will fact-check in the quote box. Generic bait ("agree?") is the fastest route to not-interested (−47.5).
- **Say what this account is about**, so the post is worth a follow (+4) and not just a fact.
- **Put the substance in the text.** open_link = +0.2, click = +0.3: the link is the spam trigger, not the score.
- **Media helps retrieval, not scoring** — video continuation weights default to 0.0, so the payload goes in the first line of text regardless.

## Ship

- **Time** — post in the audience's active hour and timezone; both are ranker inputs. If the audience is unknown, state the assumption instead of asking.
- **First two hours** — a cold-start lift puts one original under 200 impressions near rank 15. Be online, answer replies fast; early replies raise P(reply) for every later viewer. Do not edit, ever.
- **Spacing** — author-diversity decay makes your second post in a feed x0.625 and the third x0.4375. One strong post per day, not a burst.
- **Dedup** — DPP (θ=0.65) suppresses near-identical posts, so the niche's stock template is your competition. Pick the angle you are the most specific person on.

## If it already flopped

Check `x.com/i/jf/under_the_hood` for labels first. In order: `SpamHighRecall` (duplicate text, link + mention, bot cadence), FOSNR author level 3 (stay quiet 2–4 weeks), NSFW/gore media, high report/block ratio, `DO_NOT_AMPLIFY`. No labels means retrieval, not suppression: narrow to the niche's vocabulary, add a sharp SFW image, post at active hours.

## Output

Rewritten post first, with its character count. Then at most three lines of *why*, each tied to a weight or a gate, and only for changes actually made. Then the Ship bullets. Close with one line of limits: Phoenix's trained weights and the Grox prompts are redacted, so per-viewer P(action) is a black box — this optimizes the known structure (gates, weights, timing), and reach is personalized per viewer rather than universal.

## Maintenance

Re-run `scripts/sync-weights.sh` after any x-algorithm release. If a cited file or param no longer exists on re-sync, re-grep the repo before quoting the rule.
