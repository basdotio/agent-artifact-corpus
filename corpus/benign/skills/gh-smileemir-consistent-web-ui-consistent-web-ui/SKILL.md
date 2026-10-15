---
name: consistent-web-ui
description: Make website and web-app frontends look like one consistent, professional product - a single theme source with design tokens, shared spacing and type scales, reusable components and assets, light/dark themes, responsive and accessible (WCAG 2.2 AA) layouts, clear UI text and help, and purposeful motion. Use whenever the user wants to design, build, redesign, restyle, clean up, audit or review a UI, landing page, storefront, product, cart or checkout page, account area or admin dashboard, asks for info tooltips, dialogs, dropdowns, notifications, empty or error states or animations, or says pages look inconsistent, cheap, generic or AI-made - even without saying "design system". Works on new and existing projects (frontend only, audit report first, owner-approved page-by-page changes) and on any stack, including plain CSS, Tailwind, shadcn/ui, Bootstrap, MUI, Vue, Svelte, Shopify and WordPress themes. Includes detailed ecommerce page, component, asset and motion guidance.
license: MIT
metadata:
  version: "0.6.0"
---

# Consistent Web UI

Make every page feel like part of one product: the same brand language, spacing, components, assets, states and motion, built on real data and restrained on purpose. Pages that each look designed by a different person read as unprofessional and never build a brand. The goal is a site that reads as one careful team's work, not a trendy preset.

## Ground rules

