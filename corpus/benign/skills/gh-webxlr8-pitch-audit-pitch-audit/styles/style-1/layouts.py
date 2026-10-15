"""Style 1: Neon Studio. render(deck, ctx) -> full HTML document.

Layouts: cover, statement, stats, scorecard, finding, process, cards, solutions, tiers, compare, proof, center, contact.
Field reference: references/deck-data-schema.md
"""
import html
import os
import re

ICONS = {
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "send": '<path d="M22 2 11 13"/><path d="m22 2-7 20-4-9-9-4z"/>',
    "message": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22z"/>',
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "zap": '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 16v-5"/><path d="M12 16V8"/><path d="M17 16v-9"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "phone": '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M12 18h.01"/>',
    "cpu": '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    "cart": '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    "cloud": '<path d="M17.5 19H9a7 7 0 1 1 6.7-9h1.8a4.5 4.5 0 1 1 0 9z"/>',
    "book": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "palette": '<circle cx="13.5" cy="6.5" r="1.5"/><circle cx="17.5" cy="10.5" r="1.5"/><circle cx="8.5" cy="7.5" r="1.5"/><circle cx="6.5" cy="12.5" r="1.5"/><path d="M12 2a10 10 0 0 0 0 20 2 2 0 0 0 2-2 2 2 0 0 1 2-2h2a4 4 0 0 0 4-4c0-5.5-4.5-10-10-10z"/>',
    "truck": '<path d="M1 3h15v13H1z"/><path d="M16 8h4l3 3v5h-7z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
    "box": '<path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "alert": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "bot": '<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><path d="M8 16h.01M16 16h.01"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
}

