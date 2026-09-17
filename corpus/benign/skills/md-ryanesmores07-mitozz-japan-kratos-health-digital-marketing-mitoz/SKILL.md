---
name: mitozz-icon-sourcing
description: Source clean, semantically appropriate icons for Mitozz Japan creatives using Better Icons. Use when a feed, story, reel frame, or supporting design system element needs icons instead of improvised shapes.
---

# Mitozz Icon Sourcing

Use this skill when a Mitozz creative needs icons.

The goal is to replace random decorative shapes with intentional, repeatable icon cues that support meaning without making the brand feel generic, app-like, or noisy.

This should now be considered by default for every framework, selector, FAQ, answer-card, or CTA-support asset, even if the final decision is `none`.

## Primary Tool

Use the installed Better Icons skill at:

- `C:\Users\esmoresernieryanocam\.codex\skills\better-icons\SKILL.md`

Treat that skill as the icon search and retrieval engine.
This repo-local skill defines how Mitozz should use it.

Workspace execution path:

- prefer `tools/shared/invoke-better-icons.ps1` over relying on a machine-global `better-icons` PATH install
- example:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File "tools/shared/invoke-better-icons.ps1" search sleep --limit 5`

## When To Use Icons

Use icons when they improve clarity for:

- routines
- comparisons
- frameworks
- lists
- answer cards
- selector modules
- CTA reinforcement
- decision-tree moments

Good examples:

- sleep
- food
- movement
- check / yes
- save / bookmark
- question / FAQ
- route / arrow
- balance / rhythm

## When Not To Use Icons

Do not use icons:

- as filler when whitespace is enough
- when a photo should carry the meaning
- when the icon is too literal and makes the asset feel like a health app UI
- when mixed icon families would weaken the premium tone

If the post needs atmosphere, trust, or lived-in realism, prefer imagery first.
Icons should support the message, not replace the visual engine.

## Mitozz Rules

For one asset or one batch:

- use one icon family only
- keep stroke weight or fill style consistent
- keep icon color restrained
- avoid oversized icon treatment unless the icon is the main concept
- do not mix outline and solid styles casually
- do not stack many unrelated icons on one frame

Default behavior:

- `Set 1 + Set 2`: use icons sparingly for semantic support
- `Set 4`: icons should be minimal or absent unless they clarify a CTA or routine cue
- `Set 5`: use icons only when they feel editorial and trust-supportive

## Recommended Usage Patterns

Best uses:

- one icon beside a short label
- one icon inside a selector tile
- one icon as a section marker in an answer card
- one repeated icon family across 2-4 slides

Avoid:

- emoji-like visual behavior
- colorful multi-icon clusters
- random abstract-symbol swaps from slide to slide
- generic app-dashboard icon overload

## Search Guidance

When using Better Icons:

- search by semantic need first, not by trend
- prefer simple, neutral, editorial-feeling collections
- short-list 3-5 options
- choose the one that matches the batch style best

For Mitozz, favor:

- clean outline icons
- calm geometric icons
- editorial-symbol simplicity

Be careful with:

- cartoonish sets
- highly branded social-style icons
- very rounded playful icons
- overly technical developer-looking icon sets

## Output Guidance

When you source icons for a creative, record:

- the icon family or collection
- the selected icon ids
- where each icon is used in the asset
- whether the icon is structural or purely supportive

If the icon becomes part of a reusable template, mention it in the creative package or production notes so future batches stay consistent.
