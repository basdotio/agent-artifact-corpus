"""Company profile: who is pitching. Everything company-specific lives here, never in the skill code.

Profile folder (default ./pitch-profile, or $PITCH_PROFILE, or --profile):
    company.yaml   identity, contact, region, currency, language, brand files and colours
    catalog.yaml   offers (services + products) the deck can recommend
    mapping.yaml   which problems/industries lead to which offer, fit scores
    proof.yaml     stats, client names, case studies (only approved, real results)
    brand/         logos (light version for dark slides), product logos, optional fonts
    theme.json     optional hand-tuned theme; otherwise generated from company.yaml brand colours

Created by scripts/setup_profile.py <your-company-url>; checked by scripts/profile_check.py.
"""
import json
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, ".."))
DEFAULT_THEME = os.path.join(SKILL, "themes", "default.json")

# capability keys used by score.py findings; mapping.yaml maps each to an offer id
CAPABILITIES = ["web", "design", "app", "infra", "growth", "automation", "ops"]


def find_profile_dir(explicit=None, client_dir=None):
    cands = [explicit, os.environ.get("PITCH_PROFILE"), os.path.join(os.getcwd(), "pitch-profile")]
    if client_dir:  # clients/<slug> -> ../../pitch-profile
        cands.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(client_dir))), "pitch-profile"))
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "company.yaml")):
            return os.path.abspath(c)
    return None


