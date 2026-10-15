import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check import layout_problems, narration_problems, scene_problems, settled_frames


def scene(start, end, title="A short title", **more):
    return {"start": start, "end": end, "title": title, **more}


def word(text, start, end):
    return {"text": text, "start": start, "end": end}


class SceneTest(unittest.TestCase):
    def test_a_well_paced_video_has_no_problems(self):
        scenes = [scene(0, 4.5), scene(4.5, 12, points=[{"text": "One", "at": 6}, {"text": "Two", "at": 9.5}])]
        self.assertEqual(scene_problems(scenes), [])

    def test_the_video_opens_at_zero_and_scenes_run_on(self):
        found = scene_problems([scene(1, 4), scene(4.5, 8), scene(7, 10)])
        self.assertEqual(found, ["the first scene starts at 1 s: open on the hook at 0",
                                 "0.50 s gap between scene 1 and scene 2", "1.00 s overlap between scene 2 and scene 3"])

    def test_word_limits(self):
        found = scene_problems([scene(0, 4, "This title has far too many words",
                                      points=[{"text": "one two three four five six", "at": 1}])])
        self.assertEqual(found, ['scene 1 "This title has far too many words": the title has 7 words (max 6)',
                                 'scene 1 "This title has far too many words": point "one two three four five six" has 6 words (max 5)'])

    def test_a_point_pops_inside_its_scene_with_time_to_read(self):
        found = scene_problems([scene(0, 5, points=[{"text": "Late", "at": 4.7}, {"text": "Lost", "at": 5.2}])])
        self.assertEqual(found, ['scene 1 "A short title": point "Late" pops 0.3 s before the scene ends, too short to read (min 0.8 s)',
                                 'scene 1 "A short title": point "Lost" pops at 5.2 s, outside the scene (0-5 s)'])

    def test_a_held_picture_is_reported_with_where_it_starts(self):
        found = scene_problems([scene(0, 13.1, points=[{"text": "First", "at": 7.95}, {"text": "Second", "at": 12}])])
        self.assertEqual(found, ['scene 1 "A short title" holds the same picture for 8.0 s from 0 s (max 6): split it or add a point'])

    def test_one_settled_frame_per_scene_before_its_exit(self):
        self.assertEqual(settled_frames([scene(0, 4), scene(4, 4.2)]), [220, 241])


class NarrationTest(unittest.TestCase):
    def test_continuous_narration_passes(self):
        self.assertEqual(narration_problems([word("Hi", 0.3, 0.6), word("there.", 0.7, 1.2)], 2.0, 1.2), [])

    def test_late_start_dead_air_and_trailing_silence(self):
        found = narration_problems([word("Hi", 2.0, 2.4), word("there.", 4.4, 5.0)], 9.0, 1.2)
        self.assertEqual(found, ["narration starts at 2.0 s (max 1.5): open on the hook",
                                 '2.0 s of dead air after "Hi" at 2.4 s (max 1.2)',
                                 "4.0 s of silence after the last word (max 2): end on the payoff"])

    def test_a_scripted_pause_passes_with_a_wider_gap(self):
        self.assertEqual(narration_problems([word("Hi", 0.2, 0.4), word("there.", 2.4, 3.0)], 3.5, 2.5), [])


class LayoutTest(unittest.TestCase):
    def test_each_finding_names_its_frame_and_fonts_are_listed_once(self):
        reports = [
            {"frame": 220, "texts": ["A"], "cropped": ["A very long title"], "overCaptions": [], "fallbackFonts": [["Inter", "A"]]},
            {"frame": 500, "texts": ["B"], "cropped": [], "overCaptions": ["Sixth point"], "fallbackFonts": [["Inter", "B"]]},
        ]
        self.assertEqual(layout_problems(reports, lambda f: f"scene at {f}"),
                         ['scene at 220: "A very long title" is cropped or inside the side margins',
                          'scene at 500: "Sixth point" runs into the caption band',
                          'font "Inter" did not load, so a fallback is drawn (e.g. "A")'])

    def test_clean_reports_give_nothing(self):
        self.assertEqual(layout_problems([{"frame": 1, "texts": ["A"], "cropped": [], "overCaptions": [], "fallbackFonts": []}]), [])


if __name__ == "__main__":
    unittest.main()
