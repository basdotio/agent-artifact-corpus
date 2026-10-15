# <Brand> brand profile for video

The brand, the owner's standing choices and the films made so far. Every new film reads this first and only asks what is new. Each film prompt points here and only adds its story.
Sources: <brand folder | codebase | live site capture (`hyperframes capture`, date)>, <rules files>, product owner notes. When this file and the brand's own files disagree, the brand's files win.

## Owner choices (standing: reuse for every film unless they say otherwise)
- Where films play: <Reel / TikTok 9:16 | launch 16:9 | square>. Usual length: <s>. Language: <fr | en | ar (rtl)>. Audience: <who>.
- Music: <generated trap / punchy bed (synth.py), key, tempo | their track, licence | silent>.
- Tone: <confident | warm | premium | playful>. The brand's loop in three statements: <1.> <2.> <3.>
- Ending: <tagline, call to action, URL, handle>.
- Notes from past films that apply to all: <"less text", "faster", "no ambient music", ...>.

## Chosen by Claude (the owner can overrule)
- <palette, fonts, tone or anything picked because they said "you choose for me", with the date>.

## Assumed, not asked
- <choices made because the user said "just go">.

## Films
| Film | Type | Date | Owner's reaction, what changed |
|---|---|---|---|
| | | | |

## Assets on file (reusable across films)
| Asset | Path | Notes (size, rights, consent) |
|---|---|---|
| Logo | | SVG / PNG |
| Product photos | | |
| Screenshots, recordings | | |
| Music, voiceover | | licence |

## Brand moment: what bends, what never does
- Bends for video: pace, light (env map, bloom on the accent), depth (fog, particles), 3D, camera, transitions, grain, motion blur, HUD.
- Never bends: the palette (<hexes>), the one accent as the one highlight, the logo files and their build, the fonts, the voice, the claims, correctness of anything shown.
- Brand graphic pack used as stickers and slams: <phrases, shapes, icons from the brand's pack>.

## Hard rules
<!-- Every rule with its source. Capture what the product says; do not copy another product's rules. -->
- Casing: (source)
- Type: <type styles, where mono is allowed> (source)
- Corners: <radius token> (source)
- Surfaces: background `<token>`; other surfaces only where the product has them: <which> (source)
- Borders and shadows: <what the product does> (source)
- Copy: <dashes, reading level, banned words> (source)
- Claims: see "Claims".

## Frame (<width>x<height>, 60 fps, <dark|light>)
- Framing: <full bleed | the product's own framing> (source or default)
- Safe zone: <none | social 9:16: top 250, bottom 420, left 60, right 120> (social.md)
- Words: <punchline or caption style from the interview: font, weight, size, accent>.
- Scenes: UI text only unless captions were chosen; read content 100 px from the edges.

## Color
| Token | Value | Use |
|---|---|---|
| background | | |
| foreground | | |
| muted foreground | | |
| surface | | only where the product shows one |
| border | | only where the product uses one |
| accent | | |
| status tones | | pass / warn / fail, from the product |

Hex only for anything that animates.

## Type
- Fonts: the source files, copied to `assets/fonts/` with an `@font-face` each:
- Math: <KaTeX | the product's math font | none>. Right-to-left script: <font, rules>.
- Sizes at the delivery size: words __ px, headline __ px, UI 24+ px at 1080p.

## Signature elements
| Element | Look | Source | In films |
|---|---|---|---|
| Buttons (and their loading state) | | | keeps its width while loading |
| Status markers or badges | | | |
| Loader or spinner | | | frame-driven, frames every __ ms |
| Brand and partner icons | | | inline with names |
| Texture or pattern (if any) | | | calm behind UI |

## Logo and brand element
- Logo: (SVG path or component). Animation used: (draws itself / reveal / none).
- Mascot or character: (only if the product has one and the user chose it) model or asset, what drives it, its looks and poses.
- Never: (anything off brand).

## Cursors (if chosen)
- User: the OS arrow. Product: <its own cursor, if it automates> (source).
- A click = a short squash, then the target reacts.

## Components
| Need | Component (path) | In films: import / twin / redraw, and why |
|---|---|---|
| | | |

## Motion
- Durations and easing tokens from the product, as `PF.ease("cubic-bezier(...)")`: (values, source).
- Does the brand blur, overshoot, bounce? (If not, the words theme sets `blur: 0`.)
- The one highlight (if the brand has one): what it is, how it lands, how often.
- Transitions chosen: (magic moves / camera / cuts), and their rules.

## Claims
- What the product does (films may show):
- What it never does (films must not show):
- Approved lines:
- Words to avoid:

## Workspace
- Folder (`videos/<film>/`), HyperFrames version (pinned in `package.json` by init), vendored runtimes (GSAP, KaTeX), fonts, how components are brought in (copied markup, twin, static export), scripts used (setup, synth or beats + audio-edit, place-audio, beat-sheet, stills, render, verify).
