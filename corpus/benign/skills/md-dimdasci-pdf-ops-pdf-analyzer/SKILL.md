---
name: pdf-analyzer
description: Intelligent multi-pass PDF analyzer for extracting document structure, content inventory, and metadata. Uses overview-first approach - scans for TOC, infers structure from semantics when TOC missing. Handles large PDFs (>10 pages) by splitting into chunks using pdfcpu. Use when creating test expectations for pdf-translator, validating PDF conversion output, or understanding complex document structure before conversion.
---

# PDF Analyzer

Analyze PDF documents using a structured multi-pass approach to extract accurate structure and content information.

## Quick Start

```
0. Assess PDF size (split if >10 pages)
1. Read PDF overview (first/last pages)
2. Extract structure (from TOC or inferred)
3. Inventory content (images, tables, code)
4. Output ExpectedSchema JSON
```

## Pass 0: PDF Assessment

**Goal:** Determine if PDF needs splitting for manageable analysis.

**Requires:** `pdfcpu` command-line tool.

### Check Page Count

```bash
pdfcpu info -j <pdf_file>
```

Extract `pages` from JSON output.

### Decision

- **≤10 pages:** Proceed directly to Pass 1 (standard workflow)
- **>10 pages:** Use Large PDF Workflow (see below)

**Record:**

```
PDF: [filename]
Pages: [N]
Workflow: [standard / chunked]
```

## Pass 1: Document Overview

**Goal:** Understand document before detailed extraction.

Read first 3-5 pages:

- Document type (academic paper, manual, report, book)
- Primary language
- TOC presence and location (may be after title/preamble)
- Preamble elements (title page, abstract, preface)

Read last 2-3 pages:

- Appendices, references, index
- Total page count

**Record findings:**

```
Document: [filename]
Type: [manual/paper/report/book]
Pages: [N]
Language: [en/de/etc]
TOC: [found on page X / not found]
```

## Pass 2: Structure Extraction

### If TOC Found

1. Read TOC page(s) completely
2. Extract all entries with their page numbers
3. Map hierarchy from indentation/numbering:
   - Top-level entries (chapters, main sections) = H1
   - Second-level = H2
   - Continue pattern for H3-H6
4. Spot-check: verify 2-3 headings exist on indicated pages

### If NO TOC (Infer Structure)

Scan document systematically, identify headings by:

- **Font size:** Larger = higher level
- **Formatting:** Bold, caps, underlined
- **Numbering:** "1.", "1.1", "1.1.1" patterns
- **Semantic markers:** "Chapter", "Section", "Part", "Appendix"

Build hierarchy:

- Document title = H1 (usually one)
- Major sections = H2
- Subsections = H3
- Continue pattern

**Avoid skipped levels** (H1 directly to H3 is invalid).

## Pass 3: Content Inventory

Process document section by section, counting:

### Images/Figures

- Photos, diagrams, charts, graphs, screenshots
- **Include:** Numbered figures, inline illustrations
- **Exclude:** Logos, decorative elements, page headers/footers

### Tables

- Data tables with rows and columns
- Record dimensions: rows x columns (include header row)
- **Include:** Data tables, comparison tables
- **Exclude:** Layout tables (used for positioning, not data)

### Code Blocks

- Code snippets, command examples, file listings
- Note language if specified (syntax highlighting, labels)
- **Include:** Fenced/indented code blocks
- **Exclude:** Inline code references

## Pass 4: Output

Generate JSON matching ExpectedSchema (see references/expected-schema.md):

```json
{
  "metadata": {
    "name": "fixture-name",
    "pageCount": 42,
    "language": "en"
  },
  "structure": {
    "headings": {
      "byLevel": { "h1": 1, "h2": 5, "h3": 12, "h4": 0, "h5": 0, "h6": 0 },
      "items": [
        { "level": 1, "text": "Document Title" },
        { "level": 2, "text": "Introduction" }
      ]
    },
    "hierarchyValid": true
  },
  "content": {
    "images": { "count": 8 },
    "tables": {
      "count": 3,
      "details": [
        { "rows": 5, "columns": 3 },
        { "rows": 10, "columns": 4 }
      ]
    },
    "codeBlocks": { "count": 0, "languages": [] }
  },
  "format": {
    "shouldParse": true
  }
}
```

