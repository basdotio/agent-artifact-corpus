"""Invariants for attribution, Q&A units, typed Wiki pages and blind evaluation.

Each test states why the behaviour matters for answering "as Buffett/Munger would":
wrong attribution or a leaked gold answer makes the result look better than it is.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import attribution
import evaluate
import library
import qa
import retrieve
import wiki


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.writer = library.Library(self.root / "library")
        self.counter = 0

    def tearDown(self):
        self.writer.close()
        self.temp.cleanup()

    def ingest_segments(self, segments, **meta):
        self.counter += 1
        path = self.root / f"{self.counter}.json"
        path.write_text(json.dumps({"segments": segments}))
        base = {"id": f"doc-{self.counter}", "title": "Annual meeting", "date": "2005", "speaker": "mixed",
                "url": f"https://example.test/{self.counter}", "source_type": "annual_meeting",
                "primary_status": "primary", "transcript_quality": "official"}
        base.update(meta)
        self.writer.ingest(base, path)
        return base["id"]

    def chunk(self, document_id, ordinal=0):
        return self.writer.db.execute("SELECT id FROM chunks WHERE document_id=? AND ordinal=?",
                                      (document_id, ordinal)).fetchone()[0]

    def search(self, query, **kwargs):
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            return retrieve.search(corpus, query, self.root / "index", self.root / "models",
                                   mode="lexical", rerank=False, **kwargs)
        finally:
            corpus.close()


class AttributionTests(Fixture):
    def test_transcript_typo_does_not_hide_buffett_answer(self):
        # CNBC transcripts print "WARREN BUFEFTT"; a strict filter used to drop these answers silently.
        doc = self.ingest_segments([{"text": "Float is a wonderful asset.", "speaker": "WARREN BUFEFTT"}])
        result = self.search("float", speaker="Buffett")
        self.assertEqual([r["chunk_id"] for r in result["results"]], [self.chunk(doc)])
        self.assertEqual(result["results"][0]["attribution"],
                         {"basis": "chunk-speaker", "person": "Warren Buffett", "raw_label": "WARREN BUFEFTT"})

    def test_other_people_named_buffett_or_warren_are_never_attributed(self):
        # Jimmy Buffett performed at meetings and a Daily Journal questioner was labelled WARREN.
        self.ingest_segments([{"text": "Float is a song lyric here.", "speaker": "JIMMY BUFFETT"}])
        self.ingest_segments([{"text": "Float question from the floor.", "speaker": "Participant (source label WARREN)"}])
        self.assertEqual(self.search("float", speaker="Buffett")["results"], [])

    def test_author_level_uses_only_reviewed_documents_and_carries_caution(self):
        # Unlabelled Wesco notes are Munger's meetings but paraphrased; the basis must travel with the passage.
        notes = self.ingest_segments([{"text": "Incentives drive the savings and loan mess."}], source_type="meeting_notes")
        other = self.ingest_segments([{"text": "Incentives drive an unrelated speaker."}], source_type="meeting_notes")
        reviewed = {"documents": {notes: {"person": "Charlie Munger", "basis": "meeting-notes-principal",
                                          "caution": "paraphrase", "title": "notes"}}}
        map_path = self.root / "map.json"
        map_path.write_text(json.dumps(reviewed))
        with patch.object(attribution, "MAP_PATH", map_path):
            strict = self.search("incentives", speaker="Munger")
            author = self.search("incentives", speaker="Munger", attribution_mode="author")
        self.assertEqual(strict["results"], [])
        self.assertEqual([r["document_id"] for r in author["results"]], [notes])
        self.assertNotIn(other, [r["document_id"] for r in author["results"]])
        self.assertEqual(author["results"][0]["attribution"]["basis"], "meeting-notes-principal")
        self.assertEqual(author["results"][0]["attribution"]["caution"], "paraphrase")
        # The corpus label itself is untouched: attribution is a query-time reading, not a rewrite.
        self.assertIsNone(author["results"][0]["speaker"])

    def test_shipped_attribution_map_only_names_documents_a_plain_fetch_reproduces(self):
        # Entries keyed to ids of hand-staged or private batches can never match a user's library;
        # library.py fetch of the recorded url (no custom id) must yield exactly the key.
        entries = attribution.load_map()
        self.assertTrue(entries)
        for document_id, entry in entries.items():
            with self.subTest(document_id=document_id):
                self.assertEqual(library.normalize_metadata({"title": "t", "url": entry["url"]})["id"], document_id)
                self.assertIn(entry["person"], attribution.PRINCIPALS)
                self.assertTrue(entry["basis"] and entry["caution"])

    def test_semantic_matcher_applies_same_attribution_rules(self):
        rows = [{"document_id": "notes", "speaker": None, "year": 2005, "source_type": "meeting_notes", "primary_status": "secondary"},
                {"document_id": "other", "speaker": None, "year": 2005, "source_type": "meeting_notes", "primary_status": "secondary"},
                {"document_id": "m", "speaker": "CHALIE MUNGER", "year": 1997, "source_type": "annual_meeting", "primary_status": "primary"}]
        with patch.object(attribution, "author_documents", return_value={"notes": {}}):
            matcher = retrieve.make_matcher(speaker="Munger", attribution_mode="author")
        self.assertEqual([r["document_id"] for r in rows if matcher(r)], ["notes", "m"])
        strict = retrieve.make_matcher(speaker="Munger")
        self.assertEqual([r["document_id"] for r in rows if strict(r)], ["m"])

    def test_excluded_document_cannot_leak_into_results(self):
        # Blind evaluation depends on the held-out meeting being unreachable.
        held = self.ingest_segments([{"text": "Moat answer.", "speaker": "Buffett"}])
        kept = self.ingest_segments([{"text": "Moat answer elsewhere.", "speaker": "Buffett"}])
        result = self.search("moat", speaker="Buffett", exclude_documents=[held])
        self.assertEqual({r["document_id"] for r in result["results"]}, {kept})
        rows = [{"document_id": held, "speaker": "Warren Buffett", "year": 2005, "source_type": "x", "primary_status": "y"}]
        self.assertFalse(retrieve.make_matcher(exclude_documents=[held])(rows[0]))


class TranslationTests(Fixture):
    def test_translations_are_excluded_unless_requested(self):
        # A Chinese question would otherwise match Chinese translations first and crowd out the English originals.
        original = self.ingest_segments([{"text": "Invert, always invert.", "speaker": "Munger"}], source_type="speech")
        translated = self.ingest_segments([{"text": "Invert always invert 反过来想", "speaker": None}], source_type="translation",
                                          primary_status="secondary", language="zh")
        default = self.search("invert")
        included = self.search("invert", include_translations=True)
        explicit = self.search("invert", source_type="translation")
        self.assertEqual({r["document_id"] for r in default["results"]}, {original})
        self.assertEqual({r["document_id"] for r in included["results"]}, {original, translated})
        self.assertEqual({r["document_id"] for r in explicit["results"]}, {translated})
        row = {"document_id": translated, "speaker": None, "year": 2005, "source_type": "translation", "primary_status": "secondary"}
        self.assertFalse(retrieve.make_matcher()(row))
        self.assertTrue(retrieve.make_matcher(include_translations=True)(row))


class WikiTypeTests(Fixture):
    def write_page(self, chunk_ids, page_type="case", body="一项案例归纳。[E1]", name=None):
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            entries = wiki.evidence_entries(corpus, chunk_ids)
        finally:
            corpus.close()
        for entry in entries:
            entry.pop("_readable")
        meta = {"kind": "synthesis", "title": "喜诗糖果", "subjects": ["Warren Buffett"], "reviewed_on": "2026-10-09",
                "page_type": page_type, "summary": "定价权案例", "keywords": ["See's"], "evidence": entries}
        page = self.root / "wiki" / (name or f"{page_type}.md")
        page.parent.mkdir(exist_ok=True)
        page.write_text("---\n" + json.dumps(meta, ensure_ascii=False) + "\n---\n# 喜诗糖果\n" + body + "\n")
        return page

    def test_evidence_helper_produces_records_the_checker_accepts(self):
        # Hand-copied hashes were the main source of broken pages; the helper must match the validator exactly.
        doc = self.ingest_segments([{"text": "See's raised prices every year.", "speaker": "Buffett"}])
        page = self.write_page([self.chunk(doc)])
        result = wiki.validate_page(self.writer, page)
        self.assertEqual(result["status"], "source-links-current", result["errors"])
        self.assertEqual(result["page_type"], "case")

    def test_unknown_page_type_is_rejected_and_type_filter_applies(self):
        doc = self.ingest_segments([{"text": "See's raised prices every year.", "speaker": "Buffett"}])
        case = self.write_page([self.chunk(doc)], "case")
        bad = self.write_page([self.chunk(doc)], "case", name="bad.md")
        bad.write_text(bad.read_text().replace('"page_type": "case"', '"page_type": "anecdote"'))
        self.assertEqual(wiki.validate_page(self.writer, bad)["status"], "needs-review")
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            only_mistakes = wiki.search_pages(corpus, case.parent, "喜诗", page_types=["mistake"])
            cases = wiki.search_pages(corpus, case.parent, "喜诗", page_types=["case"])
        finally:
            corpus.close()
        self.assertEqual(only_mistakes["results"], [])
        self.assertEqual([Path(r["path"]).name for r in cases["results"]], ["case.md"])

    def test_pages_without_page_type_remain_valid_concepts(self):
        # The six pilot pages predate page_type and must stay valid without it.
        doc = self.ingest_segments([{"text": "A durable advantage.", "speaker": "Buffett"}])
        page = self.write_page([self.chunk(doc)])
        page.write_text(page.read_text().replace(', "page_type": "case"', ""))
        result = wiki.validate_page(self.writer, page)
        self.assertEqual((result["status"], result["page_type"]), ("source-links-current", "concept"))


MEETING = [
    {"text": "AUDIENCE MEMBER: How do you think about airlines as investments?", "speaker": "AUDIENCE MEMBER", "section": "1. Airlines"},
    {"text": "WARREN BUFFETT: Airlines have been a death trap for investors. Capital intensive, commodity pricing.", "speaker": "Warren Buffett", "section": "1. Airlines"},
    {"text": "CHARLIE MUNGER: I have nothing to add.", "speaker": "Charlie Munger", "section": "1. Airlines"},
    {"text": "BECKY QUICK: Thanks.", "speaker": "BECKY QUICK", "section": "1. Airlines"},
    {"text": "BECKY QUICK: This one is for Greg. How will the energy business handle wildfire liability?", "speaker": "BECKY QUICK", "section": "2. Utilities"},
    {"text": "GREG ABEL: Wildfire risk is changing the utility model and we are working with regulators on it.", "speaker": "GREG ABEL", "section": "2. Utilities"},
    {"text": "WARREN BUFFETT: We may not know the answer for years; the utility compact is under strain.", "speaker": "Warren Buffett", "section": "2. Utilities"},
]


class QATests(Fixture):
    def test_units_follow_questions_and_keep_responders_inside_answers(self):
        # A unit must pair a question with the people who answered it; moderators' "Thanks." is not a new question.
        doc = self.ingest_segments(MEETING)
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            units = qa.build_units(corpus)
        finally:
            corpus.close()
        self.assertEqual([u["id"] for u in units], [f"{doc}#0", f"{doc}#1"])
        first, second = units
        self.assertEqual(first["answer"]["first_responder"], "Warren Buffett")
        self.assertTrue(first["flags"]["munger_nothing_to_add"])
        self.assertEqual(first["answer"]["words_by"]["Charlie Munger"], 5)
        self.assertEqual(second["answer"]["first_responder"], "GREG ABEL")
        self.assertGreater(second["answer"]["words_by"]["Warren Buffett"], 0)
        self.assertTrue(second["question"]["text"].startswith("This one is for Greg"))

    def test_transcripts_reordered_by_speaker_are_not_paired(self):
        # A by-speaker transcript puts all questions apart from answers; adjacency would pair the wrong ones.
        self.ingest_segments(MEETING, qa_segmentable=False)
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            self.assertEqual(qa.build_units(corpus), [])
        finally:
            corpus.close()

    def test_units_go_stale_when_corpus_changes_and_exclusion_holds_out_meetings(self):
        doc = self.ingest_segments(MEETING)
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            qa.build(corpus, self.root / "models", embed=False)
            self.assertTrue(qa.status(corpus)["ready"])
            hit = qa.search(corpus, "airlines investments", self.root / "models", rerank=False)
            held = qa.search(corpus, "airlines investments", self.root / "models", rerank=False, exclude_documents=[doc])
        finally:
            corpus.close()
        self.assertEqual(hit["results"][0]["id"], f"{doc}#0")
        self.assertEqual(hit["mode_used"], "lexical")
        self.assertEqual(held["results"], [])
        self.ingest_segments(MEETING)
        corpus = retrieve.open_corpus(self.writer.root)
        try:
            self.assertFalse(qa.status(corpus)["ready"])
        finally:
            corpus.close()


def unit(doc, i, year, munger_words=0, question="Why do you avoid businesses that need constant reinvestment to stay competitive?"):
    words_by = {"Warren Buffett": 120}
    turns = [{"speaker": "Warren Buffett", "person": "Warren Buffett", "role": "principal", "words": 120,
              "text": "GOLD-BUFFETT-ANSWER " * 3, "chunk_ids": ["c"]}]
    if munger_words:
        words_by["Charlie Munger"] = munger_words
        turns.append({"speaker": "Charlie Munger", "person": "Charlie Munger", "role": "principal",
                      "words": munger_words, "text": "GOLD-MUNGER-ANSWER", "chunk_ids": ["d"]})
    return {"id": f"{doc}#{i}", "document_id": doc, "title": "t", "date": str(year), "year": year,
            "source_type": "annual_meeting", "sections": ["7. Munger: textile mills were a mistake"],
            "question": {"text": question, "speakers": ["AUDIENCE MEMBER"], "words": len(question.split()), "chunk_ids": ["q"]},
            "answer": {"turns": turns, "first_responder": "Warren Buffett", "words_by": words_by},
            "flags": {"has_question": True, "has_principal_answer": True, "procedural": False,
                      "decline_markers": [], "munger_nothing_to_add": False}}


class EvaluationTests(unittest.TestCase):
    def records(self):
        return [unit(f"m{year}-{k}", i, year, munger_words=60 if i % 2 else 0)
                for year in (1996, 2004, 2013, 2021) for k in range(3) for i in range(4)]

    def test_blind_questions_carry_no_gold_text_or_section_titles(self):
        # Section titles such as "textile mills were a mistake" give the answer away.
        chosen = evaluate.sample(self.records(), n=8)
        view = json.dumps([evaluate.question_view(r) for r in chosen])
        self.assertNotIn("GOLD-", view)
        self.assertNotIn("textile mills", view)
        # Who answered is scored (speaker_match), so revealing it would inflate the score.
        self.assertNotIn("answered_by", view)

    def test_sample_is_stratified_capped_per_session_and_time_bounded(self):
        chosen = evaluate.sample(self.records(), n=8)
        self.assertEqual(len(chosen), 8)
        self.assertEqual({r["year"] // 10 for r in chosen}, {199, 200, 201, 202})
        per_doc = {}
        for r in chosen:
            per_doc[r["document_id"]] = per_doc.get(r["document_id"], 0) + 1
            view = evaluate.question_view(r)
            self.assertEqual(view["exclusions"], {"exclude_documents": [r["document_id"]], "year_to": r["year"] - 1})
        self.assertLessEqual(max(per_doc.values()), 2)
        self.assertEqual(chosen, evaluate.sample(self.records(), n=8))
        # A unit used in an earlier batch is development data and must not return as held-out.
        again = evaluate.sample(self.records(), n=8, seed=7, exclude_ids=[r["id"] for r in chosen])
        self.assertFalse({r["id"] for r in again} & {r["id"] for r in chosen})

    def test_mechanical_metrics_compare_chinese_answers_with_english_gold(self):
        gold = evaluate.gold_view(unit("m", 0, 2004, munger_words=40))
        answer = {"id": gold["id"], "buffett": "伯" * 192, "munger": "", "basket": "too-hard"}
        metrics = evaluate.mechanical(gold, answer)
        self.assertEqual(metrics["buffett"]["answer_size"], 120)
        self.assertFalse(metrics["speaker_match"])  # Munger spoke in the real answer but not in ours
        self.assertTrue(metrics["decline_marker"]["answer"])

    def test_invalid_judgment_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "j.jsonl"
            path.write_text(json.dumps({"id": "a", "direction": "mostly", "core_reason": "same",
                                        "decline_behaviour": "n/a", "fabrication": "none"}) + "\n")
            with self.assertRaisesRegex(ValueError, "direction"):
                evaluate.summarize(path)


if __name__ == "__main__":
    unittest.main()
