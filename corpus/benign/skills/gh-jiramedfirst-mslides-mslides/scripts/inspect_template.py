"""Inspect a .pptx template so its manual.json "template" block can be written from facts, not guesses.

  python inspect_template.py <template.pptx> [--render <dir>] [--suggest]

Prints slide size, theme colours, every master's layouts (with placeholder idx/type/box) and every sample slide
(its layout + placeholders + text). --render also exports the template to <dir>/template.pdf (Keynote on macOS,
PowerPoint on Windows, else LibreOffice) so you can LOOK at where the logo, rules and footer sit before choosing "area".
Layout names can repeat across masters (e.g. "Title Slide" in three masters) — then pick layouts by sample slide number.
--suggest prints a "template" block to paste into manual.json: layouts picked by placeholder types, the area
measured from the content layout's title placeholder, dark colours when the theme background is dark.
"""
import json, pathlib, re, sys
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER as PH

EMU = 914400
THEME_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
SCHEME_RE = r"<a:(dk1|lt1|dk2|lt2|accent\d|hlink)>.*?(?:val|lastClr)=\"([0-9A-Fa-f]{6})\""


def suggest(prs, path_arg):
    """Starting point, not a verdict: run the build and look at the pages (template.md §10) before trusting it."""
    def kinds(layout):  # placeholder idx → type, ignoring the date/footer/number trio (idx ≥ 10)
        return {p.placeholder_format.idx: p.placeholder_format.type for p in layout.placeholders if p.placeholder_format.idx < 10}

    def pick(test):
        for mi, m in enumerate(prs.slide_masters):
            for l in m.slide_layouts:
                if test(kinds(l)):
                    return mi, l
        return None

    cover = pick(lambda k: k.get(0) == PH.CENTER_TITLE or (0 in k and k.get(1) == PH.SUBTITLE))
    divider = pick(lambda k: k.get(0) == PH.TITLE and k.get(1) in (PH.BODY, PH.OBJECT) and 2 not in k)
    content = pick(lambda k: k.get(0) == PH.TITLE and len(k) == 1)
    missing = [n for n, v in (("cover", cover), ("divider", divider), ("content", content)) if v is None]
    if missing:
        raise SystemExit(f"--suggest: no layout fits {missing} by placeholder types — pick by hand from the listing above")

    def ref(mi, layout):
        # A name that repeats across masters is ambiguous by name: prefer a sample slide that uses the layout.
        if sum(l.name == layout.name for m in prs.slide_masters for l in m.slide_layouts) > 1:
            for si, s in enumerate(prs.slides, 1):
                if s.slide_layout == layout:
                    return {"slide": si}
        return {"layout": layout.name, **({"master": mi} if mi else {})}

    r = lambda v: round(round(v / EMU * 20) / 20, 2)  # inches, to 0.05"
    title = next(p for p in content[1].placeholders if p.placeholder_format.idx == 0)
    sw, sh = prs.slide_width, prs.slide_height
    # Lowest layout-drawn art (a logo, a footer rule) bounds the area from below; else the slide bottom − 0.5".
    art = [s.top for s in content[1].shapes if not s.is_placeholder and s.top is not None]
    bottom = (min(art) / EMU - 0.3) if art else sh / EMU - 0.5
    # Margin floors the title's left edge to 0.1": content may hug the title, never sit inside it, and the extra
    # tenth of an inch is what lets a full-width table (the demo's 12.1") fit on the stock 13.33" slide.
    x, y = int(title.left / EMU * 10) / 10, r(title.top + title.height) + 0.2
    blk = {"path": path_arg, "cover": ref(*cover), "divider": ref(*divider), "content": ref(*content),
           "area": [x, round(y, 2), r(sw - 2 * x * EMU), round(bottom - y, 2)]}
    theme = prs.slide_masters[0].part.part_related_by(THEME_REL).blob.decode("utf8", "ignore")
    bg = dict(re.findall(SCHEME_RE, theme)).get("lt1", "FFFFFF")  # bg1 → lt1 is what the master background paints
    rr, gg, bb = (int(bg[i:i + 2], 16) for i in (0, 2, 4))
    if 0.299 * rr + 0.587 * gg + 0.114 * bb < 128:
        sys.path.insert(0, str(pathlib.Path(__file__).parent))
        from build_manual import DARK_COLORS
        blk["colors"] = DARK_COLORS
    print('\n"template": ' + json.dumps(blk, indent=2))


def box(sh):
    return "[" + ", ".join(f"{(v or 0) / EMU:.2f}" for v in (sh.left, sh.top, sh.width, sh.height)) + "]"


def phs(shapes):
    return "; ".join(f"idx{p.placeholder_format.idx} {p.placeholder_format.type} {box(p)}" for p in shapes.placeholders) or "no placeholders"


path = pathlib.Path(sys.argv[1]).expanduser()
prs = Presentation(path)
print(f"slide size {prs.slide_width / EMU:.2f}\" x {prs.slide_height / EMU:.2f}\"")

for mi, m in enumerate(prs.slide_masters):
    theme = m.part.part_related_by(THEME_REL)
    scheme = dict(re.findall(SCHEME_RE, theme.blob.decode("utf8", "ignore")))
    print(f"\nmaster {mi}: theme colours {scheme}")
    for l in m.slide_layouts:
        print(f"  layout {l.name!r}: {phs(l)}")

for si, s in enumerate(prs.slides, 1):
    texts = [sh.text_frame.text.strip().replace("\n", " / ")[:60] for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
    master = next(i for i, m in enumerate(prs.slide_masters) if s.slide_layout in list(m.slide_layouts))
    print(f"\nslide {si}: layout {s.slide_layout.name!r} (master {master})")
    print(f"  {phs(s)}")
    for sh in s.shapes:
        if not sh.is_placeholder:
            print(f"  shape {sh.shape_type} {sh.name!r} {box(sh)}")
    if texts:
        print(f"  text: {texts}")

if "--suggest" in sys.argv:
    suggest(prs, sys.argv[1])

if "--render" in sys.argv:
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from manual import render_pdf
    out = pathlib.Path(sys.argv[sys.argv.index("--render") + 1]).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "template.pptx"
    tmp.write_bytes(path.read_bytes())
    render_pdf(tmp)  # then: pdftoppm -r 60 -png <dir>/template.pdf <dir>/t  and read the PNGs
