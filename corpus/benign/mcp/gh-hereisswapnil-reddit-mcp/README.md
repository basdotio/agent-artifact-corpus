<p align="center">
  <img src="assets/logo.png" alt="Reddit MCP Logo" width="120" height="120" style="border-radius:30px;">
</p>

<h1 align="center">Reddit MCP</h1>

<p align="center">
  A Model Context Protocol (MCP) server that lets Claude Desktop browse, search, and analyze Reddit in real time.
</p>

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License">
  </a>
  <img src="https://img.shields.io/badge/python-3.12+-green.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/MCP-Claude%20Desktop-purple.svg" alt="Claude MCP">
</p>

---

## ✨ What is Reddit MCP?

**Reddit MCP** is a plug-and-play MCP server that allows Claude Desktop to interact directly with Reddit.

Your AI can:
- Explore subreddits
- Search discussions and opinions
- Fetch full comment threads
- Analyze Reddit users
- Detect trends and sentiment in real time

No scraping. No setup friction. Works instantly.

---

## 🎬 Quick Demo
https://github.com/user-attachments/assets/7cccd617-12f1-4ffc-966f-34415adb5dd6


> 💡 *Ask Claude: "What's trending on r/programming today?"*

---

## 🚀 Quick Start (30 seconds)

1. **Install `uv`** if you don't have it:

   **macOS / Linux**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   sudo ln -sf ~/.local/bin/uv /usr/local/bin/uv
   ```

   **Windows**
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Download the MCP bundle**  
   👉 [reddit-mcp.mcpb](https://github.com/hereisSwapnil/reddit-mcp/releases/download/v1.0.0/reddit-mcp.mcpb)

3. **Double-click** the `.mcpb` file — Claude Desktop installs it automatically.

4. **Open Claude Desktop** and start asking Reddit questions.

That's it!

---

## 🔥 Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Browse Subreddits** | View posts from any subreddit with hot, new, top, or rising sorting |
| 🔎 **Search Reddit** | Search globally or within specific communities |
| 📄 **Post Details** | Fetch full post content with deeply threaded comments |
| 👤 **User Analysis** | Analyze a Reddit user's karma, activity patterns, and top subreddits |
| 🔓 **Anonymous Mode** | No API keys required. Works out of the box |
| ⚡ **Optional OAuth** | Add Reddit credentials for higher rate limits and stability |

---

## 📦 One-Click Installation (Recommended)

Download and install directly in Claude Desktop:

<p align="center">
  <a href="https://github.com/hereisSwapnil/reddit-mcp/releases/download/v1.0.0/reddit-mcp.mcpb">
    <img src="https://img.shields.io/badge/Download-reddit--mcp.mcpb-orange?style=for-the-badge" alt="Download">
  </a>
</p>

**Supports:** macOS • Windows • Linux

---

## 🛠️ Manual Installation

Add the server to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "reddit-mcp": {
      "command": "/usr/local/bin/uv",
      "args": ["run", "main.py"],
      "cwd": "/path/to/reddit-mcp"
    }
  }
}
```

Restart Claude Desktop after saving.

---

## 🤖 ChatGPT Integration

Connect Reddit MCP to ChatGPT using the public SSE endpoint.

### Use Hosted Server (Recommended)

Use the pre-hosted server URL:
```
https://reddit-mcp-production-79ca.up.railway.app/sse
```

### Or Self-Host with ngrok

1. Run the server with SSE enabled:
   ```bash
   SERVE_HTTPS=true uv run main.py
   ```

2. Expose it publicly:
   ```bash
   ngrok http 8000
   ```

3. Use your ngrok URL: `https://your-subdomain.ngrok.io/sse`

### Setup in ChatGPT

1. Go to **Settings** → **Apps & Connectors**
2. Scroll down to **Advanced settings** and click **Create app**
3. Enable **Developer mode** (toggle ON)
4. Click **Create App** and fill in:
   - **Icon**: Upload the Reddit MCP logo (optional)
   - **Name**: `Reddit MCP`
   - **Description**: `Browse, search, and analyze Reddit`
   - **MCP Server URL**: `https://reddit-mcp-production-79ca.up.railway.app/sse`
   - **Authentication**: Select `No Auth`
5. Check **"I understand and want to continue"**
6. Click **Create**

Your Reddit MCP connector will appear in the enabled apps list. Start using it!

---

## 🔐 Authentication (Optional)

Anonymous access works, but OAuth unlocks higher limits.

| Mode | Rate Limit | Setup Required |
|------|------------|----------------|
| Anonymous | ~10 req/min | None |
| OAuth | ~60 req/min | Client ID + Secret |

### How to enable OAuth

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **Create another app**
3. Select **script**
4. Copy your **Client ID** and **Client Secret**
5. Enter them when prompted during MCP setup

No tokens are stored remotely.

---

## 🧰 Available MCP Tools

| Tool | Description |
|------|-------------|
| `browse_subreddit` | Browse posts from any subreddit |
| `search_reddit` | Search Reddit posts by keyword |
| `get_post_details` | Fetch full post content and comments |
| `user_analysis` | Analyze Reddit user activity and karma |

---

## 💬 Example Queries

**Trending & Discovery**
- *"What's trending across all of Reddit today?"*
- *"Show me the hottest discussions in r/technology"*

**Search & Opinions**
- *"What are people saying about GPT-4?"*
- *"Find discussions about remote work in r/cscareerquestions"*

**Post & Comment Analysis**
- *"Get the full discussion from this Reddit post"*
- *"Summarize the top comments on post abc123"*

**User Analysis**
- *"Analyze the Reddit user spez"*
- *"What subreddits does u/DeepFuckingValue post in?"*

---

## 📁 Project Structure

```
reddit-mcp/
├── main.py           # MCP server entry point
├── reddit/
│   └── api.py        # Reddit API client (OAuth + anonymous)
├── manifest.json     # MCP bundle metadata
├── pyproject.toml    # Python dependencies
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

Ideas: caching, sentiment analysis, topic clustering, summaries.

---

## 📄 License

Licensed under the [MIT License](LICENSE).

---

<p align="center">
  <b>Reddit MCP turns Claude into a real-time Reddit analyst.</b>
</p>
