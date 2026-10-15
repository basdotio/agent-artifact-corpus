# Editorial Mono (from Adon)

**Why it works:** Confidence through subtraction. Two colors, one huge grotesk, no shadows at all. The *hairline grid* (visible 1px column/row lines, `shared/light.md`) makes the layout feel architected. Scroll-scrubbed text fill (`shared/typography.md`) turns reading into an interaction.

## Tokens

```css
:root{
  --bg:#F0F0F0; --bg-2:#FFFFFF;
  --ink:#111111; --ink-body:#555555; --ink-mute:#999999;
  --line: rgb(17 17 17 / .10); --line-2: rgb(17 17 17 / .20);
  --dim: rgb(17 17 17 / .30);   /* un-filled scroll text, dimmed words */
}
```
- **Fonts:** a neo-grotesk for display (BDO Grotesk in the original; free near-matches: "Inter Tight", "Schibsted Grotesk", "Hanken Grotesk", "Familjen Grotesk") at weight 400 (not bold!), DM Sans for body.
- **Type scale:** hero 140px / lh 120px / −0.07em (−9.8px); section 90px / lh 85px / −0.05em; small labels 14–16px, often in parentheses like "(2017)" or "(Click to play reel)".
- **Radii:** 20px media, 30px big media, 500px pills. **No box-shadows anywhere.**
- **Signature pieces:** layout framed by 1px vertical lines at the page edges and between header cells; nav as a plain vertical list inside a bordered cell; a dimmed word inside the hero headline ("marketing" at 30%); scroll-fill paragraphs at 90px; black progress bars of varying heights with % labels; big stats ("130+") in display type; showreel thumbnail with play circle; custom cursor (below).

## Custom cursor

A 12px dot with `mix-blend-mode: exclusion; background:#fff`, scaled ×4 over links. Disable on `(pointer: coarse)`. Agency/portfolio pages only.

## Progress bars

Black bars of varying heights (`height: var(--v)` on a flex row aligned to the bottom), each with a "%" label in display type above it. Grow them from `scaleY(0)` with `transform-origin:bottom` on enter, staggered 0.08s.
