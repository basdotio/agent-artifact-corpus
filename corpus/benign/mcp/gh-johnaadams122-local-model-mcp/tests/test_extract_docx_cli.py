"""CLI-level coverage for extract_docx.py.

The CLI is a separate seam from the MCP tools: it declares its own caps as
LITERALS, so a change to docx_text's defaults cannot silently change what the
CLI accepts. This module deliberately does NOT import DEFAULT_MAX_BYTES --
comparing the CLI's constant against the library's would be a tautology that
can never fail, so it would prove nothing about the CLI declaring its own
caps.
"""

import ast
import json
import os
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

import extract_docx

_DOCUMENT_XML_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body>{body}</w:body></w:document>"
)

_ENTITY_BOMB = (
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
    '</w:r></w:p></w:body></w:document>'
)

_CLI_CONSTANTS = {
    "CLI_MAX_BYTES": 384000,
    "CLI_MAX_RATIO": 100,
    "CLI_MAX_TEXT_CHARS": 384000,
}


class TestExtractDocxCli(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _source(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(here, "extract_docx.py"), "r",
                  encoding="utf-8") as handle:
            return handle.read()

    def _docx(self, name, body_xml):
        path = os.path.join(self.tmpdir, name)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "word/document.xml",
                _DOCUMENT_XML_TEMPLATE.format(body=body_xml))
        return path

    def _raw_docx(self, name, document_bytes):
        path = os.path.join(self.tmpdir, name)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", document_bytes)
        return path

    def _argv(self, docx_path):
        schema_path = os.path.join(self.tmpdir, "schema.json")
        with open(schema_path, "w", encoding="utf-8") as handle:
            json.dump({"total": "string"}, handle)
        out_path = os.path.join(self.tmpdir, "out.json")
        return ["extract_docx.py", docx_path, schema_path, out_path], out_path

    def _run(self, docx_path):
        argv, out_path = self._argv(docx_path)
        with mock.patch.object(sys, "argv", argv):
            extract_docx.main()
        with open(out_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    # ------------------------------------------------- the cap is DECLARED
    def test_cli_cap_constants_are_explicit_literals(self):
        # No subTest: a subtest failure leaves the PARENT reporting "passed",
        # which makes a failing run ambiguous to read.
        for name, expected in _CLI_CONSTANTS.items():
            self.assertEqual(getattr(extract_docx, name), expected,
                             "extract_docx.%s" % name)

    def test_cli_caps_are_numeric_literals_in_source_never_aliases(self):
        r"""SOURCE-LEVEL anti-alias guard.

        The value assertion above still passes against
        `CLI_MAX_BYTES = DEFAULT_MAX_BYTES`, because the alias IS 384000 --
        so a value check alone cannot tell a literal from an alias.
        This reads the AST instead: each constant must be assigned exactly once
        at module level, from an integer literal, and the module must not
        import any DEFAULT_MAX* name."""
        tree = ast.parse(self._source())

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    self.assertFalse(
                        alias.name.startswith("DEFAULT_MAX"),
                        "extract_docx.py imports %s -- its caps must be "
                        "declared, not inherited" % alias.name)

        assignments = {}
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in _CLI_CONSTANTS:
                    assignments.setdefault(target.id, []).append(node.value)

        for name, expected in _CLI_CONSTANTS.items():
            values = assignments.get(name, [])
            self.assertEqual(
                len(values), 1,
                "%s must be assigned exactly once at module level, got %d"
                % (name, len(values)))
            value = values[0]
            self.assertIsInstance(
                value, ast.Constant,
                "%s must be a numeric literal, not %s"
                % (name, type(value).__name__))
            self.assertEqual(value.value, expected, name)

    def test_the_call_site_passes_the_CLI_NAMES_not_the_library_defaults(self):
        r"""SOURCE-LEVEL guard on the CALL SITE. Not redundant with the mock row
        below -- it covers the gap that row cannot.

        That row compares kwargs["max_bytes"] against extract_docx.CLI_MAX_BYTES
        BY VALUE, and all three pairs are value-identical: CLI 384000/100/384000
        against docx_text's DEFAULT_MAX_BYTES/RATIO/TEXT_CHARS 384000/100/384000.
        So a CLI that declares the literals correctly -- passing the AST guard
        above -- and then writes max_bytes=docx_text.DEFAULT_MAX_BYTES at the
        call site satisfies every runtime assertion in this file, while a later
        change to the library default silently changes what this CLI accepts.
        That is exactly the coupling this guard exists to prevent. Declaring
        the literals and passing something else is the alias wearing a hat.

        So read the call site: each keyword's value expression must be the bare
        NAME of the CLI constant, not some other expression that happens to
        evaluate to the same number today."""
        tree = ast.parse(self._source())

        calls = [node for node in ast.walk(tree)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name)
                 and node.func.id == "extract_text"]
        self.assertEqual(
            len(calls), 1,
            "expected exactly one extract_text(...) call site in "
            "extract_docx.py, got %d" % len(calls))
        call = calls[0]

        self.assertTrue(
            all(keyword.arg for keyword in call.keywords),
            "the call site uses a ** splat -- pass the three CLI constants as "
            "explicit keywords, so this guard can read them")

        expected = {
            "max_bytes": "CLI_MAX_BYTES",
            "max_ratio": "CLI_MAX_RATIO",
            "max_text_chars": "CLI_MAX_TEXT_CHARS",
        }
        passed = {keyword.arg: keyword.value for keyword in call.keywords}
        self.assertEqual(set(passed), set(expected),
                         "extract_text(...) keyword set")
        for arg, name in expected.items():
            value = passed[arg]
            self.assertIsInstance(
                value, ast.Name,
                "%s= must be the bare name %s, got %s"
                % (arg, name, type(value).__name__))
            self.assertEqual(
                value.id, name,
                "%s= passes %s -- the CLI must pass its OWN constant %s, or a "
                "change to the library default silently changes the CLI"
                % (arg, value.id, name))

    # ------------------------------------------------- the cap is PASSED
    @mock.patch.object(extract_docx, "extract_json")
    @mock.patch.object(extract_docx, "extract_text")
    def test_cli_passes_its_own_cap_constants_to_extract_text(
            self, mock_extract_text, mock_extract_json):
        # DECLARING the constants is not the fix -- PASSING them is. A CLI that
        # defines the literals and still calls extract_text(docx_path) fails.
        mock_extract_text.return_value = "total 42"
        mock_extract_json.return_value = {"total": "42"}
        path = self._docx("ok.docx", "<w:p><w:r><w:t>total 42</w:t></w:r></w:p>")
        self._run(path)
        mock_extract_text.assert_called_once()
        _args, kwargs = mock_extract_text.call_args
        self.assertEqual(kwargs.get("max_bytes"), extract_docx.CLI_MAX_BYTES)
        self.assertEqual(kwargs.get("max_ratio"), extract_docx.CLI_MAX_RATIO)
        self.assertEqual(kwargs.get("max_text_chars"),
                         extract_docx.CLI_MAX_TEXT_CHARS)

    # ------------------------------------------------------------ behavior
    @mock.patch.object(extract_docx, "extract_json")
    def test_normal_document_is_accepted(self, mock_extract):
        mock_extract.return_value = {"total": "42"}
        path = self._docx(
            "ok.docx", "<w:p><w:r><w:t>total 42</w:t></w:r></w:p>")
        self.assertEqual(self._run(path), {"total": "42"})

    @mock.patch.object(extract_docx, "extract_json")
    def test_the_extracted_text_and_loaded_schema_REACH_extract_json(
            self, mock_extract):
        r"""Dataflow check. Every other row here mocks extract_json with
        a FIXED return value and asserts only that value or that the mock was
        not called. None of them looks at what it was called WITH -- so a CLI
        that extracts the text correctly, loads the schema correctly, and then
        calls extract_json("", {}) passes the entire file while its only
        actual job, moving that data across, is broken.

        Assert the arguments. The body extracts to exactly "total 42" and
        _argv writes {"total": "string"} to schema.json, so both sides are
        known values, not mock artifacts."""
        mock_extract.return_value = {"total": "42"}
        path = self._docx(
            "ok.docx", "<w:p><w:r><w:t>total 42</w:t></w:r></w:p>")
        self._run(path)
        mock_extract.assert_called_once_with("total 42", {"total": "string"})

    @mock.patch.object(extract_docx, "extract_json")
    def test_oversized_member_is_rejected_before_any_model_call(self, mock_extract):
        # Return value CONFIGURED deliberately. An unconfigured mock returns a
        # MagicMock, json.dump then raises TypeError, and the red output
        # becomes an unrelated serialization error instead of a clean
        # "ValueError not raised". Configure, so the red says what it means.
        mock_extract.return_value = {"total": "42"}
        path = self._raw_docx("bomb.docx", b"A" * 200000)
        with self.assertRaisesRegex(ValueError, "compression ratio|declared size"):
            self._run(path)
        mock_extract.assert_not_called()

    @mock.patch.object(extract_docx, "extract_json")
    def test_entity_bomb_is_rejected_before_any_model_call(self, mock_extract):
        # The CLI is the seam where the expanded text would reach extract_json.
        # Configured for the same reason as the test above.
        mock_extract.return_value = {"total": "42"}
        path = self._raw_docx("entity.docx", _ENTITY_BOMB.encode("utf-8"))
        with self.assertRaisesRegex(ValueError, "declares a DTD"):
            self._run(path)
        mock_extract.assert_not_called()

    @mock.patch.object(extract_docx, "extract_json")
    def test_a_docx_with_no_extractable_text_is_rejected_before_any_model_call(
            self, mock_extract):
        # An empty extraction (an unsupported layout, or a document of images
        # only) must not be sent to the model as if it were the document.
        mock_extract.return_value = {"total": "42"}
        path = self._docx("empty.docx", "<w:p/>")
        with self.assertRaisesRegex(ValueError, "no extractable text"):
            self._run(path)
        mock_extract.assert_not_called()

    @mock.patch.object(extract_docx, "extract_json")
    def test_an_unsupported_namespace_is_rejected_before_any_model_call(
            self, mock_extract):
        mock_extract.return_value = {"total": "42"}
        path = self._raw_docx(
            "other.docx",
            b'<w:document xmlns:w="urn:example:not-word"><w:body><w:p><w:r>'
            b"<w:t>total 42</w:t></w:r></w:p></w:body></w:document>")
        with self.assertRaisesRegex(
                ValueError, "unsupported WordprocessingML namespace"):
            self._run(path)
        mock_extract.assert_not_called()

    def test_TOO_MANY_arguments_also_exits_nonzero(self):
        # The row above exercises only the too-FEW case, so
        # replacing `len(sys.argv) != 4` with `len(sys.argv) < 4` passes it
        # while the CLI silently accepts and ignores trailing arguments -- a
        # contract change nothing would notice. Both arities are asserted here.
        # Mirrors the row below in shape: patch sys.argv directly rather than
        # using _argv/_run, which build a VALID four-element argv and then
        # read the output file -- neither of which applies to a run that must
        # exit before writing anything.
        argv = ["extract_docx.py", "a.docx", "schema.json", "out.json",
                "unexpected-fifth-argument"]
        with mock.patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as caught:
                extract_docx.main()
        self.assertEqual(caught.exception.code, 1,
                         "extra arguments must be rejected, not ignored")

    def test_wrong_argument_count_exits_nonzero(self):
        # main() guards on len(sys.argv) != 4 (exact) and calls sys.exit(1).
        with mock.patch.object(sys, "argv", ["extract_docx.py", "only-one"]):
            with self.assertRaises(SystemExit) as caught:
                extract_docx.main()
        self.assertEqual(caught.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
