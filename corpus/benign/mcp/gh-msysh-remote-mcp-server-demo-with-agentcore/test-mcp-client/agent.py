import os
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

MCP_SERVER_ENDPOINT = os.getenv('MCP_SERVER_ENDPOINT')
BEARER_TOKEN = os.getenv('BEARER_TOKEN')

mcp_client = MCPClient(lambda: streamablehttp_client(
  MCP_SERVER_ENDPOINT,
  headers={
    'Authorization': f"Bearer {BEARER_TOKEN}"
  }
))

with mcp_client:
  tools = mcp_client.list_tools_sync()
  agent = Agent(tools=tools)

  agent("I'm Tom. Please greet.")