## Edge Cases

**Multi-part TOC:** Some documents split TOC across pages. Read all TOC pages.

**TOC at end:** Some reports place TOC after content. Check last pages if not found at start.

**Nested numbering:** "1.2.3.4" style may indicate H4, but use judgment - some documents use deep numbering for H2/H3.

**Image-heavy documents:** For documents with many small images, count significant ones (figures, diagrams) not decorative elements.

**Ambiguous tables:** If unsure whether something is a table or formatted list, count it as a table if it has clear row/column structure.

## Confidence Notes

When generating output, note any uncertainties:

- "Image count approximate - decorative elements excluded"
- "Heading hierarchy inferred from formatting"
- "Table dimensions estimated from visible structure"

---

## Large PDF Workflow

For PDFs with >10 pages, use chunked analysis with pdfcpu.

### Step 1: Create Temp Directory

```bash
mkdir -p /tmp/pdf-chunks-$(date +%s)
```

### Step 2: Split PDF

```bash
pdfcpu split -m span <pdf_file> <temp_dir> 10
```

This creates files like `<basename>_1.pdf`, `<basename>_2.pdf`, etc., each with up to 10 pages.

### Step 3: Get Chunk List

```bash
ls <temp_dir>/*.pdf | sort -V
```

### Step 4: Process Each Chunk

For each chunk file, run Passes 1-3:

1. Read the chunk PDF
2. Extract structure (headings, hierarchy)
3. Inventory content (images, tables, code blocks)
4. Record findings in running totals

**Important:** Track chunk boundaries - a heading or table may span chunks.

### Step 5: Aggregate Results

After all chunks processed:

- Combine all heading items in order
- Sum all content counts
- Validate hierarchy across combined headings
- Use total page count from Pass 0

### Step 6: Cleanup

```bash
rm -rf <temp_dir>
```

## Chunk Processing Guidelines

### Maintaining State Across Chunks

Track these running totals as you process each chunk:

```
Running totals:
  Images: [cumulative count]
  Tables: [cumulative count]
  Code blocks: [cumulative count]
  Headings: [accumulated list]
```

### First Chunk (Chunk 1)

- Contains document start, title, possibly TOC
- Perform full Pass 1 (Document Overview) here
- If TOC found, extract full structure for reference
- Record preamble elements

### Middle Chunks

- Focus on content inventory (Pass 3)
- Add headings to accumulated list
- Watch for continuation from previous chunk (partial tables, lists)

### Last Chunk

- May contain appendices, references, index
- Complete content inventory
- Note any back matter structure

### Boundary Cases

**Split heading:** If a heading appears at chunk end but its content is in next chunk, count the heading in the chunk where the heading text appears.

**Split table:** If a table spans chunks:

- Count as ONE table
- Record total rows across both chunks
- Note in confidence: "Table spans chunk boundary"

**Split code block:** Similar to tables - count once, aggregate lines.

## Result Aggregation

### Combining Chunk Results

After processing all chunks:

1. **Metadata:** Use values from Pass 0 and first chunk
   ```json
   "metadata": {
     "name": "fixture-name",
     "pageCount": [total from Pass 0],
     "language": [from first chunk]
   }
   ```

2. **Structure:** Merge heading lists maintaining order
   - First chunk headings, then second, etc.
   - Revalidate hierarchy across combined list

3. **Content:** Sum counts from all chunks
   ```
   Total images = chunk1.images + chunk2.images + ...
   Total tables = chunk1.tables + chunk2.tables + ... - [boundary duplicates]
   Total code = chunk1.code + chunk2.code + ... - [boundary duplicates]
   ```

4. **Format:** Use standard values

### Final Validation

Before output:

- Check heading hierarchy is valid (no skipped levels)
- Verify counts are reasonable for page count
- Note any aggregation uncertainties in Confidence Notes
