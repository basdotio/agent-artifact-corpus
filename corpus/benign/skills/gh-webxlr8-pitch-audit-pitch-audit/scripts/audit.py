#!/usr/bin/env python3
"""Collect raw website audit data for one client.

Usage:
    python3 audit.py <url> --out <client_dir> [--speed auto|psi|local|off] [--max-links 25]

Writes:
    <client_dir>/audit.json
    <client_dir>/page_text.txt          (visible homepage text, for business research)
    <client_dir>/screenshots/*.png      (desktop/mobile fold + full page)
    <client_dir>/lighthouse-*.json      (raw Lighthouse reports, if run)

Only standard library + Playwright (uses the installed Google Chrome channel).
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 pitch-audit/1.0 (+https://github.com/webxlr8/pitch-audit)")
CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/opt/homebrew/bin/google-chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def log(msg):
    print(f"[audit] {msg}", file=sys.stderr, flush=True)


def normalize_url(url):
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def http_get(url, method="GET", timeout=20, max_bytes=2_000_000, ua=None):
    """Return dict(status, url, headers, body, ttfb_ms, error). Follows redirects."""
    ctx = ssl.create_default_context()
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": ua or UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            ttfb = (time.time() - t0) * 1000
            body = r.read(max_bytes) if method == "GET" else b""
            return {"status": r.status, "url": r.geturl(), "headers": {k.lower(): v for k, v in r.headers.items()},
                    "body": body, "ttfb_ms": round(ttfb), "error": None}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "url": url, "headers": {k.lower(): v for k, v in (e.headers or {}).items()},
                "body": b"", "ttfb_ms": round((time.time() - t0) * 1000), "error": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"status": None, "url": url, "headers": {}, "body": b"", "ttfb_ms": None, "error": str(e)[:200]}


def check_http(url):
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    out = {"host": host}
    # HTTPS main fetch (3 samples, keep median TTFB)
    samples = []
    main = None
    for _ in range(3):
        r = http_get(url)
        if main is None or (r["status"] and not main["status"]):
            main = r
        if r["ttfb_ms"] is not None and r["status"]:
            samples.append(r["ttfb_ms"])
    samples.sort()
    out["status"] = main["status"]
    out["final_url"] = main["url"]
    out["error"] = main["error"]
    out["ttfb_ms"] = samples[len(samples) // 2] if samples else None
    out["https"] = main["url"].startswith("https://") and bool(main["status"])
    h = main["headers"]
    out["server"] = h.get("server")
    out["powered_by"] = h.get("x-powered-by")
    out["security_headers"] = {
        "strict-transport-security": "strict-transport-security" in h,
        "content-security-policy": "content-security-policy" in h,
        "x-content-type-options": "x-content-type-options" in h,
        "x-frame-options": "x-frame-options" in h or "frame-ancestors" in h.get("content-security-policy", ""),
        "referrer-policy": "referrer-policy" in h,
    }
    # http -> https redirect
    r = http_get(f"http://{host}{parsed.path or '/'}", timeout=15, max_bytes=1000)
    out["http_redirects_to_https"] = bool(r["url"].startswith("https://")) if r["status"] else None
    # SSL expiry
    out["ssl_days_left"] = None
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
                exp = dt.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                out["ssl_days_left"] = (exp - dt.datetime.utcnow()).days
                out["ssl_issuer"] = dict(x[0] for x in cert.get("issuer", ())).get("organizationName")
    except Exception as e:  # noqa: BLE001
        out["ssl_error"] = str(e)[:200]
    return out, main


def check_files(base):
    origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(base))
    out = {}
    r = http_get(origin + "/robots.txt", max_bytes=200_000)
    txt = r["body"].decode("utf-8", "ignore") if r["status"] == 200 else ""
    is_html = "<html" in txt[:500].lower()
    out["robots_txt"] = r["status"] == 200 and not is_html
    out["robots_blocks_all"] = bool(re.search(r"(?ims)user-agent:\s*\*\s*(?:\n(?!user-agent).*)*?\n\s*disallow:\s*/\s*$", txt)) if out["robots_txt"] else False
    sitemaps = [urllib.parse.urljoin(origin + "/", u) for u in re.findall(r"(?im)^\s*sitemap:\s*(\S+)", txt)] if out["robots_txt"] else []
    candidates = sitemaps + [origin + "/sitemap.xml", origin + "/sitemap_index.xml", origin + "/wp-sitemap.xml"]
    out["sitemap_xml"] = None
    for c in candidates:
        rr = http_get(c, max_bytes=50_000)
        body = rr["body"][:2000].decode("utf-8", "ignore").lower()
        if rr["status"] == 200 and ("<urlset" in body or "<sitemapindex" in body):
            out["sitemap_xml"] = c
            break
    rr = http_get(origin + "/llms.txt", max_bytes=20_000)
    b = rr["body"][:500].decode("utf-8", "ignore").lower()
    out["llms_txt"] = rr["status"] == 200 and "<html" not in b and len(b.strip()) > 0
    return out


DOM_JS = r"""
() => {
  const q = (s) => Array.from(document.querySelectorAll(s));
  const meta = (n) => { const m = document.querySelector(`meta[name="${n}"], meta[property="${n}"]`); return m ? (m.getAttribute('content') || '').trim() : null; };
  const vw = window.innerWidth, vh = window.innerHeight;
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
     return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0.05; };
  const inFold = (el) => { const r = el.getBoundingClientRect(); return r.top < vh && r.bottom > 0 && r.left < vw; };
  const links = q('a[href]').map(a => ({href: a.href, text: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 80)}));
  const imgs = q('img');
  const ctaRe = /(book|order|buy|shop|get|start|contact|call|enquir|inquir|quote|demo|sign ?up|register|whatsapp|talk|schedule|appointment|reserve|subscribe|download|apply|join|try)/i;
  const ctas = q('a, button, input[type=submit]').filter(el => visible(el) && inFold(el))
     .map(el => (el.innerText || el.value || el.getAttribute('aria-label') || '').trim()).filter(t => t && t.length < 40 && ctaRe.test(t));
  const jsonld = [];
  q('script[type="application/ld+json"]').forEach(s => { try { const d = JSON.parse(s.textContent);
      const walk = (o) => { if (!o) return; if (Array.isArray(o)) return o.forEach(walk); if (typeof o === 'object') { if (o['@type']) jsonld.push([].concat(o['@type']).join(',')); if (o['@graph']) walk(o['@graph']); } };
      walk(d); } catch (e) { jsonld.push('INVALID'); } });
  const scripts = q('script[src]').map(s => s.src);
  const iframes = q('iframe[src]').map(f => f.src);
  const html = document.documentElement.outerHTML;
  return {
    title: document.title || null,
    meta_desc: meta('description'),
    robots_meta: meta('robots'),
    canonical: (document.querySelector('link[rel="canonical"]') || {}).href || null,
    lang: document.documentElement.getAttribute('lang'),
    viewport: meta('viewport'),
    generator: meta('generator'),
    og: { title: meta('og:title'), description: meta('og:description'), image: meta('og:image') },
    twitter_card: meta('twitter:card'),
    favicon: !!document.querySelector('link[rel*="icon"]'),
    h1s: q('h1').map(h => h.innerText.trim().slice(0, 120)).filter(Boolean),
    h2_count: q('h2').length,
    jsonld_types: jsonld,
    images_total: imgs.length,
    images_missing_alt: imgs.filter(i => !i.hasAttribute('alt') || i.getAttribute('alt').trim() === '').length,
    forms: q('form').length,
    inputs_email: q('input[type=email]').length,
    tel_links: links.filter(l => l.href.startsWith('tel:')).length,
    mailto_links: links.filter(l => l.href.startsWith('mailto:')).length,
    whatsapp: links.some(l => /wa\.me|api\.whatsapp|whatsapp\.com\/send|web\.whatsapp/i.test(l.href)) || /wa\.me\//i.test(html),
    ctas_above_fold: Array.from(new Set(ctas)).slice(0, 10),
    links: links.slice(0, 600),
    scripts: scripts.slice(0, 200),
    iframes: iframes.slice(0, 50),
    html_len: html.length,
    word_count: (document.body ? document.body.innerText : '').split(/\s+/).filter(Boolean).length,
    text: (document.body ? document.body.innerText : '').replace(/\n{3,}/g, '\n\n').slice(0, 15000),
    scroll_width: document.documentElement.scrollWidth,
    inner_width: window.innerWidth,
    jquery: !!window.jQuery, jquery_version: window.jQuery ? window.jQuery.fn.jquery : null,
    next: !!window.__NEXT_DATA__ || !!document.querySelector('script#__NEXT_DATA__'),
    has_tables_layout: q('table').length > 5,
    year_in_footer: ((document.querySelector('footer') || document.body || {}).innerText || '').match(/(?:©|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})/i)?.[1] || null,
  };
}
"""

SOCIAL_PATTERNS = {
    "instagram": r"instagram\.com/(?!p/|reel/|explore)[A-Za-z0-9_.]+",
    "facebook": r"facebook\.com/(?!sharer|share|dialog|plugins|tr\b)[A-Za-z0-9_.\-/]+",
    "linkedin": r"linkedin\.com/(company|in|school)/[A-Za-z0-9_\-%.]+",
    "youtube": r"youtube\.com/(@|channel/|c/|user/)[A-Za-z0-9_\-]+",
    "x": r"(twitter|x)\.com/(?!intent|share|home)[A-Za-z0-9_]+",
    "tiktok": r"tiktok\.com/@[A-Za-z0-9_.]+",
    "pinterest": r"pinterest\.[a-z.]+/(?!pin/)[A-Za-z0-9_]+",
    "google_business": r"(g\.page/|maps\.app\.goo\.gl/|google\.com/maps/place|business\.site)",
}

TRACKERS = {
    "ga4": r"googletagmanager\.com/gtag/js\?id=G-|gtag\(['\"]config['\"],\s*['\"]G-",
    "gtm": r"googletagmanager\.com/gtm\.js|GTM-[A-Z0-9]{4,}",
    "universal_analytics": r"google-analytics\.com/analytics\.js|UA-\d+-\d+",
    "meta_pixel": r"connect\.facebook\.net/.+/fbevents\.js|fbq\(",
    "linkedin_insight": r"snap\.licdn\.com|_linkedin_partner_id",
    "google_ads": r"googleadservices|AW-\d{6,}",
    "clarity": r"clarity\.ms",
    "hotjar": r"hotjar\.com",
    "tiktok_pixel": r"analytics\.tiktok\.com",
}

CHAT_WIDGETS = r"(tawk\.to|intercom|crisp\.chat|drift\.com|zopim|zendesk|livechat|freshchat|hubspot.*conversations|tidio|wati\.io|interakt|gallabox|elfsight.*whatsapp|getbutton\.io|chatwoot|botpress|manychat)"

CMS_SIGNS = [
    ("WordPress", r"/wp-content/|/wp-includes/"),
    ("WooCommerce", r"/plugins/woocommerce/|woocommerce-page|wc-block"),
    ("Shopify", r"cdn\.shopify\.com|Shopify\.theme"),
    ("Wix", r"wixstatic\.com|_wix"),
    ("Squarespace", r"squarespace\.com|static1\.squarespace"),
    ("Webflow", r"webflow\.(com|io)|data-wf-page"),
    ("Joomla", r"/media/jui/|/media/system/js/"),
    ("Drupal", r"drupal-settings-json|/sites/default/files"),
    ("Magento", r"Magento_[A-Z]|/static/version\d+/frontend/"),
    ("GoDaddy Builder", r"img1\.wsimg\.com"),
    ("Zoho Sites", r"zohosites|zohopublic|sites\.zoho"),
    ("Blogger", r"blogger\.com|blogspot"),
    ("Framer", r"framer\.(com|app)|framerusercontent"),
    ("Next.js", r"/_next/static"),
    ("Astro", r"astro-island|/_astro/"),
]

OPS_SIGNALS = {
    "whatsapp_ordering": r"(order|book|enquir\w*|inquir\w*|bulk)\s+(now\s+)?(on|via|through)\s+whatsapp|whatsapp\s+(us\s+)?(to|for)\s+(order|book|price|quote)",
    "google_forms": r"docs\.google\.com/forms|forms\.gle/",
    "pdf_catalog": r"(catalog(ue)?|brochure|price\s*list|menu)[^\n]{0,40}\.pdf|\.pdf[^\n]{0,40}(catalog|brochure|price)",
    "call_to_order": r"call\s+(us\s+)?(to|for)\s+(order|book|price|quote|availability)|(phone|call)\s+(in\s+)?your\s+order",
    "customer_login": r"(log\s?in|sign\s?in|my\s+account|dealer\s+portal|customer\s+portal|partner\s+login)",
    "b2b_wholesale": r"(wholesale|bulk\s+order|b2b|distributor|dealer|retailer\s+enquir|trade\s+enquir|manufacturer|exporter|supplier)",
    "rental": r"\b(rent|rental|hire|for\s+rent|on\s+rent|lease)\b",
    "booking": r"\b(book\s+(now|online|a\s+table|your\s+slot)|check\s+availability|reserve\s+(now|online|a\s+table)|book\s+an?\s+appointment|schedule\s+an?\s+(appointment|visit|call))",
    "ecommerce": r"(add\s+to\s+cart|add\s+to\s+bag|checkout|buy\s+now|shop\s+now|cart)",
    "careers_hiring": r"(careers|we.re\s+hiring|join\s+our\s+team|openings)",
}

TRUST_SIGNALS = {
    "privacy_page": r"privacy",
    "terms_page": r"terms|conditions",
    "testimonials": r"testimonial|what\s+(our\s+)?(clients?|customers?)\s+says?|reviews?|rated\s+\d|★|google\s+reviews|trustpilot",
    "address": r"\b\d{6}\b|street|road|nagar|building|floor|suite|avenue|\bP\.?O\.?\b|kerala|india|uae|dubai",
    "cookie_banner": r"cookie(s)?\s+(policy|consent|settings|preferences)|we use cookies|accept (all )?cookies",
}


def find_chrome():
    if os.environ.get("CHROME_PATH") and os.path.exists(os.environ["CHROME_PATH"]):
        return os.environ["CHROME_PATH"]
    if os.environ.get("PITCH_BROWSER") == "chromium":
        try:  # Playwright's bundled Chromium (CI / Docker)
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                return pw.chromium.executable_path
        except Exception:  # noqa: BLE001
            pass
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return shutil.which("google-chrome") or shutil.which("chromium")


def run_browser(url, shots_dir):
    from playwright.sync_api import sync_playwright
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from browser import launch as launch_browser

    res = {"desktop": None, "mobile": None, "console_errors": [], "mixed_content": [], "failed_requests": [],
           "page_bytes": 0, "request_count": 0, "load_ms": None}
    with sync_playwright() as p:
        browser = launch_browser(p)
        try:
            for mode in ("desktop", "mobile"):
                if mode == "desktop":
                    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, user_agent=UA, ignore_https_errors=True)
                else:
                    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                              has_touch=True, ignore_https_errors=True,
                                              user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
                page = ctx.new_page()
                if mode == "desktop":
                    page.on("console", lambda m: res["console_errors"].append(m.text[:200]) if m.type == "error" and not m.text.startswith("%c") else None)
                    page.on("pageerror", lambda e: res["console_errors"].append(str(e)[:200]))

                    def on_resp(r):
                        try:
                            res["request_count"] += 1
                            if url.startswith("https://") and r.url.startswith("http://"):
                                res["mixed_content"].append(r.url[:200])
                            if r.status >= 400:
                                res["failed_requests"].append(f"{r.status} {r.url[:160]}")
                            cl = r.headers.get("content-length")
                            if cl and cl.isdigit():
                                res["page_bytes"] += int(cl)
                        except Exception:  # noqa: BLE001
                            pass
                    page.on("response", on_resp)
                t0 = time.time()
                try:
                    page.goto(url, wait_until="load", timeout=60000)
                except Exception as e:  # noqa: BLE001
                    log(f"{mode} goto warning: {str(e)[:120]}")
                try:
                    page.wait_for_load_state("networkidle", timeout=12000)
                except Exception:  # noqa: BLE001
                    pass
                if mode == "desktop":
                    res["load_ms"] = round((time.time() - t0) * 1000)
                page.wait_for_timeout(1500)
                page.screenshot(path=os.path.join(shots_dir, f"{mode}-fold.png"))
                dom = page.evaluate(DOM_JS)
                # lazy content: scroll then full page shot (capped height)
                try:
                    page.evaluate("async () => { for (let y = 0; y < Math.min(document.body.scrollHeight, 9000); y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } window.scrollTo(0, 0); }")
                    page.wait_for_timeout(800)
                    h = page.evaluate("() => Math.min(document.documentElement.scrollHeight, 7000)")
                    page.set_viewport_size({"width": page.viewport_size["width"], "height": int(h)})
                    page.screenshot(path=os.path.join(shots_dir, f"{mode}-full.png"))
                except Exception as e:  # noqa: BLE001
                    log(f"{mode} full screenshot skipped: {str(e)[:120]}")
                res[mode] = dom
                ctx.close()
        finally:
            browser.close()
    return res


AI_BOTS = {  # search = answers users get today; training = model training (blocking it is a legitimate choice)
    "OAI-SearchBot": ("ChatGPT search", "search"), "ChatGPT-User": ("ChatGPT browsing", "search"),
    "PerplexityBot": ("Perplexity", "search"), "Claude-SearchBot": ("Claude search", "search"),
    "GPTBot": ("OpenAI training", "training"), "ClaudeBot": ("Anthropic training", "training"),
    "Google-Extended": ("Google Gemini training", "training"), "CCBot": ("Common Crawl", "training"),
}


def check_ai_bots(url):
    """Can AI assistants read the site? robots.txt is read as a browser (bot-protected sites refuse
    Python's default agent, which would wrongly look like 'block everything'); a homepage request with each
    bot's user agent catches CDN/firewall blocks, trusted only when a normal browser gets 200."""
    import urllib.robotparser
    origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    rp = urllib.robotparser.RobotFileParser()
    r = http_get(origin + "/robots.txt", max_bytes=300_000)
    body = r["body"].decode("utf-8", "ignore") if r["status"] == 200 else ""
    rp.parse([] if "<html" in body[:500].lower() else body.splitlines())
    base = http_get(url, max_bytes=2000)["status"]

    def probe(bot):
        name, kind = AI_BOTS[bot]
        allowed = rp.can_fetch(bot, url)
        st = http_get(url, max_bytes=2000, ua=f"Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; {bot}/1.0)")["status"]
        firewall = base == 200 and st in (401, 403, 429, 503)
        return bot, {"name": name, "kind": kind, "robots_allows": allowed, "http": st,
                     "blocked": (not allowed) or firewall, "by": "robots.txt" if not allowed else ("firewall/CDN" if firewall else None)}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        res = dict(ex.map(probe, AI_BOTS))
    return {"bots": res, "search_blocked": [v["name"] for v in res.values() if v["kind"] == "search" and v["blocked"]],
            "training_blocked": [v["name"] for v in res.values() if v["kind"] == "training" and v["blocked"]]}


def check_links(links, origin_host, max_links):
    seen, targets = set(), []
    for l in links:
        u = l["href"].split("#")[0]
        pu = urllib.parse.urlparse(u)
        if pu.scheme not in ("http", "https") or not pu.netloc.endswith(origin_host.replace("www.", "")):
            continue
        if re.search(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|mp4)$", pu.path, re.I):
            continue
        if u in seen:
            continue
        seen.add(u)
        targets.append(u)
    targets = targets[:max_links]

    def probe(u):
        r = http_get(u, method="GET", timeout=15, max_bytes=2000)
        return u, r["status"]

    broken = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for u, st in ex.map(probe, targets):
            if st is None or st >= 400:
                broken.append({"url": u, "status": st})
    return {"checked": len(targets), "broken": broken}


def run_local_lighthouse(url, form, out_dir):
    """Lighthouse on this machine (needs Node/npx). Returns parsed result or None."""
    if not shutil.which("npx"):
        return None
    chrome = find_chrome()
    out_path = os.path.join(out_dir, f"lighthouse-{form}.json")
    cmd = ["npx", "-y", "lighthouse@13", url, "--output=json", f"--output-path={out_path}", "--quiet",
           "--only-categories=performance,accessibility,best-practices,seo",
           "--chrome-flags=--headless=new --no-sandbox --disable-gpu", "--max-wait-for-load=45000"]
    if form == "desktop":
        cmd.append("--preset=desktop")
    env = dict(os.environ)
    if chrome:
        env["CHROME_PATH"] = chrome
    try:
        subprocess.run(cmd, check=True, timeout=240, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with open(out_path) as f:
            return parse_lighthouse(json.load(f))
    except Exception as e:  # noqa: BLE001
        log(f"local lighthouse {form} failed: {str(e)[:160]}")
        return None


def is_local_url(url):
    h = urllib.parse.urlparse(url).hostname or ""
    return h in ("localhost", "127.0.0.1", "::1") or h.endswith((".local", ".test", ".localhost"))


def speed_source(mode, url):
    """auto: PageSpeed API when PSI_API_KEY is set (no install, runs on Google's servers), else local Lighthouse
    when Node is installed, else PageSpeed without a key (rate-limited). Local URLs always use local Lighthouse."""
    if mode != "auto":
        return mode
    if is_local_url(url):
        return "local"
    if os.environ.get("PSI_API_KEY"):
        return "psi"
    return "local" if shutil.which("npx") else "psi"


def run_lighthouse(url, form, out_dir, mode="auto"):
    first = speed_source(mode, url)
    order = [first] + [m for m in ("psi", "local") if m != first and not (m == "psi" and is_local_url(url))]
    for m in order:
        res = run_psi(url, form, out_dir) if m == "psi" else run_local_lighthouse(url, form, out_dir)
        if res:
            return res
        log(f"{m} speed test for {form} unavailable, trying next source")
    return None


def run_psi(url, form, out_dir=None):
    api = ("https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(
        [("url", url), ("strategy", form), ("category", "performance"), ("category", "accessibility"),
         ("category", "best-practices"), ("category", "seo")]))
    key = os.environ.get("PSI_API_KEY")
    if key:
        api += "&key=" + key
    r = http_get(api, timeout=120, max_bytes=20_000_000)
    if r["status"] != 200:
        log(f"PSI {form} failed: {r['error']}")
        return None
    data = json.loads(r["body"])
    if out_dir and data.get("lighthouseResult"):  # same file shape as local Lighthouse (filmstrip etc.)
        with open(os.path.join(out_dir, f"lighthouse-{form}.json"), "w") as f:
            json.dump(data["lighthouseResult"], f)
    out = parse_lighthouse(data.get("lighthouseResult", {}))
    crux = data.get("loadingExperience", {}).get("metrics")
    if crux:
        out["field_data"] = {k: v.get("percentile") for k, v in crux.items()}
    out["source"] = "pagespeed-insights"
    return out


def parse_lighthouse(lh):
    cats = lh.get("categories", {})
    audits = lh.get("audits", {})

    def num(a):
        return (audits.get(a) or {}).get("numericValue")

    def sc(c):
        s = (cats.get(c) or {}).get("score")
        return round(s * 100) if s is not None else None

    opps = []
    for aid, a in audits.items():
        d = a.get("details") or {}
        ms = d.get("overallSavingsMs") or (a.get("metricSavings") or {}).get("LCP")
        by = d.get("overallSavingsBytes")
        if a.get("score") is not None and a["score"] < 0.9 and ((ms and ms >= 100) or (by and by >= 50_000)):
            opps.append({"id": aid, "title": a.get("title"), "savings_ms": round(ms or 0), "savings_bytes": round(by or 0),
                         "display": a.get("displayValue")})
    opps.sort(key=lambda o: (o["savings_ms"], o["savings_bytes"]), reverse=True)
    failed = [aid for aid in ("tap-targets", "font-size", "color-contrast", "image-alt", "link-name", "button-name",
                              "document-title", "meta-description", "is-crawlable", "http-status-code", "viewport",
                              "uses-responsive-images", "modern-image-formats", "offscreen-images", "unused-javascript",
                              "render-blocking-resources", "errors-in-console", "is-on-https", "inspector-issues")
              if (audits.get(aid) or {}).get("score") == 0]
    return {
        "source": "lighthouse",
        "performance": sc("performance"), "accessibility": sc("accessibility"),
        "best_practices": sc("best-practices"), "seo": sc("seo"),
        "lcp_ms": num("largest-contentful-paint"), "fcp_ms": num("first-contentful-paint"),
        "cls": num("cumulative-layout-shift"), "tbt_ms": num("total-blocking-time"),
        "si_ms": num("speed-index"), "tti_ms": num("interactive"),
        "total_bytes": num("total-byte-weight"),
        "lcp_element": ((((audits.get("largest-contentful-paint-element") or {}).get("details") or {}).get("items") or [{}])[0]
                        .get("items", [{}])[0].get("node", {}).get("snippet") if audits.get("largest-contentful-paint-element") else None),
        "opportunities": opps[:8],
        "failed_audits": failed,
    }


def detect(text, patterns):
    return {k: bool(re.search(p, text, re.I)) for k, p in patterns.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-lighthouse", action="store_true", help="same as --speed off")
    ap.add_argument("--speed", choices=["auto", "psi", "local", "off"], default="auto",
                    help="speed test source: auto (PSI_API_KEY → PageSpeed API, else local Lighthouse if Node, else PageSpeed keyless)")
    ap.add_argument("--max-links", type=int, default=25)
    a = ap.parse_args()

    url = normalize_url(a.url)
    out_dir = os.path.abspath(a.out)
    shots = os.path.join(out_dir, "screenshots")
    os.makedirs(shots, exist_ok=True)

    log(f"HTTP checks {url}")
    http, main_resp = check_http(url)
    if not http["status"] and url.startswith("https://") and "://www." not in url:
        alt = re.sub(r"^https://", "https://www.", url)
        log(f"HTTPS failed on bare domain ({(http.get('ssl_error') or http.get('error') or '')[:80]}); trying {alt}")
        http2, main2 = check_http(alt)
        if http2["status"]:
            http2["apex_ssl_error"] = http.get("ssl_error") or http.get("error")
            http, main_resp, url = http2, main2, alt
    if not http["status"] and url.startswith("https://"):
        alt = "http://" + url[len("https://"):]
        log("HTTPS failed, retrying over HTTP")
        http2, main2 = check_http(alt)
        if http2["status"]:
            http, main_resp, url = http2, main2, alt
            http["https"] = False
    if not http["status"] and "://www." not in url:
        alt = re.sub(r"^(https?://)", r"\1www.", url)
        log(f"unreachable, retrying {alt}")
        http2, main2 = check_http(alt)
        if http2["status"]:
            http, main_resp, url = http2, main2, alt
    if http["status"] and 300 <= http["status"] < 400:
        http["error"] = f"redirect loop or broken redirect (HTTP {http['status']})"
    if not http["status"] or http["status"] >= 500 or 300 <= http["status"] < 400:
        with open(os.path.join(out_dir, "audit.json"), "w") as f:
            json.dump({"url": a.url, "reachable": False, "error": http.get("error") or f"HTTP {http.get('status')}",
                       "audited_at": dt.datetime.now().isoformat(timespec="seconds"), "http": http}, f, indent=2)
        log(f"SITE UNREACHABLE: {http.get('error') or http.get('status')}. Stopping. (Dead site = strong pitch for a new one; confirm the URL first.)")
        sys.exit(2)
    final = http.get("final_url") or url
    log("robots / sitemap / llms.txt")
    files = check_files(final)

    log("browser pass (desktop + mobile)")
    try:
        br = run_browser(final, shots)
    except Exception as e:  # noqa: BLE001
        log(f"browser failed: {e}")
        br = {"desktop": None, "mobile": None, "console_errors": [], "mixed_content": [], "failed_requests": [],
              "page_bytes": 0, "request_count": 0, "load_ms": None, "error": str(e)[:300]}
    d = br.get("desktop") or {}
    m = br.get("mobile") or {}
    parked = re.search(r"(is parked free|this domain (is|may be) for sale|get this domain|buy this domain|domain parking|sedoparking|dan\.com/buy|hugedomains|parkingcrew|bodis\.com)", d.get("text", "")[:3000], re.I)
    if parked:
        with open(os.path.join(out_dir, "audit.json"), "w") as f:
            json.dump({"url": a.url, "reachable": False, "parked": True, "error": f"parked domain ({parked.group(0)})",
                       "audited_at": dt.datetime.now().isoformat(timespec="seconds"), "http": http}, f, indent=2)
        log(f"PARKED DOMAIN: '{parked.group(0)}'. Business has no live site here. Stopping.")
        sys.exit(2)
    err_page = re.search(r"\b(ERR_[A-Z_]+|DNS_PROBE_[A-Z_]+)\b", d.get("text", "")[:600])
    if err_page and (d.get("word_count") or 0) < 60:
        with open(os.path.join(out_dir, "audit.json"), "w") as f:
            json.dump({"url": a.url, "reachable": False, "error": f"browser error {err_page.group(1)}",
                       "audited_at": dt.datetime.now().isoformat(timespec="seconds"), "http": http}, f, indent=2)
        log(f"SITE BROKEN IN BROWSER: {err_page.group(1)}. Stopping.")
        sys.exit(2)

    raw_html = main_resp["body"].decode("utf-8", "ignore") if main_resp.get("body") else ""
    blob = raw_html + "\n" + "\n".join(d.get("scripts", [])) + "\n" + "\n".join(d.get("iframes", []))
    all_links = " ".join(l["href"] for l in d.get("links", []))
    text = d.get("text", "")
    link_text = " ".join(f"{l['text']} {l['href']}" for l in d.get("links", []))

    social = {}
    for k, pat in SOCIAL_PATTERNS.items():
        mm = re.search(r"https?://(www\.)?" + pat, all_links + " " + raw_html, re.I)
        social[k] = mm.group(0) if mm else None

    cms = [name for name, pat in CMS_SIGNS if re.search(pat, blob, re.I)]
    if d.get("generator"):
        cms.append(f"generator: {d['generator']}")

    ops = detect(text + "\n" + link_text, OPS_SIGNALS)
    ops["google_forms"] = ops["google_forms"] or bool(re.search(OPS_SIGNALS["google_forms"], blob, re.I))
    ops["pdf_catalog"] = ops["pdf_catalog"] or bool(re.search(r"href=\"[^\"]+(catalog|brochure|price)[^\"]*\.pdf", raw_html, re.I))
    legacy = []
    if d.get("jquery_version") and re.match(r"^1\.", d["jquery_version"]):
        legacy.append(f"jQuery {d['jquery_version']}")
    if d.get("has_tables_layout"):
        legacy.append("table-based layout")
    if http.get("powered_by") and re.search(r"PHP/5|PHP/7\.[0-3]|ASP\.NET", http["powered_by"]):
        legacy.append(http["powered_by"])
    yr = d.get("year_in_footer")
    if yr and yr.isdigit() and int(yr) < dt.date.today().year - 1:
        legacy.append(f"footer copyright {yr}")
    ops["legacy_stack"] = legacy

    trust = detect(text + "\n" + link_text, TRUST_SIGNALS)
    trust["contact_visible"] = bool(d.get("tel_links") or d.get("mailto_links") or re.search(r"\+?\d[\d\s\-]{8,}\d", text))

    nav = []
    host = urllib.parse.urlparse(final).hostname or ""
    for l in d.get("links", []):
        pu = urllib.parse.urlparse(l["href"])
        if pu.hostname and pu.hostname.replace("www.", "") == host.replace("www.", "") and l["text"] and len(nav) < 60:
            if not any(n["href"] == l["href"] for n in nav):
                nav.append(l)

    log("link check + AI assistant access")
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        f_links = ex.submit(check_links, d.get("links", []), host, a.max_links) if d else None
        f_ai = ex.submit(check_ai_bots, final)
        links = f_links.result() if f_links else {"checked": 0, "broken": []}
        try:
            ai_bots = f_ai.result()
        except Exception as e:  # noqa: BLE001
            ai_bots = {"error": str(e)[:200]}

    lh = {"mobile": None, "desktop": None}
    if not a.no_lighthouse and a.speed != "off":
        src = speed_source(a.speed, final)
        log(f"speed tests: mobile + desktop in parallel via {'PageSpeed Insights API' if src == 'psi' else 'local Lighthouse'} (30-90s)")
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            futs = {form: ex.submit(run_lighthouse, final, form, out_dir, a.speed) for form in ("mobile", "desktop")}
            lh = {form: f.result() for form, f in futs.items()}

    audit = {
        "url": a.url, "reachable": True, "final_url": final, "audited_at": dt.datetime.now().isoformat(timespec="seconds"),
        "http": http, "files": files,
        "lighthouse": lh,
        "html": {k: d.get(k) for k in ("title", "meta_desc", "robots_meta", "canonical", "lang", "viewport", "og",
                                       "twitter_card", "favicon", "h1s", "h2_count", "jsonld_types", "images_total",
                                       "images_missing_alt", "word_count", "jquery_version")},
        "cms": sorted(set(cms)),
        "page": {"load_ms": br.get("load_ms"), "request_count": br.get("request_count"), "page_bytes_hint": br.get("page_bytes"),
                 "console_errors": br.get("console_errors", [])[:15],
                 "mixed_content": (br.get("mixed_content", []) + [c for c in br.get("console_errors", []) if "Mixed Content" in c])[:15],
                 "failed_requests": br.get("failed_requests", [])[:15],
                 "mobile_horizontal_overflow": bool(m and m.get("scroll_width", 0) > m.get("inner_width", 0) + 5),
                 "browser_error": br.get("error")},
        "links": links,
        "ai_bots": ai_bots,
        "conversion": {"ctas_above_fold_desktop": d.get("ctas_above_fold", []), "ctas_above_fold_mobile": m.get("ctas_above_fold", []),
                       "forms": d.get("forms", 0), "email_inputs": d.get("inputs_email", 0),
                       "tel_links": d.get("tel_links", 0), "mailto_links": d.get("mailto_links", 0),
                       "whatsapp": d.get("whatsapp", False),
                       "chat_widget": (re.search(CHAT_WIDGETS, blob, re.I).group(0) if re.search(CHAT_WIDGETS, blob, re.I) else None)},
        "tracking": detect(blob, TRACKERS),
        "social": social,
        "trust": trust,
        "ops_signals": ops,
        "nav_links": nav,
        "screenshots": {k: f"screenshots/{k}.png" for k in ("desktop-fold", "desktop-full", "mobile-fold", "mobile-full")
                        if os.path.exists(os.path.join(shots, f"{k}.png"))},
    }
    with open(os.path.join(out_dir, "audit.json"), "w") as f:
        json.dump(audit, f, indent=2, default=str)
    with open(os.path.join(out_dir, "page_text.txt"), "w") as f:
        f.write(text)
    log(f"done -> {os.path.join(out_dir, 'audit.json')}")


if __name__ == "__main__":
    main()
