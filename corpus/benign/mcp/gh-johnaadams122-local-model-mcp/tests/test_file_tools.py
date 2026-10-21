"""Tests for local_llm.file_tools. requests.post is patched; no live Ollama."""

import ast
import builtins
import contextlib
import inspect
import io
import json
import zipfile
import os
import tempfile
import subprocess
import sys
import unittest
from unittest import mock

from local_llm import file_tools, ollama_client
from local_llm.ollama_client import OllamaError


def _make_response(text):
    resp = mock.Mock()
    resp.status_code = 200
    resp.json.return_value = {"response": text}
    resp.text = ""
    return resp


class FileToolsBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # _ROOTS is a resolved LIST of roots (not a single root), and
        # realpath here is load-bearing -- the containment
        # predicates compare against OS-canonical paths, and mkdtemp on
        # Windows hands back a short-name (8.3) form that realpath expands.
        patcher = mock.patch.object(
            file_tools, "_ROOTS", [os.path.realpath(self.tmpdir)])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, name, content):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def _mklink_j(self, link, target):
        """Create a directory junction, failing the TEST if it cannot be made.
        Windows is a project constraint, and a junction needs no Developer
        Mode and no elevation: a failed junction must FAIL a required security
        row, never skip it green."""
        result = subprocess.run(["cmd", "/c", "mklink", "/J", link, target],
                                capture_output=True)
        self.assertEqual(
            result.returncode, 0,
            (result.stdout + result.stderr).decode("mbcs", "replace"))


