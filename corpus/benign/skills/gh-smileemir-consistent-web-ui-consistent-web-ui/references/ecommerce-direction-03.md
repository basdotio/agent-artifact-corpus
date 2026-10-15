# D3 — Movement and fit apparel: full-site design blueprint

**Status:** Original proposal, unimplemented. Actual sizes, fit guidance, returns, imagery rights and owner-approved brand must come from a real store. This concept prioritizes clothing and footwear with live size availability; no invented athletic results or endorsements.

**Customer job (brief):** Select the right style and available size, then understand fit, exchange and fulfillment. **Brand language:** energetic but controlled, human, useful; reject ceaseless floating cards and size selection indicated only by color. Keep photography lively but UI backgrounds and controls quiet, one action accent, high-contrast body type, short copy.

## Identity and visual material

Customer question: “Which size/fit should I buy and can I exchange it?” Voice: concise, active and honest. Illustrative pairs: canvas `#FAF9F5`, ink `#1F2723`, action `#8A332B` with white label, muted ink `#45554B`, divider `#B6C2B8`. Photography supplies energy; UI chrome stays quiet. Use one strong sans heading/body family or a checked licensed pairing, readable captions and named choices instead of color-only swatches. One global CSS theme file governs all surface and button states including checkout and operator screens.

Asset register per garment: on-body image with consent/rights, isolated front/back, accurate size/color alternative, fabric/detail, fit/size chart with textual measurements, optional motion/video poster and alt. A person photo cannot stand in for another color/size; keep lighting and crop family consistent without making bodies or tones indistinguishable. A standard icon family covers size help, availability, favorite, cart, delivery and return; a decoration is never a clinical or performance guarantee.

## Customer site map

| Route | User decision and page composition | Exceptional state |
| --- | --- | --- |
| C01 Home | Shop by activity/garment need → a few factual collections → fit help | Unverified “most popular” absent |
| C02 Category | Garment class and purpose then product shelf | No relevant items/long category names |
| C03 Listing | Size, fit, color, activity, stock and price filters; sort/view only when helpful | Mixed available sizes not mislabeled fully in stock |
| C04 Search | Garment name plus fit/category matches and no-result correction | Old query never overwrites new |
| C05 Detail | Correct on-body media, color, named size, fit/size guide, stock, price, delivery and exchange near CTA | No selected size blocks or explains add; photo/variant cannot diverge |
| C06 Compare | Only comparable garments; fit/care/material/sizing and value | Unknown fit not fabricated |
| C07 Saved | Current desired size, color, stock and price | Discontinued size gets clear alternative |
| C08 Cart | Explicit size/color/quantity, cost and fulfillment estimate | Last available size sold between add and checkout |
| C09 Identity | Guest/account route, keep size choices | Login interruption preserves cart |
| C10 Fulfillment | Accurate delivery or pickup per size/store | Unavailable location must not show ready today |
| C11 Payment | Valid chosen size and final quote before committing | Size stock changes trigger review, not silent swap |
| C12 Outcome | Actual ordered size/color and tracking next step | Pending payment is separate from placed order |
| C13 Lookup | Guest/registered order and exact size | Same SKU in two sizes clearly distinguished |
| C14 Tracking | Shipment, pickup or split package, with dated status | Delay doesn't falsely mark delivered |
| C15 Digital access | Not part of a physical apparel sale unless a real digital benefit exists | No automatic downloadable license UI |
| C16 Returns | Eligible item, size exchange path and actual policy | Initiated exchange differs from completed replacement |
| C17 Fit help | How to measure, fit notes and actual size data near product | Unsupported measurements have explicit uncertainty |
| C18 Account | Addresses, saved sizes if legitimately supported, orders | No cross-user preference leak |
| C19 Support | Order-aware sizing/exchange help via real channel | No fake live availability |
| C20 System/policy | Sold-out size, missing guide, recalled item, terms | Restriction remains visible when optional notice closes |

## Operator site map

| Route | Task | Failure case |
| --- | --- | --- |
| A01 Overview | Size-related stock exceptions and delayed exchanges before sales | No-data stated, not zero |
| A02 Orders | Filter by SKU/size, status, permitted fulfillment and exchange action | Two sizes of same style not merged |
| A03 Detail | Variant plus exchange/payment/shipment histories | Refund pending not refunded |
| A04 Product queue | Missing size/photo/fit metadata, stale variant stock | Unavailable size disabled on customer page |
| A05 Editor | Size-color SKU matrix, exact media mapping and guide | Changing color does not keep another shade image |
| A06 Inventory | Size per location and last sync | Inventory uncertainty not used as fake urgency |
| A07 Promotions | Actual size/color and dates of eligible offer | Markdown old price removed after expiration |
| A08 Returns | Size exchange, return reason, receipt and next allowed action | Partial exchange remains partial |
| A09 Media | On-body consent/rights, alt, fit images and uses | Unlicensed model photo withheld |
| A10 Roles | Masked customer address and allowed exchange actions | Operator cannot exceed role |
| A11 Reports | Return-rate definition, size outliers and sourced period | Small/partial sample labeled |
| A12 Settings | Theme, localization and size-unit display preview across pages | Conversion must not change underlying SKU |

## Card and motion allocation

K02/03/07/11 show only the relevant variant facts; K15 holds authored fit guidance, K16/18 reflect the confirmed chosen size, K20 surfaces true inventory exceptions. Use M15–17 for filters and modes, M20/M22 for selected size/color and correct imagery, M23 only when a real price or currency changes, M27–36 for cart/payment, M37/40 for fulfillment/exchange. M12/13 may give a subtle one-shot card reaction; moving editorial imagery must not compete with size choices. Test keyboard/screen reader size names and reduced motion.

**Prototype gate:** Choose fit → size → color, change back quickly, add and review the *same SKU* through checkout and exchange. Verify sold-out alternate and image failure on phone/tablet/desktop; owner approves copy, imagery and policy before this direction counts as a site.

**Failure test:** quickly changing three sizes cannot leave image, price and CTA representing three different variants.
