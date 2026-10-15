# Ecommerce motion records: after purchase, operators and promises (M37-M49)

Apply [motion-core.md](motion-core.md) first. Timings are hypotheses to test, not measurements.

## After purchase and administration

### M37 Order status timeline

**Purpose/trigger:** Explain a genuine preparation or delivery progression. **Timeline:** existing steps may reveal as a group in 300–500 ms on first load; a confirmed new step gets a 160–240 ms accent. **Interrupt:** delayed, reversed or split shipments create their own explicit states; do not just slide a progress indicator backwards without explanation. **Access/test:** each step has text and real time when supplied, estimates differ from actual confirmations; reduced motion is a plain status list.

### M38 Digital key or access reveal

**Purpose/trigger:** Disclose an entitled secret only after an intentional Reveal action. **Timeline:** after permission and data arrive, bounded mask-to-visible transition 220–400 ms; do not roll a long key one character at a time. **Interrupt:** role loss, refresh or route change re-mask as required by the existing security model; failure remains masked with help. **Access/test:** key, download link and account access are distinct views; button keyboard accessible, copy may operate without visible reveal if authorized; reduced motion immediate.

### M39 Copy or download status

**Purpose/trigger:** Confirm what actually reached clipboard or download. **Timeline:** successful copy icon/text updates in 140–200 ms and can return after roughly 1.5–2.5 s; prepared file uses a real stage, not a fake percentage. **Interrupt:** denied clipboard or missing file never shows a tick, retry remains possible. **Access/test:** announce result once, long code not exposed by toast, touch and keyboard equivalent; reduced motion immediate.

### M40 Return or cancellation request

**Purpose/trigger:** Explain a consequential request and its exact status. **Timeline:** optional confirmation drawer follows M08; a confirmed list-row status settles in 180–260 ms. **Interrupt:** two submissions must not invent two refunds; a failed or partially fulfilled request shows its actual state. **Access/test:** “request received” is never “money returned”; physical/digital eligibility and destructive confirmation are visible; reduced motion direct.

### M41 Admin sidebar

**Purpose/trigger:** Expose workspaces while keeping route orientation. **Timeline:** expand/collapse 180–260 ms; active route and focus remain clear. **Interrupt:** navigation loading does not auto-open/close the sidebar repeatedly. **Access/test:** icon-only state needs accessible names and visible explanation when needed; on phone it becomes an M01-style drawer; reduced motion direct.

### M42 Admin table, filters and details

**Purpose/trigger:** Find an order/product and operate on the right row. **Timeline:** filter selection 120–180 ms and table updates only when real results arrive; row detail opens 180–240 ms. **Interrupt:** stale results and partial bulk work display explicit pending/error status, never appear current. **Access/test:** selection count exact, long row details do not scramble columns, phone structured rows retain all vital facts, reduced motion direct.

### M43 Admin KPI and chart refresh

**Purpose/trigger:** Show how a *newly valid* metric relates to a time range. **Timeline:** first load displays number and freshness honestly; changing a valid series may crossfade over 180–260 ms. Do **not** count from zero to a real revenue number as entertainment. **Interrupt:** currency switch, partial period or no-data invalidates misleading charts. **Access/test:** table equivalent, unit labels, negative numbers and assistive names persist; reduced motion shows final chart/table directly.

### M44 Admin bulk action and result

**Purpose/trigger:** Keep operator aware of how many records were affected. **Timeline:** selection count immediately correct; confirmation follows M08, actual pending then per-row success/failure, optional restrained 160–220 ms row highlight. **Interrupt:** partial failure cannot collapse into a single green success toast; undo appears only if backed by a real reversible action. **Access/test:** role permission, concurrency, route exit and changed sort state; reduced motion directly presents the same per-record result.

## Verified promise icon stories

Only use these when the store actually makes and supports the corresponding claim; they are not a mandatory trust-card row. Icons share a visually balanced roughly 36–44 px drawing area, matching stroke weights and a short single-play rhythm. On desktop pointer hover and keyboard focus start once, with no looping completion animation while hovered; on touch, play once after **meaningful actual visibility**. If a card fits in the viewport, around 85–95% intersection is a useful *proposal*; for a tall card, observe its relevant message area instead. If several appear at once, stagger modestly; always show the semantic icon and text before motion. Reduced-motion mode shows each finished icon immediately. Use a quiet static hover surface if helpful, not a continuously moving effect. An illustration never serves as proof of certification, delivery or payment success.

### M45 Real delivery method

**Purpose/trigger:** Reflect an actual shipping, pickup or digital access promise in a small category-appropriate icon. **Timeline:** 0–180 ms route/receive outline appears; 180–420 ms a single marker reaches the *correct* destination; 420–500 ms a slight confirmation emphasis settles and stays still. **Interrupt:** a changed delivery condition drops the old icon/message immediately; leaving hover stops any surface response without replay. **Access/test:** no truck on a download-only product, claim text includes its real conditions, mobile one-shot with no overlapping neighbors, reduced motion static meaning.

### M46 Genuine verified product or authorized access

**Purpose/trigger:** Support a documented authenticity/authorization statement; do not imply outside certification without evidence. **Timeline:** 0–220 ms delicate shield outline, 220–400 ms one small check forms, then stops. **Interrupt:** if source validity changes, remove the verified mark and statement rather than leaving a reassuring animation. **Access/test:** a concrete label and evidence path where appropriate, keyboard and phone equivalent; no perpetual spinning seal; reduced motion static check.

### M47 Existing support channel

**Purpose/trigger:** Indicate an actual way to reach help. **Timeline:** 0–180 ms message outline, 180–360 ms two or three dots appear once, 360–480 ms they settle. **Interrupt:** channel closure updates availability copy, the dots never keep “typing” as if a human agent were live. **Access/test:** link opens a real route, actual support hours/expectation are stated, focus and touch work, reduced motion static speech icon.

### M48 Factual payment protection explanation

**Purpose/trigger:** Direct attention to real provider/process information without claiming approval. **Timeline:** 0–220 ms small card/keyline, 220–420 ms a single lock/check stroke resolves and stays still; any provider logo remains static and used under its own rights. **Interrupt:** payment failure cannot leave a completed-looking success state. **Access/test:** text describes what the checkout actually offers, screen reader hears that text, not “certified secure” unless justified; phone and reduced motion use static mark.

### M49 Actual returns/exchange policy

**Purpose/trigger:** Clarify a truly applicable return or exchange route. **Timeline:** 0–260 ms a restrained return arrow traces a short arc, 260–420 ms an actionable support/policy state settles. **Interrupt:** if the product type is ineligible, omit or change the module to explain the real exception; never universalize a conditional right. **Access/test:** timeframe and digital exceptions in ordinary text, direct link to policy, focus/mobile/reduced motion retain the same information.
