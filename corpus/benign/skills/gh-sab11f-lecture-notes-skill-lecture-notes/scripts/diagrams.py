"""Parametric inline-SVG diagram catalog for lecture notes.

Every generator has the signature  fn(pal, args) -> html string  and is invoked
from content.md with a line   @@name args .  Fields are separated by "|",
options are key=value, lists inside a field use "," or ";".  See
references/diagram-catalog.md for the user-facing documentation.
"""
import html, re

# ----------------------------------------------------------------- helpers
def _fields(args):
    parts = [p.strip() for p in (args or "").split("|")]
    opts, pos = {}, []
    for p in parts:
        if not p:
            continue
        m = re.match(r"^([A-Za-z_]+)=(.*)$", p)
        if m:
            opts[m.group(1)] = m.group(2).strip()
        else:
            pos.append(p)
    return pos, opts

def _svg(w, h, body, cap=None, cls="dg"):
    c = f'<figcaption>{html.escape(cap)}</figcaption>' if cap else ""
    return (f'<figure class="{cls}"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" font-family="Inter, sans-serif">{body}</svg>{c}</figure>')

def _t(s):
    return html.escape(s)

MATH = 'font-family="Latin Modern Math, DejaVu Math TeX Gyre, STIX Two Math, serif"'
SERIF = 'font-family="Lora, Georgia, serif" font-style="italic"'

def _arrow_defs(pal, id_="arr", color=None):
    color = color or pal["accent"]
    return (f'<defs><marker id="{id_}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{color}"/></marker></defs>')

# ----------------------------------------------------------------- flow / steps
def flow(pal, args):
    """@@flow Step one | Step two | Step three | cap=..."""
    steps, o = _fields(args)
    n = len(steps); bw = int(o.get("w", 150)); bh = 46; gap = 34
    w = n * bw + (n - 1) * gap + 8; h = bh + 8
    out = [_arrow_defs(pal)]
    for i, s in enumerate(steps):
        x = 4 + i * (bw + gap)
        out.append(f'<rect x="{x}" y="4" width="{bw}" height="{bh}" rx="8" fill="{pal["tint"]}" stroke="{pal["accent"]}" stroke-width="1.5"/>')
        out.append(f'<text x="{x+bw/2}" y="{4+bh/2+5}" text-anchor="middle" font-size="14" font-weight="600" fill="{pal["ink"]}">{_t(s)}</text>')
        if i < n - 1:
            ax = x + bw + 4
            out.append(f'<path d="M{ax} {4+bh/2} H{ax+gap-10}" stroke="{pal["accent"]}" stroke-width="2" fill="none" marker-end="url(#arr)"/>')
    return _svg(w, h, "".join(out), o.get("cap"))
steps = flow

# ----------------------------------------------------------------- truth table
def truth(pal, args):
    """@@truth A; B; A ∧ B | 0,0,0 | 0,1,0 | 1,0,0 | 1,1,1 | hl=3 | cap=...
    header fields separated by ';', one row per '|' field, last column = result."""
    pos, o = _fields(args)
    head = [h.strip() for h in pos[0].split(";")]
    rows = [[c.strip() for c in r.split(",")] for r in pos[1:]]
    hl = {int(x) for x in o.get("hl", "").split(",") if x.strip().isdigit()}
    th = "".join(f"<th>{_t(h)}</th>" for h in head)
    trs = []
    for i, r in enumerate(rows):
        cls = ' class="hl"' if i in hl else ""
        tds = "".join(f"<td>{_t(c)}</td>" for c in r[:-1]) + f'<td class="res">{_t(r[-1])}</td>'
        trs.append(f"<tr{cls}>{tds}</tr>")
    cap = f'<figcaption>{_t(o["cap"])}</figcaption>' if o.get("cap") else ""
    return f'<figure class="truth"><table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>{cap}</figure>'

