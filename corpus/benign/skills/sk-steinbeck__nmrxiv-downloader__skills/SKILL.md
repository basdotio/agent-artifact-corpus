---
name: nmrxiv
description: Search and download NMR spectroscopy datasets from nmrxiv.org. Use when the user asks to find NMR data, search for HSQC/HMBC/COSY/DEPT experiments, look up compounds by name or SMILES, download NMR datasets, or access nmrxiv.org data programmatically. Outputs JSON for easy parsing.
---

# nmrxiv-downloader: NMR Dataset Search & Download

CLI tool for searching and downloading NMR spectroscopy datasets from nmrxiv.org.

## Setup

```bash
# Install from PyPI
pip install nmrxiv-downloader

# Verify installation
nmrxiv --help
```

## Quick Reference

| Task | Command | JSON Path |
|------|---------|-----------|
| List projects | `nmrxiv list --type project` | `.items[].identifier` |
| List datasets | `nmrxiv list --type dataset` | `.items[].identifier` |
| Search molecule | `nmrxiv search --query "name"` | `.results[].canonical_smiles` |
| Search SMILES | `nmrxiv search --smiles "CCO"` | `.results[].iupac_name` |
| Filter by experiment | `nmrxiv search --type hsqc` | `.results[].identifier` |
| Show details | `nmrxiv show P5` | `.item.download_url` |
| Download | `nmrxiv download P5 -o /tmp` | `.file`, `.size` |
| Download + extract | `nmrxiv download P5 -o /tmp --extract` | `.extracted_to` |

## Common Experiment Types

```bash
nmrxiv search --type hsqc      # 1H-13C HSQC
nmrxiv search --type hmbc      # HMBC
nmrxiv search --type cosy      # COSY
nmrxiv search --type dept      # DEPT
nmrxiv search --type "1d-13c"  # 1D 13C
nmrxiv search --type noesy     # NOESY
nmrxiv search --type tocsy     # TOCSY
```

## Key Facts

- **All output is JSON by default** (add `--no-json` for human-readable)
- **Projects have download URLs, datasets don't** - download via parent project
- **Data hierarchy**: Project → Study → Dataset → Files (Bruker, JCAMP-DX)
- **Pagination**: Use `--page N` for large result sets

## Workflow: Find and Download NMR Data

```bash
# 1. Search for experiment type
nmrxiv search --type hsqc

# 2. Get dataset details (shows parent project)
nmrxiv show D410

# 3. Download parent project
nmrxiv download P11 --output ./data --extract

# 4. Data is now in ./data/P11/
```

## Workflow: Search by Compound

```bash
# 1. Search by name
nmrxiv search --query "quercetin"

# 2. Or by SMILES substructure
nmrxiv search --smiles "c1ccc(O)cc1"

# 3. Find related projects
nmrxiv list --type project | jq '.items[] | select(.name | test("quercetin"; "i"))'
```

## Error Handling

If download fails with "No download URL":
```json
{"error": true, "message": "No download URL for D410. Try downloading parent project: P11", "code": 1}
```
→ Use the suggested parent project ID to download.

## Parsing Examples

```bash
# Get first project identifier
nmrxiv list --type project | jq -r '.items[0].identifier'

# Get all HSQC dataset IDs
nmrxiv search --type hsqc | jq -r '.results[].identifier'

# Get download URL for a project
nmrxiv show P5 | jq -r '.item.download_url'
```
