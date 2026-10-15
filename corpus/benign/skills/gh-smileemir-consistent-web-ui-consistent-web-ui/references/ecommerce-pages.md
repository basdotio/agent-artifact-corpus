# Ecommerce page blueprints

## Contents

- Customer path C01–C20
- Admin path A01–A12
- Decision branches, cross-route and release gates

**Status:** Original design proposals for a single-seller store, with physical, digital and configurable product branches. These are not observations of any other shop and do not assert that a real checkout or admin backend exists. Activate each page only if the business model and existing product data support it. Use [design-contract.md](design-contract.md) for brand tokens, [ecommerce-components.md](ecommerce-components.md) for exact control/card roles, and [motion-core.md](motion-core.md) plus the ecommerce motion files for optional motion IDs. Default semantic source order follows the orders below even if desktop presents two columns. For every page test loading, empty, long-content, failure, reduced-motion, dark theme if supported, small and short phone, tablet, desktop and keyboard.

## Customer path

### C01 Home — orient, then offer a clear route

**Order:** shared header → plain-language value proposition and one useful primary path → category or task-based discovery → a small number of **distinct** real product collections → how buying works here (delivery or access, returns, support) in plain page text → a short FAQ answering real pre-purchase questions from the owner's policies (C17), with visible owner placeholders where an answer is not supplied yet → footer. Keep it simple: a few complete sections beat many thin ones. At most one optional information card (K22) may carry a non-critical tip; delivery, licence, refund and price terms stay in the page, never only in a dismissible card or an (i). If the catalog is small, a few complete shelves beat a long repeated grid; give each shelf one job, hide a shelf that has no current items instead of padding it, and do not repeat the same products across shelves to fill space. Do not create a sale, bestseller, review, low-stock, countdown or membership claim unless supported by current data. Products that cannot currently be bought should normally leave sale-oriented home shelves; keep their detail routes discoverable elsewhere when useful. **Small screens:** first useful category and call to action appear early; horizontal shelves have obvious direction, keyboard alternatives and no hidden final item. **States:** zero catalog, unavailable whole collection, category image missing, stale stock, guest/account. **Check:** a new customer can name the shop's purpose and reach a relevant product in one clear choice.

### C02 Category gateway — choose the right subset

**Order:** breadcrumb → category title/brief scope → subcategories or task entry points → relevant buying aid → products/results. Show editorial imagery only if it helps distinguish product types; it must not displace access to products. **Small screens:** subcategory labels remain legible without hover; crop keeps subject and doesn't contain essential type. **States:** shallow taxonomy, no products, mixed fulfillment, category renamed, restricted products. **Check:** leaving this page for C03 or another category preserves the customer's understanding of location.

### C03 Product listing — narrow without losing context

**Order:** category/query context → result count and active selections → one shared filter/sort/view toolbar, with a column chooser where meaningful → grid, list, compact or detailed rows as needed → pagination or continuation → optional help. Base filters on real attributes of that category; preserve logical selected filters in the URL or existing project state, with an explicit reset. A selected column, grid/list or row density never removes required name, price or availability. Same-page changes render results without a full reload when supported by the existing data flow. **Small screens:** filter opens a reachable panel; result count and selected chips remain visible; one readable mode can replace irrelevant controls. **States:** zero results, stale result count, out-of-stock, page boundaries, mixed variants. **Check:** filter, sort, back navigation, visible columns and view choice remain correct together.

### C04 Search — repair a failed query

**Order:** editable query → relevant suggestions only when available → results by meaningful type → the same filter/sort grammar as C03 → no-results recovery. Suggestions that cannot be validated are omitted; do not present invented matching inventory. **Small screens:** software keyboard must not cover suggestion selection or clear control. **States:** empty text, typing, pending, results, no result, server failure, abandoned query, repeated requests. **Check:** keyboard Enter, Escape and clear behave predictably; a stale response cannot overwrite a later query.

### C05 Product detail — make the decision before the CTA