# ----------------------------------------------------------------- ladder (precedence / ranking)
def ladder(pal, args):
    """@@ladder ¬:negacija | ∧:konjunkcija | ∨:disjunkcija | left=highest | right=lowest | cap=..."""
    items, o = _fields(args)
    items = [(i.split(":", 1) + [""])[:2] for i in items]
    bw = 112; gap = 26; n = len(items)
    out = []
    for i, (s, name) in enumerate(items):
        x = 4 + i * (bw + gap)
        shade = 1 - i * (0.8 / max(n, 2))
        out.append(f'<rect x="{x}" y="6" width="{bw}" height="64" rx="8" fill="{pal["tint"]}" stroke="{pal["accent"]}" stroke-width="1.5" opacity="{shade:.2f}"/>')
        out.append(f'<text x="{x+bw/2}" y="38" text-anchor="middle" font-size="26" {MATH} fill="{pal["ink"]}">{_t(s)}</text>')
        out.append(f'<text x="{x+bw/2}" y="60" text-anchor="middle" font-size="11.5" fill="{pal["muted"]}">{_t(name)}</text>')
        if i < n - 1:
            out.append(f'<text x="{x+bw+gap/2}" y="43" text-anchor="middle" font-size="18" fill="{pal["accent"]}">›</text>')
    W = 4 + n * bw + (n - 1) * gap + 4
    if o.get("left"):
        out.append(f'<text x="4" y="92" font-size="11.5" fill="{pal["muted"]}">{_t(o["left"])}</text>')
    if o.get("right"):
        out.append(f'<text x="{W-4}" y="92" text-anchor="end" font-size="11.5" fill="{pal["muted"]}">{_t(o["right"])}</text>')
    return _svg(W, 100, "".join(out), o.get("cap"))

# ----------------------------------------------------------------- venn
def venn3(pal, args):
    """@@venn3 A=2,3,c | B= | C=d | AB=a,b | AC= | BC=4 | ABC=1 | names=A,B,C | cap=..."""
    _, o = _fields(args)
    names = [n.strip() for n in o.get("names", "A,B,C").split(",")]
    A = (150, 110); B = (100, 190); C = (205, 190); r = 78
    c = pal["cat"]
    body = ""
    for (cx, cy), col in zip((A, B, C), c):
        body += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}" fill-opacity=".18" stroke="{col}" stroke-width="2"/>'
    body += (f'<text x="150" y="30" text-anchor="middle" font-size="18" font-weight="700" fill="{c[0]}">{_t(names[0])}</text>'
             f'<text x="34" y="262" text-anchor="middle" font-size="18" font-weight="700" fill="{c[1]}">{_t(names[1])}</text>'
             f'<text x="272" y="262" text-anchor="middle" font-size="18" font-weight="700" fill="{c[2]}">{_t(names[2])}</text>')
    # region anchor points
    regions = {"A": (150, 80), "B": (62, 205), "C": (245, 205), "AB": (108, 150), "AC": (195, 150), "BC": (152, 222), "ABC": (152, 168)}
    for key, (x, y) in regions.items():
        els = [e.strip() for e in o.get(key, "").split(",") if e.strip()]
        if not els:
            continue
        # spread elements in a small cluster
        for i, e in enumerate(els):
            dx = (i - (len(els) - 1) / 2) * 22
            dy = 0 if len(els) < 4 else (i % 2) * 16 - 8
            body += f'<text x="{x+dx}" y="{y+dy}" text-anchor="middle" font-size="15" {SERIF} fill="{pal["ink"]}">{_t(e)}</text>'
    return _svg(300, 275, body, o.get("cap"))

VENN2_MODES = {"comp": "{A}ᶜ", "inter": "{A} ∩ {B}", "union": "{A} ∪ {B}", "diff": "{A} \\ {B}",
               "subset": "{A} ⊆ {B}", "disjoint": "{A} ∩ {B} = ∅", "symdiff": "{A} △ {B}"}

