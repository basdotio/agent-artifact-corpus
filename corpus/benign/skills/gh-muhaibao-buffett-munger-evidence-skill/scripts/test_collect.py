"""Offline discovery regressions; no live requests or guessed source URLs."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import collect
from library import Library


class DiscoveryTests(unittest.TestCase):
    def test_nested_year_label_and_future_buffett_authorship(self):
        raw = b'<a href="2024ltr.pdf">20<span>24</span></a><a href="2025ltr.pdf">2025</a><a href="other.pdf">2024 translation</a>'
        rows = collect.candidates("buffett-letters", raw, collect.INDEXES["buffett-letters"])
        self.assertEqual(rows, [{"year": 2024, "url": "https://www.berkshirehathaway.com/letters/2024ltr.pdf", "landing_page": False}])

    def test_official_hosts_only_and_no_credentials_or_fragment_duplicates(self):
        raw = b'<a href="https://evil.test/2024.pdf">2024</a><a href="https://www.berkshirehathaway.com.evil.test/a">2024</a><a href="javascript:bad()">2024</a><a href="https://user:pass@www.berkshirehathaway.com/a">2024</a><a href="#local">2024</a><a href="http://www.berkshirehathaway.com/letters/2024ltr.pdf#letter">2024</a><a href="2024ltr.pdf">2024</a>'
        rows = collect.candidates("buffett-letters", raw, collect.INDEXES["buffett-letters"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "https://www.berkshirehathaway.com/letters/2024ltr.pdf")

    def test_ambiguous_year_and_conflicting_filename_fail(self):
        for raw in [b'<a href="a.pdf">2024</a><a href="b.pdf">2024</a>',
                    b'<a href="2023ltr.pdf">2024</a>']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                collect.candidates("buffett-letters", raw, collect.INDEXES["buffett-letters"])
        self.assertEqual(collect.candidates("buffett-letters", b'<a href="2024ltr.pdf">no year</a>', collect.INDEXES["buffett-letters"]), [])

    def test_reports_require_matching_landing_year_and_complete_pdf(self):
        raw = b'<a href="2024ar/linksannual24.html">2024</a><a href="2023ar/linksannual24.html">broken</a><a href="2024ar/linksannual24.html#top">2024 duplicate</a>'
        rows = collect.candidates("reports", raw, collect.INDEXES["reports"])
        self.assertEqual(len(rows), 1)
        landing = rows[0]["url"]
        html = b'<a href="2023ar.pdf">Prior Annual Report</a><a href="2024ltr.pdf">Chairman Letter</a><a href="2024ar.pdf">Annual Report</a><a href="2024ar.pdf#p2">Same PDF</a>'
        self.assertEqual(collect.report_pdf(html, landing), "https://www.berkshirehathaway.com/2024ar/2024ar.pdf")
        with self.assertRaises(ValueError):
            collect.report_pdf(b'<a href="2023ar.pdf">Annual Report</a>', landing)
        with self.assertRaises(ValueError):
            collect.report_pdf(b'<a href="other.pdf">Annual Report Letter</a>', landing)
        with self.assertRaises(ValueError):
            collect.report_pdf(b'<a href="a.pdf">Complete Annual Report</a><a href="b.pdf">Annual Report</a>', landing)

    def test_wesco_and_report_attribution_metadata(self):
        wesco = collect.document_metadata("wesco-letters", 2007, "https://example.test/w", "https://example.test/index")
        report = collect.document_metadata("reports", 2024, "https://example.test/r", "https://example.test/index")
        self.assertEqual(wesco["speaker"], "Charlie Munger")
        self.assertIsNone(report["speaker"])
        self.assertEqual(report["author"], "Berkshire Hathaway Inc.")
        self.assertEqual(report["date_precision"], "year")
        self.assertIsNone(report["publication_date"])

    def test_2014_mixed_authors_have_pdf_identity_guard(self):
        url = "https://www.berkshirehathaway.com/letters/2014ltr.pdf"
        meta = collect.document_metadata("buffett-letters", 2014, url, collect.INDEXES["buffett-letters"])
        self.assertEqual(meta["speaker"], "mixed")
        self.assertEqual(meta["speaker_page_ranges"][1], {"from": 38, "to": 42, "speaker": "Charlie Munger"})
        self.assertEqual(meta["speaker_page_ranges_url"], url)
        self.assertEqual(meta["speaker_page_ranges_sha256"], "dd00248b32ad1f67234bb4dba66755bf45a623bd94e40465a2a88707b73cd426")
        other = collect.document_metadata("buffett-letters", 2014, "https://example.test/other.pdf", collect.INDEXES["buffett-letters"])
        self.assertEqual(other["speaker"], "mixed")
        self.assertNotIn("speaker_page_ranges", other)

    def test_letter_landing_resolves_actual_nonstandard_pdf_link(self):
        raw = b"<html><h1>--IMPORTANT NOTE--</h1><p>The 1999 Chairman's Letter is being presented in HTML and PDF format.</p><a href='https://www.adobe.com/reader.pdf'>Reader</a><a href='final1999pdf.pdf'>1999 Chairman's Letter (PDF)</a><a href='1999text.html'>HTML version</a></html>"
        self.assertEqual(collect.letter_pdf(raw, "https://www.berkshirehathaway.com/letters/1999.html", 1999), "https://www.berkshirehathaway.com/letters/final1999pdf.pdf")
        for bad in [b'<p>IMPORTANT NOTE: The letter is in PDF.</p>',
                    b'<a href="2000pdf.pdf">2000 Chairman Letter</a>',
                    b'<a href="1999pdf.pdf">1999 Letter</a><a href="final1999pdf.pdf">1999 Letter</a>']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                collect.letter_pdf(bad, "https://www.berkshirehathaway.com/letters/1999.html", 1999)
        self.assertIsNone(collect.letter_pdf(b'<p>' + b'A meaningful original letter paragraph. ' * 70 + b'</p>', "https://www.berkshirehathaway.com/letters/1977.html", 1977))

    def test_dry_run_resolves_landing_and_records_pdf_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            index = collect.INDEXES["buffett-letters"]
            landing = "https://www.berkshirehathaway.com/letters/1999.html"
            responses = [(b'<a href="1999.html">1999</a>', "text/html", index),
                         (b'<a href="final1999pdf.pdf">1999 Chairman Letter (PDF)</a>', "text/html", landing)]
            with mock.patch.object(collect, "download", side_effect=responses) as download, contextlib.redirect_stdout(io.StringIO()):
                result = collect.main(["--library", directory, "--kind", "buffett-letters", "--dry-run"])
            self.assertEqual(result, 0)
            self.assertEqual(download.call_count, 2)
            manifest = json.loads((Path(directory) / "discovery/buffett-letters-manifest.json").read_text())
            doc = manifest["documents"][0]
            self.assertEqual(doc["url"], "https://www.berkshirehathaway.com/letters/final1999pdf.pdf")
            self.assertEqual(doc["source_url"], doc["url"])
            self.assertEqual(doc["discovery_landing_url"], landing)
            corpus = Library(directory)
            self.assertEqual(corpus.stats()["documents"], 0)
            corpus.close()

    def test_full_html_download_is_reused_and_index_failure_is_logged(self):
        with tempfile.TemporaryDirectory() as directory:
            index = collect.INDEXES["buffett-letters"]
            original = b'<p>' + b'A moat supports long term business durability. ' * 70 + b'</p>'
            responses = [(b'<a href="1977.html">1977</a>', "text/html", index),
                         (original, "text/html", "https://www.berkshirehathaway.com/letters/1977.html")]
            with mock.patch.object(collect, "download", side_effect=responses) as download, mock.patch.object(collect.time, "sleep"), contextlib.redirect_stdout(io.StringIO()):
                result = collect.main(["--library", directory, "--kind", "buffett-letters"])
            self.assertEqual(result, 0)
            self.assertEqual(download.call_count, 2)
            corpus = Library(directory)
            self.assertEqual(corpus.stats()["documents"], 1)
            corpus.close()
            with mock.patch.object(collect, "download", return_value=(b'<html>No valid index links</html>', "text/html", index)), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(collect.main(["--library", directory, "--kind", "buffett-letters"]), 1)
            corpus = Library(directory)
            self.assertEqual(corpus.stats()["recent_failures"][0]["operation"], "discovery")
            self.assertEqual(corpus.stats()["documents"], 1)
            corpus.close()


if __name__ == "__main__":
    unittest.main()
