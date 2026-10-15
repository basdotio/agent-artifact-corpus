"""Regression tests for scripts/scan.py. Run: python -m unittest discover -s tests"""
import os
import subprocess
import sys
import json
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "scripts", "scan.py")
FIX = os.path.join(ROOT, "tests", "fixtures")


def run(target):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "out.json")
        proc = subprocess.run([sys.executable, SCAN, target, "--json", out], capture_output=True, text=True)
        with open(out) as f:
            return proc.returncode, json.load(f)


class ScanTests(unittest.TestCase):
    def test_bad_fixture_flags_core_checks(self):
        code, res = run(os.path.join(FIX, "bad"))
        self.assertEqual(code, 1)
        for key in ("1_coppa_age_gate", "2_google_fonts_ip_leak", "3_session_replay_wiretap",
                    "4_email_can_spam", "5_auto_renewal_disclosure", "6_dmca_safe_harbor"):
            self.assertEqual(res[key]["status"], "FAIL", key)
        self.assertEqual(res["9_dark_patterns"]["status"], "REVIEW")
        self.assertEqual(res["10_terms_of_service"]["status"], "FAIL")
        self.assertEqual(res["11_dpdp_engineering_controls"]["status"], "FAIL")

    def test_good_fixture_has_no_high(self):
        code, res = run(os.path.join(FIX, "good"))
        self.assertEqual(code, 0)
        self.assertEqual(res["2_google_fonts_ip_leak"]["status"], "PASS")
        self.assertEqual(res["3_session_replay_wiretap"]["status"], "PASS")
        self.assertEqual(res["9_dark_patterns"]["status"], "PASS")
        self.assertEqual(res["10_terms_of_service"]["status"], "REVIEW")
        self.assertEqual(res["10_terms_of_service"]["severity"], "LOW")

    def test_report_orders_checks_numerically(self):
        with tempfile.TemporaryDirectory() as d:
            md = os.path.join(d, "out.md")
            subprocess.run([sys.executable, SCAN, os.path.join(FIX, "bad"), "--md", md], capture_output=True, text=True)
            with open(md) as f:
                text = f.read()
        rows = [l for l in text.splitlines() if l.startswith("| ") and l[2:3].isdigit()]
        nums = [int(l.split("|")[1]) for l in rows]
        self.assertEqual(nums, list(range(1, 12)))

    def test_missing_dir_exits_2(self):
        proc = subprocess.run([sys.executable, SCAN, "/no/such/dir"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
