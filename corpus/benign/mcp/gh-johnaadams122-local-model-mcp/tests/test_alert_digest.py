"""Tests for the deterministic llm_alerts rollup (loops/alert_digest.py)."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

_LOOPS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "loops"
)
if _LOOPS_DIR not in sys.path:
    sys.path.insert(0, _LOOPS_DIR)

import alert_digest  # noqa: E402

_NOW = datetime(2026, 7, 22, 23, 0, tzinfo=timezone.utc)


def _rec(ts, source, severity, reason, line="the line"):
    return json.dumps({
        "timestamp": ts, "source": source, "severity": severity,
        "reason": reason, "line": line, "model": "qwen2.5:7b"})


class TestReasonClass(unittest.TestCase):
    def test_digits_masked(self):
        self.assertEqual(alert_digest.reason_class("HTTP 429 error at 15:31"),
                         alert_digest.reason_class("HTTP 429 error at 16:05"))

    def test_hex_ids_masked(self):
        a = alert_digest.reason_class("snapshot failed for job aaaaaaaaaaaa")
        b = alert_digest.reason_class("snapshot failed for job bbbbbbbbbbbb")
        self.assertEqual(a, b)

    def test_different_reasons_distinct(self):
        self.assertNotEqual(alert_digest.reason_class("HTTP 429 error"),
                            alert_digest.reason_class("Daily quota limit hit"))


class TestBuildRollup(unittest.TestCase):
    def _write_alerts(self, lines):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "llm_alerts.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return path

    def test_duplicates_collapse_and_modal_label(self):
        ts = _NOW.isoformat()
        path = self._write_alerts([
            _rec(ts, "w.log", "high", "HTTPError 429 Too Many Requests at 15:31"),
            _rec(ts, "w.log", "high", "HTTPError 429 Too Many Requests at 15:32"),
            _rec(ts, "w.log", "high", "HTTPError 429 Too Many Requests at 15:31"),
            _rec(ts, "w.log", "low", "Daily quota limit hit"),
        ])
        rollup = alert_digest.build_rollup(path, now=_NOW)
        self.assertEqual(rollup["records_in_window"], 4)
        self.assertEqual(rollup["group_count"], 2)
        g429 = [g for g in rollup["groups"] if "429" in g["label"]][0]
        self.assertEqual(g429["count"], 3)
        # modal verbatim reason: the 15:31 variant appeared twice
        self.assertEqual(g429["label"],
                         "HTTPError 429 Too Many Requests at 15:31")

    def test_high_severity_sorts_first(self):
        ts = _NOW.isoformat()
        path = self._write_alerts([
            _rec(ts, "w.log", "low", "minor thing"),
            _rec(ts, "w.log", "high", "major thing"),
        ])
        rollup = alert_digest.build_rollup(path, now=_NOW)
        self.assertEqual(rollup["groups"][0]["severity"], "high")

    def test_window_excludes_old_records(self):
        old = (_NOW - timedelta(days=10)).isoformat()
        ts = _NOW.isoformat()
        path = self._write_alerts([
            _rec(old, "w.log", "high", "ancient"),
            _rec(ts, "w.log", "high", "recent"),
        ])
        rollup = alert_digest.build_rollup(path, now=_NOW)
        self.assertEqual(rollup["records_in_window"], 1)
        self.assertEqual(rollup["groups"][0]["label"], "recent")

    def test_unparseable_timestamp_fails_open_into_window(self):
        path = self._write_alerts([
            _rec("not-a-timestamp", "w.log", "high", "kept anyway"),
        ])
        rollup = alert_digest.build_rollup(path, now=_NOW)
        self.assertEqual(rollup["records_in_window"], 1)

    def test_malformed_lines_counted_not_fatal(self):
        ts = _NOW.isoformat()
        path = self._write_alerts([
            "this is not json",
            _rec(ts, "w.log", "high", "fine"),
        ])
        rollup = alert_digest.build_rollup(path, now=_NOW)
        self.assertEqual(rollup["malformed_lines"], 1)
        self.assertEqual(rollup["records_in_window"], 1)

    def test_exemplar_is_verbatim(self):
        ts = _NOW.isoformat()
        line = "SYNTHETIC_TEST_ALERT job_id=SYNTH-JOB-001"
        path = self._write_alerts([_rec(ts, "w.log", "high", "reject", line)])
        rollup = alert_digest.build_rollup(path, now=_NOW)
        self.assertEqual(rollup["groups"][0]["exemplar_line"], line)

    def test_long_exemplar_carries_explicit_truncation_marker(self):
        # Explicit marker: no silent cut posing as verbatim.
        ts = _NOW.isoformat()
        line = "WARNING " + "y" * 600
        path = self._write_alerts([_rec(ts, "w.log", "high", "long", line)])
        rollup = alert_digest.build_rollup(path, now=_NOW)
        exemplar = rollup["groups"][0]["exemplar_line"]
        self.assertTrue(exemplar.endswith("...[TRUNCATED]"))
        self.assertTrue(exemplar.startswith("WARNING yyy"))

    def test_missing_file_empty_rollup(self):
        rollup = alert_digest.build_rollup(
            os.path.join(tempfile.mkdtemp(), "nope.jsonl"), now=_NOW)
        self.assertEqual(rollup["records_in_window"], 0)
        self.assertEqual(rollup["groups"], [])

    def test_write_rollup_atomic_and_readable(self):
        ts = _NOW.isoformat()
        path = self._write_alerts([_rec(ts, "w.log", "high", "thing")])
        out = os.path.join(os.path.dirname(path), "rollup.json")
        alert_digest.write_rollup(path, out)
        with open(out, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["schema"], "llm-alerts-rollup-v1")
        self.assertFalse(os.path.exists(out + ".tmp"))


if __name__ == "__main__":
    unittest.main()
