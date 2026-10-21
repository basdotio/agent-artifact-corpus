#!/usr/bin/env python3
"""Tests for the virality skill tools. Run from skills/virality:

    python3 -m unittest discover -s tools -p "test_*.py"

Every tool is run on small generated inputs, both imported and as a CLI.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import collect     # noqa: E402
import hookscore   # noqa: E402
import speech      # noqa: E402


def cli(tool, *args, stdin=None):
    p = subprocess.run([sys.executable, os.path.join(HERE, tool)] + list(args),
                       input=stdin, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path


class TestSpeech(Base):
    def test_numbers_are_said_out_loud(self):
        cases = {"$4,200": 5, "97%": 3, "10x": 2, "1.2M": 4, "$9M": 3, "2026": 3,
                 "1,000": 2, "412,000": 4, "24/7": 3, "5-10": 3}
        for token, want in cases.items():
            self.assertEqual(speech.number_token_words(token), want, token)
        self.assertEqual(speech.spoken_words("I saved $4,200 last month."), 9)

    def test_transcripts_and_rolling_captions(self):
        srt = self.write("a.srt", "1\n00:00:00,500 --> 00:00:02,000\nI saved $400\n\n"
                                  "2\n00:00:02,100 --> 00:00:03,500\nwith one prompt.\n")
        cues = speech.load_transcript(srt)
        self.assertEqual(len(cues), 2)
        self.assertEqual(speech.measure(cues)["span"], 3.0)
        vtt = self.write("b.vtt", "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n \nhey<00:00:00.300><c> guys</c>\n\n"
                                  "00:00:02.000 --> 00:00:04.000\nhey guys\ntoday we test\n")
        self.assertEqual(" ".join(c[2] for c in speech.load_transcript(vtt)), "hey guys today we test")
        j3 = self.write("c.json3", json.dumps({"events": [{"tStartMs": 0, "dDurationMs": 2000,
                                                           "segs": [{"utf8": "I made $9M"}]}]}))
        self.assertEqual(speech.load_transcript(j3)[0], (0.0, 2.0, "I made $9M"))
        code, out, _ = cli("speech.py", srt)
        self.assertEqual(code, 0)
        self.assertIn("wpm", out)
        self.assertEqual(cli("speech.py")[0], 2)


class TestHookscore(Base):
    def test_library_self_classifies(self):
        with open(os.path.join(HERE, "hooks.json"), encoding="utf-8") as fh:
            lib = json.load(fh)
        self.assertEqual(len(lib["hooks"]), 26)
        for h in lib["hooks"]:
            self.assertLessEqual(len(h["on_screen"].split()), 6, h["id"])
            for field in ("example", "written"):
                got, _ = hookscore.classify(h[field])
                self.assertEqual(got and got["id"], h["id"], "%s %s" % (h["id"], field))

    def test_panel_payoff_and_dealbreakers(self):
        good = hookscore.analyse("I saved $400 on flights last month with one prompt.")
        self.assertEqual(good["verdict"], "STRONG")
        self.assertEqual(good["payoff"]["status"], "LEADS")
        self.assertEqual(good["formula"]["name"], "The Payoff")
        bad = hookscore.analyse("Hey guys, today I want to talk about productivity.")
        self.assertEqual(bad["verdict"], "WEAK")
        self.assertEqual(bad["payoff"]["status"], "MISSING")
        self.assertTrue(bad["flags"])
        late = hookscore.payoff("Here is something I learned the hard way after spending $9,000")
        self.assertEqual(late["status"], "LATE")

    def test_cli(self):
        hooks = self.write("h.txt", "Hey guys, welcome back.\n$18,000 is what one missing clause cost me.\n")
        code, out, _ = cli("hookscore.py", hooks)
        self.assertEqual(code, 0)
        self.assertIn("The Cost", out)
        code, out, _ = cli("hookscore.py", "--hook", "So um this is a thing", "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["verdict"], "WEAK")
        self.assertEqual(cli("hookscore.py", "missing.txt")[0], 2)
        self.assertEqual(cli("hookscore.py", "--list")[0], 0)


class TestCollectAndSwipe(Base):
    PASTE = ("# creator | views | hook | url\n"
             "@a | 1.2M | I feed four people on $62 a week. | https://www.tiktok.com/@a/video/1\n"
             "@a | 48K | Three pantry meals | https://www.tiktok.com/@a/video/2\n"
             "@a | 51,300 | My Sunday prep | https://www.tiktok.com/@a/video/3\n"
             "@a | 39.000 | Stop buying pre-cut vegetables. | https://www.tiktok.com/@a/video/4\n"
             "@a | n/a | no count here |\n"
             "@b | 3,1M | Comment \"PLAN\" and I'll send you the plan \U0001F447 I cut our bill by $300. |\n")

    def test_counts_and_cta_strip(self):
        self.assertEqual(collect.parse_count("1.2M views"), 1200000)
        self.assertEqual(collect.parse_count("412K"), 412000)
        self.assertEqual(collect.parse_count("1.234"), 1234)
        self.assertEqual(collect.parse_count("3,1M"), 3100000)
        self.assertIsNone(collect.parse_count("n/a"))
        self.assertEqual(collect.parse_duration("1:02"), 62.0)
        self.assertEqual(collect.parse_duration("PT1M20S"), 80.0)
        self.assertEqual(collect.hook_from("Comment \"X\" and I'll send it \U0001F447 I made $9M."), "I made $9M.")
        self.assertEqual(collect.hook_from("Type this into ChatGPT. It plans your week."), "Type this into ChatGPT.")

    def test_formats_and_dedup(self):
        paste = self.write("p.txt", self.PASTE)
        csvf = self.write("e.csv", "Account,Views,Caption,Link\n@c,22K,Five freezer meals,https://www.instagram.com/reel/x\n")
        ytdlp = self.write("y.json", json.dumps({"uploader_id": "@d", "channel": "D", "entries": [
            {"title": "One", "view_count": 100, "url": "https://www.youtube.com/shorts/AAAAAAAA1"},
            {"title": "One again", "view_count": 100, "url": "https://youtube.com/shorts/AAAAAAAA1?x=1"}]}))
        posts, skipped = collect.collect([paste, csvf, ytdlp])
        by = {p["channel"]: p for p in posts}
        self.assertEqual(skipped, 1)
        self.assertEqual(len(posts), 7)
        self.assertEqual(by["@b"]["hook"], "I cut our bill by $300.")
        self.assertEqual(by["@d"]["platform"], "shorts")
        self.assertEqual(by["@c"]["views"], 22000)

    def test_cli_pipeline(self):
        paste = self.write("p.txt", self.PASTE)
        out = os.path.join(self.dir, "c.json")
        self.assertEqual(cli("collect.py", paste, "-o", out, "--quiet")[0], 0)
        code, text, _ = cli("swipe.py", out, "--min", "2.0")
        self.assertEqual(code, 0)
        self.assertIn("1,200,000", text)
        self.assertIn("The Payoff", text)
        self.assertIn("@b (1)", text)                       # thin creator skipped, said out loud
        code, text, _ = cli("swipe.py", out, "--json")
        top = json.loads(text)["outliers"][0]
        self.assertEqual(top["channel"], "@a")
        self.assertGreater(top["multiple"], 20)
        self.assertEqual(cli("collect.py", self.write("j.txt", "nothing here\n"))[0], 1)
        self.assertEqual(cli("collect.py", "missing.txt")[0], 2)
        self.assertEqual(cli("swipe.py", "--help")[0], 0)


class TestHumanizeDetectTitle(Base):
    def test_humanize_strips_tells(self):
        draft = self.write("d.txt", "In this video we delve into a robust \u2014 seamless "
                                    "workflow.\u200b Let that sink in.\n")
        code, out, err = cli("humanize.py", draft, "--report")
        self.assertEqual(code, 0)
        for gone in ("\u2014", "\u200b", "delve", "robust", "In this video", "sink in"):
            self.assertNotIn(gone, out)
        self.assertIn("HUMANIZE REPORT", err)

    def test_detect_panel(self):
        human = self.write("h.txt", "I sent 400 cold DMs in March. Eleven replied. Two became "
                                    "clients, and one of them paid $8,000 for a site I built in "
                                    "nine days. I'm not doing that again without a contract. "
                                    "Honestly? Worth it, but barely.\n")
        code, out, _ = cli("detect.py", human, "--json")
        data = json.loads(out)
        self.assertIn(data["verdict"], ("PASS", "REVIEW", "FLAGGED"))
        self.assertEqual(set(data["checks"]), {"BURSTINESS", "SPECIFICITY", "SLOP DENSITY",
                                                "FINGERPRINT", "VOICE"})
        self.assertEqual(code, 0 if data["verdict"] == "PASS" else 1)

    def test_title_pairing(self):
        code, out, _ = cli("title.py", "--title", "I feed four people on $62 a week",
                           "--cover", "$62 A WEEK", "--json")
        self.assertEqual(code, 0)
        r = json.loads(out)[0]
        self.assertTrue(any(k == "duplicate" for k, _ in r["issues"]))
        self.assertEqual(cli("title.py", "--help")[0], 0)


class TestSkillFiles(unittest.TestCase):
    def test_no_em_dashes_anywhere(self):
        for root, _, files in os.walk(SKILL):
            for name in files:
                if name.endswith((".py", ".md", ".json")):
                    with open(os.path.join(root, name), encoding="utf-8") as fh:
                        self.assertNotIn("\u2014", fh.read(), name)

    def test_skill_frontmatter_and_template_hook(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("---\nname: virality\n"))
        self.assertLessEqual(len(text.splitlines()), 400)
        with open(os.path.join(SKILL, "templates", "script.md"), encoding="utf-8") as fh:
            tpl = fh.read()
        hook = [l for l in tpl.splitlines() if l.startswith("SAY:")][0][4:].strip()
        a = hookscore.analyse(hook)
        self.assertEqual((a["verdict"], a["payoff"]["status"]), ("STRONG", "LEADS"))
        self.assertLess(speech.seconds(hook, 190), 3.5)


if __name__ == "__main__":
    unittest.main()
