---
name: ui-craft-review
description: A pixel-level review skill for web and app UI craft. Pairs with the Dieter Rams design review skill: where Rams interrogates *whether the design respects the user*, this skill interrogates *whether the execution respects the craft*. Use when the user asks for a "UI review", "craft check", "design polish review", "does this look good", "is this tight", "review the typography/grid/colour/motion", or when evaluating the visual execution of a screen, component, or marketing page before shipping. Also use when comparing two visual directions on craft grounds, or when something "feels off" but the user can't say why.
---

# UI Craft Review

## The Principles

Where the Dieter Rams skill asks *should this exist?* and *does it serve the user?*, this skill asks *is it built with care?*. It draws on a lineage of practitioners who treated visual craft as a discipline: the Swiss modernists (Müller-Brockmann, Vignelli), the typographer's typographers (Spiekermann), the developer-friendly tactics of Wathan and Schoger (*Refactoring UI*), and the contemporary web craftspeople (Rauno Freiberg, Emil Kowalski, Benjamin De Cock at Stripe).

These ten principles compress that lineage into a checklist for web and app interfaces. Like Rams, not every principle bites equally on every review — focus on the four or five that matter most for the surface being reviewed.

### 1. Hierarchy is the first job

*Wathan & Schoger; Müller-Brockmann*

A well-designed interface tells the eye where to go in the first second. Hierarchy is built primarily with **size, weight, and colour/contrast** — not with borders, boxes, or decoration. If two elements compete for primary attention, one of them is wrong. If a destructive action has the same visual weight as the primary action, the design is dangerous, not just ugly. *In digital product: squint at the screen. What do you see first? Is that what the user needed to see first?*

### 2. The grid is the substrate, not the ornament

*Müller-Brockmann; Vignelli*

A grid is a rational ordering system that makes layout legible, not a decorative scaffold. Every element should land on it; deviations should be deliberate, not accidental. Consistency in column widths, gutters, and vertical rhythm produces what Müller-Brockmann called the "sense of compact planning, intelligibility, and clarity". The fewer the differences in size and alignment, the quieter and more trustworthy the design feels. *In digital product: do elements share alignment edges across the screen? Are spacing values from a consistent scale (4/8/16/24 etc.), or arbitrary?*

### 3. Typography is a system, not a choice

*Spiekermann; Vignelli*

Vignelli used six typefaces his entire career; Spiekermann argues there is no bad type, only inappropriate type. The job is not to pick a pretty font but to define a system: a small set of sizes, weights, and line-heights that map cleanly to roles (display, heading, body, caption, label). One typeface family done well beats three done casually. Letter-spacing, line-height, and measure (line length) matter more than typeface choice — body text wants ~45–75 characters per line and line-height around 1.4–1.6. *In digital product: can you list every distinct type style on the screen on one hand? If not, the system is leaking.*

### 4. Colour earns its place

*Wathan & Schoger; Vignelli*

A real colour system needs more than the five swatches a palette generator gives you — typically 1–2 primary hues with 5–10 shades each, plus a neutral ramp. Colour does work: it signals state, hierarchy, brand, and meaning. It should not be used decoratively or to "add interest". Design in greyscale first; if the hierarchy doesn't work in greyscale, colour won't save it. Saturated colours need careful pairing — pure brand colour against pure white is almost always too loud for body UI. *In digital product: is colour signifying something, or just present? Could you remove a hue without losing meaning?*

### 5. Whitespace is not empty

*Wathan & Schoger; Vignelli; Hara/Muji influence*

The fastest way to make a cramped UI better is to give it more room to breathe. Whitespace is the medium through which hierarchy is expressed. Generous padding around content blocks, ample line-height in text, and clear separation between unrelated groups do more for perceived quality than any decorative flourish. Conversely: information density done deliberately (Linear, dashboards, IDEs) is also a legitimate aesthetic — but only when the density is *systematic*, not accidental. *In digital product: does the design have a clear posture (spacious or dense)? Or is it accidentally somewhere in between?*