ARROW = '<svg viewBox="0 0 30 14"><path d="M0 7h22" style="stroke:var(--accent)" stroke-width="3"/><path d="M20 1l8 6-8 6z" style="fill:var(--accent)"/></svg>'


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def fmt(s):
    """Escape, then *green*, **bold**, and \\n -> <br>."""
    t = esc(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    t = re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', t, flags=re.S)
    return t.replace("\n", "<br>")


def icon(name, cls="icon"):
    p = ICONS.get(name or "", ICONS["check"])
    return f'<svg class="{cls}" viewBox="0 0 24 24">{p}</svg>'


def chips(items):
    if not items:
        return ""
    out = []
    for c in items:
        if isinstance(c, dict):
            cls = "chip" + (" active" if c.get("active") else "") + (f" sev-{c['severity']}" if c.get("severity") else "")
            out.append(f'<span class="{cls}">{fmt(c.get("text"))}</span>')
        else:
            out.append(f'<span class="chip">{fmt(c)}</span>')
    return f'<div class="chips">{"".join(out)}</div>'


def eyebrow(s, center=False, live=False):
    if not s:
        return ""
    badge = '<span class="badge-live">● LIVE</span>' if live else ""
    return f'<div class="eyebrow{" center" if center else ""}">{badge}{fmt(s)}</div>'


def grade_cls(g):
    g = (g or "").lower()
    return "healthy" if g.startswith("health") else ("needs" if g.startswith("need") else "critical")


def score_cls(v):
    return "healthy" if v >= 80 else ("needs" if v >= 60 else "critical")


class R:
    def __init__(self, deck, ctx):
        self.d, self.ctx = deck, ctx
        self.total = len(deck.get("slides", []))
        th = ctx.get("theme") or {}
        self.theme = th
        self.products = ctx.get("products") or {}      # from the company profile catalog
        self.logo = self.asset_uri(th.get("logo")) if th.get("logo") else ""
        self.logo_h = th.get("logo_height", 30)
        self.logo_alt = esc(th.get("label", ""))
        self.parent = ctx.get("parent")                 # {"label", "logo"} when the deck uses a product's own theme
        self.light = th.get("mode") == "light"

    def prepared_for(self):
        """'Prepared for <their logo>' on the cover, using the prospect's own logo (light version)."""
        cl = (self.d.get("client") or {})
        lg = (cl.get("logo") or cl.get("logo_on_dark")) if self.light else (cl.get("logo_on_dark") or cl.get("logo"))
        if not lg:
            return ""
        return (f'<div class="prepared"><span>Prepared for</span><img src="{esc(self.img(lg))}" alt="{esc(cl.get("name", ""))} logo"></div>')

    def asset_uri(self, path):
        return self.ctx["theme_asset"](path)

    # ---- products appear by logo + name, in the deck's colours (one deck = one brand)
    def brand_of(self, text):
        """Product id whose name/alias appears in text (longest alias wins)."""
        t = (text or "").lower()
        best, blen = None, 0
        for pid, pr in self.products.items():
            for a in pr.get("aliases", []):
                if a and a in t and len(a) > blen:
                    best, blen = pid, len(a)
        return best

    def product_logo(self, pid, h=None):
        pr = self.products.get(pid)
        if not pr or not pr.get("logo"):
            return ""
        return (f'<img class="product-logo{" on-light" if self.light else ""}" alt="{esc(pr.get("label", pid))}" src="{self.asset_uri(pr["logo"])}" '
                f'style="height:{h or pr.get("logo_height", 18)}px">')

    def card_badge(self, brand_text):
        """Tag for a card/offer: product logo + remaining sub-label for products, plain tag for services."""
        pid = self.brand_of(brand_text)
        logo = self.product_logo(pid) if pid else ""
        if not logo:
            return f'<span class="brand-tag">{fmt(brand_text)}</span>'
        rest = brand_text or ""
        for a in sorted(self.products[pid]["aliases"], key=len):  # shortest alias = the brand word the logo replaces
            rest = re.sub(r"(?i)" + re.escape(a) + r"\s*[·:-]?\s*", "", rest, count=1)
            if rest != brand_text:
                break
        rest = rest.strip(" ·:-")
        sub = f'<span class="brand-tag">{fmt(rest)}</span>' if rest else ""
        return f'<span style="display:inline-flex;align-items:center;gap:10px">{logo}{sub}</span>'

    def credit(self):
        """'A <Company> company' lockup, only when a deck is rendered in a product's own theme."""
        if not self.parent or not self.parent.get("logo"):
            return ""
        return (f'<span>A</span><img alt="{esc(self.parent.get("label", ""))}" src="{self.asset_uri(self.parent["logo"])}" '
                f'style="height:20px"><span>company</span>')

    @staticmethod
    def fit_title(title, width, max_size):
        """Largest headline size (px) at which the longest line fits `width` (≈0.56em per char for heavy grotesks)."""
        lines = [re.sub(r"[*]", "", l) for l in (title or "").split("\n")]
        longest = max((len(l) for l in lines), default=1) or 1
        return int(max(40, min(max_size, width / (0.62 * longest))))

    def img(self, src):
        if not src:
            return ""
        if re.match(r"^(https?:|data:|file:)", src):
            return src
        return self.ctx["client_file"](src)

    def frame(self, image, w, h, style=""):
        """image: {src, frame: browser|phone|plain, label}"""
        if not image or not image.get("src"):
            return ""
        src = esc(self.img(image["src"]))
        kind = image.get("frame", "browser")
        alt = esc(image.get("alt") or image.get("caption") or (f'Screenshot of {image["label"]}' if image.get("label") else "Website screenshot"))
        if kind == "phone":
            return (f'<div class="phone" style="width:{w}px;height:{h}px;{style}"><div class="screen">'
                    f'<img class="shot" src="{src}" alt="{alt}"></div></div>')
        if kind == "plain":
            return f'<img src="{src}" alt="{alt}" style="width:{w}px;height:{h}px;object-fit:cover;border-radius:14px;{style}">'
        label = esc(image.get("label", ""))
        return (f'<div class="browser" style="width:{w}px;height:{h}px;{style}"><div class="bar"><i></i><i></i><i></i>'
                f'<span>{label}</span></div><img class="shot" src="{src}" alt="{alt}" style="height:{h - 30}px"></div>')

    def chrome(self, i, s):
        parts = [f'<img class="logo" alt="{self.logo_alt}" src="{self.logo}" style="height:{self.logo_h}px">'] if not s.get("hide_logo") else []
        if not s.get("hide_counter"):
            parts.append(f'<div class="counter"><b>{i + 1:02d}</b> / {self.total:02d}</div>')
        return "".join(parts)

    def photo_layer(self, ph):
        """ph: {src, mode: full|right|left, pos: CSS background-position, dim: 0-1}"""
        if not ph or not ph.get("src"):
            return ""
        if not re.match(r"^(https?|data|file):", ph["src"]) and not os.path.exists(os.path.join(self.ctx["client_dir"], ph["src"])):
            return ""  # photo missing: the slide falls back to the theme's glow + grid background
        src = esc(self.img(ph["src"]))
        mode = ph.get("mode", "full")
        pos = esc(ph.get("pos", "center"))
        return (f'<div class="bg-photo mode-{esc(mode)}" style="--dim:{ph.get("dim", .55)}">'
                f'<div class="ph" style="background-image:url(\'{src}\');background-position:{pos}"></div></div>')

    def wrap(self, i, s, inner, cls=""):
        glow = s.get("glow", "")
        ph = self.photo_layer(s.get("photo"))
        return (f'<section class="slide {cls} {("glow-" + glow) if glow else ""}">'
                f'{ph}<div class="bg-glow"></div><div class="bg-grid"></div>{self.chrome(i, s)}{inner}</section>')

    def tiles(self, tiles, cols=None):
        """Big-number tiles: [{value, label}] (max 4). Visual replacement for a paragraph of facts."""
        if not tiles:
            return ""
        cells = "".join(f'<div class="tile"><div class="bignum" style="font-size:52px">{fmt(t.get("value"))}</div>'
                        f'<div class="tile-l">{fmt(t.get("label"))}</div></div>' for t in tiles[:4])
        return f'<div class="tiles" style="grid-template-columns:repeat({cols or min(len(tiles), 4)},1fr)">{cells}</div>'

    def ring(self, ov, size=220):
        gc = score_cls(ov)
        color = "var(--accent)"  # hero score in brand colour: reads as opportunity; severity shown by tag + bars
        circ = 2 * 3.14159 * 130
        return (f'<div class="ring" style="width:{size}px;height:{size}px"><svg viewBox="0 0 300 300">'
                f'<circle cx="150" cy="150" r="130" stroke="rgba(255,255,255,.08)" stroke-width="18" fill="none"/>'
                f'<circle cx="150" cy="150" r="130" stroke-width="18" fill="none" stroke-linecap="round" '
                f'stroke-dasharray="{circ * ov / 100:.1f} {circ:.1f}" style="stroke:{color}"/></svg>'
                f'<div class="val"><div class="bignum" style="font-size:{round(size * .38)}px">{ov}</div>'
                f'<div class="of" style="font-size:{round(size * .09)}px">/ 100</div></div></div>'), gc

    # ---------------- layouts
    def score_gaps(self, i, s):
        """Score ring + mini bars (left), the 3 gaps that matter (right). Replaces separate impact + scorecard slides."""
        ov = int(s.get("overall", 0))
        ring, gc = self.ring(ov, 210)
        grade = s.get("grade") or {"healthy": "Strong", "needs": "Room to grow", "critical": "Needs attention"}[gc]
        bars = "".join(f'<div class="mbar"><span class="n">{fmt(c.get("label"))}</span><span class="t"><i class="fill {score_cls(int(c.get("score", 0)))}" '
                       f'style="width:{max(4, int(c.get("score", 0)))}%"></i></span><b>{int(c.get("score", 0))}</b></div>'
                       for c in s.get("categories", [])[:8])
        gaps = "".join(f'<div class="gap"><div class="gi">{icon(g.get("icon", "alert"))}</div><div>'
                       f'<div class="card-title" style="font-size:24px">{fmt(g.get("title"))}</div>'
                       f'<div class="card-body" style="font-size:16px;margin-top:4px">{fmt(g.get("body"))}</div></div></div>'
                       for g in s.get("gaps", [])[:3])
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:104px;width:1100px">
            {eyebrow(s.get("eyebrow", "Your scorecard"))}
            <div class="h-md" style="margin-top:18px">{fmt(s.get("title"))}</div>
          </div>
          <div style="position:absolute;left:var(--mx);top:262px;width:430px">
            <div style="display:flex;align-items:center;gap:26px">{ring}
              <div><span class="grade-tag {gc}">{esc(grade)}</span>
              <div class="caption" style="margin-top:12px;font-size:14px;max-width:170px">{fmt(s.get("ring_caption", "60+ checks across 8 areas"))}</div></div></div>
            <div class="mbars">{bars}</div>
          </div>
          <div style="position:absolute;left:600px;right:var(--mx);top:262px;bottom:84px;display:flex;flex-direction:column;gap:14px">{gaps}</div>
        </div>"""
        return self.wrap(i, s, inner)

    def portal_mock(self, m):
        """HTML mock of the product (no stock image can show their future system)."""
        rows = "".join(f'<div class="pm-row"><span class="pm-id">{fmt(r.get("id"))}</span><span class="pm-lane">{fmt(r.get("lane"))}</span>'
                       f'<span class="pm-pill {esc(r.get("tone", "go"))}">{fmt(r.get("status"))}</span><span class="pm-eta">{fmt(r.get("eta"))}</span></div>'
                       for r in m.get("rows", [])[:4])
        alert = (f'<div class="pm-alert">{icon("alert")}<div><b>{fmt(m["alert"]["title"])}</b><span>{fmt(m["alert"]["body"])}</span></div></div>'
                 if m.get("alert") else "")
        kpis = "".join(f'<div class="pm-kpi"><b>{fmt(k.get("value"))}</b><span>{fmt(k.get("label"))}</span></div>' for k in m.get("kpis", [])[:3])
        return f"""<div class="pm"><div class="pm-bar"><i></i><i></i><i></i><span>{fmt(m.get("url", "portal"))}</span></div>
          <div class="pm-body"><div class="pm-head"><div class="pm-title">{fmt(m.get("title"))}</div><div class="pm-user">{fmt(m.get("user", ""))}</div></div>
          {f'<div class="pm-kpis">{kpis}</div>' if kpis else ""}
          <div class="pm-table">{rows}</div>{alert}</div></div>"""

    def cover(self, i, s):
        img = None if self.photo_layer(s.get("photo")) else s.get("image")  # missing photo -> show the website mockup
        right = ""
        if img:
            right = (f'<div style="position:absolute;right:-150px;top:120px;z-index:2;transform:perspective(1600px) rotateY(-16deg) rotateX(4deg);opacity:.92">'
                     f'{self.frame(img, 640, 420)}</div>')
            if s.get("image_mobile"):
                right += (f'<div style="position:absolute;right:390px;top:270px;z-index:3;transform:perspective(1600px) rotateY(-10deg)">'
                          f'{self.frame({"src": s["image_mobile"], "frame": "phone"}, 166, 340)}</div>')
        credit = self.credit()
        footer = fmt(s.get("footer", ""))
        if credit:
            footer = f'{footer}<span style="opacity:.5">·</span>{credit}' if footer else credit
        inner = f"""
        <div class="content" style="padding-top:0">
          <img alt="{self.logo_alt}" src="{self.logo}" style="position:absolute;left:var(--mx);top:52px;height:{round(self.logo_h * 1.5)}px">
          <div style="position:absolute;left:var(--mx);top:180px;width:700px;z-index:4">
            {eyebrow(s.get("eyebrow"))}
            <div class="h-xl" style="margin-top:28px;font-size:{s.get('title_size') or self.fit_title(s.get("title"), 620, 88)}px">{fmt(s.get("title"))}</div>
            <div class="lead" style="margin-top:28px;font-size:24px">{fmt(s.get("subtitle", ""))}</div>
            {self.prepared_for()}
          </div>
          <div class="footer-note" style="bottom:46px;z-index:6;white-space:nowrap;letter-spacing:.16em;gap:10px">{footer}</div>
        </div>{right}"""
        s = dict(s, hide_logo=True, hide_counter=True)
        return self.wrap(i, s, inner, "glow-strong" if not s.get("glow") else "")

    def statement(self, i, s):
        img = s.get("image")
        side = s.get("image_side", "right")
        text_w = s.get("text_width") or (600 if img or (s.get("photo") or {}).get("mode") == "right" else 1000)
        text_left = "var(--mx)" if side != "left" else "660px"
        media = ""
        if img:
            kind = img.get("frame", "browser")
            if kind == "phone":
                pos = "right:150px" if side != "left" else "left:180px"
                media = f'<div style="position:absolute;{pos};top:95px;z-index:2">{self.frame(img, 270, 560)}</div>'
            else:
                pos = "right:-40px" if side != "left" else "left:-40px"
                media = f'<div style="position:absolute;{pos};top:140px;z-index:2">{self.frame(img, 600, 440)}</div>'
        top = s.get("top", 0) or 0
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:{text_left};top:{96 + top}px;bottom:84px;width:{text_w}px;display:flex;flex-direction:column;justify-content:center">
            {eyebrow(s.get("eyebrow"), live=s.get("live", False))}
            <div class="{s.get('size', 'h-lg')}" style="margin-top:26px">{fmt(s.get("title"))}</div>
            {f'<div class="lead{"" if img else " wide"}" style="margin-top:26px">{fmt(s.get("body"))}</div>' if s.get("body") else ""}
            {f'<div style="margin-top:30px">{chips(s.get("chips"))}</div>' if s.get("chips") else ""}
            {self.tiles(s.get("tiles"), s.get("tile_cols"))}
            {f'<div class="caption" style="margin-top:22px">{fmt(s.get("footnote"))}</div>' if s.get("footnote") else ""}
          </div>
        </div>{media}"""
        return self.wrap(i, s, inner)

    def stats(self, i, s):
        st = s.get("stats", [])[:4]
        cols = " ".join(["1fr"] * max(1, len(st)))
        cells = "".join(f'<div class="stat"><div class="bignum" style="font-size:{s.get("num_size", 112)}px">{fmt(x.get("value"))}</div>'
                        f'<div class="label">{fmt(x.get("label"))}</div></div>' for x in st)
        group = ""
        if s.get("group_label"):
            group = f'<div class="eyebrow" style="color:var(--muted);margin-bottom:26px">{fmt(s["group_label"])}</div>'
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:112px;width:1100px">
            {eyebrow(s.get("eyebrow"))}
            <div class="h-md" style="margin-top:24px">{fmt(s.get("title"))}</div>
            {f'<div class="lead wide" style="margin-top:22px">{fmt(s.get("body"))}</div>' if s.get("body") else ""}
          </div>
          <div style="position:absolute;left:var(--mx);right:var(--mx);bottom:92px">
            {group}
            <div class="stat-row" style="grid-template-columns:{cols}">{cells}</div>
          </div>
        </div>"""
        return self.wrap(i, s, inner)

    def scorecard(self, i, s):
        ov = int(s.get("overall", 0))
        circ = 2 * 3.14159 * 130
        gc = score_cls(ov)
        color = {"healthy": "var(--good)", "needs": "var(--warn)", "critical": "var(--bad)"}[gc]
        rows = ""
        for c in s.get("categories", [])[:8]:
            v = int(c.get("score", 0))
            rows += (f'<div class="bar-row"><div class="name">{fmt(c.get("label"))}</div>'
                     f'<div class="track"><div class="fill {score_cls(v)}" style="width:{max(3, v)}%"></div></div>'
                     f'<div class="score">{v}</div></div>')
        grade = s.get("grade") or {"healthy": "Strong", "needs": "Room to grow", "critical": "Needs attention"}[gc]
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:112px;width:1100px">
            {eyebrow(s.get("eyebrow", "Your Scorecard"))}
            <div class="h-md" style="margin-top:22px">{fmt(s.get("title"))}</div>
          </div>
          <div style="position:absolute;left:var(--mx);top:262px;display:flex;flex-direction:column;align-items:center;gap:16px">
            <div class="ring" style="width:270px;height:270px">
              <svg viewBox="0 0 300 300"><circle cx="150" cy="150" r="130" stroke="rgba(255,255,255,.08)" stroke-width="16" fill="none"/>
              <circle cx="150" cy="150" r="130" stroke-width="16" fill="none" stroke-linecap="round"
                stroke-dasharray="{circ * ov / 100:.1f} {circ:.1f}" style="stroke:{color};filter:drop-shadow(0 0 10px color-mix(in srgb, {color} 55%, transparent))"/></svg>
              <div class="val"><div class="bignum" style="font-size:104px">{ov}</div><div class="of">/ 100</div></div>
            </div>
            <span class="grade-tag {gc}">{esc(grade)}</span>
          </div>
          <div class="bars" style="position:absolute;left:470px;right:var(--mx);top:272px">{rows}</div>
          {f'<div class="caption" style="position:absolute;left:var(--mx);bottom:36px;max-width:860px">{fmt(s.get("footnote"))}</div>' if s.get("footnote") else ""}
        </div>"""
        return self.wrap(i, s, inner)

    def filmstrip_html(self, fs):
        frames = fs.get("frames", [])[:6]
        hot = fs.get("highlight")
        cells = ""
        for n, f in enumerate(frames):
            on = (hot is not None and n == hot)
            cells += (f'<div class="fs-frame{" on" if on else ""}"><div class="fs-shot"><img src="{esc(self.img(f["src"]))}" alt="{esc(f.get("alt") or ("Page at " + str(f.get("label", ""))))}"></div>'
                      f'<div class="fs-t">{fmt(f.get("label", ""))}</div></div>')
        cap = f'<div class="caption" style="margin-top:14px;font-size:13px">{fmt(fs.get("caption"))}</div>' if fs.get("caption") else ""
        return f'<div class="filmstrip" style="--n:{len(frames)}">{cells}</div>{cap}'

    def finding(self, i, s):
        img = s.get("image")
        media = ""
        if s.get("filmstrip"):
            img = {"inset": True, "size": "large"}  # text column sized like a large inset
            media = f'<div style="position:absolute;right:var(--mx);top:150px;width:600px;z-index:2">{self.filmstrip_html(s["filmstrip"])}</div>'
        elif img:
            if img.get("frame") == "phone":
                media = f'<div style="position:absolute;right:120px;top:92px;z-index:2">{self.frame(img, 270, 560)}</div>'
            elif img.get("inset"):
                cap = f'<div class="caption" style="margin-top:12px;font-size:13px;letter-spacing:.04em">{fmt(img["caption"])}</div>' if img.get("caption") else ""
                big = img.get("size") == "large"
                w, h, t = (600, 440, 140) if big else (480, 366, 170)
                media = (f'<div style="position:absolute;right:var(--mx);top:{t}px;z-index:2;width:{w}px">'
                         f'{self.frame(img, w, h)}{cap}</div>')
            else:
                media = f'<div style="position:absolute;right:-30px;top:150px;z-index:2">{self.frame(img, 560, 420)}</div>'
        metric = ""
        if s.get("metric"):
            m = s["metric"]
            metric = (f'<div style="display:flex;align-items:flex-end;gap:16px;margin-top:26px">'
                      f'<div class="bignum" style="font-size:84px">{fmt(m.get("value"))}</div>'
                      f'<div class="small" style="padding-bottom:12px;max-width:240px">{fmt(m.get("label"))}</div></div>')
        ev = ""
        if s.get("evidence"):
            ev = '<ul class="evidence" style="margin-top:24px">' + "".join(f"<li><span>{fmt(e)}</span></li>" for e in s["evidence"][:3]) + "</ul>"
        impact = ""
        if s.get("impact"):
            impact = f'<div class="panel" style="margin-top:24px"><div class="k">Business impact</div><div class="v">{fmt(s["impact"])}</div></div>'
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:118px;width:{((470 if img.get("size") == "large" else 580) if img.get("inset") else 600) if img else 1000}px">
            {eyebrow(s.get("eyebrow"))}
            <div class="{s.get('size', 'h-md')}" style="margin-top:22px;{f'font-size:{self.fit_title(s.get("title"), 470, 56)}px' if (img and img.get("size") == "large") or s.get("filmstrip") else ''}">{fmt(s.get("title"))}</div>
            {f'<div class="lead" style="margin-top:18px">{fmt(s.get("body"))}</div>' if s.get("body") else ""}
            {metric}{ev}{impact}
            {f'<div style="margin-top:22px">{chips(s.get("chips"))}</div>' if s.get("chips") else ""}
          </div>
        </div>{media}"""
        return self.wrap(i, s, inner)

    def process(self, i, s):
        steps = s.get("steps", [])[:5]
        hot = s.get("highlight", len(steps) - 1)
        cells = []
        for n, st in enumerate(steps):
            if n:
                cells.append(f'<div class="arrow">{ARROW}</div>')
            num = st.get("num", f"{n + 1:02d}")
            ic = f'{icon(st["icon"])}' if st.get("icon") else f'<div class="num-outline">{esc(num)}</div>'
            body = f'<div class="card-body" style="font-size:16px">{fmt(st.get("body"))}</div>' if st.get("body") else ""
            cells.append(f'<div class="card{" hot" if n == hot else ""}">{ic}<div class="card-title">{fmt(st.get("title"))}</div>{body}</div>')
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:112px;width:1100px">
            {eyebrow(s.get("eyebrow"))}
            <div class="h-md" style="margin-top:22px">{fmt(s.get("title"))}</div>
          </div>
          <div class="flow" style="position:absolute;left:var(--mx);right:var(--mx);top:330px">{"".join(cells)}</div>
          {f'<div class="lead wide" style="position:absolute;left:var(--mx);bottom:92px;font-size:20px;color:var(--muted)">{fmt(s.get("footnote"))}</div>' if s.get("footnote") else ""}
        </div>"""
        return self.wrap(i, s, inner)

    def cards(self, i, s):
        cs = s.get("cards", [])[:6]
        cols = s.get("columns") or (3 if len(cs) in (3, 5, 6) else 2 if len(cs) in (2, 4) else 1)
        hot = s.get("highlight", -1)
        cells = ""
        for n, c in enumerate(cs):
            head = f'<div style="display:flex;align-items:center;gap:14px">{icon(c["icon"]) if c.get("icon") else ""}<div class="card-title" style="font-size:{c.get("title_size", 26)}px">{fmt(c.get("title"))}</div></div>'
            tag = f'<div class="card-tag" style="margin-bottom:12px">{fmt(c["tag"])}</div>' if c.get("tag") else ""
            body = f'<div class="card-body" style="margin-top:10px">{fmt(c["body"])}</div>' if c.get("body") else ""
            cst = ""
            if c.get("product"):
                tag = f'<div style="margin-bottom:12px">{self.card_badge(c["product"])}</div>'
            cells += f'<div class="card{" hot" if n == hot else ""}" style="padding:24px 26px;{cst}">{tag}{head}{body}</div>'
        dense = len(cs) > 4
        if not dense:
            cells = (cells.replace('padding:24px 26px;', 'padding:30px 30px;').replace('class="card-body" style="margin-top:10px"', 'class="card-body" style="margin-top:12px;font-size:20px"')
                     .replace('font-size:26px">', 'font-size:30px">'))
        if dense:
            cells = cells.replace('padding:24px 26px;', 'padding:18px 22px;').replace('margin-top:10px">', 'margin-top:6px">')
        top = 104 if (dense or s.get("body")) else 112
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);right:var(--mx);top:{top}px;bottom:{70 if s.get("footnote") else 84}px;display:flex;flex-direction:column">
            {eyebrow(s.get("eyebrow"))}
            <div class="h-md" style="margin-top:20px">{fmt(s.get("title"))}</div>
            {f'<div class="lead wide" style="margin-top:14px;font-size:{19 if dense else 22}px">{fmt(s.get("body"))}</div>' if s.get("body") else ""}
            <div style="{'margin-top:28px' if dense else 'margin:auto 0'};display:grid;grid-template-columns:repeat({cols},1fr);gap:{14 if dense else 20}px">{cells}</div>
            {f'<div class="caption" style="margin-top:auto;padding-top:14px">{fmt(s.get("footnote"))}</div>' if s.get("footnote") else ""}
          </div>
        </div>"""
        return self.wrap(i, s, inner)

    def solutions(self, i, s):
        items = s.get("items", [])[:4]
        cols = len(items) if len(items) <= 3 else 2
        hot = s.get("highlight", 0)
        cells = ""
        for n, it in enumerate(items):
            fixes = ""
            if it.get("fixes"):
                fixes = '<ul class="evidence" style="margin-top:14px;gap:6px">' + "".join(
                    f'<li style="font-size:15px"><span>{fmt(f)}</span></li>' for f in it["fixes"][:3]) + "</ul>"
            cst = ""
            cells += f"""<div class="card{' hot' if n == hot else ''}" style="padding:22px 24px;display:flex;flex-direction:column;{cst}">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
                  {self.card_badge(it.get("brand"))}{icon(it.get("icon")) if it.get("icon") else ""}</div>
                <div class="card-title" style="margin-top:16px;font-size:26px">{fmt(it.get("title"))}</div>
                <div class="card-body" style="margin-top:8px;font-size:16px">{fmt(it.get("body"))}</div>{fixes}
                {f'<div class="caption" style="margin-top:auto;padding-top:14px;color:var(--accent);font-size:14px">{fmt(it.get("outcome"))}</div>' if it.get("outcome") else ""}
              </div>"""
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:104px;width:1100px">
            {eyebrow(s.get("eyebrow"))}
            <div class="h-md" style="margin-top:20px">{fmt(s.get("title"))}</div>
          </div>
          <div style="position:absolute;left:var(--mx);right:var(--mx);top:{s.get('grid_top', 250)}px;bottom:96px;display:grid;grid-template-columns:repeat({cols},1fr);gap:16px">{cells}</div>
        </div>"""
        return self.wrap(i, s, inner)

    def tiers(self, i, s):
        ts = s.get("tiers", [])[:3]
        hot = s.get("highlight", 0)
        cells = ""
        for n, t in enumerate(ts):
            price = f'<div class="card-tag" style="margin-top:18px;font-size:13px">{fmt(t["price"])}</div>' if t.get("price") else ""
            cst = ""
            cells += (f'<div class="card{" hot" if n == hot else ""}" style="padding:30px 32px;min-height:196px;{cst}">'
                      f'<div class="num-outline">{esc(t.get("num", f"{n + 1:02d}"))}</div>'
                      f'<div class="card-title" style="margin-top:14px;font-size:32px">{fmt(t.get("title"))}</div>'
                      f'<div class="card-body" style="margin-top:10px;font-size:19px">{fmt(t.get("body"))}</div>{price}</div>')
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:112px;width:1100px">
            {eyebrow(s.get("eyebrow"))}
            <div class="h-md" style="margin-top:22px">{fmt(s.get("title"))}</div>
          </div>
          <div style="position:absolute;left:var(--mx);right:var(--mx);top:300px;display:grid;grid-template-columns:repeat({len(ts) or 1},1fr);gap:22px">{cells}</div>
          {f'<div class="lead wide" style="position:absolute;left:var(--mx);bottom:72px;font-size:19px;color:var(--muted)">{fmt(s.get("footnote"))}</div>' if s.get("footnote") else ""}
        </div>"""
        return self.wrap(i, s, inner)

    def proof(self, i, s):
        logos = "".join(f'<span class="chip" style="font-size:16px;padding:11px 16px">{fmt(l)}</span>' for l in s.get("clients", [])[:14])
        cases = ""
        for c in s.get("cases", [])[:3]:
            res = f'<div class="caption" style="margin-top:10px;color:var(--accent);font-size:14px">{fmt(c["result"])}</div>' if c.get("result") else ""
            cases += (f'<div class="card" style="padding:18px 22px"><div class="card-tag">{fmt(c.get("industry"))}</div>'
                      f'<div class="card-title" style="font-size:22px;margin-top:8px">{fmt(c.get("client"))}</div>'
                      f'<div class="card-body" style="font-size:15px;margin-top:6px">{fmt(c.get("work"))}</div>{res}</div>')
        stats = ""
        if s.get("stats"):
            st = s["stats"][:4]
            stats = (f'<div class="stat-row" style="grid-template-columns:repeat({len(st)},1fr);margin-top:30px">' + "".join(
                f'<div class="stat"><div class="bignum" style="font-size:64px">{fmt(x.get("value"))}</div>'
                f'<div class="label" style="font-size:16px;margin-top:8px">{fmt(x.get("label"))}</div></div>' for x in st) + "</div>")
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);right:var(--mx);top:104px;bottom:80px;display:flex;flex-direction:column">
            {eyebrow(s.get("eyebrow"))}
            <div class="h-md" style="margin-top:20px">{fmt(s.get("title"))}</div>
            {f'<div class="lead wide" style="margin-top:12px;font-size:20px">{fmt(s.get("body"))}</div>' if s.get("body") else ""}
            {stats}
            <div class="chips" style="margin-top:{26 if stats else 34}px;gap:10px">{logos}</div>
            {f'<div style="display:grid;grid-template-columns:repeat({len(s.get("cases", [])[:3]) or 1},1fr);gap:14px;margin-top:auto">{cases}</div>' if cases else ""}
          </div>
        </div>"""
        return self.wrap(i, s, inner)

    def offer(self, i, s):
        """One recommendation: product badge, promise, key facts, what's included."""
        facts = "".join(f'<div class="stat"><div class="bignum" style="font-size:58px">{fmt(f.get("value"))}</div>'
                        f'<div class="label" style="font-size:16px;margin-top:8px">{fmt(f.get("label"))}</div></div>' for f in s.get("facts", [])[:3])
        inc = "".join(f'<div style="display:flex;gap:12px;align-items:flex-start">{icon("check")}'
                      f'<div class="card-body" style="font-size:18px;padding-top:4px">{fmt(x)}</div></div>' for x in s.get("includes", [])[:6])
        badge = self.card_badge(s.get("product")) if s.get("product") else ""
        right_html = ""
        if s.get("mockup"):
            mods = chips([{"text": m, "active": n == 0} for n, m in enumerate(s.get("modules", [])[:6])])
            cap = f'<div class="caption" style="margin-top:10px;font-size:12px">{fmt(s["mockup"].get("caption"))}</div>' if s["mockup"].get("caption") else ""
            right_html = (f'<div style="position:absolute;left:660px;right:var(--mx);top:104px">{self.portal_mock(s["mockup"])}{cap}'
                          f'<div style="margin-top:14px" class="mod-chips">{mods}</div></div>')
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:104px;bottom:80px;width:560px;display:flex;flex-direction:column">
            {eyebrow(s.get("eyebrow", "Our recommendation"))}
            {f'<div style="margin-top:22px">{badge}</div>' if badge else ""}
            <div class="h-md" style="margin-top:18px">{fmt(s.get("title"))}</div>
            {f'<div class="lead" style="margin-top:16px;font-size:20px">{fmt(s.get("body"))}</div>' if s.get("body") else ""}
            {f'<div style="margin-top:22px">{chips(s.get("chips"))}</div>' if s.get("chips") else ""}
            {f'<div class="stat-row" style="grid-template-columns:repeat({len(s.get("facts", [])[:3])},1fr);margin-top:auto">{facts}</div>' if facts else ""}
            {f'<div class="caption" style="margin-top:18px;font-size:14px">{fmt(s.get("next"))}</div>' if s.get("next") else ""}
          </div>
          {right_html}
          <div class="card hot" style="{'display:none;' if s.get('mockup') else ''}position:absolute;left:700px;right:var(--mx);top:120px;bottom:96px;padding:30px 32px;display:{'none' if s.get('mockup') else 'flex'};flex-direction:column">
            <div class="card-tag">{fmt(s.get("includes_label", "What you get"))}</div>
            <div style="display:grid;gap:14px;margin-top:20px">{inc}</div>
            {f'<div class="caption" style="margin-top:auto;padding-top:16px;color:var(--accent);font-size:15px">{fmt(s.get("outcome"))}</div>' if s.get("outcome") else ""}
            {f'<div class="caption" style="margin-top:8px;font-size:13px">{fmt(s.get("footnote"))}</div>' if s.get("footnote") else ""}
          </div>
        </div>"""
        return self.wrap(i, s, inner)

    def compare(self, i, s):
        """Side-by-side comparison table: packages or options as columns, features as rows.
        columns: [{title, sub}] (2-3), highlight: column index, groups: [{label, rows: [{label, values: [..]}]}].
        A value of true shows a check, false a muted dash, a string shows as text."""
        cols = s.get("columns", [])[:3]
        hot = s.get("highlight")
        n = len(cols) or 1
        grid = f"grid-template-columns:1.3fr {' '.join(['1fr'] * n)}"
        rows = []
        for g in s.get("groups", []):
            rows.append(("group", g.get("label")))
            for r in g.get("rows", []):
                rows.append(("row", r))
        nrows = sum(1 for k, _ in rows if k == "row")
        ngroups = len(rows) - nrows
        top = 96 + (s.get("top", 0) or 0)          # eyebrow + headline block
        table_top = top + 112
        bottom = 720 - (92 if s.get("footnote") else 64)
        rh = max(28, min(50, (bottom - table_top - 76 - ngroups * 32) // max(nrows, 1)))
        fs = 18 if rh >= 42 else (16 if rh >= 34 else 14)

        def cell(v, c):
            bg = "background:rgb(var(--accent-rgb) / .09);" if c == hot else ""
            if v is True:
                body = icon("check")
            elif v is False or v is None:
                body = '<span style="color:var(--muted);font-size:20px">&ndash;</span>'
            else:
                body = f'<span style="color:var(--text);font:600 {fs}px/1.25 var(--sans)">{fmt(v)}</span>'
            return f'<div style="{bg}display:flex;align-items:center;justify-content:center;text-align:center;padding:0 12px">{body}</div>'

        head = '<div></div>' + "".join(
            f'<div style="{"background:rgb(var(--accent-rgb) / .16);border:1px solid rgb(var(--accent-rgb) / .6);" if c == hot else "border:1px solid var(--line);"}'
            f'border-bottom:0;border-radius:14px 14px 0 0;padding:14px 12px 12px;text-align:center">'
            f'<div class="card-tag">{fmt(col.get("sub", ""))}</div>'
            f'<div class="card-title" style="font-size:24px;margin-top:8px">{fmt(col.get("title"))}</div></div>'
            for c, col in enumerate(cols))
        body = ""
        for kind, r in rows:
            if kind == "group":
                body += (f'<div style="grid-column:1 / -1;height:32px;display:flex;align-items:flex-end;padding-bottom:6px;'
                         f'border-bottom:1px solid var(--line)"><span class="card-tag">{fmt(r)}</span></div>')
                continue
            vals = (r.get("values") or [])[:n] + [None] * (n - len(r.get("values") or []))
            body += (f'<div style="display:contents"><div style="height:{rh}px;display:flex;align-items:center;'
                     f'border-bottom:1px solid var(--line);color:var(--body);font:400 {fs + 1}px/1.25 var(--sans)">{fmt(r.get("label"))}</div>'
                     + "".join(cell(v, c).replace('<div style="', f'<div style="height:{rh}px;border-bottom:1px solid var(--line);', 1)
                               for c, v in enumerate(vals)) + "</div>")
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:{top}px;width:1100px">
            {eyebrow(s.get("eyebrow"))}
            <div class="h-sm" style="margin-top:14px;font-size:44px">{fmt(s.get("title"))}</div>
          </div>
          <div style="position:absolute;left:var(--mx);right:var(--mx);top:{table_top}px;display:grid;{grid};column-gap:0">
            {head}{body}
          </div>
          {f'<div class="caption" style="position:absolute;left:var(--mx);bottom:56px;font-size:15px">{fmt(s.get("footnote"))}</div>' if s.get("footnote") else ""}
        </div>"""
        return self.wrap(i, s, inner)

    def summary(self, i, s):
        """One-page executive summary (rendered as its own PDF)."""
        ov = int(s.get("overall", 0))
        gc = score_cls(ov)
        color = {"healthy": "var(--good)", "needs": "var(--warn)", "critical": "var(--bad)"}[gc]
        circ = 2 * 3.14159 * 130
        issues = "".join(f'<div style="display:grid;grid-template-columns:44px 1fr;gap:12px;align-items:start">'
                         f'<div class="num-outline" style="font-size:30px">{n + 1:02d}</div>'
                         f'<div><div class="card-title" style="font-size:21px">{fmt(x.get("title"))}</div>'
                         f'<div class="card-body" style="font-size:15px;margin-top:4px">{fmt(x.get("body"))}</div></div></div>'
                         for n, x in enumerate(s.get("issues", [])[:3]))
        rec = s.get("recommendation") or {}
        badge = self.card_badge(rec.get("product")) if rec.get("product") else ""
        c = dict(self.theme.get("contact") or {})
        c.update(self.d.get("contact") or {})
        contact = " · ".join(x for x in [c.get("website"), c.get("email"), c.get("phone"), c.get("booking")] if x)
        inner = f"""
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:100px;width:620px">
            {eyebrow(s.get("eyebrow", "Summary"))}
            <div class="h-sm" style="margin-top:16px;font-size:44px">{fmt(s.get("title"))}</div>
            <div style="display:flex;align-items:center;gap:22px;margin-top:24px">
              <div class="ring" style="width:116px;height:116px">
                <svg viewBox="0 0 300 300"><circle cx="150" cy="150" r="130" stroke="rgba(255,255,255,.08)" stroke-width="22" fill="none"/>
                <circle cx="150" cy="150" r="130" stroke-width="22" fill="none" stroke-linecap="round" stroke-dasharray="{circ * ov / 100:.1f} {circ:.1f}" style="stroke:{color}"/></svg>
                <div class="val"><div class="bignum" style="font-size:44px">{ov}</div></div>
              </div>
              <div class="lead" style="font-size:18px;max-width:440px">{fmt(s.get("score_line"))}</div>
            </div>
            <div style="display:grid;gap:16px;margin-top:26px">{issues}</div>
          </div>
          <div class="card hot" style="position:absolute;left:760px;right:var(--mx);top:100px;bottom:120px;padding:26px 28px;display:flex;flex-direction:column">
            <div class="card-tag">We recommend</div>
            {f'<div style="margin-top:16px">{badge}</div>' if badge else ""}
            <div class="card-title" style="margin-top:14px;font-size:28px">{fmt(rec.get("title"))}</div>
            <div class="card-body" style="margin-top:10px;font-size:16px">{fmt(rec.get("body"))}</div>
            {('<ul class="evidence" style="margin-top:18px;gap:8px">' + "".join(f'<li style="font-size:16px"><span>{fmt(x)}</span></li>' for x in rec.get("points", [])[:4]) + '</ul>') if rec.get("points") else ""}
            <div class="panel" style="margin-top:auto;padding:16px 18px"><div class="k">First step</div><div class="v" style="font-size:16px">{fmt(s.get("first_step"))}</div></div>
          </div>
          <div class="footer-note" style="letter-spacing:.08em;text-transform:none;font-size:14px">{fmt(contact)}</div>
        </div>"""
        s = dict(s, hide_counter=True)
        return self.wrap(i, s, inner)

    def center(self, i, s):
        inner = f"""
        <div class="content" style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">
          {eyebrow(s.get("eyebrow"), center=True)}
          <div class="{s.get('size', 'h-lg')}" style="margin-top:30px">{fmt(s.get("title"))}</div>
          {f'<div class="caption" style="margin-top:30px;font-size:19px;letter-spacing:.04em">{fmt(s.get("body"))}</div>' if s.get("body") else ""}
        </div>"""
        s = dict(s, glow=s.get("glow", "center"))
        return self.wrap(i, s, inner)

    def proof_strip(self, pf):
        if not pf:
            return ""
        st = "".join(f'<div class="ps-stat"><b>{fmt(x.get("value"))}</b><span>{fmt(x.get("label"))}</span></div>' for x in pf.get("stats", [])[:4])
        cl = " · ".join(esc(c) for c in pf.get("clients", [])[:8])
        return (f'<div class="proof-strip">{st}<div class="ps-clients"><span>{fmt(pf.get("label", "Trusted by"))}</span>{cl}</div></div>')

    def contact(self, i, s):
        c = dict(self.theme.get("contact") or {})
        c.update(self.d.get("contact") or {})
        c.update(s.get("contact") or {})
        rows = [(ic, c[k], cls) for ic, k, cls in (("globe", "website", ""), ("send", "email", ""), ("message", "phone", ""), ("home", "address", "sm")) if c.get(k)]
        if c.get("booking"):
            rows.insert(min(3, len(rows)), ("calendar", c["booking"], "sm"))
        rhtml = "".join(f'<div class="contact-row"><div class="ic">{icon(ic)}</div><div class="t {cls}">{fmt(t)}</div></div>' for ic, t, cls in rows)
        credit = self.credit()
        footer = fmt(s.get("footer", c.get("tagline", "Design · Engineering · Operations")))
        if credit:
            footer = f'{credit}<span style="opacity:.5">·</span>{footer}'
        fs = ""
        if s.get("first_step"):
            f = s["first_step"]
            fs = (f'<div class="panel" style="margin-top:22px;border-color:rgb(var(--accent-rgb) / .45)"><div class="k">{fmt(f.get("label", "First step"))}</div>'
                  f'<div class="card-title" style="font-size:24px">{fmt(f.get("title"))}</div>'
                  f'<div class="card-body" style="font-size:16px;margin-top:6px">{fmt(f.get("body"))}</div></div>')
        inner = f"""
        <div class="arc"></div>
        <div class="content">
          <div style="position:absolute;left:var(--mx);top:{(96 if s.get("proof") else 110) if fs else (130 if s.get("proof") else 170)}px;width:600px">
            <img alt="{self.logo_alt}" src="{self.logo}" style="height:{round(self.logo_h * 1.45)}px">
            <div class="bignum" style="font-size:{min(92 if fs else 110, self.fit_title(s.get("title", "Next step"), 600, 110))}px;margin-top:{24 if fs else 30}px;line-height:1">{fmt(s.get("title", "Next step"))}</div>
            <div class="lead" style="margin-top:18px">{fmt(s.get("body"))}</div>
            {fs}
            {f'<div class="btn" style="margin-top:{26 if fs else 36}px">{fmt(s.get("cta"))} →</div>' if s.get("cta") else ""}
          </div>
          <div style="position:absolute;left:740px;right:var(--mx);top:{150 if s.get("proof") else 200}px;display:grid;gap:{16 if s.get("proof") else 22}px">{rhtml}</div>
          {self.proof_strip(s.get("proof"))}
          <div class="footer-note" style="{'display:none' if s.get('proof') else ''}">{footer}</div>
        </div>"""
        s = dict(s, hide_logo=True, hide_counter=bool(s.get("proof")), glow=s.get("glow", "strong"))
        return self.wrap(i, s, inner)


