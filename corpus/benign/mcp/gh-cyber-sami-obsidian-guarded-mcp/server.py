#!/usr/bin/env python3
"""Obsidian MCP Server — multi-vault support via fastmcp."""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional

import frontmatter
from fastmcp import FastMCP

# ── vault config ──────────────────────────────────────────────────────────────

# Config path: $OBSIDIAN_MCP_CONFIG if set, otherwise vaults.json next to this file.
_CONFIG_PATH = Path(
    os.environ.get("OBSIDIAN_MCP_CONFIG") or Path(__file__).parent / "vaults.json"
).expanduser()

def _load_vault_config() -> tuple[dict[str, Path], str]:
    if not _CONFIG_PATH.exists():
        raise RuntimeError(
            f"Vault config not found at {_CONFIG_PATH}. "
            "Copy vaults.example.json to vaults.json and add your vault paths, "
            "or set OBSIDIAN_MCP_CONFIG to point at your config file."
        )
    raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    vaults = {name: Path(path).expanduser().resolve() for name, path in raw["vaults"].items()}
    if not vaults:
        raise RuntimeError("vaults.json has no vaults defined")
    default = raw.get("default", next(iter(vaults)))
    if default not in vaults:
        raise RuntimeError(f"Default vault {default!r} not listed in vaults")
    return vaults, default

_VAULTS, _default_vault = _load_vault_config()
_active_vault: str = _default_vault

def _vault_root() -> Path:
    return _VAULTS[_active_vault]


ALLOWED_EXTENSIONS = {".md", ".markdown"}

mcp = FastMCP("Obsidian Vault")


# ── path safety ───────────────────────────────────────────────────────────────

def _resolve(path: str) -> Path:
    """Resolve path against the active vault root. Raises ValueError on traversal attempt."""
    root = _vault_root()
    resolved = (root / Path(path.lstrip("/\\"))).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(f"Path traversal rejected: {path!r}")
    return resolved


def _is_hidden(path: Path) -> bool:
    """True if any component relative to the active vault root starts with a dot."""
    root = _vault_root()
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(part.startswith(".") for part in rel.parts)


def _assert_note(path: Path) -> None:
    """Raise if path is a hidden location or not a markdown file."""
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Not a markdown file: {path.name!r}")
    if _is_hidden(path):
        raise ValueError(
            f"Access to hidden/system paths is not allowed: {path.relative_to(_vault_root())}"
        )


def _inside_vault(path: Path) -> bool:
    """True if the path's real location (after following symlinks) is inside the active vault."""
    try:
        path.resolve().relative_to(_vault_root())
        return True
    except ValueError:
        return False


def _iter_notes(base: Optional[Path] = None):
    """Yield all non-hidden .md/.markdown files under base (default: the active vault root).

    Symlinked files that point outside the vault are skipped, so listing and
    search can never expose content the path guard in _resolve() would reject.
    """
    for root, dirs, files in os.walk(base or _vault_root()):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            p = Path(root) / fname
            if p.suffix.lower() in ALLOWED_EXTENSIONS and _inside_vault(p):
                yield p


# ── vault management tools ────────────────────────────────────────────────────

@mcp.tool()
def list_vaults() -> dict:
    """List all configured vaults and indicate which one is currently active."""
    return {
        "vaults": [
            {
                "name": name,
                "path": str(path),
                "active": name == _active_vault,
            }
            for name, path in _VAULTS.items()
        ],
        "active_vault": _active_vault,
    }


@mcp.tool()
def get_active_vault() -> dict:
    """Return the name and path of the currently active vault."""
    return {"name": _active_vault, "path": str(_vault_root())}


@mcp.tool()
def switch_vault(name: str) -> dict:
    """
    Switch to a different vault by name for this session.

    Use list_vaults() to see available vault names. The switch persists for
    the lifetime of this Claude Desktop session; it resets to the default
    vault on restart.
    """
    global _active_vault
    if name not in _VAULTS:
        raise ValueError(
            f"Unknown vault {name!r}. Available: {sorted(_VAULTS.keys())}"
        )
    _active_vault = name
    return {"active_vault": _active_vault, "path": str(_vault_root()), "ok": True}


# ── note tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def read_note(path: str) -> dict:
    """Read a note and return its body content plus parsed frontmatter."""
    p = _resolve(path)
    _assert_note(p)
    if not p.exists():
        raise FileNotFoundError(f"Note not found: {path!r}")
    post = frontmatter.load(str(p))
    return {
        "path": str(p.relative_to(_vault_root())),
        "vault": _active_vault,
        "frontmatter": dict(post.metadata),
        "content": post.content,
    }


@mcp.tool()
def write_note(
    path: str,
    content: str,
    mode: str = "overwrite",
    frontmatter_data: Optional[dict] = None,
) -> dict:
    """
    Write content to a note.

    mode: "overwrite" (default), "append", or "prepend".
    frontmatter_data: only used when mode="overwrite"; sets the YAML header.
    """
    if mode not in ("overwrite", "append", "prepend"):
        raise ValueError(f"Invalid mode {mode!r}. Must be overwrite, append, or prepend.")
    if frontmatter_data and mode != "overwrite":
        raise ValueError("frontmatter_data can only be set when mode='overwrite'.")

    p = _resolve(path)
    _assert_note(p)
    p.parent.mkdir(parents=True, exist_ok=True)

    if mode == "overwrite":
        if frontmatter_data:
            post = frontmatter.Post(content, **frontmatter_data)
            text = frontmatter.dumps(post)
        else:
            text = content
        p.write_text(text, encoding="utf-8")
    else:
        existing = p.read_text(encoding="utf-8") if p.exists() else ""
        if mode == "append":
            text = (existing.rstrip("\n") + "\n\n" + content) if existing else content
        else:
            text = (content + "\n\n" + existing.lstrip("\n")) if existing else content
        p.write_text(text, encoding="utf-8")

    return {"path": str(p.relative_to(_vault_root())), "vault": _active_vault, "mode": mode, "ok": True}