def _venn2(pal, title, formula, mode, A="A", B="B"):
    c = pal["accent"]; W, H = 200, 130
    ax, ay, bx, by, r = 78, 70, 122, 70, 44
    if mode == "subset": ax, ay, r_a, bx, by, r_b = 100, 72, 24, 100, 70, 48
    if mode == "disjoint": ax, bx = 55, 145
    uid = mode + str(abs(hash(title)) % 10000)
    parts = [f'<rect x="4" y="4" width="{W-8}" height="{H-8}" rx="6" fill="#fff" stroke="{pal["muted"]}" stroke-width="1"/>',
             f'<text x="12" y="20" font-size="11" fill="{pal["muted"]}">U</text>']
    fill = f'fill="{c}" fill-opacity=".35"'
    lab = lambda x, y, s: f'<text x="{x}" y="{y}" text-anchor="middle" font-size="15" {SERIF}>{_t(s)}</text>'
    if mode == "comp":
        parts.append(f'<defs><mask id="m{uid}"><rect x="4" y="4" width="{W-8}" height="{H-8}" fill="#fff"/><circle cx="{ax}" cy="{ay}" r="{r}" fill="#000"/></mask></defs>')
        parts.append(f'<rect x="4" y="4" width="{W-8}" height="{H-8}" rx="6" {fill} mask="url(#m{uid})"/>')
        parts.append(f'<circle cx="{ax}" cy="{ay}" r="{r}" fill="#fff" stroke="{pal["ink"]}" stroke-width="1.5"/>')
        parts.append(lab(ax, ay + 5, A))
    elif mode == "subset":
        parts.append(f'<circle cx="{bx}" cy="{by}" r="{r_b}" fill="{c}" fill-opacity=".15" stroke="{pal["ink"]}" stroke-width="1.5"/>')
        parts.append(f'<circle cx="{ax}" cy="{ay+10}" r="{r_a}" {fill} stroke="{pal["ink"]}" stroke-width="1.5"/>')
        parts.append(lab(ax, ay + 15, A)); parts.append(lab(bx + 30, by - 28, B))
    else:
        if mode == "inter":
            parts.append(f'<defs><clipPath id="c{uid}"><circle cx="{ax}" cy="{ay}" r="{r}"/></clipPath></defs>')
            parts.append(f'<circle cx="{bx}" cy="{by}" r="{r}" {fill} clip-path="url(#c{uid})"/>')
        elif mode == "union":
            parts.append(f'<circle cx="{ax}" cy="{ay}" r="{r}" {fill}/><circle cx="{bx}" cy="{by}" r="{r}" {fill}/>')
        elif mode in ("diff", "symdiff"):
            parts.append(f'<defs><mask id="m{uid}"><rect width="{W}" height="{H}" fill="#fff"/><circle cx="{bx}" cy="{by}" r="{r}" fill="#000"/></mask>'
                         f'<mask id="n{uid}"><rect width="{W}" height="{H}" fill="#fff"/><circle cx="{ax}" cy="{ay}" r="{r}" fill="#000"/></mask></defs>')
            parts.append(f'<circle cx="{ax}" cy="{ay}" r="{r}" {fill} mask="url(#m{uid})"/>')
            if mode == "symdiff":
                parts.append(f'<circle cx="{bx}" cy="{by}" r="{r}" {fill} mask="url(#n{uid})"/>')
        parts.append(f'<circle cx="{ax}" cy="{ay}" r="{r}" fill="none" stroke="{pal["ink"]}" stroke-width="1.5"/>')
        parts.append(f'<circle cx="{bx}" cy="{by}" r="{r}" fill="none" stroke="{pal["ink"]}" stroke-width="1.5"/>')
        parts.append(lab(ax - 18, ay + 5, A)); parts.append(lab(bx + 18, by + 5, B))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Inter,sans-serif">{"".join(parts)}</svg>'
    return f'<div class="venncell">{svg}<div class="vlabel">{_t(title)}  <span class="m">{_t(formula)}</span></div></div>'

def venn2(pal, args):
    """@@venn2 inter:Presek | union:Unija | diff:Razlika | comp:Komplement | subset:Podmnožica | disjoint:Disjunktni | names=A,B | cap=..."""
    pos, o = _fields(args)
    A, B = (o.get("names", "A,B").split(",") + ["B"])[:2]
    cells = []
    for p in pos:
        mode, _, title = p.partition(":")
        mode = mode.strip()
        if mode not in VENN2_MODES:
            continue
        formula = VENN2_MODES[mode].format(A=A.strip(), B=B.strip())
        cells.append(_venn2(pal, title.strip() or mode, formula, mode, A.strip(), B.strip()))
    cap = f'<figcaption>{_t(o["cap"])}</figcaption>' if o.get("cap") else ""
    cols = min(3, max(1, len(cells)))
    return f'<figure class="venngrid" style="grid-template-columns:repeat({cols},1fr)">{"".join(cells)}{cap}</figure>'

