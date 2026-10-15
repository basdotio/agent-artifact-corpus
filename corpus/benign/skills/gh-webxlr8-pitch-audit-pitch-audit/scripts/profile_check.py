#!/usr/bin/env python3
"""Check a company profile before it is used for decks.

Usage:
    python3 profile_check.py [--profile pitch-profile]

FAIL (must fix): missing name/website/contact, logo for dark slides missing or too dark, catalog empty,
                 mapping points at offers that don't exist, deck text colours below WCAG AA.
WARN (should fix): TODO markers left, low-resolution logo, no booking link, no proof stats/clients,
                 prices on offers (double-check they are public), case studies without approved results.
Exit code 1 on any FAIL.
"""
import argparse
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import profile as P  # noqa: E402


def logo_stats(path):
    if path.lower().endswith(".svg"):
        return None
    im = np.asarray(Image.open(path).convert("RGBA"), dtype=float)
    a = im[..., 3] > 60
    if a.sum() < 30:
        return {"w": im.shape[1], "dark_share": 1.0}
    rgb = im[..., :3] / 255
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    return {"w": im.shape[1], "dark_share": float(((lum < 0.18) & a).sum()) / a.sum()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile")
    a = ap.parse_args()
    p = P.load_profile(a.profile)
    d, c, th = p["dir"], p["company"], p["theme"]
    fails, warns = [], []
    F, W = fails.append, warns.append

    for k in ("name", "website"):
        if not c.get(k):
            F(f"company.yaml: `{k}` is missing")
    ct = c.get("contact") or {}
    if not (ct.get("email") or ct.get("phone")):
        F("company.yaml: add contact.email or contact.phone (shown on the closing slide)")
    if not ct.get("booking_url"):
        W("company.yaml: no contact.booking_url, so the CTA button has no link (Calendly/cal.com etc. recommended)")

    logo = th.get("logo")
    if not logo or (not re.match(r"^https?:", logo) and not os.path.exists(logo)):
        F("brand.logo_on_dark is missing. Put a white/light logo in brand/ and set it in company.yaml")
    elif not re.match(r"^https?:", logo):
        st = logo_stats(logo)
        if st and st["dark_share"] > 0.15:
            F(f"brand.logo_on_dark looks dark ({st['dark_share']:.0%} dark pixels): it would vanish on dark slides. Use a white/light version")
        if st and st["w"] < 300:
            W(f"brand.logo_on_dark is only {st['w']} px wide; use ≥ 600 px or an SVG for sharp PDFs")

    v = th.get("vars", {})
    bg = v.get("--bg", "#0B0B0B")
    for name, need in (("--text", 7.0), ("--body", 4.5), ("--muted", 4.5), ("--accent", 4.5)):
        col = v.get(name)
        if col and col.startswith("#"):
            r = P.contrast(col, bg)
            if r < need:
                F(f"theme {name} {col} on {bg} = {r:.2f}:1 (needs {need}:1 for WCAG AA small text)")

    offers = {o.get("id"): o for o in p["catalog"].get("offers", []) or []}
    if not offers or any(str(k).startswith("TODO") for k in offers):
        F("catalog.yaml: add your real offers (ids without TODO)")
    for oid, o in offers.items():
        if not o.get("capabilities"):
            W(f"catalog.yaml: offer `{oid}` has no capabilities, so findings will never map to it")
        if o.get("price"):
            W(f"catalog.yaml: offer `{oid}` shows a price ({o['price']}). Make sure it is public and current")
        if o.get("logo") and not os.path.exists(P.abspath(d, o["logo"])):
            F(f"catalog.yaml: logo for `{oid}` not found: {o['logo']}")
    m = p["mapping"]
    for cap, oid in (m.get("capabilities") or {}).items():
        if cap not in P.CAPABILITIES:
            W(f"mapping.yaml: unknown capability `{cap}` (known: {', '.join(P.CAPABILITIES)})")
        if oid not in offers:
            F(f"mapping.yaml: capability `{cap}` points at unknown offer `{oid}`")
    for cap in P.CAPABILITIES:
        if cap not in (m.get("capabilities") or {}):
            W(f"mapping.yaml: capability `{cap}` is not mapped to any offer")
    for r in m.get("fit_rules", []) or []:
        if r.get("offer") not in offers:
            F(f"mapping.yaml: fit rule points at unknown offer `{r.get('offer')}`")

    pr = p["proof"]
    if not pr.get("stats"):
        W("proof.yaml: no stats. The closing slide's proof strip will be empty")
    if not pr.get("clients"):
        W("proof.yaml: no client names")
    if pr.get("case_studies") and not any(cs.get("result") for cs in pr["case_studies"]):
        W("proof.yaml: no case study has a real result yet. Add 2–3 approved numbers for stronger decks")

    todos = 0
    for f in ("company.yaml", "catalog.yaml", "mapping.yaml", "proof.yaml"):
        fp = os.path.join(d, f)
        if os.path.exists(fp):
            todos += len(re.findall(r"\bTODO\b", open(fp).read()))
    if todos:
        W(f"{todos} TODO markers left in the profile")

    print(f"Profile: {c.get('name')}  ({d})")
    print(f"  offers: {len(offers)}  products with logos: {len(p['products'])}  theme accent: {v.get('--accent')}")
    for x in fails:
        print("  FAIL " + x)
    for x in warns:
        print("  WARN " + x)
    if not fails:
        print("  OK: profile is usable" + (" (see warnings)" if warns else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
