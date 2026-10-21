# Model Context Protocol (MCP) for Web Documentation Search: Distilled Guide

*Author: Gemini 2.5 Pro (Cascade)*

---

## Purpose
This document distills the official MCP standard to focus on its application for invoking web searches of standard software documentation via an MCP server. It is tailored for the `chlorpromazine-mcp` server, which provides LLM agents with reliable access to trusted development docs and community resources.

---

## 1. MCP Core Concepts (Relevant to Web Search)

### Architecture
- **Client-Server Model**: LLM applications (clients/hosts) connect to MCP servers, which expose tools and resources (e.g., documentation search).
- **Transport Layer**: Typically HTTP/SSE for remote (web) use, or stdio for local. All use JSON-RPC 2.0 for messages.

### Message Types
- **Requests**: Sent by client/host to server (e.g., search for docs)
- **Results**: Server responses (e.g., search results)
- **Notifications**: One-way updates (rarely used for search)

### Connection Lifecycle (Simplified)
1. Client sends `initialize` (with capabilities)
2. Server responds (with its capabilities)
3. Client acknowledges
4. Ready for tool/resource calls (e.g., `tools/call` for search)

---

## 2. Prompts & Tools (How Search is Exposed)

### Prompts
- **Definition**: Predefined templates/workflows exposed by the server for user/agent selection.
- **Structure**: Each prompt has a name, description, and optional arguments (e.g., search query, site filter).
- **Discovery**: Clients use `/v1/prompts/list` to enumerate available prompts.

### Tools
- **Definition**: Server-exposed functions that perform actions—here, searching documentation.
- **Discovery**: `/v1/tools/list` endpoint returns available tools (e.g., `kill_trip` for trusted doc search).
- **Invocation**: `/v1/tools/call` endpoint executes a tool with provided arguments (e.g., `{ query: "How do I use MCP?" }`).
- **Result**: Returns structured results (e.g., top documentation links, snippets).

---

## 3. Web Documentation Search via MCP

### Intended Workflow
1. **Agent/User** selects a doc search prompt or tool in their LLM app.
2. **Client** sends a tool call request to the MCP server with the search query and (optionally) site filter.
3. **Server** uses a web search API (e.g., SerpAPI) to find trusted documentation results.
4. **Server** returns structured, filtered results (links, snippets, source domains) to the client.
5. **Agent/User** reviews, cites, or uses the documentation in their workflow.

### Security & Best Practices
- **Site Filtering**: Only allow results from trusted domains (configurable via `SITE_FILTER`).
- **Input Validation**: All tool arguments and search queries must be validated.
- **Logging**: Log requests/results for debugging, but do not leak sensitive info.
- **API Keys**: Keep search API keys secure via environment variables.
- **Rate Limiting**: Prevent abuse by limiting search frequency.

---

## 4. Relevant Endpoints (chlorpromazine-mcp)
- `/healthz`: Health check
- `/v1/prompts/list`: List prompts
- `/v1/tools/list`: List tools (e.g., `kill_trip`)
- `/v1/tools/call`: Call tool (e.g., search docs)

---

## 5. Example: Search Tool Call

**Request:**
```json
{
  "method": "tools/call",
  "params": {
    "tool": "kill_trip",
    "arguments": {
      "query": "How do I implement an MCP server in Node.js?",
      "site_filter": "nodejs.org,docs.anthropic.com"
    }
  }
}
```

**Response:**
```json
{
  "result": {
    "content": [
      {
        "title": "MCP Server Quickstart (Node.js)",
        "url": "https://modelcontextprotocol.io/quickstart/server-node",
        "snippet": "Learn how to implement an MCP server in Node.js using the SDK..."
      },
      ...
    ]
  }
}
```

---

## 6. Security & Deployment Notes
- Always validate and sanitize all incoming requests.
- Restrict web search to trusted documentation domains.
- Use API key authentication if exposing the server outside localhost.
- Deploy behind an API gateway or firewall if possible.

---

## 7. Further Reading
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/docs/)
- [chlorpromazine-mcp README](../README.md)
- [SerpAPI Docs](https://serpapi.com/)

---

*This document is a distilled reference for developers and LLM agents using MCP to search standard software documentation. For full protocol details, refer to the official MCP specification.*