# ----------------------------------------------------------------- number line
_INT = re.compile(r"^([\[(])\s*(-?[\d.]+|-?inf|−?∞)\s*,\s*(-?[\d.]+|inf|∞)\s*([\])])\s*(?::\s*(.*))?$")

def numline(pal, args):
    """@@numline -4..5 | (-2,3]:A | [2,3):B | mark=-2:inf A | shade=-4..-2:spodnje meje | cap=...
    intervals are stacked on separate rows; marks put a label above a point; shade adds a band below the axis."""
    pos, o = _fields(args)
    lo, hi = [float(v) for v in pos[0].split("..")]
    ivs = []
    for p in pos[1:]:
        m = _INT.match(p)
        if m:
            ivs.append(m.groups())
    marks = [v.split(":", 1) for v in re.findall(r"mark=([^|]+)", args)]
    shades = [v.split(":", 1) for v in re.findall(r"shade=([^|]+)", args)]
    W = 520; px = (W - 100) / (hi - lo); X = lambda v: 50 + (v - lo) * px
    rows = max(1, len(ivs)); y0 = 40 + (24 if marks else 0); row_h = 26
    axis_y = y0 + rows * row_h
    out = [f'<line x1="{X(lo)}" y1="{axis_y}" x2="{X(hi)}" y2="{axis_y}" stroke="{pal["muted"]}" stroke-width="1"/>']
    step = 1 if hi - lo <= 12 else int((hi - lo) / 10)
    v = lo
    while v <= hi + 1e-9:
        out.append(f'<line x1="{X(v)}" y1="{axis_y-4}" x2="{X(v)}" y2="{axis_y+4}" stroke="{pal["muted"]}"/>')
        out.append(f'<text x="{X(v)}" y="{axis_y+18}" text-anchor="middle" font-size="11" fill="{pal["muted"]}">{v:g}</text>')
        v += step
    cols = pal["cat"]
    for i, (lb, a, b, rb, label) in enumerate(ivs):
        col = cols[i % len(cols)]; y = y0 + i * row_h + 8
        a = lo if a in ("-inf", "−∞") else float(a); b = hi if b in ("inf", "∞") else float(b)
        out.append(f'<line x1="{X(a)}" y1="{y}" x2="{X(b)}" y2="{y}" stroke="{col}" stroke-width="5"/>')
        out.append(f'<circle cx="{X(a)}" cy="{y}" r="5.5" fill="{col if lb=="[" else "#fff"}" stroke="{col}" stroke-width="2"/>')
        out.append(f'<circle cx="{X(b)}" cy="{y}" r="5.5" fill="{col if rb=="]" else "#fff"}" stroke="{col}" stroke-width="2"/>')
        if label:
            out.append(f'<text x="{X(b)+12}" y="{y+4}" font-size="12" font-weight="600" fill="{col}">{_t(label.strip())}</text>')
    for m in marks:
        xv = float(m[0]); txt = m[1] if len(m) > 1 else ""
        out.append(f'<text x="{X(xv)}" y="{y0-10}" text-anchor="middle" font-size="11.5" fill="{pal["ink"]}">{_t(txt)}</text>')
        out.append(f'<line x1="{X(xv)}" y1="{y0-6}" x2="{X(xv)}" y2="{axis_y-6}" stroke="{pal["rule"]}" stroke-dasharray="3 3"/>')
    H = axis_y + 30
    for i, s in enumerate(shades):
        a, b = [float(v) for v in s[0].split("..")]; txt = s[1] if len(s) > 1 else ""
        col = cols[(i + 2) % len(cols)]
        out.append(f'<rect x="{X(a)}" y="{axis_y+26}" width="{X(b)-X(a)}" height="12" fill="{col}" fill-opacity=".25"/>')
        out.append(f'<text x="{(X(a)+X(b))/2}" y="{axis_y+52}" text-anchor="middle" font-size="11" fill="{col}">{_t(txt)}</text>')
        H = axis_y + 60
    return _svg(W, H, "".join(out), o.get("cap"))

