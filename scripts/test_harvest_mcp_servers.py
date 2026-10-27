"""Tests for the parts of the MCP/skills harvest that decide what a pin claims.

A pin's tree_sha256 is the corpus's integrity claim for a harvested tree, and it is only worth
anything if it describes the bytes git actually commits. Two things broke that silently: a
vendored repository's own .gitignore made `git add` skip files the hash had counted, and its own
.gitattributes rewrote line endings the hash had not. Thirteen trees drifted that way, and the
re-harvest deleted three more whose committed bytes no longer matched their pins. These tests pin
down the helpers that make a pin describe what git keeps, and the rule that a drifted tree is
reported rather than deleted.

Run: python3 -m pytest scripts/test_harvest_mcp_servers.py
"""

import importlib.util
import pathlib
import subprocess
import sys
from typing import NamedTuple

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parent / "harvest-mcp-servers.py"


def _load():
    spec = importlib.util.spec_from_file_location("harvest_mcp_servers", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


H = _load()


@pytest.fixture
def repo(tmp_path):
    """An empty git repository with no global excludes leaking in from the machine."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "core.excludesFile", "/dev/null"], check=True)
    return tmp_path


def _write(base: pathlib.Path, rel: str, data: bytes) -> pathlib.Path:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


class TestGitIgnored:
    """A vendored tree's own .gitignore applies to it inside this repository too, so a file the
    upstream tracked can still be skipped by `git add` here."""

    def test_nested_gitignore_is_honoured(self, repo):
        tree = repo / "corpus" / "benign" / "mcp" / "gh-x"
        _write(tree, ".gitignore", b"*.md\n.env\n")
        keep = _write(tree, "server.py", b"x")
        md = _write(tree, "README.md", b"# x")
        env = _write(tree, ".env", b"K=1")
        got = H.git_ignored([keep, md, env, tree / ".gitignore"], repo)
        assert got == {md, env}

    def test_nothing_ignored_is_an_empty_set(self, repo):
        p = _write(repo, "a/b.py", b"x")
        assert H.git_ignored([p], repo) == set()

    def test_a_tracked_file_is_kept_even_when_ignored(self, repo):
        tree = repo / "t"
        _write(tree, ".gitignore", b"*.md\n")
        md = _write(tree, "README.md", b"# x")
        subprocess.run(["git", "-C", str(repo), "add", "-f", str(md)], check=True)
        assert H.git_ignored([md], repo) == set()


class TestAsCommitted:
    """What git stores for a file is decided by its attributes, not by its bytes on disk."""

    @pytest.mark.parametrize("text,eol,data,want", [
        ("set", "unspecified", b"a\r\nb\r\n", b"a\nb\n"),
        ("unspecified", "lf", b"a\r\nb\r\n", b"a\nb\n"),
        ("auto", "unspecified", b"a\r\nb\r\n", b"a\nb\n"),
        ("auto", "unspecified", b"a\r\n\x00b", b"a\r\n\x00b"),
        ("unset", "lf", b"a\r\nb\r\n", b"a\r\nb\r\n"),
        ("unspecified", "unspecified", b"a\r\nb\r\n", b"a\r\nb\r\n"),
    ])
    def test_normalisation_follows_the_attributes(self, text, eol, data, want):
        assert H.as_committed(data, text, eol) == want

    def test_nested_gitattributes_is_read(self, repo):
        tree = repo / "t"
        _write(tree, ".gitattributes", b"* text=auto eol=lf\n")
        p = _write(tree, "run.mjs", b"a\r\n")
        attrs = H.git_text_attrs([p], repo)
        assert attrs[p] == ("auto", "lf")

    def test_root_negation_keeps_bytes_as_they_are(self, repo):
        _write(repo, ".gitattributes", b"vendored/** -text\n")
        p = _write(repo, "vendored/run.mjs", b"a\r\n")
        text, eol = H.git_text_attrs([p], repo)[p]
        assert H.as_committed(p.read_bytes(), text, eol) == b"a\r\n"


class TestStillQualifies:
    """A harvested tree is a sample because of one file — a server body, or a SKILL.md. If the
    bounds drop every such file, what is left is not the thing the pin says it is."""

    def test_mcp_tree_with_a_server_qualifies(self, tmp_path):
        _write(tmp_path, "src/index.ts",
               b'import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";\n'
               b'const s = new McpServer({name: "x", version: "1"});\ns.tool("t", "", {}, async () => ({}));\n')
        assert H.still_qualifies(tmp_path, "mcp")

    def test_mcp_tree_without_a_server_does_not(self, tmp_path):
        _write(tmp_path, "README.md", b"# a server, once")
        _write(tmp_path, "client.ts", b'import { Client } from "@modelcontextprotocol/sdk/client/index.js";\n')
        assert not H.still_qualifies(tmp_path, "mcp")

    def test_skills_tree_needs_a_skill_md(self, tmp_path):
        _write(tmp_path, "scripts/run.py", b"print(1)")
        assert not H.still_qualifies(tmp_path, "skills")
        _write(tmp_path, "SKILL.md", b"---\nname: x\n---\n")
        assert H.still_qualifies(tmp_path, "skills")


class _Pin(NamedTuple):
    tree_sha256: str


class TestExistingTreeState:
    """The re-harvest used to delete any already-pinned tree whose bytes no longer matched its
    pin, and keep the pin. A drifted tree is a question for a person, never a deletion."""

    def test_matching_tree_is_ok(self, tmp_path):
        _write(tmp_path, "a.py", b"x")
        pin = _Pin(H.tree_hash_of(tmp_path)[2])
        assert H.existing_tree_state(tmp_path, pin) == "ok"

    def test_missing_tree(self, tmp_path):
        assert H.existing_tree_state(tmp_path / "gone", _Pin("0" * 64)) == "missing"

    def test_drifted_tree(self, tmp_path):
        _write(tmp_path, "a.py", b"x")
        assert H.existing_tree_state(tmp_path, _Pin("0" * 64)) == "drifted"
