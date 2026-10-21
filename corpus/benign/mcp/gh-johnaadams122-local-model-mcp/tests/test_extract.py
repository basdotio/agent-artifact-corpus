"""Tests for local_llm.extract. requests.post is patched so no live calls. The
two-call retry is simulated by setting side_effect to a list of responses."""

import json
import unittest
from unittest import mock

from local_llm import ollama_client
from local_llm.extract import extract_json


def _make_response(response_text):
    resp = mock.Mock()
    resp.status_code = 200
    resp.json.return_value = {"response": response_text}
    resp.text = ""
    return resp


SCHEMA = {"name": "string", "age": "integer"}


class TestExtractJson(unittest.TestCase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_valid_json_returned(self, mock_post):
        mock_post.return_value = _make_response('{"name": "Ada", "age": 36}')
        result = extract_json("Ada is 36", SCHEMA)
        self.assertEqual(result, {"name": "Ada", "age": 36})

    @mock.patch.object(ollama_client.requests, "post")
    def test_fenced_json_stripped(self, mock_post):
        fenced = '```json\n{"name": "Bob", "age": 40}\n```'
        mock_post.return_value = _make_response(fenced)
        result = extract_json("Bob is 40", SCHEMA)
        self.assertEqual(result, {"name": "Bob", "age": 40})

    @mock.patch.object(ollama_client.requests, "post")
    def test_invalid_then_valid_retries_once(self, mock_post):
        mock_post.side_effect = [
            _make_response("not json at all"),
            _make_response('{"name": "Cleo", "age": 29}'),
        ]
        result = extract_json("Cleo is 29", SCHEMA)
        self.assertEqual(result, {"name": "Cleo", "age": 29})
        self.assertEqual(mock_post.call_count, 2)

    @mock.patch.object(ollama_client.requests, "post")
    def test_two_invalid_responses_raises(self, mock_post):
        mock_post.side_effect = [
            _make_response("garbage one"),
            _make_response("garbage two"),
        ]
        with self.assertRaises(ValueError):
            extract_json("nope", SCHEMA)
        self.assertEqual(mock_post.call_count, 2)

    @mock.patch.object(ollama_client.requests, "post")
    def test_non_object_json_retried_then_value_error(self, mock_post):
        # Syntactically valid JSON that is not an object is invalid output: it
        # gets the documented retry and then ValueError, never TypeError.
        mock_post.side_effect = [
            _make_response('["Ada", 36]'),
            _make_response('["Ada", 36]'),
        ]
        with self.assertRaises(ValueError):
            extract_json("Ada is 36", SCHEMA)
        self.assertEqual(mock_post.call_count, 2)

    @mock.patch.object(ollama_client.requests, "post")
    def test_non_object_json_then_valid_object_retries_once(self, mock_post):
        mock_post.side_effect = [
            _make_response('null'),
            _make_response('{"name": "Ada", "age": 36}'),
        ]
        result = extract_json("Ada is 36", SCHEMA)
        self.assertEqual(result, {"name": "Ada", "age": 36})
        self.assertEqual(mock_post.call_count, 2)

    def test_unknown_schema_type_raises(self):
        with self.assertRaises(ValueError):
            extract_json("text", {"field": "weirdtype"})


# Field names that Pydantic would otherwise treat specially: a leading
# underscore (private attribute, silently ignored), dunder names, names that
# shadow BaseModel attributes, and model_config (rejected outright).
_AWKWARD_NAMES = ("_id", "__dunder__", "_", "model_config", "model_fields",
                  "model_dump", "schema", "copy", "json", "name with space")


class TestAwkwardFieldNames(unittest.TestCase):
    @mock.patch.object(ollama_client.requests, "post")
    def test_every_valid_schema_key_round_trips(self, mock_post):
        for name in _AWKWARD_NAMES:
            with self.subTest(name=name):
                mock_post.reset_mock()
                mock_post.return_value = _make_response(
                    json.dumps({name: "kept"}))
                self.assertEqual(
                    extract_json("text", {name: "string"}), {name: "kept"})

    @mock.patch.object(ollama_client.requests, "post")
    def test_an_awkward_key_stays_REQUIRED(self, mock_post):
        # A reply without the field must be rejected like any other missing
        # required field, not silently turned into an empty result.
        for name in _AWKWARD_NAMES:
            with self.subTest(name=name):
                mock_post.reset_mock()
                mock_post.return_value = _make_response("{}")
                with self.assertRaises(ValueError):
                    extract_json("text", {name: "string"})
                self.assertEqual(mock_post.call_count, 2)

    @mock.patch.object(ollama_client.requests, "post")
    def test_awkward_and_ordinary_keys_together_keep_schema_order(
            self, mock_post):
        schema = {"_id": "string", "name": "string", "model_config": "integer",
                  "age": "integer"}
        reply = {"age": 36, "model_config": 7, "name": "Ada", "_id": "x1"}
        mock_post.return_value = _make_response(json.dumps(reply))
        result = extract_json("text", schema)
        self.assertEqual(result, reply)
        self.assertEqual(list(result), list(schema))

    @mock.patch.object(ollama_client.requests, "post")
    def test_types_are_still_enforced_for_an_awkward_key(self, mock_post):
        mock_post.return_value = _make_response('{"_id": "not a number"}')
        with self.assertRaises(ValueError):
            extract_json("text", {"_id": "integer"})


if __name__ == "__main__":
    unittest.main()