def intervals(pal, args):
    """@@intervals [a,b] | (a,b) | [a,b) | (a,b] | note=... | cap=...   (symbolic endpoints a, b)"""
    pos, o = _fields(args)
    pos = pos or ["[a,b]", "(a,b)", "[a,b)", "(a,b]"]
    c = pal["accent"]; out = []
    for i, lab in enumerate(pos):
        l, r = lab.strip()[0], lab.strip()[-1]
        ends = lab.strip()[1:-1].split(",")
        y = 22 + i * 40; x1 = 120; x2 = 300
        out.append(f'<line x1="40" y1="{y}" x2="380" y2="{y}" stroke="{pal["muted"]}" stroke-width="1"/>')
        out.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{c}" stroke-width="4"/>')
        out.append(f'<circle cx="{x1}" cy="{y}" r="5.5" fill="{c if l=="[" else "#fff"}" stroke="{c}" stroke-width="2"/>')
        out.append(f'<circle cx="{x2}" cy="{y}" r="5.5" fill="{c if r=="]" else "#fff"}" stroke="{c}" stroke-width="2"/>')
        out.append(f'<text x="{x1}" y="{y+20}" text-anchor="middle" font-size="12" {SERIF}>{_t(ends[0].strip())}</text>')
        out.append(f'<text x="{x2}" y="{y+20}" text-anchor="middle" font-size="12" {SERIF}>{_t(ends[-1].strip())}</text>')
        out.append(f'<text x="470" y="{y+5}" text-anchor="end" font-size="15" {MATH}>{_t(lab)}</text>')
    H = 22 + len(pos) * 40
    if o.get("note"):
        out.append(f'<text x="40" y="{H+6}" font-size="11.5" fill="{pal["muted"]}">{_t(o["note"])}</text>'); H += 16
    return _svg(480, H + 4, "".join(out), o.get("cap"))

# ----------------------------------------------------------------- nested sets
def nested(pal, args):
    """@@nested ℝ; realna števila; zaprta za: + − · ÷; √2, π, e | ℚ; ... | ℕ; ...   outer → inner; fields  sym; name; top-right note; bottom-right examples"""
    pos, o = _fields(args)
    rows = [([x.strip() for x in r.split(";")] + ["", "", ""])[:4] for r in pos]
    n = len(rows); c = pal["cat"]
    W = 560; step = 34; band = 30; H = 60 + (n - 1) * (step + band) + 8
    out = []
    for i, (sym, name, top, bottom) in enumerate(rows):
        x = 4 + i * step; y = 4 + i * step; w = W - 8 - 2 * i * step; h = H - 8 - i * (step + band)
        col = c[i % len(c)]
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{col}" fill-opacity=".10" stroke="{col}" stroke-width="1.5"/>')
        out.append(f'<text x="{x+14}" y="{y+24}" font-size="20" font-weight="700" {MATH} fill="{col}">{_t(sym)}</text>')
        out.append(f'<text x="{x+14+len(sym)*16+12}" y="{y+23}" font-size="13" font-weight="600" fill="{pal["ink"]}">{_t(name)}</text>')
        if top:
            out.append(f'<text x="{x+w-12}" y="{y+23}" text-anchor="end" font-size="11.5" fill="{pal["muted"]}">{_t(top)}</text>')
        if bottom:
            out.append(f'<text x="{x+w-12}" y="{y+h-10}" text-anchor="end" font-size="12" {SERIF} fill="{pal["ink"]}">{_t(bottom)}</text>')
    return _svg(W, H + 4, "".join(out), o.get("cap"))