**Order:** product identity and media → verified price → required selection → compatibility/fit and delivery/access details → one dominant action → specifications/care/terms → actual reviews or help if present. **Physical:** fit, dimensions, finish/size, local stock, shipping or pickup and included items. **Digital:** region/device compatibility, license or access type, account requirements, delivery method, setup and support; no shipping art or promise. **Configurable:** selection updates price, media, availability and delivery as a coherent set; keep prior choices when stepping back. **Small screens:** media first, title/price/choice and true availability remain in reading order; optional sticky purchase bar mirrors current selection and never hides conditions. **States:** unavailable variant, no photo, pending quote, location unknown, changed price, duplicate add request. **Check:** customers can say exactly what they will receive and when before committing.

### C06 Comparison — expose meaningful differences

**Order:** selected products and remove action → category-relevant comparable traits → highlight differences if helpful → return-to-product or add action. Comparing unrelated product classes or a single item does not justify a comparison screen. **Small screens:** horizontally scrollable comparison retains a visible feature label and product identity; provide an alternative readable stacked layout when the table cannot fit. **States:** missing value states “not supplied” or an appropriate explanation, mismatched units, invalid variant, product removed. **Check:** a customer can identify a decisive difference without decoding an icon-only table.

### C07 Saved items — re-enter discovery with current facts

**Order:** saved items → current price/availability → product detail or removal. Honor the actual guest persistence and login rules of the app; never expose one account's saved data in another. **Small screens:** list view may be clearer than narrow cards, but keep current status and removal distinct. **States:** empty, expired saved product, price updated, permission error, sync failure. **Check:** an old saved price never looks like today's price.

### C08 Cart — edit an order without surprises

**Order:** items and chosen variants → quantity/edit/remove → physical/digital delivery groups if supported → transparent subtotal and *estimated* taxes/shipping where applicable → continue-to-checkout. Do not label an estimate final. Mixed delivery groups need explicit rules; if the current checkout cannot handle both, state the limitation rather than inventing a merge. **Small screens:** item controls precede the sticky summary; CTA does not cover last editable row. **States:** empty, insufficient stock, stale price, partial removal, invalid coupon, concurrent cart update. **Check:** line totals and order total agree after rapid edits and browser back.

### C09 Checkout identity/contact — ask only what is needed

**Order:** checkout progress → existing guest/account choice → necessary email/contact → concise privacy/terms context → continue. Keep actual authentication/consent rules. **Small screens:** labels persist when filled; errors attach to individual fields and summary as needed. **States:** recognized customer, guest, invalid address, login interruption, pending verification. **Check:** changing sign-in method does not erase a valid cart or start payment.

### C10 Checkout delivery/access — separate fulfillment types

**Order:** physical address or pickup / digital delivery or access method → verified options → cost and time with qualification → continue. Location and configured product can change real availability. Never ask for a street address for digital-only goods without an actual business/legal need. **Small screens:** long address/locker options stack; the current option and its cost remain visible. **States:** no service at address, multiple shipments, location unknown, recalculation, digital account missing. **Check:** revising the address refreshes both shipping and final summary consistently.

### C11 Checkout payment/review — one deliberate commitment

**Order:** item and fulfillment recap → full payable amount with currency and conditions → existing payment methods → explicit final action. Keep provider-hosted fields, security, existing legal text and authorization unchanged. **Small screens:** review remains available before final action; avoid layers that hide order total. **States:** invalid method, authorization pending, external verification, failed, abandoned, duplicate tap, unknown outcome. **Check:** pending is not success; a repeated tap does not produce a duplicate order because the underlying system's protection remains in place.

### C12 Order outcome — state what actually happened

**Order:** success/pending/failure header based on confirmed state → order identifier if available → exact next step → delivery/access path → help. Do not expose digital keys before entitlement is confirmed. **Small screens:** identifier can be copied, instructions wrap, next step visible. **States:** provider callback delayed, refresh, email delayed, partial fulfillment, order not found. **Check:** every status has the correct recovery route and none assumes payment has succeeded.

### C13 Order history/detail — make the past auditable

