"""Offline regression tests: python -m unittest discover -s scripts -p test_library.py."""
import contextlib
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import library


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.corpus = library.Library(self.root / "corpus")
        self.meta = {"title": "A test speech", "url": "https://example.test/speech",
                     "date": "2000", "source_type": "speech", "speaker": "Munger",
                     "primary_status": "primary", "transcript_quality": "official",
                     "rights": "test fixture"}

    def tearDown(self):
        self.corpus.close()
        self.directory.cleanup()

    def ingest(self, content, suffix=".txt", **metadata):
        source = self.root / ("fixture" + suffix)
        source.write_text(content, encoding="utf-8")
        return self.corpus.ingest(dict(self.meta, **metadata), source)

    def test_reimport_deduplication_and_content_hash(self):
        content = "A durable moat protects a business from competition."
        first = self.ingest(content)
        original_id = self.corpus.search("moat")["results"][0]["chunk_id"]
        second = self.ingest(content)
        self.assertEqual(first, second)
        self.assertEqual(first["raw_sha256"], hashlib.sha256(content.encode()).hexdigest())
        self.assertEqual(Path(first["raw_path"]).read_text(), content)
        self.assertEqual(self.corpus.search("moat")["results"][0]["chunk_id"], original_id)
        self.assertEqual(self.corpus.stats()["documents"], 1)
        self.assertEqual(self.corpus.stats()["chunks"], 1)

    def test_update_removes_stale_full_text_entries(self):
        first = self.ingest("A moat protects a business from competition.")
        old_id = self.corpus.search("moat")["results"][0]["chunk_id"]
        updated = self.ingest("Rationality is essential when evaluating incentives.",
                              url=self.meta["url"] + "#section-two")
        self.assertEqual(first["document_id"], updated["document_id"])
        self.assertFalse(self.corpus.search("moat")["results"])
        self.assertEqual(len(self.corpus.search("incentives")["results"]), 1)
        self.assertEqual(self.corpus.db.execute("SELECT count(*) FROM chunks_fts").fetchone()[0], 1)
        with self.assertRaises(ValueError):
            self.corpus.show(old_id)

    def test_page_context_and_explicit_segment_speaker(self):
        segments = {"segments": [
            {"text": "An introductory passage with context.", "page": 10},
            {"text": "Incentives influence behavior.", "speaker": "Buffett", "page": 11, "section": "Discussion"},
            {"text": "A follow-up passage matters too.", "page": 12}]}
        self.ingest(json.dumps(segments), ".json", speaker="mixed")
        found = self.corpus.search("incentives")["results"][0]
        self.assertEqual(found["speaker"], "Warren Buffett")
        self.assertEqual(found["locator"], {"page": 11, "section": "Discussion"})
        context = self.corpus.show(found["chunk_id"], context=1)["passages"]
        self.assertEqual(len(context), 3)
        self.assertIsNone(context[0]["speaker"])
        self.assertIn("follow-up", context[2]["text"])
        self.assertTrue(found["evidence_eligibility"]["personal_attribution_candidate"])

    def test_author_and_report_speaker_are_not_personal_attribution(self):
        self.ingest("Insurance float supports many operating businesses.", source_type="financial_report",
                    speaker="Buffett", author="Warren Buffett")
        found = self.corpus.search("float")["results"][0]
        self.assertIsNone(found["speaker"])
        self.assertFalse(found["evidence_eligibility"]["personal_attribution_candidate"])
        self.assertFalse(self.corpus.search("float", speaker="Buffett")["results"])
        self.ingest("Psychology helps investors understand incentives.", speaker=None,
                    author="Charlie Munger", url="https://example.test/other")
        self.assertIsNone(self.corpus.search("psychology")["results"][0]["speaker"])
        self.assertIsNone(library.speaker_name("Warren Buffett and Charlie Munger"))

    def test_pdf_extraction_records_real_page_and_rejects_scan(self):
        try:
            from pypdf import PdfWriter
            from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        except ImportError:
            self.skipTest("Optional pypdf backend is not installed")
        source = self.root / "fixture.pdf"
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
            DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        content = DecodedStreamObject()
        content.set_data(b"BT /F1 12 Tf 72 720 Td (A durable moat protects a business.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(content)
        writer.write(source)
        self.corpus.ingest(self.meta, source)
        self.assertEqual(self.corpus.search("moat")["results"][0]["locator"]["page"], 1)
        blank = PdfWriter()
        blank.add_blank_page(width=612, height=792)
        blank.write(source)
        with self.assertRaises(ValueError):
            self.corpus.ingest(dict(self.meta, url="https://example.test/scanned"), source)
        self.assertEqual(self.corpus.stats()["documents"], 1)

    def test_verified_page_ranges_and_explicit_speaker_precedence(self):
        content = json.dumps({"segments": [
            {"text": "Performance table remains unassigned.", "page": 1},
            {"text": "Buffett section discusses business economics.", "page": 2},
            {"text": "Munger section discusses mental models.", "page": 38},
            {"text": "Explicit speaker attribution takes precedence.", "page": 39, "speaker": "Interviewer"},
            {"text": "An unknown quotation remains unassigned.", "page": 42, "speaker": "unknown"}]})
        ranges = [{"from": 2, "to": 37, "speaker": "Buffett"}, {"from": 38, "to": 42, "speaker": "Munger"}]
        meta = {"speaker": "mixed", "speaker_page_ranges": ranges,
                "speaker_page_ranges_url": self.meta["url"], "speaker_page_ranges_sha256": library.digest(content)}
        self.ingest(content, ".json", **meta)
        for query, speaker in [("Performance", None), ("economics", "Warren Buffett"),
                               ("mental", "Charlie Munger"), ("precedence", "Interviewer"), ("quotation", None)]:
            self.assertEqual(self.corpus.search(query)["results"][0]["speaker"], speaker)
        with self.assertRaisesRegex(ValueError, "SHA256 differs"):
            self.ingest(content + " ", ".json", **meta)
        self.assertEqual(self.corpus.stats()["documents"], 1)

    def test_page_ranges_require_valid_nonoverlapping_bounds_and_source_guards(self):
        content = json.dumps([{"text": "A corpus paragraph with page provenance.", "page": 2}])
        good = {"speaker_page_ranges": [{"from": 2, "to": 4, "speaker": "Buffett"}],
                "speaker_page_ranges_url": self.meta["url"], "speaker_page_ranges_sha256": library.digest(content)}
        invalid = [
            {"speaker_page_ranges": [{"from": 1, "to": 3, "speaker": "Buffett"}, {"from": 3, "to": 4, "speaker": "Munger"}]},
            {"speaker_page_ranges": [{"from": 0, "to": 3, "speaker": "Buffett"}]},
            {"speaker_page_ranges": [{"from": 4, "to": 3, "speaker": "Buffett"}]},
            {"speaker_page_ranges": [{"from": True, "to": 3, "speaker": "Buffett"}]},
            {"speaker_page_ranges": [{"from": 1, "to": 3, "speaker": "mixed"}]},
            {"speaker_page_ranges_sha256": "unverified"},
            {"speaker_page_ranges_url": "https://example.test/other"},
        ]
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.ingest(content, ".json", **dict(good, **fields))
        self.assertEqual(self.corpus.stats()["documents"], 0)

    def test_vtt_and_srt_time_locators(self):
        self.ingest("WEBVTT\n\n00:01:02.000 --> 00:01:04.500\n<v Warren Buffett>A competitive moat matters.</v>\n\n00:01:05.000 --> 00:01:07.000\n<v Charlie Munger>Study incentives.</v>\n", ".vtt", speaker="mixed")
        found = self.corpus.search("incentives")["results"][0]
        self.assertEqual(found["speaker"], "Charlie Munger")
        self.assertEqual(found["locator"]["start"], "00:01:05.000")
        self.ingest("1\n00:00:01,200 --> 00:00:04,500\nMargin of safety matters.\n", ".srt",
                    url="https://example.test/srt", transcript_quality="rough")
        rough = self.corpus.search("margin")["results"][0]
        self.assertEqual(rough["locator"]["end"], "00:00:04.500")
        self.assertFalse(rough["evidence_eligibility"]["exact_quote_candidate"])

    def test_chinese_concept_expansion_and_safe_queries(self):
        self.ingest("Stay within your circle of competence. Demand a margin of safety.")
        for query in ["能力圈", "安全边际", 'competence" OR * NEAR(foo) - title:bar']:
            with self.subTest(query=query):
                self.assertTrue(self.corpus.search(query)["results"])
        self.assertFalse(self.corpus.search("*** !!!")["results"])
        self.assertEqual(self.corpus.stats()["documents"], 1)

    def test_search_filters(self):
        self.ingest("The moat is an economic advantage.")
        self.ingest("A moat can be destroyed by competition.", url="https://example.test/b",
                    date="2010-05-01", speaker="Buffett", primary_status="secondary")
        results = self.corpus.search("moat", speaker="芒格", year_from=1999, year_to=2001,
                                     primary_status="primary", source_type="speech")["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["provenance"]["date_precision"], "year")
        self.assertFalse(self.corpus.search("moat", year_from=2001, year_to=2009)["results"])
        secondary = self.corpus.search("moat", speaker="Buffett")["results"][0]
        self.assertFalse(secondary["evidence_eligibility"]["primary_evidence"])

    def test_stats_report_series_dates_and_evidence_coverage(self):
        self.assertEqual(self.corpus.stats()["date_range"], {"earliest": None, "latest": None, "unknown_documents": 0})
        self.ingest("One corpus document with clear provenance.", series="wesco-letters")
        self.ingest("A second document whose date is unknown.", url="https://example.test/undated", date=None,
                    series="wesco-letters", primary_status="secondary")
        self.ingest("A recent document from a separate series.", url="https://example.test/latest", date="2024-02-24")
        stats = self.corpus.stats()
        self.assertEqual(stats["date_range"], {"earliest": "2000", "latest": "2024-02-24", "unknown_documents": 1})
        self.assertEqual(stats["by_series"], [{"series": "unspecified", "documents": 1}, {"series": "wesco-letters", "documents": 2}])
        self.assertEqual(stats["by_primary_status"], [{"primary_status": "primary", "documents": 2}, {"primary_status": "secondary", "documents": 1}])

    def test_failed_update_retains_previous_good_document_and_logs_failure(self):
        self.ingest("A durable moat protects a company.")
        with self.assertRaises(json.JSONDecodeError):
            self.ingest('{"segments":', ".json")
        self.assertEqual(self.corpus.stats()["documents"], 1)
        self.assertTrue(self.corpus.search("moat")["results"])
        self.assertEqual(len(self.corpus.stats()["recent_failures"]), 1)

    def test_empty_malformed_subtitle_and_html_traps_are_not_indexed(self):
        for content, suffix in [("", ".txt"), ("not a subtitle file", ".vtt"),
                                ("<html><h1>Access denied</h1><p>Verify you are human</p></html>", ".html"),
                                ("<html>A downloaded error.</html>", ".pdf")]:
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                self.ingest(content, suffix)
        self.assertEqual(self.corpus.stats()["documents"], 0)
        self.assertEqual(len(self.corpus.stats()["recent_failures"]), 4)

    def test_html_paragraphs_without_scripts(self):
        self.ingest("<html><body><script>secret bogus words</script><p>First meaningful paragraph.</p><p>Second &amp; final paragraph.</p></body></html>", ".html")
        self.assertEqual(self.corpus.stats()["chunks"], 2)
        self.assertFalse(self.corpus.search("secret")["results"])
        self.assertIn("Second & final", self.corpus.search("Second")["results"][0]["snippet"])

    def test_fetch_decoded_payload_and_failures(self):
        with mock.patch.object(library, "download", return_value=(b"A moat protects a business.", "text/plain", "https://example.test/final")):
            self.corpus.fetch(self.meta)
        self.assertEqual(self.corpus.search("moat")["results"][0]["provenance"]["resolved_url"], "https://example.test/final")
        with mock.patch.object(library, "download", return_value=(b"<html>Access denied</html>", "text/html", "https://example.test/final")):
            with self.assertRaises(ValueError):
                self.corpus.fetch(dict(self.meta, url="https://example.test/report.pdf"))
        self.assertEqual(self.corpus.stats()["documents"], 1)
        self.assertFalse(list((self.root / "corpus").glob("tmp*")))

    def test_download_compression_and_size_boundaries(self):
        payload = b"A reliable evidence corpus needs exact source bytes."
        self.assertEqual(library.decode_transfer(gzip.compress(payload), "gzip"), payload)
        with mock.patch.object(library, "MAX_BYTES", 10), self.assertRaises(ValueError):
            library.decode_transfer(gzip.compress(payload), "gzip")
        with self.assertRaises(ValueError):
            library.decode_transfer(b"xxx", "mystery")
        with self.assertRaises(ValueError):
            library.download("https://example.test/video.mp4")
        with self.assertRaises(ValueError):
            library.download("file:///etc/passwd")
        with self.assertRaises(ValueError):
            library.canonical_url("https://user:password@example.test/private")

    def test_cli_works_and_errors_are_nonzero(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = library.main(["--library", str(self.root / "corpus"), "stats"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["documents"], 0)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(library.main(["--library", str(self.root / "corpus"), "show", "missing"]), 1)


if __name__ == "__main__":
    unittest.main()