# ----------------------------------------------------------------- dominoes (induction)
def dominoes(pal, args):
    """@@dominoes base=1. baza | step=2. korak: P(n) ⇒ P(n+1) | labels=n₀,n₀+1,n₀+2,…,n,n+1,… | cap=..."""
    _, o = _fields(args)
    c = pal["accent"]; g = pal["cat"][2]
    labels = [l.strip() for l in o.get("labels", "n₀,n₀+1,n₀+2,…,n,n+1,…").split(",")]
    out = [_arrow_defs(pal, "ia")]
    xs = {}
    for i, l in enumerate(labels):
        x = 20 + i * 78; xs[i] = x
        if l == "…":
            out.append(f'<text x="{x+14}" y="78" font-size="20" fill="{pal["muted"]}">…</text>'); continue
        base = i == 0; step = i >= len(labels) - 3 and l != "…"
        fill = g if base else (pal["tint"] if step else "#fff"); stroke = g if base else c
        out.append(f'<rect x="{x}" y="34" width="30" height="80" rx="5" fill="{fill}" fill-opacity="{".35" if base else "1"}" stroke="{stroke}" stroke-width="1.5"/>')
        out.append(f'<text x="{x+15}" y="132" text-anchor="middle" font-size="12.5" {SERIF}>{_t(l)}</text>')
    out.append(f'<text x="35" y="22" text-anchor="middle" font-size="11.5" font-weight="600" fill="{g}">{_t(o.get("base","base"))}</text>')
    k = len(labels) - 3
    if k >= 1:
        x1 = xs[k] + 32; x2 = xs[k + 1] - 4
        out.append(f'<path d="M{x1} 60 C {x1+18} 40, {x2-16} 40, {x2} 58" stroke="{c}" stroke-width="2" fill="none" marker-end="url(#ia)"/>')
        out.append(f'<text x="{(x1+x2)/2}" y="30" text-anchor="middle" font-size="11.5" font-weight="600" fill="{c}">{_t(o.get("step","step: P(n) ⇒ P(n+1)"))}</text>')
    return _svg(20 + len(labels) * 78, 142, "".join(out), o.get("cap"))

# ----------------------------------------------------------------- dependency (quantifier order)
def depend(pal, args):
    """@@depend ∀x ∃y : x² = y | ∃y ∀x : x² = y | each=caption | one=caption | cap=..."""
    pos, o = _fields(args)
    c = pal["accent"]; g = pal["cat"][2]
    def panel(ox, title, mode, caption):
        p = [f'<text x="{ox+150}" y="22" text-anchor="middle" font-size="15" font-weight="600" fill="{pal["ink"]}">{_t(title)}</text>']
        xs = [ox + 40, ox + 110, ox + 180, ox + 250]
        for i, x in enumerate(xs):
            p.append(f'<circle cx="{x}" cy="62" r="13" fill="{pal["tint"]}" stroke="{c}" stroke-width="1.5"/>')
            p.append(f'<text x="{x}" y="67" text-anchor="middle" font-size="13" {SERIF}>x<tspan baseline-shift="sub" font-size="9">{i+1}</tspan></text>')
        if mode == "each":
            for i, x in enumerate(xs):
                p.append(f'<circle cx="{x}" cy="132" r="13" fill="#fff" stroke="{g}" stroke-width="1.5"/>')
                p.append(f'<text x="{x}" y="137" text-anchor="middle" font-size="13" {SERIF}>y<tspan baseline-shift="sub" font-size="9">{i+1}</tspan></text>')
                p.append(f'<path d="M{x} 76 V117" stroke="{pal["muted"]}" stroke-width="1.5" marker-end="url(#qa)"/>')
            p.append(f'<text x="{ox+150}" y="168" text-anchor="middle" font-size="12" fill="{g}">{_t(caption)}</text>')
        else:
            p.append(f'<circle cx="{ox+145}" cy="132" r="13" fill="#fff" stroke="{pal["warn"]}" stroke-width="1.5"/>')
            p.append(f'<text x="{ox+145}" y="137" text-anchor="middle" font-size="13" {SERIF}>y</text>')
            for x in xs:
                p.append(f'<path d="M{x} 76 L{ox+145} 117" stroke="{pal["muted"]}" stroke-width="1.5" marker-end="url(#qa)"/>')
            p.append(f'<text x="{ox+150}" y="168" text-anchor="middle" font-size="12" fill="{pal["warn"]}">{_t(caption)}</text>')
        return "".join(p)
    body = _arrow_defs(pal, "qa", pal["muted"]) + panel(0, pos[0] if pos else "", "each", o.get("each", "")) \
        + f'<line x1="310" y1="10" x2="310" y2="175" stroke="{pal["rule"]}"/>' + panel(320, pos[1] if len(pos) > 1 else "", "one", o.get("one", ""))
    return _svg(620, 180, body, o.get("cap"))

