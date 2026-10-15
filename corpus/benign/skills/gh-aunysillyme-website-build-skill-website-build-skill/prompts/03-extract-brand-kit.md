ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Turn my approved materials into a brand kit that a website builder can use and test.
Read my brief and the completed research before interpreting the assets.

INPUTS
- Prefer my current explicit guidelines, then approved source assets, then the live site.
- If none exist, ask for screenshots of my profile picture and banner.
- Do not infer permission to reuse someone else's logo, art, or licensed typeface.

EXTRACT
- Record source, date, method, and confidence for every observation.
- Inventory logo variants, typography, color values, spacing, imagery, and motion.
- Where source code is available, read actual styles instead of estimating pixels.
- Map primitives to roles: canvas, surface, text, muted text, accent, action, border,
  focus, error, and success. One visual role can have deliberate state variants.
- Find near-duplicate accents. Show the two values and where they occur before
  deciding whether they are a mistake or an intentional distinction.
- Compute contrast for actual text/background pairs and interactive states.
- Treat gradients, opacity, image overlays, and hover states as separate evidence.
- Record font and image license evidence; unknown ownership stays UNVERIFIED.

DECIDE
- Separate observed, inferred, approved, and conflicting rules.
- Translate the brand's words into concrete choices, with a reason and an alternative.
- Propose a minimal token set; do not turn every measured pixel into a new token.
- If a brand color fails contrast, propose accessible role or shade changes for review.
- Never silently replace the brand to make a score pass.

SAVE
- site-work/brand/BRAND.md: source priority, roles, rules, conflicts, approval state.
- site-work/brand/tokens.json: primitive and semantic tokens with provenance references.
- site-work/brand/contrast.md: pair, computed ratio, criterion, state, result, method.
- site-work/brand/asset-inventory.md: observed assets, source references, and rights questions
  for Graphics. Graphics alone writes the authoritative site-work/graphics/asset-rights.md.

FINISH
Show the proposed brand rules and ask me to confirm only unresolved visual choices.
Do not call inferred rules approved. Hand the approved kit to the three-mockup stage.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply the stage route and named checks in manifest.json before handing off.
