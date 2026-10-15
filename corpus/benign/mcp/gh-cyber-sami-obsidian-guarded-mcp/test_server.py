#!/usr/bin/env python3
"""Test harness for server.py — runs against temp vaults, never touches real ones."""

import json
import os
import sys
import tempfile
import textwrap
from pathlib import Path

# ── create two temp vaults before importing server ────────────────────────────

VAULT_A = tempfile.mkdtemp(prefix="obsidian_test_a_")
VAULT_B = tempfile.mkdtemp(prefix="obsidian_test_b_")
OUTSIDE = tempfile.mkdtemp(prefix="obsidian_test_outside_")

def _populate_vault_a():
    Path(VAULT_A, "notes").mkdir()
    Path(VAULT_A, "notes", "project-alpha.md").write_text(textwrap.dedent("""\
        ---
        title: Project Alpha
        tags: [alpha, important]
        status: active
        ---

        # Project Alpha

        This is the main project note. It contains important details.
        """), encoding="utf-8")
    Path(VAULT_A, "notes", "meeting-notes.md").write_text(textwrap.dedent("""\
        ---
        title: Meeting Notes
        date: 2024-01-15
        ---

        Discussed roadmap. Action items: write specs, schedule follow-up.
        """), encoding="utf-8")
    Path(VAULT_A, "daily.md").write_text(textwrap.dedent("""\
        ---
        title: Daily Log
        ---

        Today was productive. Shipped three features.
        """), encoding="utf-8")
    Path(VAULT_A, ".obsidian").mkdir()
    Path(VAULT_A, ".obsidian", "config.json").write_text('{"hidden": true}')
    # A symlinked note pointing outside the vault must never be listed or searched.
    Path(OUTSIDE, "secret.md").write_text("OUTSIDE_SECRET", encoding="utf-8")
    try:
        Path(VAULT_A, "notes", "escape.md").symlink_to(Path(OUTSIDE, "secret.md"))
    except OSError:
        pass  # symlinks unavailable (e.g. Windows without privileges)

def _populate_vault_b():
    Path(VAULT_B, "vault-b-only.md").write_text(textwrap.dedent("""\
        ---
        title: Vault B Note
        ---

        This note exists only in vault B.
        """), encoding="utf-8")

_populate_vault_a()
_populate_vault_b()

# ── point the server at a temp config before importing it ────────────────────
# server.py reads its config at import time, so OBSIDIAN_MCP_CONFIG must be set
# first. This means the tests never need (or touch) a real vaults.json.

CONFIG_DIR = tempfile.mkdtemp(prefix="obsidian_test_config_")
CONFIG_FILE = Path(CONFIG_DIR, "vaults.json")
CONFIG_FILE.write_text(json.dumps({
    "default": "vault-a",
    "vaults": {"vault-a": VAULT_A, "vault-b": VAULT_B},
}), encoding="utf-8")
os.environ["OBSIDIAN_MCP_CONFIG"] = str(CONFIG_FILE)

import server as s  # noqa: E402

VAULT_A = str(Path(VAULT_A).resolve())
VAULT_B = str(Path(VAULT_B).resolve())

# ── helpers ───────────────────────────────────────────────────────────────────

PASS = "  PASS ✓"
FAIL = "  FAIL ✗"

def check(label: str, cond: bool, detail: str = ""):
    status = PASS if cond else FAIL
    print(f"{status}  {label}" + (f"\n         → {detail}" if detail else ""))
    return cond

results = []

print("\n=== Obsidian MCP Server Tests ===\n")

# ── 1. list_notes ─────────────────────────────────────────────────────────────
print("[ list_notes ]")
r = s.list_notes()
results.append(check("lists 3 notes in vault-a", r["count"] == 3, str(r["notes"])))
results.append(check("vault name in response", r["vault"] == "vault-a"))
results.append(check(".obsidian excluded", not any(".obsidian" in n for n in r["notes"])))
results.append(check("symlink escaping vault excluded", not any("escape" in n for n in r["notes"])))
r2 = s.list_notes("notes")
results.append(check("subfolder filter works", r2["count"] == 2, str(r2["notes"])))

