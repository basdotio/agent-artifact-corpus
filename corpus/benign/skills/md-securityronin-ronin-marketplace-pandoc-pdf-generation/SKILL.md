---
name: pandoc-pdf-generation
description: Use when generating PDFs from markdown with Pandoc - covers differences from Python-Markdown, blank line rules, fix scripts for labels/anchors/metadata, and visual testing workflow
---

# Pandoc PDF Generation Best Practices

## Overview

This skill documents lessons learned from generating PDF documents from markdown using Pandoc, drawing from experiences with MkDocs HTML generation and applying systematic validation approaches.

---

## Critical Differences: Pandoc vs Python-Markdown

### Supported Features

| Feature | Python-Markdown (MkDocs) | Pandoc (PDF) |
|---------|--------------------------|--------------|
| Roman numerals (`i.`, `ii.`) | ❌ Not supported | ✅ Supported |
| Grid tables | ⚠️ Needs extension | ✅ Native support |
| LaTeX commands (`\pagebreak`) | ❌ Renders as text | ✅ Native support |
| Nested list indent | 4 spaces (strict) | More flexible |
| Footnotes continuation | 4-space indent required | More flexible |

**Key Insight:** Pandoc is MORE capable than Python-Markdown, but this means markdown that works for PDF might break in MkDocs!

### Cross-Renderer Compatibility ✅

**Good News:** Some formatting rules work consistently across both renderers!

**Blank Line Rules (Universal):**
- ✅ Blank line after bold labels before lists - **Works in both MkDocs and Pandoc**
- ✅ Blank line after plain text labels before lists - **Works in both MkDocs and Pandoc**
- ✅ Blank line after HTML anchors before headers - **Works in both MkDocs and Pandoc**
- ✅ Blank lines between consecutive metadata fields - **Works in both MkDocs and Pandoc**

**Validation Method:**
```bash
# Generate both outputs
mkdocs build --clean
./scripts/generate-pdf.sh

# Check MkDocs HTML rendering
grep -A 5 "For complete details, see:" site/soc2-type1/index.html
# Should show: <ul><li>...</li></ul>

# Check Pandoc PDF rendering
pdftotext output/Documentation.pdf - | grep -A 5 "For complete details, see:"
# Should show: • Bullet point
```

**Implication:** Fix markdown once, works for both HTML and PDF! This makes maintaining shared source files much easier.

---

## Shared Markdown Source Strategy

### The Challenge

When using **same markdown files** for both MkDocs (HTML) and Pandoc (PDF):

**Option 1: Optimize for MkDocs** (Current Approach)
- ✅ Clean HTML rendering
- ⚠️ PDF might have issues
- 3-space indents, no `\pagebreak`, etc.

**Option 2: Optimize for Pandoc**
- ✅ Perfect PDF output
- ❌ MkDocs rendering breaks

**Option 3: Separate Sources** (Best for large projects)
- Maintain `docs/` for MkDocs
- Maintain `pdf-source/` for PDF
- Use scripts to sync common content

**Option 4: Conditional Formatting** (Advanced)
- Use Pandoc filters to handle differences
- Use MkDocs plugins for HTML-specific needs
- Keep single source, transform during build

---

## PDF Generation Testing Workflow

### Phase 1: Generate PDF (2 minutes)

```bash
./scripts/generate-pdf.sh
```

**Check for errors:**
- LaTeX errors (process exits non-zero)
- Missing file errors
- Font warnings (informational, not critical)

### Phase 2: Visual Inspection (10 minutes)

**CRITICAL: Actually open and read the PDF!**

```bash
open output/Documentation.pdf
```

**Checklist:**
- [ ] Cover page renders correctly
- [ ] TOC is accurate and complete
- [ ] All section headers are styled as headers (not plain text or literal `##`)
- [ ] Bullet lists render as bullets (not inline text with dashes)
- [ ] Numbered lists render correctly (not inline text)
- [ ] Bold labels before lists have proper spacing
- [ ] Plain text labels before lists have proper spacing
- [ ] Metadata fields appear on separate lines (not run together)
- [ ] Tables fit on pages (no overflow)
- [ ] Code blocks are formatted correctly
- [ ] Page breaks are reasonable (not mid-paragraph)
- [ ] Footnotes work (if applicable)
- [ ] No missing content
- [ ] Font rendering acceptable
- [ ] Total page count reasonable