LAYOUTS = ["cover", "statement", "stats", "scorecard", "score_gaps", "finding", "process", "cards", "solutions", "tiers", "proof", "center", "contact", "offer", "compare", "summary"]


def render(deck, ctx):
    r = R(deck, ctx)
    slides = []
    for i, s in enumerate(deck.get("slides", [])):
        lay = s.get("layout", "statement")
        fn = getattr(r, lay if lay in LAYOUTS else "statement")
        slides.append(fn(i, s))
    css = ctx["asset"]("style.css")
    title = esc(deck.get("title", "Growth Opportunities"))
    th = ctx.get("theme") or {}
    urls = []
    for t in [th]:
        for u in t.get("fonts", []):
            if u not in urls:
                urls.append(u)
    fonts = "".join(f'<link href="{esc(u)}" rel="stylesheet">' for u in urls)
    tvars = dict(th.get("vars", {}))
    variant = deck.get("theme_variant")
    if variant and variant in (th.get("vertical_accents") or {}):
        tvars.update(th["vertical_accents"][variant])
    root = ":root{" + "".join(f"{k}:{v};" for k, v in tvars.items()) + "}"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fonts}
<link rel="stylesheet" href="{css}"><style>{root}</style></head><body data-theme="{esc(th.get("name", "default"))}">{"".join(slides)}</body></html>"""
