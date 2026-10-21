"""Offline regressions for session discovery and transcript attribution."""
import unittest

from collect_meetings import INDEX, discover_sessions, discover_years, parse, transcript


class MeetingTests(unittest.TestCase):
    def test_official_year_links_only(self):
        raw = b'<a href="/1994-berkshire-hathaway-annual-meeting/">1994</a><a href="https://evil.test/2020-berkshire-hathaway-annual-meeting/">2020</a><a href="/1994-berkshire-hathaway-annual-meeting/#top">duplicate</a><a href="/video/2020/x.html">clip</a>'
        self.assertEqual(discover_years(parse(raw)), {1994: "https://buffett.cnbc.com/1994-berkshire-hathaway-annual-meeting/"})
        with self.assertRaises(ValueError):
            discover_years(parse(b'<html>Access denied</html>'))

    def test_full_sessions_require_marker_and_title_excluding_clips(self):
        raw = b'<a href="/video/2020/part1.html">WATCH FULL VIDEO</a><a href="/video/2020/part1.html">2020 Berkshire Hathaway Annual Meeting - Part 1</a><a href="/video/2020/clip.html">VIDEO</a><a href="/video/2020/clip.html">2020 annual meeting clip</a><a href="/video/2020/highlights.html">WATCH FULL VIDEO</a><a href="/video/2020/highlights.html">2020 Annual Meeting Highlight Reel</a>'
        entries = discover_sessions(parse(raw), 2020, INDEX)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["session"], "part-1")
        self.assertEqual(entries[0]["url"], "https://buffett.cnbc.com/video/2020/part1.html")
        with self.assertRaises(ValueError):
            discover_sessions(parse(b'<a href="/video/x.html">2020 Morning Session</a>'), 2020, INDEX)

    def test_speaker_continuation_and_editorial_headings(self):
        raw = b'<div class="Chapter-chapter"><h3 class="Chapter-chapterTitle">1. Editorial heading</h3><p>Unassigned introduction.</p><p>WARREN BUFFETT: Business economics.</p><p>Continued thought.</p><p>(Applause.)</p><p>CHARLIE MUNGER: Incentives matter.</p><p>AUDIENCE MEMBER: A question.</p></div><div class="Chapter-chapter"><h3 class="Chapter-chapterTitle">2. New section</h3><p>Unassigned new opening.</p><p>BECKY QUICK: Next question.</p></div>'
        segments, chapters, synthetic = transcript(parse(raw), 1, 1)
        self.assertEqual(len(segments), 8)
        self.assertEqual([row["speaker"] for row in segments], [None, "Warren Buffett", "Warren Buffett", None, "Charlie Munger", "AUDIENCE MEMBER", None, "BECKY QUICK"])
        self.assertNotIn("Editorial heading", [row["text"] for row in segments])
        self.assertEqual(len(chapters), 2)
        self.assertEqual(synthetic, [])

    def test_2021_parts_follow_observed_links_despite_older_slug_year(self):
        raw = b'<a href="/video/2021/05/03/part-1---2019-berkshire-hathaway-annual-meeting.html">WATCH FULL VIDEO</a><a href="/video/2021/05/03/part-1---2019-berkshire-hathaway-annual-meeting.html">Part 1 - 2021 Meeting</a>'
        entries = discover_sessions(parse(raw), 2021, INDEX)
        self.assertEqual(entries[0]["year"], 2021)
        self.assertEqual(entries[0]["session"], "part-1")
        self.assertIn("2019-berkshire", entries[0]["url"])

    def test_synthetic_buffett_voice_is_not_real_buffett(self):
        raw = b'<div class="Chapter-chapter"><h3 class="Chapter-chapterTitle">AI Warren from Omaha asks a question</h3><p>WARREN BUFFETT: A synthetic question.</p><p>GREG ABEL: A real answer.</p></div>'
        segments, _, synthetic = transcript(parse(raw), 1, 1)
        self.assertEqual(segments[0]["speaker"], "Synthetic or AI-generated voice")
        self.assertEqual(segments[1]["speaker"], "GREG ABEL")
        self.assertEqual(len(synthetic), 1)

    def test_missing_transcript_and_short_clip_fail(self):
        for raw in [b'<html><video></video></html>', b'<div class="Chapter-chapter"><h3 class="Chapter-chapterTitle">Short clip</h3><p>WARREN BUFFETT: Hello.</p></div>']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                transcript(parse(raw))


if __name__ == "__main__":
    unittest.main()
