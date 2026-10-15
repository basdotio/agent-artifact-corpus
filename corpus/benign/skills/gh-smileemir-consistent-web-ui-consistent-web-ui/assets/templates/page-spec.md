# Page spec - {route}

**Purpose:** {one sentence: who comes here to do what} · **Primary action:** {one} · **Contract version:** {n}

## Content order

| # | Section | Job (one) | Data source | Desktop placement | Phone order |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |

Hide a section when its data is missing or empty; never fill it with invented content.

## Components used

{component - variant - contract ID}, …

## States

| State | What the user sees | Next action |
| --- | --- | --- |
| Loading | reserved geometry, no layout jump | - |
| Empty / no results | reason + recovery | |
| Error / offline | what failed, what is safe to retry | |
| Partial or stale data | freshness label | |
| No permission / signed out | why + sign-in path | |
| Success / confirmed | only after the real confirmation | |
| Long content / longest locale | wraps, nothing clipped | |

## Behaviour to preserve

{every existing control on this page and what it does now; handlers, routes and API calls stay the same}

## Help and UI text

| Item | Needs an (i)? | Why: cannot be inferred + cost of a wrong guess | Help text (at most two sentences) | Source of truth |
| --- | --- | --- | --- | --- |
| | | | | |

Primary button label: {verb + object} · Empty state: {what appears here + first step} · Main error: {what happened + how to fix}

## Motion

{feedback on each user action (the floor); motion IDs used and why, or "none"; the single attention moment, if any}

## Verification

- Viewports: 360, 390, 768, 1024, 1280, 1440 px; short landscape phone; 200% zoom
- Keyboard path, visible focus, labels, screen-reader names for icon buttons
- Themes: {list} · Locales: {longest} · Reduced motion
- Contrast check: pass
- Existing actions re-tested: {list}
- Evidence: `{screenshot folder}`
