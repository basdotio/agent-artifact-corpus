import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "audit_instructions.py"
sys.path.insert(0, str(SCRIPT.parent))

import audit_instructions  # noqa: E402


class AuditInstructionsTests(unittest.TestCase):
    def test_absolute_script_path_works_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            scan_root = temp_root / "project"
            scan_root.mkdir()
            (scan_root / "AGENTS.md").write_text("Use targeted context.\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(scan_root), "--format", "json"],
                cwd=str(temp_root),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload["files_scanned"]), 1)

    def test_root_does_not_implicitly_include_current_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            selected = temp_root / "selected"
            current = temp_root / "current"
            selected.mkdir()
            current.mkdir()
            (selected / "AGENTS.md").write_text("Selected.\n", encoding="utf-8")
            (current / "AGENTS.md").write_text("Current.\n", encoding="utf-8")
            output = StringIO()
            previous = Path.cwd()
            try:
                os.chdir(current)
                with patch.object(sys, "argv", ["audit_instructions.py", "--root", str(selected), "--format", "json"]), redirect_stdout(output):
                    audit_instructions.main()
            finally:
                os.chdir(previous)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["files_scanned"], [(selected / "AGENTS.md").resolve().as_posix()])

    def test_explicit_package_root_does_not_scan_current_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            package = self.make_package(base)
            current = base / "current"
            current.mkdir()
            (current / "AGENTS.md").write_text("Local instruction.\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--package-root", str(package), "--format", "json"],
                cwd=str(current), capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["packages_scanned"], [package.resolve().as_posix()])
            self.assertNotIn((current / "AGENTS.md").as_posix(), report["files_scanned"])

    def test_explicit_package_root_without_entrypoint_blocks_strict_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "not-a-skill"
            package.mkdir()
            (package / "guide.md").write_text("No entrypoint.\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(SCRIPT), "--package-root", str(package), "--strict", "--format", "json"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["packages_scanned"], [])
            self.assertTrue(any(item["issue"] == "missing-entrypoint" for item in report["package_integrity_issues"]))

    def test_strict_mode_rejects_zero_target_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(temp), "--strict", "--format", "json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["files_scanned"], [])
            self.assertEqual(report["packages_scanned"], [])
            self.assertTrue(any("No AGENTS.md or SKILL.md targets" in item for item in report["skipped"]))

    def test_scan_root_named_build_is_not_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            scan_root = Path(temp) / "build"
            nested = scan_root / "nested"
            nested.mkdir(parents=True)
            (scan_root / "AGENTS.md").write_text("Root instruction.\n", encoding="utf-8")
            (nested / "SKILL.md").write_text("Nested skill.\n", encoding="utf-8")
            files, skipped = audit_instructions.iter_files([str(scan_root)])
            self.assertEqual(skipped, [])
            self.assertEqual({path.name for path in files}, {"AGENTS.md", "SKILL.md"})

    def test_conflict_is_a_medium_candidate_until_reviewed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "AGENTS.md"
            path.write_text("Do not edit files.\nYou may edit files when the user explicitly asks.\n", encoding="utf-8")
            findings, error = audit_instructions.scan_file(path, 512_000)
            self.assertIsNone(error)
            conflicts = [item for item in findings if item.category == "conflict"]
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0].severity, "medium")
            self.assertEqual(conflicts[0].confidence, "candidate")

    def test_cross_file_conflict_is_also_a_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "AGENTS.md").write_text("Do not continue until approval.\n", encoding="utf-8")
            (root / "skill").mkdir()
            (root / "skill" / "SKILL.md").write_text("Always continue without asking.\n", encoding="utf-8")
            files, skipped = audit_instructions.iter_files([str(root)])
            records = []
            for path in files:
                records.extend(audit_instructions.extract_directives(path, path.read_text(encoding="utf-8").splitlines()))
            findings = audit_instructions.scan_cross_file_conflicts(records)
            self.assertEqual(skipped, [])
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].severity, "medium")
            self.assertEqual(findings[0].confidence, "candidate")

    def test_direct_unconditional_conflict_is_confirmed_and_strict_exit_one(self):
        with tempfile.TemporaryDirectory() as temp:
            instruction = Path(temp) / "AGENTS.md"
            instruction.write_text("Always edit files.\nNever edit files.\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(temp), "--strict", "--format", "json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report["confirmed_findings"]), 1)
            self.assertEqual(report["confirmed_findings"][0]["confidence"], "confirmed")
            self.assertEqual(report["heuristic_candidates"], [])

    def test_direct_rules_with_distinct_sections_remain_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            instruction = Path(temp) / "AGENTS.md"
            instruction.write_text("# Default\nNever edit files.\n# User requested edits\nAlways edit files.\n", encoding="utf-8")
            findings, error = audit_instructions.scan_file(instruction, 512_000)
            self.assertIsNone(error)
            conflicts = [item for item in findings if item.category == "conflict"]
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0].confidence, "candidate")

    def test_context_between_direct_rules_prevents_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            instruction = Path(temp) / "AGENTS.md"
            instruction.write_text("Never edit files.\nFor generated files only:\nAlways edit files.\n", encoding="utf-8")
            findings, error = audit_instructions.scan_file(instruction, 512_000)
            self.assertIsNone(error)
            conflicts = [item for item in findings if item.category == "conflict"]
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0].confidence, "candidate")

    def make_package(self, root: Path, skill_text: Optional[str] = None) -> Path:
        package = root / "demo-skill"
        (package / "references").mkdir(parents=True)
        (package / "scripts").mkdir()
        (package / "assets").mkdir()
        (package / "SKILL.md").write_text(
            skill_text or "---\nname: demo-skill\ndescription: A test skill.\n---\n\nSee [guide](references/guide.md).\n",
            encoding="utf-8",
        )
        (package / "references" / "guide.md").write_text("Guide.\n", encoding="utf-8")
        (package / "scripts" / "run.py").write_text("print('ok')\n", encoding="utf-8")
        return package

    def test_package_frontmatter_and_references_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp))
            report = audit_instructions.build_report([str(package)], [], 512_000)
            self.assertEqual(report["package_integrity_issues"], [])
            self.assertEqual(report["packages_scanned"], [package.resolve().as_posix()])
            self.assertEqual(report["schema_version"], "1.1")
            self.assertEqual(
                set(report),
                {
                    "schema_version",
                    "roots",
                    "files_scanned",
                    "packages_scanned",
                    "confirmed_findings",
                    "heuristic_candidates",
                    "package_integrity_issues",
                    "dependency_checks",
                    "workflow_consistency_checks",
                    "skipped",
                    "unreadable",
                    "findings",
                },
            )

    def test_explicit_stage_mapping_mismatch_is_confirmed_with_both_quotes(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp))
            (package / "guides").mkdir()
            (package / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: test\n---\n"
                "| Stage | Read | Purpose |\n| --- | --- | --- |\n"
                "| **3. Brainstorming** | [guides/brainstorming.md](guides/brainstorming.md) | Generate ideas |\n",
                encoding="utf-8",
            )
            (package / "guides" / "brainstorming.md").write_text(
                "# Brainstorming (Stage 2 — generate and triage ideas)\n\n## Step 8\n", encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(SCRIPT), "--package-root", str(package), "--strict", "--format", "json"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["package_integrity_issues"], [])
            self.assertEqual(report["workflow_consistency_checks"][0]["status"], "mismatch")
            finding = next(item for item in report["confirmed_findings"] if item["category"] == "workflow-stage-mismatch")
            self.assertEqual([(item["line"], Path(item["path"]).name) for item in finding["evidence"]], [(7, "SKILL.md"), (1, "brainstorming.md")])
            self.assertIn("3. Brainstorming", finding["evidence"][0]["quote"])
            self.assertEqual(finding["evidence"][1]["quote"], "# Brainstorming (Stage 2 — generate and triage ideas)")
            markdown = subprocess.run(
                [sys.executable, "-X", "utf8", str(SCRIPT), "--package-root", str(package), "--strict", "--format", "markdown"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(markdown.returncode, 1, markdown.stderr)
            self.assertIn("## Workflow consistency checks", markdown.stdout)
            self.assertIn("brainstorming.md:1", markdown.stdout)
            self.assertIn("# Brainstorming (Stage 2 — generate and triage ideas)", markdown.stdout)

    def test_stage_mapping_negative_cases_do_not_confirm(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp))
            guides = package / "guides"
            guides.mkdir()
            (package / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: test\n---\n"
                "| Stage | Read | Purpose |\n| --- | --- | --- |\n"
                "| **3. Brainstorming** | [guide](guides/brainstorming.md) | Generate ideas |\n"
                "| **4. Writing** | [guide](guides/writing.md) | Draft |\n"
                "| **5. Evaluation** | [guide](guides/evaluation.md) | Evaluate |\n",
                encoding="utf-8",
            )
            (guides / "brainstorming.md").write_text("# Brainstorming (Stage 3 — ideas)\n## Step 2: local step\n", encoding="utf-8")
            (guides / "writing.md").write_text("# Writing\n## Stage 2 of this independent drafting flow\n", encoding="utf-8")
            (guides / "evaluation.md").write_text("# Evaluation sub-process (Stage 2)\n", encoding="utf-8")
            (guides / "unlinked.md").write_text("# Brainstorming (Stage 2)\n", encoding="utf-8")
            report = audit_instructions.build_report([str(package)], [], 512_000)
            self.assertFalse(any(item["category"] == "workflow-stage-mismatch" for item in report["confirmed_findings"]))
            self.assertEqual([item["status"] for item in report["workflow_consistency_checks"]], ["matched", "not-comparable", "not-comparable"])

    def test_missing_reference_is_integrity_issue_and_strict_exit_two(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nname: demo-skill\ndescription: test\n---\n\n[missing](references/foo.md)\n")
            report = audit_instructions.build_report([str(package)], [], 512_000)
            self.assertTrue(any(item["issue"] == "missing-reference" for item in report["package_integrity_issues"]))
            result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(package), "--strict", "--format", "json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_markdown_link_titles_do_not_become_part_of_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(
                Path(temp),
                '---\nname: demo-skill\ndescription: test\n---\n\n'
                '[plain](references/guide.md "Guide")\n'
                '[angled](<references/guide.md> "Guide")\n'
                '[title-inside-angle](<references/guide.md "Guide">)\n'
                '[parentheses](references/guide(v2).md "Guide (v2)")\n',
            )
            (package / "references" / "guide(v2).md").write_text("Guide v2.\n", encoding="utf-8")
            report = audit_instructions.build_report([str(package)], [], 512_000)
            self.assertEqual(report["package_integrity_issues"], [])

    def test_lowercase_skill_entrypoint_is_discovered_and_audited(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp))
            source = package / "SKILL.md"
            content = source.read_text(encoding="utf-8")
            source.unlink()
            (package / "skill.md").write_text(content, encoding="utf-8")
            report = audit_instructions.build_report([str(package)], [], 512_000)
            self.assertEqual(report["packages_scanned"], [package.resolve().as_posix()])
            self.assertEqual(report["files_scanned"], [(package / "skill.md").resolve().as_posix()])
            self.assertEqual(report["package_integrity_issues"], [])
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--package-root", str(package), "--strict", "--format", "json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_example_paths_are_candidates_but_explicit_links_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nname: demo-skill\ndescription: test\n---\n\n```markdown\n[example](references/absent.md)\n```\nExample: `references/other.md`.\n[guide](references/guide.md)\n")
            report = audit_instructions.build_report([str(package)], [], 512_000)
            self.assertEqual(report["package_integrity_issues"], [])
            self.assertTrue(any(item["category"] == "possible-reference" for item in report["heuristic_candidates"]))

    def test_reference_document_can_use_package_root_relative_path(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp))
            (package / "references" / "guide.md").write_text("Read `scripts/run.py` when needed.\n", encoding="utf-8")
            report = audit_instructions.build_report([str(package)], [], 512_000)
            self.assertEqual(report["package_integrity_issues"], [])
            self.assertFalse(any(item["category"] == "possible-reference" for item in report["heuristic_candidates"]))

    def test_nested_skill_package_is_discovered_and_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = self.make_package(Path(temp))
            nested = parent / ".agents" / "skills" / "nested-skill"
            nested.mkdir(parents=True)
            (nested / "SKILL.md").write_text(
                "---\nname: nested-skill\ndescription: Nested test.\n---\n[missing](references/missing.md)\n",
                encoding="utf-8",
            )
            report = audit_instructions.build_report([str(parent)], [], 512_000)
            self.assertEqual(set(report["packages_scanned"]), {parent.resolve().as_posix(), nested.resolve().as_posix()})
            self.assertTrue(any(item["issue"] == "missing-reference" and "nested-skill" in item["path"] for item in report["package_integrity_issues"]))

    def test_nested_lowercase_skill_is_a_separate_package(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = self.make_package(Path(temp))
            nested = parent / "references" / "nested-skill"
            nested.mkdir()
            (nested / "skill.md").write_text(
                "---\nname: nested-skill\ndescription: Nested test.\n---\nBody.\n",
                encoding="utf-8",
            )
            report = audit_instructions.build_report([str(parent)], [], 512_000)
            self.assertEqual(set(report["packages_scanned"]), {parent.resolve().as_posix(), nested.resolve().as_posix()})
            self.assertEqual(report["package_integrity_issues"], [])

    def test_invalid_frontmatter_missing_name_and_description(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nlicense: MIT\n---\ntext\n")
            issues, _unreadable, _checks = audit_instructions.audit_package(package, 512_000)
            kinds = {item.issue for item in issues}
            self.assertIn("missing-frontmatter-field", kinds)

    def test_invalid_yaml_and_duplicate_field_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nname: demo-skill\nname: duplicate\ndescription: test\n---\ntext\n")
            issues, _unreadable, _checks = audit_instructions.audit_package(package, 512_000)
            kinds = {item.issue for item in issues}
            self.assertIn("duplicate-frontmatter-key", kinds)
            (package / "SKILL.md").write_text("---\nname: demo-skill\ndescription: [broken\n---\ntext\n", encoding="utf-8")
            issues, _unreadable, _checks = audit_instructions.audit_package(package, 512_000)
            kinds = {item.issue for item in issues}
            self.assertIn("invalid-frontmatter", kinds)

    def test_nested_metadata_frontmatter_is_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nname: demo-skill\ndescription: test\nmetadata:\n  short-description: demo\n---\ntext\n")
            issues, _unreadable, _checks = audit_instructions.audit_package(package, 512_000)
            self.assertFalse([item for item in issues if item.issue == "invalid-frontmatter"])

    def test_yaml_block_scalar_and_nested_mapping_are_parsed(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nname: demo-skill\ndescription: >\n  Audit source:\n  preserve evidence.\nmetadata:\n  interface:\n    label: Demo\n---\nBody.\n")
            fields, issues = audit_instructions.parse_frontmatter(package / "SKILL.md")
            self.assertEqual(issues, [])
            self.assertIn("Audit source:", fields["description"])
            self.assertEqual(fields["metadata"]["interface"]["label"], "Demo")

    def test_invalid_yaml_structure_and_nested_duplicate_key_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nname: demo-skill\ndescription: [broken\n---\nBody.\n")
            _fields, issues = audit_instructions.parse_frontmatter(package / "SKILL.md")
            self.assertTrue(any(item.issue == "invalid-frontmatter" for item in issues))
            (package / "SKILL.md").write_text("---\nname: demo-skill\ndescription: test\nmetadata:\n  label: first\n  label: second\n---\nBody.\n", encoding="utf-8")
            _fields, issues = audit_instructions.parse_frontmatter(package / "SKILL.md")
            self.assertTrue(any(item.issue == "duplicate-frontmatter-key" for item in issues))

    def test_token_overuse_is_candidate_without_suggestion(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SKILL.md"
            path.write_text("Always re-read and summarize every file on every turn.\n", encoding="utf-8")
            findings, error = audit_instructions.scan_file(path, 512_000)
            self.assertIsNone(error)
            token = [item for item in findings if item.category == "token-overuse"]
            self.assertGreaterEqual(len(token), 1)
            self.assertFalse(hasattr(token[0], "suggestion"))

    def test_large_and_non_utf8_files_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp))
            (package / "references" / "large.md").write_text("x" * 20, encoding="utf-8")
            (package / "references" / "bad.md").write_bytes(b"\xff\xfe")
            issues, unreadable, _checks = audit_instructions.audit_package(package, 10)
            kinds = {item.issue for item in issues}
            self.assertIn("oversized-file", kinds)
            self.assertTrue(any("bad.md" in item for item in unreadable))

    def test_dependency_check_reports_unavailable_without_installing(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nname: demo-skill\ndescription: test\nskill-dependencies:\n  - definitely-not-installed-command\n---\ntext\n")
            issues, _unreadable, checks = audit_instructions.audit_package(package, 512_000)
            self.assertEqual(checks[0].available, False)
            self.assertEqual(checks[0].callable, False)
            self.assertTrue(any(item.issue == "unavailable-dependency" for item in issues))

    def test_out_of_bound_reference_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp), "---\nname: demo-skill\ndescription: test\n---\n\n[escape](../outside.md)\n")
            issues, _unreadable, _checks = audit_instructions.audit_package(package, 512_000)
            self.assertTrue(any(item.issue == "out-of-bound-reference" for item in issues))

    def test_strict_bad_argument_uses_exit_three(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--max-file-bytes", "0", "--strict"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 3)

    def test_multiple_roots_and_unicode_space_path(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "中文 project"
            first = base / "one"
            second = base / "two"
            first.mkdir(parents=True)
            second.mkdir()
            (first / "AGENTS.md").write_text("one\n", encoding="utf-8")
            (second / "SKILL.md").write_text("two\n", encoding="utf-8")
            report = audit_instructions.build_report([str(first), str(second)], [], 512_000)
            self.assertEqual(len(report["files_scanned"]), 2)

    def test_nonexistent_root_is_reported_in_strict_mode(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", "does-not-exist", "--strict", "--format", "json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stdout)

    def test_unsupported_script_file_type_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            package = self.make_package(Path(temp))
            (package / "scripts" / "run.exe").write_bytes(b"not a script")
            (package / "scripts" / "shell-helper").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            issues, _unreadable, _checks = audit_instructions.audit_package(package, 512_000)
            unsupported = [item.path for item in issues if item.issue == "unsupported-file-type"]
            self.assertTrue(any("run.exe" in path for path in unsupported))
            self.assertFalse(any("shell-helper" in path for path in unsupported))

    def test_out_of_bound_symlink_is_reported_when_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = self.make_package(root)
            outside = root / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            link = package / "references" / "outside.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable on this host")
            issues, _unreadable, _checks = audit_instructions.audit_package(package, 512_000)
            self.assertTrue(any(item.issue == "out-of-bound-symlink" for item in issues))


if __name__ == "__main__":
    unittest.main()
