---
name: pptx
description: "Use this skill any time a .pptx file is involved in any way -- as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file; editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions \"deck,\" \"slides,\" \"presentation,\" or references a .pptx filename."
---

# PPTX Skill

**Note**: The agent's `read_file` tool cannot read binary .pptx files. Use the methods below instead.

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python -m markitdown presentation.pptx` (recommended) |
| Read without dependencies | Unzip + extract text from XML (see below) |
| Edit or create from template | Unpack → edit XML → repack (see Editing below) |
| Create from scratch | Use python-pptx or pptxgenjs (see Creating below) |

---

## Reading Content

### With markitdown (recommended)
```bash
python -m markitdown presentation.pptx
```

### Visual overview
```bash
libreoffice --headless --convert-to pdf presentation.pptx
pdftoppm -jpeg -r 150 presentation.pdf slide
# Creates slide-01.jpg, slide-02.jpg, etc.
```

### Zero-dependency fallback (no pip install needed)

Extract text from PPTX using only stdlib — useful when markitdown is not installed:

```python
import zipfile, xml.etree.ElementTree as ET, re

with zipfile.ZipFile('presentation.pptx') as z:
    # Get metadata (slide count, word count, author)
    if 'docProps/app.xml' in z.namelist():
        app = ET.parse(z.open('docProps/app.xml'))
        ns = {'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'}
        slides = app.findtext(f'{{{ns["ep"]}}}Slides', '')
        words = app.findtext(f'{{{ns["ep"]}}}Words', '')
        print(f"Slides: {slides}, Words: {words}")

    # Extract text from each slide
    slide_files = sorted(f for f in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', f))
    for sf in slide_files:
        tree = ET.parse(z.open(sf))
        texts = [elem.text for elem in tree.iter() if elem.tag.endswith('}t') and elem.text]
        slide_num = re.search(r'slide(\d+)', sf).group(1)
        print(f"\n--- Slide {slide_num} ---")
        print(' '.join(texts))

    # Extract speaker notes
    for sf in slide_files:
        slide_num = re.search(r'slide(\d+)', sf).group(1)
        notes_file = f'ppt/notesSlides/notesSlide{slide_num}.xml'
        if notes_file in z.namelist():
            tree = ET.parse(z.open(notes_file))
            texts = [elem.text for elem in tree.iter() if elem.tag.endswith('}t') and elem.text]
            if texts:
                print(f"\n--- Notes for Slide {slide_num} ---")
                print(' '.join(texts))
```

---

## Editing Existing Presentations

### Workflow

1. **Unpack** the .pptx (it's a ZIP archive):
   ```bash
   mkdir -p unpacked && unzip -o presentation.pptx -d unpacked/
   ```

2. **Inspect slides** in `unpacked/ppt/slides/` — each slide is an XML file (slide1.xml, slide2.xml, etc.)

3. **Edit XML** directly using the edit_file tool for targeted changes

4. **Repack** into a new .pptx:
   ```bash
   cd unpacked && zip -r ../output.pptx . -x ".*" && cd ..
   ```

### Using python-pptx for programmatic edits

```python
from pptx import Presentation
from pptx.util import Inches, Pt

prs = Presentation('input.pptx')

# Access slides
for slide in prs.slides:
    for shape in slide.shapes:
        if shape.has_text_frame:
            print(shape.text)

# Add a slide
slide_layout = prs.slide_layouts[1]  # Title and Content
slide = prs.slides.add_slide(slide_layout)
title = slide.shapes.title
title.text = "New Slide Title"

prs.save('output.pptx')
```

---

## Creating from Scratch

### With python-pptx (recommended)

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.33)
prs.slide_height = Inches(7.5)

# Title slide
slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
slide.background.fill.solid()
slide.background.fill.fore_color.rgb = RGBColor(0x1E, 0x27, 0x61)

txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(1.5))
tf = txBox.text_frame
p = tf.paragraphs[0]
p.text = "Title"
p.font.size = Pt(44)
p.font.bold = True
p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
p.font.name = "Georgia"

prs.save('output.pptx')
```

### With pptxgenjs (Node.js alternative)

Install: `npm install -g pptxgenjs`

```javascript
const pptxgen = require('pptxgenjs');
const pres = new pptxgen();

pres.defineLayout({ name: 'CUSTOM', width: 13.33, height: 7.5 });
pres.layout = 'CUSTOM';

const slide = pres.addSlide();
slide.background = { color: '1E2761' };

slide.addText('Title', {
  x: 0.5, y: 0.5, w: '90%', h: 1.5,
  fontSize: 44, bold: true, color: 'FFFFFF',
  fontFace: 'Georgia'
});

pres.writeFile({ fileName: 'output.pptx' });
```

---

## Design Ideas

**Don't create boring slides.** Plain bullets on a white background won't impress anyone.

### Before Starting

- **Pick a bold, content-informed color palette**: The palette should feel designed for THIS topic.
- **Dominance over equality**: One color should dominate (60-70% visual weight), with 1-2 supporting tones and one sharp accent.
- **Dark/light contrast**: Dark backgrounds for title + conclusion slides, light for content.
- **Commit to a visual motif**: Pick ONE distinctive element and repeat it.

### Color Palettes

Choose colors that match your topic:

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` (white) |
| **Forest & Moss** | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` (cream) |
| **Coral Energy** | `F96167` (coral) | `F9E795` (gold) | `2F3C7E` (navy) |
| **Warm Terracotta** | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` (sage) |
| **Ocean Gradient** | `065A82` (deep blue) | `1C7293` (teal) | `21295C` (midnight) |
| **Charcoal Minimal** | `36454F` (charcoal) | `F2F2F2` (off-white) | `212121` (black) |

### For Each Slide

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

**Layout options:**
- Two-column (text left, illustration on right)
- Icon + text rows
- 2x2 or 2x3 grid
- Half-bleed image with content overlay

**Data display:**
- Large stat callouts (big numbers 60-72pt with small labels below)
- Comparison columns (before/after, pros/cons)
- Timeline or process flow

### Typography

| Header Font | Body Font |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Cambria | Calibri |
| Trebuchet MS | Calibri |

| Element | Size |
|---------|------|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

### Avoid

- **Don't repeat the same layout** — vary across slides
- **Don't center body text** — left-align paragraphs and lists; center only titles
- **Don't default to blue** — pick colors that reflect the specific topic
- **Don't create text-only slides** — add images, icons, charts, or visual elements
- **NEVER use accent lines under titles** — these are a hallmark of AI-generated slides

---

## QA (Required)

**Assume there are problems. Your job is to find them.**

### Content QA

```bash
python -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

### Visual QA

Convert slides to images, then inspect them:

```bash
libreoffice --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

Use the `delegate` tool to have a subagent inspect the slide images with fresh eyes. Look for:
- Overlapping elements
- Text overflow or cut off
- Elements too close (< 0.3" gaps)
- Low-contrast text or icons
- Leftover placeholder content

### Verification Loop

1. Generate slides → Convert to images → Inspect
2. **List issues found**
3. Fix issues
4. **Re-verify affected slides**
5. Repeat until clean

---

## Converting to Images

```bash
libreoffice --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
# Creates slide-01.jpg, slide-02.jpg, etc.

# Re-render specific slide after fixes:
pdftoppm -jpeg -r 150 -f N -l N output.pdf slide-fixed
```

---

## Dependencies

Install as needed:
- `pip install "markitdown[pptx]"` - text extraction
- `pip install python-pptx` - programmatic editing
- `npm install -g pptxgenjs` - creating from scratch
- LibreOffice (`soffice`) - PDF conversion (`brew install --cask libreoffice`)
- Poppler (`pdftoppm`) - PDF to images (`brew install poppler`)