---
name: "pdf"
description: "Use when tasks involve reading, creating, reviewing, filling, or signing PDF/Word documents. Covers rendering (Poppler), generation (reportlab), extraction (pdfplumber, pypdf), form filling (pymupdf), and e-signature placement. Also trigger on: fill this form, sign this document, complete this PDF."
---


# PDF Skill

## When to use
- Read or review PDF content where layout and visuals matter.
- Create PDFs programmatically with reliable formatting.
- Validate final rendering before delivery.

## Workflow
1. Prefer visual review: render PDF pages to PNGs and inspect them.
   - Use `pdftoppm` if available.
   - If unavailable, install Poppler or ask the user to review the output locally.
2. Use `reportlab` to generate PDFs when creating new documents.
3. Use `pdfplumber` (or `pypdf`) for text extraction and quick checks; do not rely on it for layout fidelity.
4. After each meaningful update, re-render pages and verify alignment, spacing, and legibility.

## Temp and output conventions
- Use `tmp/pdfs/` for intermediate files; delete when done.
- Write final artifacts under `output/pdf/` when working in this repo.
- Keep filenames stable and descriptive.

## Dependencies (install if missing)
Prefer `uv` for dependency management.

Python packages:
```
uv pip install reportlab pdfplumber pypdf
```
If `uv` is unavailable:
```
python3 -m pip install reportlab pdfplumber pypdf
```
System tools (for rendering):
```
# macOS (Homebrew)
brew install poppler

# Ubuntu/Debian
sudo apt-get install -y poppler-utils
```

If installation isn't possible in this environment, tell the user which dependency is missing and how to install it locally.

## Environment
No required environment variables.

## Rendering command
```
pdftoppm -png $INPUT_PDF $OUTPUT_PREFIX
```

## Quality expectations
- Maintain polished visual design: consistent typography, spacing, margins, and section hierarchy.
- Avoid rendering issues: clipped text, overlapping elements, broken tables, black squares, or unreadable glyphs.
- Charts, tables, and images must be sharp, aligned, and clearly labeled.
- Use ASCII hyphens only. Avoid U+2011 (non-breaking hyphen) and other Unicode dashes.
- Citations and references must be human-readable; never leave tool tokens or placeholder strings.

## Final checks
- Do not deliver until the latest PNG inspection shows zero visual or formatting defects.
- Confirm headers/footers, page numbering, and section transitions look polished.
- Keep intermediate files organized or remove them after final approval.

---

## Filling non-fillable PDFs

Use PyMuPDF (fitz) to insert text and images at precise positions on PDFs that lack interactive form fields.

### Additional dependency
```
uv pip install pymupdf
```

### Workflow

1. **Analyze structure** — Extract text positions to map form layout:
```python
import fitz
doc = fitz.open(pdf_path)
for page in doc:
    text_dict = page.get_text("dict")
    for block in text_dict["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        bbox = span["bbox"]  # (x0, y0, x1, y1)
                        print(f"'{text}' at y={bbox[1]:.1f} x={bbox[0]:.1f}")
```

2. **Calculate fill positions** — Form boxes are typically 18-25pt below their labels. PDF coordinates: origin top-left, 72 pts/inch, Y increases downward. US Letter = 612x792pt.

3. **Insert text**:
```python
page.insert_text((x, y), "value", fontsize=11, color=(0, 0, 0))
```

4. **Insert images** (signatures):
```python
page.insert_image(fitz.Rect(x0, y0, x1, y1), filename="signature.png")
```
Use PNG with transparent background. Maintain aspect ratio.

### Troubleshooting
| Issue | Fix |
|-------|-----|
| Text in wrong position | Re-run analysis, add 18-25pt to label y for input box |
| Text too large/small | Default 11pt; use 7-8pt for dense tables |
| Signature doesn't fit | Check aspect ratio matches rect proportions |
| Text overlaps content | Reduce fontsize, verify inserting in box not on label |

