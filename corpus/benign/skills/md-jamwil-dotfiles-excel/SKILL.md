---
name: excel
description:
  Automates Microsoft Excel via pywin32 (COM) for interactive pair work.
  Attaches to a running Excel instance, selects an already-open workbook by
  name, and runs agent-generated Python to manipulate sheets/cells/formulas and
  save/export.
compatibility: Windows + Microsoft Excel. Requires uv.
---

# Excel (pywin32) Skill

This skill is for **interactive pair work** where the user already has:

- Microsoft Excel running
- The target workbook already open

The harness attaches to the running Excel session and executes agent-provided
Python code with these variables pre-bound:

- `excel`: Excel Application COM object
- `wb`: target Workbook COM object
- `win32c`: `win32com.client.constants`

## Where is the Python harness script?

In this skills repo, each skill lives in its own folder. For this skill, the
entrypoint Python script is:

- `excel/scripts/excel_harness.py`

All example commands below assume you run them from the **skills directory
root** (so that relative path resolves). The skills directory is typically at
`~/.pi/agent/skills/`.

**Path note (Windows + bash):** Use **forward slashes** (`/`) in paths when
writing commands (e.g. `excel/scripts/excel_harness.py`). Windows may show paths
with backslashes (`C:\\...`), but the agent runs commands in a bash-like shell
where `/` is the expected separator.

## Run (uv one-liners)

List open workbooks:

```bash
uv run excel/scripts/excel_harness.py --list-workbooks
```

Run inline code against an open workbook:

```bash
uv run excel/scripts/excel_harness.py --workbook 'Budget.xlsx' --code 'wb.Worksheets(1).Range("A1").Value="Hi"'
```

**Quoting note (bash):** Prefer **single quotes** around CLI argument values
(e.g. `--code '...'`, `--script '...'`). This avoids bash interpreting
characters like `$` (common in Excel formulas and some code snippets) as
variable expansions.

Run a snippet file:

```bash
uv run excel/scripts/excel_harness.py --workbook 'Budget.xlsx' --script /path/to/snippet.py
```

### Snippet pattern

Write snippets assuming `excel` and `wb` exist:

```python
ws = wb.Worksheets("Sheet1")
ws.Range("A1").Value = "Hello"
ws.Range("A2").Value = 123
ws.Range("A3").Formula = "=A2*2"
wb.Save()

__result__ = {
  "sheet": ws.Name,
  "a1": ws.Range("A1").Value,
  "a3": ws.Range("A3").Value,
}
```

The harness will print `__RESULT__=<json>` if `__result__` is set.

## Agent workflow

1. Ask the user which workbook is open (usually the `.xlsx` file name).
2. If uncertain, run `--list-workbooks` and pick from the output.
3. Generate a small, incremental snippet to perform the requested action.
4. Execute via `uv run ... --code` (tiny changes) or `--script` (multi-step).

## Safety notes

- The harness **will not open Excel** or open files; it only manipulates what’s
  already open.
- **Do not save automatically.** Avoid calling `wb.Save()` / `wb.SaveAs(...)`
  unless the user explicitly asks to persist changes. The user should have a
  chance to verify the workbook looks correct before saving.
- Avoid destructive operations unless explicitly requested.
- Prefer incremental edits and frequent saves/exports when asked.
