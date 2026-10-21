---
name: lanyard-badge
description: >-
  Put a person's photo on an animated "team badge" in a website hero — a clear plastic ID-style holder hanging from a lanyard, with sway, Y-axis spin, flip to a details back (click and timed), and an optional scroll "drop" into a floating corner dock. Ships a framework-free vanilla JS/CSS badge that works on any site (plain HTML, Astro, Vue, React, Next.js) plus a React + Tailwind team-carousel component. Optionally generates a matching-uniform portrait with the Higgsfield API. Use this whenever someone wants their own photo, a headshot or a team photo on a badge in a personal portfolio or company site (no photo yet is fine: it starts with a placeholder), or wants it on a badge, ID-style card, profile card, owner/team card, rotating hero card or lanyard, or says things like "add a lanyard badge to my portfolio", "put me on a badge in my hero", "add Maria to the badge", "make a badge for our new manager", "do the badge thing for this photo", "replace the hero image with my badge", or "put our owners in the hero like an ID card", even if they don't say "lanyard".
---

# Lanyard badge

Turns one photo per person into a polished, interactive hero badge:

1. **Portrait (optional).** Use the photo as-is if it is already a clean headshot, or have Higgsfield edit it into a matching studio portrait in a company-uniform polo (`scripts/generate-portrait.mjs`).
2. **Badge.** A clear holder on a lanyard that sways, flips to a details back when clicked and on a timer, and spins on its strap. Pick the build that matches the project (step 2).

The user's ideal is "I give you a picture, you do the rest." Infer everything you can from the project and ask only for what you can't safely guess.

Paths below use `$SKILL` for this skill's folder: `~/.claude/skills/lanyard-badge` when installed for the user, or `.claude/skills/lanyard-badge` inside a project.

## What it is not

It's a decorative profile card, not a credential. Never add barcodes, QR codes, ID numbers, expiry dates, security marks or government styling, even if an inspiration image has them. Only use photos of people who agreed to be on the site, which usually means the user or their team.

## Workflow

### 1. Gather inputs

**From the user:** a photo per person. **No photo yet? Don't stop to ask.** Copy `$SKILL/assets/vanilla/demo/avatar.svg` to the site's static folder, build with it, and tell the user which file to replace with their headshot.

**Name and role.** Use them if given or already on the site (hero copy, about section, page title). Otherwise ask once, in one short question covering everyone. Don't guess surnames from file names: a misspelled name on a hero is the most visible mistake possible.

