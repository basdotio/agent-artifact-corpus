"""Tests for the decisions that define the harvested denominator.

Everything network-facing in harvest-claude-config.py is a thin wrapper over `gh`. What is
worth testing is the part with judgement in it: whether a file is on a real load path, and
which surfaces its content puts it on. Those two functions decide what the false-positive
denominator contains, and a quiet mistake in either is exactly the kind that produces a
flattering number nobody can see is wrong.

Run: python3 -m pytest scripts/test_harvest_claude_config.py
"""

import importlib.util
import json
import pathlib
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parent / "harvest-claude-config.py"


def _load():
    spec = importlib.util.spec_from_file_location("harvest_claude_config", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


H = _load()


class TestIsLoadPath:
    """A template is documentation. An agent never loads it, and a scanner is not wrong to
    treat it differently — counting one as a benign config inflates the denominator with
    something nobody runs."""

    @pytest.mark.parametrize("path", [
        ".claude/settings.json",
        "settings.json",
        ".claude/settings.local.json",
        "some/nested/project/.claude/settings.json",
    ])
    def test_real_load_paths_accepted(self, path):
        assert H.is_load_path(path, "settings")

    @pytest.mark.parametrize("path", [
        "settings.json.template",
        ".claude/settings.json.bak",
        "templates/settings.json.tmpl",
        "settings.json.example",
        "claude/settings.jsonnet",
        "docs/Add PreToolUse hook to settings.json.md",
        ".vscode/settings.json.dist",
    ])
    def test_non_load_paths_rejected(self, path):
        assert not H.is_load_path(path, "settings")

    def test_mcp_wants_only_the_dotfile(self):
        assert H.is_load_path(".mcp.json", "mcp")
        assert H.is_load_path("sub/project/.mcp.json", "mcp")
        # `mcp.json` without the dot is not the project config file.
        assert not H.is_load_path("mcp.json", "mcp")
        assert not H.is_load_path(".claude/settings.json", "mcp")


class TestSurfaceAssignment:
    """Content decides the surface, not the filename. And one file is routinely two
    surfaces — that is why a label's `surface` is a list."""

    def test_both_blocks_give_both_surfaces(self):
        doc = {"hooks": {"PreToolUse": [{}]}, "permissions": {"deny": ["Bash(rm -rf *)"]}}
        assert H.surfaces_of("settings", doc) == (("hooks", "permission"), False)

    def test_hooks_only(self):
        assert H.surfaces_of("settings", {"hooks": {"PostToolUse": [{}]}}) == (("hooks",), False)

    def test_permissions_only(self):
        doc = {"permissions": {"allow": ["Bash(ls)"]}}
        assert H.surfaces_of("settings", doc) == (("permission",), False)

    def test_empty_blocks_exercise_no_surface(self):
        # A settings file whose blocks are present but empty tests nothing on either load
        # path. Keeping it would pad the denominator with a sample no rule can fire on, which
        # moves a false-positive rate in the flattering direction.
        assert H.surfaces_of("settings", {"hooks": {}, "permissions": {}}) == ((), False)
        assert H.surfaces_of("settings", {"cleanupPeriodDays": 30}) == ((), False)

    def test_remote_server_is_a_connector(self):
        for server in (
            {"url": "https://mcp.example.com/sse"},
            {"type": "http", "url": "https://example.com/mcp"},
            {"type": "sse"},
            {"type": "streamable-http"},
        ):
            doc = {"mcpServers": {"x": server}}
            assert H.surfaces_of("mcp", doc) == (("connector",), True), server

    def test_local_process_is_not_a_connector(self):
        # `connector` means the config reaches something outside the agent. A bare command is
        # a local process launch; calling it a connector would blur the one distinction that
        # separates this surface from `mcp`.
        doc = {"mcpServers": {"x": {"command": "npx", "args": ["-y", "some-server"]}}}
        assert H.surfaces_of("mcp", doc) == ((), False)

    def test_mixed_config_counts_as_a_connector(self):
        doc = {"mcpServers": {
            "local": {"command": "uvx", "args": ["thing"]},
            "remote": {"type": "http", "url": "https://example.com/mcp"},
        }}
        assert H.surfaces_of("mcp", doc) == (("connector",), True)

    def test_malformed_server_entries_do_not_crash(self):
        for doc in ({"mcpServers": "nonsense"}, {"mcpServers": {"x": "nonsense"}},
                    {"mcpServers": {}}, {}, []):
            assert H.surfaces_of("mcp", doc) == ((), False)


class TestLoadPathInsideTheTree:
    """The tree must reproduce the path the file really loads from. A scanner that looks for
    `.claude/settings.json` and finds a bare `settings.json` scores a false pass."""

    def test_settings_go_under_dot_claude(self):
        pin = H.Pin(repo="o/r", path="settings.json", commit="c", sha256="s", license="MIT",
                    surfaces=("hooks",), remote=False, name="n")
        assert H.load_path_for(pin) == ".claude/settings.json"

    def test_already_nested_settings_keep_the_directory(self):
        pin = H.Pin(repo="o/r", path="deep/.claude/settings.local.json", commit="c", sha256="s",
                    license="MIT", surfaces=("permission",), remote=False, name="n")
        assert H.load_path_for(pin) == ".claude/settings.local.json"

    def test_mcp_config_sits_at_the_tree_root(self):
        pin = H.Pin(repo="o/r", path="sub/.mcp.json", commit="c", sha256="s", license="MIT",
                    surfaces=("connector",), remote=True, name="n")
        assert H.load_path_for(pin) == ".mcp.json"


class TestRenderedLabel:
    def _label(self, surfaces, remote=False):
        pin = H.Pin(repo="o/r", path=".claude/settings.json", commit="abc123", sha256="d" * 64,
                    license="MIT", surfaces=surfaces, remote=remote, name="o-r-settings")
        return H.render_label(pin, "o/r/.claude/settings.json", "2026-09-17")

    def test_single_surface_is_a_scalar(self):
        assert "surface: hooks\n" in self._label(("hooks",))

    def test_two_surfaces_are_a_list(self):
        assert "surface: [hooks, permission]\n" in self._label(("hooks", "permission"))

    def test_the_label_never_claims_a_review_happened(self):
        # Red line 3: "no scanner complained" is not evidence of benignity, and neither is
        # "it was published". The note has to say what benign actually means here.
        note = self._label(("hooks",))
        assert "not reviewed and not audited" in note
        assert "labeled_before_run: true" in note

    def test_sha256_is_carried_so_the_validator_can_check_it(self):
        assert f"sha256: {'d' * 64}" in self._label(("hooks",))


class TestPromotedElsewhere:
    """An artifact promoted to another class by hand must not come back as benign on the next
    harvest: the same file in two classes lets a scanner be both right and wrong about it."""

    @pytest.fixture
    def corpus(self, tmp_path, monkeypatch):
        monkeypatch.setattr(H, "ROOT", tmp_path)
        (tmp_path / "corpus" / "hard-negative" / "hooks").mkdir(parents=True)
        return tmp_path

    def _pin(self, repo="o/r", path=".claude/settings.json"):
        return H.Pin(repo=repo, path=path, commit="c", sha256="s", license="MIT",
                     surfaces=("hooks",), remote=False, name="n")

    def test_claimed_artifact_is_skipped(self, corpus):
        (corpus / "corpus" / "hard-negative" / "hooks" / "x.yaml").write_text(
            'source: "https://github.com/o/r/blob/abc/.claude/settings.json"\n')
        assert H.promoted_elsewhere(self._pin())

    def test_a_different_file_in_the_same_repo_is_not_claimed(self, corpus):
        (corpus / "corpus" / "hard-negative" / "hooks" / "x.yaml").write_text(
            'source: "https://github.com/o/r/blob/abc/.claude/settings.json"\n')
        assert not H.promoted_elsewhere(self._pin(path=".mcp.json"))

    def test_unclaimed_artifact_passes(self, corpus):
        assert not H.promoted_elsewhere(self._pin())


def test_settings_keys_cover_the_blocks_the_surfaces_need(tmp_path):
    """The content gate must not reject a file the surface assignment would have accepted, or
    a real config would be dropped for carrying nothing but the block we care about."""
    for key in ("hooks", "permissions"):
        doc = json.loads(json.dumps({key: {"x": [{}]}}))
        assert H.SETTINGS_KEYS & set(doc), key
        assert H.surfaces_of("settings", doc)[0], key