### Phase 3: Specific Checks (5 minutes)

**Check specific sections user mentioned:**

For example, if user says "these should be bullet points":

1. Find the section in PDF
2. Compare to markdown source
3. Verify markdown has proper bullets:
   ```markdown
   **Access Removal:**
   - Item one
   - Item two
   ```
4. Check PDF rendering matches markdown intent

### Phase 4: Commit (only if passes)

```bash
git add output/Documentation.pdf
git commit -m "docs: regenerate PDF with [specific improvements]"
```

---

## Common PDF Issues and Solutions

### Issue 1: Headers Render as Plain Text

**Symptom:** Text that should be headers (H2, H3) appears as regular paragraphs in PDF.

**Root Cause:** Markdown not properly formatted for Pandoc.

**Check markdown:**
```markdown
# ✅ CORRECT - Header
## User Identification and Authentication

# ❌ WRONG - Plain text
User Identification and Authentication
```

**Solution:** Ensure headers have `##` prefix, blank line before and after.

---

### Issue 2: Bullets Render as Plain Text

**Symptom:** Text shows dashes/bullets as characters, not formatted lists.

**Root Cause:**
1. Missing blank line before list
2. Incorrect indentation
3. Markdown not recognized as list

**Check markdown:**
```markdown
# ✅ CORRECT
**Access Removal:**

- Termination: Immediate revocation
- Role change: Adjusted within 5 days

# ❌ WRONG - No blank line
**Access Removal:**
- Termination: Immediate revocation
```

**Solution:**
1. Add blank line before list
2. Verify proper indentation (0 spaces for root-level)
3. Use consistent markers (`-` or `*`)

---

### Issue 3: Font Warnings for Unicode Characters

**Symptom:**
```
[WARNING] Missing character: There is no ├ (U+251C) in font [lmmono10-regular]
```

**Root Cause:** Default LaTeX font doesn't support all Unicode characters (box-drawing, emojis, etc.)

**Solutions:**

**Option 1: Change Font**
```yaml
# In pandoc command
--pdf-engine=xelatex
--variable mainfont="DejaVu Sans"
```

**Option 2: Remove Special Characters**
```bash
# Replace tree diagrams with ASCII
sed -i '' 's/├/+/g' file.md
sed -i '' 's/─/-/g' file.md
```

**Option 3: Accept Warnings**
- If characters are cosmetic (tree diagrams)
- If they don't affect content comprehension
- Document as "known limitation"

---

### Issue 4: Tables Don't Fit on Page

**Symptom:** Tables overflow page width, text cut off.

**Solutions:**

**Option 1: Rotate Table (Landscape)**
```markdown
\begin{landscape}
| Col 1 | Col 2 | Col 3 |
|-------|-------|-------|
| Data  | Data  | Data  |
\end{landscape}
```

**Option 2: Smaller Font in Table**
```markdown
\small
| Col 1 | Col 2 | Col 3 |
|-------|-------|-------|
| Data  | Data  | Data  |
\normalsize
```

**Option 3: Redesign Table**
- Split into multiple tables
- Use abbreviations
- Rotate headers vertically

---

### Issue 5: Bad Page Breaks

**Symptom:** Headers at bottom of page, orphaned content.

**Solutions:**

**Option 1: Manual Page Breaks**
```markdown
\pagebreak

## Next Section
```

**Option 2: Pandoc Variables**
```bash
--variable pagestyle=headings
--variable geometry:margin=1in
```

**Option 3: LaTeX Penalties**
```latex
\widowpenalty=10000
\clubpenalty=10000
```

---

### Issue 6: Bold Labels Before Lists Render Inline

**Symptom:** Bold labels followed by lists render as inline text instead of separate formatted list.

**Example in PDF:**
```
Technology Changes: - New system implementations - Software upgrades - Infrastructure modifications
```

**Root Cause:** Pandoc requires blank line after bold labels (format: `**Label:**`) before lists.

