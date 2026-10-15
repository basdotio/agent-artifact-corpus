# D4 — Informed beauty and personal care: full-site design blueprint

**Status:** Original, unimplemented proposal. This is for a seller whose shoppers choose product shades/formulae using actual catalog facts. No inferred skin diagnosis, medical claims, unsuitable shade matching scores or fabricated review content.

**Customer job (brief):** Match a shade/formula to a person and avoid unsuitable ingredients or a misleading representation. **Brand language:** considerate, clear, inclusive; reject glossy treatment that obscures shade or miniature ingredient lists. Use soft neutral UI planes, a small stable accent, legible labels; product images preserve true color under controlled, consistent lighting.

## Identity, color truth and media

Customer question: “Is this exact shade and formula right for my needs and available to buy?” Voice: inclusive, precise, low-pressure. Illustrative token pairs: canvas `#FFF8F6`, ink `#362B2B`, action `#76405B` with white label, muted ink `#554B4C`, divider `#CEBEC5`. These are **UI colors**; do not tint or color-grade product photography to fit the palette. Use legible labels, a single consistent icon family and a global CSS theme source. Every important shade choice has a name and code alongside its visual sample.

Assets: calibrated isolated bottle/packaging image per actual shade or shared master explicitly marked as representative, true-color swatch master, usage/texture detail, licensed diverse application imagery, ingredient list/diagram, step-by-step help and optional video poster/captions. Record capture lighting, source rights, editing history, mapping to variant ID, alternate text, safe crops and display profile; warn when real shade image is absent. Decorative portrait does not act as evidence of suitability.

## Customer site map

| Route | Decision-centered page arrangement | Exceptional state |
| --- | --- | --- |
| C01 Home | Shop by actual product need and short ingredient/shade help | No invented “perfect match” claim |
| C02 Category | Product family and decision needs before media grid | Long labels and no products |
| C03 Listing | Coverage/finish/formula/price/real ingredient attributes and available shade filters | Attribute missing ≠ product excludes ingredient |
| C04 Search | Product, brand, shade code and ingredient matches with qualification | No-result guides to help, not a fabricated alternative |
| C05 Detail | Brand/product, real price, accurate swatches/media, formula/ingredient details, actual size, availability and return/pickup near CTA | Missing shade photo cannot show another shade; dependent price and stock retarget correctly |
| C06 Compare | Only comparable shade/formula/finish/volume traits | No unverified suitability ranking |
| C07 Saved | Exact chosen shade, current price/stock | Discontinued color remains distinguishable |
| C08 Cart | Product + shade code/name + quantity; true totals and fulfillment | Substituted color must require real consent |
| C09 Identity | Minimal required contact, guest/account per store | No marketing opt-in presumed |
| C10 Fulfillment | Shipping/store collection as actually eligible by variant | Stock and pickup store mismatch explained |
| C11 Payment | Exact shade and final quote reviewed | Failed payment leaves selected shade intact |
| C12 Outcome | Confirmed shade/formula and delivery route | No confirmation until backend confirms |
| C13 Lookup | Exact item and shade in order history | Guest lookup follows product rules |
| C14 Tracking | Shipment/pickup status and real date | Partial shipment across brands labeled |
| C15 Digital access | Only for a real digital consultation or digital product, with explicit scope | Never invent key/download for makeup |
| C16 Returns | Actual return condition for opened/unopened item by policy | Request ≠ refund issued |
| C17 Guidance | How to interpret shade/formula/ingredient data, human help if real | No AI diagnosis or invented certainty |
| C18 Account | Orders, permitted preferences and opted-in choice history | Privacy scope and consent respected |
| C19 Support | Product/shade context and actual available channel | No fictional advisor or hours |
| C20 System/policy | Allergy uncertainty, absent ingredient data, media or policy pages | Essential warnings not dismissible |

## Operator site map

| Route | Task | Risk |
| --- | --- | --- |
| A01 Overview | Variant media/claim quality and unresolved orders before report | Sales growth without source omitted |
| A02 Orders | Exact shade, availability and fulfillment in compact/detailed views | Same product different shades not merged |
| A03 Detail | Payment, shade, fulfillment and approved actions | Return status separated from refund |
| A04 Products | Shade coverage, formula facts, true stock and missing media | Unverified “clean” claim blocked |
| A05 Editor | Shade code/name, variant image, ingredient source and preview | Edits to parent product do not mislabel shades |
| A06 Inventory | Stock by shade and store, last update | Wrong variant availability |
| A07 Promotions | Eligibility by actual shade/size and valid dates | Discount not inherited by excluded shade |
| A08 Returns | Eligibility, condition, partial refunds and case state | No automatic promise of opened-item refund |
| A09 Media | True-color assets, rights, alt, color/variant map and claim source | Missing photo must not inherit another shade |
| A10 Roles | Customer contact and case data only for permitted staff | No exposed sensitive profile |
| A11 Reports | Sourced shade demand and returns by real period/denominator | Small samples called out |
| A12 Settings | Contrast, localization and color-truth preview across store/admin | Theme effect does not alter shade pixels |

## Reuse, motion and release gate

Use K02/03 with text-labeled swatches, K07 for out-of-stock color, K13 for real sourced reviews, K15 for authored choice aid, K16/18 for variant truth, K21 for color/rights review. M03/15/16 for discovery, M20/22 for loaded shade-specific media, M27–36 for cart/payment, M40–44 for operator updates. Never animate a visual filter over the shade or delay its name until an animation ends; a static accessible swatch is often best.

**Prototype gate:** Run two nearly identical shades with distinct image/SKU/price/stock, absent media, long ingredient list and mismatched shade prevention through C03 → C05 → C08 → C11. Check real color display variability on supported devices, keyboard names, screen reader and 200%/400% zoom; owner approves claims/rights before “finished site.”

**Failure test:** missing swatch photo does not silently reuse another shade's picture or imply unavailable ingredient claims.
