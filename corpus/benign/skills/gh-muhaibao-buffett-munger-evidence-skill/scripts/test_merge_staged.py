"""Offline merge regressions using isolated temporary libraries and staged sources."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

import library
import merge_staged


class MergeStagedTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="buffett-merge-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.stage = self.root / "staged"
        self.stage.mkdir()
        self.library_path = self.root / "isolated-library"
        self.source = self.stage / "source.json"
        self.metadata_path = self.stage / "metadata.json"
        self.manifest = self.stage / "manifest.json"
        self.source.write_text(json.dumps({"segments": [
            {"text": "Synthetic test passage about the circle of competence.", "section": "First passage"},
            {"text": "A synthetic second passage discusses a durable business moat.", "section": "Second passage"},
        ]}))
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.metadata = {
            "id": "synthetic-merge-regression",
            "title": "Synthetic staged interview fixture",
            "url": "https://example.invalid/fixture#transcript",
            "source_type": "interview",
            "speaker": "Munger",
            "date": "2023",
            "primary_status": "primary",
            "transcript_quality": "official",
            "accessed_at": "2026-01-01T00:00:00+00:00",
        }
        self.entry = {
            "id": self.metadata["id"],
            "source_path": str(self.source),
            "metadata_path": str(self.metadata_path),
            "source_sha256": self.source_hash,
        }
        self.run_count = 0
        self.write_stage()

    def write_stage(self):
        self.metadata_path.write_text(json.dumps(self.metadata))
        self.manifest.write_text(json.dumps({"documents": [self.entry]}))

    def merge(self, clock="2026-01-01T00:00:00+00:00"):
        self.run_count += 1
        report_path = self.root / f"report-{self.run_count}.json"
        arguments = [
            "merge_staged.py", "--library", str(self.library_path),
            "--report", str(report_path), str(self.manifest),
        ]
        with mock.patch.object(sys, "argv", arguments), \
                mock.patch.object(library, "now", return_value=clock), \
                contextlib.redirect_stdout(io.StringIO()):
            code = merge_staged.main()
        self.assertTrue(report_path.is_file())
        return code, json.loads(report_path.read_text())

    def snapshot(self):
        """Observe persisted state without invoking ingestion or normalization."""
        database = self.library_path / "corpus.sqlite3"
        with sqlite3.connect(str(database)) as connection:
            connection.row_factory = sqlite3.Row
            return {
                table: [dict(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                for table in ("documents", "chunks", "chunks_fts", "attempts")
            }

    def search(self, **filters):
        corpus = library.Library(self.library_path)
        try:
            return corpus.search("competence", **filters)["results"]
        finally:
            corpus.close()

    def assert_report(self, code, report, indexed=0, skipped=0, failures=0):
        self.assertEqual(code, 1 if failures else 0)
        self.assertEqual(len(report["indexed"]), indexed)
        self.assertEqual(len(report["skipped"]), skipped)
        self.assertEqual(len(report["failures"]), failures)

    def test_first_import_indexes_staged_content_and_normalized_metadata(self):
        self.assert_report(*self.merge(), indexed=1)
        state = self.snapshot()
        self.assertEqual(len(state["documents"]), 1)
        self.assertEqual(len(state["chunks"]), 2)
        self.assertEqual(len(state["chunks_fts"]), 2)
        document = state["documents"][0]
        self.assertEqual(document["raw_sha256"], self.source_hash)
        self.assertEqual(document["url"], "https://example.invalid/fixture")
        self.assertEqual(document["speaker"], "Charlie Munger")
        self.assertEqual(document["date"], "2023")
        self.assertEqual(document["year"], 2023)
        self.assertEqual(json.loads(document["metadata"])["date_precision"], "year")
        self.assertEqual({row["speaker"] for row in state["chunks"]}, {"Charlie Munger"})
        self.assertEqual((self.library_path / document["raw_path"]).read_bytes(), self.source.read_bytes())
        self.assertEqual(len(self.search(speaker="Munger", year_from=2023, year_to=2023)), 1)

    def test_identical_source_and_metadata_are_skipped_without_database_changes(self):
        self.assert_report(*self.merge(), indexed=1)
        before = self.snapshot()
        raw_paths = sorted((self.library_path / "raw").iterdir())
        self.assert_report(*self.merge(clock="2026-01-02T00:00:00+00:00"), skipped=1)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(sorted((self.library_path / "raw").iterdir()), raw_paths)

    def test_equivalent_normalized_metadata_is_also_idempotent(self):
        self.assert_report(*self.merge(), indexed=1)
        before = self.snapshot()
        # Explicit defaults and removal of a non-semantic URL fragment do not
        # change the evidence metadata that was stored by the first import.
        self.metadata.update(
            url="https://example.invalid/fixture", date_precision="year",
            publication_date=None, rights="unknown", author=None,
        )
        self.write_stage()
        self.assert_report(*self.merge(), skipped=1)
        self.assertEqual(self.snapshot(), before)

    def test_unchanged_input_without_accessed_at_is_idempotent_across_time(self):
        self.metadata.pop("accessed_at")
        self.write_stage()
        self.assert_report(*self.merge(), indexed=1)
        before = self.snapshot()
        self.assert_report(*self.merge(clock="2026-02-01T00:00:00+00:00"), skipped=1)
        self.assertEqual(self.snapshot(), before)

    def test_same_source_with_changed_speaker_updates_attribution_and_search(self):
        self.assert_report(*self.merge(), indexed=1)
        before = self.snapshot()
        old_ids = {row["id"] for row in before["chunks"]}
        self.metadata["speaker"] = "Buffett"
        self.write_stage()
        self.assert_report(*self.merge(), indexed=1)
        after = self.snapshot()
        self.assertEqual(len(after["documents"]), 1)
        self.assertEqual(after["documents"][0]["raw_sha256"], self.source_hash)
        self.assertEqual(after["documents"][0]["speaker"], "Warren Buffett")
        self.assertEqual({row["speaker"] for row in after["chunks"]}, {"Warren Buffett"})
        self.assertEqual(len(after["chunks"]), 2)
        self.assertEqual(len(after["chunks_fts"]), 2)
        self.assertFalse(old_ids & {row["chunk_id"] for row in after["chunks_fts"]})
        self.assertEqual(self.search(speaker="Munger"), [])
        self.assertEqual(len(self.search(speaker="Buffett")), 1)
        self.assertEqual(len(list((self.library_path / "raw").iterdir())), 1)

    def test_same_source_with_changed_date_updates_provenance_and_year_filter(self):
        self.assert_report(*self.merge(), indexed=1)
        self.metadata["date"] = "2024-02-15"
        self.write_stage()
        self.assert_report(*self.merge(), indexed=1)
        state = self.snapshot()
        self.assertEqual(len(state["documents"]), 1)
        document = state["documents"][0]
        self.assertEqual(document["raw_sha256"], self.source_hash)
        self.assertEqual(document["date"], "2024-02-15")
        self.assertEqual(document["year"], 2024)
        self.assertEqual(json.loads(document["metadata"])["date_precision"], "day")
        self.assertEqual(self.search(year_to=2023), [])
        results = self.search(year_from=2024, year_to=2024)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["provenance"]["date"], "2024-02-15")
        self.assertEqual(len(state["chunks_fts"]), 2)

    def test_mismatched_source_sha_rejects_update_and_preserves_existing_evidence(self):
        self.assert_report(*self.merge(), indexed=1)
        before = self.snapshot()
        self.source.write_text(json.dumps({"segments": [{"text": "Tampered staging text must not replace valid evidence."}]}))
        self.metadata["speaker"] = "Buffett"
        self.write_stage()
        code, report = self.merge()
        self.assert_report(code, report, failures=1)
        self.assertIn("Staged text SHA256 mismatch", report["failures"][0]["error"])
        self.assertEqual(self.snapshot(), before)

    def test_source_outside_manifest_directory_is_rejected_including_symlink(self):
        outside = self.root / "outside.json"
        outside.write_bytes(self.source.read_bytes())
        symlink = self.stage / "outside-link.json"
        symlink.symlink_to(outside)
        for path in (outside, symlink):
            with self.subTest(source=path.name):
                self.entry["source_path"] = str(path)
                self.write_stage()
                code, report = self.merge()
                self.assert_report(code, report, failures=1)
                self.assertIn("within manifest directory", report["failures"][0]["error"])
                state = self.snapshot()
                self.assertEqual(state["documents"], [])
                self.assertEqual(state["chunks"], [])
                self.assertEqual(state["chunks_fts"], [])


if __name__ == "__main__":
    unittest.main()