### 6. Details are the design

*Rauno Freiberg; "Devouring Details"*

Quality is not a layer applied at the end; it is the sum of decisions about edges, corners, transitions, states, and edge cases. A button with three carefully-considered states (rest, hover, active) and a snapped focus ring will outclass a "creative" button every time. Inputs need empty states. Tables need sort indicators. Numbers need tabular alignment. The 8-pixel gap between a row and an icon either is exactly right or it is wrong — there is no third option. *In digital product: pick one component on the screen and inspect its hover, focus, active, disabled, and loading states. Are they all designed, or only the first?*

### 7. Motion has a job

*Emil Kowalski; Benjamin De Cock*

Animation exists to (a) explain a change in state and (b) make perceived performance better than actual performance. It does not exist to decorate. Use **ease-out for things entering** the viewport (fast in, soft landing), **ease-in for things leaving**, **ease-in-out for things morphing on screen**. Default duration sits around 150–250ms — longer feels sluggish, shorter is missed. Linked elements (modal + backdrop, tooltip + arrow) must share timing and easing. Respect `prefers-reduced-motion`. *In digital product: if you removed an animation, would the interface be harder to understand? If no, the animation is decoration.*

### 8. Robustness over flourish

*Rauno Freiberg*

A polished detail that breaks under real-world stress is lipstick on a pig. Scroll fast — does the parallax stutter? Resize the window to 360px — does the layout collapse intelligibly? Open the longest possible string, the empty state, the error state, the loading state. Core interactions (scroll, text input, navigation, tap) must work 100% of the time before any flourish is allowed to exist. *In digital product: have you tried this with the longest realistic content, the slowest realistic network, and the smallest realistic viewport?*

### 9. Honesty about state and time

*De Cock; Spiekermann*

