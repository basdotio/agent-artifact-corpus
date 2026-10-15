import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from align import align, text_tokens


def words(*items):
    return [{"i": i, "text": t, "start": s, "end": e, "prob": 0.9, "filler": False}
            for i, (t, s, e) in enumerate(items)]


class AlignTest(unittest.TestCase):
    def test_misheard_name_takes_the_text_spelling_and_keeps_its_timing(self):
        heard = words(("Visit", 0.0, 0.4), ("miraystudio", 0.5, 1.2), (".id.", 1.2, 1.5))
        out, share, extra, unheard = align(heard, text_tokens("Visit miraestudio.id."))
        self.assertEqual([w["text"] for w in out], ["Visit", "miraestudio.id."])
        self.assertEqual((out[1]["start"], out[1]["end"]), (0.5, 1.5))
        self.assertEqual((extra, unheard), ([], []))

    def test_lone_symbol_joins_the_word_before_it(self):
        heard = words(("about", 0.0, 0.3), ("30", 0.4, 0.7), ("%", 0.7, 0.9))
        out, *_ = align(heard, text_tokens("about 30%"))
        self.assertEqual([(w["text"], w["end"]) for w in out], [("about", 0.3), ("30%", 0.9)])

    def test_unequal_block_spreads_time_by_length(self):
        heard = words(("first", 0.0, 0.4), ("80", 0.5, 1.0), ("to", 1.0, 1.1), ("90", 1.1, 1.5), ("percent", 1.5, 2.0))
        out, *_ = align(heard, text_tokens("first 80–90% percent"))
        self.assertEqual([w["text"] for w in out], ["first", "80–90%", "percent"])
        self.assertEqual((out[1]["start"], out[1]["end"]), (0.5, 1.5))

    def test_spoken_word_written_as_a_symbol_is_not_shown_twice(self):
        heard = words(("to", 0.0, 0.2), ("90", 0.3, 0.6), ("percent", 0.6, 1.1), ("of", 1.2, 1.3))
        out, _, extra, _ = align(heard, text_tokens("to 90% of"))
        self.assertEqual([(w["text"], w["start"], w["end"]) for w in out],
                         [("to", 0.0, 0.2), ("90%", 0.3, 1.1), ("of", 1.2, 1.3)])
        self.assertEqual(extra, [])

    def test_heard_only_words_stay_and_unheard_text_is_dropped(self):
        heard = words(("so", 0.0, 0.2), ("hello", 0.3, 0.6), ("world", 0.7, 1.0))
        out, _, extra, unheard = align(heard, text_tokens("hello world again"))
        self.assertEqual([w["text"] for w in out], ["so", "hello", "world"])
        self.assertEqual((extra, unheard), (["so"], ["again"]))

    def test_indices_are_renumbered_and_pauses_skipped(self):
        heard = words(("one", 0.0, 0.2), ("two", 0.3, 0.5))
        out, share, *_ = align(heard, text_tokens("One\n\n[pause 1.0]\n\nTwo."))
        self.assertEqual([(w["i"], w["text"]) for w in out], [(0, "One"), (1, "Two.")])
        self.assertEqual(share, 1.0)

    def test_wrong_text_scores_low(self):
        heard = words(("one", 0.0, 0.2), ("two", 0.3, 0.5), ("three", 0.6, 0.9))
        self.assertLess(align(heard, text_tokens("completely different words here"))[1], 0.7)


if __name__ == "__main__":
    unittest.main()