**Check markdown:**
```markdown
# ❌ WRONG - No blank line
**Technology Changes:**
- New system implementations
- Software upgrades

# ✅ CORRECT - Blank line after label
**Technology Changes:**

- New system implementations
- Software upgrades
```

**Solution:** Add blank line between bold label and list.

**Automated Detection:**
```bash
# Find all bold labels immediately followed by lists
grep -n '^\*\*[^*]*:\*\*$' file.md | while read line; do
  num=$(echo $line | cut -d: -f1)
  next=$((num + 1))
  nextline=$(sed -n "${next}p" file.md)
  if [[ $nextline =~ ^[-*] ]]; then
    echo "Line $num: Missing blank line after bold label"
  fi
done
```

**Automated Fix:** Use `fix_pandoc_lists.py` script (see Automation section below).

---

### Issue 7: Headers Show Literal `##` Characters

**Symptom:** Headers render as plain text with literal `##` characters visible.

**Example in PDF:**
```
## Fraud Risk Assessment
```

**Root Cause:** Pandoc requires blank line after HTML anchor tags before markdown headers.

**Check markdown:**
```markdown
# ❌ WRONG - No blank line after anchor
<a name="fraud-risk"></a>
## Fraud Risk Assessment

# ✅ CORRECT - Blank line after anchor
<a name="fraud-risk"></a>

## Fraud Risk Assessment
```

**Why This Happens:** Pandoc treats HTML and markdown as separate contexts. Without blank line, it doesn't recognize the `##` as a markdown header.

**Solution:** Add blank line between HTML anchor and header.

**Automated Detection:**
```bash
# Find anchors immediately followed by headers
grep -n '^<a name=' file.md | while read line; do
  num=$(echo $line | cut -d: -f1)
  next=$((num + 1))
  nextline=$(sed -n "${next}p" file.md)
  if [[ $nextline =~ ^## ]]; then
    echo "Line $num: Missing blank line after anchor"
  fi
done
```

**Automated Fix:** Use `fix_pandoc_anchors.py` script (see Automation section below).

---

### Issue 8: Metadata Fields Run Together

**Symptom:** Consecutive metadata fields render on single line instead of separate lines.

**Example in PDF:**
```
Title: Report Name Author: Your Name Date: January 2025
```

**Root Cause:** Pandoc requires blank lines between consecutive paragraphs. Without them, it merges lines into continuous text flow.

**Check markdown:**
```markdown
# ❌ WRONG - No blank lines between
**Organization:** Example Corp
**Audit Type:** SOC 2 Type 1
**Scope:** Security (CC1-CC9)

# ✅ CORRECT - Blank lines between each
**Organization:** Example Corp

**Audit Type:** SOC 2 Type 1

**Scope:** Security (CC1-CC9)
```

**Solution:** Add blank lines between consecutive bold label lines.

**Automated Detection:**
```bash
# Find consecutive bold label lines
grep -n '^\*\*[^*]*:\*\* ' file.md | \
  awk 'NR > 1 && $1 == prev+1 {print "Lines " prev "-" $1 ": Consecutive bold labels"} {prev=$1}'
```

**Automated Fix:** Use `fix_pandoc_metadata.py` script (see Automation section below).

---

### Issue 9: Plain Text Labels Before Lists Render Inline

**Symptom:** Plain text (not bold) ending with colon followed by list renders inline.

**Example in PDF:**
```
The security program aligns with: - SOC 2 - ISO 27001 - NIST Framework
```

**Root Cause:** Same as Issue 6, but for plain text labels instead of bold.

**Check markdown:**
```markdown
# ❌ WRONG - No blank line
The security program aligns with:
- SOC 2 Trust Services Criteria
- ISO 27001 control framework

# ✅ CORRECT - Blank line after plain text label
The security program aligns with:

- SOC 2 Trust Services Criteria
- ISO 27001 control framework
```

**Solution:** Add blank line after any text ending with `:` when followed by list.

**Automated Fix:** Enhanced `fix_pandoc_lists.py` handles both bold and plain text labels.

---

## Automation: Fix Scripts

### Script 1: fix_pandoc_lists.py

