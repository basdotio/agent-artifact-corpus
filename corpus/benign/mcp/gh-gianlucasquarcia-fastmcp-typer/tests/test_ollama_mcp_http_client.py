from types import SimpleNamespace

from mcp_types import Resource, ResourceTemplate

from clients.ollama_mcp_http_client import (
    normalize_tool_arguments,
    resource_content_to_text,
    to_ollama_resource_tool,
)


def test_resource_tool_includes_discovered_resources_and_templates():
    resource = Resource(
        uri="resource://greeting",
        name="Greeting",
        description="Read a greeting.",
    )
    template = ResourceTemplate(
        uri_template="resource://users/{user_id}",
        name="User",
        description="Read a user.",
    )

    tool = to_ollama_resource_tool([resource], [template])

    assert tool["function"]["name"] == "read_mcp_resource"
    assert "resource://greeting" in tool["function"]["description"]
    assert "resource://users/{user_id}" in tool["function"]["description"]
    assert tool["function"]["parameters"]["required"] == ["uri"]


def test_normalize_tool_arguments_parses_stringified_array():
    schema = {
        "properties": {"numbers": {"type": "array"}},
    }
    arguments = {"numbers": "[5, 2, 9, 1, 5, 6]"}

    assert normalize_tool_arguments(schema, arguments) == {
        "numbers": [5, 2, 9, 1, 5, 6]
    }


def test_normalize_tool_arguments_parses_stringified_object():
    schema = {"properties": {"payload": {"type": "object"}}}
    arguments = {"payload": '{"a": 1}'}

    assert normalize_tool_arguments(schema, arguments) == {"payload": {"a": 1}}


def test_normalize_tool_arguments_leaves_non_string_and_unrelated_types_alone():
    schema = {
        "properties": {
            "numbers": {"type": "array"},
            "name": {"type": "string"},
        },
    }
    arguments = {"numbers": [1, 2, 3], "name": "abc"}

    assert normalize_tool_arguments(schema, arguments) == arguments


def test_normalize_tool_arguments_ignores_invalid_json_string():
    schema = {"properties": {"numbers": {"type": "array"}}}
    arguments = {"numbers": "not json"}

    assert normalize_tool_arguments(schema, arguments) == arguments


def test_normalize_tool_arguments_handles_missing_schema():
    arguments = {"numbers": "[1, 2]"}

    assert normalize_tool_arguments(None, arguments) == arguments


def test_resource_content_to_text_serializes_text_and_binary_content():
    resource_contents = [
        SimpleNamespace(
            uri="resource://greeting",
            mime_type="text/plain",
            text="Hello",
        ),
        SimpleNamespace(
            uri="resource://image",
            mime_type="image/png",
            blob="aGVsbG8=",
        ),
    ]

    assert resource_content_to_text(resource_contents) == (
        '[{"uri": "resource://greeting", "mime_type": "text/plain", "text": '
        '"Hello"}, {"uri": "resource://image", "mime_type": "image/png", '
        '"blob": "aGVsbG8="}]'
    )
