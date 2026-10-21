"""Tiny markdown -> PDF writer (headings, bullets, paragraphs) built on fpdf2.

Built-in PDF fonts only support Latin-1, so a few common symbols are swapped for
plain equivalents (for example the rupee sign becomes 'Rs.') instead of crashing.
"""
from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

_SWAPS = {
    "₹": "Rs.", "€": "EUR ", "£": "GBP ", "“": '"', "”": '"', "‘": "'", "’": "'",
    "–": "-", "—": "-", "…": "...", "•": "-", "→": "->", "≈": "~", "×": "x", "\u00a0": " ",
}


def _safe(text: str) -> str:
    for old, new in _SWAPS.items():
        text = text.replace(old, new)
    text = re.sub(r"[*`]|__", "", text)  # drop markdown emphasis markers
    return text.encode("latin-1", "replace").decode("latin-1")


def _break_long_words(text: str, width: int = 70) -> str:
    """Insert spaces into very long tokens (URLs) so they can wrap."""
    return " ".join(
        w if len(w) <= width else " ".join(w[i:i + width] for i in range(0, len(w), width))
        for w in text.split(" ")
    )


def md_to_pdf(markdown: str, path, title: str = "") -> Path:
    path = Path(path)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    if title:
        pdf.set_title(_safe(title))

    def write(text: str, size: float, bold: bool = False, indent: float = 0, gap: float = 1.5):
        pdf.set_font("Helvetica", style="B" if bold else "", size=size)
        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(0, size * 0.5 + 2.2, _break_long_words(text), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(gap)

    for raw in markdown.splitlines():
        line = _safe(raw.rstrip())
        if not line.strip():
            pdf.ln(2)
        elif line.startswith("### "):
            write(line[4:], 11.5, bold=True, gap=1)
        elif line.startswith("## "):
            write(line[3:], 13.5, bold=True, gap=1.5)
        elif line.startswith("# "):
            write(line[2:], 17, bold=True, gap=3)
        elif line.lstrip().startswith(("- ", "* ")):
            write("- " + line.lstrip()[2:], 10.5, indent=4)
        else:
            write(line, 10.5)

    pdf.output(str(path))
    return path