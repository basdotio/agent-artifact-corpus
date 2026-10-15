#!/usr/bin/env python3
"""
Build ATS-safe DOCX and PDF files from a resume or cover-letter Markdown source.

Layout: single column, left aligned, plain section headings, dates right
aligned on the job-title line, contact info in the document body (never in a
Word header/footer), no tables, text boxes, images, icons, or columns.
Fonts are embedded (PDF) and no ligatures are produced, so the text layer
extracts cleanly.

Resume source format (see templates/resume.md):

    # Full Name
    City, ST | email | phone | linkedin.com/in/x | github.com/x

    ## Summary
    Three or four sentences.

    ## Experience
    ### Job Title | Company | Location | Jan 2023 - Present
    - Bullet

    ## Education
    ### B.S. Computer Science | School | City, ST | 2008

    ## Skills
    - Languages: Go, Rust, Python

Cover letter source: same "# Name" and contact line, then plain paragraphs
(greeting, body, sign-off). Use --type cover.

Usage:
    build.py resume.md --out-dir DIR --basename First-Last-Resume-Company
    build.py cover-letter.md --type cover --out-dir DIR --basename First-Last-Cover-Letter-Company
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- parsing


@dataclass
class Entry:
    title: str
    org: str = ""
    location: str = ""
    dates: str = ""
    bullets: list[str] = field(default_factory=list)
    text: list[str] = field(default_factory=list)


@dataclass
class Section:
    name: str
    paragraphs: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)


@dataclass
class Doc:
    name: str = ""
    contact: str = ""
    sections: list[Section] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)  # cover letters


def strip_md(s: str) -> str:
    """Remove inline markdown the builders do not render (keep plain text)."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = s.replace("**", "").replace("__", "").replace("`", "")
    return s.strip()


def parse(path: Path, kind: str) -> Doc:
    doc = Doc()
    lines = path.read_text(encoding="utf-8").splitlines()
    # drop HTML comments (used for notes in sources)
    text = "\n".join(lines)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = text.splitlines()

    sec: Section | None = None
    ent: Entry | None = None
    para: list[str] = []

    def flush_para():
        nonlocal para
        if para:
            # short multi-line blocks (sign-offs, addresses) keep their line breaks
            keep = kind == "cover" and len(para) > 1 and all(len(x.strip()) <= 40 for x in para)
            p = ("\n" if keep else " ").join(strip_md(x) for x in para)
            if kind == "cover":
                doc.paragraphs.append(p)
            elif ent is not None:
                ent.text.append(p)
            elif sec is not None:
                sec.paragraphs.append(p)
            para = []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("# ") and not doc.name:
            doc.name = strip_md(line[2:])
            continue
        if doc.name and not doc.contact and line.strip() and not line.startswith("#"):
            doc.contact = strip_md(line)
            continue
        if kind == "cover":
            if not line.strip():
                flush_para()
            else:
                para.append(line)
            continue
        if line.startswith("## "):
            flush_para()
            sec = Section(strip_md(line[3:]))
            doc.sections.append(sec)
            ent = None
            continue
        if line.startswith("### "):
            flush_para()
            parts = [strip_md(p) for p in line[4:].split("|")]
            parts += [""] * (4 - len(parts))
            ent = Entry(*parts[:4])
            if sec is None:
                sys.exit(f"{path}: '### {parts[0]}' appears before any '## Section'")
            sec.entries.append(ent)
            continue
        m = re.match(r"^\s*[-*•]\s+(.*)", line)
        if m:
            flush_para()
            b = strip_md(m.group(1))
            if ent is not None:
                ent.bullets.append(b)
            elif sec is not None:
                sec.bullets.append(b)
            continue
        if not line.strip():
            flush_para()
        else:
            para.append(line)
    flush_para()
    if not doc.name:
        sys.exit(f"{path}: first line must be '# Full Name'")
    return doc


def stack_label(b: str) -> tuple[str, str]:
    """'Stack: Go, Kubernetes' role bullet -> ('Stack', 'Go, Kubernetes'); other bullets unchanged."""
    m = re.match(r"^(Stack):\s+(.*)$", b)
    return (m.group(1), m.group(2)) if m else ("", b)


def split_label(b: str) -> tuple[str, str]:
    """'Languages: Go, Rust' -> ('Languages', 'Go, Rust') for skill rows."""
    m = re.match(r"^([A-Za-z0-9 &/+\-]{2,40}):\s+(.*)$", b)
    return (m.group(1), m.group(2)) if m else ("", b)


# ---------------------------------------------------------------- DOCX


def build_docx(doc: Doc, out: Path, kind: str, font: str, size: float, date_line: str):
    from docx import Document
    from docx.enum.text import WD_TAB_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt

    d = Document()
    for s in d.sections:
        s.page_height, s.page_width = Inches(11), Inches(8.5)
        s.left_margin = s.right_margin = Inches(0.7)
        s.top_margin = s.bottom_margin = Inches(0.6)
    usable = Inches(8.5 - 1.4)

    st = d.styles["Normal"]
    st.font.name = font
    st.font.size = Pt(size)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), font)
    st.paragraph_format.space_after = Pt(0)
    st.paragraph_format.space_before = Pt(0)
    st.paragraph_format.line_spacing = 1.05

    def para(text="", bold=False, italic=False, sz=None, before=0, after=0):
        p = d.add_paragraph()
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        if text:
            r = p.add_run(text)
            r.bold, r.italic = bold, italic
            if sz:
                r.font.size = Pt(sz)
        return p

    def heading(text):
        p = para(text.upper(), bold=True, sz=size + 0.5, before=8, after=3)
        pPr = p._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "444444")):
            bottom.set(qn(k), v)
        bdr.append(bottom)
        pPr.append(bdr)

    def title_line(left, right, before=5):
        p = para(before=before)
        p.paragraph_format.tab_stops.add_tab_stop(usable, WD_TAB_ALIGNMENT.RIGHT)
        r = p.add_run(left)
        r.bold = True
        if right:
            p.add_run("\t" + right)

    def bullet(text, label=""):
        p = d.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(1.5)
        p.paragraph_format.left_indent = Inches(0.22)
        p.paragraph_format.first_line_indent = Inches(-0.16)
        if label:
            r = p.add_run(label + ": ")
            r.bold = True
        p.add_run(text)

    para(doc.name, bold=True, sz=size + 7, after=1)
    para(doc.contact, after=4)

    if kind == "cover":
        para(date_line, before=10, after=10)
        for ptext in doc.paragraphs:
            p = para(after=9)
            for i, line in enumerate(ptext.split("\n")):
                r = p.add_run(line)
                if i < ptext.count("\n"):
                    r.add_break()
    else:
        for sec in doc.sections:
            heading(sec.name)
            for ptext in sec.paragraphs:
                para(ptext, after=2)
            is_skills = sec.name.lower().startswith(("skill", "technical skill", "core skill"))
            for b in sec.bullets:
                if is_skills:
                    lab, val = split_label(b)
                    p = para(after=1.5)
                    if lab:
                        p.add_run(lab + ": ").bold = True
                    p.add_run(val)
                else:
                    bullet(b)
            for e in sec.entries:
                title_line(e.title, e.dates)
                sub = ", ".join(x for x in (e.org, e.location) if x)
                if sub:
                    para(sub, italic=False, after=2)
                for t in e.text:
                    para(t, after=2)
                for b in e.bullets:
                    lab, val = stack_label(b)
                    bullet(val, label=lab)

    cp = d.core_properties
    cp.author = doc.name
    cp.title = f"{doc.name} - {'Cover Letter' if kind == 'cover' else 'Resume'}"
    d.save(out)


# ---------------------------------------------------------------- PDF


def register_font(font: str) -> tuple[str, str]:
    """Embed a TrueType font if available; fall back to Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = {
        "Arial": ("Arial.ttf", "Arial Bold.ttf"),
        "Georgia": ("Georgia.ttf", "Georgia Bold.ttf"),
        "Calibri": ("calibri.ttf", "calibrib.ttf"),
    }
    dirs = [
        Path("/System/Library/Fonts/Supplemental"),
        Path("/Library/Fonts"),
        Path.home() / "Library/Fonts",
        Path("/usr/share/fonts/truetype/msttcorefonts"),
        Path("/usr/share/fonts/truetype/liberation"),
    ]
    reg, bold = candidates.get(font, candidates["Arial"])
    for dd in dirs:
        r, b = dd / reg, dd / bold
        if r.exists() and b.exists():
            pdfmetrics.registerFont(TTFont(f"{font}-R", str(r)))
            pdfmetrics.registerFont(TTFont(f"{font}-B", str(b)))
            pdfmetrics.registerFontFamily(f"{font}-R", normal=f"{font}-R", bold=f"{font}-B")
            return f"{font}-R", f"{font}-B"
    print(f"note: {font} TTF not found, using built-in Helvetica", file=sys.stderr)
    return "Helvetica", "Helvetica-Bold"


def build_pdf(doc: Doc, out: Path, kind: str, font: str, size: float, date_line: str):
    from xml.sax.saxutils import escape

    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

    from reportlab import rl_config

    reg, bold = register_font(font)
    rl_config.canvas_basefontname = reg  # avoid an unused, unembedded Helvetica in the PDF
    lead = size * 1.25

    base = ParagraphStyle("base", fontName=reg, fontSize=size, leading=lead)
    name_st = ParagraphStyle("name", parent=base, fontName=bold, fontSize=size + 7, leading=size + 10)
    contact_st = ParagraphStyle("contact", parent=base, spaceAfter=4)
    body_st = ParagraphStyle("body", parent=base, spaceAfter=2)
    letter_st = ParagraphStyle("letter", parent=base, spaceAfter=9, leading=size * 1.35)
    bullet_st = ParagraphStyle(
        "bullet", parent=base, leftIndent=14, bulletIndent=3, spaceAfter=1.5, bulletFontName=reg
    )

    class Heading(Flowable):
        def __init__(self, text, width):
            super().__init__()
            self.text, self.width = text.upper(), width
            self.height = size + 7

        def wrap(self, aw, ah):
            self.width = aw
            return aw, self.height

        def draw(self):
            c = self.canv
            c.setFont(bold, size + 0.5)
            c.drawString(0, 4, self.text)
            c.setStrokeColor(HexColor("#444444"))
            c.setLineWidth(0.6)
            c.line(0, 1, self.width, 1)

    class TitleLine(Flowable):
        """Bold title left, dates right, same baseline. Wraps title if needed."""

        def __init__(self, left, right):
            super().__init__()
            self.left, self.right = left, right

        def wrap(self, aw, ah):
            from reportlab.pdfbase.pdfmetrics import stringWidth

            self.aw = aw
            rw = stringWidth(self.right, reg, size) + 12 if self.right else 0
            self.fits = stringWidth(self.left, bold, size) <= aw - rw
            self.height = lead if self.fits else lead * 2
            return aw, self.height

        def draw(self):
            c = self.canv
            y = self.height - size
            c.setFont(bold, size)
            c.drawString(0, y, self.left)
            if self.right:
                c.setFont(reg, size)
                if self.fits:
                    c.drawRightString(self.aw, y, self.right)
                else:
                    c.drawString(0, y - lead, self.right)

    story = [Paragraph(escape(doc.name), name_st), Paragraph(escape(doc.contact), contact_st)]

    if kind == "cover":
        story += [Spacer(1, 10), Paragraph(escape(date_line), letter_st), Spacer(1, 2)]
        for p in doc.paragraphs:
            story.append(Paragraph("<br/>".join(escape(x) for x in p.split("\n")), letter_st))
    else:
        for sec in doc.sections:
            story += [Spacer(1, 6), Heading(sec.name, 0), Spacer(1, 3)]
            for p in sec.paragraphs:
                story.append(Paragraph(escape(p), body_st))
            is_skills = sec.name.lower().startswith(("skill", "technical skill", "core skill"))
            for b in sec.bullets:
                if is_skills:
                    lab, val = split_label(b)
                    txt = (f"<b>{escape(lab)}:</b> " if lab else "") + escape(val)
                    story.append(Paragraph(txt, ParagraphStyle("sk", parent=body_st, spaceAfter=1.5)))
                else:
                    story.append(Paragraph(escape(b), bullet_st, bulletText="•"))
            for e in sec.entries:
                story += [Spacer(1, 4), TitleLine(e.title, e.dates)]
                sub = ", ".join(x for x in (e.org, e.location) if x)
                if sub:
                    story.append(Paragraph(escape(sub), body_st))
                for t in e.text:
                    story.append(Paragraph(escape(t), body_st))
                for b in e.bullets:
                    lab, val = stack_label(b)
                    txt = (f"<b>{escape(lab)}:</b> " if lab else "") + escape(val)
                    story.append(Paragraph(txt, bullet_st, bulletText="•"))

    title = f"{doc.name} - {'Cover Letter' if kind == 'cover' else 'Resume'}"
    pdf = SimpleDocTemplate(
        str(out),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=title,
        author=doc.name,
        subject=title,
        creator="tech-resume skill",
    )
    pdf.build(story)


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("--type", choices=["resume", "cover"], default="resume")
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--basename", default=None, help="file name without extension")
    ap.add_argument("--font", default="Arial", choices=["Arial", "Georgia", "Calibri"])
    ap.add_argument("--size", type=float, default=10.5, help="body point size (10-11.5)")
    ap.add_argument("--date", default=None, help="cover letter date line (default: today)")
    ap.add_argument("--formats", default="docx,pdf")
    a = ap.parse_args()

    if not 9.5 <= a.size <= 12:
        sys.exit("--size must be between 9.5 and 12")
    import datetime as dt

    date_line = a.date or dt.date.today().strftime("%B %-d, %Y")
    doc = parse(a.source, a.type)
    out_dir = a.out_dir or a.source.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    base = a.basename or re.sub(r"\s+", "-", doc.name) + ("-Cover-Letter" if a.type == "cover" else "-Resume")

    made = []
    if "docx" in a.formats:
        p = out_dir / f"{base}.docx"
        build_docx(doc, p, a.type, a.font, a.size, date_line)
        made.append(p)
    if "pdf" in a.formats:
        p = out_dir / f"{base}.pdf"
        build_pdf(doc, p, a.type, a.font, a.size, date_line)
        made.append(p)
    for p in made:
        print(p)


if __name__ == "__main__":
    main()
