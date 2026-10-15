# Audit rubric: how we judge a client's online presence

**Status: v1.0 defaults. Tune the weights for your market.** Numbers live in `rubric.json`; `scripts/score.py` applies them. Run `python3 scripts/score.py --explain` to print the current table.

## How scoring works
1. `audit.py` collects facts automatically (Lighthouse, HTML, headers, links, screenshots, tracking, social links, ops signals).
2. Claude adds facts a script can't get into `manual.json` (social activity, Google rating, AI-search presence, business-model expectations).
3. Each of 8 categories starts at 100. Each failed check deducts points. Floor 0.
4. Overall = weighted average. Grades: **80+ healthy**, **60–79 needs work**, **below 60 critical**.
5. Each deduction becomes a **finding**: severity, evidence (from data), business impact, service hint.
   Severity = points lost from the overall score: ≥3 critical, ≥1.8 high, ≥0.8 medium, else low.
6. **Lead score** = 0.6 × (100 − overall) + 0.4 × fit. High lead score = big gap + strong fit with what we sell.

## Categories (weight)

| Category | Wt | What it means for the client | Main checks |
|---|---|---|---|
| Performance | 20 | Do visitors wait? | Lighthouse perf (70% mobile, 30% desktop), LCP, CLS, TBT, server response (TTFB), page weight |
| SEO Foundations | 15 | Can Google find and describe them? | title, meta description, H1, canonical, sitemap, robots, noindex, schema, alt text, lang, Lighthouse SEO |
| Mobile & UX | 15 | Does it work on a phone? | viewport, sideways overflow, Lighthouse accessibility, mobile LCP, JS errors, broken links |
| Trust & Security | 10 | Would a stranger trust it? | HTTPS + redirect, SSL expiry, security headers, mixed content, privacy page, testimonials, visible contact, best-practices |
| Conversion | 15 | Can a ready buyer act? | above-fold CTA, tap-to-call, WhatsApp/chat, form/booking/cart, analytics, ad pixel, online ordering when the business needs it |
| Social Visibility | 10 | Are they alive and visible? | profiles linked, OG share tags, posting recency, audience size vs peers |
| AI Search (GEO) | 5 | Do ChatGPT / Gemini / AI Overviews recommend them? | llms.txt, schema, FAQ, presence in answers for category queries, Google Business Profile |
| Ops Maturity | 10 | Is the back office holding growth back? | WhatsApp ordering, Google Forms, PDF catalogue, call-to-order, missing customer portal, legacy stack, manual signals |

## Rules for Claude when filling `manual.json`
- Only record what you verified. If you can't see follower counts or post dates, leave them out: the deck will say "not verified" rather than guess.
- `geo.queries`: run 2–3 searches a buyer would type ("<category> in <city>", "best <product> supplier <region>"). Mark `appears: true` only if the client's own site or listing is in the results.
- `expect_online_transaction`: true when the business sells products or bookings a customer could reasonably buy online (retail, rental, restaurant ordering, B2B reorders).
- `expect_customer_portal`: true for B2B, dealers, repeat orders, rentals with deposits.
- `ops_signals`: plain-English observations, e.g. "Instagram bio says 'DM for bulk orders'".
- `extra_findings`: anything important the rubric doesn't cover (dated design, wrong info, dead blog). Give a `deduct` value comparable to similar checks.

## manual.json template
```json
{
  "industry": "event equipment rental",
  "city": "Portland",
  "product_match": null,
  "ops_icp": false,
  "expect_online_transaction": true,
  "expect_online_transaction_reason": "Rental business with fixed catalogue but no online booking or availability.",
  "expect_customer_portal": true,
  "expect_customer_portal_reason": "Repeat corporate clients and deposits handled offline.",
  "social": {
    "instagram": { "url": "https://instagram.com/acme", "followers": 1200, "last_post_days": 60 },
    "facebook": { "url": "https://facebook.com/acme", "last_post_days": 400 },
    "low_audience": true,
    "low_audience_evidence": "1.2k Instagram followers vs 8k+ for two local competitors"
  },
  "geo": {
    "queries": [ { "q": "event equipment rental Portland", "appears": false } ],
    "google_business_profile": true, "google_rating": 4.4, "google_reviews": 38, "faq_present": false
  },
  "ops_signals": ["Quotes sent by phone/email only"],
  "extra_findings": [
    { "category": "trust", "id": "dated_design", "title": "Design looks 10+ years old", "evidence": "Fixed-width layout, clip-art icons, © 2015 footer.",
      "impact": "First impression undercuts premium pricing.", "deduct": 12, "service": "design" }
  ],
  "fit": null
}
```
`fit` may be set to `{ "score": 0-100, "primary": "<offer-id>", "reason": "..." }` to override the profile's fit rules.

## Capability keys used in findings
`web`, `design`, `app`, `infra`, `growth`, `automation`, `ops`. Each capability maps to one of your offers in `pitch-profile/mapping.yaml`.
