# Noir Spotlight (from Davies)

**Why it works:** Pure black + one neon accent gives maximum contrast and a nightlife/tech feel. The giant name interacting with a photo (solid behind, outline in front) creates depth with zero 3D. Motion (shader ripple, marquee, stacking cards) does the heavy lifting.

## Tokens

```css
:root{
  --bg:#000; --bg-2:#0A0A0A; --card:#111; --card-2:#191919;
  --fg:#fff; --fg-2:rgb(255 255 255 / .6); --line: rgb(255 255 255 / .1);
  --accent:#07C42C;   /* neon green; alternatives: #D4FF3A lime, #2AC6F8 cyan */
}
```
- **Fonts:** Figtree (or Outfit) 500–600; hero word 260–300px, uppercase, tracking ~0; small caps nav at 11–12px with +0.04em tracking.
- **Signature pieces:** preloader with accent-colored vertical bars wiping away; hero = huge wordmark + B/W portrait (outline-over-photo, below); an accent block as a blinking "_" cursor after the name; brand names with a trailing underscore ("Nexbot_"); WebGL background (own Three.js shader from `shared/webgl.md`, a Unicorn Studio embed, or a CSS/SVG turbulence fallback); big-type marquee; full-width project cards that *stack* (sticky) as you scroll (`shared/motion.md`); white pill CTA.

## Outline-over-photo hero word

```html
<div class="name-hero">
  <h1 class="word">DAVIES</h1>
  <img class="portrait" src="…bw portrait…" alt="">
  <h1 class="word outline" aria-hidden="true">DAVIES</h1>
</div>
```
```css
.name-hero{position:relative;display:grid;place-items:center}
.name-hero>*{grid-area:1/1}
.word{font-size:clamp(80px,21vw,300px);font-weight:500;line-height:.8;color:#fff;letter-spacing:-.02em}
.portrait{width:28%;aspect-ratio:3/4;object-fit:cover;filter:grayscale(1) contrast(1.1)}
.word.outline{color:transparent;-webkit-text-stroke:1px #fff;
  clip-path:inset(0 36% 0 36%)}   /* match the portrait's horizontal span */
```
**Diacritics:** `line-height:.8` puts the second line's accents (Á, Ő, Ű, Ä...) into the first line, and any `overflow:hidden`/SplitText `mask` on the lines clips them. Names are often Hungarian/Czech/Nordic, so use `line-height:.92` or more when the text has capitals with accents (check the real name, not DAVIES), give each line `padding-top:.18em; margin-top:-.18em` instead of a tight box, and never mask hero lines whose glyphs carry accents; reveal them with opacity + `y` instead.

Letters are solid outside the photo and *outlined* where they cross it. Add the accent block after the word: `<span class="caret"></span>` with `width:.35em;height:.08em;background:var(--accent);animation:blink 1s steps(1) infinite`.

## Big-type marquee

"Selected Work ◎ Selected Work ◎" at 120px, 500 weight, with an inline SVG wireframe globe as separator. Same track mechanics as the logo marquee in `shared/components.md`.

## Preloader

3–5 accent-colored vertical bars that scale to 0 on `transform-origin: top`, staggered 0.08s, total under 1.2s. Portfolios/agencies only; on SaaS pages it slows conversion.

## Custom cursor

A 12px dot with `mix-blend-mode: exclusion; background:#fff`, scaled ×4 over links. Disable on `(pointer: coarse)`.
