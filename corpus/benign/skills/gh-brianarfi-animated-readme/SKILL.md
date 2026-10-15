---
name: animated-readme
description: Write or rewrite a GitHub README so a visitor gets it in ten seconds, with animated GIFs rendered from HTML (hero, before and after, how it works) and alt text for each. Use when someone wants a better README, a README with GIFs or a demo, a project page that shows what the project does, or to re-render README animations after the copy changed.
---

# animated-readme

The loop: read the project, write the copy, fill the scenes in `readme-scenes.json`, render the
GIFs, assemble the README, and show it to the user before anything is committed or pushed.

`KIT` below means this folder (`.claude/skills/animated-readme/` in an installed project).

## Steps

1. **Read the project before writing a word.** The current README, `docs/`, the package or
   project file, the entry points, the CHANGELOG and the last releases. Write down three things:
   who uses it, what they do with it, and what is true today. A feature that is planned, half
   done or only on a branch is not "what it does".
2. **Write the copy** to `KIT/docs/writing-guide.md`. It sets the README order, the voice and
   the words to avoid. Draft the copy in the chat first and keep it short.
3. **Ask which style, and show the gallery.** Do not pick a look for the user. Copy
   `KIT/assets/style-gallery.html` somewhere they can open (in an AI Second Brain workspace, into the
   workspace, for example `inbox/<date>-style-gallery/index.html`) and give the **absolute** path. Ask
   in plain words: "Open this, click the style you like and paste me the line it gives you (for
   example `style: clay`). Or tell me what the project is and I will suggest one." Seventeen choices do
   not fit a multiple-choice question, so ask in text.
   - They name a style: put its key in `readme-scenes.json` as `"style"`.
   - "Suggest": pick ONE, with one line of why. Developer tools fit `terminal`, `ascii`, `blueprint`,
     `holo`. A friendly product fits `clay`, `cutpaper`, `brutalist`. A serious or finance product
     fits `typographic`, `artdeco`, `glass`. Let them overrule.
   - "Keep my colours" or "same as before": leave `"style"` out. That is the original look, recoloured
     only by `theme`.
   - They do not care: use `brutalist` with their `theme`, and say so in one line.
   The style key is in `readme-scenes.json`, so a later `render` keeps it.
4. **Fill the scenes.** Copy `KIT/readme-scenes.json` to the project root and replace every
   `data` block with this project's copy. Three templates are available:
   - `hero` (1600 x 800): headline, subline, a terminal that types a prompt, a result card.
   - `before-after` (1200 x 680): up to six pain cards, a wipe, then a terminal and up to five outcomes.
   - `how-it-works` (1200 x 660): three or four steps left to right, then a loop line.
   Set the style in `style` (see step 3). The shipped `readme-scenes.json` carries a green `theme`:
   delete that block when a style is chosen, because `theme` wins over the style's palette. Keep
   `theme` only when the project has brand colours that must override the style. Write the `alt` for every scene: what the GIF shows,
   in the order it happens, for someone who cannot see it.
5. **Render.** `python KIT/scripts/render.py --check`, then `python KIT/scripts/render.py`.
   Open the GIFs or the still PNGs and look at them. Fix overflowing text by shortening the copy,
   never by shrinking the template.
6. **Assemble the README** from `readme-snippets.md`, which holds the image line and alt text for
   each GIF. Keep install and usage sections that already work; move them below the story.
7. **Show the user** the README and the GIFs. Commit and push only after they approve.

## Tools

- `python KIT/scripts/render.py [--config PATH] [--only NAME] [--check] [--list-styles]`: render every scene,
  write still PNGs where asked, warn over 4 MB, and write `readme-snippets.md`.
- `python KIT/scripts/record_html.py page.html out.gif --w W --h H --dur S`: record any animated
  HTML page you wrote yourself, with the same deterministic engine. `--still S` writes one PNG.
- `python KIT/tests/test_render.py`: the kit's own check.

## Rules

- **Every claim comes from the repo.** If the copy says it does something, point to the file,
  command or release that does it. A claim with no source is cut or flagged to the user.
- **Copy lives in `readme-scenes.json`, never in the templates.** Templates stay generic so the
  next render and the next project reuse them.
- **No em-dash, no hype words, no "unlock", "seamless", "supercharge", "revolutionize".**
  See the writing guide for the full list.
- **Every GIF has alt text** that describes what happens, not "demo" or "screenshot".
- **Illustrations say so.** A scene that shows a typical or sample situation carries a caption
  like "Illustration of a typical project README." Never present a drawing as a real screen.
- **The user chooses the style.** Never pick one silently unless they say to choose for them.
  `KIT/assets/style-gallery.html` is a shared copy (same page, same keys as `explainer-video` and
  `mockup`): do not edit it here.
- **Nothing is pushed without approval.** A README is public the moment it reaches the default branch.
