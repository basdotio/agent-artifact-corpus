"""Tests for scripts/journal.py. Standard library only: python3 -m unittest discover -s tests"""
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "journal.py"
TODAY = "2026-10-03"

_spec = importlib.util.spec_from_file_location("journal", SCRIPT)
journal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(journal)


def text_pdf(path: Path, page_lines: list) -> None:
    """Write a minimal PDF with one line of text per page (plain ASCII, no parentheses)."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", "",
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for line in page_lines:
        stream = f"BT /F1 12 Tf 72 720 Td ({line}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                       f"/Resources << /Font << /F1 3 0 R >> >> /Contents {len(objects)} 0 R >>")
        kids.append(len(objects))
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def tiny_png(path: Path) -> None:
    """Write a small valid PNG, so the inbox has a real image to work with."""
    w, h = 8, 8
    raw = b"".join(b"\x00" + b"\xc8\xbe\xaa" * w for _ in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class JournalTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "journal"
        self.env = dict(os.environ, MARGINALIA_HOME=str(self.home))

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *args, ok=True):
        proc = subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True)
        if ok and proc.returncode != 0:
            self.fail(f"journal.py {' '.join(args)} failed:\n{proc.stderr}")
        if not ok:
            self.assertNotEqual(proc.returncode, 0, f"expected journal.py {' '.join(args)} to fail")
        return proc

    def add(self, book="novel", result="got", today=TODAY, question="q"):
        return self.run_cli("add", "--book", book, "--question", question, "--key", "k",
                            "--source", "ch. 1", "--result", result, "--today", today)

    def items(self):
        return json.loads((self.home / "review-queue.json").read_text())["items"]

    def item(self, item_id):
        return next(it for it in self.items() if it["id"] == item_id)


class QueueTests(JournalTestCase):
    def test_first_review_depends_on_how_they_did(self):
        self.add(result="got")
        self.add(result="partial")
        self.add(result="missed")
        self.assertEqual([it["due"] for it in self.items()], ["2026-10-06", "2026-10-04", "2026-10-04"])

    def test_correct_answers_climb_the_boxes_then_retire(self):
        self.add(result="got")  # box 2, due in 3 days
        for day, expected_due in [("2026-10-06", "2026-10-13"), ("2026-10-13", "2026-11-03"),
                                  ("2026-11-03", "2027-01-02")]:
            self.run_cli("grade", "1", "got", "--today", day)
            self.assertEqual(self.item(1)["due"], expected_due)
        out = self.run_cli("grade", "#1", "got", "--today", "2027-01-02").stdout
        self.assertIn("retired", out)
        self.assertEqual(self.item(1)["retired"], "2027-01-02")
        self.run_cli("grade", "1", "got", ok=False)

    def test_partial_repeats_the_box_and_missed_starts_over(self):
        self.add(result="got")
        self.run_cli("grade", "1", "got", "--today", "2026-10-06")  # box 3
        self.run_cli("grade", "1", "partial", "--today", "2026-10-13")
        self.assertEqual((self.item(1)["box"], self.item(1)["due"]), (3, "2026-10-20"))
        self.run_cli("grade", "1", "missed", "--today", "2026-10-20")
        self.assertEqual((self.item(1)["box"], self.item(1)["due"]), (1, "2026-10-21"))

    def test_due_mixes_books_and_respects_the_limit(self):
        for i in range(3):
            self.add(book="novel", result="missed", question=f"n{i}")
        self.add(book="essays", result="missed", question="e0")
        out = self.run_cli("due", "--limit", "2", "--today", "2026-10-04").stdout
        self.assertIn("4 due (showing 2)", out)
        self.assertIn("novel", out)
        self.assertIn("essays", out)
        self.assertIn("Nothing due.", self.run_cli("due", "--today", TODAY).stdout)

    def test_dropped_questions_leave_due_and_retired_counts(self):
        self.add(result="missed")
        self.run_cli("drop", "1", "--today", TODAY)
        self.assertIn("Nothing due.", self.run_cli("due", "--today", "2026-10-04").stdout)
        stats = self.run_cli("stats", "--today", "2026-10-04").stdout
        self.assertIn("Active: 0 · due now: 0 · retired (yours now): 0", stats)
        self.assertIn("dropped", self.run_cli("list", "--all").stdout)

    def test_stats_count_only_the_window_up_to_today(self):
        self.add(result="missed")
        self.run_cli("grade", "1", "partial", "--today", "2026-10-04")
        self.run_cli("grade", "1", "got", "--today", "2026-10-30")  # future relative to the check below
        stats = self.run_cli("stats", "--today", "2026-10-05").stdout
        self.assertIn("Reruns answered: last 7 days 1", stats)

    def test_bad_input_fails_cleanly(self):
        self.run_cli("grade", "99", "got", ok=False)
        self.run_cli("grade", "abc", "got", ok=False)
        self.run_cli("add", "--book", "b", "--question", "q", "--key", "k", "--source", "s",
                     "--result", "maybe", ok=False)
        self.run_cli("due", "--today", "10/3/2026", ok=False)

    def test_corrupt_queue_is_reported_not_overwritten(self):
        self.home.mkdir(parents=True)
        (self.home / "review-queue.json").write_text("{oops")
        self.run_cli("due", ok=False)
        self.assertEqual((self.home / "review-queue.json").read_text(), "{oops")

    @unittest.skipIf(os.name == "nt", "queue writes are only locked on POSIX")
    def test_simultaneous_writes_keep_every_question(self):
        procs = [subprocess.Popen([sys.executable, str(SCRIPT), "add", "--book", f"b{i % 3}",
                                   "--question", f"q{i}", "--key", "k", "--source", "s",
                                   "--result", "partial", "--today", TODAY],
                                  env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                 for i in range(15)]
        for p in procs:
            self.assertEqual(p.wait(), 0)
        self.assertEqual(sorted(it["id"] for it in self.items()), list(range(1, 16)))


class JournalSetupTests(JournalTestCase):
    def test_where_reports_a_missing_journal(self):
        out = self.run_cli("where").stdout
        self.assertIn(str(self.home), out)
        self.assertIn("run init", out)

    def test_init_creates_the_journal_and_never_overwrites(self):
        out = self.run_cli("init").stdout
        self.assertIn("Journal ready", out)
        for name in ("shelf.md", "profile.md", "README.md", "commonplace.md", "writing.md", "reflections.md"):
            self.assertTrue((self.home / name).is_file(), name)
        for folder in ("books", "plans", "inbox/done"):
            self.assertTrue((self.home / folder).is_dir(), folder)
        (self.home / "shelf.md").write_text("my shelf")
        self.assertIn("nothing changed", self.run_cli("init").stdout)
        self.assertEqual((self.home / "shelf.md").read_text(), "my shelf")
        self.assertNotIn("run init", self.run_cli("where").stdout)

    def test_bundled_plans_can_be_listed_and_copied_once(self):
        self.assertIn("harvard-classics", self.run_cli("plans").stdout)
        self.run_cli("add-plan", "harvard-classics")
        copied = self.home / "plans" / "harvard-classics.md"
        self.assertIn("### Jan 1 ·", copied.read_text())
        copied.write_text("my progress notes")
        self.assertIn("left it alone", self.run_cli("add-plan", "harvard-classics").stdout)
        self.assertEqual(copied.read_text(), "my progress notes")
        self.run_cli("add-plan", "no-such-plan", ok=False)


class InboxTests(JournalTestCase):
    def test_inbox_lists_readable_files_and_skips_the_rest(self):
        inbox = self.home / "inbox"
        inbox.mkdir(parents=True)
        tiny_png(inbox / "page-12.png")
        (inbox / "notes.docx").write_text("not a page")
        (inbox / ".DS_Store").write_text("")
        out = self.run_cli("inbox").stdout
        self.assertIn("1 file(s) ready", out)
        self.assertIn("page-12.png", out)
        self.assertIn("skipped notes.docx", out)
        self.assertNotIn(".DS_Store", out)

    def test_archive_moves_files_and_avoids_name_clashes(self):
        inbox = self.home / "inbox"
        inbox.mkdir(parents=True)
        tiny_png(inbox / "p.png")
        self.run_cli("archive", "p.png", "--today", TODAY)
        tiny_png(inbox / "p.png")
        self.run_cli("archive", "--all", "--today", TODAY)
        done = sorted(f.name for f in (inbox / "done" / TODAY).iterdir())
        self.assertEqual(done, ["p-1.png", "p.png"])
        self.assertIn("Inbox is empty.", self.run_cli("inbox").stdout)

    def test_archive_refuses_files_outside_the_inbox(self):
        outside = self.tmp / "elsewhere.png"
        tiny_png(outside)
        self.run_cli("archive", str(outside), ok=False)
        self.assertTrue(outside.exists())
        self.run_cli("archive", ok=False)

    @unittest.skipUnless(shutil.which("sips"), "HEIC conversion uses macOS sips")
    def test_iphone_heic_photos_become_jpegs(self):
        inbox = self.home / "inbox"
        inbox.mkdir(parents=True)
        tiny_png(self.tmp / "src.png")
        made = subprocess.run(["sips", "-s", "format", "heic", str(self.tmp / "src.png"),
                               "--out", str(inbox / "IMG_0001.HEIC")], capture_output=True)
        if made.returncode != 0:
            self.skipTest("this Mac's sips can't write HEIC")
        out = self.run_cli("inbox", "--today", TODAY).stdout
        self.assertIn("IMG_0001.jpg", out)
        self.assertTrue((inbox / "IMG_0001.jpg").is_file())
        self.assertTrue((inbox / "done" / TODAY / "IMG_0001.HEIC").is_file())


class PageNumberTests(unittest.TestCase):
    def test_running_heads_give_up_their_page_numbers(self):
        self.assertEqual(journal.head_number("390 SIR CHARLES LYELL"), 390)
        self.assertEqual(journal.head_number("UNIFORMITY OF CHANGE 399"), 399)
        self.assertEqual(journal.head_number("UNIFORMITY OF CHANGE 4O9"), 409)  # OCR letter O
        self.assertIsNone(journal.head_number("T H E A M E R I C A N S C H O L A R I I"))
        self.assertIsNone(journal.head_number("THE AMERICAN SCHOLAR"))
        self.assertIsNone(journal.head_number(""))

    def test_one_misread_page_is_outvoted(self):
        self.assertEqual(journal.pick_offset({404: 390, 405: 397, 407: 399, 408: 400}), 8)
        self.assertIsNone(journal.pick_offset({406: 398}))
        self.assertIsNone(journal.pick_offset({}))

    def test_page_ranges_in_the_plan_formats(self):
        self.assertEqual(journal.parse_ranges("398-405"), [(398, 405)])
        self.assertEqual(journal.parse_ranges("pp. 71–87"), [(71, 87)])
        self.assertEqual(journal.parse_ranges("p. 337; also pp. 395–410"), [(337, 337), (395, 410)])
        self.assertEqual(journal.parse_ranges("119–120, 388–394"), [(119, 120), (388, 394)])
        with self.assertRaises(SystemExit):
            journal.parse_ranges("chapter five")
        with self.assertRaises(SystemExit):
            journal.parse_ranges("20-10")


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("swiftc"), "page extraction uses macOS PDFKit")
class PagesCommandTests(JournalTestCase):
    def setUp(self):
        super().setUp()
        heads = ["Title page", "Contents", "Preface"]  # front matter: 3 unnumbered pages
        heads += [f"{n} THE AUTHOR" if n % 2 == 0 else f"THE BOOK {n}" for n in range(1, 31)]
        self.pdf = self.tmp / "book.pdf"
        text_pdf(self.pdf, heads)

    def test_finds_the_offset_and_splits_long_readings(self):
        out = self.run_cli("pages", str(self.pdf), "5-17").stdout
        self.assertIn("PDF page = printed page +3", out)
        files = sorted(p.name for p in (self.home / ".pages").glob("*.pdf"))
        self.assertEqual(files, ["book-pp15-17.pdf", "book-pp5-14.pdf"])

    def test_each_run_replaces_the_previous_extracts(self):
        self.run_cli("pages", str(self.pdf), "5-17")
        self.run_cli("pages", str(self.pdf), "2", "--offset", "3")
        self.assertEqual([p.name for p in (self.home / ".pages").glob("*.pdf")], ["book-pp2-2.pdf"])

    def test_refuses_pages_outside_the_pdf(self):
        self.run_cli("pages", str(self.pdf), "29-40", ok=False)
        self.run_cli("pages", str(self.tmp / "missing.pdf"), "1-2", ok=False)


if __name__ == "__main__":
    unittest.main()
