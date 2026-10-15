# 🧠 Second Brain MCP

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that turns your Obsidian vault into an AI-queryable second brain.

It combines:
- **KuzuDB** — an embedded graph database to store notes, tags, and `[[wikilink]]` relationships
- **ChromaDB** — a local vector database for semantic search over note contents
- **Watchdog** — a live file watcher that auto-indexes notes as you write/edit/delete them

---

## ✨ Features

| Tool | Description |
|------|-------------|
| `search_notes` | Semantic search across all note contents |
| `list_all_notes` | List every note with tags and last-modified date |
| `get_note` | Retrieve full content, tags, links, and backlinks for a note |
| `find_related` | Find 1-hop and 2-hop related notes via graph traversal |
| `list_tags` | Show all unique tags across the vault with usage counts |
| `search_by_tag` | Return all notes carrying a specific tag |
| `get_note_stats` | Vault-wide analytics: totals, hub notes, recent activity |
| `create_note` | Create a new markdown note directly in the vault |
| `rename_note` | Rename a note and auto-update all `[[wikilink]]` references |
| `get_orphan_notes` | Find isolated notes with no incoming or outgoing links |
| `get_unresolved_links` | Find placeholder/stub notes referenced in wikilinks but not yet created |
| `get_link_suggestions` | Find notes that mention a target title but do not link to it |
| `surface_contradictions` | Detect conflicting statements across notes using NLI or heuristics |
| `daily_context` | Get notes tagged with or modified on a specific date |

---

## 🚀 Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Second-Brain-MCP.git
cd Second-Brain-MCP
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your vault path

Set the `VAULT_PATH` environment variable to the absolute path of your Obsidian vault:

```bash
# Windows (PowerShell)
$env:VAULT_PATH = "C:\Users\YourName\Documents\MyVault"

# macOS/Linux
export VAULT_PATH="/Users/YourName/Documents/MyVault"
```

> If `VAULT_PATH` is not set, the server defaults to a local `./vault/` folder.

### 5. Run the server

```bash
python main.py
```

On first run, the server performs an **initial sync** — crawling and indexing all `.md` files in the vault. Subsequent runs are faster as the databases persist in the `.db_data/` folder.

---

## 🔌 Connecting to an MCP Client

This server uses [FastMCP](https://github.com/jlowin/fastmcp). To connect it to Claude Desktop or any MCP-compatible client, add it to your MCP config:

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["C:/path/to/Second-Brain-MCP/main.py"],
      "env": {
        "VAULT_PATH": "C:/path/to/your/ObsidianVault"
      }
    }
  }
}
```

---

## 📁 Project Structure

```
Second-Brain-MCP/
├── main.py          # MCP server entry point & all tool definitions
├── graph.py         # KuzuDB graph database wrapper
├── vector.py        # ChromaDB vector database wrapper
├── parser.py        # Obsidian markdown & frontmatter parser
├── watcher.py       # Live vault file watcher (watchdog)
├── requirements.txt # Python dependencies
└── .db_data/        # Auto-created: persisted KuzuDB & ChromaDB data
```

---

## ⚙️ Dependencies

| Package | Purpose |
|---------|---------|
| `fastmcp` | MCP server framework |
| `kuzu` | Embedded graph database |
| `chromadb` | Local vector database |
| `sentence-transformers` | Local embeddings (`all-MiniLM-L6-v2`) |
| `python-frontmatter` | Parse YAML frontmatter from markdown files |
| `watchdog` | File system monitoring |
| `transformers` + `torch` | Optional NLI model for contradiction detection |

---

## 📝 Notes

- All databases are stored locally in `.db_data/` — no cloud services required.
- The embedding model (`all-MiniLM-L6-v2`) is downloaded once and cached by `sentence-transformers`.
- The NLI model for `surface_contradictions` (`cross-encoder/nli-MiniLM2-L6-H768`) is optional; if unavailable, a lexical negation fallback is used.
- Notes are matched by filename (without `.md`) as their title, unless a `title:` field is set in the YAML frontmatter.

---

## 📄 License

MIT