@mcp.tool()
def patch_note(
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> dict:
    """
    Exact string replace inside a note without rewriting the whole file.

    Errors if old_string is not found, or if there are multiple matches and
    replace_all is False.
    """
    p = _resolve(path)
    _assert_note(p)
    if not p.exists():
        raise FileNotFoundError(f"Note not found: {path!r}")

    text = p.read_text(encoding="utf-8")
    count = text.count(old_string)

    if count == 0:
        raise ValueError(f"String not found in note: {old_string!r}")
    if count > 1 and not replace_all:
        raise ValueError(
            f"Found {count} occurrences. Pass replace_all=True to replace all, "
            "or provide a more specific string."
        )

    p.write_text(text.replace(old_string, new_string), encoding="utf-8")
    return {"path": str(p.relative_to(_vault_root())), "vault": _active_vault, "replacements": count}


@mcp.tool()
def list_notes(subfolder: str = "") -> dict:
    """List all markdown notes in the active vault, or within a specific subfolder."""
    root = _vault_root()
    if subfolder:
        base = _resolve(subfolder)
        if _is_hidden(base):
            raise ValueError(f"Access to hidden folders is not allowed: {subfolder!r}")
        if not base.is_dir():
            raise ValueError(f"Subfolder not found: {subfolder!r}")
    else:
        base = root
    notes = sorted(str(p.relative_to(root)) for p in _iter_notes(base))

    return {"vault": _active_vault, "notes": notes, "count": len(notes)}


@mcp.tool()
def search_notes(query: str, limit: int = 10) -> dict:
    """
    Case-insensitive substring search across all notes in the active vault.

    Returns up to `limit` matches with path, line number, and a short excerpt.
    Filename matches are prioritised over content matches.
    """
    q = query.lower()
    root = _vault_root()
    results = []

    for p in _iter_notes():
        rel = str(p.relative_to(root))

        if q in p.name.lower():
            results.append({"path": rel, "line": 0, "excerpt": "(filename match)"})
        else:
            try:
                lines = p.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                if q in line.lower():
                    results.append({"path": rel, "line": i, "excerpt": line.strip()[:200]})
                    break

        if len(results) >= limit:
            break

    return {"vault": _active_vault, "query": query, "matches": results, "count": len(results)}


@mcp.tool()
def get_frontmatter(path: str) -> dict:
    """Return only the YAML frontmatter of a note as a dict."""
    p = _resolve(path)
    _assert_note(p)
    if not p.exists():
        raise FileNotFoundError(f"Note not found: {path!r}")
    post = frontmatter.load(str(p))
    return {"path": str(p.relative_to(_vault_root())), "vault": _active_vault, "frontmatter": dict(post.metadata)}


@mcp.tool()
def update_frontmatter(path: str, updates: dict, merge: bool = True) -> dict:
    """
    Update a note's frontmatter without touching its body.

    merge=True (default) preserves existing keys and only updates the ones in `updates`.
    merge=False replaces the entire frontmatter with `updates`.
    """
    p = _resolve(path)
    _assert_note(p)
    if not p.exists():
        raise FileNotFoundError(f"Note not found: {path!r}")

    post = frontmatter.load(str(p))
    if merge:
        post.metadata.update(updates)
    else:
        post.metadata = dict(updates)

    p.write_text(frontmatter.dumps(post), encoding="utf-8")
    return {"path": str(p.relative_to(_vault_root())), "vault": _active_vault, "frontmatter": dict(post.metadata)}


@mcp.tool()
def delete_note(path: str, confirm_path: str) -> dict:
    """
    Soft-delete a note by moving it to .trash/ inside the active vault.

    Never hard-deletes. You must pass the same path as both `path` and
    `confirm_path`; any mismatch is rejected as a safeguard.
    """
    if path != confirm_path:
        raise ValueError(
            f"Deletion rejected: path {path!r} does not match confirm_path {confirm_path!r}. "
            "Both arguments must be identical."
        )

    root = _vault_root()
    p = _resolve(path)
    _assert_note(p)
    if not p.exists():
        raise FileNotFoundError(f"Note not found: {path!r}")

    rel = p.relative_to(root)
    trash_dest = root / ".trash" / rel
    trash_dest.parent.mkdir(parents=True, exist_ok=True)

    if trash_dest.exists():
        stamp = int(time.time())
        trash_dest = trash_dest.with_stem(f"{trash_dest.stem}_{stamp}")

    shutil.move(str(p), str(trash_dest))
    return {
        "moved_from": str(rel),
        "moved_to": str(trash_dest.relative_to(root)),
        "vault": _active_vault,
        "ok": True,
    }


@mcp.tool()
def get_vault_stats() -> dict:
    """Return note count, folder count, total size, and the 5 most recently modified notes."""
    root = _vault_root()
    notes = list(_iter_notes())
    total_size = sum(p.stat().st_size for p in notes)

    folders = {
        str(p.parent.relative_to(root))
        for p in notes
        if p.parent != root
    }
    folders.discard(".")

    recent = sorted(notes, key=lambda p: p.stat().st_mtime, reverse=True)[:5]

    return {
        "vault": _active_vault,
        "note_count": len(notes),
        "folder_count": len(folders),
        "total_size_bytes": total_size,
        "total_size_kb": round(total_size / 1024, 1),
        "recently_modified": [
            {"path": str(p.relative_to(root)), "modified_ts": p.stat().st_mtime}
            for p in recent
        ],
    }


if __name__ == "__main__":
    mcp.run()
