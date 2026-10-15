# Ecommerce motion records: buy (M20-M36)

Apply [motion-core.md](motion-core.md) first. Timings are hypotheses to test, not measurements.

## Product selection and cart

### M20 Gallery thumbnail

**Purpose/trigger:** Link chosen image to the currently selected product variant. **Timeline:** thumbnail selection outline 120–180 ms; new main image crossfades 140–220 ms only after its correct file loads. **Interrupt:** fast image changes keep the latest intended picture; a failed load leaves an honest placeholder or previous labeled image, never another variant masquerading as current. **Access/test:** arrow/keyboard navigation, meaningful alt text, natural phone scrolling; reduced motion swaps directly. Test 1 image, many images and failed media.

### M21 Zoom, product video and size drawing

**Purpose/trigger:** Let a buyer inspect detail on request. **Timeline:** zoom container appears in 200–280 ms, retaining the product's selected point; size diagram remains readable as static content. **Interrupt:** close/Escape returns focus and video stops; loading failure offers original media. **Access/test:** video uses poster/controls and captions when applicable; no automatic sound, pinch handling cannot steal page navigation; under reduced motion zoom opens without travel.

### M22 Product variant choice

**Purpose/trigger:** Make the selected size, shade, capacity or license unmistakable. **Timeline:** selected ring 120–180 ms; genuinely changed product image fades after load in 160–220 ms. **Interrupt:** only the newest choice's quote and image may render; unknown price/availability exposes pending state, not old facts beside a new choice. **Access/test:** out-of-stock choices remain explained, radio/choice semantics and touch match, reduced motion direct; test quick three-way selection and offline failure.

### M23 Price or currency update

**Purpose/trigger:** Communicate a confirmed value change without corrupting its formatting. **Timeline:** optional change-only digit roll 180–240 ms; use a direct replacement for a major magnitude, different digit length or slower device. **Interrupt:** invalid or superseded quote never completes its visual story. **Access/test:** screen reader announces final price once; decimals, thousands, tax, negatives and locale remain correct; don't pair old amount with new delivery. Reduced motion changes directly.

### M24 Availability and delivery lookup

**Purpose/trigger:** Answer whether, where and when a product is actually obtainable. **Timeline:** pending label within about 120 ms of an actual lookup; verified response resolves in 140–200 ms without celebratory entrance. **Interrupt:** changing location or variant invalidates older response; stale inventory says stale, not “available.” **Access/test:** physical shipment, local pickup and digital access use distinct text and icon; long phone address wraps; reduced motion direct.

### M25 Comparison tray

**Purpose/trigger:** Keep chosen compatible products visible until comparison. **Timeline:** add reveals small tray over 160–220 ms and updates true count; removal 120–180 ms. **Interrupt:** changing route, unavailable product or maximum capacity updates labels and actions without stale selection. **Access/test:** tray never obscures mobile purchase CTA, keyboard/close focus follow M08, mismatched categories have an explanation; reduced motion direct.

### M26 Quantity control

**Purpose/trigger:** Change an allowed item count safely. **Timeline:** press feedback 100–150 ms, confirmed number settles in 160–200 ms if animation helps; display true total as one coherent value. **Interrupt:** rapid presses, stock boundary and failed update settle on one real quantity, not a phantom intermediate number. **Access/test:** minimum/maximum and item limits are in text; announce final value once; 1→0 removal uses the real cart rule; reduced motion direct.

### M27 Add to cart

**Purpose/trigger:** Link a selected product with confirmed cart state. **Timeline:** button enters pending within 100 ms; on real success update cart count immediately; optional small visual path to a *measured, visible* cart icon lasts 400–550 ms. **Interrupt:** failed add aborts success motion, leaves selected variant intact and offers retry; repeated tap follows the existing cart operation's idempotency rule. **Access/test:** a hidden mobile cart icon removes the flight animation; no secret or license value enters a visual clone; reduced motion uses result text/count only.