**Order:** list with date/status → order detail with items, paid amounts, fulfillment, status history and support. A real guest lookup may use the current project's order credentials; never fabricate a lookup endpoint. **Small screens:** order summary cards preserve total and status, detail is a separate navigable view. **States:** zero orders, split shipments, partial refund, masked sensitive key, permission denied. **Check:** signed-out, other-account and expired-session states do not leak data.

### C14 Physical delivery tracking — explain progress, not certainty

**Order:** factual status and last update → carrier/reference where real → estimated versus confirmed times → exceptions and help. Only show live map if truly provided; do not animate a parcel along guessed steps. **Small screens:** timeline is readable as a vertical text list and dates are localized. **States:** label created, unshipped, delayed, out for delivery, returned, missing feed. **Check:** a delayed order cannot still be represented by a cheerful “arrives today” banner.

### C15 Digital delivery/access — help someone use what they bought

**Order:** purchase identity and compatibility → account/download/key path based on real fulfillment → setup → troubleshooting → support. Mask secret content until the customer intentionally reveals it; copy action may not require visible reveal if existing security rules allow it. **Small screens:** long codes and URLs wrap or scroll without spilling offscreen. **States:** entitlement pending, file unavailable, unsupported platform, already redeemed, revoked access. **Check:** refresh and permission loss leave no stale unlocked key on screen.

### C16 Returns, cancellation and problems — clarify what was requested

**Order:** eligible items and true conditions → issue/reason → action summary and confirmation → request status and help. Digital and physical returns have distinct rules; the UI must separate “request received”, “approved”, and “funds returned.” **Small screens:** attach evidence only if actually supported; confirm destructive changes before submission. **States:** ineligible, partial return, duplicate request, timed-out submission, rejected evidence. **Check:** a failed request never produces a completed refund message.

### C17 Buying guide/FAQ — answer the hesitation

**Order:** topic navigation → short direct answer → decision aid, applicable product or support route. Do not move extensive editorial content above urgent price, availability and purchase facts on C05. **Small screens:** accordions expose their state to keyboard and assistive technology. **States:** no answer, outdated content, translated title wraps, conflicting policy. **Check:** answer and policy agree on actual terms.

### C18 Account/settings — avoid losing preferences

**Order:** account identity → addresses (if needed) → locale/currency → notification choices → order/security links. Persist only preferences supported by the product; don't invent payment data storage. **Small screens:** settings form shows saved/unsaved state and protects unsaved changes on navigation. **States:** guest, stale session, validation error, permission change, multiple locales. **Check:** theme, language and currency preference do not silently reset an in-progress cart.

### C19 Support/contact — route to a real channel

**Order:** issue or order context → available channel and actual hours/response expectation → contact action → history if implemented. Do not call an asynchronous form “live chat.” **Small screens:** long order IDs remain copyable and visible. **States:** support closed, no order, upload failure, request received, no reply yet. **Check:** every action goes to an existing support destination.

### C20 System and policy pages — recover or inform

**Cases:** 404, no results, empty state, offline, session expired, access denied, maintenance; policy, privacy, shipping and returns pages when relevant. Each screen needs a specific task label, explanation and return path; no generic pretty illustration substitutes for recovery. **Small screens:** heading, action, help and footer remain reachable. **Check:** product and checkout errors offer safe navigation without duplicating a transaction; legal/policy copy is supplied by the product owner, not invented by the skill.

## Admin path

Admin screens are original task designs. They must not be described as audited examples of another service. Show only data and actions permitted by the real system; missing authorization and data stay documented dependencies.

### A01 Owner overview

**Order:** timeframe and freshness → 2–4 well-defined real numbers → urgent queue with direct resolution path → compact trend with labeled units. **Small screens:** place urgent work before decorative charts; each metric includes its timeframe. **States:** no data, partially loaded, stale period, restricted metric, mismatched currency. **Check:** figures reconcile with A11 under the same filters.

### A02 Order queue

**Order:** shared search/filter/sort/columns and compact/detailed row controls → readable table → row detail → permitted bulk action. Keep an item identifier, status and next allowed action visible even when optional columns are hidden. **Small screens:** structured rows retain identity, status, date and amount; bulk selection is explicit. **States:** none, many, partial success, conflict, permission denial. **Check:** status and count update in place with one consistent result after an action, preserving selection and view preference where supported.

