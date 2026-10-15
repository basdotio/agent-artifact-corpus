#!/usr/bin/env python3
"""Score a client from audit.json (+ optional manual.json) using references/rubric.json.

Usage:
    python3 score.py <client_dir>            # writes <client_dir>/scores.json, prints summary
    python3 score.py --explain               # print the rubric as a readable table

Every deduction becomes a finding with: category, severity, title, evidence, impact, service hint.
Numbers in findings come only from audit.json / manual.json, never invented.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUBRIC_PATH = os.path.join(HERE, "..", "references", "rubric.json")

# Industry -> offer fit rules come from the company profile (pitch-profile/mapping.yaml), not from code.


def load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


def sev(points, weight=10):
    """Severity from the points this finding costs the OVERALL score (points x category weight / 100)."""
    loss = points * weight / 100
    if loss >= 3:
        return "critical"
    if loss >= 1.8:
        return "high"
    if loss >= 0.8:
        return "medium"
    return "low"


class Cat:
    def __init__(self, key, label, weight, base=100.0):
        self.key, self.label, self.weight = key, label, weight
        self.score = float(base)
        self.findings = []
        self.passed = []
        self.notes = []

    def deduct(self, pts, fid, title, evidence, impact, service, severity=None):
        if pts <= 0:
            return
        self.score -= pts
        self.findings.append({"id": fid, "category": self.key, "category_label": self.label, "points": round(pts, 1),
                              "severity": severity or sev(pts, self.weight), "title": title, "evidence": evidence,
                              "impact": impact, "service": service})

    def ok(self, text):
        self.passed.append(text)

    def final(self):
        return max(0, min(100, round(self.score)))


def ms(v):
    return f"{v / 1000:.1f}s" if v is not None else "n/a"


def mb(v):
    return f"{v / 1_000_000:.1f} MB" if v else "n/a"


def score(audit, manual, R, mapping=None):
    D, T = R["deductions"], R["thresholds"]
    C = {k: Cat(k, v["label"], v["weight"]) for k, v in R["categories"].items()}
    lh = audit.get("lighthouse") or {}
    lm, ld = lh.get("mobile") or {}, lh.get("desktop") or {}
    http, html, files = audit.get("http") or {}, audit.get("html") or {}, audit.get("files") or {}
    page, conv, trk = audit.get("page") or {}, audit.get("conversion") or {}, audit.get("tracking") or {}
    social, trust, ops = audit.get("social") or {}, audit.get("trust") or {}, audit.get("ops_signals") or {}
    man_social = manual.get("social") or {}
    man_geo = manual.get("geo") or {}

    # ---------------- Performance
    p = C["performance"]
    if lm.get("performance") is not None:
        base = 0.7 * lm["performance"] + 0.3 * (ld.get("performance") if ld.get("performance") is not None else lm["performance"])
        p.score = base
        p.notes.append(f"Lighthouse performance: mobile {lm.get('performance')}, desktop {ld.get('performance')}")
        if lm["performance"] < 50:
            p.findings.append({"id": "perf_score", "category": "performance", "category_label": p.label, "points": round(100 - base, 1),
                               "severity": "critical" if lm["performance"] < 30 else "high",
                               "title": f"Mobile speed score {lm['performance']}/100",
                               "evidence": f"Google Lighthouse mobile performance {lm['performance']}/100, desktop {ld.get('performance')}/100.",
                               "impact": "Most visitors arrive on phones; slow pages lose them before they see the offer, and Google ranks slow pages lower.",
                               "service": "web"})
        elif lm["performance"] < 80:
            p.findings.append({"id": "perf_score", "category": "performance", "category_label": p.label, "points": round(100 - base, 1),
                               "severity": "medium", "title": f"Mobile speed score {lm['performance']}/100",
                               "evidence": f"Google Lighthouse mobile performance {lm['performance']}/100.",
                               "impact": "Room to load faster on phones; every extra second costs conversions.", "service": "web"})
        else:
            p.ok(f"Mobile Lighthouse performance {lm['performance']}/100")
        lcp = lm.get("lcp_ms")
        if lcp and lcp > T["lcp_ms"]["warn"]:
            p.findings.append({"id": "lcp", "category": "performance", "category_label": p.label, "points": 0,
                               "severity": "high" if lcp > T["lcp_ms"]["crit"] else "medium",
                               "title": f"Main content appears after {ms(lcp)} on mobile",
                               "evidence": f"Largest Contentful Paint {ms(lcp)} (Google's 'good' target is under 2.5s).",
                               "impact": "Visitors stare at a half-loaded page; many leave before the first impression lands.",
                               "service": "web"})
        cls = lm.get("cls")
        if cls is not None and cls > T["cls"]["warn"]:
            p.findings.append({"id": "cls", "category": "performance", "category_label": p.label, "points": 0,
                               "severity": "medium" if cls < T["cls"]["crit"] else "high",
                               "title": "Page layout jumps while loading",
                               "evidence": f"Cumulative Layout Shift {cls:.2f} (target under 0.1).",
                               "impact": "Buttons move under the thumb; users tap the wrong thing and lose trust.", "service": "web"})
        tbt = lm.get("tbt_ms")
        if tbt and tbt > T["tbt_ms"]["warn"]:
            p.findings.append({"id": "tbt", "category": "performance", "category_label": p.label, "points": 0,
                               "severity": "high" if tbt > T["tbt_ms"]["crit"] else "medium",
                               "title": "Page freezes on interaction",
                               "evidence": f"Total Blocking Time {int(tbt)} ms on mobile (target under 200 ms).",
                               "impact": "Taps and scrolls feel stuck; heavy scripts block the page.", "service": "web"})
        if lm.get("opportunities"):
            p.notes.append("Top fixes: " + "; ".join(f"{o['title']} ({o.get('display') or ''})" for o in lm["opportunities"][:4]))
    else:
        p.notes.append("Lighthouse not available; scored from server response and page weight only.")
    ttfb = http.get("ttfb_ms")
    if ttfb and ttfb > T["ttfb_ms"]["crit"]:
        p.deduct(D["performance"]["ttfb_crit"], "ttfb", f"Server takes {ms(ttfb)} to respond",
                 f"Time to first byte {ttfb} ms (good: under 800 ms). Server: {http.get('server') or 'unknown'}.",
                 "Slow hosting delays every page before anything renders.", "infra")
    elif ttfb and ttfb > T["ttfb_ms"]["warn"]:
        p.deduct(D["performance"]["ttfb_warn"], "ttfb", f"Slow server response ({ms(ttfb)})",
                 f"Time to first byte {ttfb} ms (good: under 800 ms).", "Hosting adds delay to every page view.", "infra")
    elif ttfb:
        p.ok(f"Server response {ttfb} ms")
    tb = lm.get("total_bytes") or page.get("page_bytes_hint")  # without Lighthouse: bytes measured by the browser
    if tb and tb > T["page_bytes"]["crit"]:
        p.deduct(D["performance"]["page_bytes_crit"], "weight", f"Homepage weighs {mb(tb)}",
                 f"Total transfer size {mb(tb)} on mobile (healthy: under 3 MB).",
                 "Heavy pages burn mobile data and load slowly on 4G.", "web")
    elif tb and tb > T["page_bytes"]["warn"]:
        p.deduct(D["performance"]["page_bytes_warn"], "weight", f"Homepage weighs {mb(tb)}",
                 f"Total transfer size {mb(tb)} (healthy: under 3 MB).", "Oversized images and scripts slow every visit.", "web")

    # ---------------- SEO
    s, d = C["seo"], D["seo"]
    title = html.get("title") or ""
    if not title:
        s.deduct(d["title_missing"], "title", "Homepage has no title tag", "No <title> found.", "Google has nothing to show in search results.", "growth")
    elif not (T["title_len"]["min"] <= len(title) <= T["title_len"]["max"]):
        s.deduct(d["title_length"], "title_len", "Search title is the wrong length",
                 f"Title is {len(title)} characters: \"{title[:80]}\" (best: 30-65).",
                 "Google cuts or rewrites it; the search listing loses its pitch.", "growth")
    else:
        s.ok("Title tag present and well sized")
    md = html.get("meta_desc") or ""
    if not md:
        s.deduct(d["meta_desc_missing"], "meta_desc", "No search description", "Meta description missing.",
                 "Google picks random page text for the listing; fewer clicks.", "growth")
    elif not (T["meta_desc_len"]["min"] <= len(md) <= T["meta_desc_len"]["max"]):
        s.deduct(d["meta_desc_length"], "meta_desc_len", "Search description is the wrong length",
                 f"Meta description is {len(md)} characters (best: 70-160).", "Listing is truncated or thin.", "growth")
    h1s = html.get("h1s") or []
    if len(h1s) == 0:
        s.deduct(d["h1_missing"], "h1", "No main heading (H1) on the homepage", "Zero <h1> tags.",
                 "Google can't tell what the page is about.", "growth")
    elif len(h1s) > 1:
        s.deduct(d["h1_multiple"], "h1_multi", f"{len(h1s)} competing main headings", f"{len(h1s)} <h1> tags.", "Dilutes the page topic.", "growth")
    if not html.get("canonical"):
        s.deduct(d["canonical_missing"], "canonical", "No canonical URL", "No <link rel=canonical>.", "Duplicate URLs split ranking signals.", "growth")
    if not files.get("sitemap_xml"):
        s.deduct(d["sitemap_missing"], "sitemap", "No XML sitemap", "No sitemap.xml found (checked robots.txt and common paths).",
                 "New pages get found and indexed slowly.", "growth")
    if not files.get("robots_txt"):
        s.deduct(d["robots_missing"], "robots", "No robots.txt", "robots.txt missing.", "Crawlers get no guidance.", "growth")
    if files.get("robots_blocks_all"):
        s.deduct(d["robots_blocks_all"], "robots_block", "robots.txt blocks all search engines", "Disallow: / for all user-agents.",
                 "The site can disappear from Google entirely.", "growth", "critical")
    if "noindex" in (html.get("robots_meta") or "").lower():
        s.deduct(d["noindex"], "noindex", "Homepage tells Google not to index it", f"meta robots = {html.get('robots_meta')}",
                 "The homepage is invisible in search.", "growth", "critical")
    jl = [t for t in (html.get("jsonld_types") or []) if t != "INVALID"]
    if not jl:
        s.deduct(d["schema_missing"], "schema", "No structured data (schema.org)", "No JSON-LD found.",
                 "No rich results (ratings, hours, prices) in Google; AI assistants understand the business less.", "growth")
    else:
        s.ok("Structured data: " + ", ".join(sorted(set(jl))[:6]))
    it, im = html.get("images_total") or 0, html.get("images_missing_alt") or 0
    if it and im / it * 100 > T["alt_missing_pct"]["warn"]:
        s.deduct(d["alt_missing"], "alt", f"{im} of {it} images have no alt text", f"{round(im / it * 100)}% images lack alt.",
                 "Lost image-search traffic and poor accessibility.", "growth")
    if not html.get("lang"):
        s.deduct(d["lang_missing"], "lang", "Page language not declared", "<html> has no lang attribute.", "Minor search and accessibility issue.", "web")
    if lm.get("seo") is not None and lm["seo"] < 90:
        s.deduct((90 - lm["seo"]) * d["lighthouse_seo_below_90_per_point"], "lh_seo", f"Lighthouse SEO {lm['seo']}/100",
                 f"Google Lighthouse SEO score {lm['seo']}/100.", "Basic search hygiene gaps.", "growth")

    # ---------------- Mobile & UX
    u, d = C["mobile_ux"], D["mobile_ux"]
    if not html.get("viewport"):
        u.deduct(d["viewport_missing"], "viewport", "Site is not set up for phones", "No viewport meta tag.",
                 "Phones show a shrunk desktop page; users pinch and leave.", "web", "critical")
    if page.get("mobile_horizontal_overflow"):
        u.deduct(d["horizontal_overflow"], "overflow", "Page spills sideways on mobile", "Mobile layout wider than screen (horizontal scroll).",
                 "Looks broken on phones; erodes trust instantly.", "web")
    if lm.get("accessibility") is not None and lm["accessibility"] < 90:
        u.deduct((90 - lm["accessibility"]) * d["lighthouse_a11y_below_90_per_point"], "a11y",
                 f"Accessibility score {lm['accessibility']}/100",
                 f"Lighthouse accessibility {lm['accessibility']}/100. Failed: {', '.join(a for a in lm.get('failed_audits', []) if a in ('tap-targets','font-size','color-contrast','image-alt','link-name','button-name')) or 'see report'}.",
                 "Hard-to-read text and small tap targets frustrate mobile users.", "design")
    if lm.get("lcp_ms") and lm["lcp_ms"] > T["lcp_ms"]["crit"]:
        u.deduct(d["mobile_lcp_crit"], "mobile_lcp", "Mobile first view is very slow", f"Mobile LCP {ms(lm['lcp_ms'])}.",
                 "First impression on phones is a blank or half-loaded screen.", "web")
    ce = page.get("console_errors") or []
    if ce:
        u.deduct(d["console_errors"], "console", f"{len(ce)} JavaScript errors on load", "Example: " + ce[0][:140],
                 "Broken scripts can silently break forms, menus or tracking.", "web")
    br = (audit.get("links") or {}).get("broken") or []
    if br:
        u.deduct(min(d["broken_links_max"], d["broken_links_each"] * len(br)), "broken_links", f"{len(br)} broken links",
                 "e.g. " + ", ".join(f"{b['url']} ({b['status']})" for b in br[:3]),
                 "Dead ends lose visitors and hurt SEO.", "web")

    # ---------------- Trust & security
    t, d = C["trust"], D["trust"]
    if not http.get("https"):
        t.deduct(d["no_https"], "https", "Site is not secure (no HTTPS)", "Site served over plain HTTP.",
                 "Browsers show 'Not secure'; Google ranks it lower; form data is exposed.", "infra", "critical")
    elif http.get("http_redirects_to_https") is False:
        t.deduct(d["no_https_redirect"], "https_redirect", "HTTP version doesn't redirect to HTTPS", "http:// stays insecure.",
                 "Some visitors land on the insecure version.", "infra")
    if http.get("apex_ssl_error"):
        t.deduct(d.get("apex_cert_mismatch", 30), "apex_cert", "Security warning on the bare domain",
                 f"https://{(http.get('host') or '').replace('www.', '')} serves the wrong SSL certificate: {http['apex_ssl_error'][:120]}",
                 "Anyone who types the address without 'www' gets a full-page 'connection not private' warning and most leave.",
                 "infra")
    if http.get("ssl_days_left") is not None and http["ssl_days_left"] < T["ssl_days_left"]["warn"]:
        t.deduct(d["ssl_expiring"], "ssl_exp", f"SSL certificate expires in {http['ssl_days_left']} days", f"Issuer: {http.get('ssl_issuer')}.",
                 "If it lapses, browsers block the site with a full-page warning.", "infra")
    sh = http.get("security_headers") or {}
    if http.get("https") and not sh.get("strict-transport-security"):
        t.deduct(d["hsts_missing"], "hsts", "Missing HSTS security header", "No Strict-Transport-Security header.", "Weaker protection against downgrade attacks.", "infra")
    missing = [k for k in ("content-security-policy", "x-content-type-options", "x-frame-options") if not sh.get(k)]
    if missing:
        t.deduct(min(d["security_header_max"], d["security_header_missing_each"] * len(missing)), "sec_headers",
                 f"{len(missing)} security headers missing", "Missing: " + ", ".join(missing) + ".",
                 "Basic hardening gaps that security scanners flag.", "infra")
    if page.get("mixed_content"):
        t.deduct(d["mixed_content"], "mixed", "Insecure content on a secure page", f"{len(page['mixed_content'])} http:// resources, e.g. {page['mixed_content'][0][:100]}",
                 "Browsers block or warn on parts of the page.", "web")
    if not trust.get("privacy_page"):
        t.deduct(d["privacy_missing"], "privacy", "No privacy policy", "No privacy link found on homepage.",
                 "Required for ads and data laws (DPDP Act, GDPR); signals an unfinished business.", "web")
    if not trust.get("testimonials"):
        t.deduct(d["social_proof_missing"], "proof", "No reviews or testimonials on the homepage", "No testimonial/review section found.",
                 "Visitors have no proof others trust you.", "design")
    if not trust.get("contact_visible"):
        t.deduct(d["contact_missing"], "contact", "Contact details are hard to find", "No phone/email on homepage.",
                 "Ready buyers can't reach you quickly.", "web")
    if ld.get("best_practices") is not None and ld["best_practices"] < 80:
        t.deduct(d["lighthouse_best_practices_below_80"], "best_practices", f"Lighthouse best-practices {ld['best_practices']}/100",
                 f"Google Lighthouse best-practices {ld['best_practices']}/100.", "Outdated or risky code patterns.", "web")

    # ---------------- Conversion
    c, d = C["conversion"], D["conversion"]
    ctas = (conv.get("ctas_above_fold_mobile") or []) + (conv.get("ctas_above_fold_desktop") or [])
    if not ctas:
        c.deduct(d["no_cta_above_fold"], "cta", "No clear call-to-action on first screen", "No 'book / order / contact / get quote' style button visible without scrolling.",
                 "Visitors don't know the next step; intent is wasted.", "web")
    else:
        c.ok("Above-fold CTA: " + ", ".join(sorted(set(ctas))[:3]))
    if not conv.get("tel_links"):
        c.deduct(d["no_click_to_call"], "tel", "No tap-to-call phone link", "No tel: links.", "Mobile users can't call in one tap.", "web")
    if not conv.get("whatsapp") and not conv.get("chat_widget"):
        c.deduct(d["no_whatsapp_or_chat"], "chat", "No WhatsApp or live chat", "No wa.me link or chat widget found.",
                 "In India most buyers prefer WhatsApp; no instant channel loses warm leads.", "automation")
    if not conv.get("forms") and not ops.get("booking") and not ops.get("ecommerce"):
        c.deduct(d["no_form_or_booking"], "form", "No enquiry form, booking or cart", "No <form>, booking or cart flow on homepage.",
                 "Leads can't leave details outside business hours.", "web")
    if not (trk.get("ga4") or trk.get("gtm") or trk.get("universal_analytics") or trk.get("clarity")):
        c.deduct(d["no_analytics"], "analytics", "No analytics installed", "No GA4 / GTM / Clarity detected.",
                 "No data on visitors, sources or conversions; marketing spend is blind.", "growth", "critical")
    elif trk.get("universal_analytics") and not trk.get("ga4") and not trk.get("gtm"):
        c.deduct(d["no_analytics"] / 2, "analytics_old", "Only old Universal Analytics found", "UA stopped collecting data in 2023/2024.",
                 "Tracking is effectively off.", "growth")
    if not (trk.get("meta_pixel") or trk.get("google_ads") or trk.get("linkedin_insight") or trk.get("tiktok_pixel")):
        c.deduct(d["no_ad_pixel"], "pixel", "No ad pixels (Meta / Google Ads)", "No retargeting pixel detected.",
                 "Can't retarget visitors or measure ad ROI.", "growth")
    if manual.get("expect_online_transaction") and not ops.get("ecommerce") and not ops.get("booking"):
        c.deduct(d["no_online_transaction_when_expected"], "no_txn", "Customers can't order or book online",
                 manual.get("expect_online_transaction_reason") or "Business sells products/bookings but site has no cart or booking flow.",
                 "Every sale needs a call or message; you lose buyers who want to self-serve at night.",
                 manual.get("product_match") or manual.get("vertical_match") or "web")

    # ---------------- Social
    so, d = C["social"], D["social"]
    linked = [k for k in ("instagram", "facebook", "linkedin", "youtube", "x", "tiktok", "pinterest") if social.get(k) or (man_social.get(k) or {}).get("url")]
    if not linked:
        so.deduct(d["no_profiles_linked"], "no_social", "No social profiles linked from the website", "No Instagram/Facebook/LinkedIn/YouTube links found.",
                  "Visitors can't verify you're active; social proof is lost.", "growth")
    elif len(linked) == 1:
        so.deduct(d["one_profile_linked"], "one_social", f"Only one social channel linked ({linked[0]})", f"Linked: {linked[0]}.",
                  "Narrow reach; buyers on other platforms never find you.", "growth")
    else:
        so.ok("Linked: " + ", ".join(linked))
    og = html.get("og") or {}
    if not og.get("image"):
        so.deduct(d["og_image_missing"], "og_image", "Links shared on WhatsApp/social show no preview image", "No og:image tag.",
                  "Shared links look bare and get fewer clicks.", "growth")
    if not og.get("title"):
        so.deduct(d["og_title_missing"], "og_title", "No social share title", "No og:title.", "Shares show a messy default title.", "growth")
    inactive = []
    for k, v in man_social.items():
        if isinstance(v, dict) and v.get("last_post_days") is not None and v["last_post_days"] > T["social_inactive_days"]:
            inactive.append(f"{k} (last post ~{v['last_post_days']} days ago)")
    if inactive:
        so.deduct(min(d["inactive_max"], d["inactive_platform_each"] * len(inactive)), "inactive", "Social channels have gone quiet",
                  "; ".join(inactive) + ".", "A dormant page tells buyers the business may be slowing down.", "growth")
    if man_social.get("low_audience"):
        so.deduct(d["low_audience"], "low_audience", "Small social audience for the category",
                  man_social.get("low_audience_evidence") or "Follower counts low vs. local competitors.",
                  "Limited organic reach; every launch starts from zero.", "growth")
    if not man_social:
        so.notes.append("Follower counts / activity not verified.")

    # ---------------- GEO
    g, d = C["geo"], D["geo"]
    if not files.get("llms_txt"):
        g.deduct(d["llms_txt_missing"], "llms", "No llms.txt for AI assistants", "/llms.txt not found.",
                 "AI crawlers get no summary of what you do.", "growth")
    if not jl:
        g.deduct(d["schema_missing"], "geo_schema", "No machine-readable business data", "No JSON-LD (Organization/LocalBusiness/Product).",
                 "ChatGPT, Gemini and Google AI Overviews can't reliably describe or recommend you.", "growth")
    faq = man_geo.get("faq_present")
    if faq is None:
        faq = any("FAQ" in t for t in jl)
    if not faq:
        g.deduct(d["faq_missing"], "faq", "No FAQ content", "No FAQ section/schema found.", "AI answers pull from Q&A content; you're not in it.", "growth")
    qs = man_geo.get("queries") or []
    if qs and not any(q.get("appears") for q in qs):
        g.deduct(d["absent_in_answers"], "geo_absent", "Not showing up when buyers ask AI or search",
                 "Checked: " + "; ".join(f"\"{q['q']}\"" for q in qs[:3]) + ", business not found in top results.",
                 "Buyers asking ChatGPT/Google for your category get your competitors.", "growth", "high")
    ab = audit.get("ai_bots") or {}
    if ab.get("search_blocked"):
        who = ", ".join(ab["search_blocked"])
        how = sorted({v["by"] for v in (ab.get("bots") or {}).values() if v.get("blocked") and v.get("kind") == "search"})
        g.deduct(d["ai_search_bots_blocked"], "ai_search_blocked", "AI assistants are blocked from reading the site",
                 f"Blocked: {who} (via {' and '.join(how)}).",
                 "When buyers ask ChatGPT or Perplexity for your category, they can't read or recommend you.", "growth", "high")
    elif ab.get("bots"):
        g.ok("AI search assistants can read the site")
    if man_geo.get("google_business_profile") is False:
        g.deduct(d["no_google_business_profile"], "gbp", "No Google Business Profile found", "No Maps listing found.",
                 "Invisible in 'near me' searches and Google Maps.", "growth")

    # ---------------- Ops maturity
    o, d = C["ops"], D["ops"]
    ops_service = "ops" if (manual.get("product_match") or manual.get("vertical_match") or manual.get("ops_icp")) else "automation"
    if ops.get("whatsapp_ordering"):
        o.deduct(d["whatsapp_only_ordering"], "wa_order", "Orders run through WhatsApp chats", "Site asks customers to order/enquire on WhatsApp.",
                 "Orders get lost in chats, no order history, no reporting, staff time burned on copy-paste.", ops_service)
    if ops.get("google_forms"):
        o.deduct(d["google_forms"], "gforms", "Google Forms used for orders/enquiries", "Link to docs.google.com/forms found.",
                 "Data sits in a spreadsheet nobody owns; no follow-up automation.", ops_service)
    if ops.get("pdf_catalog"):
        o.deduct(d["pdf_catalog"], "pdf_cat", "Catalogue/price list is a PDF", "PDF catalogue/brochure link found.",
                 "Prices go stale; buyers can't search, filter or order.", ops_service)
    if ops.get("call_to_order") and not ops.get("ecommerce") and not ops.get("booking"):
        o.deduct(d["call_to_order_no_online_flow"], "call_order", "Ordering needs a phone call", "'Call to order' wording, no online flow.",
                 "Sales stop when the phone isn't answered.", ops_service)
    if manual.get("expect_customer_portal") and not ops.get("customer_login"):
        o.deduct(d["no_customer_portal_when_expected"], "no_portal", "No customer/dealer portal",
                 manual.get("expect_customer_portal_reason") or "B2B/repeat customers but no login or portal.",
                 "Repeat buyers can't reorder, track or download invoices themselves.", ops_service)
    if ops.get("legacy_stack"):
        o.deduct(d["legacy_stack"], "legacy", "Site runs on outdated technology", ", ".join(ops["legacy_stack"]) + ".",
                 "Harder to secure, slower to change, costlier to maintain.", "web")
    ms_ = manual.get("ops_signals") or []
    if ms_:
        o.deduct(min(d["manual_signal_max"], d["manual_signal_each"] * len(ms_)), "ops_manual", "Manual back-office signals",
                 "; ".join(ms_[:4]), "Growth is capped by manual work and spreadsheets.", ops_service)

    # ---------------- Extra findings from Claude's research
    for xf in manual.get("extra_findings") or []:
        cat = C.get(xf.get("category"))
        if cat:
            cat.deduct(float(xf.get("deduct", 0)), xf.get("id", "extra"), xf["title"], xf.get("evidence", ""), xf.get("impact", ""),
                       xf.get("service", "web"), xf.get("severity"))

    # ---------------- Totals
    cats = {}
    overall = 0.0
    for k, cat in C.items():
        sc = cat.final()
        overall += sc * cat.weight / 100
        cats[k] = {"label": cat.label, "weight": cat.weight, "score": sc, "grade": grade(sc, R),
                   "findings": cat.findings, "passed": cat.passed, "notes": cat.notes}
    overall = round(overall)
    fit = compute_fit(audit, manual, R, mapping)
    lsw = R["lead_score"]
    lead = round(lsw["opportunity_weight"] * (100 - overall) + lsw["fit_weight"] * fit["score"])
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    allf = [f for c_ in cats.values() for f in c_["findings"]]
    allf.sort(key=lambda f: (sev_rank[f["severity"]], -f["points"] * R["categories"][f["category"]]["weight"]))
    return {"overall": overall, "grade": grade(overall, R), "categories": cats, "top_findings": allf[:12],
            "finding_count": {s_: sum(1 for f in allf if f["severity"] == s_) for s_ in sev_rank},
            "fit": fit, "lead_score": lead, "rubric_version": R.get("version")}


def grade(sc, R):
    b = R["grade_bands"]
    return "healthy" if sc >= b["healthy"] else ("needs work" if sc >= b["needs_work"] else "critical")


def compute_fit(audit, manual, R, mapping=None):
    """Which offer fits this prospect best, and how strongly (0-100). Rules live in the company profile."""
    if isinstance(manual.get("fit"), dict) and manual["fit"].get("score") is not None:
        return {"score": manual["fit"]["score"], "primary": manual["fit"].get("primary"), "reason": manual["fit"].get("reason", "set manually")}
    mapping = mapping or {}
    text = " ".join([manual.get("industry") or "", (audit.get("html") or {}).get("title") or "",
                     (audit.get("html") or {}).get("meta_desc") or ""]).lower()
    forced = manual.get("product_match") or manual.get("vertical_match")
    for rule in mapping.get("fit_rules", []) or []:
        if forced == rule.get("offer") or any(str(k).lower() in text for k in rule.get("keywords", [])):
            hit = forced if forced == rule.get("offer") else next(k for k in rule["keywords"] if str(k).lower() in text)
            return {"score": rule.get("score", 80), "primary": rule["offer"], "reason": f"Matches {rule['offer']} ({hit})"}
    d = mapping.get("default_fit") or {"offer": None, "score": R["lead_score"].get("fit_defaults", {}).get("generic", 50)}
    return {"score": d.get("score", 50), "primary": d.get("offer"), "reason": "General web/growth fit"}


def explain(R):
    print(f"Rubric {R.get('version')}  (edit references/rubric.json)\n")
    for k, v in R["categories"].items():
        print(f"{v['label']:<20} weight {v['weight']:>3}")
        for dk, dv in R["deductions"].get(k, {}).items():
            if not dk.startswith("_"):
                print(f"    -{dv:<5} {dk}")
    print("\nGrade bands:", R["grade_bands"])
    print("Lead score:", R["lead_score"]["_doc"])


def main():
    R = load(RUBRIC_PATH)
    if len(sys.argv) > 1 and sys.argv[1] == "--explain":
        explain(R)
        return
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cdir = sys.argv[1]
    audit = load(os.path.join(cdir, "audit.json"))
    if not audit:
        sys.exit(f"no audit.json in {cdir}")
    manual = load(os.path.join(cdir, "manual.json"), {}) or {}
    sys.path.insert(0, HERE)
    import profile as P
    prof = P.load_profile(client_dir=cdir, required=False)
    res = score(audit, manual, R, (prof or {}).get("mapping"))
    if prof:
        caps = prof["mapping"].get("capabilities") or {}
        for f in res["top_findings"] + [x for c in res["categories"].values() for x in c["findings"]]:
            f["offer"] = caps.get(f["service"], f["service"])
    with open(os.path.join(cdir, "scores.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(f"Overall {res['overall']}/100 ({res['grade']})  lead score {res['lead_score']}  fit: {res['fit']['primary']} ({res['fit']['score']})")
    for k, c in res["categories"].items():
        print(f"  {c['label']:<20} {c['score']:>3}  {c['grade']}")
    print("Top findings:")
    for f in res["top_findings"][:8]:
        print(f"  [{f['severity']}] {f['category_label']}: {f['title']}")


if __name__ == "__main__":
    main()
