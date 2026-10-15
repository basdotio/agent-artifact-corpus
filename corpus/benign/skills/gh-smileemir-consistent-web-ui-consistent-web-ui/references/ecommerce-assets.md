# Ecommerce asset register and production recipes

The product owner supplies the actual brand, catalog and rights. This file specifies **which families to inventory and how to reuse them**; it includes no third-party art. Use one canonical ID per reused asset, and choose distinct pictures where the object, variant, platform or context truly differs. See [design-contract.md](design-contract.md) for the complete record schema.

## Shared site identity and UI assets

| Asset family | Variants/placements to plan | Accessibility, failure and reuse rule |
| --- | --- | --- |
| Wordmark and symbol | Header, checkout, admin, small fallback; light/dark on actual supported surfaces | Text brand name fallback; don't shrink to an unreadable symbol |
| Favicon and browser/app icon | Browser tab, bookmarks and optional install contexts | Clear silhouette at very small sizes; use only if actually supported |
| Social preview | Owned page preview with safe text crop | Do not embed essential page description only in image |
| Unified UI icon set | Menu, chevron, search/clear, account, bag, filter, sort, views, columns, compare, favorite, share, help, close, show/hide | One optical grid, stroke/caps, state size and meaning; descriptive names and text for critical actions |
| Fulfillment/status marks | Delivery/pickup, digital access, processing, success, failure, stale, partial, info, warning | Never infer a verified badge from a decorative shield or truck |
| Provider/legal marks | Payment, real partner, regulatory mark only with actual permission | Correct official artwork, no recoloring outside usage rules; text alternative |
| Focus/selection treatments | Controls, cards, swatches, table row, media thumbnail, drag handle if real | A visible focus indication distinct from hover and selection; non-color cue |
| Empty/recovery visuals | Search miss, empty cart, saved list, denied access, interrupted network, failed payment, missing entitlement | Specific title, reason and next action remain as HTML without illustration |
| Progress and skeleton masks | Image, list, product price/availability, checkout quote and admin data | Reserve final geometry; no perpetual shimmer or fictional percent |
| Reusable notice frame | Optional informational card, its in-place `!` minimized control and critical non-dismissible alert | X, menu choices and persistence have distinct meanings; never store sensitive content in browser preference |

## Merchandise and content assets

| Asset family | Applicable task | Integrity check |
| --- | --- | --- |
| Category discovery still | Choose meaningful category/use | Safe cropping on phone, tablet, desktop; HTML heading independently available |
| Campaign/editorial master | A **real** campaign or authored feature | Correct dates and rights; remove when claim expires; no fake timer |
| Product primary media | Identify actual variant clearly | One approved master per genuinely distinct visual SKU, responsive derivatives, honest missing-media state |
| Alternate/zoom image | Examine sides, packaging and texture | Pixel quality at zoom; consistent ordering and accessible exit |
| In-use/context image | Assess real scale, fit or use | Permission/model release and no misleading proportions |
| Scale/fit/size drawing | Furniture dimensions or apparel measurements | Accessible textual equivalent with units; not flattened into a bitmap only |
| Technical/compatibility diagram | Compare device ports, platform and included components | True model labels, no invented checkmarks; table equivalent |
| Shade/finish swatch | Select exact cosmetic shade, garment color or material | Named value, variant ID, actual color fidelity and a no-photo fallback |
| Product video and poster | Explain a step or angle that stills cannot | Play/stop/captions, no forced autoplay narration, meaningful poster and reduced-motion treatment |
| Bundle/complement media | Explain exact components | Never imply a bundle discount without a real bundled product/price |
| Verified review media | Actual permissioned customer evidence | Attribution, moderation and rights; no invented testimonial |
| Help/setup illustrations | Fit, assembly, install, activation or return path | Steps also in selectable text; each depicts the correct product/version |
| Download/file icon | Entitled digital content | Format and platform label; actual file identity/rights; no unlock until entitlement confirmed |

## Order and operator assets

| Asset family | Surface | Integrity check |
| --- | --- | --- |
| Cart/order thumbnail | Cart, checkout, receipt and operator order | Same variant media/ID across route; generic fallback named honestly |
| Order state glyph | Pending, confirmed, partial, delayed, returned | Same state label and icon across customer/operator screens; timestamp source visible |
| Receipt/document preview | Account and authorized operator | Sensitive values masked by existing roles; accessible document title |
| SKU/variant thumbnail | Product queue, editor, stock and returns | Status and caption remain legible at compact density |
| Media rights/alt indicator | Content manager | Record license, creator, derivative rights, affected pages and missing fields |
| Chart palette, marker and table | Admin reports with actual units and periods | Distinguishable without color; accessible data table agrees with plot and source |
| File/export indicator | Existing export/document workflow | No download or success indicator until actual result exists |

## Asset handoff per product/page

1. Record `asset ID → canonical master → owner/right → approved placement(s) → subject/variant → derivative sizes/formats → safe crop → light/dark/locale handling → alt or decorative decision → fallback → last review`. Record whether the image is current; a shared file can serve several pages, but changing it must list affected routes.
2. Produce responsive derivatives sized for actual rendered slots; reserve width/height or aspect ratio and provide correct `srcset`/`sizes` where the framework supports it. Keep text and purchase controls in semantic HTML; do not burn price or CTA into a bitmap.
3. Approve image and icon sets with the brand owner on existing sites before replacing them. For new sites, choose one coherent icon grammar and a short photography guide before page production. Avoid importing an unrelated vendor pack merely because it is popular.
4. Review one representative record for every family in a small phone, wide phone, tablet, desktop, high zoom and supported themes, then spot-check each variant mapping. If the rights or exact variant are unknown, show a truthful fallback and keep the issue open rather than inventing media.
