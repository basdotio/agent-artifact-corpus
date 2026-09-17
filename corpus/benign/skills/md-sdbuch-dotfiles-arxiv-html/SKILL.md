---
name: arxiv-html
description: Convert any arxiv URL (abs, pdf, versioned) to HTML format for better parsing. Use when you encounter arxiv.org URLs that need to be fetched or read.
allowed-tools: Bash(python3:*)
---

# ArXiv URL to HTML Conversion

## When to Use
Use this whenever you see an arxiv URL and need to fetch or parse its content.
The HTML version is much better for content extraction than PDF.

## How to Convert
Run the conversion script:
```bash
python3 ~/.claude/skills/arxiv-html/convert.py "URL"
```

## Conversion Rules

| Input Format | Example | Output |
|-------------|---------|--------|
| abs | `arxiv.org/abs/2401.12345` | `arxiv.org/html/2401.12345` |
| pdf | `arxiv.org/pdf/2401.12345.pdf` | `arxiv.org/html/2401.12345` |
| versioned | `arxiv.org/abs/2401.12345v2` | `arxiv.org/html/2401.12345v2` |

## Version Handling
- If URL has version (v1, v2, etc.), preserve it
- If no version, get latest (no version suffix)

## Fallback Behavior
- Try HTML URL first (best for parsing)
- If HTML returns 404 or fails, use abs URL instead (older papers may not have HTML)