### Why PyMuPDF over other libraries
PyPDF2/fillpdf only work with fillable forms. reportlab creates new PDFs (can't overlay). PyMuPDF inserts text/images at any position on existing PDFs.

---

## Signing and filling documents

Complete workflow for filling forms and adding e-signatures to PDF and Word documents.

**Scripts location**: `~/.claude/scripts/sign-document/`
**Signature assets**: `~/.claude/scripts/sign-document/assets/`

### Additional dependencies
```bash
pip install pypdf reportlab pdf2image python-docx cairosvg pillow
brew install poppler  # Required for pdf2image on macOS
```

### Decision tree

```
Input document?
├── PDF
│   ├── Has fillable fields? → Fillable PDF Workflow
│   └── No fillable fields? → Annotation-Based Workflow
└── Word (.docx) → Word Document Workflow

All workflows end with → Add Signature → Export as PDF
```

### Step 1: Detect document type
```bash
file "$DOCUMENT_PATH"
```

### Step 2: Check for fillable fields (PDF only)
```bash
python ~/.claude/scripts/sign-document/check_fillable_fields.py "$INPUT_PDF"
```

### Fillable PDF workflow
```bash
# Extract field info
python ~/.claude/scripts/sign-document/extract_form_field_info.py "$INPUT_PDF" field_info.json

# Convert to images for visual reference
python ~/.claude/scripts/sign-document/convert_pdf_to_images.py "$INPUT_PDF" form_images/

# Fill the form (create field_values.json first)
python ~/.claude/scripts/sign-document/fill_fillable_fields.py "$INPUT_PDF" field_values.json filled.pdf
```

**field_values.json format:**
```json
[
  {"field_id": "last_name", "description": "Last name", "page": 1, "value": "Cai"},
  {"field_id": "agree_checkbox", "description": "Agreement", "page": 2, "value": "/On"}
]
```

Value formats: Text → string, Checkbox → `"/On"` or `"/Yes"`, Radio → value from `radio_options`, Dropdown → value from `choice_options`.

### Annotation-based workflow (non-fillable PDFs)
```bash
# Convert to images, analyze layout, create fields.json
python ~/.claude/scripts/sign-document/convert_pdf_to_images.py "$INPUT_PDF" form_images/

# Validate bounding boxes
python ~/.claude/scripts/sign-document/check_bounding_boxes.py fields.json
python ~/.claude/scripts/sign-document/create_validation_image.py 1 fields.json form_images/page_1.png validation.png

# Fill
python ~/.claude/scripts/sign-document/fill_pdf_form_with_annotations.py "$INPUT_PDF" fields.json filled.pdf
```

Bounding box format: `[left, top, right, bottom]` in pixels. Label and entry boxes MUST NOT overlap.

### Word document workflow
```python
from docx import Document
doc = Document('template.docx')
replacements = {'{{name}}': 'Jeremy Cai', '{{date}}': 'January 13, 2026'}
for paragraph in doc.paragraphs:
    for key, value in replacements.items():
        if key in paragraph.text:
            for run in paragraph.runs:
                if key in run.text:
                    run.text = run.text.replace(key, value)
doc.save('filled.docx')
```

### Add signature and export (final step)
```bash
python ~/.claude/scripts/sign-document/add_signature_and_export.py filled.pdf output.pdf
```

| Option | Default | Description |
|--------|---------|-------------|
| `--position` | `bottom-right` | `bottom-left`, `bottom-right`, `bottom-center` |
| `--margin` | `50` | Points from page edge |
| `--width` | `200` | Signature width in points |
| `--page` | `-1` (last) | Page to sign (0-indexed, -1=last) |
| `--no-signature` | false | Convert to PDF without signature |

### User data reference

When filling documents for Jeremy Cai:
- Full Name: Jeremy Cai
- DOB: April 21, 1995
- Height: 182cm / 6'0"
- Locations: Park City UT, Chicago IL, Los Angeles CA
- Occupation: Serial Entrepreneur & Angel Investor
- Companies: Fountain, Italic, Carbon (acquired by Perplexity), Blemish, Courtly
- Spouse: Katherine (Kati) Holland Cai (b. Mar 23, 1994)
- Parents: Emily Chen (b. Apr 16, 1963), James Cai (b. Nov 10, 1963)
- Sister: Jillian Cai (b. Mar 7, 1998)
