#!/usr/bin/env python3
"""content.md  ->  <out>.html  ->  <out>.pdf   (A4, print-ready)

usage:  python3 build.py content.md out/notes.pdf [--html-only]

Frontmatter keys (all optional except title):
  course, chapter, title, institution, source, accent (#hex), lang (sl|en|de|hr|it),
  solutions (inline|end), binding (left|none), paper (A4|Letter)
"""
import sys, re, pathlib, asyncio, html, json
from markdown_it import MarkdownIt
from mdit_py_plugins.container import container_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diagrams

I18N = {
    "sl": dict(def_="Definicija", thm="Izrek", ex="Zgled", warn="Pozor", idea="Ideja", summary="Povzetek", proof="Dokaz",
               task="Naloga", sol="Rešitev", toc="Vsebina", space="prostor za reševanje", solutions="Rešitve nalog", video="Video razlage"),
    "en": dict(def_="Definition", thm="Theorem", ex="Example", warn="Watch out", idea="Idea", summary="Summary", proof="Proof",
               task="Exercise", sol="Solution", toc="Contents", space="work space", solutions="Solutions", video="Video explanations"),
    "de": dict(def_="Definition", thm="Satz", ex="Beispiel", warn="Achtung", idea="Idee", summary="Zusammenfassung", proof="Beweis",
               task="Aufgabe", sol="Lösung", toc="Inhalt", space="Platz zum Rechnen", solutions="Lösungen", video="Videoerklärungen"),
    "hr": dict(def_="Definicija", thm="Teorem", ex="Primjer", warn="Oprez", idea="Ideja", summary="Sažetak", proof="Dokaz",
               task="Zadatak", sol="Rješenje", toc="Sadržaj", space="prostor za rješavanje", solutions="Rješenja", video="Video objašnjenja"),
    "it": dict(def_="Definizione", thm="Teorema", ex="Esempio", warn="Attenzione", idea="Idea", summary="Riepilogo", proof="Dimostrazione",
               task="Esercizio", sol="Soluzione", toc="Indice", space="spazio per lo svolgimento", solutions="Soluzioni", video="Video spiegazioni"),
}

def main():
    src = pathlib.Path(sys.argv[1]).resolve()
    out_pdf = pathlib.Path(sys.argv[2]).resolve()
    html_only = "--html-only" in sys.argv
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")

    # ---- frontmatter
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if k.strip():
                meta[k.strip()] = v.strip().strip('"')
        text = text[m.end():]
    lang = meta.get("lang", "sl")
    T = I18N.get(lang, I18N["en"])
    if "labels" in meta:  # optional override: labels: task=Vaja;sol=Odgovor
        for kv in meta["labels"].split(";"):
            k, _, v = kv.partition("=")
            if k.strip() in T: T[k.strip()] = v.strip()
    accent = meta.get("accent", "#1d5c8a")
    PAL = {"accent": accent, "tint": "#eaf1f7", "ink": "#1b1f24", "muted": "#6b7280", "rule": "#d7dce2",
           "warn": "#b7791f", "cat": [accent, "#c0392b", "#2e7d4f", "#6b4fa0"], "t": T}

    # ---- diagrams: "@@name args" -> raw html block
    def diag_sub(mm):
        name, args = mm.group(1), (mm.group(2) or "").strip()
        fn = diagrams.REGISTRY.get(name)
        if not fn:
            return f'<p class="missing">[unknown diagram: {name}]</p>'
        try:
            return "\n" + fn(PAL, args) + "\n"
        except Exception as e:  # never kill the build over one diagram
            return f'<p class="missing">[diagram {name} failed: {html.escape(str(e))}]</p>'
    text = re.sub(r"^@@(\w+)(?:[ \t]+(.*))?[ \t]*$", diag_sub, text, flags=re.M)

    # ---- display math must be its own block
    lines = text.split("\n"); fixed = []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("$$") and fixed and fixed[-1].strip() != "":
            fixed.append("")
        fixed.append(ln)
        if ln.rstrip().endswith("$$") and i + 1 < len(lines) and lines[i + 1].strip() != "":
            fixed.append("")
    text = "\n".join(fixed)

    # ---- markdown
    md = MarkdownIt("commonmark", {"html": True, "typographer": False}).enable(["table", "strikethrough"])
    md.use(dollarmath_plugin, double_inline=False)
    BOXES = {"def": T["def_"], "thm": T["thm"], "ex": T["ex"], "warn": T["warn"], "idea": T["idea"],
             "summary": T["summary"], "proof": T["proof"], "task": T["task"], "sol": T["sol"], "video": T["video"]}

    def title_html(t):
        parts = re.split(r"(\$[^$]+\$)", t)
        return "".join(f'<span class="math">{html.escape(p[1:-1])}</span>' if p.startswith("$") else html.escape(p) for p in parts)

    def make_render(kind):
        def render(self, tokens, idx, options, env):
            t = tokens[idx]
            if t.nesting == 1:
                title = t.info.strip()[len(kind):].strip()
                head = (f'<div class="bx-head"><span class="bx-label">{BOXES[kind]}</span>'
                        + (f'<span class="bx-title">{title_html(title)}</span>' if title else "") + "</div>")
                return f'<div class="bx bx-{kind}">{head}<div class="bx-body">'
            return "</div></div>\n"
        return render
    for k in BOXES:
        md.use(container_plugin, name=k, render=make_render(k))
    md.add_render_rule("math_inline", lambda self, tokens, i, o, e: f'<span class="math">{html.escape(tokens[i].content)}</span>')
    md.add_render_rule("math_block", lambda self, tokens, i, o, e: f'<div class="math display">{html.escape(tokens[i].content)}</div>')
    body_html = md.render(text)
    # youtu.be/<id> codes become clickable links (PDF keeps them)
    body_html = re.sub(r'<code>(youtu\.be/[\w-]+)</code>', r'<a class="yt" href="https://\1"><code>\1</code></a>', body_html)
    body_html = re.sub(r'(?<![\w/])<code>([\w-]{11})</code>', r'<a class="yt" href="https://youtu.be/\1"><code>\1</code></a>', body_html)

    # ---- numbering + TOC
    toc = []; n = [0, 0]
    def num_h(mm):
        lvl, inner = mm.group(1), mm.group(2)
        if lvl == "1":
            n[0] += 1; n[1] = 0; num = f"{n[0]}"
        else:
            n[1] += 1; num = f"{n[0]}.{n[1]}"
        toc.append((lvl, num, inner))
        return f'<h{lvl} id="s{num.replace(".", "-")}"><span class="hnum">{num}</span>{inner}</h{lvl}>'
    body_html = re.sub(r"<h([12])>(.*?)</h\1>", num_h, body_html)
    toc_html = "".join(f'<li class="l{l}"><span class="tnum">{nm}</span>{t}</li>' for l, nm, t in toc)

    # ---- assemble page
    css = (HERE.parent / "theme" / "theme.css").read_text(encoding="utf-8").replace("ACCENT", accent)
    katex_dir = HERE / "node_modules" / "katex" / "dist"
    if not katex_dir.exists():
        sys.exit("KaTeX not installed – run scripts/setup.sh first")
    katex_css = (katex_dir / "katex.min.css").read_text(encoding="utf-8").replace("url(fonts/", f"url({katex_dir.as_uri()}/fonts/")
    katex_js = (katex_dir / "katex.min.js").read_text(encoding="utf-8")
    E = lambda k: html.escape(meta.get(k, ""))
    sol_end = meta.get("solutions", "inline") == "end"
    page = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<title>{E('course')} – {E('title')}</title>
