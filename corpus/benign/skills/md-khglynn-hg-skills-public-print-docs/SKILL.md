---
name: print-docs
description: >
  Convert markdown files into a single, print-friendly HTML document. Use when
  Kevin says "print this," "make a print file," "I want to review this on paper,"
  "combine these for printing," "create a print version," or when multiple markdown
  files need to be combined into one printable document. Also use at session end
  when Kevin wants to print deliverables for pen-and-paper review.
---

# Print Docs

Combine markdown files into a single styled HTML document for printing from Chrome.

## How It Works

1. **Collect the files** — ask Kevin which files to include, or infer from the session's deliverables
2. **Combine into one markdown file** with `---` separators between documents
3. **Convert to styled HTML** via pandoc
4. **Open in Chrome** — Kevin prints with `Cmd+P`

## The Command

```bash
# Combine files
cat file1.md > /tmp/print-combined.md
echo -e "\n---\n" >> /tmp/print-combined.md
cat file2.md >> /tmp/print-combined.md
# ... repeat for each file

# Convert to styled HTML
pandoc /tmp/print-combined.md \
  -o ~/Desktop/PRINT-{description}.html \
  --standalone \
  --metadata title="{title}" \
  -V "header-includes=$(cat << 'STYLE'
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;max-width:900px;margin:0 auto;padding:20px;color:#222}
h1{font-size:24px;border-bottom:1px solid #aaa;padding-bottom:5px;margin-top:32px}
h2{font-size:19px;border-bottom:1px solid #ddd;padding-bottom:3px;margin-top:22px}
h3{font-size:16px;font-weight:600;margin-top:14px}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}
th,td{border:1px solid #ccc;padding:4px 8px;text-align:left}
th{font-weight:600}
code{padding:1px 3px;border-radius:2px;font-size:12.5px}
pre{padding:10px;border:1px solid #ddd;border-radius:3px;overflow-x:auto;font-size:12.5px;line-height:1.4}
blockquote{border-left:2px solid #999;margin:8px 0;padding:4px 10px;color:#555}
hr{border:none;border-top:1px solid #ccc;margin:28px 0}
@media print{body{font-size:13.5px}table{font-size:12px}code,pre{font-size:11.5px}}
</style>
STYLE
)"

# Open in Chrome
open -a "Google Chrome" ~/Desktop/PRINT-{description}.html
```

## Style Principles

- **No colored elements** — all black/grey for ink savings
- **Body text 15px screen, 13.5px print** — readable without squinting
- **Tables have light borders** — visible structure, no heavy ink
- **Code blocks have light borders, no backgrounds in print** — saves ink
- **`---` separators between documents** — visual breaks without page-break-after (avoids blank pages)
- **Output to Desktop** — easy to find, filename starts with `PRINT-`

## When Kevin Asks to Print

1. Identify which files are relevant (session deliverables, skills for review, plans, etc.)
2. Ask if anything should be excluded (large reference files that are better reviewed digitally)
3. Combine in priority order — most important first
4. Add a cover line: `# {Title} — {Date}` with a note about what's inside
5. Convert and open in Chrome
6. Tell Kevin: "`Cmd+P` when ready. Set margins to Minimum."

## Prerequisites

Requires `pandoc`. If not installed: `brew install pandoc`