**Purpose:** Fix bold and plain text labels before lists.

**Usage:**
```bash
python3 fix_pandoc_lists.py
```

**What it fixes:**
- Bold labels before lists: `**Label:**` → blank line → list
- Plain text labels before lists: `Text:` → blank line → list

**Example output:**
```
Processing 03-risk-assessment.md...
  Line 186: Added blank line after '**Technology Changes:**'
  Line 265: Added blank line after 'The security program aligns with:'
  ✅ Fixed 03-risk-assessment.md
```

**Script location:** Project root directory

---

### Script 2: fix_pandoc_anchors.py

**Purpose:** Fix HTML anchors before headers.

**Usage:**
```bash
python3 fix_pandoc_anchors.py
```

**What it fixes:**
- `<a name="..."></a>` → blank line → `## Header`

**Example output:**
```
Processing 03-risk-assessment.md...
  Line 141: Added blank line after '<a name="fraud-risk"></a>'
  ✅ Fixed 03-risk-assessment.md
```

**Script location:** Project root directory

---

### Script 3: fix_pandoc_metadata.py

**Purpose:** Fix consecutive bold label metadata fields.

**Usage:**
```bash
python3 fix_pandoc_metadata.py
```

**What it fixes:**
- Consecutive `**Label:** value` lines → add blank lines between them

**Example output:**
```
Processing index.md...
  Line 3: Added blank line after '**Organization:** Example Corp'
  Line 4: Added blank line after '**Audit Type:** SOC 2 Type 1'
  ✅ Fixed index.md
```

**Script location:** Project root directory

---

### Running All Fix Scripts

**Complete fix workflow:**
```bash
# Fix all Pandoc formatting issues
python3 fix_pandoc_lists.py       # Lists after labels
python3 fix_pandoc_anchors.py     # Anchors before headers
python3 fix_pandoc_metadata.py    # Consecutive metadata

# Regenerate PDF
./scripts/generate-pdf.sh

# Visual verification
open output/Documentation.pdf
```

**When to run:**
- After adding new content with lists
- After modifying metadata sections
- After adding HTML anchors
- Before committing PDFs
- When user reports inline rendering issues

---

## Pandoc Command Reference

### Basic PDF Generation

```bash
pandoc file.md -o output.pdf \
  --from markdown \
  --to pdf \
  --pdf-engine=xelatex
```

### With TOC and Sections

```bash
pandoc file.md -o output.pdf \
  --from markdown \
  --to pdf \
  --pdf-engine=xelatex \
  --toc \
  --toc-depth=3 \
  --number-sections
```

### With Metadata

```bash
pandoc file.md -o output.pdf \
  --from markdown \
  --to pdf \
  --pdf-engine=xelatex \
  --metadata title="Document Title" \
  --metadata author="Author Name" \
  --metadata date="$(date +%Y-%m-%d)"
```

### With Custom Template

```bash
pandoc file.md -o output.pdf \
  --from markdown \
  --to pdf \
  --pdf-engine=xelatex \
  --template=custom-template.tex
```

---

## Testing Checklist Template

Copy this checklist for each PDF generation:

```markdown
## PDF Generation Test - [DATE]

### Generation Phase
- [ ] Script runs without errors
- [ ] PDF file created
- [ ] File size reasonable (< 10MB for typical docs)

### Visual Inspection Phase
- [ ] Opened PDF and scrolled through ALL pages
- [ ] Cover page correct
- [ ] TOC complete and accurate
- [ ] All headers styled correctly (no literal `##`)
- [ ] All bullets formatted as lists (not inline)
- [ ] All numbered lists formatted correctly (not inline)
- [ ] Bold/plain labels before lists properly spaced
- [ ] Metadata fields on separate lines (not run together)
- [ ] All tables fit on pages
- [ ] No obviously bad page breaks
- [ ] No missing content
- [ ] Font rendering acceptable

### Specific Checks (from user feedback)
- [ ] [Specific section] renders correctly
- [ ] [Specific formatting] matches intent
- [ ] [Specific issue] is fixed

### Final Validation
- [ ] PDF matches markdown source intent
- [ ] All user-reported issues addressed
- [ ] Ready for commit

