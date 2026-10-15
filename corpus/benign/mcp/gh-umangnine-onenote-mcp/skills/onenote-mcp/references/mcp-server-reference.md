# OneNote MCP Server Reference & Setup Guide

## 1. Technical Architecture Overview

The **OneNote MCP Server** is a Model Context Protocol (MCP) server that provides AI coding assistants and agents direct access to Microsoft OneNote notebooks on Windows machines.

It uses a dual-engine architecture:

1. **Reading Pipeline (Local Backup Parser)**:
   - Accesses local OneNote backup files (`.one`) stored on disk.
   - Default path: `%LOCALAPPDATA%\Microsoft\OneNote\16.0\Backup\`.
   - Uses `pyOneNote` (`pyOneNote.OneDocument.OneDocment`) to parse binary `.one` files.
   - Extracts Unicode text (`RichEditTextUnicode`) and section/page metadata.
   - Zero credentials, zero Microsoft Graph / Azure API registration, and no cloud tokens required.

2. **Writing Pipeline (Live COM Automation Engine)**:
   - Automates the running Microsoft OneNote desktop application directly via its Windows COM Automation API (`OneNote.Application`).
   - Executes single-threaded apartment (STA) PowerShell subprocess commands (`powershell.exe -STA -NoProfile -ExecutionPolicy Bypass`).
   - Uses OneNote COM API methods: `GetHierarchy`, `CreateNewPage`, `GetPageContent`, `UpdatePageContent`.
   - Modifies the OneNote page DOM using Microsoft OneNote XML Schema (`http://schemas.microsoft.com/office/onenote/2013/onenote`).

---

## 2. Complete Tool Catalog & Capabilities

### A. Reading Tools (Backup File Parsing)

| Tool | Parameters | Return Value | Operational Notes |
|---|---|---|---|
| `list_notebooks()` | *None* | List of notebook names and section counts | Scans `%LOCALAPPDATA%\...\Backup` for top-level folders. |
| `list_sections(notebook_name)` | `notebook_name: str` | List of section names and file sizes in KB | Resolves case-insensitively. Identifies most recent backup file per section. |
| `read_section(notebook_name, section_name)` | `notebook_name: str`<br>`section_name: str` | Full extracted text content of section | Joins all `RichEditTextUnicode` blocks separated by double linebreaks. |
| `search_notes(query)` | `query: str` | List of matching sections with 160-char text snippets | Full-text substring search across all discovered local `.one` files. |
| `list_all_sections()` | *None* | Complete directory tree of all notebooks and sections | Useful for initial workspace discovery and orientation. |
| `get_notebook_summary(notebook_name)` | `notebook_name: str` | Section outline with first ~200 chars preview per section | Quick scan without dumping whole sections. |

### B. Writing Tools (Live COM Automation)

| Tool | Parameters | Return Value | Operational Notes |
|---|---|---|---|
| `list_live_notebooks()` | *None* | Markdown list of notebooks and live sections currently open in OneNote | Uses `GetHierarchy(..., 3)`. Shows live state including locked sections. |
| `create_page(notebook_name, section_name, title, content)` | `notebook_name: str`<br>`section_name: str`<br>`title: str`<br>`content: str` | Success confirmation with generated OneNote page ID | Finds section ID via live hierarchy, calls `CreateNewPage`, updates title and body outline. |
| `list_live_pages(notebook_name, section_name)` | `notebook_name: str`<br>`section_name: str` | List of page titles and their persistent page IDs | Required to obtain `page_id` before calling `append_to_page` or `read_live_page`. |
| `append_to_page(page_id, content)` | `page_id: str`<br>`content: str` | Success status string | Fetches existing page XML, appends new `<one:Outline>` block at bottom, calls `UpdatePageContent`. |
| `read_live_page(page_id, notebook_name, section_name, page_title)` | `page_id: str` (optional)<br>`notebook_name: str`<br>`section_name: str`<br>`page_title: str` | Full structured Markdown representation of live page | Calls `GetPageContent`, parses XML DOM, formats headings, native tables, and nested sub-bullets into Markdown. |

---

## 3. Installation & Environment Setup

### System Prerequisites
- Windows 10/11 with **Microsoft OneNote Desktop** (Microsoft 365, Office 2021, 2019, or 2016 desktop version; NOT the discontinued Windows 10 UWP app).
- Python 3.12+ (or `uv`).
- Local OneNote backups enabled in OneNote: **File → Options → Save & Backup → Back Up All Notebooks Now**.

### Server Source Installation
```bash
# Clone or navigate to the server directory:
git clone https://github.com/mhzarem/onenote-mcp.git
cd onenote-mcp

# Using uv (recommended):
uv sync

# Or using pip:
pip install "mcp[cli]" pyOneNote
```

---

## 4. Configuring MCP in AI Clients

### 1. Antigravity IDE
In `%USERPROFILE%\.gemini\antigravity\mcp_config.json` (or active workspace MCP config):
```json
{
  "mcpServers": {
    "onenote": {
      "command": "C:\\Users\\YOUR_USER\\.gemini\\antigravity\\scratch\\onenote-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\YOUR_USER\\.gemini\\antigravity\\scratch\\onenote-mcp\\server.py"
      ],
      "env": {
        "ONENOTE_BACKUP_DIR": "C:\\Users\\YOUR_USER\\AppData\\Local\\Microsoft\\OneNote\\16.0\\Backup"
      }
    }
  }
}
```

### 2. Claude Code CLI
```bash
claude mcp add --transport stdio onenote -- uv --directory "C:\path\to\onenote-mcp" run server.py
```
Verify status:
```bash
claude mcp list
```

### 3. Claude Desktop
In `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "onenote": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\onenote-mcp",
        "run",
        "server.py"
      ]
    }
  }
}
```

---

## 5. How to Invoke OneNote MCP in Any Conversation

When an AI assistant has access to the OneNote MCP server, tools can be invoked in two ways:

### 1. Native Tool Execution (`call_mcp_tool`)
The agent calls tools using `call_mcp_tool` with `ServerName: "onenote"`:

```json
{
  "ServerName": "onenote",
  "ToolName": "create_page",
  "Arguments": {
    "notebook_name": "Notes-2026",
    "section_name": "Update-Notes-26",
    "title": "Wednesday, 30 September, 2026",
    "content": "<h1>Daily Report</h1><p>Work completed...</p>"
  }
}
```

### 2. Conversational Intent Prompts
Users can trigger OneNote workflows naturally:
- *"List all notebooks in OneNote"*
- *"Search my notes for database migration guidelines"*
- *"Create a page in notebook 'Notes-2026' under 'Update-Notes-26' with our sprint summary"*
- *"Append the latest API benchmark numbers to the existing Performance page"*

---

## 6. Backup vs Live Differences & Known Constraints

1. **Backup Sync Latency**:
   - Reading tools (`read_section`, `search_notes`) inspect backup `.one` files. OneNote creates backups according to user settings (e.g. daily, weekly, or on manual trigger).
   - If a page was created seconds ago, it exists in **live** memory/cloud cache, but might not yet appear in backup files.
   - For immediate retrieval of newly written pages, use the live COM automation scripts (`GetPageContent`).

2. **Windows Desktop & Single-Threaded Apartment (STA)**:
   - Writing tools communicate with `OneNote.Application` through COM.
   - Any custom PowerShell script interacting with OneNote MUST use `powershell.exe -STA`. Running in MTA (Multi-Threaded Apartment) triggers `0x80010106` or `Unexpected HRESULT`.

3. **Desktop App State**:
   - The OneNote desktop app does not need to be visibly open; the COM API will automatically start a headless or background instance if installed.
