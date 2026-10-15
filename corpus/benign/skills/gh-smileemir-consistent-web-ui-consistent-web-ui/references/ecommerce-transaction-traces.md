# Ecommerce data and transaction traces

Use this original acceptance specification for real customer and operator workflows. It describes the **frontend's required truth**; it does not authorize changing an existing backend, payment processor, database or business rule. Mark each result `implemented and verified`, `designed only`, `blocked by real data/approval`, or `not applicable` for the actual project.

## One consistent quote

For a purchasable line keep `product ID, variant ID, currency/locale, unit amount, quantity, real discount scope, inventory condition, location, fulfillment method, shipping estimate/actual cost, tax estimate/actual tax, line total, cart total, quote timestamp/source`. The frontend should bind all dependent labels to the **same settled quote version**; if the source cannot supply one, show which numbers remain estimates and prevent an inconsistent CTA. A visual transition must not “fix” a logically mismatched price. Format only a valid amount in the user's locale, never calculate currency conversion by animating digits.

| Branch | Required rule | Visible exceptional state |
| --- | --- | --- |
| Physical goods | Pickup and shipping availability depend on real item, variant, location and inventory; estimated dates and fees are labeled | Unknown postcode, store closed, oversized delivery, split shipment, changing stock |
| Sized goods | A chosen fit/size/color maps to one valid SKU before add | Size unavailable, wrong image, size-guide unavailable, size removed while editing |
| Shade or formulation | Chosen shade/media/ingredients reflect actual variant; never tint a photo to simulate a shade | Photo absent, mismatched swatch, unverified ingredient claim |
| Configurable goods | Price, delivery and image update as one settled configuration; optional coverage stays separate | Required step unfinished, stale selection, incompatible component, coverage declined |
| Digital goods | Compatibility/region/license/term and entitlement method are explained; no physical shipping metaphor on a download-only selection | Payment pending, delayed activation, revoked entitlement, missing key/download; mixed physical/digital cart only if product supports it |

## Public frontend traces to test on a real project

| Trace | Actions and exact expected UI | Failure or recovery |
| --- | --- | --- |
| T01 Discover to product | Select a category → apply two real filters → change sort → switch meaningful grid/list view → open product. Count, chips, URL/state and selected product facts agree. | Zero results offers clear/reset; back restores applied constraints; removed/renamed item has a safe destination. |
| T02 Product to cart | Choose each required variant; wait for settled image/price/delivery; add once. Cart badge and line show the chosen SKU and quantity only after real success. | Missing selection has field-level explanation; rapid A→B→C ends on C; duplicate/failed request never displays false success. |
| T03 Cart edits | Increase/decrease, remove or save for later if supported, change pickup/shipping, apply a real code. The line, summary, shipping and tax qualification update together. | Stock/price change is explained; a failed code retains the old total; a rejected removal restores the correct row. |
| T04 Checkout identity | Continue as allowed guest/account → enter required contact only → return to cart then forward. Preserve the cart and original payment intent. | Invalid/duplicate email, interrupted login, consent requirements and address validation remain visible without claiming success. |
| T05 Fulfillment | Choose a real pickup location or delivery address → quote eligible options and estimated/final amounts. Digital-only orders show access method and actual contact/legal needs. | Region ineligible, store closed, missing quote, mixed delivery unsupported; do not fill in a cost that cannot be obtained. |
| T06 Payment start and return | Review exact quote → trigger the product's existing payment flow → show pending → inspect a confirmed success, failure or unknown result returned by the real system. | Double taps, provider redirect/back, expired session and offline: never treat a spinner or navigation as a successful charge; do not start a duplicate charge after an unknown result. |
| T07 Order outcome | For confirmed order, show true order ID, chosen items, delivery or entitlement and next action; a pending or failed result has its own screen. | Refresh, delayed email, split shipment and stale quote do not switch order identities. |
| T08 Physical aftercare | Track split order and fulfillment status; show return eligibility and request state separately from refund paid state. | Partial return, failed carrier update and refund pending get accurate status and source timestamp. |
| T09 Digital aftercare | Confirm entitlement first; then reveal only the correct key, download or account activation path for this product. Mask secrets by default. | Access pending/revoked, interrupted download, copy failure, long key, logged-out user and unsupported platform never leak credentials or fake delivery. |
| T10 Operator order | From A02 queue → A03 detail → permitted action → updated queue; share filter/sort/column/view grammar. | Role denied, competing changes, partial bulk success; backend meaning unchanged. |
| T11 Operator catalog | From A04 incomplete SKU → A05 variant edit → A09 media rights/alt review → safe preview and existing publish action. | Wrong shade or size image, missing rights, unsaved changes, publication rejection; customer page never displays a draft as live. |
| T12 Operator facts | Confirm A06 inventory freshness, A07 active discount scope, A11 report source/time/currency and A12 theme preview across routes. | Stale stock, expired coupon, partial metrics and unsaved theme never turn into believable but incorrect claims. |

## Complete route-level screen states

For **each applicable C01–C20 and A01–A12** record a representative normal state and exact input/output for `loading`, `empty`, `error`, `restored`, `unauthorized` where applicable, `long translation`, `narrow screen`, `keyboard`, `reduced motion`, and `stale source`. Record the real data dependency and route owner. A page without a backend may still have a prototype, but label the state simulated; never claim it tested a live purchase.

The five example design directions in this skill are **blueprints**. Before counting one as a working site, the owner approves that exact brand, real product fixture/content and rights; its responsive pages are built; T01–T12 are executed only where supported; device and accessibility evidence is recorded. Five briefs or color palettes do not equal five finished sites.
