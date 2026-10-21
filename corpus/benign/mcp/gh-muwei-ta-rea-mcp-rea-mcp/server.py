"""FastMCP server exposing every rea CLI command as an MCP tool.

Tools are generated dynamically from `rea --llms` and each command's
`--schema` output, so new rea releases add tools without code changes.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools.base import Tool, ToolResult

from .cli import fetch_schema, load_catalog, resolve_entry, run_command

mcp = FastMCP("rea-mcp")


class ReaCommandTool(Tool):
    """A tool that proxies one rea CLI command.

    The JSON Schema for tool parameters is taken verbatim from
    `rea <command> --schema --format json`, merged from its `args` and
    `options` sections.
    """

    command: str

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            output = run_command(self.command, arguments)
        except Exception as exc:  # surface CLI errors to the agent
            raise RuntimeError(f"rea {self.command} failed: {exc}") from exc
        return ToolResult(output)


def _merged_parameters(schema: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Merge a command schema's args + options into one parameters schema."""
    args = schema.get("args", {})
    options = schema.get("options", {})
    properties: dict[str, Any] = dict(args.get("properties", {}))
    for name, spec in options.get("properties", {}).items():
        properties.setdefault(name, spec)
    required = list(args.get("required", []))
    return properties, required


def _build_tool(command: str, description: str) -> ReaCommandTool:
    schema = fetch_schema(command)
    properties, required = _merged_parameters(schema)
    parameters = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
    return ReaCommandTool(
        name=f"rea_{command.replace('-', '_')}",
        description=description or f"Run rea {command}.",
        parameters=parameters,
        command=command,
    )


def register_tools() -> int:
    """Register one MCP tool per rea CLI command. Returns the tool count."""
    count = 0
    for entry in load_catalog():
        tool = _build_tool(entry["name"], entry["description"])
        mcp.add_tool(tool)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="rea-mcp: FastMCP wrapper for rea CLI")
    parser.add_argument(
        "--transport", choices=["stdio", "http", "sse"], default="stdio"
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP/SSE listen address")
    parser.add_argument("--port", type=int, default=8000, help="HTTP/SSE listen port")
    args = parser.parse_args()

    if resolve_entry() is None:
        sys.stderr.write(
            "rea CLI not found. Install rea-agents (`npm i -g rea-agents`) or set "
            "REA_MCP_CLI, then restart rea-mcp.\n"
        )
        sys.exit(1)

    count = register_tools()
    sys.stderr.write(f"rea-mcp: registered {count} tools\n")

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
