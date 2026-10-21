"""Tests for scrub.py. Run: python3 -m unittest discover -s tests -v

Every fake token is assembled at runtime so this file never contains a
string that a secret scanner (or this tool) would flag.
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import scrub  # noqa: E402

A = "a1B2c3D4e5F6g7H8i9J0"
FAKES = {
    "anthropic_key": "sk-" + "ant-api03-" + A * 3,
    "openai_key": "sk-" + "proj-" + A * 2,
    "github_token": "gh" + "p_" + A + "k2L3m4N5o6P7q8R9s0T1",
    "aws_access_key_id": "AK" + "IA" + "Q3X7Z2P9L4M8N1B6",
    "google_api_key": "AI" + "za" + "SyD3x9Q2w8E7r6T5y4U3i2O1p0A9s8D7f6G",
    "slack_token": "xo" + "xb-" + "1234567890-" + A,
    "stripe_key": "sk" + "_live_" + A,
    "telegram_bot_token": "7123456789" + ":AA" + "Hk3Lm9Qp2Rs8Tv4Wx7Yz1Ab5Cd6Ef0GhI",
    "jwt": "ey" + "JhbGciOiJIUzI1NiJ9." + "ey" + "JzdWIiOiIxMjM0NTY3ODkwIn0." + "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
}
PRIVATE_KEY = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA7x9\nQ2w8E7r6T5y4\n-----END " + "RSA PRIVATE KEY-----"

POSITIVE_TEXT = [
    ("my password is Hunter2024!", "Hunter2024!"),
    ("DB_PASSWORD=S3cr3tPa55", "S3cr3tPa55"),
    ('{"client_secret": "q8Zr4LpX2mN7vB1c"}', "q8Zr4LpX2mN7vB1c"),
    ("export OPENAI_API_KEY=zz9Qw8Er7Ty6Ui5Op4", "zz9Qw8Er7Ty6Ui5Op4"),
    ("mysql --password=Tr0ub4dor&3 -u root", "Tr0ub4dor&3"),
    ("postgres://admin:Pg5ecretPw@db.example.com:5432/app", "Pg5ecretPw"),
    ("curl -H 'Authorization: Bearer abc123def456ghi789jkl012'", "abc123def456ghi789jkl012"),
    ("the wifi pw: Kettle-Lamp-77", "Kettle-Lamp-77"),
    ("apiKey: 'Zx81Lm22Qp93Rt'", "Zx81Lm22Qp93Rt"),
    ("Meeting ID: 939 609\\r\\nPasscode: kX7q2Lm9 Teams", "kX7q2Lm9"),
    ('<a href="https://x.com/login?otpToken=AbC123dEf456GhI789&amp;trk=1">', "AbC123dEf456GhI789"),
    ("FTP_PASS=Qw3rty!2024", "Qw3rty!2024"),
]

NEGATIVE_TEXT = [
    '"usage":{"input_tokens":1234,"output_tokens":567,"cache_read_input_tokens":0}',
    "password = get_password()",
    "password = user_input",
    'const password = process.env.DB_PASSWORD;',
    'api_key = os.getenv("API_KEY")',
    '"password": "string"',
    '<input type="password" placeholder="Enter your password">',
    "PASS: test_login_flow1",
    "max_tokens=4096",
    "token_type: bearer",
    "the token is expired, please log in again",
    "my password is correct",
    "commit 3f9a2b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
    "session 0c683802-0d66-488c-8685-95521b381817",
    "secret_name: prod/db/credentials",
    'password: "${DB_PASSWORD}"',
    "API_KEY=your_api_key_here",
    "password: [REDACTED:password]",
    "see https://github.com/example/project/blob/main/README.md",
    "sk-learn-is-a-python-library-for-machine-learning-stuff",
    "next_page_token: CiAKGjBpNDd2Nmp2Zml2cXRkMGx",
    "token_file: ~/.config/app/token.json",
    'echo "loudnorm pass1: I=-23.45 TP=-1.2"',
    "--pass-bg: #E9F4EC; --fail-bg: #F6E9EB;",
    "with sync_playwright() as pw:\n    b = pw.chromium.launch()",
    "if best_score >= critic.PASS_MARK:\n    print(best)",
    "fetch(u, {credentials:'include'})",
    "System.Web, PublicKeyToken=b03f5f7f11d50a3a",
    "VITE_CLERK_PUBLISHABLE_KEY=pk_" + "test_Y2xlcmsuZXhhbXBsZS5jb20k",
    "  - Token: gho_************************************",
    "pat = r'\\bfoo\\d+'",
]


def detect(text, **kw):
    return scrub.Detector(**kw).spans(text, human=True)


class DetectorTests(unittest.TestCase):
    def test_known_formats(self):
        for kind, tok in FAKES.items():
            with self.subTest(kind=kind):
                spans = detect(f"here it is: {tok} ok")
                self.assertEqual(len(spans), 1, spans)
                s, e, k, _ = spans[0]
                self.assertEqual(k, kind)
                self.assertEqual(f"here it is: {tok} ok"[s:e], tok)

    def test_private_key(self):
        spans = detect("key:\n" + PRIVATE_KEY + "\nthanks")
        self.assertEqual([s[2] for s in spans], ["private_key"])

    def test_contextual_positives(self):
        for text, secret in POSITIVE_TEXT:
            with self.subTest(text=text):
                red = scrub.apply_spans(text, detect(text))
                self.assertNotIn(secret, red)
                self.assertIn("[REDACTED:", red)

    def test_negatives(self):
        for text in NEGATIVE_TEXT:
            with self.subTest(text=text):
                self.assertEqual(detect(text), [], scrub.apply_spans(text, detect(text)))

    def test_idempotent(self):
        text = "DB_PASSWORD=S3cr3tPa55 and " + FAKES["github_token"]
        once = scrub.apply_spans(text, detect(text))
        self.assertEqual(detect(once), [])

    def test_literals(self):
        spans = detect("I typed hunterzz twice: hunterzz", literals=["hunterzz"])
        self.assertEqual([s[2] for s in spans], ["literal", "literal"])

    def test_aggressive_only_for_humans(self):
        tok = "Qm7xR2pL9vT4nK8wZ3yB"
        self.assertEqual(detect(f"use {tok}"), [])
        self.assertEqual([s[2] for s in detect(f"use {tok}", aggressive=True)], ["high_entropy"])
        self.assertEqual(scrub.Detector(aggressive=True).spans(f"use {tok}", human=False), [])


def _rec(role, content, **extra):
    return {"type": role, "message": {"role": role, "content": content},
            "uuid": "u-" + FAKES["github_token"][:6], "sessionId": "s", **extra}


class FileTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.f = self.dir / "session.jsonl"
        gh = FAKES["github_token"]
        records = [
            _rec("user", f"here is my token {gh} and DB_PASSWORD=S3cr3tPa55 please use it"),
            _rec("assistant", [{"type": "thinking", "thinking": "ok", "signature": "EqQBCkgIAxABGAIiQL" + "x" * 40},
                               {"type": "text", "text": "Thanks, using it now."}]),
            _rec("user", [{"type": "tool_result", "tool_use_id": "t1",
                           "content": "DB_PASSWORD=S3cr3tPa55\nPORT=5432"}]),
            _rec("user", [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                        "data": "iVBOR" + A * 5}}]),
            {"type": "ai-title", "aiTitle": "Set up the deploy — naïve café ✓", "sessionId": "s"},
        ]
        self.lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in records]
        self.f.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        old = time.time() - 3600
        os.utime(self.f, (old, old))
        self.mtime = self.f.stat().st_mtime_ns

    def run_main(self, *args):
        return scrub.main(["--path", str(self.f), "--json", "--workers", "1",
                           "--report", str(self.dir / "report.md"), *args])

    def capture(self, *args):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            scrub.main(["--path", str(self.f), "--workers", "1", "--report", str(self.dir / "report.md"), *args])
        return buf.getvalue()

    def test_dry_run_report_has_table_and_next_steps(self):
        for fmt, marker in (("text", "┌"), ("markdown", "|---")):
            out = self.capture("--format", fmt)
            self.assertIn(marker, out)
            self.assertIn("github_token", out)
            self.assertIn("certain", out)
            self.assertRegex(out, r"(?i)next steps")
            self.assertIn("--apply", out)
            self.assertNotIn(FAKES["github_token"], out)

    def test_apply_report_shows_replacements_and_is_saved(self):
        out = self.capture("--apply")
        self.assertIn("[REDACTED:github_token]", out)
        self.assertIn("[REDACTED:password]", out)
        self.assertIn("0 secrets left", out)
        saved = (self.dir / "report.md").read_text()
        self.assertIn("[REDACTED:github_token]", saved)
        self.assertNotIn(FAKES["github_token"], saved + out)
        self.assertNotIn("S3cr3tPa55", saved + out)

    def test_dry_run_does_not_write(self):
        before = self.f.read_bytes()
        rc = self.run_main()
        self.assertEqual(rc, 1)
        self.assertEqual(self.f.read_bytes(), before)

    def test_apply(self):
        rc = self.run_main("--apply")
        self.assertEqual(rc, 0)
        out = self.f.read_text(encoding="utf-8")
        self.assertNotIn(FAKES["github_token"], out)
        self.assertNotIn("S3cr3tPa55", out)
        self.assertIn("[REDACTED:github_token]", out)
        self.assertIn("[REDACTED:password]", out)
        new_lines = out.split("\n")
        self.assertEqual(len(new_lines), len(self.lines) + 1)
        for ln in new_lines[:-1]:
            json.loads(ln)
        # untouched lines are byte-identical: thinking signature, base64 image, unicode title
        self.assertEqual(new_lines[1], self.lines[1])
        self.assertEqual(new_lines[3], self.lines[3])
        self.assertEqual(new_lines[4], self.lines[4])
        # mtime preserved so the session list order does not change
        self.assertEqual(self.f.stat().st_mtime_ns, self.mtime)
        # second run finds nothing
        self.assertEqual(self.run_main(), 0)

    def test_active_file_skipped(self):
        os.utime(self.f, None)  # now
        before = self.f.read_bytes()
        scrub.main(["--path", str(self.f), "--apply", "--workers", "1", "--json", "--no-report-file"])
        self.assertEqual(self.f.read_bytes(), before)

    def test_kinds_filter_snippet_hides_other_secrets(self):
        import io
        from contextlib import redirect_stdout
        for flag in (["--kinds", "github_token"], ["--kinds", "high_entropy", "--aggressive"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                scrub.main(["--path", str(self.f), "--workers", "1", "--no-report-file", *flag])
            self.assertNotIn("S3cr3tPa55", buf.getvalue(), flag)
            self.assertNotIn(FAKES["github_token"], buf.getvalue(), flag)

    def test_report_never_contains_secret(self):
        import io
        from contextlib import redirect_stdout
        for flag in ([], ["--json"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                scrub.main(["--path", str(self.f), "--workers", "1", "--no-report-file", *flag])
            out = buf.getvalue()
            self.assertNotIn(FAKES["github_token"], out)
            self.assertNotIn("S3cr3tPa55", out)
            self.assertIn("github_token", out)


if __name__ == "__main__":
    unittest.main()
