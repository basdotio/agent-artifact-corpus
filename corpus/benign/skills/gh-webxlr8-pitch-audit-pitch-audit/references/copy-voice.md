# Copy and voice: how the deck talks

Write like a sharp consultant who has actually looked at their business, not like a template. If a sentence could appear in anyone's deck, rewrite it with their names, numbers, places and words.

## Headlines
- Sentence case. Capitalise the first word and names only ("The phone number can't be tapped", not "The Phone Number Can't Be Tapped").
- Highlight one phrase with `*...*` (the part that stings or the part that helps). It does not have to be a second sentence.
- Vary the shape. Use the "claim. *payoff.*" two-beat at most twice per deck. Mix in:
  - a number: `9.9 seconds *of blank screen*`
  - a question: `“24/7 tracking” *or 9 to 5?*`
  - their own words, quoted from their site: `“The most reliable team” *needs a page that loads*`
  - a plain statement: `Fourteen tankers, *one phone line*`
- Say the specific finding on the cover. "What shippers see before they call you" beats "Growth opportunities".
- Name the real next step on the closing slide ("Next step: a 30-minute walkthrough"), not "Let's talk".
- `lint_deck.py` fails decks with stock phrases, em dashes, Title Case headlines or a single repeated headline formula.

## Body
- Max 2 sentences under a headline. Plain words. Numbers beat adjectives.
- Every finding slide: **what we saw** (metric/evidence) → **what it costs** (impact panel).
- Use the client's name and their products. Show we understood the business (slide 2).

## Numbers
- Every number must come from `audit.json`, `scores.json`, `manual.json` or your profile (`catalog.yaml`, `proof.yaml`). No invented stats, no "industry studies say 53%…" unless the source is cited in the footnote.
- Round sensibly: `6.2s`, `4.8 MB`, `38/100`.

## Respect
- Critique the website, never the people. "Your site hides the booking button", not "your team got it wrong".
- Open with something they do well (slide 2 or a "What's working" chip set) before the gaps.
- No fear-mongering. Calm, factual urgency.

## Banned
- Stock phrases (full list in `scripts/lint_deck.py → SLOP`): "growth opportunities", "let's talk", "unlock", "seamless", "leverage", "elevate", "game-changer", "cutting-edge", "world-class", "streamline", "drive growth", "tailored solutions"…
- Em dashes, emoji, exclamation marks, "solutions" as a noun on its own.
- Rhetorical triplets ("Faster. Smarter. Better.") and "It's not X, it's Y".
- Prices that are not in `catalog.yaml` (`price` field = public price). Everything else: "scoped after a 30-minute call".
- Guarantees that are not in `catalog.yaml` (`guarantees` field).

## Visual-first rules (most important)
The client reads the PDF in under 2 minutes. **Fewest pages, most visuals, least text.** Page count and file size don't matter; attention does.
- **Text budget per slide:** headline ≤ 8 words + one line ≤ 15 words + one impact line ≤ 12 words. Nothing else. No paragraphs, and no bullet lists on client slides.
- **Every slide has a visual anchor:** a photo, their own screenshot, a big number, a score ring, or a product mockup. Text alone is not a slide.
- **Show, don't tell:** use the real screenshot of the problem (browser warning, contact page, phone view) instead of describing it.
- **Facts as big-number tiles**, not sentences (`tiles`, `facts`, `metric`).
- **Show the product** as an HTML mockup with their own data (`offer.mockup`). Label it "Illustrative mockup".
- Merge rather than add: impact + score on one slide (`score_gaps`), proof + contact on one slide (`contact.proof`).
- Everything else (method, details, objections) goes in the sales notes, not the deck.

## Standard deck outline (8 slides + 1-page summary)
| # | Layout | Visual anchor | Example headline |
|---|---|---|---|
| 1 | cover + `photo` (full) + `client.logo` | Their own photo, their logo ("Prepared for") | `What shippers see\n*before they call you*` |
| 2 | statement + `photo` (right) + `tiles` | Their photo + 4 big-number tiles | `Fourteen tankers,\n*one phone line*` |
| 3 | score_gaps | Score ring + 8 mini bars + 3 gap cards | `45/100, *mostly lost on three things*` |
| 4–6 | finding (`image.size: large`, phone frame, or `filmstrip`) | Their own screenshot, load filmstrip, metric | `“24/7 tracking”\n*or 9 to 5?*` |
| 7 | offer + `mockup` + `modules` | Product mockup with their data | `A customer portal,\n*live in four weeks*` |
| 8 | contact + `photo` + `proof` | Generated brand background + proof strip | `Next step:\n*a 30-minute walkthrough*` |
| - | `summary` block (optional) | One-page PDF for the email | `Three things to fix\n*in this order*` |

## Colour & emotion (the story the colours tell)
| Moment | Slides | Feeling we want | Colour rule |
|---|---|---|---|
| Respect | cover, understood | Confident, warm, "they get us" | Dark canvas + brand orange. Photos graded warm (`--photo-grade`). No red. |
| Concern | score + gaps, findings | Honest, calm urgency, never panic | The score ring uses the brand colour. The grade tag reads "Needs attention", not "Critical". Red only on thin severity bars and in their own evidence screenshots. |
| Relief / hope | recommendation | "This is solvable, fast" | Brightest, warmest slide (`glow: strong`). Green only for positive states (Delivered ✓). |
| Energy | let's talk | Act now, low risk | Orange gradient CTA button; proof strip for trust. |
Never put the semantic "bad" red next to brand orange at the same size. They read as the same colour, and in colour-blind views both turn yellow.
Accessibility floor: WCAG 2.2 AA (`scripts/a11y_check.py`). Secondary text uses `--muted` (#A8A8A8 in the default theme), which passes AA on every background including the orange glow.

## Images (in this order)
1. **Theirs** (`scripts/prospect_assets.py`): their logo for the cover ("Prepared for"), their own photos (fleet, products, premises, team) for the cover and slide 2, and the Lighthouse load filmstrip. Nothing says "we looked at you" like their own truck.
2. **Real data as pictures**: the filmstrip (what a phone shows at 0.8s, 2.3s, 4.6s…), evidence screenshots (`evidence.py`), a search-results screenshot showing who appears instead of them.
3. **Free stock** (`fetch_image.py`): Unsplash or Pexels, only when they have no usable photos. Match industry and region; no other companies' logos; no recognisable faces.
4. **Generated abstract backgrounds** (`backgrounds.py`): on-brand topographic texture for the closing slide or when nothing else fits.
Never generate or fake photos of their business, people or premises. Photos set the mood; proof always comes from their own pages.