**Issues Found:** [List any issues]
**Next Steps:** [What needs fixing]
```

---

## Automation: PDF Testing Script

**Create:** `scripts/test-pdf.sh`

```bash
#!/bin/bash
# Test PDF generation and basic quality checks

set -e

# Generate PDF
./scripts/generate-pdf.sh

PDF="output/Documentation.pdf"

# Check file exists
if [ ! -f "$PDF" ]; then
    echo "❌ PDF not generated"
    exit 1
fi

# Check file size (should be between 100KB and 10MB)
SIZE=$(stat -f%z "$PDF" 2>/dev/null || stat -c%s "$PDF")
if [ $SIZE -lt 100000 ]; then
    echo "⚠️  WARNING: PDF seems too small ($SIZE bytes)"
elif [ $SIZE -gt 10000000 ]; then
    echo "⚠️  WARNING: PDF seems too large ($SIZE bytes)"
else
    echo "✅ PDF size OK: $(numfmt --to=iec-i --suffix=B $SIZE)"
fi

# Check page count (using pdfinfo if available)
if command -v pdfinfo &> /dev/null; then
    PAGES=$(pdfinfo "$PDF" | grep "Pages:" | awk '{print $2}')
    echo "📄 Pages: $PAGES"

    if [ $PAGES -lt 50 ]; then
        echo "⚠️  WARNING: Expected ~89 pages, got $PAGES"
    fi
fi

echo ""
echo "✅ Basic checks passed!"
echo "📋 Next: Open PDF and visually inspect"
echo "   open $PDF"
```

---

## Key Takeaways

1. **Different renderers = different rules** - Pandoc ≠ Python-Markdown
2. **Visual inspection required** - Terminal success ≠ correct PDF
3. **Blank lines are critical** - Pandoc needs blank lines between different markdown elements
4. **Test locally before committing** - Generate, open, review
5. **Same workflow as MkDocs** - Systematic testing, not assumptions
6. **Font limitations are real** - Accept or configure around them
7. **Markdown intent matters** - Source should express desired structure
8. **Create testing checklists** - Catch issues systematically
9. **Automate fixes** - Create scripts for common formatting issues
10. **HTML and markdown need separation** - Always blank line after HTML elements

---

## Common Pandoc Gotchas Summary

**The "Blank Line Rule":**
Pandoc requires blank lines in these situations:
- After bold/plain text labels before lists
- After HTML tags before markdown headers
- Between consecutive paragraph-like elements
- Before and after headers

**Quick Check Commands:**
```bash
# Check for labels before lists (no blank line)
grep -B1 '^[-*] ' file.md | grep ':$' | grep -v '^--$'

# Check for anchors before headers (no blank line)
grep -A1 '^<a name=' file.md | grep '^##'

# Check for consecutive bold labels
grep '^\*\*[^*]*:\*\* ' file.md | uniq -c | grep -v '^ *1 '
```

**When in doubt:** Add a blank line. Pandoc almost never complains about too many blank lines.

---

## Real-World Example

**Project:** Large documentation set
**Files:** 15 markdown files
**Issues Found:** 469 formatting problems across 4 categories

**Fixes Applied:**
- 376 labels before lists (Issues 6 & 9)
- 45 anchors before headers (Issue 7)
- 62 consecutive metadata fields (Issue 8)

**Time Investment:**
- Discovery: ~2 hours (user feedback + testing)
- Script development: ~1 hour (3 scripts)
- Execution: ~5 minutes (automated)
- Verification: ~10 minutes (visual PDF review)

**ROI:** 3 hours invested, automated solution for future. All issues fixed in 5 minutes.

---

## References

- [Pandoc User's Guide](https://pandoc.org/MANUAL.html)
- [Pandoc PDF Options](https://pandoc.org/MANUAL.html#variables-for-latex)
- [XeLaTeX Documentation](https://tug.org/xetex/)
- [LaTeX Font Selection](https://tug.org/FontCatalogue/)
- [Pandoc Markdown Spec](https://pandoc.org/MANUAL.html#pandocs-markdown)

---

**Status:** Production-ready with automation scripts