# ── 2. read_note ──────────────────────────────────────────────────────────────
print("\n[ read_note ]")
r = s.read_note("notes/project-alpha.md")
results.append(check("reads content", "Project Alpha" in r["content"]))
results.append(check("parses frontmatter", r["frontmatter"]["status"] == "active"))
results.append(check("tags are a list", isinstance(r["frontmatter"]["tags"], list)))

# ── 3. path traversal rejection ───────────────────────────────────────────────
print("\n[ path traversal ]")
for evil in ["../../etc/passwd", "../../../root/.bashrc", "/etc/shadow"]:
    try:
        s.read_note(evil)
        results.append(check(f"blocks {evil!r}", False, "no error raised!"))
    except ValueError as e:
        results.append(check(f"blocks {evil!r}", True, str(e)))

# ── 4. write_note ─────────────────────────────────────────────────────────────
print("\n[ write_note ]")
s.write_note("new-note.md", "Hello world", frontmatter_data={"title": "New Note"})
r = s.read_note("new-note.md")
results.append(check("write overwrite", r["content"].strip() == "Hello world"))
results.append(check("frontmatter written", r["frontmatter"]["title"] == "New Note"))

s.write_note("new-note.md", "Appended line", mode="append")
r = s.read_note("new-note.md")
results.append(check("append mode", "Appended line" in r["content"]))

s.write_note("new-note.md", "Prepended line", mode="prepend")
r = s.read_note("new-note.md")
results.append(check("prepend mode", r["content"].startswith("Prepended line")))

try:
    s.write_note("new-note.md", "x", mode="turbo")
    results.append(check("invalid mode rejected", False))
except ValueError:
    results.append(check("invalid mode rejected", True))

# ── 5. patch_note ─────────────────────────────────────────────────────────────
print("\n[ patch_note ]")
s.write_note("patch-test.md", "line one\nline two\nline three")
r = s.patch_note("patch-test.md", "line two", "LINE TWO")
results.append(check("single replace", r["replacements"] == 1))
results.append(check("vault name in patch response", r["vault"] == "vault-a"))
content = s.read_note("patch-test.md")["content"]
results.append(check("replacement applied", "LINE TWO" in content))

try:
    s.patch_note("patch-test.md", "line", "LINE")
    results.append(check("multi-match without replace_all rejected", False))
except ValueError as e:
    results.append(check("multi-match without replace_all rejected", True, str(e)))

r2 = s.patch_note("patch-test.md", "line", "LINE", replace_all=True)
results.append(check("replace_all replaces all", r2["replacements"] == 2))

try:
    s.patch_note("patch-test.md", "NOPE_NOT_HERE", "x")
    results.append(check("not-found error", False))
except ValueError:
    results.append(check("not-found error", True))

# ── 6. search_notes ───────────────────────────────────────────────────────────
print("\n[ search_notes ]")
r = s.search_notes("important")
results.append(check("finds content match", r["count"] >= 1))
results.append(check("has excerpt", "excerpt" in r["matches"][0]))

r2 = s.search_notes("alpha")
results.append(check("filename match works", any(m["line"] == 0 for m in r2["matches"])))

r3 = s.search_notes("ROADMAP")
results.append(check("case insensitive", r3["count"] >= 1))

r4 = s.search_notes("OUTSIDE_SECRET")
results.append(check("search ignores symlink escaping vault", r4["count"] == 0))

# ── 7. get_frontmatter ────────────────────────────────────────────────────────
print("\n[ get_frontmatter ]")
r = s.get_frontmatter("notes/meeting-notes.md")
results.append(check("returns frontmatter dict", r["frontmatter"]["title"] == "Meeting Notes"))
results.append(check("no content key", "content" not in r))

# ── 8. update_frontmatter ─────────────────────────────────────────────────────
print("\n[ update_frontmatter ]")
r = s.update_frontmatter("notes/project-alpha.md", {"status": "done", "priority": 1})
results.append(check("merge updates key", r["frontmatter"]["status"] == "done"))
results.append(check("merge preserves other keys", "tags" in r["frontmatter"]))
results.append(check("new key added", r["frontmatter"]["priority"] == 1))

