# D2 — Clear technical equipment: full-site design blueprint

**Status:** Original proposal, unimplemented. Model data, valid compatibility claims, service terms, brand name and media rights require a real owner's review. The design is for devices and accessories sold by one store; a third-party seller system would need a separate marketplace specification.

**Customer job (brief):** Narrow a broad catalog using comparable specifications and pickup/support constraints. **Brand language:** exact, assured, organized; reject endless specification walls and fake futuristic glow. Use a neutral cool surface, a single highly legible action color, sturdy sans typography with tabular figures for metrics, compact but breathable rows.

## Identity, assets and data

Customer question: “Which configuration is compatible and available, at what total cost?” Voice: exact, reassuring, short. Illustrative token pairs: canvas `#F4F7F8`, ink `#192B36`, action `#154E67` with white label, muted ink `#41545F`, divider `#A6B9C0`. Use a restrained sans family, tabular figures, crisp plain line icons and low-elevation sections. Compact rows may show more facts than living-goods cards, but line lengths and tap targets stay readable. A single global theme file owns these values; a dark mode requires its own checked token pairs, never an automatic color inversion.

Asset family per SKU: clear isolated front/side, port/connection view, real dimension drawing, accessories/compatibility diagram, setup sheet or poster when applicable. Shared icon family covers compare, pickup, warranty, service, download and statuses. Keep provider/trademark marks only with rights. Record master, formats, safe crop, variant mapping, alt/decorative role, license and fallback; an absent port photograph remains absent, not replaced by a similar model.

## Customer site map

| Route | Page priority | State or contradiction to catch |
| --- | --- | --- |
| C01 Home | Shop by job/device family; relevant comparison guide; a few complete collections | Promotional metrics only if sourced |
| C02 Category | Device class and intended use before product shelf | Category with 0 compatible devices |
| C03 Listing | Model/specification/pickup filters, sort, grid/list, compact/detailed rows and relevant columns | One chosen filter must not change unrelated units |
| C04 Search | Model number, category and support result sections | Partial model IDs, unavailable SKUs |
| C05 Detail | Model and core specs → compatibility → configuration → real price, pickup/shipping and optional coverage → CTA | Configuration change updates delivery and quote, no fake checked coverage |
| C06 Compare | Side-by-side compatibility, interface, core specs, service and total; stable labels | Missing spec is explicit, cannot rank as zero |
| C07 Saved | Current configured model/price/availability | Saved outdated spec is flagged |
| C08 Cart | Exact SKU, accessories versus optional plan separated; quote, pickup/shipping and quantity | Unrequested service never auto-added |
| C09 Identity | Guest/account choice and necessary contact | Cart survives sign-in exit |
| C10 Fulfillment | Actual store and shipping eligibility per SKU | Split pickup/shipping groups only if supported |
| C11 Payment | Price, tax, service fee and plan term clearly itemized | Plan not purchased unless actually selected |
| C12 Outcome | Confirmed SKU, pickup instructions or delivery, plan status if bought | No order number on ambiguous payment |
| C13 Lookup | Status, selected device and service linked to same order | Guest path follows existing policy |
| C14 Tracking | Shipping or ready-for-pickup only when reported | Device and accessory can ship separately |
| C15 Digital access | Only when actual device software/download entitlement exists | Serial/software keys stay masked |
| C16 Returns | Device/plan eligibility and separate cancellation | Refund requested is not refund paid |
| C17 Guide | Choose by compatibility and required ports without invented scores | Unknown compatibility needs help, not a green check |
| C18 Account | Saved devices, receipts, warranties actually purchased | No permissions beyond account scope |
| C19 Support | Actual model, manual and accessible assistance route | Support hours/status true |
| C20 System/policy | No-spec, stale quote, recall, failed comparison, privacy/return pages | No misleading “secure certified” art |

## Operator site map

| Route | Task layout | Failure to resolve |
| --- | --- | --- |
| A01 Overview | Exceptions and pickup readiness before compact sales metric | Stale source named |
| A02 Orders | Shared toolbar, identity, status, chosen service and next permitted action | Bulk selection with mixed permissions |
| A03 Detail | SKU/configuration, payment, plan, pickup timeline in separate sections | Canceling device cannot silently retain invalid coverage |
| A04 Products | Missing spec, wrong comparison group, stock and unpublished SKU filters | Unknown data not forced into comparison |
| A05 Editor | Model identity, compatible accessories and config combinations before preview | Wrong port image or unsupported combo |
| A06 Inventory | Store and ship stock freshness by SKU | Online/physical inventory conflict |
| A07 Promotions | Valid configured variants and genuinely optional plans | Outdated discount at checkout |
| A08 Returns | Device status and service-plan issue separate | Request mistaken for issued refund |
| A09 Media | Ports, dimension chart, manual, rights and alt text | Similar device image substitution blocked |
| A10 Roles | Customer/service agent controls under existing policy | Secret/PII not leaked in compact view |
| A11 Reports | Units/time/source and accessible data behind trend | Mixed-currency comparisons labeled |
| A12 Settings | Token preview for dense tables, chart, dialogs and purchase screens | Contrast lost in secondary mode |

## Components, motion and completion check

Use K02–04 for product density, K09 for a **real** bundle, K10 compare, K16/18 cart, K19–21 operator. A repeated list toolbar has predictable filter/sort/view/columns controls where useful; product grid need not expose meaningless raw database columns. Selected motion: M03/15–17 for selection changes, M20–23 for actual configuration and quote, M27–36 for cart/payment, M41–44 for operator queues and report updates. A spec panel may use M10; a tooltip must not contain decisive compatibility alone. No mechanical loading animation masquerades as verified compatibility.

**Prototype gate:** Compare two variants with one missing spec; configure, decline an optional plan, change pickup store, review a fresh quote, then exercise payment pending/error and support recovery using actual project behavior. Test C03/C05/C06/C08–C12 and A02/A04/A06 at small/large phone and 200%/400% zoom. Review the complete direction with the owner before treating it as a working site.

**Failure test:** missing specification says unknown instead of winning or losing a comparison by blank cell.
