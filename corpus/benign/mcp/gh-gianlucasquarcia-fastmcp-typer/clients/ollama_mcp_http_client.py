"""Bridge between a local Ollama model and this project's FastMCP server (HTTP transport).

Connects to an already-running FastMCP server over streamable-http (mirroring
`mcp_http_client.py`), exposes its tools and resources to an Ollama model, and
forwards tool calls and requested resource reads to the MCP server.

Usage:
    uv run mcp_server.py run --transport streamable-http --port 8000  # in one terminal
    uv run clients/ollama_mcp_http_client.py "What time is it?"       # in another
    uv run clients/ollama_mcp_http_client.py --verbose "What time is it?"

Only the model's final answer is printed. Every run appends a full trace
(tool calls, recoverable tool errors, final answer) to
``clients/ollama_mcp_http_client.log``. Pass ``--verbose`` (or ``-v``) to
also echo the tool calls and errors to stderr.

Requires a running Ollama daemon (``ollama serve``) with a tool-calling
capable model already pulled, e.g. ``ollama pull llama3.1``.
"""

import ast
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import ollama
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from mcp_types import Prompt as MCPPrompt
from mcp_types import Resource, ResourceTemplate
from mcp_types import Tool as MCPTool

SERVER_URL = "http://localhost:8000/mcp"
LOCAL_OLLAMA_MODEL = "llama3.1"  # Ollama model to use for tool calls
MAX_TOOL_ROUNDS = 10  # Safety guard against endless tool-call loops
PROMPT_URI_PREFIXES = ("resource://", "prompt://")

LOG_FILE = Path(__file__).with_suffix(".log")  # clients/ollama_mcp_http_client.log

logger = logging.getLogger("ollama_mcp_http_client")


