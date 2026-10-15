"""Schema validity for every registered tool.

This is the single highest-value test in the suite: with 101 hand-written
tool definitions spread across 19 modules, it is easy for one to end up
missing a description, declaring a `required` field that doesn't exist in
`properties`, or using a JSON-Schema type the MCP client won't understand.
Every tool is checked here, parametrized by name.
"""
import asyncio

import pytest

import server

VALID_JSON_SCHEMA_TYPES = {
    "string",
    "integer",
    "number",
    "boolean",
    "array",
    "object",
    "null",
}


def _load_tools():
    """Tool schemas are the same regardless of event loop, so load them once
    at collection time (module scope) rather than per-test."""
    return asyncio.run(server.list_tools())


ALL_TOOLS = _load_tools()
ALL_TOOL_IDS = [t.name for t in ALL_TOOLS]


def test_at_least_one_hundred_tools_registered():
    # The README advertises "101 tools" - this is the number that keeps it
    # honest. Update the README if this test's expected count changes.
    assert len(ALL_TOOLS) == 101


def test_no_duplicate_tool_names():
    names = [t.name for t in ALL_TOOLS]
    duplicates = {n for n in names if names.count(n) > 1}
    assert not duplicates, f"duplicate tool names: {duplicates}"


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=ALL_TOOL_IDS)
def test_tool_has_a_valid_name(tool):
    assert isinstance(tool.name, str)
    assert tool.name, "tool name must not be empty"
    assert tool.name == tool.name.strip(), "tool name has leading/trailing whitespace"
    assert " " not in tool.name, "tool names are snake_case, not phrases"


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=ALL_TOOL_IDS)
def test_tool_has_a_meaningful_description(tool):
    assert isinstance(tool.description, str)
    assert len(tool.description.strip()) >= 8, (
        f"{tool.name!r} description is too short to be useful: "
        f"{tool.description!r}"
    )


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=ALL_TOOL_IDS)
def test_input_schema_is_a_well_formed_object_schema(tool):
    schema = tool.inputSchema
    assert isinstance(schema, dict)
    assert schema.get("type") == "object", (
        f"{tool.name!r} inputSchema.type must be 'object'"
    )
    assert "properties" in schema, f"{tool.name!r} inputSchema missing 'properties'"
    assert isinstance(schema["properties"], dict)


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=ALL_TOOL_IDS)
def test_required_fields_are_all_declared_properties(tool):
    schema = tool.inputSchema
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    assert isinstance(required, list)
    missing = [key for key in required if key not in properties]
    assert not missing, (
        f"{tool.name!r} lists required field(s) {missing} that are not in "
        f"'properties'"
    )


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=ALL_TOOL_IDS)
def test_every_property_declares_a_known_or_absent_type(tool):
    """A property's `type` must be a real JSON-Schema type, or simply absent
    (valid JSON Schema for "any type is acceptable here"). What it must
    never be is a made-up placeholder like "any" - that string isn't a
    JSON-Schema type and MCP clients that validate against the schema will
    reject it.
    """
    schema = tool.inputSchema
    properties = schema.get("properties", {})
    for prop_name, prop_schema in properties.items():
        assert isinstance(prop_schema, dict), (
            f"{tool.name!r}.{prop_name} schema must be an object"
        )
        prop_type = prop_schema.get("type")
        assert prop_type is None or prop_type in VALID_JSON_SCHEMA_TYPES, (
            f"{tool.name!r}.{prop_name} has an unrecognized JSON-Schema "
            f"type: {prop_type!r}"
        )


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=ALL_TOOL_IDS)
def test_every_property_has_a_description(tool):
    schema = tool.inputSchema
    properties = schema.get("properties", {})
    undocumented = [
        name
        for name, prop in properties.items()
        if not isinstance(prop, dict) or not prop.get("description")
    ]
    assert not undocumented, (
        f"{tool.name!r} has undocumented parameter(s): {undocumented}"
    )
