---
name: cross-compare
description: Compare values in a column across two different Excel files to find matches or differences
---

# Cross Compare Skill

Use this skill to compare data between two different Excel files on a common column
(e.g. same material code or same description appearing in both documents).

## When to use

- "Are there products with the same description in both files?"
- "Find materials that appear in both CCMC and MLCC files"
- "Which codes exist in file A but not in file B?"

## How to call

```
run_skill_script("cross-compare", "cross-compare.py", {"file1_path": "/abs/file1.xlsx", "col1": "Código", "file2_path": "/abs/file2.xlsx", "col2": "Código"})
```

Or with sheet names:

```
run_skill_script("cross-compare", "cross-compare.py", {"file1_path": "/abs/file1.xlsx", "col1": "Código", "file2_path": "/abs/file2.xlsx", "col2": "Código", "sheet1": "Hoja1", "sheet2": "Hoja1"})
```

### Arguments (dict keys)
- `file1_path` (required): Absolute path to the first Excel file
- `col1` (required): Column name in the first file (use inspect-document to confirm)
- `file2_path` (required): Absolute path to the second Excel file
- `col2` (required): Column name in the second file
- `sheet1` (optional): Sheet name for file1. Defaults to first sheet.
- `sheet2` (optional): Sheet name for file2. Defaults to first sheet.

### Return format

Returns JSON:
```json
{
  "file1": "path/to/file1.xlsx",
  "col1": "Código",
  "file2": "path/to/file2.xlsx",
  "col2": "Código",
  "total_file1": 3000,
  "total_file2": 4000,
  "matches_count": 120,
  "only_in_file1_count": 2880,
  "only_in_file2_count": 3880,
  "matches": [{"value": 4032591, "rows_in_file1": 1, "rows_in_file2": 2}],
  "only_in_file1": ["val1", "val2"],
  "only_in_file2": ["val3", "val4"]
}
```

The result is also saved to `exports/.last_result.json` for the app to render as a table.