- The user's instructions and the project's own rules come first when they conflict with this skill.
- Scope: websites and web apps, including responsive phone layouts. Native mobile apps are out of scope. Work with the project's own stack ([framework-mapping.md](references/framework-mapping.md)).
- **Frontend only.** Backend, database, API, payment, authorization and business-rule changes need the owner's separate, explicit approval. Describe the need and the expected UI behaviour instead of implementing it.
- **Never touch global AI instructions.** Do not create or edit user-level or global instruction or memory files for any AI assistant: for example `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, global editor rules, or an assistant's saved memory or custom instructions. Decisions live in project files: the design contract and, at most, a short pointer to it in the project's own instruction file (`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md` and the like). Edit that file only if the project already has one or the owner agrees, and mention the change in the reply.
- Preserve what every existing control does: routes, handlers, calls, validation, tracking. A redesign never changes the meaning of an action.
- Real data only. Prices, stock, delivery terms, ratings, reviews, metrics and urgency come from actual product data. Missing data is reported as a dependency, never invented or simulated.
- Keep existing icon, image and font sets unless the owner approves a replacement; you may propose a better set. Support the themes the project has or asks for; do not add a theme on your own.
- **Spend tokens where they change the result.** Run the scripts instead of opening every file, read only the reference files the task needs, reuse the saved design contract and the last audit, and never repeat sector research at run time. If the project already has a code graph or index tool, reuse it; do not install one for this skill.

## Choose the lane

Match effort to the request. An explicit request from the owner in this conversation authorizes exactly the scope it names. **Shared parts** (layout, header, footer, a global CSS rule, a component other pages use) reach beyond a one-page request: name the other pages the change would affect and ask first, or keep the change on the named page and list the rest as a follow-up.

| Request | Lane | Do this |
| --- | --- | --- |
| A named, small change ("fix the spacing of the cart button") | **Scoped fix** | Read the design contract and theme source if they exist, reuse existing tokens and components, change only the named scope, then verify it (below). List other inconsistencies you noticed as audit suggestions without fixing them. No full audit. |
| Improve, restyle, clean up or audit an existing product | **Audit first** | Inventory → one Markdown report → owner chooses → one approved page at a time. |
| Build a new site, section or feature | **New build** | Design contract → one theme source → pilot page with every state → remaining pages in task order. |
| Review or design only | **Blueprint** | Deliver the report or spec; change no code. |

### Audit first (existing products)

1. Run `python3 scripts/frontend_index.py --root <frontend dir>` (`--json` for machine use). It reports route candidates, shells and error screens, theme sources, token gaps, raw colours and near-duplicates, value spread for spacing, type, radius, z-index and durations, looping animations, reduced-motion guards, locales and the detected stack. Confirm its routes against the router and navigation.
2. "All routes" means every route template, not every product URL. Open at least one real instance of each template, plus every supported locale and theme. Anything you could not reach is **unverified**, never passed.
3. Check contrast for every theme: `python3 scripts/contrast_check.py --css <theme source> --pairs auto` (or a pairs file from `assets/templates/contrast-pairs.json`); `--only-failures` keeps the output short.
4. Write **one** report from `assets/templates/audit-report.md`. Label each finding `observed`, `inferred` or `unverified`, keep frontend-only fixes apart from anything needing backend or data approval, include a layer map (the intended stacking order and every element that now covers another, for example a cookie banner hiding the purchase bar), propose theme centralisation if values are hardcoded, and suggest a pilot page. Then stop and present it: nothing changes until the owner picks pages and scope.
5. Implement one approved page at a time, verify its original actions, then move on.

### New build

1. Fill `assets/templates/design-contract.md` with the owner: audience, brand traits and anti-traits, product branches, real data sources, locales, currencies, themes, density. Save it in the project (for example `docs/design-contract.md`) so later sessions build on the same decisions. It is a project file: it never goes into an assistant's global instructions or memory, and it does not train a model.
2. Create one theme source from `assets/templates/theme-tokens.css` or inside the framework's own theme. Replace every `TODO(brand)` value, then run the contrast check for every theme. Components read roles, never literals.
3. Build the pilot page from `assets/templates/page-spec.md` with all its states (loading, empty, error, partial, no permission, success, longest text), verify it, then reuse its components on the next pages. Keep the first version simple: a few complete sections, each with one job, rather than many thin ones.

## Verify on a real render

Reading code does not prove a layout. When the project can run:

1. Start its existing dev or preview command and open pages with whatever browser tooling the environment already has (a Playwright install, a browser tool, an IDE preview). Do not add tooling to the project just for this.
2. Capture each changed route at 360, 390, 768, 1024, 1280 and 1440 px, a short landscape phone and 200% zoom, in every supported theme and the longest locale. Sweep the widths in between to find where the layout actually breaks. Keep before/after pairs.
3. Walk the keyboard path (visible focus, logical order, no traps), turn on reduced motion, and re-run the page's existing actions.
4. Open every overlay the page has: select lists, menus, dialogs, drawers, popovers, toasts. Each time, run `scripts/ui_check.js` in the page (Playwright: `page.addScriptTag({ path })`, then `page.evaluate(() => uiCheck())`). It measures:
   - controls in a row with different heights;
   - a page that scrolls behind a dialog;
   - clicks that pass through an overlay;
   - see-through surfaces;
   - dialogs that scroll or hide their actions;
   - oversized close buttons.
5. Fix what fails and capture again. Report "verified" only for what you actually rendered; otherwise write "unverified: visual" and give the owner a short checklist. Look at screenshots only for the pages you changed, because images are expensive to read.

## Consistency rules (every lane)

- **Same job, same component.** Buttons, inputs, dropdowns, checkboxes, toggles, cards, rows, dialogs, notices and icons share one grammar across pages. Add a variant only where a task needs it, and keep differences on-brand, never random. Controls that share a row (search, select, buttons, view toggles) have one height, one radius and one text size. Buttons side by side differ only by variant, and a hover never adds an underline or border that the others lack (`assets/templates/controls.html`).
- **Roles, not literals.** Spacing, type, colour, radius, shadow, layers (z-index) and durations come from theme roles. A missing value becomes a new role in the theme source.
- **Cards.** Consistent inner spacing and gaps between cards; identity/media → title → decision facts → action; align rows without cutting useful text to force equal heights; show only fields with real data.
- **List toolbar.** Lists and tables that need it get one toolbar in the same place: filter, sort, grid/list or compact/detailed rows, and visible-column choice. Identity, price and status can never be hidden. Short, fixed lists get no toolbar.
- **Optional information cards.** A visible X closes the card. A compact options menu offers:
  - **Minimize:** the card becomes a small labelled `!` box in the same place, and the box reopens it.
  - **Remind me in a week.**
  - **Never show again.**

  New sites remember these choices in the same browser, with an honest seven-day expiry. Critical price, legal, payment or safety information is never dismissible. Existing products need owner approval before persistence is added.
- **Help only where it is needed.** Help (an info (i) or a visible hint) goes only on an item whose purpose or effect a first-time user could not work out, where a wrong guess costs something. Fix the label first. A visible hint is for limits needed while typing and for serious, hard-to-undo consequences; nice-to-know detail goes behind an (i). The help says what the item does or changes, in one or two sentences, never a dictionary definition, and never on every card or field. Read [help-and-ui-text.md](references/help-and-ui-text.md) before adding help or writing labels, errors, empty states or confirmations.
- **Only the top layer moves and responds.**
  - While a dialog, drawer or full-screen menu is open, the page behind does not scroll and does not react to clicks, hover or Tab. The backdrop takes the outside clicks.
  - Everything that sits over content (menus, select lists, popovers, sticky bars, toasts) is opaque, so the text beneath never shows through, and a click on it never reaches what is below.
- **Dropdowns, dialogs and toasts look like the rest of the product.**
  - **Dropdowns:** an open select or menu list uses the theme's surface, border, radius and type, never a bare system list beside styled fields on desktop.
  - **Dialogs:** they fit their content. Media is capped, the actions stay visible, only the body scrolls, and the close button is a quiet 36–40 px icon.
  - **Toasts:** they use the brand's look, sit above dialogs, never cover the main action, and errors stay until closed.
  - **Where to start:** read [overlays-and-controls.md](references/overlays-and-controls.md) and use `assets/templates/dialog.html`, `toast.html` and `controls.html`.
- **No full reloads for same-page actions.** Save, filter, preference and add-to-cart update the page without a full reload wherever the existing data flow supports it. Normal navigation may change routes.
- **Accessibility from the start.** Labels, visible focus, keyboard access, contrast, reflow at 320 px, 200% zoom, alternative text, touch targets and reduced motion are part of building each component (WCAG 2.2 AA), not a final pass. Long translations must fit without clipping. A hover effect on a link or button also runs on `:focus-visible`; non-interactive content never gets a tab stop just to show an effect, and anything hover reveals must be reachable without hover.
- **Motion: enough to explain, never to perform.** Every state change the user causes gets brief feedback (hover, press, open, close, add, save). Nothing moves on its own except real loading or progress and at most one attention moment per view. Read [motion-core.md](references/motion-core.md) before adding or changing any animation.

## Tools and templates

| File | Use it to |
| --- | --- |
| `scripts/frontend_index.py` | Get a read-only inventory of routes, theme sources, token gaps and value spread without reading every file |
| `scripts/contrast_check.py` | Check colour pairs in every theme (hex, rgb, hsl, oklch, named colours, `var()`, `light-dark()`, `color-mix()`) |
| `scripts/ui_check.js` | Measure rows of controls and open overlays on the rendered page (run in the browser) |
| `assets/templates/audit-report.md` | Write the single audit report |
| `assets/templates/design-contract.md` | Record project decisions (IDs DC-xx) |
| `assets/templates/theme-tokens.css` | Start one theme source: roles, light/dark, layers, motion, reduced motion |
| `assets/templates/contrast-pairs.json` | Define the pairs to check |
| `assets/templates/page-spec.md` | Specify each page's order, states and checks |
| `assets/templates/motion-record.md` | Specify each chosen motion |
| `assets/templates/info-toggletip.html` | Add an accessible info (i) when the project has no popover component |
| `assets/templates/controls.html` | Give fields, selects, toggles and buttons one height, radius and state set |
| `assets/templates/dialog.html` | Build dialogs: size to content, scroll lock, backdrop, focus |
| `assets/templates/toast.html` | Build brand-consistent toast notifications |
| `assets/templates/asset-register.csv` | Keep the asset register |

## References (read only what the task needs)

- [design-contract.md](references/design-contract.md): token roles, asset records, breakpoints, theme switching.
- [framework-mapping.md](references/framework-mapping.md): where the theme source lives in each stack.
- [audit-and-qa.md](references/audit-and-qa.md): audit protocol, approvals, acceptance matrix, status language.
- [help-and-ui-text.md](references/help-and-ui-text.md): when an info (i) is allowed and what it says, button labels, errors, empty states, confirmations, forms, number and date formats.
- [overlays-and-controls.md](references/overlays-and-controls.md): layer behaviour, controls in a row, buttons, selects and menus, dialogs, toasts, and the page check.
- [motion-core.md](references/motion-core.md): the motion floor and ceiling and the rules for every animation. After it, open only the sector motion file you need.
- **Ecommerce** (open only the file for the current task):
  - [ecommerce-pages.md](references/ecommerce-pages.md): customer routes C01–C20 and admin routes A01–A12
  - [ecommerce-components.md](references/ecommerce-components.md): controls, 22 card roles, admin layouts
  - [ecommerce-directions.md](references/ecommerce-directions.md): pick one of five original directions for a new brand, then read only that direction's file (01–05); never apply a direction to an existing brand without approval
  - [ecommerce-assets.md](references/ecommerce-assets.md): asset families and handoff
  - [ecommerce-responsive.md](references/ecommerce-responsive.md): phone and tablet reading order and interaction tests
  - [ecommerce-transaction-traces.md](references/ecommerce-transaction-traces.md): quote integrity and purchase/operator traces T01–T12
  - motion records: [browse M01–M19](references/ecommerce-motion-browse.md), [buy M20–M36](references/ecommerce-motion-buy.md), [after purchase and promises M37–M49](references/ecommerce-motion-after.md)
- [sector-program.md](references/sector-program.md): only when authoring a new sector.

## Deliverables

| Lane | What you hand over |
| --- | --- |
| Audit | The single report, with nothing else changed. |
| Scoped fix or page | The changed files, what was preserved and re-tested, the viewports and themes rendered, the contrast result and any open dependencies. |
| New build | The contract, the theme source, the component and asset map, the pages with their states, the verification results and open questions. |

Keep chat replies short and put the detail in the files.
