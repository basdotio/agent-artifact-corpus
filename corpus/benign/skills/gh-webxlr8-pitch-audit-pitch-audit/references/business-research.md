# Business research: understand the client before judging the site

Output: `clients/<slug>/research.md`. Keep it factual, with source URLs. ~1 page.

## Sources (in order)
1. `page_text.txt` + `audit.json → nav_links` (homepage text and menu, from audit.py).
2. WebFetch 2–4 key pages from `nav_links`: About, Services/Products, Contact, Pricing/Catalogue.
3. WebSearch `"<business name>" <city>` → Google Business Profile (rating, reviews count), directories (IndiaMART, JustDial, Zomato, etc.), news.
4. WebSearch for social profiles if the site doesn't link them. Read public profile pages with WebFetch when reachable. Record follower count and latest-post date **only if visible**.
5. GEO check: 2–3 WebSearch queries a buyer would type (`<category> in <city>`, `best <product> supplier <region>`, `<service> near <area>`). Note who appears instead (competitors).

## research.md sections
```
# <Business name>
URL · City/Region · Industry · Founded (if known)

## What they do
2–4 sentences in plain words. Products/services, who buys, how they sell (walk-in, online, B2B, dealers).

## Offerings
Bullet list of main product/service lines.

## Customers & channels
Who buys (B2C/B2B/both), where (local/national/export), how orders happen today (phone, WhatsApp, cart, forms).

## Size & maturity signals
Branches, staff, years, export markets, clients named, hiring, tech stack (from audit.json cms), funding/news.

## Online presence
Google rating + reviews, social profiles (followers, last post, when verified), directories, competitors seen in search.

## Ops signals
Anything suggesting manual operations (WhatsApp ordering, Google Forms, PDF price lists, "call for availability", no portal, Excel mentions in job posts).

## Likely pains (hypotheses)
3–5 bullets linking signals to pain, e.g. "Bookings over phone → double-booking risk, no availability view".

## Sources
- URLs used
```

## Industry classification
Set `manual.json → industry` to a short lowercase label (e.g. "bulk fuel tanker trucking").
- If the prospect clearly fits one of your products, set `product_match: <offer-id>` (offer ids from `pitch-profile/catalog.yaml`). Otherwise `score.py` matches the industry against `fit_rules` in `pitch-profile/mapping.yaml`.
- Set `ops_icp: true` for operations-heavy businesses (manufacturing, logistics, distribution, wholesale, field service) that show manual ops signals.

## Ethics
- Public information only. No logins, no scraping behind walls, no personal data about individuals beyond named business contacts on the client's own site.
- Never state guesses as facts in the deck. Hypotheses stay in research.md and sales notes.
