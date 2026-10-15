# Ecommerce motion records: browse (M01-M19)

Apply [motion-core.md](motion-core.md) first. Timings are hypotheses to test, not measurements.

## Shell and communication

### M01 Mobile navigation drawer

**Purpose/trigger:** Open real navigation from the menu button; focus moves into the drawer. **Timeline:** backdrop opacity 0→final over 100–160 ms; panel opacity and translate 12–20 px→0 over 260–320 ms; exit 180–240 ms. **Interrupt:** Escape, close button and safe backdrop click converge on the same closed state; rapid reopen reverses from the current frame, and an existing drawer closes when another opens. **Access/test:** trap focus only for a true modal drawer, return it to the opener, allow internal scroll on a short phone and prevent background interaction; under reduced motion change state and focus immediately.

### M02 Category submenu

**Purpose/trigger:** Reveal navigable subcategories on click or keyboard activation; hover may enhance but never be sole access. **Timeline:** 6–10 px + opacity in 160–220 ms, out 120–160 ms. **Interrupt:** moving across trigger/panel must not cause accidental closure; Escape or focus leaving closes the intended menu. **Access/test:** mobile uses an in-menu expandable group, not hover; check rapid movement between adjacent submenus, long labels, and reduced-motion instant state.

### M03 Search suggestions

**Purpose/trigger:** Surface actual suggestions after input changes. **Timeline:** input pending state immediately, verified list opacity over 140–200 ms; avoid animating every result on every keystroke. **Interrupt:** a late response to an earlier query cannot overwrite the newest one; Escape closes, changing language clears incompatible suggestions. **Access/test:** arrows, Enter and Escape work; phone keyboard cannot hide results; zero, loading and error labels are visible without animation.

### M04 Compact sticky header

**Purpose/trigger:** Keep essential navigation reachable on genuinely long pages. **Timeline:** one measured threshold, 160–220 ms height/transform shift; avoid scroll-driven continuous parallax. **Interrupt:** when returning upward, expanding header does not cover focused content or jump the page. **Access/test:** anchors account for the sticky offset, search/cart remain reachable, short phones retain useful content space; reduced motion changes directly.

### M05 Locale or currency switch

**Purpose/trigger:** Confirm a real preference selection. **Timeline:** menu opens 160–200 ms; chosen label updates immediately; only changed price digits may roll 180–240 ms if formatting stays correct. **Interrupt:** two rapid switches apply the newest valid locale/quote, never mix old currency with new amount. **Access/test:** announcements give final price once; test separators, tax wording, missing exchange data and long locale. Reduced motion replaces numbers directly.

### M06 Theme switch

**Purpose/trigger:** Apply an actually supported visual mode. **Timeline:** selected control changes in 100–150 ms; token-based surfaces/foreground may transition 180–240 ms. **Interrupt:** failed persistence restores previous theme and explains why. **Access/test:** open menus, charts, alerts, focus rings and reload use the same scheme; both modes retain contrast; reduced motion makes changes immediate.

### M07 Expandable `!` information box

**Purpose/trigger:** Collapse only optional explanation **in place** into a small `!` box with a short topic label; activating that box reopens the full card in the same position. Keep any essential warning visible outside the optional collapsed body. **Controls:** a visible X dismisses the current view only; a compact options menu holds distinct **Minimize**, **Remind me in a week**, and **Never show again** choices. New projects remember minimized state in the same browser until the user reopens it; a one-week reminder uses an actual expiration timestamp, and never-show is a separate explicit preference. Existing projects require owner approval before introducing persistence. **Timeline:** opening grows a bounded panel over 180–240 ms and the body resolves in the final 120–160 ms; minimizing fades the body then closes over 160–200 ms, leaving the `!` box. **Interrupt:** three rapid toggles finish in the last requested state; focus moves to the surviving `!` control before the body hides. **Access/test:** real button with `aria-expanded` and `aria-controls`, Enter/Space/touch, browser reload, one-week expiry, long text and short phone; reduced motion toggles instantly. No critical policy/price/safety message can be hidden by these preferences.

### M08 Modal or action drawer

**Purpose/trigger:** Focus an actual decision. **Timeline:** backdrop 100–160 ms; panel with 8–16 px travel in 200–300 ms, shorter exit. **Interrupt:** canceling a request must have real transaction semantics; closing an in-flight UI cannot imply its server-side action was canceled. **Access/test:** correct dialog semantics, Escape where safe, focus contained and returned, mobile full-screen/bottom sheet selected by content height, long errors scroll into view; reduced motion immediate.

### M09 Result toast

