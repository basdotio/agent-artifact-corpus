# Warm Playful (from Pastily, an indie desktop-app landing)

**Why it works:** Every other direction here is cool, hard-edged or dramatic. This one is *friendly and premium at once*: warm off-white paper, near-black ink, one muted green that drifts into gold only inside gradients, big 28px-radius white cards that sit on the page with a whisper of shadow, and a hand-drawn layer (Caveat notes, arrows, a mascot) that makes it feel made by a person. Restraint comes from tone, not from darkness. The product is the hero: a real OS screenshot or recording, not an abstract render.

Pick it for: desktop/menu-bar apps, utilities, indie and solo-founder products, consumer or prosumer tools, one-time-purchase software, anything where "trustworthy and nice" beats "futuristic". Avoid it for enterprise/AI-infra pitches (use Ember Dark) or luxury services (use Editorial Mono).

## Tokens

```css
:root{
  --page:#F5F5F3;        /* body */
  --cream:#FAF6ED;       /* warm section / story card 2 */
  --mint:#F1F5EC;        /* pale green story card 3 */
  --card:#FFFFFF;
  --ink:#1D1D1F;         /* headings, wordmark (Apple near-black) */
  --ink-2:#2D2F33;       /* body */
  --ink-3:#6E6E73;       /* secondary */
  --line:rgb(0 0 0/.08);
  --accent:#4A7A3C;      /* eyebrow labels, check marks, links: muted green, 5.1:1 on white / 4.6:1 on --mint */
  --accent-soft:#5E8F4E; /* lighter green for icon fills, nav download dot, illustration; never for text (3.8:1) */
  --g-0:#12211A; --g-1:#1B2F22; --g-2:#3F5A34;   /* deep green ramp */
  --gold-1:#8A7A3A; --gold-2:#C99A3F;            /* gradient end only, never flat fills */
  --cta-grad:linear-gradient(100deg,var(--g-0) 0%,var(--g-1) 30%,var(--g-2) 52%,var(--gold-1) 76%,var(--gold-2) 100%);
  --dark-btn:linear-gradient(#2A2A2A,#0A0A0A);
  /* semantic highlight colors, used ONLY on keywords in story text. All ≥4.6:1 on --card, --cream and --mint.
     The bright originals (#2FD07F, #4A9BEA, #A66BEF) read only 2.0–3.5:1 on these backgrounds; don't use them. */
  --k-copy:#1F7A4A; --k-link:#1E6FC2; --k-code:#7B44C9;
  --soft-shadow:0 1px 2px rgb(0 0 0/.03),0 8px 28px -12px rgb(0 0 0/.08);
}
```
- **Fonts:** a rounded grotesk for display plus a clean sans for body plus a handwriting face for notes only. Google equivalents: **Nunito** (800) or **Figtree** (800) for headings, **Rethink Sans** (400/600) for body, **Caveat** (400/600) for annotations. Max three families; Caveat appears in short labels only, never in paragraphs.
- **Display:** H1 60px / weight 800 / `letter-spacing:-2px` (about −0.033em) / line-height 63px, in `--ink`. Section H2: `clamp(36px,4.4vw,56px)` / 800 / −0.03em. Eyebrow: 11px / 600 / `letter-spacing:.025em` / `--accent`, plain text (no pill) above headings. Body 16px `--ink-2`.
- **Radii:** 999px buttons and nav pill, **28px** cards and the video card, 24px CTA gradient button, 16/12 inner chips.
- **Buttons:** dark pill = `--dark-btn` gradient, `1px solid rgb(255 255 255/.08)`, `padding:16px 32px`, 15px/600, white text. Big green CTA (pricing) = `--cta-grad`, radius 24px, `box-shadow:inset 0 1px 0 rgb(255 255 255/.12),0 18px 40px -16px rgb(0 0 0/.6)`, 19px label with an arrow.
- **Accent budget:** green appears on eyebrow text, check icons, one CTA gradient and keyword highlights. Gold exists only at the end of that gradient: no gold stars, swatches, strokes or icon fills (use `--ink` for rating stars).
- **Keep the green.** The muted green is part of what makes this direction read calm and trustworthy. Swap it only when the user names a brand color or the product already has one. Mood words in the brief ("cozy", "sleepy", "dusk", "warm") are not a reason to swap; carry the mood with copy, illustration and the warm neutrals instead.

## Signature pieces

1. **Product bleeding off the left edge.** The hero is a two-column split. The device mockup (laptop with real macOS/Windows chrome: menubar, dock, an open app menu) is wider than its column and runs off the viewport's left edge; copy sits right: badge row, tiny status line with a pulsing green dot ("v2.2 is here: Notch Island"), app icon, H1, subcopy, dark CTA, price line ("$8.99 · One-time purchase"), then "Also on" platform chips. Recipe in `shared/product-proof.md`.
2. **Handwritten annotations.** A Caveat note with a hand-drawn curved arrow pointing at the product ("open control", "hey, click me!") placed beside the app icon and the menu. Recipe in `shared/components.md`.
3. **Section-aware pill nav.** A black pill nav that collapses on scroll into a tiny pill showing the current section name and a round green download button. Recipe in `shared/components.md`.
4. **White video card.** After the hero, one big white 28px-radius card with a short H2 ("Copy anything.") and a screen recording inside a device frame, with sound and pause buttons bottom-right. Scrolling swaps the headline ("Every copy, remembered.") if the video has chapters.
5. **Bento of soft white cards** with live mini-UIs (typing search, ring countdown, a lock). Caps heading, 11px grey body. Cells of unequal width on a 12-col grid, 12–16px gap. `--soft-shadow`, no borders.
6. **One black interlude.** A single full-bleed black section (a pinned wall of UI chips that scales as you scroll, closing with a white headline over it) breaks the warm page and makes the return to cream feel earned. Recipe in `shared/product-proof.md`. Use at most once.
7. **Story card stack** with tone shifts and colored keywords (`shared/motion.md` and `shared/typography.md`).
8. **Photo-backed pricing**: full-bleed landscape photo or looping video behind a single white price card; falling particles (leaves, snow, dust) matching the photo. Recipe in `shared/components.md`. No photo or video available? Use the **plain single-price card** from the same file instead: one white card, still one price, still the gradient CTA. A free trial is a line inside that card, not a second card.
9. **Giant footer wordmark** over the same photo, fading in from the page color (`shared/components.md`).

## Mascot (optional but powerful)

A tiny character (the app icon with a face and arms is enough) repeated at the end of story lines in 5–6 different poses (holding a cup, magnifying glass, sleeping). If image generation is available, generate one pose sheet with a transparent background and reuse it. If not, skip the mascot and use the app icon at 28px; don't draw a clumsy SVG character.

## Page rhythm

hero → white video card → soft bento → "what's new" headline + dark showcase frame → black chip wall → **story card stack** → gallery on dark rounded frame → trust/security band on cream → reviews slider → FAQ (tabs + sticky side) → photo pricing (or the plain single-price card) → footer with wordmark. Backgrounds alternate `--page` / `--cream` / one black / one photo; most sections end with generous 140–176px padding.

## Don'ts specific to this direction

- No glows, no neon, no glass blur beyond the nav. Light comes from soft shadows.
- No second accent color. Keyword highlights default to `--k-copy` (green) only. Add `--k-link` blue or `--k-code` purple only when the product literally handles links or code (a clipboard manager, a dev tool), one word each, never on UI chrome, icon chips or bento tiles.
- Don't set body copy in Caveat, and don't use more than two annotation arrows per viewport.
