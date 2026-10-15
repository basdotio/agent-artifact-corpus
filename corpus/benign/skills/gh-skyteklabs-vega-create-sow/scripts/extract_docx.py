# /// script
# requires-python = ">=3.10"
# dependencies = ["python-docx>=1.1"]
# ///
"""Print a .docx RFP as plain text, paragraphs and tables in document order.

    uv run extract_docx.py RFP.docx

Table rows print as `| cell | cell |`, since RFPs often keep requirements in tables.
"""

import sys

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)


def table_lines(table):
    for row in table.rows:
        cells, seen = [], set()
        for cell in row.cells:
            # A merged cell appears once per grid column it spans; print it once.
            if id(cell._tc) in seen:
                continue
            seen.add(id(cell._tc))
            cells.append(" / ".join(p.text.strip() for p in cell.paragraphs if p.text.strip()))
        yield "| " + " | ".join(cells) + " |"


def extract(path):
    doc = Document(path)
    out = []
    for block in blocks(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            style = block.style.name if block.style is not None else ""
            if style.startswith("Heading"):
                level = style.removeprefix("Heading").strip()
                text = "#" * (int(level) if level.isdigit() else 1) + " " + text
            elif "List" in style:
                text = "- " + text
            out.append(text)
        else:
            out.extend(table_lines(block))
            out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: extract_docx.py RFP.docx")
    print(extract(sys.argv[1]))
