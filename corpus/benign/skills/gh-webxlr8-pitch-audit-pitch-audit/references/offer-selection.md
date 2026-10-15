# Offer selection: from findings to ONE recommendation

Every recommendation answers a gap the prospect can see on their own screen. Never pitch an offer with no finding behind it.

Inputs: `scores.json` (findings carry `service` = capability and `offer` = your mapped offer id; `fit.primary` = best-fit offer), and your profile:
`pitch-profile/catalog.yaml` (offers), `mapping.yaml` (capabilities → offers, `fit_rules`, `guidance`), `proof.yaml`.

## 1. Pick the lead offer (exactly one)
Read `mapping.yaml → guidance` first. It holds your company's own rules. Without guidance, use this order:

| Situation | Lead with |
|---|---|
| Prospect matches a **product** in `fit_rules` (industry keywords) and shows matching ops signals | That product |
| Operations-heavy business (`ops_icp`) running on phone / WhatsApp / spreadsheets / PDFs | The offer mapped to `ops` |
| Overall < 60 and web categories (performance, SEO, mobile, trust) are weak | The offer mapped to `web` (rebuild beats piecemeal fixes) |
| Website is fine but invisible (SEO, AI search, social, analytics) | The offer mapped to `growth` |
| Website is fine, but hosting/security is weak | The offer mapped to `infra` |

Consumer businesses with critical conversion gaps (no online ordering or booking): lead with the `web` offer even if a product fits. Put the product in the `next` line.

## 2. Build the offer slide from the catalog
- `product` = offer `name` (a catalog product shows its logo badge).
- `facts`: 3 big numbers from the offer (price only if `price` is set, timeline, module count…). Never invent.
- `includes` / `modules` from the offer's `includes`. `chips` from `guarantees` (only if listed).
- `next`: one line naming 2–3 other mapped offers (from findings' `offer` values), e.g. "Later: website rebuild · search visibility".
- First step (contact slide): the offer's `first_step`, else "30-minute call". Booking link: the offer's `booking_url`, else `company.contact.booking_url`.

## 3. Prices and promises
- Print a price only if the offer has `price` in `catalog.yaml`. Otherwise "scoped after a 30-minute call".
- Guarantees, SLAs and timelines only as written in the catalog.
- Proof (stats, clients, results) only from `proof.yaml`. A case-study `result` is shown only if it is filled (approved).

## 4. Fit score (lead ranking)
`score.py` uses the first matching `fit_rules` entry (its `score`), else `default_fit`. Override per prospect with `manual.json → fit: {score, primary, reason}` (e.g. ±20 for size: multiple branches/exports up, one-person shop down).
