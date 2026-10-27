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


class TestUnmodelledAttributes:
    """git can also rewrite a file on add through a filter (LFS), a working-tree encoding or
    `ident`, and whether it does depends on the committer's machine. Those files are not
    vendored, so a pin never depends on which drivers happen to be installed."""

    def test_filter_encoding_and_ident_files_are_dropped(self, repo):
        tree = repo / "t"
        _write(tree, ".gitattributes",
               b"*.json filter=lfs\n*.c ident\n*.txt working-tree-encoding=UTF-16\n")
        keep = _write(tree, "server.py", b"x\r\n")
        lfs = _write(tree, "data.json", b"{}")
        ident = _write(tree, "x.c", b"/* $Id$ */")
        enc = _write(tree, "notes.txt", b"hi")
        written = [tree / ".gitattributes", keep, lfs, ident, enc]
        dropped = H.commit_view(written, repo)
        assert dropped == 3
        assert keep.exists() and not lfs.exists() and not ident.exists() and not enc.exists()


def _pin(**kw):
    base = dict(repo="o/r", dir="", hit="server.py", commit="c" * 40, license="MIT",
                created_at="2026-01-01", stars=0, phase="servers", surface="mcp",
                files=1, omitted=0, bytes=1, tree_sha256="0" * 64, name="gh-o-r")
    base.update(kw)
    return H.Pin(**base)


class TestCloneDirSurvivesGitFailure:
    """A git error while making the committed view used to raise out of a clone thread and
    abort the whole harvest after other trees were already written. It now fails that tree."""

    def test_returns_none_and_cleans_up(self, tmp_path, monkeypatch):
        def fake_run(cmd, **kw):
            if cmd[:2] == ["git", "clone"]:
                d = pathlib.Path(cmd[-1])
                d.mkdir(parents=True)
                (d / "server.py").write_text("x")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        def boom(written, repo=None):
            raise RuntimeError("git check-attr failed: bad .gitattributes")

        monkeypatch.setattr(H.subprocess, "run", fake_run)
        monkeypatch.setattr(H, "commit_view", boom)
        dest = tmp_path / "gh-x"
        assert H.clone_dir("o/r", "c" * 40, "", dest) is None
        assert not dest.exists()


class TestRebuildSwapsOnlyAMatch:
    """--from-pins used to rebuild straight into the committed tree, so a drifted rebuild had
    already replaced it by the time the hash was compared, while the run said nothing was
    rewritten. A rebuild now lands beside the tree and replaces it only if it matches."""

    def _fake_clone(self, content, digest):
        def clone(repo, commit, directory, dest):
            dest.mkdir(parents=True)
            (dest / "server.py").write_text(content)
            return 1, len(content), digest, 0
        return clone

    def test_a_match_replaces_the_tree(self, tmp_path):
        dest = tmp_path / "gh-o-r"
        _write(dest, "server.py", b"old")
        state = H.rebuild_if_matches(_pin(tree_sha256="a" * 64), dest, self._fake_clone("new", "a" * 64))
        assert state == "ok"
        assert (dest / "server.py").read_text() == "new"
        assert not dest.with_name("gh-o-r.rebuild").exists()

    def test_drift_leaves_the_committed_tree_untouched(self, tmp_path):
        dest = tmp_path / "gh-o-r"
        _write(dest, "server.py", b"committed")
        state = H.rebuild_if_matches(_pin(tree_sha256="a" * 64), dest, self._fake_clone("new", "b" * 64))
        assert state == "drifted"
        assert (dest / "server.py").read_text() == "committed"
        assert not dest.with_name("gh-o-r.rebuild").exists()

    def test_failure_leaves_the_committed_tree_untouched(self, tmp_path):
        dest = tmp_path / "gh-o-r"
        _write(dest, "server.py", b"committed")
        state = H.rebuild_if_matches(_pin(), dest, lambda *a: None)
        assert state == "failed"
        assert (dest / "server.py").read_text() == "committed"


class TestReconcileNeverDeletesAPinnedTree:
    """The regression behind the orphan pins: a tree an earlier run pinned, whose bytes no
    longer match, was deleted while its pin was kept. It must be kept and reported."""

    def test_drifted_tree_is_kept_and_reported(self, tmp_path, monkeypatch):
        out = tmp_path / "corpus" / "benign"
        monkeypatch.setattr(H, "ROOT", tmp_path)
        monkeypatch.setattr(H, "OUT", out)
        tree = out / "mcp" / "gh-o-r"
        _write(tree, "server.py", b"committed")
        label = tree.with_suffix(".yaml")
        label.write_text(f"# {H.MARKER}\nid: ben-mcp-gh-o-r\n")
        stale = out / "mcp" / "gh-gone.yaml"
        stale.write_text(f"# {H.MARKER}\nid: ben-mcp-gh-gone\n")

        stats = H.reconcile_labels([_pin(tree_sha256="0" * 64)], fresh=set(), added="2026-10-27")

        assert tree.exists() and label.exists()
        assert stats["drifted"] == [("gh-o-r", "drifted")]
        assert not stale.exists() and stats["removed"] == 1
