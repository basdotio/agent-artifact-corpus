# Frontend audit: {product} - {YYYY-MM-DD}

> **Status: audit only. Nothing has been changed.** Pick what to approve in section 5.
> Evidence labels: **observed** = seen on the running page (route + viewport + action), **inferred** = read in code but not seen, **unverified** = could not be reached in this audit.

## 1. Scope and coverage

- Environment: {URL or local command} · commit {sha} · browsers/devices {list} · date {date}
- Route templates covered: {n}/{n} (Appendix A). Sampled instances per template: {k}. Locales: {list}. Themes: {list}.
- Not verified and why: {login-only screens, payment step, admin, region-locked pages}
- Tools: inventory `scripts/frontend_index.py` ({date}), contrast `scripts/contrast_check.py` ({pass}/{fail}), screenshots in `{folder}`

## 2. Design contract as found

| Area | What exists | Source files | Consistent? |
| --- | --- | --- | --- |
| Theme source | {single file / scattered / none} | | |
| Colours | {n} distinct raw colours, {m} tokens, near-duplicates {list} | | |
| Type scale | {sizes in use} | | |
| Spacing | {n} distinct values, {p}% via tokens | | |
| Radius, shadows, layers | {z-index values in use} | | |
| Icons | {set, stroke/fill, mixed sets?} | | |
| Imagery | {ratios, treatment, missing-image fallback} | | |
| Motion | {durations in use, looping animations, reduced-motion guards; ten-second idle test; missing feedback on clicks} | | |
| Controls and overlays | {heights and radii of controls that share a row; do dropdown lists, dialogs and toasts match the theme; does the page scroll or react under an open dialog; `ui_check.js` results} | | |
| Help and UI text | {info (i): how many and where; help that defines the word or guesses; hover-only or `title` help; button, error and empty-state patterns} | | |
| Themes and locales | {light/dark support, which parts break when switching} | | |

Rights questions: {fonts, icons, images or logos whose licence is unknown}

### Layer map

| Element | Pages | z-index and stacking context | Must sit above | Currently covered by | Evidence |
| --- | --- | --- | --- | --- | --- |
| {sticky purchase bar} | {product} | {100, fixed} | {page content} | {cookie banner at 900} | {observed: product page at 390 px with the banner open} |

Stacking contexts matter as much as numbers. A parent with `transform`, `filter`, `opacity` below 1, `will-change`, `isolation: isolate` or `position: fixed`/`sticky` starts a new stacking context: nothing inside it can rise above a layer outside it, whatever its z-index.

## 3. Findings

Priority: **P0** blocks a task or misleads (wrong price, hidden error, unusable checkout, keyboard trap) · **P1** visible inconsistency across routes · **P2** polish.

| ID | Routes / components | Evidence | User impact | Proposed frontend change | Needs backend, data or permission? | Risk | Priority | Owner decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | | | | | | | | approve / defer / reject |

<!-- Example rows show the level of detail expected. They are fictional: delete them.
| F01 | Home, product, cart - primary button | observed: /product/[id] and /cart at 390 px, screenshots 03-04 | Same action looks like three different actions; users hesitate | One button hierarchy on `--color-brand`, `--space-control`, `--radius-control` | None: handlers unchanged | Low | P1 | approve / defer / reject |
| F02 | Shop list, admin orders - toolbar | observed: filter/sort/columns sit in three places | Controls are hard to find; view choice is lost | One shared toolbar; keep list-specific filters; remember view where supported | Existing data contract only | Low | P1 | approve / defer / reject |
| F03 | Checkout - payment result | unverified: payment step needs a real card | Pending may read as paid | Distinct pending / failed / confirmed states | Uses existing payment status; no API change | Medium | P0 | investigate first |
-->

## 4. Theme centralisation (only when values are hardcoded)

- Proposed single source: {file} ({framework mapping})
- Roles to add or rename: {list}
- Files affected: {count} - impact map: {components and routes}
- After the change, a theme switch reaches: header, footer, overlays, toasts, forms, charts, admin, error pages

## 5. Delivery order and approval

1. Pilot page: {route} - why first: {it sets the shared pieces for …}
2. {next route} …

Frontend-only: {F…}. Needs separate backend/API/data/payment approval: {F…} (expected UI behaviour only; nothing implemented).

Reply with, for example: "Approve F01, F02 on /product and /cart. Defer F05."

## 6. Verification baseline

- Working controls recorded before any change: {list with how they were checked}
- Before screenshots: {viewports} + 200% zoom + dark theme → `{folder}`
- Contrast: {n} pass / {n} fail - {failures}
- Accessibility quick pass: keyboard path, visible focus, names/labels, reduced motion, reflow at 320 px
- Overlay check: `scripts/ui_check.js` run with each dialog, menu, select list and toast open: {issues}
- Performance (if field or lab data exists): LCP / INP / CLS
- Cannot test yet: {list}

## Appendix A - Route inventory

| Route template | Instances checked | File | States seen | Locales / themes | Evidence |
| --- | --- | --- | --- | --- | --- |
