# Code Context MCP Setup

## Prerequisites

```bash
ollama pull unclemusclez/jina-embeddings-v2-base-code
```

## Install

```bash
npm install
npm run build
```

## Configuration

Copy `claude_desktop_config.example.json` to your Claude Desktop config location:

**Linux/macOS**: `~/.config/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Replace `<CLAUDE_CONFIG_DIR>` with your actual path:
- Linux/macOS: `/home/username/.config/Claude`
- Windows: `C:\Users\username\AppData\Roaming\Claude`

## Environment

Copy `.env.example` to `.env` and adjust paths if needed.

The `repos/` directory stores configuration metadata for repositories, not full clones.
For local repositories (file:// URLs), no cloning occurs - files are accessed directly.

## Test

```bash
npm run start:mcp
```

Restart Claude Desktop.
