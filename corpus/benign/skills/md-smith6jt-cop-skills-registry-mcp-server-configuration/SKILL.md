---
name: mcp-server-configuration
description: "MCP (Model Context Protocol) server configuration for Claude Code integration with trading platform. Trigger when setting up MCP servers, fixing alpaca-mcp-server issues, or adding new integrations."
author: Claude Code
date: 2026-01-30
---

# MCP Server Configuration for Trading Platform

## Experiment Overview
| Item | Details |
|------|---------|
| **Date** | 2026-01-30 |
| **Goal** | Configure MCP servers for Claude Code integration with trading platform |
| **Environment** | Windows, Claude Code, uvx package manager |
| **Status** | Success |

## Current Configuration

The project uses `.mcp.json` in the repository root for MCP server configuration:

```json
{
  "mcpServers": {
    "alpaca": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--with", "pytz", "alpaca-mcp-server", "serve"],
      "env": {
        "ALPACA_API_KEY": "your_key",
        "ALPACA_SECRET_KEY": "your_secret",
        "ALPACA_PAPER_TRADE": "True"
      }
    },
    "sqlite-trading": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-sqlite", "C:/Users/smith/Alpaca_trading/data/trading.db"]
    },
    "sqlite-market-data": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-sqlite", "C:/Users/smith/Alpaca_trading/data_cache/market_data.db"]
    }
  }
}
```

## Configured Servers

### 1. Alpaca MCP Server (alpaca-mcp-server)
**Purpose:** Trade stocks, ETFs, crypto, and options via natural language through Claude Code.

**Features:**
- Portfolio management and account information
- Real-time market data and historical data
- Order placement, cancellation, and modification
- Watchlist management

**Known Issue:** The `alpaca-mcp-server` package has a missing `pytz` dependency when run via uvx. Fix by adding `--with pytz` to args.

**Source:** https://github.com/alpacahq/alpaca-mcp-server

### 2. SQLite MCP Servers (mcp-sqlite)
**Purpose:** Query trading databases directly from Claude Code.

**Databases:**
- `sqlite-trading`: Trading records (`data/trading.db`)
- `sqlite-market-data`: Market data cache (`data_cache/market_data.db`)

**Usage:** Natural language queries like "Show me all trades from last week" or "What's the schema of the predictions table?"

**Source:** https://github.com/jparkerweb/mcp-sqlite

## Failed Attempts

| Attempt | Why it Failed | Lesson Learned |
|---------|---------------|----------------|
| `uvx alpaca-mcp-server serve` without `--with pytz` | ModuleNotFoundError: No module named 'pytz' | uvx creates isolated env, missing transitive deps |
| Installing alpaca-mcp-server via pip | Conflicts with conda environment | Use uvx for MCP servers to isolate |

## Recommended Additional MCP Servers

### For Trading Platform Development

| Server | Purpose | Installation |
|--------|---------|--------------|
| **yahoo-finance-mcp** | Backup market data queries (sector lookups ONLY) | `uvx yahoo-finance-mcp` |
| **alphavantage-mcp** | Technical indicators, fundamentals | `uvx alphavantage-mcp` |
| **notifyme-mcp** | Trading alerts via Discord/Slack | `uvx notifyme-mcp` |

### Example: Adding Yahoo Finance for Sector Data

```json
"yahoo-finance": {
  "type": "stdio",
  "command": "uvx",
  "args": ["yahoo-finance-mcp"]
}
```

**WARNING:** Yahoo Finance MCP is ONLY for sector/industry lookups. NEVER use for OHLCV price/volume data - use Alpaca API exclusively for that.

## Troubleshooting

### Missing Dependency Errors
```
ModuleNotFoundError: No module named 'xyz'
```
**Fix:** Add `"--with", "xyz"` to the args array before the package name.

### Server Won't Start
1. Test manually: `uvx --with pytz alpaca-mcp-server --help`
2. Check API keys are set correctly
3. Restart Claude Code after changing `.mcp.json`

### API Key Security
- Never commit actual API keys to `.mcp.json`
- Use environment variables or separate key files
- Paper trading keys shown in examples are for demonstration only

## Key Insights

1. **uvx isolates environments** - Each MCP server runs in its own isolated Python environment
2. **--with flag for deps** - Add missing transitive dependencies with `--with package_name`
3. **Restart required** - Claude Code must restart to pick up `.mcp.json` changes
4. **Multiple SQLite servers** - Can configure separate servers for different databases
5. **Data source policy still applies** - MCP servers don't change the rule: Alpaca API for OHLCV, yfinance only for sector lookups

## Files Modified

| File | Purpose |
|------|---------|
| `.mcp.json` | MCP server configuration |

## References

- Alpaca MCP Server: https://github.com/alpacahq/alpaca-mcp-server
- Alpaca MCP Docs: https://docs.alpaca.markets/docs/alpaca-mcp-server
- mcp-sqlite: https://github.com/jparkerweb/mcp-sqlite
- MCP Protocol: https://modelcontextprotocol.io/
- Skill: `data-source-priority` - Data source policy (Alpaca API mandatory)
