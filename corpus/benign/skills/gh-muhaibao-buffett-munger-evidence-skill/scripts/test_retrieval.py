"""Offline invariants; real-model corpus measurements live in the project verification report."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import library
import retrieve
import wiki


class FakeEncoder:
    def __init__(self, *args, **kwargs):
        pass

    def embed(self, texts, query=False):
        import numpy as np
        result = np.zeros((len(texts), 384), dtype=np.float32)
        for i, text in enumerate(texts):
            result[i, 0 if ("durable" in text or "稳固竞争优势" in text) else 1] = 1
        return result


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.writer = library.Library(self.root / "library")
        self.index = self.root / "index"
        self.models = self.root / "models"
        self.counter = 0

    def tearDown(self):
        self.writer.close()
        self.temp.cleanup()

    def ingest(self, text, **kwargs):
        self.counter += 1
        path = self.root / f"{self.counter}.txt"
        path.write_text(text)
        meta = {"id": f"doc-{self.counter}", "title": "Source speech", "date": "2000", "speaker": "Buffett",
                "url": f"https://example.test/{self.counter}", "source_type": "speech",
                "primary_status": "primary", "transcript_quality": "official"}
        meta.update(kwargs)
        self.writer.ingest(meta, path)
        return self.writer.db.execute("SELECT id FROM chunks WHERE document_id=?", (meta["id"],)).fetchone()[0]

    def run_search(self, query, **kwargs):
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            return retrieve.search(corpus, query, self.index, self.models, **kwargs)
        finally:
            corpus.close()

    def build(self):
        with patch.object(retrieve, "LocalModel", FakeEncoder):
            return retrieve.build_index(self.writer, self.index, self.models)

    def test_readonly_corpus_cannot_mutate(self):
        self.ingest("Original evidence remains unchanged.")
        c = retrieve.open_corpus(self.writer.root)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                c.db.execute("DELETE FROM chunks")
        finally:
            c.close()
        self.assertEqual(self.writer.stats()["chunks"], 1)

    def test_exact_phrase_excludes_word_only_match(self):
        expected = self.ingest("The owner earnings calculation requires judgment.")
        self.ingest("An owner can report earnings without cash.")
        result = self.run_search("owner earnings", exact=True)
        self.assertEqual([r["chunk_id"] for r in result["results"]], [expected])
        self.assertEqual(result["mode_used"], "lexical")
        self.assertFalse(result["reranked"])

    def test_unassigned_fallback_preserves_speaker_and_excludes_other_speakers(self):
        self.ingest("A durable competitive advantage.", speaker="Munger")
        unknown = self.ingest("A durable competitive advantage.", speaker=None, author="Warren Buffett")
        self.ingest("A durable competitive advantage.", speaker="Interviewer")
        result = self.run_search("durable", speaker="Buffett", include_unassigned=True, mode="lexical", rerank=False)
        self.assertEqual([r["chunk_id"] for r in result["results"]], [unknown])
        self.assertIsNone(result["results"][0]["speaker"])
        self.assertFalse(result["results"][0]["evidence_eligibility"]["personal_attribution_candidate"])

    def test_exact_preserves_punctuation_and_does_not_lose_matches_after_cutoff(self):
        self.ingest("90 dollars.")
        expected = self.ingest("Invest 90% of the fund in productive assets and retain the rest.")
        result = self.run_search("90%", exact=True, limit=1, candidates=1)
        self.assertEqual([r["chunk_id"] for r in result["results"]], [expected])

    def test_exact_normalizes_case_and_whitespace_only(self):
        expected = self.ingest("The OWNER   earnings are estimated, not exact.")
        result = self.run_search("owner earnings", exact=True)
        self.assertEqual([r["chunk_id"] for r in result["results"]], [expected])

    def test_missing_index_is_explicit_and_strict_mode_fails(self):
        self.ingest("A durable advantage.")
        result = self.run_search("durable", rerank=False)
        self.assertEqual(result["mode_used"], "lexical")
        self.assertTrue(result["warnings"])
        with self.assertRaisesRegex(ValueError, "not built"):
            self.run_search("durable", mode="hybrid")

    def test_semantic_candidates_survive_without_keyword_overlap(self):
        target = self.ingest("A durable advantage protects the business.")
        self.ingest("Snow falls in the winter.")
        self.build()
        with patch.object(retrieve, "LocalModel", FakeEncoder):
            result = self.run_search("稳固竞争优势", mode="hybrid", rerank=False, limit=1)
        self.assertEqual(result["results"][0]["chunk_id"], target)
        self.assertEqual(result["candidate_counts"]["bm25_0"], 0)
        self.assertEqual(result["mode_used"], "hybrid")

    def test_semantic_filters_apply_before_candidate_cutoff(self):
        self.ingest("A durable advantage.", speaker="Buffett", date="1990")
        target = self.ingest("A durable advantage.", speaker="Munger", date="2010")
        self.build()
        with patch.object(retrieve, "LocalModel", FakeEncoder):
            result = self.run_search("稳固竞争优势", mode="hybrid", rerank=False, speaker="Munger",
                                     year_from=2000, limit=1, candidates=1)
        self.assertEqual(result["results"][0]["chunk_id"], target)

    def test_changed_attribution_invalidates_index(self):
        self.ingest("A durable advantage.")
        self.build()
        self.assertTrue(retrieve.index_status(self.writer, self.index)["ready"])
        with self.writer.db:
            self.writer.db.execute("UPDATE chunks SET speaker='Charlie Munger'")
        self.assertFalse(retrieve.index_status(self.writer, self.index)["ready"])
        with self.assertRaisesRegex(ValueError, "stale"):
            self.run_search("durable", mode="hybrid")

    def test_corrupt_completed_index_is_never_reactivated(self):
        self.ingest("A durable advantage.")
        self.build()
        current = json.loads((self.index / "current.json").read_text())
        (self.index / current["generation"] / "rows.json").write_text("[]")
        self.assertFalse(retrieve.index_status(self.writer, self.index)["ready"])
        with self.assertRaisesRegex(ValueError, "corrupt"):
            self.build()

    def test_failed_build_preserves_previous_generation_pointer(self):
        self.ingest("A durable advantage.")
        self.build()
        before = (self.index / "current.json").read_bytes()
        self.ingest("Another source arrives.")
        with patch.object(retrieve, "LocalModel", side_effect=ValueError("model unavailable")):
            with self.assertRaises(ValueError):
                retrieve.build_index(self.writer, self.index, self.models)
        self.assertEqual((self.index / "current.json").read_bytes(), before)

    def test_context_keeps_each_speaker_and_original_locator(self):
        path = self.root / "meeting.json"
        path.write_text(json.dumps({"segments": [
            {"text": "What drives investment behavior?", "speaker": "Interviewer", "page": 2},
            {"text": "Incentives drive behavior.", "speaker": "Munger", "page": 2},
            {"text": "Now a different topic.", "speaker": "Buffett", "page": 3}]}))
        self.writer.ingest({"id": "meeting", "title": "Meeting", "speaker": "mixed", "source_type": "speech"}, path)
        r = self.run_search("incentives", mode="lexical", rerank=False, speaker="Munger")
        self.assertEqual([p["speaker"] for p in r["results"][0]["context"]], ["Interviewer", "Charlie Munger", "Warren Buffett"])
        self.assertEqual(r["results"][0]["locator"]["page"], 2)

    def test_reranker_missing_does_not_claim_reranking(self):
        self.ingest("A durable advantage.")
        result = self.run_search("durable", mode="lexical")
        self.assertFalse(result["reranked"])
        self.assertTrue(any("Reranker unavailable" in w for w in result["warnings"]))

    def make_wiki(self):
        key = self.ingest("A durable advantage.")
        doc = self.writer.db.execute("SELECT * FROM documents").fetchone()
        page = self.root / "wiki" / "moat.md"
        page.parent.mkdir()
        meta = {"kind": "synthesis", "title": "护城河", "subjects": ["Warren Buffett"], "reviewed_on": "2026-10-06",
                "evidence": [{"label": "E1", "chunk_id": key, "raw_sha256": doc["raw_sha256"],
                              "text_sha256": hashlib.sha256("A durable advantage.".encode()).hexdigest(),
                              "metadata_sha256": hashlib.sha256(doc["metadata"].encode()).hexdigest(), "speaker": "Warren Buffett"}]}
        page.write_text("---\n" + json.dumps(meta) + "\n---\n# 护城河\n一项有据归纳。[E1]\n")
        return page

    def test_wiki_stale_sources_are_flagged_and_excluded(self):
        page = self.make_wiki()
        self.assertEqual(wiki.validate_page(self.writer, page)["status"], "source-links-current")
        with self.writer.db:
            self.writer.db.execute("UPDATE documents SET metadata='{}'")
        self.assertEqual(wiki.validate_page(self.writer, page)["status"], "needs-review")
        result = wiki.search_pages(self.writer, page.parent, "护城河")
        self.assertFalse(result["results"])
        self.assertEqual(len(result["needs_review"]), 1)

    def test_wiki_undefined_citation_is_rejected(self):
        page = self.make_wiki()
        page.write_text(page.read_text() + "没有来源的判断。[E2]\n")
        self.assertEqual(wiki.validate_page(self.writer, page)["status"], "needs-review")

    def test_wiki_extraction_changes_invalidate_even_when_original_file_is_unchanged(self):
        page = self.make_wiki()
        with self.writer.db:
            self.writer.db.execute("UPDATE chunks SET text='Corrected OCR text'")
        result = wiki.validate_page(self.writer, page)
        self.assertEqual(result["status"], "needs-review")
        self.assertTrue(any("passage text changed" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
