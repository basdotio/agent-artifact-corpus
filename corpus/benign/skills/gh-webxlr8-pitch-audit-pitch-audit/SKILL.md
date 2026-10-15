---
name: pitch-audit
description: Turn any prospect's website into a short, visual pitch deck PDF from YOUR company. Audits the site (speed, SEO, mobile, trust, conversion, social, AI search, ops signals), researches the business, scores the gaps, maps them to your offers, and renders one PDF that looks identical in WhatsApp and email, plus internal sales notes. First run sets up your company profile from your own website. Use when the user wants to set up their company for pitching, or shares a prospect URL or lead list and asks to audit, analyse, pitch, prospect, or create a proposal/report/deck.
---

# pitch-audit

- **This skill** is generic: audit, scoring, layouts, rendering, checks.
- **The company profile** says who is pitching: `./pitch-profile/` or `$PITCH_PROFILE`, holding company, catalog, mapping and proof YAML plus `brand/`.
- **Scripts** live in `scripts/` under this skill folder: `${CLAUDE_PLUGIN_ROOT}/skills/pitch-audit` as a plugin, `.claude/skills/pitch-audit` when copied. Run them from the project root.
- **Per-prospect output** goes to `clients/<slug>/`.
- **Machine setup, company setup, tool options and check details:** `references/setup-and-tools.md`. If `pitch-profile/company.yaml` is missing, do company setup first.

## Rules
1. **One deck, one brand: yours.** Your products appear by name and logo, in your colours.
2. **About 8 slides, each built on one visual:** their photo, their screenshot, a big number, the score ring, the load filmstrip or a product mockup. Headline ≤ 8 words, one line ≤ 15, impact ≤ 12. Details go in the sales notes.
3. **One recommendation, one first step.** Other offers go in one `next` line.
4. **Honest and kind.** Every number comes from the audit, scores, manual facts or the profile. Prices, guarantees and results only as written in the profile. Criticise the website, not the people.
5. **Written about this prospect.** Sentence-case headlines in varied shapes; no stock phrases (`references/copy-voice.md`).
6. **Send only what passed `build.py`.** One flattened PDF, safe on WhatsApp and email.

## Workflow per prospect
1. **Prepare** (one command, about 1 minute; run in background): `python3 scripts/prepare.py <url> clients/<slug>`. The audit runs in parallel with their logo and photos, then the filmstrip, score and a background. Exit 2 means unreachable or parked: confirm the URL.
2. **Research** → `research.md` (`references/business-research.md`).
3. **Facts + score**:
   - Write `manual.json` (`references/audit-rubric.md`) with verified facts and visual `extra_findings`.
   - Run `python3 scripts/score.py clients/<slug>`. Fix false positives in `manual.json`.
4. **Lead offer**: pick one, using `references/offer-selection.md` and `mapping.yaml → guidance`.
5. **Visuals**:
   - Theirs first, already collected by `prepare.py`: their logo, their photos and the load filmstrip. Look at `images/prospect-photos.png` and pick.
   - Evidence: `scripts/evidence.py` captures proof from their pages.
   - Fallbacks:
     - free stock photos (`fetch_image.py`) only when they have no usable photos
     - `backgrounds.py` for texture
   - Never fake photos of their business.
6. **deck-data.json**:
   - Follow `references/deck-data-schema.md` and the outline in `references/copy-voice.md`: cover → what we understood → score + 3 gaps → 3 gap slides → recommendation with product mockup → next step + proof.
   - Style:
     - `style-1`: dark; tech, logistics, SaaS
     - `style-2` "Editorial": light, serif; hospitality, food, professional and traditional businesses
   - Every image needs an `alt`. Mockups are labelled "Illustrative mockup".
7. **Build**: `python3 scripts/build.py clients/<slug>`. It runs lint (facts, word budget, slop) → render → WCAG 2.2 AA → viewer checks.
   - Then read every `previews/slide-XX.png` yourself. Look for clipped text, empty areas, busy photo behind text, a single word alone on a line.
8. **Sales notes** (internal) → `sales-notes.md`:
   - lead score + offer, decision maker
   - why now (3), objections → answers (3), first offer
   - follow-up email (< 150 words), WhatsApp opener (< 50 words)
   - risks
9. **Report**:
   - Send the PDF (SendUserFile).
   - Give the score, top 3 gaps, lead offer, lead score and anything unverified.

Lead lists: `scripts/batch.py leads.csv --audit`, then steps 2–8 per client (subagents, max 4 in parallel), then `batch.py leads.csv --rank`.

## Never
- Invent metrics, reviews, follower counts, client results, prices or guarantees.
- Log in, bypass bot protection, or crawl aggressively.
- Put sales notes or internal profile notes in the deck.