**From the project (infer, don't ask):**
- **Brand colors and fonts:** Tailwind theme, CSS variables, CLAUDE.md, brand files. Accent = primary brand color; strap = the color the user asks for (default red `#d62f2f`); fonts = the site's display / body / mono families.
- **Facts for the back:** use only facts stated in the project (hero copy, meta description, about text, content files). Never invent years, certifications, numbers or links. Follow any "do not publish" rules in CLAUDE.md.
- **Primary CTA:** reuse the site's existing main CTA label and anchor instead of inventing one.
- **Logo** (only for the Higgsfield polo or the React company card): look in `brand_assets/`, `public/brand/`, `public/`, `src/assets/`.

**Existing badge?** Grep for `LanyardBadge`, `lanyard-badge`, `data-badge-slot` or `initBadge`. If it exists, the job is usually to add or swap a person in the config. Don't reinstall.

**Whatever the hero shows now** (illustration, mascot, 3D scene) is what the badge usually replaces. Before deleting it, grep the whole source tree for every import of its module and every function it exports, and remove those call sites too. One dangling ES-module import stops *all* of the site's JavaScript, not just the badge.

### 2. Choose the build

| Project | Build | Files |
| --- | --- | --- |
| Any site: static HTML, Vite, Astro, Vue, Svelte, WordPress, **and React / Next.js** | Vanilla (default) | `assets/vanilla/badge.js`, `dock.js`, `badge.css` |
| React / Next.js site that wants a **carousel** of several team members plus a company card | React component | `assets/LanyardBadge.tsx` |

Use the vanilla build unless the user asks for a team carousel. It is the badge in the live demo, and the only one with the scroll dock. In React and Next.js, mount it from a `useEffect` (step 4b).

### 3. Portrait

**Use the photo directly** when it is already a head-and-shoulders shot with a plain background. Convert it to WebP at about 720×720 (sharp: `sharp(src).resize(720, 720).webp({ quality: 88 })`) and put it where the site serves static files. The vanilla front shows it in a circle with a ring, so square and circular-crop photos both work. Never ship the multi-MB original.

**Use Higgsfield** when the team should look uniform or the photos are casual. It needs `HF_CREDENTIALS=key-id:key-secret` in the environment, `.env.local` or `.env` (keep it out of git). Dry-run first; it validates files and credentials without spending credits:

```bash
node $SKILL/scripts/generate-portrait.mjs --photo <photo> --logo <logo> --slug <first-name> --dry-run
node $SKILL/scripts/generate-portrait.mjs --photo <photo> --logo <logo> --slug <first-name> \
  --out brand_assets/badge/generated --webp public/badge \
  [--shirt "black short-sleeve polo shirt"] [--notes "Keep the curly hair and glasses."] [--no-logo]
```

Look at every result before using it: same face, clean (or no) chest logo, no stray text, both shoulders in frame. If the logo is garbled, rerun once, then use `--no-logo`. Show the user the portrait before wiring it in, since it's their face on their site.

### 4a. Install the vanilla build

1. Copy `assets/vanilla/badge.js`, `dock.js` and `badge.css` into the project (e.g. `src/js/badge/`, and the CSS into the main stylesheet or its own file). With a Tailwind CLI setup, paste `badge.css` into the input CSS; it is plain CSS and needs no Tailwind.
2. Put the slot in the hero's visual column, replacing what was there:
   ```html
   <div class="badge-slot" data-badge-slot>
     <noscript><!-- static fallback: photo + name --></noscript>
   </div>
   ```
3. Call it from the site's entry script:
   ```js
   import { initBadge } from "./badge/badge.js";
   initBadge({
     name: "JOHN DOE",
     role: "Software engineer",
     chip: "Go, Python, Postgres",            // under ~22 characters
     photo: "/badge/john.webp",
     backHeading: "What I do",
     items: [                                 // 3 fit best
       { icon: "code", title: "APIs", detail: "Fast, documented, versioned" },
       { icon: "cloud", title: "Infrastructure", detail: "Kubernetes, CI, observability" },
       { icon: "shield", title: "Reliability", detail: "On-call that lets people sleep" },
     ],
     links: [{ label: "GitHub", href: "https://github.com/..." }, { label: "LinkedIn", href: "https://..." }],
     cta: { label: "View projects", href: "#projects" },
     autoFlipMs: 5000,                        // 0 = never auto-flip
     dock: { nav: "header" },                 // false = no scroll dock
   });
   ```
   Icons: `search`, `shield`, `spark`, `code`, `cloud`, `user`, or a raw `<svg>` string. `assets/vanilla/demo/index.html` is a complete working page.
4. **Theme** by setting CSS variables on `:root`, any parent of the slot, or `.badge-slot` itself (defaults live in `var()` fallbacks, so any of these wins): `--badge-accent`, `--badge-on-accent`, `--badge-strap`, `--badge-strap-dark`, `--badge-strap-light`, `--badge-surface-top`, `--badge-surface`, `--badge-ink`, `--badge-muted`, `--badge-faint`, `--badge-line`, `--badge-line-strong`, `--badge-shine` (the light that runs around the holder edge; white by default, so set it to the accent on a light page, or `transparent` to turn it off), `--badge-font-display`, `--badge-font-body`, `--badge-font-mono`, `--badge-z`. Defaults are a dark card with an orange accent and a red strap; for a light site flip the surfaces light and the ink dark (the demo's `?theme=light` shows a full set).
5. **Dock options** (`dock: {...}`): `nav` (selector of the fixed header the lanyard hangs beneath, default `[data-nav]`), `dockMinWidth` (1280), `twoColMinWidth` (1024), `collapsedScale` (0.6), `expandedScale` (0.85), `margin`, `belowNav`, `dockAt`, `undockAt`, `minHeroScale`, `dropVelocity`, `swingKick`. Keep `--badge-z` below the header's z-index so the strap emerges from under it.

What the visitor gets: the badge drops in with a full turn when the hero first scrolls into view, sways, flips every `autoFlipMs`, and has a light running around its edge, holds a side when clicked (click again, or the ↻ button, to return). Hover and keyboard focus pause the timer. Links on the back never flip it. Past the hero (from `dockMinWidth`) it lets go, springs into the top-right corner under the header with a bounce and swing, stays there while the page scrolls, swings a little with scroll speed, grows on hover so the back is readable, and flies home when the visitor scrolls back up. Below `dockMinWidth` it stays in the page. On short screens the in-page badge scales down to clear the fold. `prefers-reduced-motion` gets no sway, spin, springs, edge light or timer.

### 4b. Vanilla build inside React or Next.js

Copy the three files into e.g. `src/components/badge/`, import `badge.css` once (Next.js: in the root layout or `globals.css`), and add a client component. `initBadge` ignores a second call on the same slot, so StrictMode's double effect is safe.

```tsx
"use client"; // Next.js App Router only
import { useEffect } from "react";

export function HeroBadge() {
  useEffect(() => {
    import("./badge/badge.js").then(({ initBadge }) => initBadge({ name: "JOHN DOE", role: "Software engineer", photo: "/badge/john.webp" /* ...same config as 4a */ }));
  }, []);
  return <div className="badge-slot" data-badge-slot />;
}
```

In TypeScript projects without `allowJs`, add `declare module "*/badge.js";` to a `.d.ts` file. Put `<HeroBadge />` in the hero's visual column; give the fixed header `data-nav` or pass `dock: { nav: "header" }`.

### 4c. Install the React build (team carousel)

1. Copy `assets/LanyardBadge.tsx` into the components folder. It uses a boolean `inert`, so React 19+; for React 18 change `inert={x}` to `inert={x ? "" : undefined}`.
2. Define the `BadgeConfig` at module level next to the hero. `references/react-example.md` is a complete example.
3. Put `<LanyardBadge config={badge} />` in the hero's visual column with an `auto`-sized grid column (`lg:grid-cols-[minmax(0,1fr)_auto]`) so the headline keeps its width. Controls use `theme.onDark`; set it dark if the hero is light. `theme.shine` colours the edge light (`"transparent"` turns it off).
4. Adding a person: add `{ name, role, photo }` to `config.people`. Default timeline: each person 10 s (back at 5 s, front at 8 s), company card 50 s flipping every 10 s; change it via `config.timeline`.

### 5. Verify

1. Run the project's build (and lint/type-check if it has them). For plain ES-module files in a package without `"type": "module"`, syntax-check with `node --input-type=module --check < file.js`; plain `node --check` reports false errors.
2. **Optional, recommended:** with the dev server running, verify in a real headless browser. The scripts need `puppeteer` (the badge itself doesn't). They find it in the project or next to the skill (`npm i puppeteer --prefix ~/.claude/skills/lanyard-badge`). Never add it to the user's `package.json`. If it's missing and the user doesn't want it, skip the scripts and check by hand: open the page, click the badge, scroll past the hero, and look at it at 390 px wide.
   - Vanilla: `node $SKILL/scripts/verify-vanilla.mjs --url http://localhost:5173 --hero "#hero"` runs 13 checks (render, photo, click-hold, flip back, auto-flip, dock, page bottom, return, mobile dock and overflow, reduced motion, page errors), exits 1 on failure, and saves screenshots.
   - React: `node $SKILL/scripts/verify-badge.mjs --url http://localhost:3000 --seconds 75` screenshots every card and prints the timeline.
3. Look at the screenshots yourself: name on one line, role at most 2 lines, chip on one line, nothing clipped at the card bottom, whole badge visible at 1280×720.
4. Check about 390 px wide: no horizontal scroll and the badge sits under the hero text.

Report what was built, where the files are, and the verification results. If the site deploys previews (Vercel, Netlify), check the preview too: asset paths are case-sensitive there.

## Things that went wrong before (so they don't again)

- **A deleted hero mascot was still imported by another module** (a project-card hover hook). The 404 on that import killed every script on the page. Grep for imports before deleting.
- **The page's global `button:active { transform: scale(.97) }`** shrank the full-card flip button. `badge.css` overrides it on `.badge-hit`; keep that if you restyle.
- **Automated clicks time out** in Playwright ("element is not stable") because the badge sways forever. Click from `page.evaluate(() => el.click())` or pass `force: true`.
- **The docked badge covered content at 1024–1279 px**, so the dock starts at 1280 px. Lower `dockMinWidth` only if the page has a wide right margin.
- **At 1280×720 the bottom of the badge was below the fold.** The vanilla build now scales the in-page badge to fit (`minHeroScale`).
- **The square photo crop hid the chest logo** in the React build: `photoFocusY: "22%"` shows hair to logo; adjust per person.
- **Card text clipped at the bottom:** keep chip text under about 20 characters ("MA and Southern NH", not "Serving Massachusetts and Southern New Hampshire").
- **A navy card back blended into a navy hero:** backs are light cards in the React build; in the vanilla build pick `--badge-surface*` values that contrast with the hero.
- **Video tools (e.g. HyperFrames) are the wrong fit.** They render MP4: soft text, dead links, no interaction. Keep it live HTML/CSS.
