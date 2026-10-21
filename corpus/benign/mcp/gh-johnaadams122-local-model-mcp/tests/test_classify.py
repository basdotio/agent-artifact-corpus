"""Tests for local_llm.classify. requests.post is patched so no live calls."""

import unittest
from unittest import mock

from local_llm import ollama_client
from local_llm.classify import classify


def _make_response(response_text):
    resp = mock.Mock()
    resp.status_code = 200
    resp.json.return_value = {"response": response_text}
    resp.text = ""
    return resp


CATEGORIES = ["positive", "negative", "neutral"]


class TestClassify(unittest.TestCase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_plain_json_parsed(self, mock_post):
        mock_post.return_value = _make_response(
            '{"label": "positive", "confidence": 0.9}'
        )
        result = classify("great product", CATEGORIES)
        self.assertEqual(result["label"], "positive")
        self.assertEqual(result["confidence"], 0.9)

    @mock.patch.object(ollama_client.requests, "post")
    def test_fenced_json_parsed(self, mock_post):
        fenced = '```json\n{"label": "negative", "confidence": 0.7}\n```'
        mock_post.return_value = _make_response(fenced)
        result = classify("terrible", CATEGORIES)
        self.assertEqual(result["label"], "negative")
        self.assertEqual(result["confidence"], 0.7)

    @mock.patch.object(ollama_client.requests, "post")
    def test_confidence_above_one_clamped(self, mock_post):
        mock_post.return_value = _make_response(
            '{"label": "neutral", "confidence": 1.5}'
        )
        result = classify("ok", CATEGORIES)
        self.assertEqual(result["confidence"], 1.0)

    @mock.patch.object(ollama_client.requests, "post")
    def test_label_not_in_categories_raises(self, mock_post):
        mock_post.return_value = _make_response(
            '{"label": "spam", "confidence": 0.5}'
        )
        with self.assertRaises(ValueError):
            classify("buy now", CATEGORIES)

    @mock.patch.object(ollama_client.requests, "post")
    def test_case_insensitive_label_normalized(self, mock_post):
        mock_post.return_value = _make_response(
            '{"label": "POSITIVE", "confidence": 0.8}'
        )
        result = classify("nice", CATEGORIES)
        self.assertEqual(result["label"], "positive")

    @mock.patch.object(ollama_client.requests, "post")
    def test_nan_confidence_raises(self, mock_post):
        # NaN fails both '< 0.0' and '> 1.0', so a bounds check alone lets it
        # through. Python's json module accepts the bare NaN literal.
        mock_post.return_value = _make_response(
            '{"label": "positive", "confidence": NaN}'
        )
        with self.assertRaises(ValueError):
            classify("great product", CATEGORIES)

    @mock.patch.object(ollama_client.requests, "post")
    def test_string_nan_confidence_raises(self, mock_post):
        mock_post.return_value = _make_response(
            '{"label": "positive", "confidence": "nan"}'
        )
        with self.assertRaises(ValueError):
            classify("great product", CATEGORIES)

    @mock.patch.object(ollama_client.requests, "post")
    def test_infinite_confidence_raises(self, mock_post):
        mock_post.return_value = _make_response(
            '{"label": "positive", "confidence": Infinity}'
        )
        with self.assertRaises(ValueError):
            classify("great product", CATEGORIES)

    @mock.patch.object(ollama_client.requests, "post")
    def test_negative_infinite_confidence_raises(self, mock_post):
        mock_post.return_value = _make_response(
            '{"label": "positive", "confidence": -Infinity}'
        )
        with self.assertRaises(ValueError):
            classify("great product", CATEGORIES)

    @mock.patch.object(ollama_client.requests, "post")
    def test_overflowing_integer_confidence_is_treated_as_unparseable(self, mock_post):
        # float() of a huge integer raises OverflowError; it is handled like any
        # other unparseable confidence (0.0) instead of escaping as an exception.
        mock_post.return_value = _make_response(
            '{"label": "positive", "confidence": 1' + "0" * 400 + '}'
        )
        result = classify("great product", CATEGORIES)
        self.assertEqual(result, {"label": "positive", "confidence": 0.0})

    @mock.patch.object(ollama_client.requests, "post")
    def test_non_object_json_raises_value_error(self, mock_post):
        # Valid JSON that is not an object raises the documented ValueError,
        # not AttributeError.
        for reply in ('["positive", 0.9]', '"positive"', 'null'):
            with self.subTest(reply=reply):
                mock_post.return_value = _make_response(reply)
                with self.assertRaises(ValueError):
                    classify("great product", CATEGORIES)

    def test_empty_categories_raises(self):
        with self.assertRaises(ValueError):
            classify("text", [])


if __name__ == "__main__":
    unittest.main()
