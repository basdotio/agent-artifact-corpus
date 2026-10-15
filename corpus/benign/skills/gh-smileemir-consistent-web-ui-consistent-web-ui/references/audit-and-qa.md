# Frontend audit, permission and acceptance protocol

## 1. Audit a live existing project before changing pages

Start with `scripts/frontend_index.py`, then inventory **all** frontend route templates and accessible states with the repository's route configuration, nav destinations, dynamic routes, error boundaries, shared shell and admin routes. "All routes" means every route *template* (one product page stands for all products), opened with at least one real instance, in every supported locale and theme; sample more instances where content varies (long titles, missing media, sold-out items). Trace a representative happy/failure path for each kind of transaction. Index existing CSS, component libraries, tokens, media, icon set, locale data and motion definitions. Map the layers: list everything that overlaps (header, menus, drawers, dialogs, toasts, tooltips, sticky bars, cookie banners, chat widgets) with its z-index, its stacking context and what it must sit above, then open them together on a real render (every overlay with every other one that can appear at the same time) and record which one covers which. Start with filenames and route maps, then read the smallest relevant frontend set and expand based on dependencies. Do not treat a quick homepage scan as a full audit; if a route cannot be reached, label it unverified. Reuse a graph/index tool only if the project already uses one and the tool stays within frontend scope.

Produce **one Markdown report** from `assets/templates/audit-report.md`, with these sections:

1. Scope, route inventory, date, environment and unverified areas.
2. Existing brand/design contract and actual asset/icon/theme inventories, with reuse and rights questions.
3. `Issue ID | routes/components | observed evidence | user impact | proposed design | data/permission dependency | risk | priority | owner decision` table. An evidence label must be `observed`, `inferred` or `unverified`.
4. Proposed global tokens/theme centralization and impact map (when existing hardcoded colors make themes inconsistent), without silently rewriting the app.
5. Page-by-page delivery order and exact approval choices; separate frontend-only changes from requests needing backend/API/database/payment authorization.
6. Verification baseline: current working controls, comparable before/after screenshots where possible, screen sizes, performance/accessibility issues, and what cannot yet be tested.

Present that report to the owner. Record approval by named page and scope; an earlier explicit instruction in the conversation counts as approval for its stated scope. Apply one approved page at a time, update the shared frontend contract only where approved, and verify its original actions before the next page. If approval is limited to an audit, stop at the audit. Do not change operational metrics, backend, database, API, permission rules, payment logic or business meaning. A required server change is described as a request with expected UI behavior but is not implemented unless separately approved.

A narrowly named fix (one component or page the owner points to) does not need this full audit: reuse the contract and tokens, change only that scope, verify it, and list anything else you noticed as audit suggestions. When the fix sits in a part other pages share (layout, header, footer, a global CSS rule, a shared component), name the pages it would also change and ask before touching them, or keep the change on the named page and list the rest as a follow-up.

## 2. Build a new frontend in task order

Write the product/brand and data contract → route map with conditional branches → central global theme CSS → canonical asset register and primitives → first complete customer task → remaining customer routes → required operator routes → appropriate motion → responsive and accessibility checks. New projects should use a single global theme file as the semantic theme source, with other styles consuming those variables. Never delay state or function until visual polish is finished. Page-level completion requires happy, pending, empty, error, unauthorized (when applicable) and restored states.

## 3. Acceptance matrix

| Check | Test method | Release-blocking example |
| --- | --- | --- |
| Brand continuity | Compare all route families, shared header/footer, spacing, typography, icon and status language | Checkout or admin looks like an unrelated brand |
| Correct product facts | Trace one physical, one digital and one configurable example **when offered** through list → detail → cart → checkout → outcome → aftercare | Wrong variant image, mismatched tax/total, fake stock |
| Responsive | Small and large phone, short landscape, tablet, narrow/wide desktop, 200% text and 400% browser zoom/reflow where feasible; long locale | Sticky footer covers final input, price clipped, keyboard inaccessible |
| Accessibility | Applicable WCAG 2.2 AA review plus keyboard, screen reader, focus, names, 320 CSS px reflow, contrast and reduced motion | Focus hidden behind sticky bar, dialog focus lost, status only in color |
| Content and media | Alt/decorative roles, source rights, missing media, video poster/captions, long translations | Different product used as missing-photo fallback |
| States and data | Offline, loading, stale, empty, partial, permission denied, repeat actions | Payment pending presented as success, no-data shown as zero |
| Layers | Open every overlay together with the others that can appear at the same time, then run `scripts/ui_check.js` | A cookie banner that hides the purchase bar on phones; the page scrolls or reacts under an open dialog |
| Help and UI text | Check each info (i) against [help-and-ui-text.md](help-and-ui-text.md); read buttons, errors and empty states in the longest locale | An (i) on every card, or help that defines the word instead of saying what the item does |
| Motion | Ten-second idle test and the feedback floor from [motion-core.md](motion-core.md); initial/final states, interruption, low-power phone, tall cards, reduced motion | Card content inaccessible until unreachable visibility threshold; a click with no visible response |
| Performance | Measure with real representative route and network/device; where field data exists, inspect p75 LCP, INP and CLS | An optional effect dominates input latency or shifts purchase controls |
| Preserved behavior | Compare existing control paths and backend contracts before/after approved frontend change | Clicking same CTA changes purchase semantics |

Reference web performance thresholds, where applicable and measurable, are LCP ≤2.5 s, INP ≤200 ms and CLS ≤0.1 at the 75th percentile. These are product checks, not proof that a particular prototype meets them. Never mark a closed checkout or authenticated admin route verified because a public marketing page loaded.

## 4. Motion and display edge cases

A compact card can use a high intersection ratio for a one-shot decorative story; a taller-than-viewport card needs a reachable meaningful subregion and should never hide its content. On desktop, one hover/focus narrative is enough; do not auto-loop it. A dialog's closing animation cannot change whether an irreversible operation occurred. For an expandable notice, preserve the short title and critical terms outside the collapsed body, make the disclosure keyboard operable, and move focus before hiding focused content. Do not persist “remind me in a week” if the app cannot store it; show owner dependency instead.

## 5. Owner-facing status language

`Implemented and verified` means an approved frontend change was made and tested in its real route. `Designed, unimplemented` means a blueprint exists. `Observed` means the exact screen/action was actually inspected. `Inferred` is an interpretation, and `Unverified` remains open. This prevents a good design document from being mistaken for proof of production behavior.

## 6. Measure whether a change helped (when the owner asks)

Agree one metric per change before shipping it, for example the share of product-page visitors who add to cart, or the share of carts that reach payment. Ship one change at a time and compare equal periods before and after; several simultaneous changes cannot be told apart. Small sites rarely have the traffic for a meaningful A/B test; watching about five target users attempt a real task, without helping them, finds most usability problems faster. Report measured numbers only; a design change is not proven by the fact that it shipped.