def _yaml(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path) as f:
        return yaml.safe_load(f) or (default if default is not None else {})


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rel_lum(h):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted([rel_lum(a), rel_lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def readable_accent(accent, bg, need=4.5):
    """Lighten the brand accent just enough to pass WCAG AA as small text on the deck background."""
    c, t = accent, 0.0
    while contrast(c, bg) < need and t < 1:
        t += 0.04
        c = mix(accent, "#FFFFFF", t)
    return c


def google_fonts_url(families):
    fams = [f for f in families if f]
    if not fams:
        return None
    q = "&".join("family=" + f.replace(" ", "+") + ":wght@400;500;600;700;800" for f in dict.fromkeys(fams))
    return f"https://fonts.googleapis.com/css2?{q}&display=swap"


def theme_from_company(company, profile_dir):
    """Generate a deck theme from company.yaml brand settings (dark canvas, brand accent)."""
    with open(DEFAULT_THEME) as f:
        th = json.load(f)
    b = company.get("brand", {}) or {}
    v = th["vars"]
    bg = b.get("background") or v["--bg"]
    accent = b.get("accent") or v["--accent"]
    acc = readable_accent(accent, bg)
    # Glow: bright accents (teal, yellow, lime) are darkened so the glow never washes out small text.
    glow = accent
    while rel_lum(glow) > 0.22:
        glow = mix(glow, "#000000", 0.08)
    # Secondary text: lighten until it passes WCAG AA on the brightest glow area (glow at ~55% over bg).
    hot_bg = mix(bg, glow, 0.55)
    muted, body = v["--muted"], v["--body"]
    while contrast(muted, hot_bg) < 4.6 and rel_lum(muted) < 0.9:
        muted = mix(muted, "#FFFFFF", 0.06)
    while contrast(body, hot_bg) < 4.6 and rel_lum(body) < 0.9:
        body = mix(body, "#FFFFFF", 0.06)
    v.update({"--muted": muted, "--body": body})
    v.update({
        "--bg": bg, "--bg-2": b.get("background_2") or mix(bg, "#FFFFFF", .05),
        "--accent": acc, "--accent-rgb": " ".join(str(x) for x in hex_to_rgb(acc)),
        "--accent-2": b.get("accent_2") or mix(acc, "#FFFFFF", .3),
        "--num-solid": mix(acc, "#FFFFFF", .1),
        "--glow-a-rgb": " ".join(str(x) for x in hex_to_rgb(glow)),
        "--glow-b-rgb": " ".join(str(x) for x in hex_to_rgb(b.get("glow_2") or mix(glow, "#000000", .55))),
        "--accent-ink": "#0B0B0B" if rel_lum(acc) > 0.35 else "#FFFFFF",
    })
    head, body = b.get("heading_font"), b.get("body_font")
    if head or body:
        url = google_fonts_url([head, body])
        if url:
            th["fonts"] = [url]
        if head:
            v["--head"] = f'"{head}", system-ui, sans-serif'
        if body:
            v["--sans"] = f'"{body}", system-ui, sans-serif'
    if b.get("heading_weight"):
        v["--head-weight"] = str(b["heading_weight"])
    if b.get("corner_radius") is not None:
        v["--radius-card"] = f'{b["corner_radius"]}px'
    th["name"] = company.get("id") or "company"
    th["label"] = company.get("name", "")
    th["generated_from"] = "company.yaml brand"
    return th


LIGHT = {  # paper-like editorial base; accent/status colours are darkened per brand to pass WCAG AA
    "--bg": "#F6F4EF", "--bg-2": "#FFFFFF", "--text": "#15171B", "--body": "#3B4048", "--muted": "#5B626C",
    "--grid": "rgba(20,22,26,.035)", "--line": "rgba(20,22,26,.12)", "--good": "#166534", "--warn": "#854D0E", "--bad": "#991B1B",
    "--head-track": "-0.02em", "--eyebrow-track": ".2em",
    "--photo-grade": "saturate(.9) contrast(1.02) brightness(1.02)",
}


def light_theme(company, base):
    """Light variant of a theme for light styles: same brand, paper background, accent darkened to pass AA."""
    th = json.loads(json.dumps(base))
    v = th["vars"]
    accent = (company.get("brand") or {}).get("accent") or v.get("--accent", "#3355DD")
    v.update(LIGHT)
    acc = accent
    while contrast(acc, "#E6E3DC") < 4.6:  # pass on paper AND on tinted cards/chips
        acc = mix(acc, "#000000", 0.06)
    v.update({"--accent": acc, "--accent-rgb": " ".join(str(x) for x in hex_to_rgb(acc)), "--accent-2": mix(acc, "#FFFFFF", .25),
              "--accent-ink": "#FFFFFF" if rel_lum(acc) < 0.4 else "#111111", "--num-solid": acc,
              "--glow-a-rgb": " ".join(str(x) for x in hex_to_rgb(mix(accent, "#FFFFFF", .55))),
              "--glow-b-rgb": " ".join(str(x) for x in hex_to_rgb(mix(accent, "#FFFFFF", .8)))})
    th["mode"] = "light"
    return th


def load_profile(explicit=None, client_dir=None, required=True, mode="dark"):
    d = find_profile_dir(explicit, client_dir)
    if not d:
        if required:
            raise SystemExit("No company profile found. Run: python3 scripts/setup_profile.py <your-company-url>  "
                             "(creates ./pitch-profile), or set PITCH_PROFILE.")
        return None
    company = _yaml(os.path.join(d, "company.yaml"))
    p = {"dir": d, "company": company, "catalog": _yaml(os.path.join(d, "catalog.yaml"), {"offers": []}),
         "mapping": _yaml(os.path.join(d, "mapping.yaml")), "proof": _yaml(os.path.join(d, "proof.yaml"))}
    tp = os.path.join(d, "theme.json" if mode == "dark" else f"theme.{mode}.json")
    if os.path.exists(tp):
        with open(tp) as f:
            th = json.load(f)
    else:
        th = theme_from_company(company, d)
    if mode == "light" and not os.path.exists(tp):
        th = light_theme(company, th)
    b = company.get("brand", {}) or {}
    logo = (b.get("logo") or b.get("logo_on_dark")) if mode == "light" else (b.get("logo_on_dark") or b.get("logo"))
    th["logo"] = abspath(d, logo) if logo else None
    th["logo_height"] = b.get("logo_height", th.get("logo_height", 30))
    th["label"] = company.get("name", th.get("label", ""))
    c = company.get("contact", {}) or {}
    th["contact"] = {k: v for k, v in {
        "website": strip_scheme(company.get("website")), "email": c.get("email"), "phone": c.get("phone"),
        "address": c.get("address_short") or (c.get("address") if c.get("address") and len(c["address"]) <= 42 else None), "booking": strip_scheme(c.get("booking_url")),
        "tagline": company.get("tagline")}.items() if v}
    if b.get("fonts_css"):  # local brand fonts (from --assets) loaded via @font-face
        import pathlib
        th.setdefault("fonts", []).append(pathlib.Path(abspath(d, b["fonts_css"])).as_uri())
    p["theme"] = th
    p["products"] = products(p)
    return p


def strip_scheme(u):
    return re.sub(r"^https?://(www\.)?", "", u).rstrip("/") if u else u


def abspath(base, path):
    return path if not path or os.path.isabs(path) or re.match(r"^https?:", path) else os.path.normpath(os.path.join(base, path))


def products(p):
    """Offers that are named products (shown with their own logo badge in the deck)."""
    out = {}
    for o in p["catalog"].get("offers", []) or []:
        if o.get("type") == "product" or o.get("logo"):
            out[o["id"]] = {"id": o["id"], "label": o.get("name", o["id"]),
                            "aliases": [a.lower() for a in ([o.get("name", "")] + (o.get("aliases") or [])) if a],
                            "logo": abspath(p["dir"], o.get("logo")) if o.get("logo") else None,
                            "logo_height": o.get("logo_height", 18)}
    return out


def offer(p, oid):
    return next((o for o in p["catalog"].get("offers", []) if o.get("id") == oid), None)