The interface should never lie about what it knows. Optimistic UI is fine — pretending a database write succeeded before it did is a craft choice that respects perceived speed (De Cock's "benevolent lie" at Stripe). But misleading affordances — disabled buttons that look enabled, links that look like buttons, empty states that look like loading states — are craft failures, not stylistic choices. Loading skeletons should match the shape of what's coming. Error messages should say what went wrong, not "Something went wrong". *In digital product: for every interactive element, is it obvious what will happen when I tap or click it? Does the system tell the truth about its state?*

### 10. The system makes the screen

*All of them, especially Vignelli*

A great screen is a manifestation of a coherent system, not a clever one-off. Spacing values, type styles, colours, radii, shadows, and motion timings should all be drawn from a small, named set of tokens. When a new component needs a new value, that value should be deliberately added to the system, not invented in-place. Vignelli: "design without discipline is anarchy". *In digital product: if you handed this screen to another developer/designer, could they add a new section that looks like it belongs without making a single arbitrary decision?*

## When To Use This Skill

Trigger when:
- The user asks for a UI review, craft review, or design polish check
- The user is comparing two visual executions of the same idea on craft grounds
- The user says "does this look right?", "is this tight?", "what's off about this?", "craft check", "UI review", "review the typography/grid/colour/motion"
- A component has been built and the user wants a pre-ship critique
- The user wants to identify *why* a UI feels unfinished or amateurish

Do not use when:
- The user is asking *whether to build something* or *whether the UX is right* — that's the Rams skill
- The user wants new UI generated from scratch — that's a UI-generation skill such as frontend-design
- The question is about user research, copy, or product strategy

## Workflow

### Phase 1: Observe the surface

Before applying principles, understand what you're reviewing.

1. If it's a live page, look at it — take a screenshot via the browser tools if available
2. If it's code, read the component(s) so you understand the structure
3. Identify the **surface type** — this matters because the principles weight differently:
   - **Marketing page**: hierarchy, typography, motion, and whitespace dominate
   - **Product app screen**: hierarchy, system consistency, robustness, details dominate
   - **Data-dense interface (dashboard, table)**: grid, typography, density discipline dominate
   - **Single component (button, input, modal)**: details, motion, robustness dominate
4. Identify the **posture** the design is trying to take — premium/spacious (luxury and hospitality brands), dense/utilitarian (tools, dashboards, training logs), confident/editorial (studios, publications), or playful (consumer-app feel). Critique within the posture, not against it.

### Phase 2: Apply the principles

Walk through the 10 principles. For each one that's clearly relevant to the surface, provide:

- **Verdict**: Pass / Tension / Fail
- **Observation**: A specific, pixel-level statement of what's there — measurements, weights, hex values, timings where you can
- **Recommendation**: The smallest change that would resolve it

Use the same scoring as the Rams skill:
- **Pass**: The execution satisfies this principle
- **Tension**: Partial — there's a specific conflict worth naming
- **Fail**: The execution actively violates the principle

Skip principles that don't bite for this surface — a static blog post doesn't need a motion review. Be ruthless about relevance; an over-long review is itself a craft failure.

### Phase 3: Synthesise

1. **Headline verdict** — one sentence. Something like "This screen is 80% there but the hierarchy is fighting itself" or "The grid is doing all the work; the typography hasn't shown up yet"
2. **The one thing to fix** — if only one change is possible, what has the highest leverage?
3. **What's already working** — name two or three things specifically. Designers and developers respond to specific praise; vague praise reads as filler
4. **Priority actions** — ranked list, highest impact first. Each action should be small enough that someone could ship it in under an hour

## Tone

- **Be specific, not poetic.** "The 14px label sits 4px too close to the 24px heading; needs ~12px of space to read as a separate group" beats "the spacing feels a bit tight".
- **Reference the principle.** "Principle 4 (Colour earns its place): the brand teal is doing decorative work on the badge here — it should be reserved for primary actions" is more useful than naked opinion.
- **Use real measurements and tokens.** Talk in px, rem, hex, ms. If the design system has tokens, use the token names.
- **Name trade-offs honestly.** Density vs. whitespace, motion expressiveness vs. perceived speed, brand colour vs. neutral UI — these are real tensions, not failures.
- **Less is more.** Don't deliver a 30-bullet review when 6 sharp ones would land harder. Cut anything that doesn't change a decision.
- **Acknowledge posture before critiquing.** If the surface is spacious and premium (a luxury booking site), don't critique it for not being information-dense. If it's a utilitarian tool (a training log), don't critique it for not being editorial.

## Example application

When reviewing a property card on a search results page:

**Principle 1 (Hierarchy is the first job): Tension** — The property name (18px semibold) and the price (16px semibold) read at near-identical visual weight. On a search results page the booking-critical scan order is name → location → price → rating → capacity. Either lift the name to 20px or drop the price to 14px regular until it's queried.

**Principle 3 (Typography is a system): Pass** — Three type styles on the card, all from the same family, all from the established scale. No casual additions.

**Principle 6 (Details are the design): Fail** — The favourite icon has no hover state and the focus ring is the browser default. The card hover lifts 4px with a shadow change but the inner content stays static — feels like a sheet of paper being nudged rather than a tactile object. Add a `transform: translateY(-2px)` to the title or image to give the hover some internal life, or remove the lift entirely.

**Principle 8 (Robustness over flourish): Tension** — Property names over ~38 characters wrap to a third line and break the card's vertical rhythm. Either truncate with an ellipsis at line 2 or commit to a min-height that absorbs three lines gracefully across the grid.

---

**Headline:** The card system is well-built but its hierarchy needs sharpening — the price is currently competing with the name for first attention.

**The one thing to fix:** Drop the price weight from semibold to regular and shrink to 14px so the name leads cleanly.

**What's already working:** Tight typographic system, consistent 16px internal padding, the image-to-content ratio gives the card a confident posture.

**Priority actions:**
1. Re-weight the price (Principle 1)
2. Add hover/focus states to the favourite icon and a proper focus ring to the card (Principle 6)
3. Decide a wrap policy for long names and apply it consistently (Principle 8)