### A03 Order detail

**Order:** current state and timestamp → customer/order identity under role rules → fulfillment/payment history → actions → notes/support. Mask digital secrets; visually separate order actions from notes. **States:** concurrent update, split order, refund pending, forbidden action. **Check:** an admin cannot confuse a request with a completed refund.

### A04 Product queue

**Order:** search/filters including type and publication → listing with media, stock and completeness → bulk controls when permitted. **Small screens:** show critical publication blockers without unreadable 12-column table. **States:** no media, stale inventory, out-of-stock, multiple variants. **Check:** unavailable home merchandise does not appear as purchasable.

### A05 Product editor

**Order:** identity/content → real variants/media → price display → availability → preview → publish/save. Keep actual backend validation; frontend preview is not publication. **Small screens:** grouped steps and always visible save status; warn before losing changes. **States:** unsaved, invalid, saving, conflict, published, permission denied. **Check:** editing a variant cannot silently mislabel a different image.

### A06 Inventory and fulfillment

**Order:** source and last sync → exceptions → SKU/location status or digital delivery queue → correction path. **Small screens:** display item, location and last update before secondary metrics. **States:** stale feed, manual delivery, no source, delayed job. **Check:** stock uncertainty does not generate false scarcity copy in customer UI.

### A07 Promotions

**Order:** active/scheduled/ended offers → scope and dates → real price preview → publish controls. **Small screens:** validity conditions remain adjacent to resulting price. **States:** conflicting promotions, invalid reduction, expired offer, unknown tax. **Check:** customer price and admin preview agree for one selected variant/currency.

### A08 Returns/support queue

**Order:** current requests by priority → related order and SLA if real → details and evidence → permitted resolution. **Small screens:** one case at a time with status always visible. **States:** pending evidence, partial refund, duplicate request, closed case, permission revoked. **Check:** a support resolution does not masquerade as a payment event.

### A09 Content and assets

**Order:** where used → media previews with rights and accessibility data → publish/replace → history. **Small screens:** show preview and source fields in sequence; avoid a gallery that hides missing rights. **States:** missing master, unsupported format, no alt text, license unresolved. **Check:** shared image update identifies every affected page before publication.

### A10 Customer and roles

**Order:** permitted account search → restricted profile summary → allowed actions → audit record if present. **Small screens:** mask sensitive details and avoid hidden buttons in horizontal tables. **States:** no access, ambiguous match, expired session, action rejected. **Check:** UI does not display or imply privileges the current role lacks.

### A11 Reporting

**Order:** source and date/currency definitions → primary metrics → explanatory chart → accessible data table → export if already supported. **Small screens:** chart and its data table stay synchronized. **States:** zero, partial, delayed, invalid comparison period, mixed currency. **Check:** “no data” is not a value of zero; tables express the same calculation as the chart.

### A12 Settings/appearance

**Order:** editable theme/localization and support settings → cross-page preview → change scope → save/cancel and rollback. **Small screens:** preview lists affected surfaces, not a tiny fake homepage. **States:** unsaved, validation failure, missing permission, stale version. **Check:** a theme switch covers modal, toast, product, account and admin states; this screen must not mutate backend infrastructure without permission.

## Cross-route release gates

1. Match product identity, selected variant, price, currency and fulfillment across C03 → C05 → C08 → C11 → C12 → C13. A changed quote must be explained, not animated away.
2. Trace a physical purchase from stock and address to C14; trace digital entitlement to C15. Treat mixed carts only if the existing business system really supports them.
3. Run the same search/filter/view language through C03/C04 and A02/A04 where tasks overlap, adjusting information density for operator needs.
4. Complete keyboard, touch, accessible names and failure recovery for every visible route; check permissions on account, order and admin screens.
5. Every page is a blueprint until real brand inputs, data, code, device behavior and owner decisions are verified. Do not declare the ecommerce sector fully validated without live mobile and checkout observations and a real prototype review.
