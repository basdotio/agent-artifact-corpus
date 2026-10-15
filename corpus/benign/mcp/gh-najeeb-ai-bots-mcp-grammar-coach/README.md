# 🔌 grammar-coach — an MCP Server

> A **Model Context Protocol (MCP)** server, built from scratch with the official Python SDK, that exposes grammar and readability analysis as callable tools to any MCP host (Claude Desktop, Cursor, etc.).

**Built by:** [Mohammed Abdul Najeeb](https://github.com/Najeeb-AI-bots)

> 💡 This is a hand-built MCP server demonstrating correct **tool design** — the core of the Model Context Protocol. It pairs with my [VoiceCoach Lite](https://github.com/Najeeb-AI-bots/voicecoach-lite) app, which uses the same analysis engine in a web UI.

---

## What is MCP (in one line)?

MCP is a standard protocol — "USB-C for AI" — that lets any AI host call tools and read data from any server. This repo is the **server** side: it publishes tools, and the AI host decides when to call them. The host decides; **the server runs the code.**

## The tools this server exposes

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `check_grammar` | Detect grammar/spelling/style errors | `text: str` | `{error_count, errors[], engine}` |
| `score_readability` | Measure how easy text is to read | `text: str` | `{word_count, reading_ease, grade_level, ...}` |
| `suggest_rewrite` | Produce a cleaned-up rewrite in a tone | `text: str, tone: str` | `{original, rewritten, changes_made}` |

Each tool follows deliberate design rules (see below).

## Tool-design principles applied

This server is a worked example of good MCP tool design:

1. **Verb-noun names** — `check_grammar`, not `process` or `tool1`
2. **Descriptions state purpose + inputs + outputs + WHEN to use** — so the host routes to the right tool
3. **Single-purpose tools** — grammar, readability, and rewrite are *different jobs*, kept separate (not a `mode` mega-tool)
4. **Typed parameters** — `text: str`, `tone: str = "professional"` auto-generate the JSON input schema
5. **Structured output** — every tool returns a predictable dict, never free-form prose

## How it's built

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("grammar-coach")

@mcp.tool()
def check_grammar(text: str) -> dict:
    """Check English text for grammar, spelling, and style errors. ..."""
    return run_grammar_check(text)
```

The `@mcp.tool()` decorator turns a documented, type-hinted Python function into
a fully-schema'd MCP tool — name from the function, schema from the type hints,
description from the docstring.

## Run / test locally

```bash
pip install -r requirements.txt
python server.py          # starts the server over stdio
```

Register it with Claude Desktop by adding the block in
`claude_desktop_config.example.json` to your Claude config, then ask Claude:
*"Check the grammar of this sentence: ..."* — it will call `check_grammar`.

## Architecture

```
AI Host (Claude Desktop) ──MCP/stdio──► server.py ──► grammar_engine.py ──► LanguageTool
   "check my grammar"                    (3 tools)       (analysis)
```

## Skills demonstrated

MCP server design · Tool schema definition · Structured output · Single-responsibility tool granularity · Python SDK (FastMCP)

## License

MIT.
