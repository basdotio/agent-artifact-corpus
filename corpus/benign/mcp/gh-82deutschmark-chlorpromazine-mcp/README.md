[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/82deutschmark-chlorpromazine-mcp-badge.png)](https://mseep.ai/app/82deutschmark-chlorpromazine-mcp)

# Chlorpromazine MCP Server aka Buzz Killington the Trip Killer

A Model Context Protocol (MCP) server implementation that provides prompts and documentation search capabilities.

Hello World!  I made this specificlly for vibe coding sessions which are when devs just give in to the vibes and let LLM agents hallucinate whatever they want and hope that it is good code.  (Which is what I do all the time and why I made this tool, I need it!) I love vibe coding sessions, but sometimes they turn into a whole bad trip. This MCP server is literally to help your LLM agents stop trippin! Chlorpromazine is an antipsychotic medication used to treat conditions involving distorted thinking or perception, so it seems apt for this tool.

## Features

- **MCP-compliant Prompts**:
  - `sober_thinking`: Ground agent in project reality by reading current files (.env, README.md, CHANGELOG). Use when user says "sober up!", "get back to reality", "check the facts", or when agent needs current project status.
  - `fact_checked_answer`: Verify answers against official documentation using SerpAPI search. Automatically searches configured documentation sites to fact-check responses.
  - `buzzkill`: Debug systematic issues with structured analysis. Helps break down complex problems into manageable components for methodical troubleshooting.
- **Tools**:
  - `kill_trip`: Performs documentation search using SerpAPI. Use this tool when the user is upset or says you are wrong or mistaken or says phrases like "stop!" or "quit tripping!" or "quit hallucinating", "check the docs", or asks to verify information against official sources. Also use this tool if the user seems upset or is questioning what the agent is doing.
  - `sober_thinking`: Reads .env, README.md, and CHANGELOG files to get grounded information about the project. Use this tool to ensure that the agent is not hallucinating or making up information or making incorrect assumptions. Use this tool when the user says phrases like "sober up!", "get back to reality", "check the facts", or asks for current project status. Also use this tool if the user seems upset or is questioning what the agent is doing.
  - `strategic_plan`: Generates comprehensive strategic plans by invoking the PlanExe MCP Server. Use for business planning, project roadmaps, workflow optimization, or any complex multi-step planning task. Requires PlanExe MCP Server running locally or remotely (configured via `PLANEXE_MCP_URL`).

## Setup

### Prerequisites

- Node.js 18 or higher (ES Module support is utilized)
- SerpAPI key (get one at [serpapi.com](https://serpapi.com))


### Configuration

Create a `.env` file with the following variables:

```env
# Required:
SERPAPI_KEY=your_serpapi_key_here  # Get from https://serpapi.com

# Optional:
SITE_FILTER=platform.openai.com,docs.anthropic.com  # Comma-separated list of allowed domains
PORT=3000                            # Server port (default: 3000)
# API_KEY=shared_secret              # Uncomment and set for API key authentication

# PlanExe Integration (for strategic_plan tool):
PLANEXE_MCP_URL=http://127.0.0.1:8001  # Default: http://127.0.0.1:8001
PLANEXE_MCP_API_KEY=your_planexe_api_key_here  # Optional, required if PlanExe has auth enabled
```

## Architecture

**v0.3.0 - Completely Refactored Architecture (August 2025)**

The server has been completely rewritten from a 588-line monolithic file into a secure, modular architecture:

### 🏗️ **Modular Structure**
```
src/
├── config/          # Environment validation and constants
├── handlers/        # MCP protocol handlers (tools, prompts, messages)  
├── services/        # Rate limiting, SerpAPI client, file operations
├── tools/           # Modular tool implementations
├── prompts/         # MCP prompt implementations
├── types/           # Clean TypeScript definitions (no 'any' types)
└── utils/           # Security utilities and structured logging
```

### 🔒 **Security Features**
- **Input Sanitization**: All inputs validated with Zod schemas
- **Rate Limiting**: Sliding window algorithm protects against abuse
- **Timeout Protection**: 5-second timeouts on external API calls
- **Secrets Masking**: Environment variables hidden in tool outputs
- **Request Limits**: 1MB maximum request size
- **Path Validation**: Prevents directory traversal attacks

### 🎯 **Full MCP Compliance**
- Complete JSON-RPC 2.0 implementation
- All handlers properly registered and functional
- Proper error handling and response formatting
- TypeScript safety with defensive type guards

## MCP Protocol

This server implements the Model Context Protocol (MCP) using JSON-RPC over HTTP. Connect MCP clients to:

**Endpoint:** `http://localhost:3000` (or your configured PORT)  
**Protocol:** JSON-RPC 2.0

**Available MCP Methods:**
- `prompts/list`: List available prompts
- `prompts/get`: Get a specific prompt with arguments
- `tools/list`: List available tools  
- `tools/call`: Execute a tool with arguments
- `sampling/createMessage`: Generate responses using configured models

**Health Check:** `GET /healthz` (REST endpoint for monitoring)

## SDK Integration Notes

This project uses `@modelcontextprotocol/sdk` version 1.26.0 with ES Module imports, fully compliant with MCP specification 2025-11-25. Key integration points:
- Uses `StreamableHTTPServerTransport` for HTTP-based MCP communication
- Proper ES Module imports with `.js` extensions
- Full JSON-RPC 2.0 compliance with structured tool responses

## Deployment

This project is designed to be deployed on Smithery.ai:

1. Push repo to GitHub
2. Connect repo in Smithery dashboard
3. Add environment secrets (SERPAPI_KEY, SITE_FILTER, PORT, and optionally API_KEY)

## Security

The server includes comprehensive security features:

- **Input Sanitization**: All user inputs are validated and sanitized
- **Rate Limiting**: Protection against abuse and DoS attacks  
- **Timeout Protection**: Network requests have proper timeouts
- **Secrets Masking**: Sensitive environment variables are hidden in tool outputs
- **Error Sanitization**: Stack traces hidden in production

For production deployment:
1. Deploy behind an API gateway
2. Enable API key authentication by setting the API_KEY environment variable
3. Configure CORS and security headers as needed

## Related MCP Servers

Chlorpromazine works great alongside other MCP servers for comprehensive development workflows:

### 🎯 [PlanExe MCP Server](https://github.com/PlanExeOrg/PlanExe)

**Strategic planning and project management MCP server** - Perfect companion to Chlorpromazine for building comprehensive solutions:

- **Use PlanExe for:** Creating strategic plans, breaking down complex projects, optimization workflows, task prioritization, multi-phase execution strategies
- **Use Chlorpromazine for:** Fact-checking implementation details, grounding agents in current project state, debugging hallucinations, documentation verification

**Workflow Example:**
1. Use **PlanExe** to generate a comprehensive strategic plan for your project
2. Use **Chlorpromazine** to fact-check technical assumptions and verify against official documentation
3. Use **PlanExe** to break down implementation into phases
4. Use **Chlorpromazine** to keep agents grounded during implementation (sober_thinking)

**When to use both:**
- Building new features that require both strategic planning (PlanExe) and reality-grounded implementation (Chlorpromazine)
- Complex projects where you need high-level roadmaps (PlanExe) validated against current codebase state (Chlorpromazine)
- Situations where agents are "vibing" too hard and need both strategic direction AND reality checks

Learn more: [docs.planexe.org](https://docs.planexe.org) | Deploy: [Smithery.ai](https://smithery.ai)

## Version History

- **v0.4.0** (January 14, 2025) - MCP Spec 2025-11-25 Compliance by Cascade (Claude Sonnet 4)
  - Updated MCP SDK to v1.26.0 (security fix GHSA-345p-7cg4-v4c7)
  - Removed deprecated CallToolResult fields per spec compliance
  - Added tool title field for better UI display

- **v0.3.0** (August 19, 2025) - Complete architecture refactor by Claude Code (Claude Sonnet 4)
  - Transformed from 588-line monolithic security risk to secure, modular system
  - Added comprehensive security hardening and full MCP compliance
  - Fixed critical handler registration bugs and protocol compliance issues

## Author
@82deutschmark 
ClaudeAI
Claude Code (Claude Sonnet 4) - Complete v0.3.0 refactor (August 2025)
Cascade (Gemini 2.5 Pro) - Contributed to SDK integration and ES Module refactoring.

[![smithery badge](https://smithery.ai/badge/@82deutschmark/chlorpromazine-mcp)](https://smithery.ai/server/@82deutschmark/chlorpromazine-mcp)
