#!/usr/bin/env python3
"""Smoke test for mcp-notes-server storage/tool logic.

Runs WITHOUT an MCP host and without the mcp SDK installed: if the SDK is
missing, a minimal stub stands in for FastMCP so the module can be imported
and its tool functions called directly. If the SDK is installed, the real
decorators are used and the functions are called the same way.

Usage: python tests/smoke_test.py   (exit code 0 = all checks passed)
"""
import importlib.util
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "..", "server.py")


def load_server(storage_dir):
    try:
        import mcp.server.fastmcp  # noqa: F401
    except ImportError:
        # Minimal stub: FastMCP class whose .tool() decorator is a passthrough.
        stub = types.ModuleType("mcp")
        server_pkg = types.ModuleType("mcp.server")
        fastmcp_mod = types.ModuleType("mcp.server.fastmcp")

        class FastMCP:  # noqa: D101
            def __init__(self, *a, **k):
                pass

            def tool(self, *a, **k):
                def deco(fn):
                    return fn

                return deco

            def run(self):
                pass

        fastmcp_mod.FastMCP = FastMCP
        sys.modules.setdefault("mcp", stub)
        sys.modules["mcp.server"] = server_pkg
        sys.modules["mcp.server.fastmcp"] = fastmcp_mod

    spec = importlib.util.spec_from_file_location("notes_server", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Redirect storage into the temp dir so the test never touches real notes.
    mod._STORAGE_PATH = os.path.join(storage_dir, "notes.json")
    return mod


def main():
    checks = []
    with tempfile.TemporaryDirectory() as td:
        m = load_server(td)
        n1 = m.create_note("Shopping list", "milk, eggs, coffee")
        checks.append(("create returns id/title", bool(n1["id"]) and n1["title"] == "Shopping list"))
        n2 = m.create_note("Release checklist", "tag v1.0, update changelog")
        listed = m.list_notes()
        checks.append(("list returns 2, newest first", len(listed) == 2 and listed[0]["id"] == n2["id"]))
        hits = m.search_notes("EGGS")
        checks.append(("search is case-insensitive, 1 hit", len(hits) == 1 and hits[0]["id"] == n1["id"]))
        try:
            m.create_note("   ")
            checks.append(("empty title rejected", False))
        except ValueError:
            checks.append(("empty title rejected", True))
        try:
            m.search_notes("")
            checks.append(("empty query rejected", False))
        except ValueError:
            checks.append(("empty query rejected", True))
        raw = json.load(open(os.path.join(td, "notes.json")))
        checks.append(("storage file holds 2 notes", len(raw["notes"]) == 2))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), "-", name)
    print(f"{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
