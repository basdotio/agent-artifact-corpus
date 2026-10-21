from __future__ import annotations

import unittest

from approved_workflows import run_pipeline


class ApprovedWorkflowTests(unittest.TestCase):
    def test_normalize_uses_talkpipe(self):
        result = run_pipeline("normalize", ["  Hello \n   world ", "  Another    item "])
        self.assertEqual(result["results"], ["Hello world", "Another item"])
        self.assertEqual(result["engine"], "talkpipe")

    def test_literal_keyword_filter(self):
        result = run_pipeline("keyword_filter", ["TalkPipe", "Other", "talkpipe MCP"], needle="TALK")
        self.assertEqual(result["results"], ["TalkPipe", "talkpipe MCP"])

    def test_statistics(self):
        result = run_pipeline("text_statistics", ["  One   two three "])
        self.assertEqual(result["results"][0]["words"], 3)
        self.assertEqual(result["results"][0]["characters"], len("One two three"))

    def test_output_is_bounded(self):
        result = run_pipeline("normalize", [str(i) for i in range(80)], limit=3)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["results"], ["0", "1", "2"])

    def test_arbitrary_code_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "Unsupported workflow"):
            run_pipeline("__import__('os').system('echo injected')", ["a"])

    def test_input_limits(self):
        for items in (["a" * 4097], ["a"] * 101, [1]):
            with self.subTest(items=str(items)[:15]):
                with self.assertRaises(ValueError):
                    run_pipeline("normalize", items)
        for limit in (0, 100, True):
            with self.assertRaises(ValueError):
                run_pipeline("normalize", ["hello"], limit=limit)

    def test_keyword_required(self):
        with self.assertRaisesRegex(ValueError, "needle"):
            run_pipeline("keyword_filter", ["foo"])

    def test_empty(self):
        self.assertEqual(run_pipeline("normalize", [])["results"], [])


if __name__ == "__main__":
    unittest.main()