r2 = s.update_frontmatter("notes/project-alpha.md", {"only": "this"}, merge=False)
results.append(check("merge=False replaces entirely", list(r2["frontmatter"].keys()) == ["only"]))

# ── 9. delete_note ────────────────────────────────────────────────────────────
print("\n[ delete_note ]")
try:
    s.delete_note("daily.md", "daily.md.typo")
    results.append(check("mismatch rejected", False))
except ValueError as e:
    results.append(check("mismatch rejected", True, str(e)))

r = s.delete_note("daily.md", "daily.md")
results.append(check("soft delete moves to .trash", r["ok"]))
results.append(check("moved_to starts with .trash", r["moved_to"].startswith(".trash")))
results.append(check("original file gone", not Path(VAULT_A, "daily.md").exists()))
results.append(check("trash file exists", Path(VAULT_A, r["moved_to"]).exists()))

# ── 10. get_vault_stats ───────────────────────────────────────────────────────
print("\n[ get_vault_stats ]")
r = s.get_vault_stats()
results.append(check("note_count correct", r["note_count"] >= 2))
results.append(check("has total_size_kb", r["total_size_kb"] > 0))
results.append(check("recently_modified is list", isinstance(r["recently_modified"], list)))

# ── 11. vault management ──────────────────────────────────────────────────────
print("\n[ list_vaults / get_active_vault / switch_vault ]")

r = s.list_vaults()
results.append(check("list_vaults returns both vaults", len(r["vaults"]) == 2))
results.append(check("active vault marked correctly", next(v for v in r["vaults"] if v["name"] == "vault-a")["active"]))
results.append(check("inactive vault not marked", not next(v for v in r["vaults"] if v["name"] == "vault-b")["active"]))

r = s.get_active_vault()
results.append(check("get_active_vault returns vault-a", r["name"] == "vault-a"))
results.append(check("get_active_vault has path", r["path"] == VAULT_A))

# switch to vault-b and verify isolation
r = s.switch_vault("vault-b")
results.append(check("switch_vault returns ok", r["ok"]))
results.append(check("switch_vault reports new name", r["active_vault"] == "vault-b"))

r = s.get_active_vault()
results.append(check("get_active_vault reflects switch", r["name"] == "vault-b"))

r = s.list_notes()
results.append(check("vault-b has only its own notes", r["count"] == 1))
results.append(check("vault-b note is vault-b-only.md", r["notes"] == ["vault-b-only.md"]))

# vault-a notes must not bleed into vault-b
try:
    s.read_note("notes/project-alpha.md")
    results.append(check("vault-a note not visible from vault-b", False))
except FileNotFoundError:
    results.append(check("vault-a note not visible from vault-b", True))

# unknown vault raises
try:
    s.switch_vault("nonexistent")
    results.append(check("unknown vault rejected", False))
except ValueError as e:
    results.append(check("unknown vault rejected", True, str(e)))

# switch back
s.switch_vault("vault-a")
r = s.list_notes()
results.append(check("switch back to vault-a works", r["count"] >= 2))

# ── 12. config loading ────────────────────────────────────────────────────────
print("\n[ config ]")
results.append(check("config loaded from OBSIDIAN_MCP_CONFIG", s._CONFIG_PATH == CONFIG_FILE))
original = s._CONFIG_PATH
s._CONFIG_PATH = Path(CONFIG_DIR, "missing.json")
try:
    s._load_vault_config()
    results.append(check("missing config gives clear error", False))
except RuntimeError as e:
    results.append(check("missing config gives clear error", "vaults.example.json" in str(e), str(e)))
finally:
    s._CONFIG_PATH = original

# ── summary ───────────────────────────────────────────────────────────────────
import shutil as _shutil
for d in (VAULT_A, VAULT_B, OUTSIDE, CONFIG_DIR):
    _shutil.rmtree(d)

passed = sum(results)
total = len(results)
print(f"\n{'='*40}")
print(f"Result: {passed}/{total} passed", "🎉" if passed == total else "⚠️")
if passed < total:
    sys.exit(1)
