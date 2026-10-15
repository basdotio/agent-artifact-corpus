---
description: Write or rewrite this project's README with animated GIFs (hero, before and after, how it works) rendered from HTML
argument-hint: "[optional: what to focus on, or 'render' to only re-render the GIFs]"
---

Follow the `animated-readme` skill (`.claude/skills/animated-readme/SKILL.md`).

- With no argument: run the full loop, from reading the project to showing the user the README.
- With `render`: skip the writing. Run `render.py --check` and `render.py` on the existing
  `readme-scenes.json`, then show the result.
- With anything else: treat it as the focus or the audience for the copy.

Never commit or push the README without the user's approval.

Focus: $ARGUMENTS