def to_ollama_tool(tool: MCPTool) -> dict:
    """Convert an MCP tool definition into the tool schema Ollama expects."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


def to_ollama_resource_tool(
    resources: list[Resource], templates: list[ResourceTemplate]
) -> dict:
    """Expose MCP resource reads as an Ollama function call."""
    resource_details = [
        {
            "uri": str(resource.uri),
            "name": resource.name,
            "description": resource.description or "",
        }
        for resource in resources
    ]
    template_details = [
        {
            "uri_template": template.uri_template,
            "name": template.name,
            "description": template.description or "",
        }
        for template in templates
    ]
    description = (
        "Read a resource exposed by the MCP server. Use a URI from the resource "
        "catalog, or construct a URI that matches a resource template. "
        f"Resources: {json.dumps(resource_details)}. "
        f"Resource templates: {json.dumps(template_details)}."
    )
    return {
        "type": "function",
        "function": {
            "name": "read_mcp_resource",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "uri": {
                        "type": "string",
                        "description": "The MCP resource URI to read.",
                    }
                },
                "required": ["uri"],
            },
        },
    }


def to_ollama_prompt_tool(prompts: list[MCPPrompt]) -> dict:
    """Expose MCP prompts as an Ollama function call."""
    prompt_details = [
        {
            "name": prompt.name,
            "description": prompt.description or "",
            "arguments": [
                {
                    "name": argument.name,
                    "description": argument.description or "",
                    "required": argument.required,
                }
                for argument in (prompt.arguments or [])
            ],
        }
        for prompt in prompts
    ]
    description = (
        "Call a prompt exposed by the MCP server. Use a name from the prompt "
        "catalog. Prompts: "
        f"{json.dumps(prompt_details)}."
    )
    return {
        "type": "function",
        "function": {
            "name": "call_mcp_prompt",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The MCP prompt name to call.",
                    },
                    "arguments": {
                        "type": "object",
                        "description": (
                            "The arguments to pass to the MCP prompt. "
                            'Use a JSON object, e.g. {"arg1": 123, "arg2": true}.'
                        ),
                    },
                },
                "required": ["name", "arguments"],
            },
        },
    }


def prompt_messages_to_ollama(messages: list[Any]) -> list[dict]:
    """Convert rendered MCP prompt messages into Ollama chat messages."""
    return [
        {
            "role": (
                message.role.value
                if hasattr(message.role, "value")
                else str(message.role)
            ),
            "content": (
                message.content.text
                if hasattr(message.content, "text")
                else str(message.content)
            ),
        }
        for message in messages
    ]


def _parse_object(arguments: Any) -> dict:
    """Parse a JSON object or Python-style dict string emitted by a local model."""
    if isinstance(arguments, str):
        text = arguments.strip()
        try:
            arguments = json.loads(text) if text else {}
        except json.JSONDecodeError:
            # Local models sometimes emit a Python-style dict with single quotes.
            arguments = ast.literal_eval(text)
    if not isinstance(arguments, dict):
        raise TypeError("Arguments must be a JSON object.")
    return arguments


def _to_prompt_arguments(arguments: Any) -> dict[str, str]:
    """MCP prompt arguments are strings; JSON-encode any non-string values."""
    arguments = _parse_object(arguments)
    return {
        key: value if isinstance(value, str) else json.dumps(value)
        for key, value in arguments.items()
    }


def resolve_prompt_call(
    name: str, arguments: dict, prompt_names: set[str]
) -> tuple[str | None, dict[str, str]]:
    """Detect whether an Ollama function call targets an MCP prompt.

    Small local models do not always use the ``call_mcp_prompt`` wrapper: they
    may call the prompt name directly, or misuse ``read_mcp_resource`` with a
    prompt name (either as a ``resource://<prompt>`` URI or with no ``uri``).
    Returns ``(prompt_name, prompt_arguments)`` or ``(None, {})`` when the call
    is not a prompt request.
    """
    if name in prompt_names:
        return name, _to_prompt_arguments(arguments)

    if name == "call_mcp_prompt":
        prompt_name = arguments.get("name")
        if not prompt_name:
            raise ValueError("call_mcp_prompt requires a 'name' argument.")
        return str(prompt_name), _to_prompt_arguments(arguments.get("arguments", {}))

    if name == "read_mcp_resource" and isinstance(arguments.get("uri"), str):
        uri = arguments["uri"]
        for prefix in PROMPT_URI_PREFIXES:
            if uri.startswith(prefix) and uri[len(prefix) :] in prompt_names:
                nested = arguments.get("arguments", {})
                return uri[len(prefix) :], _to_prompt_arguments(nested)

    if name == "read_mcp_resource" and "uri" not in arguments:
        for key, value in arguments.items():
            if isinstance(value, str) and value in prompt_names:
                remaining = {k: v for k, v in arguments.items() if k != key}
                nested = remaining.pop("arguments", None)
                if isinstance(nested, dict):
                    remaining.update(nested)
                return value, _to_prompt_arguments(remaining)

    return None, {}


def extract_tool_calls(
    message: Any, callable_names: set[str]
) -> list[tuple[str, dict]]:
    """Return ``(name, arguments)`` pairs for the tool calls in an Ollama reply.

    Uses the structured ``tool_calls`` when present. Otherwise looks for a JSON
    tool call such as ``{"name": "...", "parameters": {...}}`` in the reply
    text (possibly surrounded by prose or code fences), which llama3.1
    sometimes emits instead of a real tool call.
    """
    if message.tool_calls:
        return [
            (call.function.name, dict(call.function.arguments or {}))
            for call in message.tool_calls
        ]

    text = message.content or ""
    decoder = json.JSONDecoder()
    index = text.find("{")
    while index != -1:
        try:
            payload, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            index = text.find("{", index + 1)
            continue
        if isinstance(payload, dict):
            name = payload.get("name")
            arguments = payload.get("parameters", payload.get("arguments", {}))
            if name in callable_names and isinstance(arguments, dict):
                return [(name, arguments)]
        index = text.find("{", end)
    return []


def resource_uri_as_tool(
    name: str, arguments: dict, resource_uris: set[str], tool_names: set[str]
) -> str | None:
    """Map a ``read_mcp_resource`` call on ``resource://<tool>`` to that tool.

    Local models sometimes confuse tools with resources and try to read a tool
    as if it were a resource. Real resource URIs are never remapped.
    """
    uri = arguments.get("uri")
    if name != "read_mcp_resource" or not isinstance(uri, str):
        return None
    if uri in resource_uris or not uri.startswith("resource://"):
        return None
    candidate = uri.removeprefix("resource://")
    return candidate if candidate in tool_names else None


def unwrap_tool_arguments(
    tool_name: str, input_schema: dict | None, arguments: dict
) -> dict:
    """Undo ``{"name"|"tool": ..., "arguments": {...}}`` wrapping of tool calls.

    After seeing the ``call_mcp_prompt`` schema, local models sometimes copy
    its wrapper shape when calling an ordinary tool. Unwrap it only when the
    tool's own schema does not declare the wrapper keys as parameters.
    """
    properties = (input_schema or {}).get("properties", {})
    if "arguments" not in arguments or "arguments" in properties:
        return arguments
    for key in ("name", "tool"):
        if key in arguments and (arguments[key] != tool_name or key in properties):
            return arguments
    extra_keys = set(arguments) - {"arguments", "name", "tool"}
    if extra_keys:
        return arguments
    return _parse_object(arguments["arguments"])


def drop_unknown_arguments(input_schema: dict | None, arguments: dict) -> dict:
    """Remove arguments the tool schema does not declare.

    Local models sometimes invent extra parameters (e.g. ``temp``), which the
    MCP server rejects as unexpected keyword arguments.
    """
    properties = (input_schema or {}).get("properties")
    if not properties or (input_schema or {}).get("additionalProperties") is True:
        return arguments
    unknown = set(arguments) - set(properties)
    if unknown:
        logger.info("Dropping unknown arguments %s", sorted(unknown))
    return {key: value for key, value in arguments.items() if key in properties}


def normalize_tool_arguments(input_schema: dict | None, arguments: dict) -> dict:
    """Coerce stringified array/object arguments back to their JSON types.

    Local Ollama models occasionally emit array- or object-typed tool
    arguments as their JSON-encoded string form (e.g. ``"[1, 2, 3]"``
    instead of ``[1, 2, 3]``). Parse those back to native Python values so
    the MCP server's argument validation does not reject the call.
    """
    if not input_schema:
        return arguments

    properties = input_schema.get("properties", {})
    normalized = dict(arguments)
    for key, value in arguments.items():
        if not isinstance(value, str):
            continue
        expected_type = properties.get(key, {}).get("type")
        if expected_type not in ("array", "object"):
            continue
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, (list, dict)):
            normalized[key] = parsed
    return normalized


def resource_content_to_text(resource_contents: list[Any]) -> str:
    """Serialize text and binary MCP resource content for an Ollama tool result."""
    contents = []
    for content in resource_contents:
        if hasattr(content, "text"):
            contents.append(
                {
                    "uri": str(content.uri),
                    "mime_type": content.mime_type,
                    "text": content.text,
                }
            )
        else:
            contents.append(
                {
                    "uri": str(content.uri),
                    "mime_type": content.mime_type,
                    "blob": content.blob,
                }
            )
    return json.dumps(contents)


async def run(prompt: str) -> None:
    mcp_client = Client(SERVER_URL)

    async with mcp_client:
        (
            tools_result,
            resources_result,
            templates_result,
            prompts_result,
        ) = await asyncio.gather(
            mcp_client.list_tools(),
            mcp_client.list_resources(),
            mcp_client.list_resource_templates(),
            mcp_client.list_prompts(),
        )
        # tools = tools_result.tools
        ollama_tools = [to_ollama_tool(tool) for tool in tools_result]
        ollama_tools.append(to_ollama_resource_tool(resources_result, templates_result))
        ollama_tools.append(to_ollama_prompt_tool(prompts_result))
        input_schemas_by_name = {tool.name: tool.input_schema for tool in tools_result}
        prompt_names = {mcp_prompt.name for mcp_prompt in prompts_result}

        messages = [
            {
                "role": "system",
                "content": (
                    "Use read_mcp_resource when a resource catalog entry is relevant. "
                    "Use call_mcp_prompt when an MCP prompt offers a suitable workflow; "
                    "follow the rendered prompt's instructions and use available tools "
                    "as needed."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = ollama.chat(
            model=LOCAL_OLLAMA_MODEL, messages=messages, tools=ollama_tools
        )
        messages.append(response.message)

        rounds = 0
        rendered_prompts: set[str] = set()
        resource_uris = {str(resource.uri) for resource in resources_result}
        callable_names = (
            set(input_schemas_by_name)
            | prompt_names
            | {"read_mcp_resource", "call_mcp_prompt"}
        )
        pending_calls = extract_tool_calls(response.message, callable_names)
        while pending_calls:
            rounds += 1
            if rounds > MAX_TOOL_ROUNDS:
                logger.warning("Stopping after %d tool-call rounds.", MAX_TOOL_ROUNDS)
                break
            rendered_prompt_messages: list[dict] = []
            for name, arguments in pending_calls:
                logger.info("-> calling tool '%s' with %s", name, arguments)
                try:
                    # Local models sometimes route a plain tool through the
                    # prompt wrapper, e.g. call_mcp_prompt(name=<tool>).
                    if (
                        name == "call_mcp_prompt"
                        and arguments.get("name") in input_schemas_by_name
                    ):
                        name = arguments["name"]
                        arguments = _parse_object(arguments.get("arguments", {}))
                    prompt_name, prompt_arguments = resolve_prompt_call(
                        name, arguments, prompt_names
                    )
                    tool_name = resource_uri_as_tool(
                        name, arguments, resource_uris, set(input_schemas_by_name)
                    )
                    if tool_name is not None:
                        name = tool_name
                        arguments = _parse_object(arguments.get("arguments", {}))
                    if prompt_name in rendered_prompts:
                        content = (
                            f"Prompt '{prompt_name}' is already loaded. Follow its "
                            "instructions using the available tools."
                        )
                    elif prompt_name is not None:
                        prompt_result = await mcp_client.get_prompt(
                            prompt_name, prompt_arguments
                        )
                        rendered_prompts.add(prompt_name)
                        rendered_prompt_messages.extend(
                            prompt_messages_to_ollama(prompt_result.messages)
                        )
                        content = (
                            f"Prompt '{prompt_name}' rendered. Follow its "
                            "instructions in the next message, calling tools as needed."
                        )
                    elif name == "read_mcp_resource":
                        uri = arguments.get("uri")
                        if not uri:
                            raise ValueError(
                                "read_mcp_resource requires a 'uri' argument "
                                "taken from the resource catalog."
                            )
                        resource_result = await mcp_client.read_resource(str(uri))
                        content = resource_content_to_text(resource_result)
                    else:
                        input_schema = input_schemas_by_name.get(name)
                        call_arguments = normalize_tool_arguments(
                            input_schema,
                            drop_unknown_arguments(
                                input_schema,
                                unwrap_tool_arguments(name, input_schema, arguments),
                            ),
                        )
                        result = await mcp_client.call_tool(name, call_arguments)
                        content = json.dumps(result.structured_content)
                except (
                    ToolError,
                    MCPError,
                    ValueError,
                    TypeError,
                    SyntaxError,
                ) as error:
                    content = f"Error calling '{name}': {error}"
                    logger.info("%s", content)
                messages.append(
                    {
                        "role": "tool",
                        "content": content,
                        "tool_name": name,
                    }
                )

            # Rendered prompts are injected as real conversation messages so the
            # model follows them instead of treating them as opaque tool output.
            # Once a prompt workflow is selected, stop offering the prompt tool so
            # the model moves on to real tools instead of re-rendering the prompt.
            if rendered_prompt_messages:
                messages.extend(rendered_prompt_messages)
                # The rendered prompt is now the latest user message, so small
                # models tend to treat it as the whole task. Restate the original
                # request so every part of it still gets answered.
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Use the instructions above only for the part of my "
                            "request they cover. My full original request was: "
                            f'"{prompt}". Answer every part of it in your final reply.'
                        ),
                    }
                )
                ollama_tools = [
                    tool
                    for tool in ollama_tools
                    if tool["function"]["name"] != "call_mcp_prompt"
                ]

            response = ollama.chat(
                model=LOCAL_OLLAMA_MODEL, messages=messages, tools=ollama_tools
            )
            messages.append(response.message)
            pending_calls = extract_tool_calls(response.message, callable_names)

        logger.debug("Final answer: %s", response.message.content)
        print(response.message.content)


def configure_logging(verbose: bool) -> None:
    """Always write the full trace to LOG_FILE; echo it to stderr only if verbose."""
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO if verbose else logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)


if __name__ == "__main__":
    cli_args = sys.argv[1:]
    verbose = any(arg in ("-v", "--verbose") for arg in cli_args)
    cli_args = [arg for arg in cli_args if arg not in ("-v", "--verbose")]
    configure_logging(verbose)
    # user_prompt = (
    #     " ".join(cli_args)
    #     or "What time is it? Where are you? Say hello. Then Sort this list of numbers: 5, 2, 9, 1, 5, 6. What is the current temperature and wind speed in Rome, Italy? lat=41.9028, lon=12.4964"
    # )
    user_prompt = (
        " ".join(cli_args)
        or "Say hello and then tell me what is the weather at lat=41.9028 lon=12.4964"
    )
    asyncio.run(run(user_prompt))
