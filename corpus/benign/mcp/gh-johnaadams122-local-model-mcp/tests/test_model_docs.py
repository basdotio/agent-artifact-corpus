"""Guard on the model/tool documentation.

These assertions state RELATIONSHIPS, not vocabulary. The rejected form
asserted only that two variable names and two model strings appeared SOMEWHERE
in README.md -- a README that swapped the defaults between the variables passed
every one of them. These read the model table as a mapping instead, so a swap
fails.
"""

import ast
import os
import re
import unittest

from local_llm import file_tools

_MODEL_MATRIX = {
    "LOCAL_LLM_MODEL": ("gemma4:12b-it-qat",
                        frozenset({"summarize", "classify", "extract_json"})),
    "LOCAL_LLM_FILE_MODEL": ("qwen2.5:7b",
                             frozenset({"summarize_file", "extract_json_file"})),
}


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _repo_file(name):
    with open(os.path.join(_repo_root(), name), "r", encoding="utf-8") as handle:
        return handle.read()


def _cells(row):
    return [cell.strip().strip("`").strip()
            for cell in row.strip().strip("|").split("|")]


class TestModelDocsDoNotRegress(unittest.TestCase):
    def _model_rows(self):
        """Map variable name -> (default, set of tool names) from README's
        model table. Reading it as a TABLE is what makes a swapped default
        fail: the default and the tool list are read from the same row as the
        variable, not searched for independently."""
        rows = {}
        for line in _repo_file("README.md").splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = _cells(line)
            if len(cells) != 3:
                continue
            name = cells[0]
            if name not in _MODEL_MATRIX:
                continue
            tools = frozenset(
                tool.strip().strip("`") for tool in cells[2].split(",")
                if tool.strip())
            rows[name] = (cells[1], tools)
        return rows

    def test_readme_maps_each_model_variable_to_its_own_default_and_tools(self):
        rows = self._model_rows()
        self.assertEqual(
            set(rows), set(_MODEL_MATRIX),
            "README's model table must have one row per model variable")
        for variable, (default, tools) in _MODEL_MATRIX.items():
            actual_default, actual_tools = rows[variable]
            self.assertEqual(
                actual_default, default,
                "%s must be documented as defaulting to %s"
                % (variable, default))
            # Compared as a SET, not by substring: "summarize" is a substring
            # of "summarize_file" and "extract_json" of "extract_json_file", so
            # an assertIn here would pass against a swapped tool list.
            self.assertEqual(
                actual_tools, set(tools),
                "%s must be documented as governing exactly %s"
                % (variable, sorted(tools)))

    def test_readme_documents_every_tool_the_server_registers(self):
        """A tool count written in prose goes stale. The truth is not a
        number in prose -- it is server.py's registration list, so that is
        what this reads. A sixth tool added without a README section fails
        here."""
        tree = ast.parse(_repo_file("server.py"))
        registered = None
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_tools":
                    registered = [element.id for element in node.value.elts]
        self.assertIsNotNone(registered, "server.py has no _tools list")
        self.assertEqual(len(registered), 5)

        readme = _repo_file("README.md")
        headings = {line.split("(")[0].replace("### ", "").strip()
                    for line in readme.splitlines() if line.startswith("### ")}
        for tool in registered:
            self.assertIn(
                tool, headings,
                "README has no '### %s(...)' section, but server.py registers "
                "it" % tool)

    def test_readme_rollback_names_exactly_the_model_variables(self):
        r"""Asserted as SET EQUALITY, not as "each name appears".

        "Appears somewhere" is the vocabulary shape this module exists to
        reject, and an earlier draft of this very test used it. Equality is a
        relationship: a Rollback
        section naming only LOCAL_LLM_MODEL fails on the missing element, and
        one naming some other LOCAL_LLM_* variable fails on the extra one, so
        the section cannot drift out of step with the table above it."""
        readme = _repo_file("README.md")
        self.assertIn("### Rollback", readme)
        section = readme.split("### Rollback", 1)[1].split("\n## ", 1)[0]
        named = set(re.findall(r"LOCAL_LLM_[A-Z_]+", section))
        self.assertEqual(
            named, set(_MODEL_MATRIX),
            "the Rollback section must name exactly the model variables %s; "
            "it names %s. A rollback that sets only one variable is the error "
            "this guard exists to catch."
            % (sorted(_MODEL_MATRIX), sorted(named)))
        # And it must say what it is rolling back TO, read from the matrix
        # rather than hardcoded here.
        target = _MODEL_MATRIX["LOCAL_LLM_MODEL"][0]
        self.assertIn(
            target, section,
            "the Rollback section must name the model being rolled back to "
            "(%s), or it does not describe a rollback at all" % target)

    def test_readme_still_documents_the_file_model_variable(self):
        # Guard the public model documentation against an edit that collapses
        # the independent model controls back to one variable.
        self.assertIn("LOCAL_LLM_FILE_MODEL", _repo_file("README.md"))

    def test_the_two_code_defaults_really_are_different(self):
        # Pins the premise the docs rest on. Read from SOURCE rather than from
        # the imported values, which carry the deployed env override.
        self.assertIn(
            'os.environ.get("LOCAL_LLM_MODEL", "gemma4:12b-it-qat")',
            _repo_file(os.path.join("local_llm", "ollama_client.py")))
        self.assertIn(
            'os.environ.get("LOCAL_LLM_FILE_MODEL", "qwen2.5:7b")',
            _repo_file(os.path.join("local_llm", "file_tools.py")))


