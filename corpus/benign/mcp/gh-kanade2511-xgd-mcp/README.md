# xgd-mcp

MCP server for [x.gd](https://x.gd) URL shortener API.

## Features

- Shorten URLs with custom short IDs
- Enable/disable analytics
- Bot filtering support

## Install

```bash
git clone https://github.com/sou-to/xgd-mcp.git ~/.bin/mcps/xgd-mcp
cd ~/.bin/mcps/xgd-mcp
uv sync
```

## Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "xgd": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/xgd-mcp", "python", "server.py"],
      "env": {
        "XGD_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Hermes

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  xgd:
    command: uv
    args:
      - run
      - --directory
      - /Users/sou/.bin/mcps/xgd-mcp
      - python
      - server.py
    env:
      XGD_API_KEY: ${XGD_API_KEY}
```

Then add `XGD_API_KEY` to `~/.hermes/.env`:

```
XGD_API_KEY=*** Tools

### shorten_url

Shorten a URL using x.gd API.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | yes | URL to shorten (must be http(s)://) |
| shortid | string | no | Custom short ID (6-15 chars, alphanumeric and underscore) |
| analytics | boolean | no | Enable access analytics (default: true) |
| filterbots | boolean | no | Enable bot filtering (default: false) |
