"""Tests for the background triage loop's pure helpers. No live Ollama calls."""

import json
import logging
import os
import sys
import unittest

# triage_loop lives in loops/ (not a package); add it to sys.path.
_LOOPS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "loops"
)
if _LOOPS_DIR not in sys.path:
    sys.path.insert(0, _LOOPS_DIR)

import triage_loop  # noqa: E402


class TestParseFlags(unittest.TestCase):
    def test_none_token_skipped(self):
        self.assertEqual(triage_loop.parse_flags("NONE"), [])

    def test_empty_output_returns_empty(self):
        self.assertEqual(triage_loop.parse_flags(""), [])

    def test_non_json_lines_skipped(self):
        self.assertEqual(triage_loop.parse_flags("not json at all"), [])

    def test_unknown_severity_normalized_to_medium(self):
        out = '{"severity": "CRITICAL", "line": "boom", "reason": "x"}'
        flags = triage_loop.parse_flags(out)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "medium")
        self.assertEqual(flags[0]["line"], "boom")

    def test_valid_severity_lowercased(self):
        out = '{"severity": "High", "line": "boom", "reason": "x"}'
        flags = triage_loop.parse_flags(out)
        self.assertEqual(flags[0]["severity"], "high")

    def test_flag_without_line_dropped(self):
        out = '{"severity": "high", "reason": "no line here"}'
        self.assertEqual(triage_loop.parse_flags(out), [])


