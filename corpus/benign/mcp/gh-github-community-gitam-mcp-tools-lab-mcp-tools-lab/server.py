"""One MCP server, exactly seven tools. Keep tool logic in tools/."""

from mcp.server.fastmcp import FastMCP

from mcp_tools_lab.tools.csv_tool import inspect_csv
from mcp_tools_lab.tools.diff import compare_text
from mcp_tools_lab.tools.hashing import hash_text
from mcp_tools_lab.tools.json_tool import process_json
from mcp_tools_lab.tools.text import analyze_text
from mcp_tools_lab.tools.timestamps import convert_timestamp
from mcp_tools_lab.tools.urls import inspect_url

mcp = FastMCP("MCP Tools Lab")

for tool in (analyze_text, process_json, inspect_csv, hash_text,
             compare_text, convert_timestamp, inspect_url):
    mcp.tool()(tool)


def main() -> None:
    """Run locally over standard input/output (no web server or keys)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