### M28 Cart drawer

**Purpose/trigger:** Confirm the newly added item and show the next path. **Timeline:** open 240–320 ms after real add, highlight only the new row once over 450–650 ms; total changes to a verified number. **Interrupt:** another successful add updates the current drawer instead of replaying its whole entrance. **Access/test:** one dominant checkout action, shopping return clearly secondary, internal scroll and mobile full-screen variant, Escape/focus return; reduced motion direct.

### M29 Remove and genuine undo

**Purpose/trigger:** Explain a removal and permit reversal only where supported. **Timeline:** after confirmed removal row closes in 180–260 ms and total updates in 160–220 ms; no violent reflow. **Interrupt:** failed removal restores item with an error; parallel removals reconcile with the final server cart. **Access/test:** last item reaches an honest empty state, undo stays reachable and long enough when implemented, reduced motion direct removal plus announcement.

### M30 Real timed offer

**Purpose/trigger:** Show a verified offer deadline where one exists. **Timeline:** only changed clock digits may update over 100–160 ms, with no whole-card flash every second. **Interrupt:** background tab or clock drift must recalculate from the actual expiry; on expiry revalidate product price and checkout. **Access/test:** no artificial timer or invented stock limit; remaining time also appears as text; reduced motion has a static textual time and data still updates.

## Checkout and order outcome

### M31 Checkout step progress

**Purpose/trigger:** Locate the buyer in the real purchase journey. **Timeline:** validated progress indicator changes in 180–260 ms; next form is immediately available and focus moves to its heading. **Interrupt:** invalid submission does not mark a step complete; browser back restores real known fields. **Access/test:** narrow view uses clear step names, no lost data or clipped heading, reduced motion direct.

### M32 Form validation

**Purpose/trigger:** Help correct the exact field and retain progress. **Timeline:** on a real error, quiet border/help text appears within 120–180 ms without shaking the field; on correction, error disappears without moving focus. **Interrupt:** server error may override local validity, and a newer value wins over a delayed old response. **Access/test:** focus first invalid field after submit, group and summarize errors, phone keyboard doesn't obscure message, reduced motion direct.

### M33 Fulfillment/address selection

**Purpose/trigger:** Show what a delivery choice changes. **Timeline:** selected method ring 120–180 ms; relevant fields reveal in 180–260 ms; only quote-confirmed cost appears beside method. **Interrupt:** changing address invalidates earlier shipping total; mixed carts split by supported fulfillment policy. **Access/test:** pickup, physical shipping and digital access have distinct descriptions, unsupported location gets a real next step, reduced motion direct.

### M34 Coupon apply

**Purpose/trigger:** Report an actual eligibility calculation. **Timeline:** pending button within 100–150 ms; verified discount row and total settle 160–220 ms. **Interrupt:** expired, invalid or conflicting code has a reason, duplicate submit must not apply twice. **Access/test:** currency, tax and promotional conditions remain legible; never celebrate a discount before validation; reduced motion updates numbers directly.

### M35 Payment pending and failure

**Purpose/trigger:** Explain transaction status without implying a charge succeeded. **Timeline:** input acknowledgement immediately, clear “processing/checking status” label while the real provider returns; no decorative timer can signal approval. **Interrupt:** refresh, back, network loss, external challenge and repeated tap preserve the existing payment safety rules; unknown outcome remains unknown until confirmed. **Access/test:** text-only status works with no spinner and reduced motion; never enable a second charge blindly.

### M36 Order result

**Purpose/trigger:** Give a confirmed outcome and a next action. **Timeline:** true success heading/summary may enter once in 260–400 ms; pending or failure uses distinct static content, no confetti or delayed access. **Interrupt:** reload and partial fulfillment keep the actual outcome. **Access/test:** order ID copy on phone, digital entitlement only after permission check, help route always present; reduced motion displays all facts immediately.