**Purpose/trigger:** Report a confirmed small action result. **Timeline:** 140–220 ms opacity with minimal movement; don't use a toast animation as proof of success. **Interrupt:** multiple notifications queue or consolidate without overwriting essential failures. **Access/test:** persistent recovery for critical failures or undo, readable timeout only for low-importance notes, a single appropriate announcement; on phone avoid keyboard/CTA obstruction; reduced motion direct.

### M10 Tabs and accordions

**Purpose/trigger:** Expose optional details and return to the same section. **Timeline:** active underline 120–180 ms; contents remain usable immediately, optional 100–160 ms opacity; bounded accordion opens 180–240 ms. **Interrupt:** fast tab changes keep latest panel and any pending fetch is labeled; closing panel never retains hidden focus. **Access/test:** native keyboard tab/arrow patterns as applicable, expanded states announced, long mobile tab strip indicates scroll; reduced motion direct.

## Discovery and cards

### M11 Category tile or visual shelf

**Purpose/trigger:** Indicate an actionable collection, without obscuring its heading. **Timeline:** hover/focus border or arrow 180–240 ms; optional first meaningful mobile appearance 250–360 ms with 50–90 ms stagger. **Interrupt:** image failure leaves HTML label and route; changing scroll direction does not replay repeatedly. **Access/test:** safe crops for text length; no automatic sound, uncontrolled video or text baked into imagery; reduced motion still tile.

### M12 Product card first appearance

**Purpose/trigger:** Gently organize a newly shown row, not delay product information. **Timeline:** 6–10 px settle plus opacity over 260–360 ms, 40–80 ms modest stagger. **Interrupt:** repeat scrolling does not replay; newly filtered or paginated items may get a new one-shot entrance only once. **Access/test:** tall card uses meaningful visible content instead of an impossible 90% whole-card intersection; text and price already readable, large lists do not animate hundreds of elements; reduced motion static.

### M13 Product card hover/focus

**Purpose/trigger:** Show clickable surface and secondary detail on pointer/focus. **Timeline:** 160–220 ms border/elevation and at most 2 px lift on enter; no full repeating loop while hovered. **Interrupt:** crossing adjacent cards restores the first without layout shifts. **Access/test:** focus retains a distinct visible ring and all actions; touch has essential price, delivery and CTA already visible; reduced motion keeps focus style without lift.

### M14 Verified badge

**Purpose/trigger:** Call attention to a sourced new/discount/verification status. **Timeline:** optional entry fade 140–200 ms; actual changed discount figure 160–220 ms; validated symbolic mark may draw once over 220–320 ms. Out-of-stock label stays still. **Interrupt:** invalidated offer disappears or changes with the real record, never leaves an old saving figure. **Access/test:** prioritize competing badges, announce meaning with text rather than shape/color, no continual glow; reduced motion direct.

### M15 Filter panel

**Purpose/trigger:** Narrow a product list without losing the user's selections. **Timeline:** desktop side panel 200–280 ms or phone sheet 240–320 ms; results count updates with actual data. **Interrupt:** closing clarifies whether choices apply immediately or on “Show results”; reopen preserves the right staged/applied state. **Access/test:** focus return, Escape, scroll and long options, zero-results recovery; reduced motion direct.

### M16 Applied chips and sorting

**Purpose/trigger:** Show which constraints control the result. **Timeline:** chips settle in 120–180 ms; small result changes can settle over 180–260 ms, large sets update directly rather than dance. **Interrupt:** old request cannot reset new sort/filter state. **Access/test:** remove-chip focus moves logically, URL/state and result count agree, phone retains selected-summary text; reduced motion direct.

### M17 Grid/list view

**Purpose/trigger:** Let a meaningful alternate density reveal the same essential product facts. **Timeline:** selected toggle 100–150 ms; modest layout change 220–300 ms only if smooth on the actual list size. **Interrupt:** focused item stays identifiable across rearrangement and filter changes. **Access/test:** name, price and availability remain in both modes; phone may have one readable mode; reduced motion jumps with context retained.

### M18 Quick view

**Purpose/trigger:** Preview a simple item without duplicating a complex product detail screen. **Timeline:** panel opens 220–300 ms and uses M08 for exit/focus. **Interrupt:** if variant, price or delivery cannot be made current together, remove the purchase control or quick view. **Access/test:** phone uses readable full-screen form, Escape/close returns focus to the initiating card; reduced motion direct.

### M19 Save/favorite action

**Purpose/trigger:** Confirm an actual save or removal. **Timeline:** icon fill 140–200 ms after the result model updates; no bouncing heart burst. **Interrupt:** failure reverts state with a reason, repeated taps resolve to one final saved state. **Access/test:** sign-in path returns to the original product, the icon button does not also open the card, state announced and reduced motion direct.
