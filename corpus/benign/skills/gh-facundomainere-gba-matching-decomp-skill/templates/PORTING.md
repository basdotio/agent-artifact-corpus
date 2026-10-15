# Porting the bundled tools to a new ROM

The tools come from the Medabots AX project and still contain its constants. Change these before you use them:

| What | Where | Medabots AX value |
|---|---|---|
| Code region end (data starts after it) | `split.py` `CODE_END`; `version_align.py` and `objdiff_report.py` (`0x08056538`); `make_version.py` `code_end` | `0x08056538` |
| Output ROM name | `Makefile` `ROM`, `*.sha1` files, `make_version.py`, workflow prompt arg `rom` | `medabots_ax.gba` |
| Base version name | `check_func.py`, `objdiff_report.py`, `Makefile` (`VERSION ?= metabee`) | `metabee` |
| Library symbol addresses (memcpy, libgcc division, `_call_via_rN`) | `check_func.py` `ALIASES`; `templates/aliases.s` | `0x08056440`, `0x080561A0`, ... |
| Ghidra function list | `decomp/functions.csv` (columns start,end,thumb,name), written by `templates/ghidra/ExportFuncs.py` | your Ghidra export |
| Ghidra memory map / Thumb seeding | `templates/ghidra/GbaSetup.py` (standard GBA map; usually no change) | |
| ELF path the tools read | `check_func.py`, `version_align.py` | `build/medabots_ax.elf` |

Tools that need no changes: `claim.py`, `retry_claim.py`, `integrate_one.sh`, `add_funcs.py` (apart from the CFLAGS it shares with check_func), `post_run.py`, `bandit.py`, `tip_stats.py`, `collect_notes.py`, `resolve_decl_conflicts.py`, `tokmerge.py`, `rename.py`, `use_headers.py`, `syms.py`, `progress.py` (reads `CODE_END` from split.py), `permute*.{py,sh}` (needs decomp-permuter installed in `tools/decomp-permuter`).

The compiler flags (`-mthumb-interwork -O2 -fhex-asm -fprologue-bugfix`) appear in the Makefile, `check_func.py` and `add_funcs.py`. Keep all three in sync.

The workflow scripts in `workflows/` take the project-specific parts as args (see "Workflow arguments" in SKILL.md for their shapes): `repo`, `game`, `about` (one line about the game), `rom`, `shared` (the shared header list), `headers`, `globals`, `chunks`, `projectNotes` (facts every matching agent needs, e.g. "memcpy resolves to sub_XXXXXXXX") and `foldPrompt`.
