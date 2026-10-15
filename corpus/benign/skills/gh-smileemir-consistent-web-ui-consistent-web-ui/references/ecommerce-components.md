# Ecommerce controls, assets and card roles

## Contents

- Shared controls and complete states
- 22 card roles and mapping
- Six admin layout patterns
- Shared asset coverage

The base component contract is `purpose → real data → hierarchy → affordance → states → phone and keyboard behavior → validation`. A component is reusable only when its meaning and state behavior stay consistent. Do not replace a real task with decoration merely to reuse a visual template.

## Shared controls and states

| Component family | Stable information order and variants | Required cases and interaction checks |
| --- | --- | --- |
| Header and menus | Logo/name; primary destinations; search; account and cart; optional region | Open/closed/active/loading; mobile drawer returns focus; no overlay traps page scroll/focus |
| Breadcrumbs/tabs/anchors | Current location and previous level, then destination choices | Long names, nested levels, wrap/scroll, selected state announced |
| Search | Label and query, optional validated suggestions, result path and clear | Typing, pending, no result, error, Escape, Enter, stale response, screen keyboard |
| Filter | Real attributes, selection, count, applied chips, clear | Multi-select, range, no eligible results, overlay close, back navigation; visible result count |
| Sort, columns and view | Shared toolbar: sort, grid/list or compact/detailed rows, column chooser only where these change the user's task | Visible selected columns and essential non-removable fields; preferences remembered where supported; keyboard labels, pressed states and no data loss when view changes |
| Product list/table | Identity, key decision facts and action; stable responsive reading order | Zero/large set, page position, mixed availability, progressive load without jumps |
| Button/link | One visual primary action per task block; secondary and destructive meanings distinct | Default, hover, focus, press, pending, success, failure, disabled *with explanation*; never hide a link behind a button look |
| Input/textarea | Visible label, help, input, inline error, next action | Empty, filled, invalid, awaiting validation, correct, pasted, autofill, zoom, long errors |
| Checkbox/radio/toggle | Label + consequences; use radio for one-of-many, checkbox for multiple | Checked/unchecked/indeterminate, focus, disabled explanation, preference persistence; never treat toggle as a one-off submit |
| Choice chips/swatches | Visible value name, selectable target, real stock/compatibility | Selected, sold out, absent image, changed price, long localized name; color alone never identifies a swatch |
| Price/money | Currency, amount, tax or recurrence when relevant, sale evidence | Pending quote, changed total, mixed currencies, thousands/decimals, long labels, real old/new price |
| Availability/fulfillment | Product/variant + location + timeframe/source status | In stock, out, unknown, digital, pickup, delayed, stale; no universal shipping line |
| Media gallery/zoom/video | Primary image then alternate/detail/scale/video poster | Loading/failure, correct variant, alt text, zoom exit, keyboard, video controls |
| Compare control | Selected product names/count, remove, meaningful table | Mixed category, max capacity, missing property, horizontal phone view |
| Cart and quantity | Item and selected variant, current total, edit/remove | Rapid changes, insufficient stock, promotion invalid, pending, duplicate request, undo if real |
| Checkout stepper | Current and completed steps with editable return path | Validation, method switch, external payment pending; never label processing “paid” |
| Dialog/drawer/dropdown | Title/purpose, content, actions, dismissal ([overlays-and-controls.md](overlays-and-controls.md)) | Trigger/return focus, Escape where safe, outside click only when safe; the page behind locked and inert; only the body scrolls; opaque lists in the theme; stacking, screen-reader role |
| Tooltip | Names an icon-only control on hover and focus; never carries an explanation | Touch and keyboard reach the same name; never essential price or policy |
| Info (i) help | Explains one non-obvious item on demand, right after its label ([help-and-ui-text.md](help-and-ui-text.md)) | Only where an item's purpose or effect cannot be inferred; opens on click, tap, Enter or Space, closes on Escape or outside click; plain text in at most two sentences; never on every card |
| Notice/alert | Severity, concise reason, next action, optional dismissal | Critical persists; on optional cards visible X plus compact menu: Minimize, Remind me in a week, Never show again; browser-local preference and exact expiry only if supported; failure is not a success toast |
| Expandable info box | In-place small `!` box + meaningful title replaces only the optional full card | Activate to reopen in the same slot; `aria-expanded`/`aria-controls`; remember minimized state in the same browser for new projects until reopened; closing moves focus out; never hide critical terms |
| Toast/status | One concise result and correction route if needed, in the brand's look (`assets/templates/toast.html`) | Announce once; duplicate request; no fake success; avoid covering cart/CTA on phone; above dialogs; errors stay until closed |
| Skeleton/progress | Reserves target geometry; real content arrives without jump | Slow/no network, abort, retry; avoid endless shimmer and fake percentage |
| Empty/error state | What happened, why if known, next safe action | No data vs zero, permission vs outage, refresh and loss of state |
| Table and bulk work | Stable identifier and status; shared toolbar for filter/sort/column choice and compact/detailed rows | Keep identity/status/action visible even when columns are personalized; many rows, selected rows, partial results, role restrictions |
| Chart/KPI | Measure, unit, time range, source/freshness, visual and underlying table | No/partial/delayed data, negative values, currency changes, keyboard/table alternative |
| Pagination/load more | Current place and next available range | Browser back, empty page, count changes, keyboard, scroll restoration |

Use native HTML controls and the project's existing accessible primitives where available. Replacing an icon family, introducing new notifications or changing list display across an established product requires owner approval as a visual/behavior scope decision.