class TestSaveOffsetsAtomic(unittest.TestCase):
    def test_round_trips_and_leaves_no_tmp(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            offsets_file = os.path.join(tmp, "state", "offsets.json")
            data = {"C:\\a.log": {"offset": 12, "size": 30}}
            triage_loop.save_offsets(offsets_file, data)
            self.assertEqual(triage_loop.load_offsets(offsets_file), data)
            self.assertFalse(os.path.exists(offsets_file + ".tmp"))


class TestBuildPrompt(unittest.TestCase):
    def test_log_data_is_fenced(self):
        prompt = triage_loop.build_prompt("some log line")
        self.assertIn(triage_loop._LOG_BEGIN, prompt)
        self.assertIn(triage_loop._LOG_END, prompt)
        self.assertIn("some log line", prompt)


class TestProcessPathResilience(unittest.TestCase):
    def _write(self, path, text):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def _config(self, tmp, **overrides):
        config = {
            "ollama_url": "http://localhost:11434/api/generate",
            "model": "test-model",
            "alerts_file": os.path.join(tmp, "state", "llm_alerts.jsonl"),
            "request_timeout_seconds": 5,
        }
        config.update(overrides)
        return config

    def test_batch_cap_limits_whole_line_read(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "test.log")
            # Three 300-byte lines; a 650-byte cap admits two whole lines (600 B)
            # and never a partial third line (whole-line batching).
            with open(log_path, "wb") as handle:
                handle.write((b"A" * 299 + b"\n") * 3)

            config = self._config(tmp, max_chars_per_call=650)
            logger = logging.getLogger("test_triage_resilience")
            offsets = {}

            with patch.object(triage_loop, "call_ollama",
                              return_value=triage_loop.OllamaResult(
                                  "ok", "NONE", "stop", 10, "")):
                triage_loop.process_path(log_path, offsets, config, logger)

            abs_path = triage_loop.resolve_path(log_path)
            self.assertEqual(offsets[abs_path]["offset"], 600)   # two whole lines
            self.assertEqual(offsets[abs_path]["consecutive_failures"], 0)

    def test_failure_does_not_advance_offset_below_threshold(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "test.log")
            self._write(log_path, "some new log content\n")

            config = self._config(tmp, max_consecutive_failures=5)
            logger = logging.getLogger("test_triage_resilience")
            offsets = {}

            with patch.object(triage_loop, "call_ollama",
                              return_value=triage_loop.OllamaResult(
                                  "outage", None, None, None, "refused")):
                triage_loop.process_path(log_path, offsets, config, logger)

            abs_path = triage_loop.resolve_path(log_path)
            self.assertEqual(offsets[abs_path]["offset"], 0)
            self.assertEqual(offsets[abs_path]["consecutive_failures"], 1)

    def test_offset_skips_forward_after_max_consecutive_failures(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "test.log")
            text = b"some new log content\n"          # 21 bytes, one whole line
            with open(log_path, "wb") as handle:
                handle.write(text)

            alerts_file = os.path.join(tmp, "state", "llm_alerts.jsonl")
            config = self._config(tmp, max_consecutive_failures=3)
            logger = logging.getLogger("test_triage_resilience")
            abs_path = triage_loop.resolve_path(log_path)
            offsets = {abs_path: {"offset": 0, "size": 0, "consecutive_failures": 2}}

            with patch.object(triage_loop, "call_ollama",
                              return_value=triage_loop.OllamaResult(
                                  "outage", None, None, None, "refused")):
                triage_loop.process_path(log_path, offsets, config, logger)

            self.assertEqual(offsets[abs_path]["offset"], len(text))
            self.assertEqual(offsets[abs_path]["consecutive_failures"], 0)

            with open(alerts_file, "r", encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["severity"], "high")
            self.assertIn("consecutive triage failures", records[0]["reason"])


class TestParseFailClosed(unittest.TestCase):
    """Fail direction: CLOSED -- malformed model output is never a clean batch."""

    def test_parse_flags_with_counts_counts_junk(self):
        flags, junk = triage_loop.parse_flags_with_counts(
            'garbage line\n{"severity": "high", "line": "x", "reason": "r"}\n[1,2]\n')
        self.assertEqual(len(flags), 1)
        self.assertEqual(junk, 2)

    def test_total_parse_failure_holds_offset_and_alerts(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "test.log")
            with open(log_path, "w", encoding="utf-8") as h:
                h.write("some new log content\n")
            alerts_file = os.path.join(tmp, "state", "llm_alerts.jsonl")
            config = {"ollama_url": "u", "model": "m", "alerts_file": alerts_file,
                      "request_timeout_seconds": 5, "max_consecutive_failures": 5}
            logger = logging.getLogger("t")
            offsets = {}
            with patch.object(triage_loop, "call_ollama",
                              return_value=triage_loop.OllamaResult(
                                  "ok", "I think everything looks fine!",
                                  "stop", 20, "")):
                triage_loop.process_path(log_path, offsets, config, logger)
            abs_path = triage_loop.resolve_path(log_path)
            self.assertEqual(offsets[abs_path]["offset"], 0)              # HELD
            self.assertEqual(offsets[abs_path]["consecutive_failures"], 1)
            with open(alerts_file, "r", encoding="utf-8") as h:
                records = [json.loads(line) for line in h]
            self.assertEqual(len(records), 1)                             # loud
            self.assertIn("parse failure", records[0]["reason"].lower())
            self.assertEqual(records[0]["severity"], "high")

    def test_empty_model_output_is_a_failure_not_clean(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "test.log")
            with open(log_path, "w", encoding="utf-8") as h:
                h.write("content\n")
            config = {"ollama_url": "u", "model": "m",
                      "alerts_file": os.path.join(tmp, "state", "a.jsonl"),
                      "request_timeout_seconds": 5, "max_consecutive_failures": 5}
            offsets = {}
            with patch.object(triage_loop, "call_ollama",
                              return_value=triage_loop.OllamaResult(
                                  "empty", "   ", None, None, "blank")):
                triage_loop.process_path(log_path, offsets, config,
                                         logging.getLogger("t"))
            abs_path = triage_loop.resolve_path(log_path)
            self.assertEqual(offsets[abs_path]["offset"], 0)
            self.assertEqual(offsets[abs_path]["consecutive_failures"], 1)

    def test_partial_parse_commits_with_parse_partial_alert(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "test.log")
            text = b"content\n"
            with open(log_path, "wb") as h:
                h.write(text)
            alerts_file = os.path.join(tmp, "state", "a.jsonl")
            config = {"ollama_url": "u", "model": "m", "alerts_file": alerts_file,
                      "request_timeout_seconds": 5, "max_consecutive_failures": 5}
            out = '{"severity": "high", "line": "x", "reason": "r"}\njunk here\n'
            offsets = {}
            with patch.object(triage_loop, "call_ollama",
                              return_value=triage_loop.OllamaResult(
                                  "ok", out, "stop", 20, "")):
                triage_loop.process_path(log_path, offsets, config,
                                         logging.getLogger("t"))
            abs_path = triage_loop.resolve_path(log_path)
            self.assertEqual(offsets[abs_path]["offset"], len(text))      # committed
            with open(alerts_file, "r", encoding="utf-8") as h:
                records = [json.loads(line) for line in h]
            reasons = " ".join(r["reason"] for r in records).lower()
            self.assertEqual(len(records), 2)                             # flag + partial note
            self.assertIn("parse partial", reasons)


class TestPassthroughLane(unittest.TestCase):
    """Deterministic pass-through for structured *alerts.jsonl sources."""

    def test_is_passthrough_matches_glob_default_off(self):
        self.assertFalse(triage_loop.is_passthrough(r"C:\x\alerts.jsonl", {}))
        cfg = {"passthrough_globs": ["*alerts.jsonl"]}
        self.assertTrue(triage_loop.is_passthrough(r"C:\x\alerts.jsonl", cfg))
        self.assertTrue(triage_loop.is_passthrough(r"C:\x\llm_alerts.jsonl", cfg))
        self.assertFalse(triage_loop.is_passthrough(r"C:\x\worker.log", cfg))

    def test_passthrough_flags_maps_severity_fail_closed(self):
        lines = [
            '{"severity": "WARNING", "reason": "queue_stalled", "component": "a"}',
            '{"severity": "CRITICAL", "reason": "service_restart"}',
            '{"reason": "no severity field"}',
            'not json at all',
        ]
        flags, malformed = triage_loop.passthrough_flags(lines)
        self.assertEqual([f["severity"] for f in flags],
                         ["medium", "high", "high", "high"])   # unknown/missing -> high
        self.assertEqual(malformed, 1)
        self.assertIn("queue_stalled", flags[0]["reason"])

    def test_passthrough_process_path_never_calls_ollama_and_consumes_whole_lines(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "alerts.jsonl")
            whole = '{"severity": "WARNING", "reason": "r1"}\n'
            partial = '{"severity": "ERR'                     # producer mid-write
            # newline="" disables Windows' text-mode \n -> \r\n translation so
            # the on-disk bytes match `whole + partial` exactly (this test
            # asserts an exact byte offset against the literal content above).
            with open(log_path, "w", encoding="utf-8", newline="") as h:
                h.write(whole + partial)
            alerts_file = os.path.join(tmp, "state", "a.jsonl")
            config = {"ollama_url": "u", "model": "m", "alerts_file": alerts_file,
                      "request_timeout_seconds": 5,
                      "passthrough_globs": ["*alerts.jsonl"]}
            offsets = {}
            with patch.object(triage_loop, "call_ollama") as ollama:
                triage_loop.process_path(log_path, offsets, config,
                                         logging.getLogger("t"))
            ollama.assert_not_called()
            abs_path = triage_loop.resolve_path(log_path)
            self.assertEqual(offsets[abs_path]["offset"],
                             len(whole.encode("utf-8")))      # partial line NOT consumed
            with open(alerts_file, "r", encoding="utf-8") as h:
                records = [json.loads(line) for line in h]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["model"], "passthrough")


if __name__ == "__main__":
    unittest.main()
