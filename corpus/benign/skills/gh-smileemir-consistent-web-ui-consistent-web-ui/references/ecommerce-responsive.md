# Ecommerce responsive and interaction specification

This is an **original implementation and test specification**, not a record of a third-party mobile screen. Apply only the business branches the store supports. Use the existing route IDs from [ecommerce-pages.md](ecommerce-pages.md). A phone version is a complete task flow, not a scaled desktop screenshot.

## Viewport and content rules

- Inspect real layout at approximately 320, 360, 390 and 430 CSS px, a short landscape phone, tablet widths where a column breaks, narrow desktop and wide desktop; choose actual breakpoints where content ceases to fit. Repeat at 200% text and 400% browser zoom/reflow where feasible. Record browser, OS, keyboard and DPR. Do not claim a tested width that was not actually rendered.
- Keep semantic document order aligned with reading order. A two-column desktop purchase panel becomes media → identity → variant → price/availability → fulfillment → action → supporting details. Sticky purchase bars repeat current verified price/variant and do not cover inputs, errors, system gestures, legal terms or the last row.
- Reserve image geometry to avoid layout shift; choose crop by asset intent (portrait apparel, shade evidence, device ports, scale drawing), not one sitewide aspect ratio. A missing variant image gets an honest fallback, not another variant's picture.
- Keep one primary action visible per current task. Touch and keyboard must reach the same decision, including text that hover reveals on desktop. A destructive action is distinct from the product-card navigation surface.
- A visible filter or menu control announces state, count and close behavior. On mobile, preserve applied chips and result count outside a closed sheet; when results are applied, return focus to the toolbar or result heading. A column chooser is for real data tables and meaningful lists; do not cram it into a one-column shopping feed.
- Use locale-aware prices and delivery dates. Keep chosen product identity, price, discount reason, total qualification and available action as one coherent snapshot after rapid changes or navigation back.

## Customer flow, narrow screen decisions

| Routes | What stays reachable in reading order | Interaction or failure to verify |
| --- | --- | --- |
| C01–C02 Home and category | Name/purpose → relevant way in → categories/products; real delivery/support claim follows appropriate context | No hero that pushes the first useful route below multiple screens; image failure leaves HTML heading and destination. |
| C03–C04 List and search | Query/category, count, selected constraints, filter/sort/view then items | Open sheet on short screen; keyboard doesn't cover suggestions; cancel/apply semantics clear; back restores query and scroll; stale response cannot overwrite newer input. |
| C05 Product | Correct variant image, title, price, options, stock/delivery/access, CTA, support facts | Swatches have names and stock labels; sticky CTA never contradicts selected variant; image zoom closes, restores focus and cannot trap swipe scrolling. |
| C06 Compare | Product identity and at least one comparable trait alongside each value | Frozen labels or stacked alternative if wide table cannot fit; missing values are text, not empty winners; focus order matches visual order. |
| C07 Saved | Product and *current* price/availability with separate remove and view targets | Guest/local/account behavior is truthful; old snapshot explicitly refreshes or says unavailable. |
| C08 Cart | Each line's chosen variant, quantity, line price, remove, then quote and checkout | Long SKU/title, quantity changes while network pending, out-of-stock and updated tax; sticky summary does not hide last item. |
| C09–C12 Checkout | Stage, actionable field labels, local error, price/delivery summary and next step | On-screen keyboard/safe area, back/refresh restoration, offline and interrupted payment; never call an estimate final or show a paid state before confirmation. |
| C13–C16 Outcome, orders, access, returns | Confirmed state and permitted next action before decorative content | Guest lookup, split shipment, partial refund, entitlement pending/revoked and masked secrets have separate titles/actions. |
| C17–C20 Help, account, policies, recovery | Current issue or preference, supporting fact, real recovery route | 404, expired session, support closed, long legal/translation text; critical policy stays reachable, optional cards may collapse only by explicit action. |

## Operator flow, narrow screen decisions

| Routes | Essential data | Check |
| --- | --- | --- |
| A01, A11 | Timeframe, currency, source/freshness, a few defined metrics and exception queue | Do not place a colorful chart before blocked work or show missing data as zero. |
| A02–A04, A06, A08 | Record identity, date/status, next permitted action; shared filter/sort/columns/compact/detailed controls where useful | A row can stack on phone, but selected records and authorization do not disappear; bulk work cannot accidentally act on hidden rows. |
| A05, A07, A09 | Draft content, rights/variant or promotion scope, preview, explicit save/publish state | Long editor fields and upload failures remain recoverable; media rights and price date do not disappear in a collapsed tab. |
| A10, A12 | Role-masked identity and current setting versus proposed preview | Theme preview includes alerts, modals, checkout, customer and admin surfaces; a visual save does not silently change access. |

## Interaction and motion test cases

1. In a phone browser with a virtual keyboard, type a query then switch filters: the keyboard, sheet and selected-result action must not overlap. Repeat at large text size and with screen reader focus.
2. Choose variants A → B → C quickly while B image is slow. Only C may supply the final image, price, inventory, CTA and delivery text; keep the previous valid state or show an explicit pending quote while inputs are unsettled.
3. Change cart quantity as another item becomes unavailable. Preserve the affected line and explain the new total; a repeated tap cannot falsely indicate two successful additions.
4. Open a long optional notice; choose **Minimize**, then use the small labeled `!` control in the same position to reopen. Confirm focus relocation, reduced motion, browser-local persistence and honest one-week expiry. Never allow dismissal of required payment/legal/safety facts.
5. On touch, compact decorative cards may play a one-time illustration when roughly 85–95% visible, but a taller card requires a reachable *meaningful section*. Labels, prices and controls stay usable from first paint. On desktop hover/focus play once per entry, with no repeating full animation. Reduced motion shows the final state immediately.
6. Inspect for sticky-content occlusion at the bottom of the page, system safe areas, software keyboard appearance, landscape, high zoom and a long translated currency. Test real pointer, touch and keyboard; mouse-resized desktop is useful but does not prove phone behavior.

**Evidence gate:** record screenshots or an exact observed state for each tested browser/viewport and result for category → filter → product → cart → accessible public checkout. A declared CSS breakpoint, official help page, or a desktop viewport cannot close a live-phone interaction gap.
