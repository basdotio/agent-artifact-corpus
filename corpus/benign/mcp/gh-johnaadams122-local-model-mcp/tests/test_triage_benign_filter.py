"""Tests for the benign-line prefilter in the background triage loop."""

import logging
import os
import sys
import unittest
from unittest import mock

_LOOPS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "loops"
)
if _LOOPS_DIR not in sys.path:
    sys.path.insert(0, _LOOPS_DIR)

import triage_loop  # noqa: E402

_LOGGER = logging.getLogger("test_benign")
_LOGGER.addHandler(logging.NullHandler())

_HEARTBEAT = (r"^\d{4}-\d{2}-\d{2} .* INFO __main__ heartbeat service=\S+ "
              r"processed=\d+ queued=\d+ errors=\d+$")


def _settings(**overrides):
    base = dict(model="qwen2.5:7b", ollama_url="http://x/api/generate",
                timeout=120, num_ctx=32768, think=False, batch_cap=12000,
                min_batch_chars=512, time_budget=100,
                max_consecutive_failures=5)
    base.update(overrides)
    return triage_loop.LlmSettings(**base)


class TestCompileBenignRegexes(unittest.TestCase):
    def test_absent_key_means_no_patterns(self):
        self.assertEqual(
            triage_loop.compile_benign_regexes({}, r"C:\x\example-service.log"),
            [])

    def test_glob_match_selects_patterns(self):
        config = {"benign_line_regexes": {"example-service.log": [_HEARTBEAT]}}
        pats = triage_loop.compile_benign_regexes(
            config, r"C:\x\example-service.log")
        self.assertEqual(len(pats), 1)

    def test_other_basename_gets_no_patterns(self):
        config = {"benign_line_regexes": {"example-service.log": [_HEARTBEAT]}}
        self.assertEqual(
            triage_loop.compile_benign_regexes(config, r"C:\x\worker.log"), [])

    def test_invalid_regex_fails_closed(self):
        config = {"benign_line_regexes": {"*.log": ["("]}}
        with self.assertRaises(triage_loop.TriageConfigError):
            triage_loop.compile_benign_regexes(config, r"C:\x\a.log")

    def test_non_dict_table_fails_closed(self):
        with self.assertRaises(triage_loop.TriageConfigError):
            triage_loop.compile_benign_regexes(
                {"benign_line_regexes": ["x"]}, r"C:\x\a.log")

    def test_non_list_value_fails_closed(self):
        with self.assertRaises(triage_loop.TriageConfigError):
            triage_loop.compile_benign_regexes(
                {"benign_line_regexes": {"*.log": "notalist"}}, r"C:\x\a.log")

    def test_non_string_regex_item_fails_closed(self):
        # re.compile(123) raises TypeError, not re.error; both must land on
        # the TriageConfigError fail-closed path.
        with self.assertRaises(triage_loop.TriageConfigError):
            triage_loop.compile_benign_regexes(
                {"benign_line_regexes": {"*.log": [123]}}, r"C:\x\a.log")


class TestFilterBenign(unittest.TestCase):
    def test_no_patterns_keeps_everything(self):
        lines = ["a\n", "b\n"]
        kept, benign = triage_loop.filter_benign(lines, [])
        self.assertEqual(kept, lines)
        self.assertEqual(benign, 0)

    def test_matching_lines_dropped_and_counted(self):
        import re
        pats = [re.compile(_HEARTBEAT)]
        hb = ("2026-01-01 00:00:00,000 INFO __main__ heartbeat service=example "
              "processed=10 queued=0 errors=0\n")
        err = "2026-01-01 00:01:00,000 ERROR __main__ feed crashed\n"
        kept, benign = triage_loop.filter_benign([hb, err, hb], pats)
        self.assertEqual(kept, [err])
        self.assertEqual(benign, 2)

    def test_a_pattern_must_match_the_WHOLE_line_not_just_a_prefix(self):
        # A heartbeat pattern with no end anchor must not hide a real failure
        # that merely STARTS with the heartbeat text.
        import re
        pats = [re.compile(r"^HEARTBEAT")]
        failing = "HEARTBEAT ERROR synthetic failure\n"
        plain = "HEARTBEAT\n"
        kept, benign = triage_loop.filter_benign([failing, plain], pats)
        self.assertEqual(kept, [failing])
        self.assertEqual(benign, 1)

    def test_a_trailing_CRLF_does_not_defeat_a_whole_line_match(self):
        import re
        pats = [re.compile(r"HEARTBEAT")]
        kept, benign = triage_loop.filter_benign(["HEARTBEAT\r\n"], pats)
        self.assertEqual((kept, benign), ([], 1))


class TestTriageBatchWithFilter(unittest.TestCase):
    def test_all_benign_batch_commits_without_model_call(self):
        import re
        pats = [re.compile(_HEARTBEAT)]
        hb = ("2026-01-01 00:00:00,000 INFO __main__ heartbeat service=example "
              "processed=10 queued=0 errors=0\n").encode()
        with mock.patch.object(triage_loop, "call_ollama") as mock_call:
            kind, detail = triage_loop.triage_llm_batch(
                [hb, hb], _settings(), {"alerts_file": "state/x.jsonl"},
                r"C:\x\example-service.log", _LOGGER, pats)
        self.assertEqual(kind, "committed")
        self.assertEqual(detail, len(hb) * 2)
        mock_call.assert_not_called()

    def test_mixed_batch_sends_only_non_benign_but_commits_all_bytes(self):
        import re
        pats = [re.compile(_HEARTBEAT)]
        hb = ("2026-01-01 00:00:00,000 INFO __main__ heartbeat service=example "
              "processed=10 queued=0 errors=0\n").encode()
        err = b"2026-01-01 00:01:00,000 ERROR __main__ feed crashed\n"
        captured = {}

        def fake_call(settings, prompt, logger):
            captured["prompt"] = prompt
            return triage_loop.OllamaResult("ok", "NONE", "stop", 100, "")

        with mock.patch.object(triage_loop, "call_ollama", fake_call):
            kind, detail = triage_loop.triage_llm_batch(
                [hb, err], _settings(), {"alerts_file": "state/x.jsonl"},
                r"C:\x\example-service.log", _LOGGER, pats)
        self.assertEqual(kind, "committed")
        self.assertEqual(detail, len(hb) + len(err), "ALL bytes committed")
        self.assertIn("feed crashed", captured["prompt"])
        self.assertNotIn("processed=", captured["prompt"],
                         "benign heartbeat must not reach the model")

    def test_no_patterns_behavior_unchanged(self):
        err = b"2026-01-01 00:01:00,000 ERROR __main__ feed crashed\n"

        def fake_call(settings, prompt, logger):
            return triage_loop.OllamaResult("ok", "NONE", "stop", 100, "")

        with mock.patch.object(triage_loop, "call_ollama", fake_call):
            kind, detail = triage_loop.triage_llm_batch(
                [err], _settings(), {"alerts_file": "state/x.jsonl"},
                r"C:\x\worker.log", _LOGGER, None)
        self.assertEqual(kind, "committed")
        self.assertEqual(detail, len(err))


if __name__ == "__main__":
    unittest.main()
