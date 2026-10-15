# D1 — Considered living goods: full-site design blueprint

**Status:** Original, unimplemented design proposal for a furniture and home-goods store; brand name, real products, media rights and owner approval are still project inputs. Use the common C/A definitions, K card roles and M motion contracts. Never import this palette or photography direction into an existing brand without approval.

**Customer job (brief):** Choose a physical object that fits a real room, budget and delivery area. **Brand language:** calm, tangible, thoughtful; reject noisy discounts and inaccessible tiny editorial type. Use warm neutral canvas, one grounded accent for actions, product-material colors left untouched; editorial heading with readable, restrained body type. Pages have generous section spacing but product comparisons and dimensions remain close to the decision.

## Brand and visual contract

Customer question: “Will this fit my room, and how/when can I get it?” Voice: calm, specific, helpful; avoid grandiose interiors copy and sale pressure. Illustrative **light-theme pairings to verify in the actual product:** canvas `#F6F4EE`, primary ink `#1D2922`, action `#23533B` with white label, muted ink `#45534A`, divider `#B7C5B7`. Headings may use a licensed humanist serif; body, labels and figures use one highly legible sans. Do not use the serif for measurements or checkout data. Example spacing roles: control 8/12, card 16/24, section 48/64 CSS px adjusted to content, not multiplied in a short phone. One global CSS theme file owns colors, type roles, spacing and motion tokens.

Imagery grammar: truthful scale and natural materials under consistent diffuse light; show objects in an actual space, isolated product, detail and measurement drawing as **different assets**. Product photographs do not carry text. Wordmark, square icon, favicon, navigation/status icon family, document icons, full image alt/rights registry and fallback are separately authored. Never manufacture a certification, delivery promise or customer review.

## Customer site map and default page composition

| Route | Distinct page and decision element | Required evidence/state |
| --- | --- | --- |
| C01 Home | Promise and shop-by-room/use first; three truthful product shelves with different jobs, material-help and delivery explainer | Empty collection collapses; no invented sale badge |
| C02 Category | Room/task routes then collection name, buying dimensions, product entry | Missing room image preserves route and title |
| C03 Listing | Dimensions/material/availability filters, price, sort, grid/list; show measurements on dense K03 | Filter location and result count stay accurate |
| C04 Search | Product, material and room matches with typo/no-result recovery | Stale query cannot overwrite newer search |
| C05 Detail | Media sequence: room → product → texture → dimensions; exact size/finish, price, local pickup/delivery, assembly and returns near CTA | Unknown location and oversized item do not inherit another item's promise |
| C06 Compare | Dimensions, material, load/fit, care and fulfillment for like products | Missing measurement is “not provided,” never zero |
| C07 Saved | Current finish, price and local availability for each saved SKU | Older price is visibly refreshed |
| C08 Cart | Chosen finish/dimensions, per-item quantity, assembly only if real, pickup versus delivery and estimate | Split/oversized items remain explicit |
| C09 Identity | Guest/account plus necessary email; keep cart and selected items | No forced account if guest is truly allowed |
| C10 Fulfillment | Real postcode/store and eligible pickup/home delivery; costs/slots after location | Pending quote not shown as final total |
| C11 Payment | Item, delivery, estimated/final tax, fee and authorized method | Payment pending/failure never shows paid |
| C12 Outcome | Confirmed items, location, delivery window and next step | Split order gets separate substatus |
| C13 Order lookup | Guest or account status according to actual policy | Wrong order/expired lookup has recovery |
| C14 Tracking | Furniture delivery and pickup stages with source timestamps | Delayed or rescheduled item named |
| C15 Digital access | Not applicable unless the real shop sells digital plans or downloadable assembly files; documents are linked from C05/C17 | Never invent license/key screen for a physical catalog |
| C16 Returns | Product and condition, actual timeframe, bulky-item handling and request versus refund | Refund pending differs from request accepted |
| C17 Guides | Scale diagrams, assembly/care and space-planning help | Alternate text/table carries essential sizes |
| C18 Account | Addresses, receipts and communication preferences | Guest order mapping follows actual rules |
| C19 Support | Order/item context, assembly or delivery help, real channel/hours | Offline channel is not “live” |
| C20 System/policy | Missing item, out-of-delivery-area, recalls and returns terms | Critical restrictions always visible |

## Operator site map

| Route | Priority and arrangement | Exceptional case |
| --- | --- | --- |
| A01 Overview | Fulfillment exceptions → inventory age → few sourced metrics | No generic chart wall |
| A02 Order queue | Delivery method, bulky item flag, next action in consistent table | Location changed after quote |
| A03 Order detail | Split packages and eligible action separated from customer note | One delayed part doesn't mark whole order delivered |
| A04 Product queue | Missing measurements, finish media and stock state | Unpublished item excluded from shelf |
| A05 Editor | Size/material/finish linked to actual variant media and care files | Wrong finish photo flagged before preview |
| A06 Inventory | Store versus ship stock and last-sync date | Unknown stock never presented as scarce |
| A07 Promotions | Real category/finish eligibility and start/end | Expired label removed from customer pages |
| A08 Returns | Bulky pickup/resolution queue with order context | Requested refund distinct from issued payment |
| A09 Media | Room shot, scale drawing, material close-up, rights and alt records | Missing drawing called out without cloning another product |
| A10 Roles | Supplier/service visibility only under actual permissions | No fabricated supplier controls |
| A11 Reports | Delivery method, damaged return and sales with dates/units | Partial feed named, no zero placeholders |
| A12 Theme/settings | Light theme and any *actually supported* mode preview across product, cart, checkout, operator | No hardcoded modal palette |

## Reused assets, components and motion

Asset identities per SKU: `cover`, `in-room`, `side-angle`, `texture`, `dimension-drawing`, optional `assembly-poster`, appropriate alt/rights and crop. A category image is shared only when it truly names the same room/use; never reuse a product image to depict a different finish. Use K01/02/03/04/05/07/08/10/14/16/18/20/21 when data fits. An illustrated trust tile is optional; a plain verified shipping/returns text row is often clearer.

Selected motion: M01/03/15/16 for navigation and filtering; M12/13 at low intensity; M20/22 **only for true finish imagery**; M23 for actual quote change; M27–M36 for real cart/payment result; M37 for shipment state; M41–M44 for operator changes. M45 only if there is a specific verified delivery promise. No perpetual room-photo parallax, bouncing furniture card, fake “fast shipping” timer or animated measurement that impairs reading. Apply each M record's trigger, interruption, keyboard/touch and reduced-motion behavior.

**Prototype gate:** Using licensed media and real or prominently labeled demo data, review C03 → C05 → C08 → C09–C12 → C14 plus A04/A06 on small/large phones, tablet, desktop, high zoom and keyboard. Record the exact final price and delivery after postcode and variant changes. Owner sign-off is needed before calling this a finished direction or shipping it for a particular store.

**Failure test:** a large object not available at a postcode never retains a buyable delivery claim.
