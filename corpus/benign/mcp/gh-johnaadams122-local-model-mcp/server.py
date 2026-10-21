from mcp.server.fastmcp import FastMCP

from local_llm.summarize import summarize
from local_llm.classify import classify
from local_llm.extract import extract_json
from local_llm.file_tools import summarize_file, extract_json_file

mcp = FastMCP("local-llm")

_tools = [summarize, classify, extract_json, summarize_file, extract_json_file]

for _tool in _tools:
    mcp.tool()(_tool)

if __name__ == "__main__":
    mcp.run()
