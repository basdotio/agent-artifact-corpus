#!/usr/bin/env python3
"""Tests for gavel.py. Run: python3 test_gavel.py   (standard library only, no network, temp folders only)"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gavel  # noqa: E402

PRETRIAL = {
    "motion": "Resolved: the team should ship the beta on Friday.",
    "standard": "preponderance",
    "hypotheses": [{"id": "H1", "text": "Friday is right"}, {"id": "H2", "text": "Wait a week"},
                   {"id": "H3", "text": "The beta is the wrong next step"}],
    "criteria": [{"id": "C1", "name": "Risk", "weight": 3, "question": "What breaks?"},
                 {"id": "C2", "name": "Value", "weight": 2, "question": "Who gains?"}],
    "seats": [{"seat": "engineer", "question": "Will it hold?"},
              {"seat": "designer", "question": "Is it usable?"},
              {"seat": "premortem", "question": "It failed. Why?", "premortem": True}],
}


def ballot(seat, verdict="adopt", prob=70, conf="medium", claims=("F1",), favors="for", grade="plausible", **extra):
    b = {"seat": seat, "verdict": verdict, "probability": prob, "confidence": conf,
         "findings": [{"claim": c, "text": f"point {c}", "grade": grade, "favors": favors} for c in claims],
         "scores": {"C1": 3, "C2": 4}, "decisive": "the main point", "change_my_mind": "a failed test",
         "conditions": ["a condition"] if verdict == "adopt_with_conditions" else [], "objection": None}
    b.update(extra)
    return b


class CaseTest(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.case = os.path.join(self.base, "case")
        os.makedirs(os.path.join(self.case, "ballots", "round1"))
        self.put("pretrial.json", json.dumps(PRETRIAL))
        self.put("case.md", "# Case\n\nThe facts.")

    def tearDown(self):
        shutil.rmtree(self.base)

    def put(self, rel, text):
        path = os.path.join(self.case, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def vote(self, rnd, b):
        self.put(f"ballots/round{rnd}/{gavel.seat_file(b['seat'])}", json.dumps(b))

    def speeches(self, n_open=100, n_reb=50, rebuttals=True):
        self.put("opening-for.md", "word " * n_open)
        self.put("opening-against.md", "word " * n_open)
        if rebuttals:
            self.put("rebuttal-for.md", "word " * n_reb)
            self.put("rebuttal-against.md", "word " * n_reb)

    def assertFix(self, fn, *needles):
        with self.assertRaises(gavel.CaseError) as cm:
            fn()
        joined = " | ".join(cm.exception.problems)
        for needle in needles:
            self.assertIn(needle, joined)


class TestNew(unittest.TestCase):
    def test_new_makes_a_case_folder_and_never_overwrites(self):
        base = tempfile.mkdtemp()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gavel.main(["new", "Ship it?", "--dir", base]), 0)
                self.assertEqual(gavel.main(["new", "Ship it?", "--dir", base]), 0)
            names = sorted(n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))
            self.assertEqual(len(names), 2)
            self.assertTrue(names[1].endswith("-2"))
            self.assertTrue(os.path.isdir(os.path.join(base, names[0], "ballots", "round1")))
        finally:
            shutil.rmtree(base)


class TestSetup(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.base)

    def new(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = gavel.main(["new", "Should we ship?", "--dir", self.base, *args])
        return code, out.getvalue().splitlines()

    def test_defaults_are_a_strong_judge_and_a_tough_prosecution(self):
        s = gavel.build_setup("Ship?")
        self.assertEqual(s["models"], {"judge": "opus", "defense": "sonnet", "prosecution": "sonnet", "jury": "sonnet"})
        self.assertEqual((s["opposition"], s["jurors"], s["seats"]), ("tough", 5, None))

    def test_seats_take_custom_people_and_per_seat_models(self):
        seats = gavel.parse_seats("engineer, designer: opus, a retired airline pilot")
        self.assertEqual([x["seat"] for x in seats], ["engineer", "designer", "a retired airline pilot", "premortem"])
        self.assertEqual(seats[1]["model"], "opus")
        setup = gavel.build_setup("Ship?", seats=seats, models={"jury": "haiku"})
        self.assertEqual(setup["jurors"], 4)
        self.assertEqual(gavel.seat_model(setup, "designer"), "opus")
        self.assertEqual(gavel.seat_model(setup, "engineer"), "haiku")

    def test_bad_choices_are_all_named(self):
        with self.assertRaises(gavel.CaseError) as cm:
            gavel.build_setup("Ship?", opposition="savage", seats=gavel.parse_seats("engineer"),
                              models={"judge": "gpt"})
        joined = " | ".join(cm.exception.problems)
        for needle in ("opposition", "model for judge", "3 to 8 seats"):
            self.assertIn(needle, joined)

    def test_case_folder_holds_the_setup_and_the_choices_are_remembered(self):
        code, lines = self.new("--opposition", "ruthless", "--judge", "fable", "--jury", "haiku")
        self.assertEqual(code, 0)
        setup = json.loads(gavel.read(os.path.join(lines[0], "setup.json")))
        self.assertEqual((setup["opposition"], setup["models"]["judge"]), ("ruthless", "fable"))
        self.assertIn("judge fable", lines[1])
        code, lines = self.new("--last", "--defense", "opus")
        setup = json.loads(gavel.read(os.path.join(lines[0], "setup.json")))
        self.assertEqual(setup["opposition"], "ruthless")         # remembered
        self.assertEqual(setup["models"]["jury"], "haiku")        # remembered
        self.assertEqual(setup["models"]["defense"], "opus")      # changed this time

    def test_quick_means_three_jurors(self):
        self.assertEqual(gavel.build_setup("Ship?", quick=True)["jurors"], 3)


class TestSlug(unittest.TestCase):
    def test_long_motions_are_cut_at_a_word_boundary(self):
        s = gavel.slug("Gavel should run a jury deliberation round by default after the blind vote")
        self.assertLessEqual(len(s), 48)
        self.assertTrue(s.endswith("-by"), s)

    def test_empty_motion_still_gets_a_name(self):
        self.assertEqual(gavel.slug("???"), "case")


class TestPretrial(CaseTest):
    def test_good_pretrial_passes(self):
        self.assertEqual(len(gavel.check_pretrial(self.case)["seats"]), 3)

    def test_bad_pretrial_lists_every_problem(self):
        bad = dict(PRETRIAL, standard="vibes", seats=PRETRIAL["seats"][:2], hypotheses=[{"id": "H1", "text": "x"}])
        self.put("pretrial.json", json.dumps(bad))
        self.assertFix(lambda: gavel.check_pretrial(self.case), "standard", "seats", "hypotheses")

    def test_premortem_seat_is_required(self):
        seats = [{"seat": s, "question": "q"} for s in ("a", "b", "c")]
        self.put("pretrial.json", json.dumps(dict(PRETRIAL, seats=seats)))
        self.assertFix(lambda: gavel.check_pretrial(self.case), "premortem")

    def test_the_judge_must_seat_the_jury_the_user_chose(self):
        setup = gavel.build_setup("Ship?", seats=gavel.parse_seats("engineer, finance"))
        self.put("setup.json", json.dumps(setup))
        self.assertFix(lambda: gavel.check_pretrial(self.case), "exactly the ones the user chose")

    def test_the_judge_must_seat_the_number_asked_for(self):
        self.put("setup.json", json.dumps(gavel.build_setup("Ship?", jurors=4)))
        self.assertFix(lambda: gavel.check_pretrial(self.case), "asked for 4 seats, got 3")

    def test_broken_json_is_named(self):
        self.put("pretrial.json", "{not json")
        self.assertFix(lambda: gavel.check_pretrial(self.case), "not valid JSON")


class TestRecord(CaseTest):
    def test_record_has_both_sides_and_never_the_sealed_prior(self):
        self.speeches()
        self.put("sealed-prior.md", "SECRET PRIOR 40")
        gavel.build_record(self.case, seed=1)
        text = gavel.read(os.path.join(self.case, "record.md"))
        self.assertIn("For the motion", text)
        self.assertIn("Against the motion", text)
        self.assertIn("Rebuttals", text)
        self.assertNotIn("SECRET PRIOR", text)

    def test_side_order_follows_the_seed(self):
        self.speeches()
        orders = {tuple(gavel.build_record(self.case, seed=s)) for s in range(20)}
        self.assertEqual(len(orders), 2)  # both orders occur, so neither side always speaks first

    def test_over_limit_speech_is_refused(self):
        self.speeches(n_open=600)
        self.assertFix(lambda: gavel.build_record(self.case), "opening-for.md: 600 words", "opening-against.md")

    def test_one_sided_rebuttal_is_refused(self):
        self.speeches(rebuttals=False)
        self.put("rebuttal-for.md", "word " * 10)
        self.assertFix(lambda: gavel.build_record(self.case), "one side filed a rebuttal")

    def test_quick_mode_without_rebuttals_is_fine(self):
        self.speeches(rebuttals=False)
        gavel.build_record(self.case)
        self.assertNotIn("Rebuttals", gavel.read(os.path.join(self.case, "record.md")))


class TestTally(CaseTest):
    def test_lean_for_with_a_strong_minority(self):
        self.vote(1, ballot("engineer", "adopt", 80, "high"))
        self.vote(1, ballot("designer", "adopt_with_conditions", 65))
        self.vote(1, ballot("premortem", "reject", 20, claims=("A2",), favors="against", grade="verified"))
        r, letters = gavel.tally(self.case, seed=3)
        self.assertEqual(r["majority_side"], "for")
        self.assertEqual(r["spread"], "lean")
        self.assertEqual(r["probability"]["median"], 65)
        self.assertTrue(r["strong_minority"])
        self.assertEqual(r["minority"][0]["seat"], "premortem")
        self.assertIn("same model (sonnet)", r["correlation_note"])
        packet = gavel.read(os.path.join(self.case, "jury-packet.md"))
        self.assertIn("Juror A", packet)
        self.assertEqual(len(letters), 3)

    def test_mixed_juror_models_are_reported(self):
        seats = gavel.parse_seats("engineer, designer: opus")
        self.put("setup.json", json.dumps(gavel.build_setup("Ship?", seats=seats)))
        for seat in ("engineer", "designer", "premortem"):
            self.vote(1, ballot(seat))
        r, _ = gavel.tally(self.case)
        self.assertEqual(r["juror_models"]["designer"], "opus")
        self.assertIn("2 models", r["correlation_note"])

    def test_bad_ballots_are_all_named(self):
        self.vote(1, ballot("engineer", "maybe", 140))
        self.vote(1, dict(ballot("designer"), scores={"C1": 9}))
        self.assertFix(lambda: gavel.tally(self.case), "engineer.json: verdict", "probability",
                       "designer.json: scores", "round1/premortem.json: missing")

    def test_condition_required_for_adopt_with_conditions(self):
        b = ballot("engineer", "adopt_with_conditions")
        b["conditions"] = []
        self.vote(1, b)
        self.vote(1, ballot("designer"))
        self.vote(1, ballot("premortem"))
        self.assertFix(lambda: gavel.tally(self.case), "needs at least one condition")

    def test_herding_in_round_two_falls_back_to_the_blind_vote(self):
        self.vote(1, ballot("engineer", "adopt", 80))
        self.vote(1, ballot("designer", "adopt", 75))
        self.vote(1, ballot("premortem", "reject", 20, claims=("A1",), favors="against"))
        self.vote(2, ballot("engineer", "adopt", 80, flip_reason=""))
        self.vote(2, ballot("designer", "adopt", 75, flip_reason=""))
        self.vote(2, ballot("premortem", "adopt", 70, flip_reason="the others agree"))
        r, _ = gavel.tally(self.case)
        self.assertEqual(r["round_used"], 1)
        self.assertEqual(r["sides"]["against"], 1)
        self.assertFalse(r["flips"][0]["justified"])

    def test_a_flip_that_names_a_new_point_is_kept(self):
        self.vote(1, ballot("engineer", "adopt", 80))
        self.vote(1, ballot("designer", "adopt", 75))
        self.vote(1, ballot("premortem", "reject", 20, claims=("A1",), favors="against"))
        self.vote(2, ballot("engineer", "redesign", 35, flip_reason="Juror C showed A1 breaks the rollback"))
        self.vote(2, ballot("designer", "adopt", 75, flip_reason=""))
        self.vote(2, ballot("premortem", "reject", 20, claims=("A1",), favors="against", flip_reason=""))
        r, _ = gavel.tally(self.case)
        self.assertEqual(r["round_used"], 2)
        self.assertTrue(r["flips"][0]["justified"])


class TestClose(CaseTest):
    GOOD = ("VERDICT: Adopt with conditions (confidence medium)\n\n## Ruling\nx\n## From my prior\nx\n"
            "## Decisive evidence\nx\n## Dissent\nx\n## Conditions\nx\n## What would flip this\nx\n"
            "## What to watch\nx\n## The vote\nx\n")

    def test_good_ruling_closes_and_dockets_once(self):
        self.put("ruling.md", self.GOOD)
        self.assertEqual(gavel.close(self.case), ("Adopt with conditions", "medium"))
        gavel.close(self.case)
        docket = gavel.read(os.path.join(self.base, "docket.md"))
        self.assertEqual(docket.count("Adopt with conditions"), 1)
        self.assertEqual(gavel.list_cases(self.base)[0][1], "Adopt with conditions")

    def test_ruling_without_verdict_line_or_sections_is_refused(self):
        self.put("ruling.md", "I think it is fine.\n## Ruling\nok\n")
        self.assertFix(lambda: gavel.close(self.case), "first line", "## Dissent", "## What would flip this")


if __name__ == "__main__":
    unittest.main(verbosity=1)
