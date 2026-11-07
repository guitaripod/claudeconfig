---
name: app-short
description: Make TikTok / Reels / Shorts videos about Marcus's apps - Saga, the recurring AI-generated Nordic presenter (Flux 3 klein stills animated by LTX-2.5, Tailscode's local video lane), holds a phone whose green screen is replaced with the real app recording, then real app footage in a sharp `frames` bezel over the same footage blurred into the app's palette, short text cards and a locally generated instrumental bed (ACE-Step 1.5) with cuts on the beat. Use for "TikTok for <app>", "short-form content", "Reels", "Shorts", "app promo clips", "marketing video". Not for launch films (keynote-video) or footage hype edits (hype-edit).
---

# App shorts

Scripts (all in `scripts/`):
- `comfy.py` generates stills (Flux 3 klein, with references) and clips (LTX-2.5 i2v) on the arch ComfyUI.
- `screen.py` puts real app footage on a generated phone's green screen.
- `music.py` makes instrumental beds with ACE-Step.
- `short.py` renders the 1080x1920, 30 fps short from a JSON spec.
- `deliver.sh` sends finals and captions to Marcus's Telegram.

The first batch (App of the Dead, Master of Flags, 2026-11-07) has its specs in each app's `marketing/shorts/` in the monorepo; copy one as the starting point.

## Saga, the presenter

Marcus's standing direction (2026-11-07): a beautiful Nordic blonde woman appears in all the marketing, made to look real.
- Her canonical look is `cast/saga.jpg` (25, platinum-blonde waves, light blue eyes, freckles). Every new scene cites it as `<ref_image_0>` with `--ref-mp 2.0`, which keeps her face from scene to scene.
- Prompts that worked are in `cast/prompts/` (`portrait`, `scene-*`, `motion-*`).
- Keep her tasteful and clearly adult. She's the hook, not the content, and she never speaks or poses as a customer giving a testimonial.

What makes her read as real:
- Candid iPhone-photo wording ("candid vertical photo taken on an iPhone, natural and unretouched, slight phone-camera noise").
- A specific place with practical light (candles, museum spotlights, a train window, an airport gate) and shallow depth of field.
- "Healthy, even, youthful complexion with light natural makeup ... no redness". Without it klein over-reddens her skin.
- One small, believable action per clip: a head tilt, a glance at the phone, a smile, a look back over her shoulder.
- "Keeps the phone perfectly still ... its screen staying a flat, evenly lit green for the whole shot". LTX keeps the green solid then.
- "Tiny natural handheld sway", and nothing fast.

