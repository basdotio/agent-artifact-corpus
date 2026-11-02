# From Slack Logs to Smart Search — Powered by MCP and Claude Desktop

A local, AI-powered Slack search interface that uses [Model Context Protocol (MCP)](https://modelcontextprotocol.io) to enhance Claude Desktop experience. This project helps you search and retrieve meaningful insights from Slack export logs, all locally and privately.

## What is This?

This project sets up a local MCP server (`mcp_server.py`) that parses Slack export logs and registers custom MCP resources for intelligent search. It integrates with Claude Desktop via a JSON config (`claude_desktop_config.json`), allowing you to query Slack data directly using natural language.

---

## Project Structure

```bash
├── mcp_server.py               # The MCP server that registers search resources
├── claude_desktop_config.json # Config file for Claude Desktop to connect to this server
├── Slack-dataset/              # Slack dataset (not included)
└── README.md                   
```
Dataset found at: https://github.com/preethac/Software-related-Slack-Chats-with-Disentangled-Conversations

---

## ⚙️ Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/AdilFayyaz/Slack-Search.git
cd Slack-Search
```

### 2. Set up a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


### 3. Update Claude Desktop Config

Paste the following into your Claude Desktop config file:

```json
{
  "mcpServers": {
    "search_slack": {
      "command": "/bin/zsh",
      "args": [
        "-c",
        "source /Users/yourname/path-to-project/.venv/bin/activate && python3 /Users/yourname/path-to-project/mcp_server.py"
      ],
      "host": "127.0.0.1",
      "port": 5000,
      "timeout": 10000
    }
  }
}
```

Make sure to update file paths to your local machine setup.

---

## Usage

Open Claude Desktop, and try queries like:

```
Search for onboarding discussions from February.
What did we say about the pricing model in #general?
Find mentions of "launch" in random.
```

Claude will use `search://` and `summary://` style MCP URIs behind the scenes to get you results from your local server.

---

## How it Works

- The MCP server parses Slack JSON files and indexes content.
- It registers searchable resources like `search://{query}` or `summary://{channel}`.
- Claude Desktop makes MCP calls to your server to fetch and return contextual results.

---

## Motivation

Slack is where decisions happen and get buried. This tool helps resurface important context from old threads without uploading your data to the cloud. It's a small step toward smarter, local-first search powered by AI.

---

## Acknowledgments

- [Claude Desktop](https://claude.ai/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
