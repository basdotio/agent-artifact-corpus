---
name: cpa-antigravity-rt-extract
description: Extract Google Refresh Tokens (RT) from Antigravity JSON configuration files. Use when you need to batch process JSON files to retrieve and deduplicate refresh_token values.
---

# CPA Antigravity RT Extract

Batch extract `refresh_token` values from JSON files produced by Antigravity or compatible tools.

## Usage

1. Identify the directory containing your JSON configuration files.
2. Run the extraction script using Python 3.13:

```bash
python3.13 scripts/extract.py <directory_path>
```

## Resources

- **scripts/extract.py**: The core logic for parsing JSON files and deduplicating tokens.
