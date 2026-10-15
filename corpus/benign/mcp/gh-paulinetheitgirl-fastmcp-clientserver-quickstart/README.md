# A FastMCP Python quickstart sample
A super-basic FastMCP server and client to get you started :grin:

Built for FastMCP 4.0.

The Model Context Protocol (MCP) standard celebrated its first anniversary in [November 2025](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/) and is still evolving, so expect this repo to change over time!

### Why HTTP transport instead of STDIO?
FastMCP servers use [STDIO transport](https://gofastmcp.com/deployment/running-server#stdio-transport-default) by default. But if you're learning about MCP, it's likely that you want other clients to connect to your MCP server too, so it helps to understand how it works [over HTTP](https://gofastmcp.com/deployment/http).

### Assumes OpenAI API client
This sample assumes that you are connecting to an OpenAI model. (Should also work with Docker Model Runner).
For other supported APIs and SDKs, see the official [FastMCP docs](https://gofastmcp.com/integrations/openai).

## Setup
1. Set the values your `.env` file with the keys shown in the example file
2. Start the server with `fastmcp run server.py:mcp --transport http --port 8000`
3. Run the client with `python client.py`