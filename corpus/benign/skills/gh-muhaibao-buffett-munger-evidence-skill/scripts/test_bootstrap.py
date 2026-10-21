"""Offline bootstrap regressions: every skill script is replaced by a fake that writes
the same result files, so no network, models or index builds are touched.

An agent installs unattended and reports what the bootstrap says. These tests guard the
two ways that can go wrong: redoing or losing work across reruns, and a report that
looks healthier than the library really is.
"""
import contextlib
import fcntl
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import bootstrap
import library

COLLECTOR_SCRIPTS = {"collect.py", "collect_financials.py", "collect_meetings.py", "collect_speeches.py"}


class FakeScripts:
    """Stands in for the skill scripts, writing the result files the real ones write."""

    def __init__(self):
        self.calls = []
        self.crash = set()        # scripts that exit 1 without writing a result
        self.gaps = {}            # script -> manifest failures (source gaps)
        self.search_mode = "hybrid"
        self.missing_chapter_links = False

    def __call__(self, command, log_path, capture=False):
        script = Path(command[1]).name
        option = lambda flag: command[command.index(flag) + 1]
        label = script if script != "collect.py" else "collect.py:" + option("--kind")
        self.calls.append(label)
        if script in self.crash:
            return 1, ""
        if script == "library.py":
            library.Library(option("--library")).close()
        elif script == "collect.py":
            result = Path(option("--library")) / "discovery" / (option("--kind") + "-last-run.json")
            result.parent.mkdir(parents=True, exist_ok=True)
            gaps = self.gaps.get(label, [])
            result.write_text(json.dumps({"discovered": 1, "selected": 1, "indexed": 1, "skipped": 0, "failures": gaps}))
            return (1 if gaps else 0), ""
        elif script in {"collect_financials.py", "collect_meetings.py", "collect_speeches.py"}:
            output = Path(option("--stage" if script == "collect_financials.py" else "--output"))
            if script == "collect_speeches.py":
                links = output / "chapter-links.json"
                self.missing_chapter_links = not links.exists() or len(json.loads(links.read_text())["chapter_urls"]) != 11
                if self.missing_chapter_links:
                    return 1, ""
            output.mkdir(parents=True, exist_ok=True)
            gaps = self.gaps.get(script, [])
            (output / "manifest.json").write_text(json.dumps({"documents": [], "failures": gaps}))
            return (1 if gaps else 0), ""
        elif script == "merge_staged.py":
            source = Path(option("--report")).parent / "fixture.txt"
            source.write_text("Synthetic passage about the circle of competence.")
            corpus = library.Library(option("--library"))
            corpus.ingest({"id": "fixture", "title": "Fixture", "url": "https://example.test/fixture"}, source)
            corpus.close()
            Path(option("--report")).write_text(json.dumps({"indexed": [{"id": "fixture"}], "skipped": [],
                                                            "failures": [], "source_gaps": []}))
        elif script == "retrieve.py" and "status" in command:
            return 0, json.dumps({"ready": True, "chunks": 1})
        elif script == "retrieve.py" and "search" in command:
            # The real search still reranks after falling back to BM25, so only mode_used reveals it.
            return 0, json.dumps({"mode_used": self.search_mode, "reranked": True,
                                  "results": [{"chunk_id": "fixture:0"}], "warnings": []})
        elif script == "qa.py" and "status" in command:
            built = "qa.py:build" in self.calls
            return 0, json.dumps({"ready": built, "semantic": built, "units": 1})
        elif script == "qa.py":
            self.calls.append("qa.py:build")
        return 0, ""

    def collectors(self):
        return [call for call in self.calls if call.split(":")[0] in COLLECTOR_SCRIPTS]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="buffett-bootstrap-test-")
        self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name) / "data"
        self.fake = FakeScripts()

    def run_bootstrap(self, problems=()):
        self.fake.calls.clear()
        with mock.patch.object(bootstrap, "execute", self.fake), \
                mock.patch.object(bootstrap, "check_dependencies", return_value=(list(problems), {}, [])), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = bootstrap.main(["--data", str(self.data)])
        return code, json.loads((self.data / "bootstrap-report.json").read_text())

    def test_fresh_run_collects_every_automated_source_and_reports_a_usable_library(self):
        code, report = self.run_bootstrap()
        self.assertEqual(code, 0, report["failures"])
        self.assertTrue(report["ok"])
        # Annual reports are written directly first so the staged financials collector,
        # which only reads the library to skip duplicates, does not stage them twice.
        self.assertEqual(self.fake.collectors(), ["collect.py:buffett-letters", "collect.py:wesco-letters",
                                                  "collect.py:reports", "collect_financials.py",
                                                  "collect_meetings.py", "collect_speeches.py"])
        # The speeches collector refuses to run without the verified chapter links.
        self.assertFalse(self.fake.missing_chapter_links)
        self.assertEqual((report["documents"], report["chunks"]), (1, 1))
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["source_gaps"], [])

    def test_rerun_after_a_crash_resumes_only_the_unfinished_collector(self):
        # Rerunning a finished collector re-downloads sources and can re-ingest them with new
        # capture times, which invalidates a 30-minute semantic index for nothing.
        self.fake.crash = {"collect_meetings.py"}
        code, report = self.run_bootstrap()
        self.assertEqual(code, 1)
        self.assertFalse(report["ok"])
        self.assertEqual([f["step"] for f in report["failures"]], ["collect-meetings"])
        self.fake.crash = set()
        code, report = self.run_bootstrap()
        self.assertEqual(code, 0, report["failures"])
        self.assertEqual(self.fake.collectors(), ["collect_meetings.py"])
        self.assertEqual(report["documents"], 1)

    def test_source_gaps_are_reported_without_failing_the_install_and_retried_next_run(self):
        # A transcript the publisher no longer serves is a gap to report, not a broken install;
        # it is retried because the cause may be transient.
        gaps = [{"stage": "session_transcript", "year": 2001, "url": "https://example.test/a", "error": "no text"},
                {"stage": "session_transcript", "year": 2002, "url": "https://example.test/b", "error": "no text"}]
        self.fake.gaps = {"collect_meetings.py": gaps}
        code, report = self.run_bootstrap()
        self.assertEqual(code, 0, report["failures"])
        self.assertTrue(report["ok"])
        self.assertEqual(report["failures"], [])
        self.assertEqual([gap["url"] for gap in report["source_gaps"]], ["https://example.test/a", "https://example.test/b"])
        self.assertEqual({gap["step"] for gap in report["source_gaps"]}, {"collect-meetings"})
        self.assertEqual(next(s for s in report["steps"] if s["name"] == "collect-meetings")["status"], "partial")
        self.fake.gaps = {}
        code, report = self.run_bootstrap()
        self.assertEqual(self.fake.collectors(), ["collect_meetings.py"])
        self.assertEqual(report["source_gaps"], [])

    def test_gap_filled_by_another_collector_is_not_reported_as_missing(self):
        # The 2020 annual-report PDF once failed in collect.py while collect_financials staged the
        # same file; telling the user it is missing would be false.
        self.fake.gaps = {"collect.py:reports": [{"url": "https://example.test/fixture", "error": "Invalid object in /Pages"},
                                                 {"url": "https://example.test/missing", "error": "timed out"}]}
        code, report = self.run_bootstrap()
        self.assertEqual(code, 0, report["failures"])
        self.assertEqual([gap["url"] for gap in report["source_gaps"]], ["https://example.test/missing"])
        self.assertEqual([gap["url"] for gap in report["filled_gaps"]], ["https://example.test/fixture"])

    def test_result_file_left_by_an_earlier_run_cannot_hide_a_crash(self):
        self.fake.gaps = {"collect_meetings.py": [{"stage": "session_transcript", "url": "u", "error": "no text"}]}
        self.run_bootstrap()
        self.fake.gaps = {}
        self.fake.crash = {"collect_meetings.py"}
        code, report = self.run_bootstrap()
        self.assertEqual(code, 1)
        self.assertIn("collect-meetings", [f["step"] for f in report["failures"]])
        self.assertEqual(next(s for s in report["steps"] if s["name"] == "collect-meetings")["status"], "failed")

    def test_whole_collector_failure_is_not_downgraded_to_a_source_gap(self):
        # The meetings collector records an unreachable archive index inside its manifest.
        self.fake.gaps = {"collect_meetings.py": [{"stage": "index", "error": "timed out"}]}
        code, report = self.run_bootstrap()
        self.assertEqual(code, 1)
        self.assertEqual([f["step"] for f in report["failures"]], ["collect-meetings"])

    def test_missing_dependency_stops_before_any_download(self):
        code, report = self.run_bootstrap(problems=["lxml is not importable"])
        self.assertEqual(code, 1)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(report["failures"][0]["step"], "dependencies")
        self.assertIn("uv pip install", report["failures"][0]["fix"])

    def test_keyword_fallback_is_not_reported_as_a_working_install(self):
        # retrieve.py silently degrades to BM25 when the index or models are unusable.
        self.fake.search_mode = "lexical"
        code, report = self.run_bootstrap()
        self.assertEqual(code, 1)
        self.assertFalse(report["ok"])
        self.assertEqual({f["step"] for f in report["failures"]}, {"smoke-buffett", "smoke-munger"})

    def test_deleted_library_is_rebuilt_from_every_collector(self):
        self.run_bootstrap()
        shutil.rmtree(self.data / "buffett-munger-library")
        code, report = self.run_bootstrap()
        self.assertEqual(code, 0, report["failures"])
        self.assertEqual(len(self.fake.collectors()), 6)

    def test_second_bootstrap_on_the_same_data_refuses_to_start(self):
        # Two writers on one library corrupt merges and leave indexes stale.
        stage = self.data / "staging" / "bootstrap"
        stage.mkdir(parents=True)
        with (stage / "bootstrap.lock").open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with mock.patch.object(bootstrap, "execute", self.fake), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(bootstrap.main(["--data", str(self.data)]), 1)
        self.assertEqual(self.fake.calls, [])


if __name__ == "__main__":
    unittest.main()
