"""Tests for local_llm.ollama_client. No live Ollama calls; requests.post is
patched at local_llm.ollama_client.requests.post."""

import unittest
from unittest import mock

import requests

from local_llm import ollama_client
from local_llm.ollama_client import OllamaError, generate


def _make_response(status_code=200, json_body=None, text=""):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.return_value = json_body if json_body is not None else {}
    resp.text = text
    return resp


class TestGenerate(unittest.TestCase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_connection_error_raises_ollama_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")
        with self.assertRaises(OllamaError):
            generate("hello")

    @mock.patch.object(ollama_client.requests, "post")
    def test_timeout_raises_ollama_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("timed out")
        with self.assertRaises(OllamaError):
            generate("hello")

    @mock.patch.object(ollama_client.requests, "post")
    def test_non_200_status_raises_ollama_error(self, mock_post):
        mock_post.return_value = _make_response(
            status_code=500, text="internal server error"
        )
        with self.assertRaises(OllamaError):
            generate("hello")

    @mock.patch.object(ollama_client.requests, "post")
    def test_200_returns_response_text(self, mock_post):
        mock_post.return_value = _make_response(
            status_code=200, json_body={"response": "hi"}
        )
        self.assertEqual(generate("hello"), "hi")

class TestGenerateDoesNotFollowRedirects(unittest.TestCase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_the_request_is_sent_with_redirects_disabled(self, mock_post):
        mock_post.return_value = _make_response(
            status_code=200, json_body={"response": "hi"})
        generate("hello")
        self.assertIs(mock_post.call_args.kwargs.get("allow_redirects"), False)

    @mock.patch.object(ollama_client.requests, "post")
    def test_a_redirect_is_a_clean_error_naming_the_redirect(self, mock_post):
        mock_post.return_value = _make_response(
            status_code=302, text="Found")
        with self.assertRaisesRegex(OllamaError, "redirect"):
            generate("hello")


def _raw_response(status_code, body):
    """A real requests.Response carrying 'body' bytes, so .json() runs the
    library's own decoder rather than a mock."""
    resp = requests.models.Response()
    resp.status_code = status_code
    resp._content = body
    resp.encoding = "utf-8"
    return resp


class TestGenerateMalformedBody(unittest.TestCase):
    """A 200 whose body is not a JSON object must surface as OllamaError, and
    the message must not echo the body."""

    def _assert_ollama_error_without_body(self, mock_post, body, marker):
        mock_post.return_value = _raw_response(200, body)
        with self.assertRaises(OllamaError) as ctx:
            generate("hello")
        if marker:
            self.assertNotIn(marker, str(ctx.exception))

    @mock.patch.object(ollama_client.requests, "post")
    def test_200_invalid_json_raises_ollama_error(self, mock_post):
        self._assert_ollama_error_without_body(
            mock_post, b"<html>synthetic gateway page</html>",
            "synthetic gateway page")

    @mock.patch.object(ollama_client.requests, "post")
    def test_200_empty_body_raises_ollama_error(self, mock_post):
        self._assert_ollama_error_without_body(mock_post, b"", None)

    @mock.patch.object(ollama_client.requests, "post")
    def test_200_json_array_raises_ollama_error(self, mock_post):
        self._assert_ollama_error_without_body(
            mock_post, b'["synthetic-array-item"]', "synthetic-array-item")

    @mock.patch.object(ollama_client.requests, "post")
    def test_200_json_null_raises_ollama_error(self, mock_post):
        self._assert_ollama_error_without_body(mock_post, b"null", None)

    @mock.patch.object(ollama_client.requests, "post")
    def test_200_non_text_response_field_raises_ollama_error(self, mock_post):
        self._assert_ollama_error_without_body(
            mock_post, b'{"response": null}', None)


class TestGenerateHardening(unittest.TestCase):
    """num_ctx + top-level truncate:false + model-agnostic overrides."""

    def _capture(self, mock_post):
        captured = {}

        def fake(url, json=None, timeout=None, allow_redirects=True):
            captured["json"] = json
            captured["url"] = url
            captured["timeout"] = timeout
            return _make_response(200, {"response": "ok"})

        mock_post.side_effect = fake
        return captured

    @mock.patch.object(ollama_client.requests, "post")
    def test_num_ctx_in_options_and_truncate_false_top_level(self, mock_post):
        captured = self._capture(mock_post)
        generate("hello")
        self.assertIs(captured["json"]["truncate"], False)       # TOP LEVEL
        self.assertNotIn("truncate", captured["json"]["options"])  # not in options
        self.assertEqual(captured["json"]["options"]["num_ctx"], ollama_client.NUM_CTX)

    @mock.patch.object(ollama_client.requests, "post")
    def test_think_included_by_default(self, mock_post):
        captured = self._capture(mock_post)
        generate("hello")
        self.assertIn("think", captured["json"])                 # default False

    @mock.patch.object(ollama_client.requests, "post")
    def test_think_omitted_when_none(self, mock_post):
        captured = self._capture(mock_post)
        generate("hello", think=None)
        self.assertNotIn("think", captured["json"])              # non-thinking model

    @mock.patch.object(ollama_client.requests, "post")
    def test_model_and_num_ctx_override(self, mock_post):
        captured = self._capture(mock_post)
        generate("hello", model="qwen2.5:7b", num_ctx=8192)
        self.assertEqual(captured["json"]["model"], "qwen2.5:7b")
        self.assertEqual(captured["json"]["options"]["num_ctx"], 8192)

    @mock.patch.object(ollama_client.requests, "post")
    def test_context_exceeded_400_raises_ollama_error(self, mock_post):
        mock_post.return_value = _make_response(
            status_code=400,
            text='{"error":{"type":"exceed_context_size_error"}}')
        with self.assertRaises(OllamaError):
            generate("hello")


if __name__ == "__main__":
    unittest.main()
