"""Tests for local_llm.summarize. requests.post is patched so no live calls."""

import unittest
from unittest import mock

from local_llm import ollama_client
from local_llm.ollama_client import OllamaError
from local_llm.summarize import summarize


def _make_response(json_body):
    resp = mock.Mock()
    resp.status_code = 200
    resp.json.return_value = json_body
    resp.text = ""
    return resp


class TestSummarize(unittest.TestCase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_returns_stripped_summary(self, mock_post):
        mock_post.return_value = _make_response({"response": "  a short summary  \n"})
        self.assertEqual(summarize("some long text", 10), "a short summary")

    @mock.patch.object(ollama_client.requests, "post")
    def test_empty_response_raises(self, mock_post):
        mock_post.return_value = _make_response({"response": "   \n"})
        with self.assertRaises(OllamaError):
            summarize("some long text", 10)

    def test_zero_max_words_raises(self):
        with self.assertRaises(ValueError):
            summarize("text", 0)

    def test_negative_max_words_raises(self):
        with self.assertRaises(ValueError):
            summarize("text", -5)


if __name__ == "__main__":
    unittest.main()
