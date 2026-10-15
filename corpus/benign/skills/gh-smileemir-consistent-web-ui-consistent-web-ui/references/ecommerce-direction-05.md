# D5 — Dependable digital access: full-site design blueprint

**Status:** Original, unimplemented proposal for a single seller of legitimate downloadable software or account-based access. A real merchant must supply license terms, region/platform restrictions, fulfillment mechanism, refund policy, brand, rights and secure entitlement; this skill cannot invent or implement any of these backend processes.

**Customer job (brief):** Buy the compatible access type and know how to activate it after confirmed payment. **Brand language:** straightforward, secure, dependable; reject physical-delivery metaphors and invented security seals. Use a dark or light mode only when all surfaces pass contrast checks; medium information density, precise sans type and readable code/data styling, restrained brand accent.

## Identity, assets and visible trust

Customer question: “Will this work for me, and where is my access after the payment clears?” Voice: plain, competent, exact. Illustrative **dark** token pairs: canvas `#0F1722`, ink `#EDF4F7`, action `#A3E1D1` with on-action `#102026`, muted ink `#A8B7C4`, divider `#526072`. Use a clean sans with clear tabular prices and distinguishable focus ring; verify exact contrast for every state, including overlays and inputs. If a real brand supports light mode, its separate semantic palette is reviewed across all pages; don't invert photos or license art. One global CSS theme file owns color, spacing, type and motion roles.

Assets: original product/feature diagram, licensed program/platform mark if permitted, compatibility icons with labels, download/file-type illustration, platform screenshot with permission, setup steps and a mask/reveal/copy symbol. Maintain provenance, correct alt, crop and light/dark variants. No unofficial payment-security badge, fake partner logo, truck or box graphic for downloads, or “instant” claim unless delivery really is instant.

## Customer site map

| Route | Decision-centered page composition | State or prohibition |
| --- | --- | --- |
| C01 Home | Plain product family and verified delivery path, compatibility aid and support | No fabricated authenticity certificate |
| C02 Category | Use case/platform/licensing class before items | Region unavailable explained |
| C03 Listing | Platform, region, access term and license type filters only when sourced | Don't force physical-stock filters |
| C04 Search | Product, compatible platform and setup help separated | Similar license names distinct |
| C05 Detail | Exact edition, license/term, required account, compatibility and region, real price, actual delivery method then CTA | Region mismatch, unsupported OS, missing entitlement quote |
| C06 Compare | Like licenses by term, platform, included rights, activation and support | Unknown condition never treated as included |
| C07 Saved | Current license/term, price and availability | Expired offer clearly refreshed |
| C08 Cart | Each access/term/quantity where allowed, taxes and real totals | No shipping-address requirement without actual need |
| C09 Identity | Actual contact/account needed to deliver, guest path only if offered | Guest order later requires an honest lookup |
| C10 Access method | Download, key or linked account as **separate conditional** UI; show time and region constraints | Mixed digital/physical only if checkout supports it |
| C11 Payment | Confirm selected license, tax and processing state | Never show a key on payment initiation |
| C12 Outcome | Order status with entitlement pending versus ready | Ambiguous charge cannot claim delivered |
| C13 Lookup | Order history and access eligibility after identity check | Repeated checkout does not duplicate entitlement |
| C14 Tracking | Not physical tracking; show activation/fulfillment states if real | No fabricated parcel milestone |
| C15 Access | Masked authorized key or download/account link, setup path, copy/expiry rules | Pending, revoked, failed download, lost login and blocked region distinct |
| C16 Returns | True digital cancellation/refund conditions with clear request state | “Refund requested” never “refunded” |
| C17 Setup help | Device checks, installation steps and existing support route | No invented installation success |
| C18 Account | Only actually supported purchases, devices and settings | No secret in account listing preview |
| C19 Support | Purchase and platform context, real contact/hours | Manual activation delay visible |
| C20 System/policy | Incompatible region, entitlement failure, legal license/terms from owner | Critical restrictions cannot collapse away |

## Operator site map

| Route | Task | Failure case |
| --- | --- | --- |
| A01 Overview | Fulfillment failures, pending entitlements and valid sales totals | No arbitrary 0→sales counter |
| A02 Orders | Payment versus entitlement status in stable compact/detailed rows | Same amount does not mean same entitlement |
| A03 Detail | Identity under role scope, processor status and delivery audit | No plaintext secret in general notes |
| A04 Products | Region/platform/license term filters, publication completeness | Invalid compatibility claim blocks publish |
| A05 Editor | License terms and sanctioned media/compatibility facts | Never generate a key in frontend editor |
| A06 Fulfillment | Pending/failed access queue, retry pathway only if current API supports it | Charge confirmed but access delayed |
| A07 Promotions | Currency/term scope, effective date and true price preview | Expired offer not reused |
| A08 Returns | Entitlement/cancellation/refund requests with allowed action | Revoked access is not proof money returned |
| A09 Media | Program marks, version images, docs, rights and alt | Trademark usage unresolved |
| A10 Roles | Minimize secret display by existing permissions and audit rules | Copy/preview button role-restricted |
| A11 Reports | Source/time/currency plus sales/refund and entitlement-lag definitions | Partial payments/failed delivery tracked separately |
| A12 Settings | Theme and localization previews of masks, errors and access states | No design control can change license rights |

## Components, motion and gate

K04 for precise product facts, K09 only for truly compatible bundles, K16/17 for order and entitlement, K18 for cart, K20 for failed delivery tasks and K22 for optional supporting explanation. M20/23 only when real license/term changes price; M27–36 preserve purchase truth; M38/39 mask, reveal or copy only after authorization; M40–44 show distinct return and operator state. An individual changing currency digit can turn once on a successful quote, but the formatted result remains readable immediately and keyboard/screen reader receives only the final value. No false physical shipping stories or pulsing fake trust seal.

**Prototype gate:** Choose two editions with different compatible regions; change term and locale rapidly; confirm final quote, payment pending/failed/confirmed and a **simulated** entitlement only in a clearly marked demo. A real end-to-end access test needs an authorized sandbox or owned production environment. Review C05/C08–C13/C15 and A02/A06/A10 at small/large phone, tablet, keyboard and high zoom. Obtain the owner's real brand/terms and actual integration approval before counting this as a finished site.

**Failure test:** pending payment and a refreshed page can never show a usable secret before entitlement exists.