# ----------------------------------------------------------------- timeline
def timeline(pal, args):
    """@@timeline 1806:De Morgan | 1815:Boole | 1845:Cantor | cap=..."""
    pos, o = _fields(args)
    items = [(p.split(":", 1) + [""])[:2] for p in pos]
    n = len(items); W = max(320, 80 + n * 110); y = 60
    out = [f'<line x1="30" y1="{y}" x2="{W-30}" y2="{y}" stroke="{pal["accent"]}" stroke-width="2"/>']
    for i, (when, what) in enumerate(items):
        x = 40 + i * ((W - 80) / max(n - 1, 1))
        out.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{pal["accent"]}"/>')
        out.append(f'<text x="{x}" y="{y-16}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal["accent"]}">{_t(when.strip())}</text>')
        for j, line in enumerate(what.strip().split(";")):
            out.append(f'<text x="{x}" y="{y+24+j*14}" text-anchor="middle" font-size="11.5" fill="{pal["ink"]}">{_t(line.strip())}</text>')
    return _svg(W, 110, "".join(out), o.get("cap"))

# ----------------------------------------------------------------- tree
def tree(pal, args):
    """@@tree Root > A, B, C ; A > A1, A2 ; B > B1 | cap=...   (layered top-down tree)"""
    pos, o = _fields(args)
    spec = pos[0] if pos else ""
    children = {}; order = []
    for rule in spec.split(";"):
        if ">" not in rule:
            continue
        parent, kids = rule.split(">", 1)
        parent = parent.strip(); kids = [k.strip() for k in kids.split(",") if k.strip()]
        children[parent] = kids
        if parent not in order: order.append(parent)
        for k in kids:
            if k not in order: order.append(k)
    root = order[0] if order else ""
    # layout
    pos_xy = {}; width = {}
    def measure(n):
        kids = children.get(n, [])
        width[n] = max(1, sum(measure(k) for k in kids)) if kids else 1
        return width[n]
    measure(root)
    bw, bh, gx, gy = 120, 34, 16, 50
    def place(n, x0, depth):
        w = width[n] * (bw + gx)
        pos_xy[n] = (x0 + w / 2, 20 + depth * (bh + gy))
        cx = x0
        for k in children.get(n, []):
            place(k, cx, depth + 1); cx += width[k] * (bw + gx)
    place(root, 4, 0)
    out = []
    for n, (x, y) in pos_xy.items():
        for k in children.get(n, []):
            kx, ky = pos_xy[k]
            out.append(f'<path d="M{x} {y+bh/2} C {x} {y+bh/2+gy/2}, {kx} {ky-bh/2-gy/2}, {kx} {ky-bh/2}" stroke="{pal["muted"]}" stroke-width="1.5" fill="none"/>')
    for n, (x, y) in pos_xy.items():
        depth = int((y - 20) / (bh + gy))
        fill = pal["tint"] if depth == 0 else "#fff"
        out.append(f'<rect x="{x-bw/2}" y="{y-bh/2}" width="{bw}" height="{bh}" rx="7" fill="{fill}" stroke="{pal["accent"]}" stroke-width="1.5"/>')
        out.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="12" font-weight="{700 if depth==0 else 500}" fill="{pal["ink"]}">{_t(n)}</text>')
    W = width[root] * (bw + gx) + 8; H = 20 + (max(int((y - 20) / (bh + gy)) for _, y in pos_xy.values()) + 1) * (bh + gy)
    return _svg(W, H, "".join(out), o.get("cap"))

# ----------------------------------------------------------------- workspace
def space(pal, args):
    """@@space 5   (height in cm of a dotted area for the student's own work)"""
    pos, _ = _fields(args)
    cm = float(pos[0]) if pos else 5
    return f'<div class="space" style="height:{cm}cm"><span class="space-label">{_t(pal["t"]["space"])}</span></div>'

REGISTRY = {"flow": flow, "steps": steps, "truth": truth, "ladder": ladder, "venn2": venn2, "venn3": venn3,
            "numline": numline, "intervals": intervals, "nested": nested, "dominoes": dominoes,
            "depend": depend, "timeline": timeline, "tree": tree, "space": space}
