# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram MCP Server - a full-featured Telegram integration for Claude, Cursor, and MCP-compatible clients. Uses Telethon for Telegram API access and exposes 60+ tools via the Model Context Protocol.

## Commands

### MCP Server (Python)
```bash
# Install dependencies
uv sync

# Run the MCP server
uv run main.py

# Generate Telegram session string
uv run session_string_generator.py

# Format code
black .

# Lint code
flake8 .
```

### Run Tests
```bash
# Run validation tests
pytest test_validation.py -v
```

### TypeScript Agent (in agent/)
```bash
cd agent
bun install
bun run dev
```

### Docker
```bash
docker build -t telegram-mcp:latest .
docker compose up --build
```

## Architecture

### MCP Server (`main.py`)
Single-file MCP server exposing Telegram functionality as tools. Key components:
- `FastMCP("telegram")` - MCP server instance
- `TelegramClient` - Telethon client (supports both string and file-based sessions)
- `@mcp.tool()` decorated functions - 60+ tools for chat, messaging, contacts, admin, media operations
- `@validate_id()` decorator - validates chat_id/user_id parameters (accepts int, string int, or @username)
- `log_and_format_error()` - centralized error handling with error codes logged to `mcp_errors.log`

### TypeScript Agent (`agent/`)
CLI agent using Claude Sonnet via Vercel AI Gateway. Communicates with Telegram through an HTTP bridge:
- `telegram_api.py` - FastAPI HTTP bridge exposing Telethon via REST (runs on port 8765)
- `agent/src/agent.ts` - AI agent using @ai-sdk/gateway
- `agent/src/tools/` - Tool definitions (telegram.ts, nia.ts, aiify.ts)

### ID Validation
All functions accept flexible ID formats:
- Integer ID: `123456789` or `-1001234567890`
- String ID: `"123456789"`
- Username: `"@username"` or `"username"`

## Code Style

- Python: Black formatter (line-length 99), Flake8 linter
- Target Python version: 3.10+
- Use `Union[int, str]` for ID parameters
- Error codes follow pattern: `{CATEGORY}-ERR-{hash}`

## Environment Variables

Required in `.env`:
- `TELEGRAM_API_ID` - from my.telegram.org/apps
- `TELEGRAM_API_HASH` - from my.telegram.org/apps
- `TELEGRAM_SESSION_STRING` (preferred) or `TELEGRAM_SESSION_NAME` (file-based)

For TypeScript agent:
- `AI_GATEWAY_API_KEY` - Vercel AI Gateway key
- `NIA_API_KEY` - Nia API key
- `TELEGRAM_API_URL` - HTTP bridge URL (default: http://localhost:8765)
