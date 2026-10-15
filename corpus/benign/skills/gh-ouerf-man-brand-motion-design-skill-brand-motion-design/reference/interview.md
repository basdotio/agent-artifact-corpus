# Interview: ask little, remember everything

The film is always a showreel cut ([showreel.md](showreel.md)): fast, lit 3D, a new picture every 2 beats. Never ask about pace, "calm or catchy", effects or transitions. Ask only what the brand files, the codebase or the captured site cannot answer.

Always ask with the **AskUserQuestion** tool (never as a list in chat): at most 4 questions per call, 2 to 4 options each ("Other" is added automatically for free text), options named after what you found (their products, their colours, their tagline), `multiSelect` where several answers fit. **Every question has a "You choose for me" option**; when there is a clear best answer, put it first and mark it "(Recommended)". If the tool is unavailable, ask the same questions in one short numbered message with the defaults stated.

## Step 0: is there a saved profile?

Look for `videos/BRAND.md` (the brand profile this skill writes) before asking anything. If it exists, read it: the brand, the owner's standing choices (format, music, language, tone, audience) and past films. Reuse all of it. Ask only what is new for this film (the type, the message, new assets), and say in one line what you reused ("Using your saved profile: charcoal and orange, trap beat, 9:16, English").

## Round A: the brand (only when there is no brand book, no codebase and no usable site)

If the user gave a brand book, a codebase or a site, skip this round: discovery answers it. Otherwise ask, in one call:

| Question | Options |
|---|---|
| What are your brand colours? | The colours in your logo, as I read them: <hexes> (Recommended, if a logo was given) / I'll paste my hex codes (Other) / You choose for me: 3 palettes shown as style frames |
| Which typeface feel? | Bold condensed headlines + clean sans (Recommended for social) / Elegant serif + sans / Rounded and friendly / You choose for me |
| How does the brand talk? | Confident and direct / Warm and friendly / Premium and minimal / Playful, Gen Z |
| Who is it for? | <the audience you infer> / Young people 15 to 25 / Professionals / Parents, families |

"You choose for me" means: pick, build 3 style frames that show the choice, and let them react to pictures. Write every choice under "Chosen by Claude" in `BRAND.md` so they can overrule it later.

Also ask for the logo file if you do not have it (SVG best, transparent PNG fine).

## Round B: this film

| Question | Options (adapt to what you found) |
|---|---|
| What kind of video? | The types from [video-types.md](video-types.md) that fit this brand: Product launch / Feature spotlight / Promo or offer / Brand teaser / Social proof / Event / Before and after / Product showcase / You choose for me |
| Where will it play, and how long? | Reel / TikTok / Shorts, 9:16, 15 to 20 s (Recommended) / Launch or website video, 16:9, 20 to 30 s / Square post, 1:1, 15 s / You choose for me |
| What is the one message? | <two or three candidates written from their site or brand book, each as three short statements> / You choose for me |
| What music? | A generated hip-hop / trap beat, royalty-free (Recommended for a young audience) / A generated punchy electronic beat / My own licensed track / Silent (reads muted) |

Then, if the type needs facts you do not have (a price, a date, an address, a review), ask for them exactly; never invent them. Then ask for assets in one question (`multiSelect`): "Do you have any of these to include?" Logo (SVG or PNG) / Product photos / Screenshots or a screen recording / Footage, a song or a voiceover. See [assets.md](assets.md) for how each is used.

Ask the language only if the brand speaks more than one and the choice is unclear (right-to-left scripts change layout and type).

## Remember for next time

Write the answers down as soon as you have them:
- **`videos/BRAND.md`**: the brand (what discovery found and what Round A decided), plus "Owner choices" (the standing answers: format, music style, language, tone, audience, series look) and "Chosen by Claude". This is the profile Step 0 reads next time.
- **`videos/<film>/PROMPT.md`**: this film's type, message, facts, assets and any one-off choice.
- Add the film to the "Films" list in `BRAND.md` (name, type, date, what the owner liked or changed). Their notes on one film ("faster", "less text", "no ambient music") become owner choices for all the next ones.
- If the agent has a user memory, it may also save the standing choices there; the files above stay the source of truth, because they travel with the project.

## When the user is away or says "just go"

Use the saved profile, else the recommended options, write them under "Assumed, not asked" in `BRAND.md`, tell the user in one line, and continue. Show 3 style frames as soon as they exist, so they can redirect early.

## When the user shows a reference video

Study it before building: a contact sheet every 0.25 s, then name what makes it work (light and materials, scale of type, how often the picture changes, transitions, the HUD, the ending). Apply those to this brand; never copy the reference's colours, words or marks.

## Explainer mode (only on request)

If the user explicitly asks for a calm film, a tutorial, a walkthrough or a product tour, switch to the explainer column of [showreel.md](showreel.md) and also ask the ingredients: what carries the brand (logo build, mascot, wordmark), how words appear (punchlines, captions, none), how scenes connect (magic moves, one canvas with camera moves, cuts), extras (cursor interactions, partner logos, proof moments, brand texture). See [ingredients.md](ingredients.md).

## Don't ask

- What the files already answer: colours, fonts, radius, the logo, the claims rules.
- What the saved profile already answers.
- Taste you can show instead: make 3 style frames and let them react. People answer pictures faster than questions.
