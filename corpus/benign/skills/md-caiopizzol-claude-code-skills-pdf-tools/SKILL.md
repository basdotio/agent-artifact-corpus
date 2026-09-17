---
name: pdf-tools
description: Search and extract content from PDF files. Use when searching PDFs, finding text in documents, or extracting specific pages without reading the entire file.
allowed-tools: Bash, Read, Glob
---

# PDF Tools

Search and extract content from PDFs without loading entire files into context.

## Installation

```bash
# macOS
brew install pdfgrep poppler

# Ubuntu/Debian
sudo apt install pdfgrep poppler-utils
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Search | `pdfgrep "term" file.pdf` |
| Search with page numbers | `pdfgrep -n "term" file.pdf` |
| Search with context | `pdfgrep -n -C 2 "term" file.pdf` |
| Get page count | `pdfinfo file.pdf \| grep Pages` |
| Extract pages 5-10 | `pdftotext -f 5 -l 10 file.pdf -` |

---

## Core Workflow

**Step 1: Search** - Find where content lives
```bash
pdfgrep -n "authentication" large-manual.pdf
# Output: 42: User authentication requires...
#         45: Authentication tokens expire...
```

**Step 2: Extract** - Get just those pages
```bash
pdftotext -f 41 -l 46 large-manual.pdf -
```

---

## Search Commands

```bash
# Basic search
pdfgrep "search term" document.pdf

# Case-insensitive
pdfgrep -i "search term" document.pdf

# With page numbers
pdfgrep -n "search term" document.pdf

# With context (2 lines before/after)
pdfgrep -n -C 2 "search term" document.pdf

# Count occurrences
pdfgrep -c "search term" document.pdf

# Search all PDFs in directory
pdfgrep -r "term" /path/to/pdfs/
```

---

## Extract Commands

```bash
# Extract specific page range
pdftotext -f 10 -l 15 document.pdf -

# Extract single page
pdftotext -f 42 -l 42 document.pdf -

# Preserve layout (for tables)
pdftotext -layout -f 10 -l 10 document.pdf -

# Extract and limit output
pdftotext -f 10 -l 15 document.pdf - | head -50
```

---

## Metadata

```bash
# Get page count
pdfinfo document.pdf | grep Pages

# Full metadata
pdfinfo document.pdf
```

---

## Troubleshooting

**Empty output from pdftotext**: PDF is image-based (scanned). These tools work with text-based PDFs only.

**pdfgrep missing matches**: Try case-insensitive (`-i`). Check if PDF has selectable text.
