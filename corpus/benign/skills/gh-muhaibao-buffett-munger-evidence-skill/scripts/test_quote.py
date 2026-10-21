"""Quotes must be complete sentences: a fragment can drop the condition or negation that changes the meaning."""
import json
from pathlib import Path
import tempfile
import unittest

import library
import quote
import retrieve


class QuoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.writer = library.Library(self.root / "library")
        self.n = 0

    def tearDown(self):
        self.writer.close()
        self.temp.cleanup()

    def doc(self, segments, **meta):
        self.n += 1
        path = self.root / f"{self.n}.json"
        path.write_text(json.dumps({"segments": segments}))
        base = {"id": f"d{self.n}", "title": "Source", "date": "1996", "speaker": "mixed", "url": f"https://example.test/{self.n}",
                "source_type": "annual_meeting", "primary_status": "primary", "transcript_quality": "official"}
        base.update(meta)
        self.writer.ingest(base, path)
        return [r["id"] for r in self.writer.db.execute("SELECT id FROM chunks WHERE document_id=? ORDER BY ordinal", (base["id"],))]

    def q(self, chunk_id, match, **kw):
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            return quote.quote(corpus, chunk_id, match, **kw)
        finally:
            corpus.close()

    def test_mid_sentence_phrase_returns_the_whole_sentence_with_its_condition(self):
        # Quoting only "buy a meaningful amount" would hide the condition that comes first.
        [cid] = self.doc([{"text": "Most investors should own index funds. When you see one that qualifies, you should buy a meaningful amount of stock. Patience matters.",
                           "speaker": "Buffett"}])
        r = self.q(cid, "buy a meaningful amount")
        self.assertEqual(r["quote"], "When you see one that qualifies, you should buy a meaningful amount of stock.")
        self.assertEqual(r["sentences"], 1)

    def test_abbreviations_and_initials_do_not_cut_a_sentence(self):
        [cid] = self.doc([{"text": "Mr. Graham told Charles T. Munger that the U.S. market would recover. It did.", "speaker": "Buffett"}])
        r = self.q(cid, "would recover")
        self.assertEqual(r["quote"], "Mr. Graham told Charles T. Munger that the U.S. market would recover.")

    def test_sentence_crossing_a_chunk_boundary_is_joined_for_the_same_speaker_only(self):
        ids = self.doc([{"text": "WARREN BUFFETT: We never want to depend on", "speaker": "Buffett"},
                        {"text": "the kindness of strangers. That is rule one.", "speaker": "Buffett"},
                        {"text": "BECKY QUICK: Thank you.", "speaker": "Becky Quick"}])
        r = self.q(ids[1], "kindness of strangers")
        self.assertEqual(r["quote"], "We never want to depend on the kindness of strangers.")  # label removed, chunks joined
        self.assertEqual(r["chunk_ids"], ids[:2])
        self.assertNotIn("Thank you", self.q(ids[1], "rule one", after=1)["quote"])  # another speaker never joins

    def test_chinese_punctuation_and_context_sentences(self):
        [cid] = self.doc([{"text": "反过来想，总是反过来想。很多难题只有倒过来才能解决。这是雅可比的话。", "speaker": None}],
                         source_type="translation", primary_status="secondary", transcript_quality="edited", translation_of="talk-four")
        r = self.q(cid, "倒过来", before=1)
        self.assertEqual(r["quote"], "反过来想，总是反过来想。很多难题只有倒过来才能解决。")
        self.assertTrue(any("Translation" in n for n in r["notes"]))  # translations must be labelled 译文

    def test_unknown_phrase_fails_loudly(self):
        [cid] = self.doc([{"text": "Price is what you pay.", "speaker": "Buffett"}])
        with self.assertRaisesRegex(ValueError, "not found"):
            self.q(cid, "value is what you get")


if __name__ == "__main__":
    unittest.main()