class TestBoundaryDocsDoNotRegress(unittest.TestCase):
    r"""Guards the file-tool boundary documentation, not just the model
    matrix: any default roots in README and in both MCP docstrings, the
    384,000-byte cap, the hard-link refusal, the credential exclusions, the
    threat-model marker in the module docstring, and the public README
    containment line.

    These are the surfaces that regress SILENTLY -- a root added or a refusal
    removed changes no behavior a test would notice, only a promise a reader
    relies on.

    The root list is driven from _DEFAULT_ROOTS, never from literals. A public
    install ships with NO default roots (_DEFAULT_ROOTS is empty), so the
    per-root checks are vacuous today; any default root added later must be
    documented or these rows fail. The cap, hard-link and threat-model checks
    always run.
    """

    def _shipped_roots(self):
        return list(file_tools._DEFAULT_ROOTS)

    def test_module_docstring_carries_the_threat_model_and_every_root(self):
        doc = file_tools.__doc__ or ""
        self.assertIn("THREAT MODEL:", doc,
                      "the threat-model note belongs in the MODULE "
                      "docstring specifically, not only in external docs")
        for root in self._shipped_roots():
            self.assertIn(root, doc,
                          "module docstring omits root %s" % root)
        self.assertIn("Hard-linked files are", doc)

    def _assert_tool_docstring_is_complete(self, doc, label):
        r"""BOTH MCP docstrings are held to the SAME standard.

        An earlier revision gave extract_json_file a cross-reference instead
        of the literals and then rewrote its assertion to certify that
        narrowing -- so the guard had been changed to bless the gap rather
        than catch it. BOTH docstrings must name every default root (there
        are none in a public install), the hard-link refusal and the cap.
        """
        for root in self._shipped_roots():
            self.assertIn(root, doc, "%s docstring omits root %s"
                          % (label, root))
        self.assertIn("hard-linked", doc.lower(),
                      "%s docstring omits the hard-link refusal" % label)
        # "384" alone matches 3840, 384-anything, or a stray year-like token.
        # Assert the CAP as it is written.
        self.assertIn("384 KB", doc,
                      "%s docstring must state the cap as '384 KB'" % label)

    def test_summarize_file_docstring_names_every_root_and_the_refusal(self):
        self._assert_tool_docstring_is_complete(
            file_tools.summarize_file.__doc__ or "", "summarize_file")

    def test_extract_json_file_docstring_names_every_root_and_the_refusal(self):
        self._assert_tool_docstring_is_complete(
            file_tools.extract_json_file.__doc__ or "", "extract_json_file")

    def test_the_dtd_claim_is_narrowed_wherever_it_appears(self):
        r"""The DTD refusal is scoped to word/document.xml in docx_text and
        pinned there by that module's own tests. This row covers the
        documentation surfaces (the file_tools module docstring and README),
        so the broad archive-level phrasing cannot be restored on either of
        them without a test noticing.
        """
        module_doc = file_tools.__doc__ or ""
        readme = _repo_file("README.md")
        for label, text in (("module docstring", module_doc),
                            ("README.md", readme)):
            self.assertIn("word/document.xml", text,
                          "%s must scope the DTD refusal to the member" % label)
            # The broad form is the regression. It must not reappear.
            self.assertNotIn("archive is refused", text,
                             "%s restored the archive-level DTD claim" % label)
            # The METADATA-screen claim must be scoped as well. "every member
            # is screened on metadata" would contradict docx_text.py -- its
            # loop does `if not info.filename.lower().endswith((".xml",
            # ".rels")): continue`, so a 400 KB PNG is skipped entirely. That
            # sentence would advertise protection the code does not provide,
            # so the scoped form is required and the broad form is forbidden.
            self.assertIn(".rels", text,
                          "%s must scope the metadata screen to .xml and "
                          ".rels members" % label)
            self.assertNotIn("every member is screened", text,
                             "%s claims a screen over members the code "
                             "deliberately skips" % label)

    def test_readme_boundary_section_names_the_roots_cap_and_refusals(self):
        readme = _repo_file("README.md")
        self.assertIn("File tool boundary", readme)
        section = readme.split("File tool boundary", 1)[1].split("\n## ", 1)[0]
        for root in self._shipped_roots():
            self.assertIn(root, section,
                          "README boundary section omits root %s" % root)
        self.assertIn("384000", section)
        self.assertIn("hard-link", section.lower())
        self.assertIn("credential", section.lower())

    def test_readme_documents_the_containment_and_refusals(self):
        readme = _repo_file("README.md")
        self.assertIn("two-tier", readme.lower())
        self.assertIn("hard-link refusal", readme.lower())
        # NARROWED: the DTD refusal covers word/document.xml, not the
        # archive. Asserting the member name is what keeps the corrected
        # wording from drifting back.
        self.assertIn("word/document.xml", readme)


if __name__ == "__main__":
    unittest.main()
