#!/usr/bin/env python3
"""Render a Markdown resume to a one-column, text-based PDF and report how every line wraps.

Usage:
  python3 make_pdf.py resume.md Resume.pdf [--font 10.5] [--paper letter|a4]

Needs reportlab (pip install reportlab). Reads the Markdown, writes only the PDF, makes no
network calls. The PDF is plain selectable text in reading order with real links, so applicant
tracking systems parse it the same way a person reads it.

The report lists the page count, then every paragraph that wraps:
  SHORTEN  the second line holds only a few words; tighten it to one line
  OK       the second line is about half full or more; leave it
"""
import argparse
import difflib
from collections import Counter
import html
import re
import shutil
import subprocess
import sys

try:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate
except ImportError:
    sys.exit("make_pdf.py needs reportlab: pip install reportlab")

LINK = "#1a4fa0"
MIN_FONT = 10


esc = html.escape


def inline(text):
    """Markdown links and **bold** to reportlab markup."""
    out, pos = [], 0
    for m in re.finditer(r"\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*", text):
        out.append(esc(text[pos:m.start()]))
        if m.group(3):
            out.append(f"<b>{esc(m.group(3))}</b>")
        elif m.group(2).startswith(("https://", "http://", "mailto:")):
            out.append(f'<a href="{esc(m.group(2))}" color="{LINK}">{esc(m.group(1))}</a>')
        else:  # any other scheme stays visible as plain text
            out.append(esc(m.group(0)))
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def styles(fs):
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=fs, leading=fs * 1.22)
    return {
        "name": ParagraphStyle("name", parent=body, fontName="Helvetica-Bold", fontSize=fs + 8, leading=(fs + 8) * 1.15),
        "contact": ParagraphStyle("contact", parent=body, spaceAfter=2),
        "h2": ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=fs + 0.7, leading=(fs + 0.7) * 1.2,
                             spaceBefore=5),
        "h3": ParagraphStyle("h3", parent=body, spaceBefore=2.5),
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=10, bulletIndent=1, spaceBefore=0.6),
        "body": body,
    }


def build(md, fs):
    """Turn Markdown lines into flowables. Returns (flowables, [(line number, paragraph)])."""
    st = styles(fs)
    lines = md.splitlines()
    nonempty = [(n, raw.rstrip()) for n, raw in enumerate(lines, 1) if raw.strip()]
    following = {n: nonempty[k + 1][1] for k, (n, _) in enumerate(nonempty[:-1])}
    flow, wraps, skip, first_body = [], [], False, True
    for n, raw in nonempty:
        if skip:
            skip = False
            continue
        if raw.startswith("# "):
            p = Paragraph(esc(raw[2:]), st["name"])
        elif raw.startswith("## "):
            flow.append(Paragraph(esc(raw[3:].strip().upper()), st["h2"]))
            flow.append(HRFlowable(width="100%", thickness=0.6, color=HexColor("#555555"), spaceBefore=1, spaceAfter=2))
            continue
        elif raw.startswith("### "):
            nxt = following.get(n, "")
            if nxt.startswith("**") and " | " in nxt:
                # "Company" + "**Title** | dates" print as one line: Title | Company | dates
                title, dates = nxt.rsplit(" | ", 1)
                p = Paragraph(f"{inline(title)} | <b>{inline(raw[4:])}</b> | {inline(dates)}", st["h3"])
                skip = True
            else:
                p = Paragraph(f"<b>{inline(raw[4:])}</b>", st["h3"])
        elif re.match(r"\s*[-*]\s+", raw):
            p = Paragraph(inline(re.sub(r"^\s*[-*]\s+", "", raw)), st["bullet"], bulletText="•")
        elif first_body:
            p = Paragraph(inline(raw), st["contact"])
        else:
            p = Paragraph(inline(raw), st["body"])
        if not raw.startswith("#"):
            first_body = False
        flow.append(p)
        wraps.append((n, p))
    return flow, wraps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("resume")
    ap.add_argument("pdf")
    ap.add_argument("--font", type=float, default=10.5)
    ap.add_argument("--paper", choices=["letter", "a4"], default="letter")
    a = ap.parse_args()
    if a.font < MIN_FONT:
        print(f"note: {a.font} pt is below {MIN_FONT} pt and hard to read; cut content instead", file=sys.stderr)
    try:
        md = open(a.resume, encoding="utf-8-sig").read()
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"cannot read {a.resume}: {e}")
    # Limit: built-in Helvetica covers Western European text only; register a TTF font if this warning bites.
    odd = sorted({c for c in md if not c.encode("cp1252", "ignore")})
    if odd:
        print(f"warning: these characters will not print in the built-in font: {' '.join(odd[:20])}", file=sys.stderr)

    paper = letter if a.paper == "letter" else A4
    margin_x, margin_y = 0.5 * inch, 0.45 * inch
    name = next((l[2:].strip() for l in md.splitlines() if l.startswith("# ")), "Resume")
    pages = []
    doc = SimpleDocTemplate(a.pdf, pagesize=paper, leftMargin=margin_x, rightMargin=margin_x,
                            topMargin=margin_y, bottomMargin=margin_y, title=f"{name} - Resume", author=name)
    flow, wraps = build(md, a.font)
    doc.build(flow, onFirstPage=lambda c, d: pages.append(1), onLaterPages=lambda c, d: pages.append(1))

    width = paper[0] - 2 * margin_x
    print(f"{a.pdf}: {len(pages)} page(s), {a.font} pt, {a.paper}")
    for n, p in wraps:
        avail = width - p.style.leftIndent
        p.wrap(avail, 10_000)
        lines = p.blPara.lines
        if len(lines) < 2:
            continue
        last = lines[-1]
        extra = last[0] if isinstance(last, tuple) else last.extraSpace
        full = 1 - extra / avail
        verdict = "SHORTEN" if full < 0.35 else "OK"
        print(f"line {n:>3}: {len(lines)} lines, last line {full:4.0%} full  {verdict}")
    print(text_check(md, a.pdf))



def read_back(pdf):
    """The PDF's text layer, as screening software would read it: pypdf if installed, else pdftotext."""
    try:
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(pdf).pages)
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    return None


def text_check(md, pdf):
    """Every word of the resume comes back out of the PDF, in nearly the same order.
    The PDF joins each company and job title on one line, so a few words move by design."""
    text = read_back(pdf)
    if text is None:
        return "text check: skipped; pip install pypdf to confirm screening software can read the PDF"
    tokens = lambda t: re.findall(r"\w+", t.lower())
    want = tokens(re.sub(r"\]\([^)]*\)", "]", md))  # link targets are not printed
    got = tokens(text)
    missing = sorted((Counter(want) - Counter(got)).elements())
    in_order = sum(b.size for b in difflib.SequenceMatcher(None, want, got, autojunk=False).get_matching_blocks())
    share = in_order / max(len(want), 1)
    ok = not missing and share >= 0.9
    return (f"text check: {len(want) - len(missing)} of {len(want)} words read back, {share:.0%} in order  "
            + ("OK" if ok else "PROBLEM: screening software may misread this PDF")
            + (f"; missing: {' '.join(missing[:10])}" if missing else ""))

if __name__ == "__main__":
    main()