<style>{katex_css}</style><style>{css}</style></head>
<body>
<section class="cover">
  <div class="cover-course">{E('course')}</div>
  <div class="cover-num">{E('chapter')}</div>
  <h1 class="cover-title">{E('title')}</h1>
  <div class="cover-meta">{E('institution')}<br>{E('source')}</div>
  <div class="toc"><div class="toc-head">{html.escape(T['toc'])}</div><ul>{toc_html}</ul></div>
</section>
<main>{body_html}</main>
<script>{katex_js}</script>
<script>
const SOL_END = {json.dumps(sol_end)};
const T_SOL = {json.dumps(T['solutions'])}, T_TASK = {json.dumps(T['task'])};
if (SOL_END) {{
  const main = document.querySelector('main');
  const h = document.createElement('h1'); h.innerHTML = '<span class="hnum"></span>' + T_SOL; h.className = 'solutions-head';
  const app = document.createElement('section'); app.className = 'solutions'; app.appendChild(h);
  let k = 0;
  document.querySelectorAll('main .bx-task').forEach(t => {{
    k++; let s = t.nextElementSibling; if (s && s.classList.contains('space')) s = s.nextElementSibling;
    if (s && s.classList.contains('bx-sol')) {{
      s.querySelector('.bx-label').textContent = T_SOL.split(' ')[0] + ' – ' + T_TASK + ' ' + k;
      app.appendChild(s);
    }}
  }});
  main.appendChild(app);
}}
// keep-together groups (Chromium does not honour break-after:avoid reliably)
const wrap = (a, b) => {{ const w = document.createElement('div'); w.className = 'keep'; a.parentNode.insertBefore(w, a); w.appendChild(a); w.appendChild(b); }};
document.querySelectorAll('main .bx-def, main .bx-thm').forEach(t => {{ const f = t.nextElementSibling; if (f && f.tagName === 'FIGURE') wrap(t, f); }});
document.querySelectorAll('main .bx-task').forEach(t => {{ const s = t.nextElementSibling; if (s && s.classList.contains('space')) wrap(t, s); }});
document.querySelectorAll('main h1, main h2, main h3').forEach(h => {{ const n = h.nextElementSibling; if (n) wrap(h, n); }});
document.querySelectorAll('.math').forEach(el => {{
  try {{ katex.render(el.textContent, el, {{displayMode: el.classList.contains('display'), throwOnError: false}}); }}
  catch (e) {{ el.classList.add('math-error'); }}
}});
</script>
</body></html>"""
    out_html = out_pdf.with_suffix(".html")
    out_html.write_text(page, encoding="utf-8")
    if html_only:
        print("wrote", out_html); return

    async def render():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page()
            await pg.goto(out_html.as_uri(), wait_until="load")
            await pg.evaluate("document.fonts.ready")
            footer = (f'<div style="width:100%;font-family:Inter,sans-serif;font-size:8.5px;color:#6b7280;padding:0 16mm;'
                      f'display:flex;justify-content:space-between;align-items:center">'
                      f'<span>{E("course")} · {E("chapter")}{"." if meta.get("chapter") else ""} {E("title")}</span>'
                      f'<span style="color:{accent};font-weight:600"><span class="pageNumber"></span></span></div>')
            binding = meta.get("binding", "left")
            margin = {"top": "18mm", "bottom": "18mm", "left": "22mm" if binding == "left" else "18mm", "right": "16mm" if binding == "left" else "18mm"}
            await pg.pdf(path=str(out_pdf), format=meta.get("paper", "A4"), print_background=True,
                         display_header_footer=True, header_template="<div></div>", footer_template=footer, margin=margin)
            await b.close()
    asyncio.run(render())
    print("wrote", out_pdf)

if __name__ == "__main__":
    main()
