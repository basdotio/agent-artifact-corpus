import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from post import post_text, problems

GOOD = {
    "title": "What gives AI fiction away?",
    "hook": "A novel pulled for AI",
    "caption": "A publisher pulled a novel. Here is what the research says.",
    "hashtags": ["ai", "writing", "books"],
    "sources": ["https://example.org/study"],
    "generated": ["voice (VoxCPM2)"],
    "chapters": [{"at": "0:00", "title": "The novel"}, {"at": "0:11", "title": "Same story"}, {"at": "0:45", "title": "Fixes"}],
}


def broken(**changes):
    return problems({**GOOD, **changes}, 72.0, "A novel pulled for AI")


class PostTest(unittest.TestCase):
    def test_a_complete_post_has_no_problems(self):
        self.assertEqual(broken(), [])

    def test_chapters_are_optional(self):
        post = {k: v for k, v in GOOD.items() if k != "chapters"}
        self.assertEqual(problems(post, 72.0), [])

    def test_length_limits(self):
        self.assertIn("title is 101 characters, over the 100 limit", broken(title="x" * 101))
        self.assertIn("caption is 2201 characters, over the 2200 limit", broken(caption="x" * 2201))

    def test_hashtags(self):
        self.assertEqual(broken(hashtags=["one", "two"]), ["hashtags needs 3 to 8 entries"])
        self.assertEqual(broken(hashtags=["#ai", "two words", "ok"]),
                         ['hashtag "#ai" must have no "#" and no spaces', 'hashtag "two words" must have no "#" and no spaces'])

    def test_sources_and_generated_must_be_stated(self):
        post = {k: v for k, v in GOOD.items() if k not in ("sources", "generated")}
        self.assertEqual(problems(post, 72.0),
                         ["sources must be a list (empty when there is nothing to list)",
                          "generated must be a list (empty when there is nothing to list)"])

    def test_hook_must_read_as_the_first_scene(self):
        self.assertEqual(broken(hook="a  NOVEL pulled for ai"), [])
        self.assertEqual(broken(hook="Something else"),
                         ['hook is "Something else" but the first scene reads "A novel pulled for AI"'])

    def test_chapter_rules(self):
        two = GOOD["chapters"][:2]
        self.assertEqual(broken(chapters=two), ["chapters needs at least 3 entries, or none"])
        late = [{"at": "0:05", "title": "a"}, {"at": "0:09", "title": "b"}, {"at": "2:00", "title": "c"}]
        self.assertEqual(broken(chapters=late),
                         ["the first chapter must be at 0:00", 'chapter "b" starts under 10 s after the one before it',
                          'chapter "c" at 2:00 is past the end of the video (72 s)'])
        self.assertEqual(broken(chapters=[{"at": "soon", "title": "a"}]), ['each chapter needs "at" as m:ss and a title'])

    def test_post_text_is_paste_ready(self):
        text = post_text(GOOD, ["Music: Song by Artist (CC BY 4.0)"])
        self.assertIn("#ai #writing #books", text)
        self.assertIn("Chapters\n0:00 The novel\n0:11 Same story", text)
        self.assertIn("Sources\n- https://example.org/study", text)
        self.assertIn("Credits\nMusic: Song by Artist (CC BY 4.0)", text)
        self.assertTrue(text.endswith("AI-generated: voice (VoxCPM2)\n"))


if __name__ == "__main__":
    unittest.main()
