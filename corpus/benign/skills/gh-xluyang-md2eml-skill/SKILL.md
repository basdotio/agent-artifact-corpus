---
name: local-markdown-to-email
description: Convert a local Markdown note into an email-ready HTML document, a local-image CID .eml draft, or rich-text clipboard content. Use when a user asks to turn a Markdown note into an email while keeping local images and readable email-safe formatting.
---

# Local Markdown to Email

Use `scripts/local_markdown_to_email.py` for the conversion. Pass only note and root paths plus the requested output mode; the script reads image bytes locally and never emits them as model context.

```bash
python3 scripts/local_markdown_to_email.py \
  --note-path "Projects/design.md" \
  --root-path "/path/to/notes" \
  --output-type eml
```

The command prints a JSON response. `output-type` can be `eml`, `clipboard`, or `both`; `--theme` supports `default`, `modern`, and `minimal`. An absolute note path may be used without `--vault-path`. Relative attachment paths are resolved from the note directory, then the vault; unresolved images remain visible as `[图片缺失: ...]` and are listed in `missing_images`.

Keep processing local. Do not upload note contents or image data. For clipboard output, a platform clipboard utility or optional `pyperclip` is used; if unavailable, the JSON response reports the failure while the HTML remains available in the result.