## Card anatomy and 22 task roles

Shared alignment: related cards agree on outer rhythm, identity position, price/status row and action hierarchy. Use meaningful ratios and minimum heights instead of forcing titles to truncate. Card hover can reveal polish, but every action and fact must be present on focus/touch. A card's whole surface is clickable only if secondary controls retain distinct targets. Do not give every card a border, shadow or glass finish automatically.

| ID | Role and minimum facts | Main alternatives/failure case |
| --- | --- | --- |
| K01 | Category discovery: topic, representative image, destination | No image or long topic; heading remains HTML |
| K02 | Standard product: true image, name, current price, applicable availability | No media or price, variable title, no ratings unless real |
| K03 | Dense list product: image, name, 1–3 decisive facts, price | Changes from grid without losing decision facts |
| K04 | Technical product: name, model, comparable specifications, price | Unknown specification described, full table deferred to detail |
| K05 | Editorial feature: single curated story, product relationship, real route | Omit overlong copy and false campaign claim |
| K06 | Promotion: real old/new amount, term, end condition | Expired or unverified offer drops badge and savings claim |
| K07 | Unavailable/restock: product and current unavailability, allowed next step | Never show enabled “Buy” without real eligibility |
| K08 | Complementary item: relevant related product and actual linkage | Do not claim “people bought together” without data |
| K09 | Bundle: full contents, compatibility and real total | Mixed licenses, partial availability, invalid discount |
| K10 | Compare summary: chosen items and 2–4 critical differences | Missing value explained, remove control distinct |
| K11 | Saved product: identity, refreshed price and availability | Removed/renamed product, outdated saved snapshot |
| K12 | Recently viewed: optional with consent/data, clear route back | Don't infer tracking when unavailable |
| K13 | Review: attributed real rating/text with date or verified context | Empty, missing source, truncation must not invert sentiment |
| K14 | Trust promise: one verified benefit, evidence link if appropriate | Sometimes simple text row is more appropriate than a card; payment/provider logos stay static in one row, never a scrolling marquee |
| K15 | Buying guide: one decision question and expandable short answer | No authored guide means no decorative placeholder |
| K16 | Order summary: items, variant, fulfillment, amount and status | Split shipment, partial refund, secret masked |
| K17 | Digital access: entitled item, method, setup action | Pending/revoked access, no automatic key reveal |
| K18 | Cart row: product, chosen variant, quantity, line price, remove | Changing total, concurrent edit, narrow screen |
| K19 | Admin KPI: defined metric, period, unit and freshness; its definition goes in an (i) only when the name does not say it | No data not zero, permission denied not a red error graph |
| K20 | Admin task: issue, priority, accountable action, timestamp | Avoid all-red alert wall and fake undo |
| K21 | Admin media: thumbnail, rights, usage routes, missing alt | Broken asset, unauthorized use, variant dependency |
| K22 | Expandable note: `!` label, short summary, optional details | Real collapse/expand; critical message remains legible |

### Card behaviors that must be specified on a real page

For every selected role record: desktop width and alignment, phone order and action reach, long translation, missing image, empty text, supported theme modes, keyboard focus, mobile touch, loading/disabled/updated, screen-reader name, data/permission source, and which motion ID (if any) serves a function. K01–K13 may use M11–M19; K14 may use M45–M49 only if the claim is true; K15 uses M10 for its expandable answer; K16–K18 map to transaction motion (M26–M36); K19–K21 map to admin state motion (M41–M44); K22 uses M07. Using none is often the best option. Motion files: [core](motion-core.md), [browse](ecommerce-motion-browse.md), [buy](ecommerce-motion-buy.md), [after](ecommerce-motion-after.md).

## Six admin screen layouts

| Pattern | First question | Primary geometry | Avoid |
| --- | --- | --- | --- |
| Owner overview | Which decision needs attention now? | Few defined metrics → exception queue → compact trend | A wall of empty KPI cards |
| Order operations | Which order is blocked? | Filters/search → clear table → detail drawer | Piling up unrelated charts |
| Catalog and media | Which product cannot be published? | Completeness filters → product status → fix path | Hiding rights/alt text behind images |
| Support and returns | Who is waiting and why? | Priority queue → related order → case resolution | Three stacked modals and unclear state |
| Analysis and reports | What does this metric count? | Source/time/unit → chart → accessible table | Treating no-data as flat zero trend |
| Theme and settings | What would a change affect? | Scope → reversible preview → save/cancel | Showing a fake one-screen preview for all UI |

The six patterns are layouts, not six compulsory dashboards. Real roles and verified data decide which are present.

## Asset coverage by surface

- **Shared shell:** identity variants, favicon, nav icon family, UI status icons, focus/color tokens, locale labels.
- **Discovery:** category imagery, product cover angles, campaign master when real, crop masks/safe regions; no copied competitors' art.
- **Product decision:** variant thumbs, size/scale/fit charts, compatible-device labels, delivery/access symbol and optional media poster.
- **Transaction:** honest payment-provider marks used under their terms, order/return status icons; never an unofficial certification seal.
- **After purchase:** setup diagrams, masked key glyph, download file/type indicator, support and return documentation.
- **Admin:** chart series/markers, table symbols, media rights field, export indicator, partial-data warning.

Record asset identity and reuse in [design-contract.md](design-contract.md). Asset libraries are governed by meaning and rights, not by raw entry count.