class TestResolveAllowed(FileToolsBase):
    def test_outside_root_rejected(self):
        other = tempfile.mkdtemp()
        outside = os.path.join(other, "x.txt")
        with open(outside, "w") as handle:
            handle.write("hi")
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools.summarize_file(outside)

    def test_missing_file_rejected(self):
        with self.assertRaisesRegex(ValueError, "not a file"):
            file_tools.summarize_file(os.path.join(self.tmpdir, "nope.txt"))

    def test_size_cap_rejected_with_guidance(self):
        path = self._write("big.txt", "x" * 100)
        with mock.patch.object(file_tools, "MAX_FILE_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "file too large"):
                file_tools.summarize_file(path)


class TestSummarizeFile(FileToolsBase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_small_file_full_coverage(self, mock_post):
        mock_post.return_value = _make_response("a fine summary")
        path = self._write(
            "log.txt",
            "line one ok\n2026-07-22 ERROR root: boom happened\nline three\n")
        out = file_tools.summarize_file(path, max_words=50)
        self.assertIn("UNVERIFIED-DIGEST", out["label"])
        self.assertEqual(out["coverage"], "FULL")
        self.assertEqual(out["lines"], 3)
        self.assertEqual(out["summary"], "a fine summary")
        # notable lines are code-grepped and byte-verbatim with line numbers
        self.assertEqual(len(out["notable_lines"]), 1)
        self.assertEqual(out["notable_lines"][0]["line_number"], 2)
        self.assertEqual(out["notable_lines"][0]["line"],
                         "2026-07-22 ERROR root: boom happened")
        # model pinned per-call
        body = mock_post.call_args.kwargs["json"]
        self.assertEqual(body["model"], file_tools.FILE_MODEL)

    @mock.patch.object(ollama_client.requests, "post")
    def test_multi_chunk_maps_then_reduces(self, mock_post):
        mock_post.return_value = _make_response("part")
        # ~30k chars of 100-char lines -> 3 chunks at the 12k cap
        path = self._write("big.txt", ("y" * 99 + "\n") * 300)
        out = file_tools.summarize_file(path, max_words=100)
        self.assertEqual(out["chunks_total"], 3)
        self.assertEqual(out["coverage"], "FULL")
        # 3 map calls + 1 reduce call
        self.assertEqual(mock_post.call_count, 4)

    @mock.patch.object(ollama_client.requests, "post")
    def test_time_budget_partial_is_loud(self, mock_post):
        mock_post.return_value = _make_response("part")
        path = self._write("big.txt", ("y" * 99 + "\n") * 300)  # 3 chunks
        # monotonic: deadline calc, chunk1 check (in budget), chunk2 check (over)
        with mock.patch.object(file_tools.time, "monotonic",
                               side_effect=[0, 0, 1000, 1000]):
            out = file_tools.summarize_file(path, max_words=100)
        self.assertIn("PARTIAL", out["coverage"])
        self.assertIn("NOT covered", out["coverage"])

    @mock.patch.object(ollama_client.requests, "post")
    def test_budget_exhausted_before_first_chunk_raises(self, mock_post):
        path = self._write("f.txt", "hello\n")
        with mock.patch.object(file_tools.time, "monotonic",
                               side_effect=[0, 1000]):
            with self.assertRaises(OllamaError):
                file_tools.summarize_file(path)

    def test_bad_max_words_raises(self):
        path = self._write("f.txt", "hello\n")
        with self.assertRaises(ValueError):
            file_tools.summarize_file(path, max_words=0)


class TestExtractJsonFile(FileToolsBase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_verbatim_fields_kept_fabricated_nulled(self, mock_post):
        mock_post.return_value = _make_response(
            json.dumps({"vendor": "Acme Tools", "total": "999.99"}))
        path = self._write("receipt.txt",
                           chr(36).join(["Receipt from Acme Tools. Total due ", "226.31.\n"]))
        out = file_tools.extract_json_file(
            path, {"vendor": "string", "total": "string"})
        self.assertEqual(out["fields"]["vendor"], "Acme Tools")
        self.assertIsNone(out["fields"]["total"], "999.99 is not in the source")
        self.assertEqual(out["unverified_fields"], ["total"])
        self.assertIn("NULLED", out["note"])

    @mock.patch.object(ollama_client.requests, "post")
    def test_normalized_match_covers_commas_and_case(self, mock_post):
        mock_post.return_value = _make_response(
            json.dumps({"files": "12,441", "job": "NIGHTLY-ops"}))
        path = self._write("r.txt", "job nightly-ops moved 12441 files\n")
        out = file_tools.extract_json_file(
            path, {"files": "string", "job": "string"})
        self.assertEqual(out["unverified_fields"], [])

    @mock.patch.object(ollama_client.requests, "post")
    def test_model_pinned_per_call(self, mock_post):
        mock_post.return_value = _make_response(json.dumps({"a": "hello"}))
        path = self._write("r.txt", "hello\n")
        file_tools.extract_json_file(path, {"a": "string"})
        body = mock_post.call_args.kwargs["json"]
        self.assertEqual(body["model"], file_tools.FILE_MODEL)

    def test_over_cap_text_rejected(self):
        path = self._write("big.txt", "z" * (file_tools.CHUNK_CHARS + 1))
        with self.assertRaisesRegex(ValueError, "single-call cap"):
            file_tools.extract_json_file(path, {"a": "string"})

    @mock.patch.object(ollama_client.requests, "post")
    def test_fabricated_scalar_inside_array_nulls_field(self, mock_post):
        # Nested scalars must verify too, not only top-level ones.
        mock_post.return_value = _make_response(
            json.dumps({"items": ["alpha", "FABRICATED-999"]}))
        path = self._write("r.txt", "the word alpha appears here\n")
        out = file_tools.extract_json_file(path, {"items": "array"})
        self.assertIsNone(out["fields"]["items"])
        self.assertEqual(out["unverified_fields"], ["items"])

    @mock.patch.object(ollama_client.requests, "post")
    def test_nested_object_scalars_verified(self, mock_post):
        mock_post.return_value = _make_response(
            json.dumps({"meta": {"vendor": "Acme", "total": "555.55"}}))
        path = self._write("r.txt", chr(36).join(["Acme sold it for ", "12.00\n"]))
        out = file_tools.extract_json_file(path, {"meta": "object"})
        self.assertIsNone(out["fields"]["meta"], "555.55 not in source")

    @mock.patch.object(ollama_client.requests, "post")
    def test_boolean_exempt_from_grounding(self, mock_post):
        # A bool is the model's classification, not a copied figure.
        mock_post.return_value = _make_response(json.dumps({"is_receipt": True}))
        path = self._write("r.txt", "some receipt text\n")
        out = file_tools.extract_json_file(path, {"is_receipt": "boolean"})
        self.assertIs(out["fields"]["is_receipt"], True)
        self.assertEqual(out["unverified_fields"], [])


class TestNotableLineTruncation(FileToolsBase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_long_notable_line_carries_explicit_marker(self, mock_post):
        mock_post.return_value = _make_response("summary")
        long_line = "ERROR " + "x" * 500
        path = self._write("log.txt", long_line + "\nok line\n")
        out = file_tools.summarize_file(path)
        quoted = out["notable_lines"][0]["line"]
        self.assertIn("[TRUNCATED: read line 1]", quoted)
        self.assertTrue(quoted.startswith("ERROR "))

    @mock.patch.object(ollama_client.requests, "post")
    def test_short_notable_line_is_byte_verbatim(self, mock_post):
        mock_post.return_value = _make_response("summary")
        path = self._write("log.txt", "ERROR short and sweet\n")
        out = file_tools.summarize_file(path)
        self.assertEqual(out["notable_lines"][0]["line"],
                         "ERROR short and sweet")


if __name__ == "__main__":
    unittest.main()


def _enable_case_sensitivity(test, directory):
    """fsutil setCaseSensitiveInfo needs NO elevation (measured rc=0 from an
    unelevated shell). A required security row must FAIL, never skip green, so
    a non-zero return fails the calling test with the real output."""
    result = subprocess.run(
        ["fsutil", "file", "setCaseSensitiveInfo", directory, "enable"],
        capture_output=True)
    test.assertEqual(
        result.returncode, 0,
        "could not enable case sensitivity, so this row cannot run: "
        + (result.stdout + result.stderr).decode("mbcs", "replace"))


class TestParseRoots(unittest.TestCase):
    """_parse_roots is ENVIRONMENT-DECOUPLED, not pure: it reads the
    filesystem (isdir/realpath/samefile) and writes warnings to stderr. What it
    does NOT do is read os.environ -- env values arrive as arguments, so tests
    never reload the module inside a patch context."""

    def test_no_configured_roots_fails_closed(self):
        self.assertEqual(file_tools._DEFAULT_ROOTS, ())
        self.assertEqual(file_tools._parse_roots(None, None), [])

    def test_explicit_synthetic_root_is_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(
                file_tools._parse_roots(root, None),
                [os.path.realpath(root)])


    def test_present_but_blank_roots_var_fails_closed(self):
        with tempfile.TemporaryDirectory() as valid_legacy:
            for blank in ("", " ", os.pathsep):
                self.assertEqual(
                    file_tools._parse_roots(blank, valid_legacy), [])


    def test_roots_var_wins_over_legacy_var(self):
        first = tempfile.mkdtemp()
        second = tempfile.mkdtemp()
        self.assertEqual(file_tools._parse_roots(first, second),
                         [os.path.realpath(first)])

    def test_legacy_var_is_one_exact_root_never_split(self):
        weird = os.path.join(tempfile.mkdtemp(), "a;b")
        os.mkdir(weird)
        self.assertEqual(file_tools._parse_roots(None, weird),
                         [os.path.realpath(weird)])

    def test_relative_and_missing_entries_are_dropped_with_a_warning(self):
        good = tempfile.mkdtemp()
        missing = os.path.join(good, "nope")
        raw = os.pathsep.join([good, r"relative\path", missing])
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            roots = file_tools._parse_roots(raw, None)
        self.assertEqual(roots, [os.path.realpath(good)])
        self.assertIn(r"relative\path", stderr.getvalue())
        self.assertIn(missing, stderr.getvalue())

    def test_nested_roots_collapse_and_duplicates_dedupe(self):
        parent = tempfile.mkdtemp()
        child = os.path.join(parent, "child")
        os.mkdir(child)
        raw = os.pathsep.join([child, parent, parent.upper()])
        self.assertEqual(file_tools._parse_roots(raw, None),
                         [os.path.realpath(parent)])

    def test_all_entries_invalid_fails_closed_rather_than_defaulting(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(file_tools._parse_roots(r"relative\only", None), [])

    def test_invalid_roots_var_does_NOT_fall_back_to_a_valid_legacy_root(self):
        r"""Every other fail-closed row in this class tests the winning
        variable ALONE. None pairs a losing-but-VALID source with a
        winning-but-INVALID one, so nothing distinguishes "precedence is
        decided by presence" from "precedence is decided by whether the winner
        survived validation". An implementation that re-consults the legacy var
        after validation empties the list stays green on every other row in
        this class and silently restores a root the operator believed they had
        overridden."""
        legacy = tempfile.mkdtemp()          # VALID, and must NOT be consulted
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            roots = file_tools._parse_roots(r"relative\only", legacy)
        self.assertEqual(roots, [], "an invalid winner must not fall back")
        # Non-vacuity: prove the invalid entry was actually SEEN and rejected,
        # not that _parse_roots returned [] for some unrelated reason.
        self.assertIn(r"relative\only", stderr.getvalue())

        """An invalid explicit root remains closed with no implicit defaults.

        Validation must not widen the caller's configured boundary.
        """
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            roots = file_tools._parse_roots(None, r"relative\only")
        self.assertEqual(roots, [], "an invalid legacy root must not default")
        self.assertIn(r"relative\only", stderr.getvalue())

    def test_an_existing_regular_file_as_a_root_is_rejected(self):
        r"""Every dropped-entry row above uses a path that does not EXIST,
        so all of them pass against os.path.exists exactly as readily as
        against os.path.isdir. Swapping the two would accept a
        regular FILE as a root -- and containment is pure string logic that
        never asks what kind of object a root is, so `C:\...\notes.txt` as a
        root would admit `C:\...\notes.txt.bak` and anything else sharing that
        prefix. The screen must be isdir, and only this row says so."""
        holder = tempfile.mkdtemp()
        afile = os.path.join(holder, "notadir.txt")
        with open(afile, "w", encoding="utf-8") as handle:
            handle.write("x")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            roots = file_tools._parse_roots(afile, None)
        self.assertEqual(roots, [], "a regular file must not become a root")
        # Non-vacuity: the file really does exist, so os.path.exists would
        # have admitted it. Without this the row proves nothing about isdir.
        self.assertTrue(os.path.isfile(afile))
        self.assertIn(afile, stderr.getvalue())


class TestParseRootsKeepsCaseDistinctRoots(unittest.TestCase):
    r"""A case-folding dedupe silently DISCARDS one of two explicitly
    configured roots on a case-sensitive directory, and a read under the
    discarded root then passes the cheap filter and fails the case-exact
    authorization -- i.e. it becomes silently unreadable.

    Measured: with normcase dedup, configuring both Root and root kept only
    Root. Measured again: fixing ONLY the dedupe is not enough -- with a
    permissive nesting collapse, root still collapses into Root. Both the
    dedupe predicate and the collapse predicate had to change, and this class
    fails against either half-fix."""

    def _case_sensitive_pair(self):
        container = os.path.join(tempfile.mkdtemp(), "cs")
        os.mkdir(container)
        _enable_case_sensitivity(self, container)
        upper = os.path.join(container, "Root")
        lower = os.path.join(container, "root")
        os.mkdir(upper)
        os.mkdir(lower)
        # Guard: on a filesystem that ignored the request these are ONE
        # directory and every assertion below would be vacuous.
        self.assertNotEqual(os.stat(upper).st_ino, os.stat(lower).st_ino)
        return upper, lower

    def test_both_case_distinct_roots_survive_parsing(self):
        upper, lower = self._case_sensitive_pair()
        roots = file_tools._parse_roots(os.pathsep.join([upper, lower]), None)
        self.assertEqual(len(roots), 2, "a configured root was discarded: %s" % roots)
        self.assertEqual(set(roots),
                         {os.path.realpath(upper), os.path.realpath(lower)})

    # Keep method names in this class unique. Python silently keeps the LAST
    # definition of a duplicated method name, so a duplicate makes a row
    # vanish from collection with no error.

    def _junction(self, link, target):
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", link, target], capture_output=True)
        self.assertEqual(
            result.returncode, 0,
            (result.stdout + result.stderr).decode("mbcs", "replace"))

    def test_same_directory_compares_objects_not_strings(self):
        r"""Covers _same_directory DIRECTLY.

        The alias row below does NOT exercise it: os.path.realpath resolves a
        junction, so both entries canonicalize to the same STRING before the
        dedupe runs, and the case-exact nesting collapse would then remove the
        duplicate on its own. Deleting _same_directory entirely leaves that row
        green. This row does not."""
        base = tempfile.mkdtemp()
        target = os.path.join(base, "real")
        other = os.path.join(base, "other")
        os.mkdir(target)
        os.mkdir(other)
        link = os.path.join(base, "alias")
        self._junction(link, target)
        # One object reached two ways -> True, though the strings differ.
        self.assertNotEqual(link, target)
        self.assertTrue(file_tools._same_directory(link, target))
        # Two genuinely different directories -> False.
        self.assertFalse(file_tools._same_directory(target, other))
        # A nonexistent path must not raise: it fails open to "not the same",
        # which KEEPS both entries rather than silently dropping one.
        self.assertFalse(
            file_tools._same_directory(os.path.join(base, "gone"), target))

    def test_a_true_filesystem_alias_still_dedupes(self):
        # End-to-end companion to the row above: two roots naming one directory
        # collapse to one. NOTE this passes even with _same_directory deleted
        # (realpath already makes the two strings equal, and the nesting
        # collapse removes the duplicate), so it is NOT the proof that the
        # dedupe exists -- the direct row above is.
        base = tempfile.mkdtemp()
        target = os.path.join(base, "real")
        os.mkdir(target)
        link = os.path.join(base, "alias")
        self._junction(link, target)
        roots = file_tools._parse_roots(os.pathsep.join([target, link]), None)
        self.assertEqual(roots, [os.path.realpath(target)])

    def _usable(self, root_list, real_dir):
        r"""A canonical root is not enough -- it has to still AUTHORIZE reads
        beneath it. _is_within_exact is the case-SENSITIVE predicate whose
        stated precondition is that BOTH sides are already realpath-normalized,
        so it is exactly what a noncanonical root breaks."""
        note = os.path.join(real_dir, "note.txt")
        with open(note, "w", encoding="utf-8") as handle:
            handle.write("body")
        self.assertTrue(
            file_tools._is_within_exact(os.path.realpath(note), root_list[0]),
            "the parsed root no longer authorizes reads beneath it: %s"
            % root_list)

    def test_an_alias_ONLY_root_is_canonicalized_to_its_target(self):
        r"""test_a_true_filesystem_alias_still_dedupes supplies the REAL
        target first and the junction second, so the dedupe
        discards the later alias -- and the row therefore passes even if
        os.path.realpath is replaced by os.path.abspath, or dropped entirely.
        The canonicalization it appears to cover is never exercised by it.

        Configure ONLY the alias. Now nothing can discard it, and the parsed
        root must still be the OS-canonical target. An implementation that
        keeps the raw string leaves _ROOTS holding a noncanonical path, and
        the case-EXACT check -- whose precondition is that both sides are
        realpath-normalized -- then REJECTS legitimate reads underneath it.
        Fail-closed, but silent: a configured root simply stops working."""
        base = tempfile.mkdtemp()
        target = os.path.join(base, "real")
        os.mkdir(target)
        link = os.path.join(base, "alias")
        self._junction(link, target)
        roots = file_tools._parse_roots(link, None)
        self.assertEqual(roots, [os.path.realpath(target)])
        # Non-vacuity: the configured spelling really did differ from the
        # canonical one, so an abspath implementation would have kept it.
        self.assertNotEqual(os.path.abspath(link), os.path.realpath(target))
        self._usable(roots, target)

    def test_an_alias_listed_FIRST_still_canonicalizes(self):
        r"""Ordering half of the row above. Same construction as the
        existing alias row but with the junction AHEAD of its target -- the
        order that row does not use. Whichever entry survives the dedupe, the
        surviving STRING must be the canonical target."""
        base = tempfile.mkdtemp()
        target = os.path.join(base, "real")
        os.mkdir(target)
        link = os.path.join(base, "alias")
        self._junction(link, target)
        roots = file_tools._parse_roots(os.pathsep.join([link, target]), None)
        self.assertEqual(roots, [os.path.realpath(target)])
        self._usable(roots, target)

    def test_a_wrong_case_root_canonicalizes_to_the_true_on_disk_case(self):
        r"""Case half of the alias-only row. realpath restores true on-disk
        case (measured). A root configured in the WRONG
        case must therefore land in _ROOTS in its TRUE case -- otherwise the
        case-exact check rejects every legitimate read beneath it. Neither
        abspath nor keeping the raw string does this."""
        base = tempfile.mkdtemp()
        target = os.path.join(base, "MixedCase")
        os.mkdir(target)
        roots = file_tools._parse_roots(target.upper(), None)
        self.assertEqual(roots, [os.path.realpath(target)])
        # Non-vacuity: the configured spelling really was a different string.
        self.assertNotEqual(target.upper(), os.path.realpath(target))
        self._usable(roots, target)

    def test_a_file_under_each_root_passes_the_authoritative_check(self):
        upper, lower = self._case_sensitive_pair()
        roots = file_tools._parse_roots(os.pathsep.join([upper, lower]), None)
        with mock.patch.object(file_tools, "_ROOTS", roots):
            for root in (upper, lower):
                target = os.path.join(root, "note.txt")
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write("body")
                # No assertRaises: this must NOT raise for either root.
                file_tools._assert_contained_exact(os.path.realpath(target))

class TestRootsWiring(unittest.TestCase):
    r"""The module-level line that CONNECTS _parse_roots to the environment.

    Every precedence row above calls _parse_roots(a, b) DIRECTLY, and every
    public-tool row patches _ROOTS. Nothing exercises the one line between
    them -- and that line IS the env-precedence feature. Measured: swapping
    the two variable names there, or replacing the whole call with
    _parse_roots(None, None), leaves every other test green.

    This assertion is SOURCE-LEVEL. It proves the line is WRITTEN correctly;
    it cannot prove it RAN, and it cannot see a fake environment provider.
    TestRootsWiringBehavioral below closes both gaps by importing the module
    in a subprocess under a controlled environment and asserting the VALUE
    _ROOTS takes. Keep BOTH: the AST row pins the precedence ORDER at the call
    site in a form that names the impostor, and the behavioral rows prove the
    line executes. Neither subsumes the other.

    The module is imported once per process, and this suite never uses
    importlib.reload inside a patch context, but a behavioral test needs
    neither: a subprocess imports the module fresh with no reload and no
    patch.
    """

    def _module_assignment(self, name):
        tree = ast.parse(inspect.getsource(file_tools))
        found = [node for node in tree.body
                 if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == name
                         for target in node.targets)]
        self.assertEqual(
            len(found), 1,
            "%s must be assigned exactly once at module level, got %d"
            % (name, len(found)))
        return found[0].value

    @staticmethod
    def _environ_get_key(node):
        """The KEY of an os.environ.get("KEY") call, else None.

        Returns None rather than raising for any other shape, so the assertion
        below reports what it FOUND instead of dying on an AttributeError."""
        if not isinstance(node, ast.Call):
            return None
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "get"):
            return None
        owner = func.value
        if not (isinstance(owner, ast.Attribute) and owner.attr == "environ"):
            return None
        # The owner of .environ must be the NAME os. Without this check the
        # helper accepted ANY object with an .environ attribute, so a module
        # reading fake.environ.get("LOCAL_LLM_FILE_ROOTS") -- a stale snapshot,
        # a shim, a test double left in by accident -- satisfied every
        # assertion below while never consulting the process environment.
        if not (isinstance(owner.value, ast.Name) and owner.value.id == "os"):
            return None
        if not node.args or not isinstance(node.args[0], ast.Constant):
            return None
        return node.args[0].value

    def test_roots_is_wired_to_both_env_vars_in_precedence_order(self):
        call = self._module_assignment("_ROOTS")
        self.assertIsInstance(
            call, ast.Call, "_ROOTS must be assigned from a call")
        self.assertTrue(
            isinstance(call.func, ast.Name) and call.func.id == "_parse_roots",
            "_ROOTS must be assigned from _parse_roots(...)")
        self.assertEqual(
            len(call.args), 2,
            "_parse_roots takes the ROOTS var then the legacy var")
        # ORDER IS THE ASSERTION. Swapping these two names is the impostor
        # this row exists to exclude, and it is invisible to every other test
        # in the suite. Comparing the extracted KEYS as a LIST (not a set,
        # not two assertIns) is what makes the order load-bearing.
        self.assertEqual(
            [self._environ_get_key(arg) for arg in call.args],
            ["LOCAL_LLM_FILE_ROOTS", "LOCAL_LLM_FILE_ROOT"],
            "_ROOTS must be _parse_roots("
            "os.environ.get('LOCAL_LLM_FILE_ROOTS'), "
            "os.environ.get('LOCAL_LLM_FILE_ROOT')) -- in that order")

    def test_the_other_env_reads_are_still_wired(self):
        """MAX_FILE_BYTES and FILE_MODEL must CONSUME their env vars.

        An assertIn against the raw module text is not enough: a comment, a
        docstring, a dead read or an unused os.environ.get call satisfies it,
        so it cannot tell a live read from a mention of one. This row walks
        each module assignment and extracts the env key structurally -- the
        same mechanism the _ROOTS row above uses, and it inherits the
        os-ownership check.

        No subTest here, deliberately: a subTest failure can leave the parent
        reporting PASSED.
        """
        checked = 0
        for name, key in (("MAX_FILE_BYTES", "LOCAL_LLM_FILE_MAX_BYTES"),
                          ("FILE_MODEL", "LOCAL_LLM_FILE_MODEL")):
            value = self._module_assignment(name)
            # MAX_FILE_BYTES is int(os.environ.get(...)); FILE_MODEL is the
            # bare call. Unwrap ONE conversion layer so the row asserts the env
            # read rather than the coercion wrapped around it.
            if (isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id in ("int", "float", "str")):
                self.assertTrue(
                    value.args, "%s: conversion call takes no argument" % name)
                value = value.args[0]
            self.assertEqual(
                self._environ_get_key(value), key,
                "%s must be ASSIGNED FROM os.environ.get(%r) -- mentioning the "
                "name in a comment or a dead read no longer counts" % (name, key))
            checked += 1
        # Non-vacuity: emptying the tuple above must not leave this row green.
        self.assertEqual(checked, 2)


class TestRootsWiringBehavioral(unittest.TestCase):
    r"""The same wiring, exercised through a REAL import in a REAL process.

    TestRootsWiring proves the line is WRITTEN correctly. This class proves it
    RUNS: a fresh interpreter, a controlled environment, real directories, and
    an assertion on the VALUE _ROOTS actually takes.

    Why a subprocess. _parse_roots is deliberately environment-decoupled --
    env values arrive as arguments -- so the ONLY env-coupled code in this
    module is the single module-level _ROOTS assignment, and that line runs
    exactly once per process at import. This suite never reloads the module
    inside a patch context, and mocking _ROOTS cannot see the call site. A
    child interpreter sidesteps all of it: the import is genuinely the first
    one, and nothing is patched.
    """

    #: local_llm/file_tools.py -> local_llm -> repo root. Derived from the
    #: module so the child does not depend on how this suite was invoked;
    #: relying on an inherited PYTHONPATH would make the rows environment-
    #: dependent, which is the very thing they exist to test.
    REPO_ROOT = os.path.dirname(
        os.path.dirname(os.path.abspath(file_tools.__file__)))

    CHILD = (
        "import json, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from local_llm import file_tools\n"
        "sys.stdout.write(json.dumps(list(file_tools._ROOTS)))\n"
    )

    def _roots_under(self, **env):
        """Import file_tools in a fresh interpreter; return its _ROOTS."""
        child_env = dict(os.environ)
        # Drop BOTH names first. Inheriting either from the parent shell would
        # make every row below depend on how the suite was invoked.
        child_env.pop("LOCAL_LLM_FILE_ROOTS", None)
        child_env.pop("LOCAL_LLM_FILE_ROOT", None)
        child_env.update(env)
        result = subprocess.run(
            [sys.executable, "-c", self.CHILD, self.REPO_ROOT],
            capture_output=True, text=True, env=child_env, timeout=120)
        self.assertEqual(
            result.returncode, 0,
            "child import failed (rc=%d)\nSTDERR:\n%s"
            % (result.returncode, result.stderr))
        return [os.path.realpath(p) for p in json.loads(result.stdout)]

    def _tempdir(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        return os.path.realpath(holder.name)

    def test_the_ROOTS_var_actually_reaches_ROOTS(self):
        """Excludes _parse_roots(None, None) -- env ignored entirely."""
        first, second = self._tempdir(), self._tempdir()
        self.assertEqual(
            self._roots_under(
                LOCAL_LLM_FILE_ROOTS=os.pathsep.join([first, second])),
            [first, second])

    def test_the_LEGACY_var_actually_reaches_ROOTS(self):
        """Excludes wiring that passes only the ROOTS var and drops legacy."""
        only = self._tempdir()
        self.assertEqual(self._roots_under(LOCAL_LLM_FILE_ROOT=only), [only])

    def test_the_ROOTS_var_WINS_over_the_legacy_var(self):
        """THE discriminating row: excludes the SWAPPED-names impostor.

        The AST row excludes the swap by reading the source. This one excludes
        it by observing which directory the RUNNING module authorizes, so it
        survives any refactor that keeps the source shape and breaks the
        behavior -- an alias, a wrapper, a stale snapshot of os.environ.
        """
        winner, loser = self._tempdir(), self._tempdir()
        roots = self._roots_under(
            LOCAL_LLM_FILE_ROOTS=winner, LOCAL_LLM_FILE_ROOT=loser)
        self.assertEqual(roots, [winner])
        self.assertNotIn(loser, roots)

    def test_no_env_at_all_falls_back_to_the_shipped_defaults(self):
        """CONTROL, and it is honest about excluding no impostor by itself.

        _parse_roots(None, None) produces the defaults too, so this row does
        not discriminate against that impostor -- the three above do. Its job
        is to prove the harness reports DEFAULTS when the environment is clean,
        which is what makes the differing results above attributable to the env
        vars rather than to the subprocess plumbing.

        Compared against _parse_roots(None, None) computed HERE rather than
        against a literal list: the default roots (_DEFAULT_ROOTS) are empty
        in a public install, so the expected value is normally [], and
        computing it keeps the row correct whatever the defaults are and
        whichever default directories exist on the machine running it.
        """
        expected = [os.path.realpath(p)
                    for p in file_tools._parse_roots(None, None)]
        self.assertEqual(self._roots_under(), expected)


class TestIsWithin(unittest.TestCase):
    """The CHEAP PRE-OPEN FILTER. Case-insensitive and deliberately
    over-permissive -- it is not authorization. See TestIsWithinExact."""

    def test_bare_unc_share_root_contains_its_descendants(self):
        # commonpath treats a bare UNC share as RELATIVE (empty tail after
        # splitdrive), so mixing it with an absolute descendant raises
        # ValueError and would reject everything under a UNC root.
        self.assertTrue(file_tools._is_within(
            chr(92).join(["", "", "server", "share", "folder", "x.txt"]), chr(92).join(["", "", "server", "share"])))

    def test_unc_share_does_not_contain_a_different_share(self):
        self.assertFalse(file_tools._is_within(
            chr(92).join(["", "", "server", "other", "x.txt"]), chr(92).join(["", "", "server", "share"])))

    def test_drive_root_contains_everything_on_that_drive(self):
        self.assertTrue(file_tools._is_within(r"C:\Windows\notepad.exe", "C:\\"))

    def test_sibling_prefix_is_not_containment(self):
        self.assertFalse(file_tools._is_within(
            r"C:\Synthetic\WorkspaceEvil\x.txt",
            r"C:\Synthetic\Workspace"))

    def test_root_contains_itself(self):
        self.assertTrue(file_tools._is_within(
            r"C:\Synthetic\Workspace", r"C:\Synthetic\Workspace"))

    def test_cross_drive_is_not_containment(self):
        self.assertFalse(file_tools._is_within(
            r"D:\elsewhere\x.txt", r"C:\Synthetic\Workspace"))

    def test_case_insensitivity_is_INTENTIONAL_and_NON_AUTHORITATIVE(self):
        # This permissiveness is deliberate and is NOT a bug: _is_within is the
        # cheap pre-open filter, and it may admit a path the authoritative
        # case-exact check will later reject. The companion assertion is what
        # keeps that from being a silent contradiction.
        self.assertTrue(file_tools._is_within(
            r"C:\Synthetic\Workspace\x.txt",
            r"c:\synthetic\workspace"))
        self.assertFalse(file_tools._is_within_exact(
            r"C:\Synthetic\Workspace\x.txt",
            r"c:\synthetic\workspace"))


class TestIsWithinExact(unittest.TestCase):
    r"""The AUTHORITATIVE rule. Case-SENSITIVE. Pure string logic -- no
    filesystem access, so every case here runs on any machine."""

    def test_case_differing_sibling_is_NOT_containment(self):
        # On a case-sensitive directory C:\Case\Root and C:\Case\root are two
        # different directories. The commonpath-based filter calls them one
        # (measured live: it returned True while the OS proved secret.txt was
        # not under Root).
        self.assertFalse(file_tools._is_within_exact(
            r"C:\Case\root\secret.txt", r"C:\Case\Root"))

    def test_true_case_descendant_is_containment(self):
        self.assertTrue(file_tools._is_within_exact(
            r"C:\Case\Root\benign.txt", r"C:\Case\Root"))

    def test_sibling_prefix_is_not_containment(self):
        self.assertFalse(file_tools._is_within_exact(
            r"C:\X\SyntheticWorkspaceEvil\x.txt", r"C:\X\SyntheticWorkspace"))

    def test_root_contains_itself(self):
        self.assertTrue(file_tools._is_within_exact(
            r"C:\Case\Root", r"C:\Case\Root"))

    def test_drive_root_contains_everything_on_that_drive(self):
        # normpath("C:\\") is "C:\\"; rstrip leaves "C:", so the prefix tested
        # is "C:\\" -- exactly right, with no double separator.
        self.assertTrue(file_tools._is_within_exact(
            r"C:\Windows\notepad.exe", "C:\\"))

    def test_unc_same_share_is_containment(self):
        self.assertTrue(file_tools._is_within_exact(
            chr(92).join(["", "", "server", "share", "folder", "x.txt"]), chr(92).join(["", "", "server", "share"])))

    def test_unc_different_share_is_not_containment(self):
        self.assertFalse(file_tools._is_within_exact(
            chr(92).join(["", "", "server", "other", "x.txt"]), chr(92).join(["", "", "server", "share"])))

    def test_unc_sibling_share_prefix_is_not_containment(self):
        self.assertFalse(file_tools._is_within_exact(
            chr(92).join(["", "", "server", "shareEvil", "x.txt"]), chr(92).join(["", "", "server", "share"])))

    def test_trailing_separator_on_the_candidate_is_still_the_root(self):
        self.assertTrue(file_tools._is_within_exact(
            chr(92).join(["C:", "Case", "Root", ""]), chr(92).join(["C:", "Case", "Root"])))

    def test_dot_segment_traversal_is_rejected(self):
        self.assertFalse(file_tools._is_within_exact(
            r"C:\a\b\..\..\etc\x.txt", r"C:\a\b"))

    def test_relative_candidate_fails_closed(self):
        self.assertFalse(file_tools._is_within_exact(
            r"relative\x.txt", r"C:\a\b"))

    def test_degenerate_empty_root_is_rejected_not_treated_as_a_prefix(self):
        # MEASURED HAZARD: "\\".rstrip("\\") is "", and "" + "\\" prefixes
        # every UNC path, so without an explicit guard a degenerate root would
        # silently admit the entire network.
        self.assertFalse(file_tools._is_within_exact(
            chr(92).join(["", "", "server", "share", "x.txt"]), chr(92).join(["", "", ""])))
        self.assertFalse(file_tools._is_within_exact(
            r"C:\Windows\x.txt", "\\"))


class TestCheapFilterIsNeverStricterThanTheAuthoritativeCheck(unittest.TestCase):
    """ORDERING INVARIANT. The pre-open filter exists to reject the obvious
    cases cheaply. It is sound only while it is at least as permissive as the
    authoritative check -- if it ever became stricter, it would silently deny
    legitimate reads that the real rule would allow, with no security gain."""

    PAIRS = (
        (r"C:\Case\Root\benign.txt", r"C:\Case\Root"),
        (r"C:\Case\Root", r"C:\Case\Root"),
        (r"C:\Windows\notepad.exe", "C:\\"),
        (chr(92).join(["", "", "server", "share", "folder", "x.txt"]), chr(92).join(["", "", "server", "share"])),
        (r"C:\Synthetic\Workspace\a\b.txt",
         r"C:\Synthetic\Workspace"),
    )

    def test_exact_true_implies_filter_true(self):
        checked = 0
        for candidate, root in self.PAIRS:
            with self.subTest(candidate=candidate, root=root):
                if file_tools._is_within_exact(candidate, root):
                    checked += 1
                    self.assertTrue(
                        file_tools._is_within(candidate, root),
                        "cheap filter rejected a path the authoritative check "
                        "accepts: %s in %s" % (candidate, root))
        # NON-VACUITY GUARD. Every assertion above sits behind an `if`, so a
        # regression that made _is_within_exact always False would take this
        # whole class green having verified nothing.
        self.assertEqual(checked, len(self.PAIRS))


class TestAssertContained(unittest.TestCase):
    def _roots(self, *roots):
        return mock.patch.object(
            file_tools, "_ROOTS", [os.path.realpath(root) for root in roots])

    def test_sibling_prefix_escape_is_rejected(self):
        parent = tempfile.mkdtemp()
        root = os.path.join(parent, "SyntheticWorkspace")
        evil = os.path.join(parent, "SyntheticWorkspaceEvil")
        os.mkdir(root)
        os.mkdir(evil)
        target = os.path.join(evil, "x.txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("hi")
        with self._roots(root):
            with self.assertRaisesRegex(ValueError, "outside the allowed root"):
                file_tools._assert_contained(os.path.realpath(target))

    def test_second_root_is_reachable(self):
        first = tempfile.mkdtemp()
        second = tempfile.mkdtemp()
        target = os.path.join(second, "note.md")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("body")
        with self._roots(first, second):
            file_tools._assert_contained(os.path.realpath(target))

    def test_empty_roots_fails_closed(self):
        with mock.patch.object(file_tools, "_ROOTS", []):
            with self.assertRaisesRegex(ValueError, "no usable allowlist roots"):
                file_tools._assert_contained(r"C:\Synthetic\Workspace\x.txt")

    def test_explicit_configured_root_denies_an_outside_path(self):
        with tempfile.TemporaryDirectory() as root, \
                tempfile.TemporaryDirectory() as outside:
            with self._roots(root):
                self.assertIsNone(file_tools._assert_contained(
                    os.path.join(root, "synthetic-inside.txt")))
                with self.assertRaises(ValueError):
                    file_tools._assert_contained(
                        os.path.join(outside, "synthetic-outside.txt"))


class TestAssertContainedExact(unittest.TestCase):
    def test_case_differing_path_is_rejected_with_a_DISTINGUISHABLE_message(self):
        # The marker is what lets a later test prove WHICH check fired. The
        # cheap filter accepts this path; only this check rejects it.
        with mock.patch.object(file_tools, "_ROOTS", [r"C:\Case\Root"]):
            with self.assertRaisesRegex(ValueError, "case-exact handle check"):
                file_tools._assert_contained_exact(r"C:\Case\root\secret.txt")

    def test_true_case_descendant_is_accepted(self):
        with mock.patch.object(file_tools, "_ROOTS", [r"C:\Case\Root"]):
            file_tools._assert_contained_exact(r"C:\Case\Root\benign.txt")

    def test_empty_roots_fails_closed(self):
        with mock.patch.object(file_tools, "_ROOTS", []):
            with self.assertRaisesRegex(ValueError, "no usable allowlist roots"):
                file_tools._assert_contained_exact(r"C:\Case\Root\x.txt")

    def test_a_DIFFERENT_DRIVE_is_rejected_by_the_AUTHORITATIVE_check(self):
        r"""The only other C:-root / D:-candidate row exercises the CHEAP
        filter. _is_within_exact backs the live authorization boundary
        (_assert_contained_exact on the opened handle's final path), so a
        drive-stripping regression there would pass every other row in this
        class -- the class tests case handling exhaustively and volume
        handling not at all.

        Excludes: an implementation that compares os.path.splitdrive(p)[1]
        rather than p, or that normalises the drive away before comparing.
        """
        with mock.patch.object(file_tools, "_ROOTS", [r"C:\Case\Root"]):
            with self.assertRaises(ValueError):
                file_tools._assert_contained_exact(r"D:\Case\Root\secret.txt")
            # NON-VACUITY: the identical tail under the real drive must be
            # ACCEPTED, so the rejection above is attributable to the volume
            # and not to the path shape or to a missing directory.
            file_tools._assert_contained_exact(r"C:\Case\Root\benign.txt")

    def test_the_two_checks_disagree_on_case_which_is_the_whole_point(self):
        # Pins the two-tier design itself. If someone later makes the cheap
        # filter case-exact, or the authoritative check case-insensitive, this
        # fails and forces the change to be deliberate.
        with mock.patch.object(file_tools, "_ROOTS", [r"C:\Case\Root"]):
            file_tools._assert_contained(r"C:\Case\root\secret.txt")   # accepted
            with self.assertRaises(ValueError):
                file_tools._assert_contained_exact(r"C:\Case\root\secret.txt")

    def test_every_configured_root_is_reachable_by_the_authoritative_check(self):
        temp_roots = [tempfile.TemporaryDirectory() for _ in range(3)]
        for temp_root in temp_roots:
            self.addCleanup(temp_root.cleanup)
        roots = [os.path.realpath(item.name) for item in temp_roots]
        checked = []
        with mock.patch.object(file_tools, "_ROOTS", roots):
            for root in roots:
                file_tools._assert_contained_exact(
                    os.path.join(root, "synthetic-probe.txt"))
                checked.append(root)
        self.assertEqual(checked, roots)
        self.assertEqual(len(roots), 3)



class TestEveryRootReachableFromPublicTools(unittest.TestCase):
    """Public tools reach every configured root and fail closed with none.

    Synthetic temporary roots keep coverage independent of machine state.
    """


    def setUp(self):
        self._root_dirs = [tempfile.TemporaryDirectory() for _ in range(3)]
        for root_dir in self._root_dirs:
            self.addCleanup(root_dir.cleanup)
        self.roots = [os.path.realpath(root_dir.name)
                      for root_dir in self._root_dirs]
        patcher = mock.patch.object(file_tools, "_ROOTS", self.roots)
        patcher.start()
        self.addCleanup(patcher.stop)


    def _write(self, root, name="transcript.md"):
        target = os.path.join(root, name)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("dataset had 42 entries.\n")
        return target

    @mock.patch.object(ollama_client.requests, "post")
    def test_summarize_file_reads_from_EVERY_root(self, mock_post):
        mock_post.return_value = _make_response("a fine summary")
        checked = []
        for root in self.roots:
            # No subTest: a subtest failure can leave the parent reporting
            # PASSED.
            note = self._write(root)
            out = file_tools.summarize_file(note, max_words=20)
            self.assertEqual(out["summary"], "a fine summary")
            self.assertEqual(out["path"], os.path.realpath(note))
            checked.append(root)
        # NON-VACUITY: a loop that never entered, or a root list that
        # silently shrank, must not pass this row.
        self.assertEqual(checked, self.roots)

    @mock.patch.object(ollama_client.requests, "post")
    def test_extract_json_file_reads_from_EVERY_root(self, mock_post):
        mock_post.return_value = _make_response('{"total": "42"}')
        checked = []
        for root in self.roots:
            note = self._write(root)
            out = file_tools.extract_json_file(note, {"total": "string"})
            self.assertEqual(out["fields"]["total"], "42")
            self.assertEqual(out["unverified_fields"], [])
            checked.append(root)
        self.assertEqual(checked, self.roots)

    @mock.patch.object(ollama_client.requests, "post")
    def test_outside_every_root_is_denied_with_no_model_call(self, mock_post):
        outside = os.path.join(tempfile.mkdtemp(), "secret.txt")
        with open(outside, "w", encoding="utf-8") as handle:
            handle.write("SENSITIVE")
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools.summarize_file(outside)
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools.extract_json_file(outside, {"a": "string"})
        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_zero_roots_refuses_BOTH_public_tools_with_no_model_call(
            self, mock_post):
        r"""Drives BOTH public tools with _ROOTS = []. Asserting the
        zero-root guarantee only on _assert_contained DIRECTLY is not enough:
        a read path that skips containment when the list is empty -- `if
        _ROOTS and not any(...)`, a two-word difference -- would pass every
        predicate-level row while reading ARBITRARY files under blank or
        wholly-invalid configuration. That is exactly the state a mistyped
        LOCAL_LLM_FILE_ROOTS produces, so it has to be pinned end-to-end and
        not just at the predicate.

        The no-model-call assertion is load-bearing: without it, a tool that
        refused only AFTER shipping the file's bytes to Ollama would pass.
        """
        inside = self._write(self.roots[0], "readable.md")
        with mock.patch.object(file_tools, "_ROOTS", []):
            with self.assertRaisesRegex(ValueError, "no usable allowlist roots"):
                file_tools.summarize_file(inside)
            with self.assertRaisesRegex(ValueError, "no usable allowlist roots"):
                file_tools.extract_json_file(inside, {"a": "string"})
        mock_post.assert_not_called()
        # CONTROL: the same file IS readable once roots are configured, so the
        # refusals above are the empty root list and not a missing file.
        mock_post.return_value = _make_response("a fine summary")
        self.assertEqual(
            file_tools.summarize_file(inside, max_words=20)["summary"],
            "a fine summary")


class TestLinkEscapeThroughResolveAllowed(unittest.TestCase):
    r"""A directory link that lives INSIDE a root and points OUTSIDE it must
    not grant a read outside the root. (The class name refers to
    _resolve_allowed, the read path's former authorization helper; the rows
    now drive _open_contained and the public tools.)

    What this excludes, as the two ways a containment check can go wrong:
      (a) os.path.abspath in place of os.path.realpath -- abspath normalizes
          the STRING and never resolves the link, so the requested name looks
          contained while the read lands outside;
      (b) authorizing the REQUESTED path and then opening the RESOLVED one --
          containment checked against a different string than the one read.
    Both leave every row that uses only ordinary files green.

    A junction is the vehicle, not a symlink: junctions need no privilege on
    Windows, whereas a directory symlink needs Developer Mode or elevation
    (TestSymlinkEscapes covers symlinks). realpath resolves both identically,
    so the junction excludes the same two impostors -- and it does so WITHOUT
    a conditional skip, which this suite does not permit in a security row:
    the suite is meant to run with zero skips.
    """

    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())
        self.outside = os.path.realpath(tempfile.mkdtemp())
        with open(os.path.join(self.outside, "secret.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("SENSITIVE")
        patcher = mock.patch.object(file_tools, "_ROOTS", [self.root])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _junction(self, link, target):
        # Same shape as TestParseRootsKeepsCaseDistinctRoots._junction: a
        # required security row FAILS with the real output, never skips green.
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", link, target], capture_output=True)
        self.assertEqual(
            result.returncode, 0,
            (result.stdout + result.stderr).decode("mbcs", "replace"))

    def _escaping_path(self, name):
        link_dir = os.path.join(self.root, name)
        self._junction(link_dir, self.outside)
        via_link = os.path.join(link_dir, "secret.txt")
        # PRECONDITION, not decoration: prove the link genuinely reaches the
        # outside file. Without it this row could pass because the escape was
        # never constructed, which is the classic way a link test rots green.
        with open(via_link, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "SENSITIVE")
        return via_link

    def test_junction_inside_a_root_cannot_reach_outside_it(self):
        # _open_contained is the read path's authorization boundary (it
        # replaced the former _resolve_allowed helper), so this row targets
        # it directly; the next row covers the public tools.
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools._open_contained(self._escaping_path("jn"))

    @mock.patch.object(ollama_client.requests, "post")
    def test_public_tools_refuse_the_junction_escape_with_no_model_call(
            self, mock_post):
        via_link = self._escaping_path("jn2")
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools.summarize_file(via_link)
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools.extract_json_file(via_link, {"a": "string"})
        mock_post.assert_not_called()


class TestOpenContained(FileToolsBase):
    def test_exact_cap_is_accepted_and_cap_plus_one_is_rejected(self):
        ok = self._write("ok.txt", "x" * 100)
        big = self._write("big.txt", "x" * 101)
        with mock.patch.object(file_tools, "MAX_FILE_BYTES", 100):
            final, handle, size = file_tools._open_contained(ok)
            handle.close()
            self.assertEqual(size, 100)
            self.assertEqual(final, os.path.realpath(ok))
            with self.assertRaisesRegex(ValueError, "file too large"):
                file_tools._open_contained(big)

    def test_read_bounded_rejects_a_file_that_grew_past_the_cap(self):
        path = self._write("grow.txt", "x" * 50)
        handle = open(path, "rb")
        try:
            with open(path, "ab") as growing:
                growing.write(b"y" * 200)
            with self.assertRaisesRegex(ValueError, "grew past the"):
                file_tools._read_bounded(handle, 100)
        finally:
            handle.close()

    def test_directory_is_rejected_as_not_a_file(self):
        with self.assertRaisesRegex(ValueError, "not a file"):
            file_tools._open_contained(self.tmpdir)

    # ------------------------------------- authorizing the opened handle
    def test_open_contained_authorizes_the_HANDLE_path_not_a_cached_name(self):
        r"""Proves that the value _handle_final_path RETURNS is the value
        _assert_contained_exact RECEIVES.

        The impostor: call _handle_final_path (so it LOOKS wired) but
        authorize a cached os.path.realpath(handle.name) taken right after
        open. That passes even the two-swap row below -- at that instant the
        name still resolves outside, so it rejects for the right reason by
        accident -- while remaining exactly as raceable as a purely
        name-based check.

        No scenario can settle this, because the impostor and the real
        implementation agree on every scenario where the name happens to be
        right. Assert the WIRING: make the two values diverge and check which
        one crosses the boundary."""
        target = self._write("doc.txt", "body")
        sentinel = os.path.join(self.tmpdir, "SENTINEL-FROM-THE-HANDLE.txt")
        seen = []
        with mock.patch.object(file_tools, "_handle_final_path",
                               lambda handle: sentinel):
            with mock.patch.object(file_tools, "_assert_contained_exact",
                                   seen.append):
                final, handle, _size = file_tools._open_contained(target)
                handle.close()
        self.assertEqual(
            seen, [sentinel],
            "the authoritative check did not receive _handle_final_path's "
            "return value")
        # The RETURNED path is handle-derived too, so no later consumer can
        # re-introduce the requested name after authorization.
        self.assertEqual(final, sentinel)

    def test_a_non_regular_OPENED_object_is_rejected_after_open(self):
        r"""test_directory_is_rejected_as_not_a_file fails at the PRE-open
        os.stat, so deleting the post-open stat.S_ISREG(post.st_mode) guard
        would leave it green. The post-open check is the one that matters:
        the pre-open answer describes a NAME, and the handle check exists
        because a name is not the object.

        fstat is doctored so IDENTITY still matches -- otherwise the row could
        pass by tripping the identity check instead, proving nothing about the
        mode guard."""
        target = self._write("doc.txt", "body")
        real_fstat = os.fstat

        def not_regular(fd):
            fields = list(real_fstat(fd))
            fields[0] = (fields[0] & ~0o170000) | 0o010000    # S_IFIFO
            return os.stat_result(fields)

        with mock.patch.object(os, "fstat", not_regular):
            with self.assertRaisesRegex(ValueError, "not a regular file|not a file"):
                file_tools._open_contained(target)

    def test_static_junction_escaping_a_root_is_rejected(self):
        outside = tempfile.mkdtemp()
        with open(os.path.join(outside, "secret.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("s")
        link = os.path.join(self.tmpdir, "link")
        self._mklink_j(link, outside)
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools._open_contained(os.path.join(link, "secret.txt"))

    def test_parent_component_swapped_for_a_junction_after_authorization(self):
        r"""THE PLAIN TOCTOU RACE. Authorize C:\root\sub\doc.txt while `sub` is
        a real directory, then replace `sub` with a junction to an outside
        directory before stat/open run. Both follow the NEW junction to the
        SAME outside file, so the fstat identity tuple MATCHES -- an
        identity-only check passes here.

        NOTE what this does NOT prove. A name-based implementation
        (os.path.realpath(handle.name)) also rejects here, because the junction
        is still in place when the final path is resolved -- measured, both
        return "outside". This row covers the plain race; it does NOT
        discriminate handle binding. See
        test_handle_authorization_survives_the_directory_being_restored.
        """
        outside = tempfile.mkdtemp()
        with open(os.path.join(outside, "doc.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("SENSITIVE-OUTSIDE")
        sub = os.path.join(self.tmpdir, "sub")
        os.mkdir(sub)
        target = os.path.join(sub, "doc.txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("benign-inside")

        real_assert = file_tools._assert_contained
        state = {"swapped": False}

        def swapping_assert(real_path):
            # Authorize first (so the pre-open check passes), THEN swap.
            real_assert(real_path)
            if not state["swapped"]:
                state["swapped"] = True
                os.remove(target)
                os.rmdir(sub)
                self._mklink_j(sub, outside)

        with mock.patch.object(file_tools, "_assert_contained", swapping_assert):
            with self.assertRaisesRegex(ValueError, "outside the allowed root"):
                file_tools._open_contained(target)
        self.assertTrue(state["swapped"], "the race never fired -- test is vacuous")

    def test_handle_authorization_survives_the_directory_being_restored(self):
        r"""THE DISCRIMINATING ROW. Two swaps, not one.

        Swap 1 (after authorization): replace `sub` with a junction to an
        outside directory, so stat/open/fstat all bind to the OUTSIDE file.
        Swap 2 (after fstat, before the final-path check): put the real `sub`
        directory and its inside file BACK.

        The open handle still refers to the outside file. But the NAME
        C:\root\sub\doc.txt now resolves to a legitimate inside file again, so:

          - a name-based impostor (os.path.realpath(handle.name)) reports
            INSIDE and AUTHORIZES -- measured, and the handle then returns
            b'SENSITIVE-OUTSIDE';
          - GetFinalPathNameByHandleW reports the outside path and REJECTS.

        The single-swap row above cannot tell these apart (measured: both
        reject). This one can, which is what makes the handle-binding claim
        mechanical rather than described.

        The swap-2 hook wraps _handle_final_path because that is the only seam
        between os.fstat and the authoritative check. The wrapper still
        delegates to the real implementation, so the real code path runs.
        """
        outside = tempfile.mkdtemp()
        with open(os.path.join(outside, "doc.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("SENSITIVE-OUTSIDE")
        sub = os.path.join(self.tmpdir, "sub")
        os.mkdir(sub)
        target = os.path.join(sub, "doc.txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("benign-inside")

        real_assert = file_tools._assert_contained
        real_final = file_tools._handle_final_path
        state = {"swapped": False, "restored": False}

        def swapping_assert(real_path):
            real_assert(real_path)
            if not state["swapped"]:
                state["swapped"] = True
                os.remove(target)
                os.rmdir(sub)
                self._mklink_j(sub, outside)

        def restoring_final_path(handle):
            if not state["restored"]:
                state["restored"] = True
                os.rmdir(sub)                 # removes the junction only
                os.mkdir(sub)
                with open(target, "w", encoding="utf-8") as inside:
                    inside.write("benign-inside")
            return real_final(handle)

        with mock.patch.object(file_tools, "_assert_contained", swapping_assert):
            with mock.patch.object(
                    file_tools, "_handle_final_path", restoring_final_path):
                with self.assertRaisesRegex(ValueError, "case-exact handle check"):
                    file_tools._open_contained(target)

        self.assertTrue(state["swapped"],
                        "the first swap never fired -- test is vacuous")
        self.assertTrue(state["restored"],
                        "the second swap never fired -- test is vacuous")
        # The name really is legitimate again: without this, the row could pass
        # for the wrong reason (e.g. the junction was never removed).
        self.assertTrue(file_tools._is_within_exact(
            os.path.realpath(target), os.path.realpath(self.tmpdir)))

    def test_handle_final_path_matches_realpath_for_an_ordinary_file(self):
        # No false positives: an ordinary file's handle must resolve back to
        # its own realpath, or every legitimate read would start failing.
        # On systems where 8.3 short-name generation is disabled, the two
        # paths are byte-identical, so assert exact equality -- a normcase
        # comparison here would hide a real divergence.
        #
        # NON-DISCRIMINATING by construction: a name-based impostor also passes
        # this row. It is a false-positive guard, not a handle-binding proof.
        path = self._write("plain.txt", "hello")
        final, handle, _size = file_tools._open_contained(path)
        try:
            self.assertEqual(file_tools._handle_final_path(handle), final)
            self.assertEqual(final, os.path.realpath(path))
        finally:
            handle.close()


class TestHandleFinalPathIsBoundToTheHandle(FileToolsBase):
    r"""THE HANDLE-BINDING PROOF. Calls _handle_final_path DIRECTLY, so there is
    no injection point an implementation can dodge by resolving earlier.

    Why the two-swap row above is NOT sufficient on its own: it injects its
    second swap by patching _handle_final_path, so it can only observe the
    window that opens once _handle_final_path is entered. An implementation
    that resolved the requested NAME any time between open() and that call sits
    behind the injection point. Measured: an impostor resolving
    os.path.realpath(handle.name) immediately after open() reads the OUTSIDE
    path (the junction is still in place then), rejects, and therefore PASSES
    the two-swap row while being entirely name-based.

    This row removes the timing question. The namespace is changed BEFORE the
    call, and _handle_final_path receives only a handle -- it has nowhere to
    cache an earlier answer. Any name-derived result is INSIDE the root; only
    an answer taken from the handle is OUTSIDE.
    """

    def test_final_path_follows_the_handle_after_its_name_is_repointed(self):
        outside = tempfile.mkdtemp()
        with open(os.path.join(outside, "doc.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("SENSITIVE-OUTSIDE")

        # `sub` is a junction from the start, so the handle binds to the
        # OUTSIDE file...
        sub = os.path.join(self.tmpdir, "sub")
        self._mklink_j(sub, outside)
        opened = open(os.path.join(sub, "doc.txt"), "rb")
        try:
            # ...then the junction is replaced by a real directory holding a
            # real file, so the NAME now resolves somewhere legitimate.
            os.rmdir(sub)               # removes the junction only
            os.mkdir(sub)
            with open(os.path.join(sub, "doc.txt"), "w",
                      encoding="utf-8") as inside:
                inside.write("benign-inside")

            name_based = os.path.realpath(opened.name)
            handle_based = file_tools._handle_final_path(opened)

            # The premise: the two answers really do diverge here. Without
            # this, the row could pass vacuously on a system where the swap
            # silently failed.
            self.assertNotEqual(handle_based, name_based)
            self.assertEqual(handle_based,
                             os.path.realpath(os.path.join(outside, "doc.txt")))
            # A name-derived answer would AUTHORIZE; the handle's does not.
            self.assertTrue(file_tools._is_within_exact(
                name_based, os.path.realpath(self.tmpdir)))
            self.assertFalse(file_tools._is_within_exact(
                handle_based, os.path.realpath(self.tmpdir)))
            # And the bytes really are the outside file's, so authorizing on
            # the name would have been a live read-anything bypass.
            self.assertEqual(opened.read(), b"SENSITIVE-OUTSIDE")
        finally:
            opened.close()


class TestIdentityMismatchIsReachable(FileToolsBase):
    r"""_open_contained compares (st_dev, st_ino) before and after open().
    EVERY TOCTOU row in this file fires its swap BEFORE os.stat -- that is
    the documented point of those rows -- so pre and post always agree and
    not one of them can fail if the comparison is deleted. Measured:
    deleting it leaves every other test green.

    Reaching the branch needs the pre-open stat to describe a DIFFERENT object
    than the handle. Racing the filesystem for that is unreliable, so this
    patches os.stat to return a doctored st_ino for exactly the path under
    test and DELEGATES every other call to the real implementation -- the temp
    machinery and os.path.realpath must keep working. The comparison is on the
    raw string os.stat is called with, never on a re-resolved path, so the
    patch cannot recurse into itself.
    """

    def test_identity_mismatch_between_stat_and_open_is_rejected(self):
        root = tempfile.mkdtemp()
        target = os.path.join(root, "note.txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("body")
        real = os.path.realpath(target)
        real_stat = os.stat
        fired = []

        def _doctored(path, *args, **kwargs):
            result = real_stat(path, *args, **kwargs)
            if str(path) in (target, real):
                fired.append(str(path))
                # Identical in every respect EXCEPT identity, so this row
                # cannot pass by tripping the regular-file, nlink or size
                # checks instead of the one it is aimed at. tuple(result) is
                # the 10-tuple (st_mode, st_ino, st_dev, st_nlink, ...), so
                # slicing from index 3 preserves everything downstream.
                return os.stat_result(
                    (result.st_mode, result.st_ino + 1, result.st_dev)
                    + tuple(result)[3:])
            return result

        with mock.patch.object(file_tools, "_ROOTS", [os.path.realpath(root)]):
            with mock.patch.object(file_tools.os, "stat", _doctored):
                with self.assertRaisesRegex(ValueError, "identity mismatch"):
                    file_tools._open_contained(target)
        # NON-VACUITY: prove the patch actually ran. Without it this row would
        # still pass against an implementation that stopped calling os.stat.
        self.assertTrue(fired, "the doctored os.stat was never called")


class TestHandleFinalPathFailsClosed(unittest.TestCase):
    r"""Covers three branches of _handle_final_path that no end-to-end read
    reaches: length == 0 (the API failed), length >= _FINAL_PATH_BUFFER (the
    path is too long to validate, so fail closed rather than validate a
    truncated one), and the \\?\UNC\ prefix restoration.

    The UNC branch matters most: stripping only the 4-character prefix from
    a UNC result yields UNC\server\share\..., an invalid path that would
    reject every read under a UNC root.

    These are unit rows over the prefix logic and the two error returns, not
    end-to-end reads: the point is the branch, and the branches are cheap.
    """

    class _FakeHandle:
        """_handle_final_path only ever calls handle.fileno()."""

        def fileno(self):
            return 0

    def setUp(self):
        # get_osfhandle would reject the fake descriptor; the value is unused
        # because _GetFinalPathNameByHandleW is patched too.
        patcher = mock.patch.object(
            file_tools.msvcrt, "get_osfhandle", lambda _fd: 0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _returning(self, value, length=None):
        r"""Patch the ctypes entry point to write `value` into the caller's
        buffer and report `length` (defaulting to len(value), which is what
        the real API does on success)."""
        def _fake(_handle, buffer, _size, _flags):
            buffer.value = value
            return len(value) if length is None else length
        return mock.patch.object(
            file_tools, "_GetFinalPathNameByHandleW", _fake)

    def test_a_dos_device_prefix_is_stripped(self):
        with self._returning(r"\\?\C:\x\y.txt"):
            self.assertEqual(
                file_tools._handle_final_path(self._FakeHandle()),
                r"C:\x\y.txt")

    def test_a_unc_result_is_restored_to_its_server_share_shape(self):
        # Without this restoration every read under a UNC root would fail.
        with self._returning(r"\\?\UNC\server\share\x.txt"):
            self.assertEqual(
                file_tools._handle_final_path(self._FakeHandle()),
                chr(92).join(["", "", "server", "share", "x.txt"]))

    def test_a_bare_path_is_returned_unchanged(self):
        with self._returning(r"C:\x\y.txt"):
            self.assertEqual(
                file_tools._handle_final_path(self._FakeHandle()),
                r"C:\x\y.txt")

    def test_a_zero_length_return_fails_closed(self):
        with self._returning("", length=0):
            with self.assertRaisesRegex(ValueError, "could not resolve"):
                file_tools._handle_final_path(self._FakeHandle())

    def test_a_length_at_or_past_the_buffer_fails_closed(self):
        # The API returns the REQUIRED size and writes nothing. Validating a
        # truncated path would be worse than refusing outright.
        with self._returning("", length=file_tools._FINAL_PATH_BUFFER):
            with self.assertRaisesRegex(ValueError, "too long to validate"):
                file_tools._handle_final_path(self._FakeHandle())


class TestHandleResolutionFailureIsFailClosedOnTheReadPath(FileToolsBase):
    r"""Every row in the class above calls _handle_final_path DIRECTLY. This
    class proves the READ PATH fails closed when handle resolution fails.

    The impostor: catch the helper's error and fall back to the requested
    realpath. It passes all four direct rows -- they never go through
    _open_contained -- and it reopens the containment boundary at precisely
    the moment the OS has stopped being able to say what was opened, which is
    the worst possible moment to start trusting a name.

    Asserts three things, because a refusal that leaks a handle or reaches the
    model is not fail-closed: both public tools raise, no model call happens,
    and every handle opened during the attempt is closed.
    """

    @mock.patch.object(ollama_client.requests, "post")
    def test_both_public_tools_refuse_make_no_model_call_and_leak_no_handle(
            self, mock_post):
        target = self._write("doc.txt", "body")
        opened = []
        real_open = builtins.open

        def tracking_open(*args, **kwargs):
            handle = real_open(*args, **kwargs)
            opened.append(handle)
            return handle

        def resolution_fails(handle):
            raise OSError("GetFinalPathNameByHandleW failed")

        with mock.patch.object(file_tools, "_handle_final_path",
                               resolution_fails):
            with mock.patch.object(builtins, "open", tracking_open):
                with self.assertRaises(ValueError):
                    file_tools.summarize_file(target)
                with self.assertRaises(ValueError):
                    file_tools.extract_json_file(target, {"a": "string"})
        mock_post.assert_not_called()
        # NON-VACUITY: if nothing was opened the row proves nothing about
        # handle lifetime.
        self.assertTrue(opened, "no handle was opened -- the row is vacuous")
        for handle in opened:
            self.assertTrue(handle.closed, "an opened handle leaked")


class TestEveryOsCallInOpenContainedFailsInTheDeclaredType(FileToolsBase):
    r"""Every OS call in `_open_contained` must fail as ValueError, not only
    the `_handle_final_path` ctypes resolution.

    The bug shape: converting OSError to ValueError for exactly ONE OS call
    and leaving its NEIGHBOURS unconverted. If `handle = open(real, "rb")`
    sits between the guarded `os.stat` and the `try:` whose handler is
    `except BaseException: handle.close(); raise`, it is inside NO handler at
    all; and that BaseException handler re-raises the ORIGINAL type, so an
    `os.fstat` failure would escape as OSError too. Yet `_open_contained`'s
    own comment states that "every public entry point in this module
    promises ValueError", and `server.py` registers both entry points as MCP
    tools with NO translation layer -- so the wrong type would reach the
    tool boundary unmodified.

    This is not hypothetical. Reading a live worker log is this module's
    stated primary use case (see the identity-check comment, which accepts
    growth precisely so live logs work), and a Windows sharing violation on an
    actively-written log is exactly the routine condition these two calls hit.

    THE IMPOSTOR THIS EXCLUDES: guarding only the ctypes call. It passes
    TestHandleResolutionFailureIsFailClosedOnTheReadPath above and fails both
    rows here. The class above is necessary and NOT sufficient -- a guard on
    one call site of a shared unsafe primitive never generalises to its
    siblings.
    """

    def _deny(self, target, exc):
        """Patch builtins.open so ONLY `target` raises; everything else (temp
        files, fixtures, the model stub) opens normally."""
        real_open = builtins.open
        attempted = []

        def denying_open(file, *args, **kwargs):
            if os.path.realpath(str(file)) == os.path.realpath(target):
                attempted.append(file)
                raise exc
            return real_open(file, *args, **kwargs)

        return denying_open, attempted

    @mock.patch.object(ollama_client.requests, "post")
    def test_a_sharing_violation_on_open_raises_valueerror(self, mock_post):
        target = self._write("locked.txt", "body")
        denying_open, attempted = self._deny(
            target,
            PermissionError(13, "The process cannot access the file because "
                                "it is being used by another process"))

        with mock.patch.object(builtins, "open", denying_open):
            with self.assertRaises(ValueError):
                file_tools.summarize_file(target)
            with self.assertRaises(ValueError):
                file_tools.extract_json_file(target, {"a": "string"})
        mock_post.assert_not_called()
        # NON-VACUITY: assertRaises(ValueError) is satisfied by ANY earlier
        # refusal. Unless open was actually reached -- twice, once per tool --
        # this row proves nothing about the open call itself.
        self.assertEqual(
            len(attempted), 2,
            "open() was not reached for the target on both tools -- the row "
            "is vacuous and some earlier refusal satisfied assertRaises")

    @mock.patch.object(ollama_client.requests, "post")
    def test_an_fstat_failure_raises_valueerror(self, mock_post):
        target = self._write("vanishing.txt", "body")
        real_fstat = os.fstat
        called = []

        def failing_fstat(fd):
            called.append(fd)
            raise OSError(9, "Bad file descriptor")

        with mock.patch.object(os, "fstat", failing_fstat):
            with self.assertRaises(ValueError):
                file_tools.summarize_file(target)
            with self.assertRaises(ValueError):
                file_tools.extract_json_file(target, {"a": "string"})
        mock_post.assert_not_called()
        self.assertEqual(
            len(called), 2,
            "os.fstat was not reached on both tools -- the row is vacuous")
        # The real fstat must still be in place for the rest of the suite.
        self.assertIs(os.fstat, real_fstat)


class TestCaseFoldEscapeIsRejectedByTheHandleCheck(FileToolsBase):
    r"""A case-sensitive directory makes Root and root two different
    directories, and the commonpath filter cannot tell them apart.

    This proves the AUTHORITATIVE check is actually wired in, not merely
    defined: it asserts on the "case-exact handle check" marker, which only
    _assert_contained_exact produces. The cheap filter ACCEPTS this path -- if
    the exact check were missing, the read would succeed.

    NON-DISCRIMINATING for handle binding: a name-based impostor also passes,
    because realpath restores true on-disk case. This row is about WIRING, not
    about which resolver is used.
    """

    def test_case_differing_sibling_directory_cannot_be_read(self):
        container = os.path.join(self.tmpdir, "cs")
        os.mkdir(container)
        _enable_case_sensitivity(self, container)

        allowed = os.path.join(container, "Root")
        shadow = os.path.join(container, "root")
        os.mkdir(allowed)
        os.mkdir(shadow)
        # Guard: on a filesystem that ignored the request these are ONE
        # directory and the test would be vacuous.
        self.assertTrue(os.path.isdir(allowed))
        self.assertTrue(os.path.isdir(shadow))
        self.assertNotEqual(os.stat(allowed).st_ino, os.stat(shadow).st_ino)

        secret = os.path.join(shadow, "secret.txt")
        with open(secret, "w", encoding="utf-8") as handle:
            handle.write("SENSITIVE")
        self.assertFalse(os.path.exists(os.path.join(allowed, "secret.txt")))

        with mock.patch.object(file_tools, "_ROOTS", [os.path.realpath(allowed)]):
            # The CHEAP filter accepts it -- that is the bug being closed.
            file_tools._assert_contained(os.path.realpath(secret))
            # The AUTHORITATIVE check must refuse it, distinguishably.
            with self.assertRaisesRegex(ValueError, "case-exact handle check"):
                file_tools._open_contained(secret)


class TestDocxRoutingFollowsTheHandleNotTheName(FileToolsBase):
    r"""The .docx decision, and the reported path, must come from the object
    that was OPENED, not from the name that was requested.

    Construction (needs symlink creation rights, as TestSymlinkEscapes does):
    request a.docx, have it become a symlink to b.txt inside the SAME root
    before stat/open run. Both
    files are inside the root, so containment is not what is under test --
    routing and provenance are. If routing follows the requested name, the
    plain text of b.txt is handed to the zip reader and raises BadZipFile, so
    these cannot pass vacuously.
    """

    def _swapping_assert(self, a_docx, b_txt, state):
        real_assert = file_tools._assert_contained

        def swapping_assert(real_path):
            real_assert(real_path)
            if not state["swapped"]:
                state["swapped"] = True
                os.remove(a_docx)
                os.symlink(b_txt, a_docx)
        return swapping_assert

    def test_extension_follows_the_opened_object(self):
        b_txt = self._write("b.txt", "plain text, definitely not a zip archive")
        a_docx = self._write("a.docx", "placeholder")
        state = {"swapped": False}
        with mock.patch.object(file_tools, "_assert_contained",
                               self._swapping_assert(a_docx, b_txt, state)):
            final, handle, _size = file_tools._open_contained(a_docx)
            try:
                text, nbytes = file_tools._read_text(final, handle)
            finally:
                handle.close()
        self.assertTrue(state["swapped"], "the swap never fired -- test is vacuous")
        self.assertEqual(final, os.path.realpath(b_txt))
        self.assertTrue(final.lower().endswith(".txt"))
        self.assertIn("plain text", text)
        self.assertGreater(nbytes, 0)

    @mock.patch.object(ollama_client.requests, "post")
    def test_public_tool_reports_the_handle_path_not_the_requested_name(self, mock_post):
        mock_post.return_value = _make_response("a fine summary")
        b_txt = self._write("b.txt", "plain text, definitely not a zip archive")
        a_docx = self._write("a.docx", "placeholder")
        # SNAPSHOT BEFORE THE SWAP. After a.docx becomes a symlink to b.txt,
        # os.path.realpath(a_docx) resolves THROUGH it and returns b.txt, so a
        # later assertNotEqual against realpath(a_docx) would compare the
        # expected value with itself and fail against a CORRECT implementation.
        requested_path = os.path.realpath(a_docx)
        state = {"swapped": False}
        with mock.patch.object(file_tools, "_assert_contained",
                               self._swapping_assert(a_docx, b_txt, state)):
            out = file_tools.summarize_file(a_docx, max_words=20)
        self.assertTrue(state["swapped"], "the swap never fired -- test is vacuous")
        self.assertEqual(out["path"], os.path.realpath(b_txt))
        self.assertNotEqual(out["path"], requested_path)
        self.assertTrue(requested_path.lower().endswith(".docx"))

    @mock.patch.object(ollama_client.requests, "post")
    def test_extract_json_file_ALSO_reports_the_handle_path(self, mock_post):
        """The same swap through the OTHER public tool. Without this
        row, an implementation that returns the requested path from
        extract_json_file passes everything -- measured: such an impostor
        leaves the summarize_file row above green."""
        mock_post.return_value = _make_response('{"total": "42"}')
        b_txt = self._write("b.txt", "the total is 42 exactly\n")
        a_docx = self._write("a.docx", "placeholder")
        requested_path = os.path.realpath(a_docx)
        state = {"swapped": False}
        with mock.patch.object(file_tools, "_assert_contained",
                               self._swapping_assert(a_docx, b_txt, state)):
            out = file_tools.extract_json_file(a_docx, {"total": "string"})
        self.assertTrue(state["swapped"], "the swap never fired -- test is vacuous")
        self.assertEqual(out["path"], os.path.realpath(b_txt))
        self.assertNotEqual(out["path"], requested_path)
        self.assertTrue(requested_path.lower().endswith(".docx"))
        # The bytes really came from b.txt, so the path is not merely relabeled.
        self.assertEqual(out["fields"]["total"], "42")


class TestSymlinkEscapes(FileToolsBase):
    """Symlinks resolve to their target, so a symlink out of a root must be
    refused exactly as a junction is.

    Symlink creation needs Developer Mode or elevation (with Developer Mode
    on, os.symlink succeeds unelevated). A required security row must FAIL
    rather than skip green, so the helper fails the test with the
    remediation if creation is refused.
    """

    def _symlink(self, link, target, is_dir):
        try:
            os.symlink(target, link, target_is_directory=is_dir)
        except OSError as exc:
            self.fail(
                "could not create a symlink for a required security test "
                "(%r). Enable Developer Mode (Settings > System > For "
                "developers), run the suite elevated, or grant "
                "SeCreateSymbolicLinkPrivilege to this account. Expected "
                "failure on a box without it is WinError 1314." % (exc,))

    def test_file_symlink_escaping_a_root_is_rejected(self):
        outside = tempfile.mkdtemp()
        secret = os.path.join(outside, "secret.txt")
        with open(secret, "w", encoding="utf-8") as handle:
            handle.write("SENSITIVE")
        link = os.path.join(self.tmpdir, "alias.txt")
        self._symlink(link, secret, False)
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools._open_contained(link)

    def test_directory_symlink_escaping_a_root_is_rejected(self):
        outside = tempfile.mkdtemp()
        with open(os.path.join(outside, "secret.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("SENSITIVE")
        link = os.path.join(self.tmpdir, "linkdir")
        self._symlink(link, outside, True)
        with self.assertRaisesRegex(ValueError, "outside the allowed root"):
            file_tools._open_contained(os.path.join(link, "secret.txt"))


class TestDocxReadPath(FileToolsBase):
    def _write_docx(self, name, body_xml):
        path = os.path.join(self.tmpdir, name)
        document = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            'wordprocessingml/2006/main"><w:body>' + body_xml
            + "</w:body></w:document>")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document)
        return path

    def test_docx_read_through_the_bounded_handle(self):
        path = self._write_docx(
            "doc.docx", "<w:p><w:r><w:t>Hello world</w:t></w:r></w:p>")
        final, handle, _size = file_tools._open_contained(path)
        try:
            text, nbytes = file_tools._read_text(final, handle)
        finally:
            handle.close()
        self.assertEqual(text, "Hello world")
        self.assertGreater(nbytes, 0)

    def test_docx_growth_past_the_cap_is_caught_by_the_raw_bound(self):
        # The DOCX path must go through _read_bounded too, or the outer
        # archive escapes the cap even though every inner member is capped.
        path = self._write_docx(
            "grow.docx", "<w:p><w:r><w:t>Hello world</w:t></w:r></w:p>")
        final, handle, _size = file_tools._open_contained(path)
        try:
            with open(path, "ab") as growing:
                growing.write(b"z" * 500000)
            with mock.patch.object(file_tools, "MAX_FILE_BYTES", 1000):
                with self.assertRaisesRegex(ValueError, "grew past the"):
                    file_tools._read_text(final, handle)
        finally:
            handle.close()

    @mock.patch.object(ollama_client.requests, "post")
    def test_entity_bomb_docx_is_refused_with_no_model_call(self, mock_post):
        """The public-tool side of the DTD (entity-expansion) refusal. The
        archive passes every byte-level guard, so without the DTD refusal the
        expanded text reaches the chunker and the model. test_docx_text.py
        covers the library; this covers the tools."""
        mock_post.return_value = _make_response("a fine summary")
        document = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<!DOCTYPE w:document ['
            '<!ENTITY a "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA">'
            '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
            '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
            '<!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">'
            '<!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;">'
            ']>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            'wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>&e;</w:t>'
            '</w:r></w:p></w:body></w:document>')
        path = os.path.join(self.tmpdir, "bomb.docx")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", document.encode("utf-8"))
        with self.assertRaisesRegex(ValueError, "declares a DTD"):
            file_tools.summarize_file(path)
        with self.assertRaisesRegex(ValueError, "declares a DTD"):
            file_tools.extract_json_file(path, {"a": "string"})
        mock_post.assert_not_called()


class TestReportedByteCount(FileToolsBase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_read_text_returns_what_was_read_not_the_stale_stat(self, mock_post):
        # Sub-cap growth is ACCEPTED (an active log gains lines constantly), so
        # the pre-read fstat size goes stale and must not be reported as the
        # byte count. Rejecting every size change instead would make reading a
        # live worker log flaky, which is a core use case.
        mock_post.return_value = _make_response("a fine summary")
        path = self._write("live.txt", "x" * 50)
        final, handle, size = file_tools._open_contained(path)
        try:
            with open(path, "a", encoding="utf-8") as growing:
                growing.write("y" * 25)
            text, nbytes = file_tools._read_text(final, handle)
        finally:
            handle.close()
        self.assertEqual(size, 50)      # the stale pre-read stat
        self.assertEqual(nbytes, 75)    # what actually came back
        self.assertEqual(len(text), 75)

    @mock.patch.object(ollama_client.requests, "post")
    def test_summarize_file_REPORTS_the_read_count_in_its_public_output(
            self, mock_post):
        # THE PUBLIC CONTRACT. The test above calls the private helpers, so it
        # passes even if summarize_file still reports the stale stat size.
        #
        # HOOK CHOICE MATTERS. The growth must land AFTER _open_contained has
        # taken both os.stat and os.fstat, or the "stale" size would simply be
        # the grown size and this test would pass whichever value is reported.
        # _assert_contained_exact runs after both stats and after the identity
        # comparison, so patching THAT is what makes the staleness real. Do not
        # move this hook to _assert_contained.
        mock_post.return_value = _make_response("a fine summary")
        path = self._write("live.txt", "x" * 50)

        real_assert_exact = file_tools._assert_contained_exact
        state = {"grown": False}

        def growing_assert_exact(final_path):
            real_assert_exact(final_path)
            if not state["grown"]:
                state["grown"] = True
                with open(path, "a", encoding="utf-8") as growing:
                    growing.write("y" * 25)

        with mock.patch.object(
                file_tools, "_assert_contained_exact", growing_assert_exact):
            out = file_tools.summarize_file(path, max_words=20)

        self.assertTrue(state["grown"], "the growth never fired -- test is vacuous")
        self.assertEqual(out["bytes"], 75)
        # Pins the staleness itself: if these were equal, the hook fired too
        # early and the test would prove nothing.
        self.assertEqual(os.path.getsize(path), 75)


class TestEmptySummaryNamesTheHandlePath(FileToolsBase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_empty_summary_raises_ollama_error_naming_the_handle_path(
            self, mock_post):
        r"""summarize_file's local `real` went out of scope once the read
        path moved to _open_contained, and the empty-summary raise still
        referenced it -- a NameError on a path no other test exercises, so
        the suite would stay green while shipping the defect.

        A whitespace-only response strips to "", which is the branch. The swap
        makes the row stronger than a NameError check: it pins that the message
        names the HANDLE's object, not the requested name."""
        mock_post.return_value = _make_response("   ")
        b_txt = self._write("b.txt", "plain text, definitely not a zip archive")
        a_docx = self._write("a.docx", "placeholder")
        requested_path = os.path.realpath(a_docx)

        real_assert = file_tools._assert_contained
        state = {"swapped": False}

        def swapping_assert(real_path):
            real_assert(real_path)
            if not state["swapped"]:
                state["swapped"] = True
                os.remove(a_docx)
                os.symlink(b_txt, a_docx)

        with mock.patch.object(file_tools, "_assert_contained", swapping_assert):
            with self.assertRaises(OllamaError) as caught:
                file_tools.summarize_file(a_docx, max_words=20)

        self.assertTrue(state["swapped"], "the swap never fired -- test is vacuous")
        message = str(caught.exception)
        self.assertIn("empty summary", message)
        self.assertIn(os.path.realpath(b_txt), message)
        self.assertNotIn(requested_path, message)


class TestDeniedPathMakesNoModelCall(FileToolsBase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_denied_path_never_reaches_the_model(self, mock_post):
        # CHARACTERIZATION: the code rejects before any model call. Pinned so
        # a future refactor cannot reorder validation after generate().
        outside = os.path.join(tempfile.mkdtemp(), "x.txt")
        with open(outside, "w", encoding="utf-8") as handle:
            handle.write("hi")
        with self.assertRaises(ValueError):
            file_tools.summarize_file(outside)
        with self.assertRaises(ValueError):
            file_tools.extract_json_file(outside, {"a": "string"})
        mock_post.assert_not_called()


class TestHardLinkRejection(FileToolsBase):
    def _hard_link(self, link, target):
        """Create a hard link, failing the TEST if it cannot be made. Same
        discipline as _mklink_j: a required security row must never skip
        green."""
        try:
            os.link(target, link)
        except OSError as exc:
            self.fail("could not create a hard link for the security test: %r"
                      % (exc,))

    def test_hard_link_alias_inside_a_root_is_refused(self):
        outside = tempfile.mkdtemp()
        secret = os.path.join(outside, "secret.txt")
        with open(secret, "w", encoding="utf-8") as handle:
            handle.write("SENSITIVE")
        alias = os.path.join(self.tmpdir, "alias.txt")
        self._hard_link(alias, secret)

        # Both containment checks are blind to this: the alias really is
        # inside, and its handle's final path is the alias name. Neither call
        # below raises -- that is why the hard-link refusal exists.
        file_tools._assert_contained(os.path.realpath(alias))
        file_tools._assert_contained_exact(os.path.realpath(alias))
        with self.assertRaisesRegex(ValueError, "hard link"):
            file_tools._open_contained(alias)

    def test_ordinary_file_with_one_link_is_unaffected(self):
        # No false positives: every normal read has st_nlink == 1.
        path = self._write("plain.txt", "hello")
        final, handle, size = file_tools._open_contained(path)
        handle.close()
        self.assertEqual(size, 5)
        self.assertEqual(final, os.path.realpath(path))

    @mock.patch.object(ollama_client.requests, "post")
    def test_both_public_tools_refuse_a_hard_link_with_no_model_call(self, mock_post):
        # Return value CONFIGURED: with an unconfigured mock, a failure of this
        # row would surface as an unrelated mock error instead of the
        # assertion this row is about.
        mock_post.return_value = _make_response("a fine summary")
        outside = tempfile.mkdtemp()
        secret = os.path.join(outside, "secret.txt")
        with open(secret, "w", encoding="utf-8") as handle:
            handle.write("SENSITIVE")
        alias = os.path.join(self.tmpdir, "alias.txt")
        self._hard_link(alias, secret)
        with self.assertRaisesRegex(ValueError, "hard link"):
            file_tools.summarize_file(alias)
        with self.assertRaisesRegex(ValueError, "hard link"):
            file_tools.extract_json_file(alias, {"a": "string"})
        mock_post.assert_not_called()
