# Directions

Each folder is one visual direction measured from a real top-selling template. Load only the folder you picked. Swap the accent hue only when the brand actually has a color (the user names one, or the product already uses one); a mood word in the brief is not a brand color. When you do swap, keep the *structure* (how many neutrals, which opacities, which radii) intact. That structure is what makes it work.

| Folder | Source |
|---|---|
| `ember-dark/` | OptimAI |
| `tactile-light/` | Aigocy |
| `editorial-mono/` | Adon |
| `noir-spotlight/` | Davies |
| `warm-playful/` | Pastily |

## Swapping the accent

Only for a real brand color (see above). Warm Playful keeps its muted green unless that is the case: "cozy", "dusk" or "sleepy" is carried by copy and illustration, not by a new accent.

Keep lightness/chroma similar to the original and use OKLCH to rotate hue:
- Ember: orange `oklch(70% .2 50)` → blue `oklch(68% .17 255)` → violet `oklch(62% .22 295)` → green `oklch(75% .2 150)`.
- Always regenerate the *glow* color as a more saturated, darker sibling of the accent (glows look best at very high chroma because blur dilutes them).
- Re-check contrast of any text placed on the accent.

## Adding a new direction

1. Create `directions/<kebab-name>/style.md` with this outline:
   - `# Name (from <reference site>)` and a **Why it works** paragraph.
   - `## Tokens`: one `:root{}` block, then Fonts, Radii, Signature pieces.
   - One `##` section per technique that only this direction uses (copy-ready CSS/JS, each with a one-line *why*).
2. Anything that more than one direction can use goes into `shared/`, not here, so a fix only has to be made once.
3. Add a row to the direction table in `SKILL.md` (feel, best for, source) and to the table above.
4. Optional: drop reference screenshots in the same folder (`ref-hero.jpg`, …) and mention them in `style.md`.