Recipe:
1. **Still.** `comfy.py klein --prompt-file scene.txt --ref cast/saga.jpg --ref-mp 2.0 --width 1152 --height 2048 --steps 28 --seeds 1,2,3 --prefix shorts/scene-x` (about 30 s each). She holds an iPhone toward the camera, close (about 40 cm), with the screen a flat chroma-key green and her fingers only on the sides. Pick by face fidelity, hands and phone size.
2. **Clip.** `comfy.py i2v --image first.png --prompt-file motion.txt --width 768 --height 1344 --seconds 5 --seeds 1 --prefix shorts/clip-x` (about 70 s on a free card, ~72 GB VRAM peak). llama-keepwarm unloads Bolt by itself once ComfyUI has work, but check `nvidia-smi` for anything else (an SGLang or vLLM model of 70 GB leaves no room; llama-swap TTLs free it in 10 minutes). Make a 2 fps strip and reject clips where the green flickers, the hands morph or the face drifts.
3. **Screen.** `screen.py --clip clip.mp4 --app take.mp4 --app-t0 4.3 [--hold-at 1.2 | --still] --out broll.mp4 --debug /path/prefix`.
   - The key takes only bright, saturated green, so green sofas and forests stay.
   - Geometry: a line is fitted to each straight edge of the keyed screen and the corners are their intersections. Never fit a polygon to the blob: the rounded corners skew the quad and the UI ends up tilted against the phone. That was the "obviously fake" look of 2026-11-07.
   - Light: the green plate's own shading and reflections (luma over its median, and the rise of min(R,B)) are multiplied and screen-blended onto the app. On top come a white balance to the room, exposure and black lift, camera softness, a dark rim where the glass meets the bezel, sensor grain over everything, and sub-frame motion blur when the phone moves. The green spill on the fingers comes back in the app's colour as screen light.
   - Let the app play (`--hold-at` seconds, then hold before any answer). A frozen screen reads as fake; `--still` is the fallback.
   - Reds and magentas on her skin are calmed (`--blush`).
   - Check the `--debug` frames zoomed in at the screen edge.
   - The 2026-11 research is behind these choices. Commercial planar trackers (Mocha Pro $1495 on Linux; Resolve Fusion; Blender's Plane Track) solve geometry only. CoTracker3 is non-commercial. AI editors (Wan VACE or Animate, Runway Aleph, Kling) and AI-UGC SaaS (Arcads, Creatify) re-synthesise the screen, so the UI text garbles. If a relight pass is ever added, mask the screen out of it and put the UI back on top.
4. **Spec.** Her shot is a segment `{"broll": "<broll.mp4>", "beats": 6}` (full frame, no phone layer). She opens every video, followed by the framed-phone segments.

**Disclosure (not optional):** TikTok's Community Guidelines (effective 2026-09-24) require creators to label AI-generated content showing realistic people. Unlabeled posts may be removed, restricted or labeled by TikTok. Every post with Saga goes up with TikTok's "AI-generated content" toggle on, and the delivery message says so. Never strip provenance or try to beat detection.

## Non-cringe rules

- The app stays the hero. Its footage is real and sharp (inside her phone, and in the bezel segments). The only generated parts are Saga and her surroundings, the music and the type.
- One idea per video, 10-20 s. The hook is a question or a fact the footage answers, in the first second. No "wait for it", fake stats ("only 1% get this"), emoji in the video, or voice-over.
- Every claim on a card or in a caption must match the live listing and the app as recorded.
  - Price and version: `https://itunes.apple.com/search?term=<app>&entity=software`.
  - UI: check the takes still match the shipped app (`git log -- apps/<app>` since the take date).
- Facts on cards (mythology, geography) must be right. Keep away from anything political or outdated in the footage. Master of Flags' takes from before 4.2.1 show Syria's pre-2025 flag and Kyrgyzstan's old sun.
- Interaction beats polish: quiz holds with a countdown, "what would you answer" questions, a reveal. These earn comments without asking for them.

## Flow

1. **Takes.** App Preview takes live on the mac in `~/Videos/previews/<app>/rec`, with `notes.md`, `spec.json` and drive scripts.
   - They're raw simulator recordings at 1320x2868 and variable frame rate. `short.py` and `screen.py` resample them, so seeking into a still stretch is safe.
   - Copy them to `/mnt/nvme8tb/shorts-work/<app>/`. Make a 1 fps contact sheet (`ffmpeg -vf "fps=1,scale=220:-1,tile=9x4"`) to pick moments.
   - New moments need a new take with the app's preview rig (see its `notes.md`).
2. **Music.** ACE-Step 1.5 lives in `/mnt/nvme8tb/ace-step` (MIT; outputs cleared for commercial use; uv project; XL turbo + 1.7B LM):
   ```
   uv run --project /mnt/nvme8tb/ace-step python scripts/music.py --caption "<genre, instruments, mood>, instrumental" --bpm 90 --key "D minor" --duration 42 --takes 4 --seed 101 --out /mnt/nvme8tb/shorts-work/music/<app>
   ```
   - Keep captions to restrained instrumental beds (ambient, cinematic, light indie pop). AI music gives itself away in vocals and busy melodies.
   - Pick a take whose detected tempo matches the request (librosa `beat_track`). It should have a steady pulse and no swirls or vocal-like sweeps in `showspectrumpic`.
   - Use `start_bar` to skip a quiet intro.
   - Marcus should hear a new bed style once before it goes out.
3. **Spec.**
   - Segments cut the takes. Lengths in `beats` land every cut on a detected beat of the bed; `dur` gives seconds instead.
   - `{"freeze": true, "beats": 6}` holds the previous frame.
   - `{"broll": ..., "beats": n}` is a full-frame Saga shot.
   - Texts span segments (`from`/`to`, optional `delay`). A card is a `label` + `title`, or `{"countdown": 3, "y": 1150}` for a ring on a dark disc.
   - Style files hold the palette, fonts and device placement per app:
   ```json
   {"root": "<takes dir>", "work": "<build dir>", "out": "<mp4>", "bpm": 90, "seed": 3,
    "music": {"file": "<bed.flac>", "start_bar": 2, "fade_out": 1.4},
    "palette": {"bg_top": "#140e1d", "bg_bottom": "#07060b", "tint": "#c9a37a", "screen_mix": 0.3, "glow": "#d9a441", "glow_strength": 0.2, "bokeh": ["#e3b25a", "#9a7be0"], "bokeh_count": 24},
    "style": {"label": "#e3b25a", "title": "#f3e9d2", "top": 150, "title_font": {"file": "...ttf"}, "title_size": 76, "label_font": {"file": "...ttf", "variation": "SemiBold"}, "label_size": 30},
    "device": {"color": "Silver", "height": 1130, "center_y": 968, "push": 0.08},
    "segments": [{"broll": "/mnt/.../broll.mp4", "beats": 4}, {"clip": "s1.mp4", "t0": 0.3, "beats": 1}, {"freeze": true, "beats": 5}],
    "texts": [{"from": 0, "to": 1, "label": "Quick quiz", "title": "Who ruled the\nGreek underworld?"}, {"from": 2, "to": 2, "countdown": 3, "y": 1150}]}
   ```
   - Titles stay at two lines of at most ~22 characters.
   - Type sits in y 150-400 and the phone in 400-1530, clear of TikTok's top tabs, right rail and bottom caption.
4. **Render and look.**
   - Quick checks: `scripts/short.py spec.json --stills 0.5,4,-1 --zones`. Full render: `scripts/short.py spec.json`.
   - View a frame per segment at phone size (scale to 540 wide). Fix legibility, timing (the card should arrive with what it describes) and safe zones.
   - Do at least three passes per new format.
   - Loudness lands at about -14 LUFS.
5. **Deliver.**
   - Finals go to `/mnt/nvme8tb/Clips/<app>-<idea>-tiktok.mp4` (never overwrite), each with a `.txt` caption beside it: one hook line, one context line, 6-10 hashtags.
   - `scripts/deliver.sh` sends each video with its caption to Marcus's Telegram (the hypebot bot). That's how he posts from his phone.
   - Posting stays manual: the unaudited Content Posting API posts privately and risks a new account's reach.

## Accounts and cadence

- One TikTok account per app, because the algorithm learns one audience per account. App of the Dead posts mythology and afterlife topics; Master of Flags posts flag quizzes.
- At most one post a day per account, spaced over the week, best hook first.
