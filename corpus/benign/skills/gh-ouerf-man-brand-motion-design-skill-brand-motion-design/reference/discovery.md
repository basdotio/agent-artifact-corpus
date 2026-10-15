# Discovery: learn the product before drawing a frame

The film is judged against the product's own look. Collect it first, write it down, and treat it as law. Output: `videos/BRAND.md` (template: `templates/BRAND.md`), and `findings.md` if you use planning files.

## Four starting points

First, look for a saved profile: `videos/BRAND.md` from an earlier film. If it exists, it is the brand; only refresh what changed.

- **Nothing** (a small business with no brand book or site): the brand round of the interview ([interview.md](interview.md)), with "You choose for me" on every question; read the logo they send for its colours.
- **A brand folder** (a brand book, `tokens.css`, logos, fonts, a graphic pack): read it all; it is the law. Look for the brand's pack of stickers, shapes and phrases: those become the film's stickers and slams.
- **A codebase:** the sweeps below.
- **Only a website URL:** capture it, then read the capture like a brand folder.

```bash
npx hyperframes capture https://example.com -o videos/_capture --json --max-screenshots 16
```

  - Hard stop on a non-zero exit, `"ok": false` or a `BLOCKED.md` in the output (sites behind bot protection, sandbox network rules): never build from a partial capture. Retry once into a fresh folder with `--timeout 60000`; if it still fails, ask the user for a brand folder, the logo SVG and the font files, or screenshots.
  - `screenshots/contact-sheet.jpg` first: the whole page at a glance (layout, where colour sits, the hero).
  - `extracted/tokens.json`: colours, fonts, headings, CTAs. Rank colours by how much area they cover on the screenshots: the background, the ink, the one accent. Never take a colour that only appears in a third-party widget.
  - `extracted/design-styles.json`: type scale, button, card and nav styles, radius, shadows.
  - `extracted/visible-text.txt`: the hero line, the product's own words for what it does (the source of the three-statement loop and the tagline), claims to respect.
  - `assets/` (fonts, SVGs, images, with `extracted/asset-descriptions.md`): the logo as SVG if it is there (prefer the header SVG over a raster), the font files for `assets/fonts/`. If only a raster logo exists, use it as a flat card and say so; never redraw a logo.
  - Write what you took and from where into `BRAND.md`, marked "from the live site on <date>", so the owner can correct it.

## Where to look

Run 3 or 4 read-only sweeps in parallel (Explore subagents), one topic each, and ask each to return paths, values and quotes. Do not ask for opinions.

1. **Rules and voice.**
   - Files: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `CONTRIBUTING.md`, `BRAND.md`, `brand/`, `docs/brand*`, `docs/design*`, `DESIGN.md` or `frame.md`, style guides, `DOCUMENTATION.md`.
   - Linked sources the rules files point to (a Notion or Drive brand page), if a connector can read them.
   - Memory notes, if the harness has them.
   - Extract, with the source of each rule:
     - hard rules (casing, dashes, reading level, banned words)
     - design rules (radius, borders, shadows, mono usage, letter spacing)
     - claims and legal limits, approved taglines
2. **Tokens.**
   - Files: the global CSS (`globals.css`, `@theme`, CSS variables), the Tailwind config, theme files.
   - Extract: background, foreground, muted, card, border and accent in dark and light, plus hover and pressed states.
   - Also: radius, fonts (the files, not just the names: the film needs local copies), and the motion tokens: durations, `cubic-bezier` curves, springs (grep `cubic-bezier`, `spring`, `transition`, `duration`). The film uses these exact curves through `PF.ease`.
   - A brand token file (`tokens.css`, `tokens.json`) wins over what the app happens to use.
3. **Components and signature elements.**
   - Button variants, markers or status glyphs, stamps, badges, spinners and loaders (and how submit buttons show loading), avatars, toggles, cards.
   - Brand icons for partner names, and the logo (SVG, component or model).
   - Anything the landing page uses as a signature: dashed outlines, dithers, hatch bands, ornaments.
   - For each: path, props, and whether it runs its own clock (motion libraries, `requestAnimationFrame`, `setInterval`, CSS keyframes, shader libraries, async image state). Animated SVG logos usually animate with CSS keyframes: they need a frame-driven twin.
4. **Features on screen.**
   - For each feature the film will show: the real screen or component, its copy, and the states it moves through.
   - Also the demo data the landing already uses, and any fake-data preview routes.
5. **Old video work, if any:** what to keep, what was tried and dropped, licenses of music and SFX.

## Tour the live site

If there is a live site, open it in a browser at desktop width (and at phone width for a social cut). No site yet (a pre-launch product)? Use the brand book, mockups and app screens instead.
- Scroll every section.
- Note in `findings.md` right after every two screenshots: layout (framed or full bleed?), colors on screen, type sizes, how CTAs look and press, animated demos, how the logo (or any character) moves, how partner logos are shown.
- Screenshots do not persist, so write findings down right away.

## The logo and any brand element

- Find the logo as SVG (paths you can draw on), plus any animated version: an SVG with CSS animation, Lottie, Rive, or a component driven by code. Read its spec (durations, curves, order) so the film's build matches it.
- Note whether the product has a mascot or character. Only then can one appear in the film, and only if the user asks for it (a showreel uses the logo build at the end by default).
- If a mascot is chosen and has a model or animation code, find its pure functions and drive them from `t`. Never render anything that runs its own clock. If only an SVG exists, animate its transforms from `t`.
- Note the brand's rules for the logo in motion and in video (which file on dark, where the build may appear, what it must never do).
- If anything animates, render a pose sheet still before scene work.

## Feed the interview

Stop discovery once you can write the product loop in three statements and name the palette, the fonts, the logo file, the accent (the one highlight) and the brand's graphic pack. Then run the interview (interview.md). Finish discovery on what the user chose.

## Write BRAND.md

Fill `templates/BRAND.md`.
- Every rule cites its source (file path or product owner quote).
- Keep a "Components" table: import as is, frame-driven twin, or redraw, with the reason.
- Keep a "Claims" section: what the product does, what it never does, approved lines.
- Where the product says nothing, use the craft defaults in `SKILL.md` and mark them as defaults so the product owner can overrule them.

## Ask when it matters

Ask the user (AskUserQuestion) only for choices the code cannot answer:
- the audience and where it plays
- which features to show
- the music (and its license)
- anything the brand rules contradict each other on
