# Microsoft OneNote Model Context Protocol (MCP) Server

[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6.svg?logo=windows)](https://microsoft.com/windows)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB.svg?logo=python)](https://python.org)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-6C47FF.svg)](https://modelcontextprotocol.io)
[![Office: OneNote Desktop](https://img.shields.io/badge/Office-OneNote%20Desktop-7719AA.svg?logo=microsoftonenote)](https://onenote.com)

A high-performance, enterprise-grade **Model Context Protocol (MCP)** server providing AI coding assistants (Google Antigravity, Claude Code, Claude Desktop, Cursor) with full bi-directional integration into **Microsoft OneNote Desktop** on Windows.

> **Author**: [**Umang Kathiyara**](https://github.com/umangnine) (`@umangnine`)

---

## 🌟 Key Architecture & Capabilities

The server employs an intelligent **dual-engine architecture** requiring **zero cloud API tokens, zero Microsoft Graph registrations, and zero Azure tenant credentials**:

```
                                  ┌────────────────────────┐
                                  │   AI Assistant Client  │
                                  │ (Antigravity / Claude) │
                                  └───────────┬────────────┘
                                              │ MCP stdio
                                              ▼
                                  ┌────────────────────────┐
                                  │  OneNote FastMCP Server │
                                  │      (server.py)       │
                                  └─────┬────────────┬─────┘
                                        │            │
                 Offline Reading Engine │            │ Live Real-time Engine
                 (Zero latency backups) │            │ (Active desktop automation)
                                        ▼            ▼
                   ┌──────────────────────┐  ┌──────────────────────┐
                   │      pyOneNote       │  │ Windows COM (STA PS) │
                   │ (.one binary parser) │  │(OneNote.Application)│
                   └──────────┬───────────┘  └──────────┬───────────┘
                              ▼                         ▼
                   ┌──────────────────────┐  ┌──────────────────────┐
                   │ Local Backup Storage │  │ OneNote Desktop GUI  │
                   │ (%LOCALAPPDATA%\...) │  │ (Active Notebooks)   │
                   └──────────────────────┘  └──────────────────────┘
```

1. **Offline Reading Engine (`pyOneNote`)**:
   - Parses local `.one` binary backup files in `%LOCALAPPDATA%\Microsoft\OneNote\16.0\Backup\`.
   - Blazing-fast full-text search across all notebooks and sections without querying the UI.
2. **Live Automation Engine (Windows COM `OneNote.Application`)**:
   - Automates the running OneNote desktop application in real-time.
   - Creates and updates pages with native OneNote XML DOM elements in **< 1.0 second**.
3. **Rich Text & High-Fidelity Typography Engine**:
   - Automatically converts semantic HTML (`h1`-`h6`, `p`, `ul`/`ol`/`li`, `pre`/`code`, `table`, `hr`, `br`, `span`, `b`, `i`) into structured `<one:OE>` elements.
   - Enforces minimum **12.0pt font size** across body content to eliminate unstyled, squinty text.
   - Preserves **true hierarchical sub-bullet indentation** using native `<one:OEChildren>` nesting.
   - Renders **native grid tables** (`<one:Table bordersVisible="true">`) with styled headers and automatic column width calculation.
   - Generates clean, styled horizontal dividers (`──────────────────────────────────────────────────`) with vertical padding.
4. **Resilient Process & Connection Governance**:
   - Selectively cleans up headless background zombie processes (`MainWindowHandle == 0`) while guarding visible desktop UI windows.
   - Enforces Single-Threaded Apartment (STA) PowerShell execution.

---

## 📁 Repository Structure

```
onenote-mcp/
├── server.py                          # Polished FastMCP OneNote server implementation
├── pyproject.toml                     # Modern Python project configuration
├── uv.lock                            # Deterministic dependency lockfile
├── .python-version                    # Target Python version (3.12)
├── .gitignore                         # Git exclusion rules
├── LICENSE                            # MIT open-source license
├── README.md                          # Comprehensive setup & operations guide
├── SETUP_PROMPT.md                    # One-shot setup prompt for AI coding assistants
├── setup_mcp.cmd                      # One-click automated setup launcher for Windows
├── test_connection.cmd                # One-click environment diagnostic launcher
├── schemas/                           # MCP tool JSON schema declarations
│   ├── list_live_notebooks.json
│   ├── list_live_pages.json
│   ├── create_page.json
│   ├── append_to_page.json
│   ├── update_page_content.json
│   ├── read_live_page.json
│   ├── list_notebooks.json
│   ├── list_sections.json
│   ├── list_all_sections.json
│   ├── read_section.json
│   ├── search_notes.json
│   └── get_notebook_summary.json
├── scripts/                           # Standalone PowerShell diagnostic & utility scripts
│   ├── setup_mcp.ps1                  # Automated setup script (venv, schemas, skills, diagnostics)
│   ├── test_connection.ps1            # Diagnostic connection probe for COM and backup paths
│   └── read_onenote_page.ps1          # Standalone CLI reader for live OneNote pages
└── skills/                            # Agent Skill package for AI assistants
    └── onenote-mcp/
        ├── SKILL.md                   # Core skill workflow & formatting rules
        ├── references/
        │   ├── mcp-server-reference.md
        │   ├── onenote-xml-and-formatting.md
        │   └── page-parsing-and-reading.md
        └── scripts/
            └── read_onenote_page.ps1
```

---

## 🛠️ System Prerequisites

1. **Operating System**: Windows 10 or Windows 11 (64-bit).
2. **Microsoft OneNote Desktop**:
   - Microsoft 365, Office 2021, Office 2019, or Office 2016 desktop edition.
   - *Note: The discontinued "OneNote for Windows 10" (UWP app from the Microsoft Store) does NOT provide the COM Automation API. The desktop version must be installed.*
3. **Python**: Python 3.12+ installed (or [`uv`](https://github.com/astral-sh/uv)).
4. **OneNote Backups Enabled**:
   - Open OneNote Desktop.
   - Navigate to: **File → Options → Save & Backup**.
   - Ensure the backup path points to `%LOCALAPPDATA%\Microsoft\OneNote\16.0\Backup` (default).
   - Click **Back Up All Notebooks Now** to initialize the backup cache for offline search.

---

## 🚀 Setup & Installation on Windows

### Option 1: Fast Setup using `uv` (Recommended)

[`uv`](https://docs.astral.sh/uv/) provides lightning-fast, reproducible virtual environment setup:

```powershell
# 1. Clone the repository
git clone https://github.com/umangnine/onenote-mcp.git
cd onenote-mcp

# 2. Sync virtual environment and dependencies in one step
uv sync
```

### Option 2: Standard Python `pip` Setup

```powershell
# 1. Clone the repository
git clone https://github.com/umangnine/onenote-mcp.git
cd onenote-mcp

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install "mcp[cli]" pyOneNote
```

---

## 🤖 One-Shot AI Agent Setup Prompt (Fastest Setup)

If you use **Google Antigravity**, **Claude Code**, **Cursor**, or **Windsurf**, you can set up everything in one shot:
1. Clone this repository to any folder on your Windows machine:
   ```powershell
   git clone https://github.com/umangnine/onenote-mcp.git
   cd onenote-mcp
   ```
2. Open your AI coding assistant inside this directory.
3. Provide the ready-to-use prompt from [**`SETUP_PROMPT.md`**](SETUP_PROMPT.md).
Your AI agent will automatically create the virtual environment, install dependencies, register the MCP server, copy tool schemas and skills, and run the verification suite.

---

## ⚡ Automated One-Click Setup Script

Prefer running a script directly? We provide an automated setup script that handles environment creation, dependency synchronization, MCP registration, schema installation, and diagnostics:

```powershell
# In PowerShell:
powershell -ExecutionPolicy Bypass -File .\scripts\setup_mcp.ps1

# Or simply double-click / run the Windows batch launcher:
.\setup_mcp.cmd
```

---

## 🧪 Verifying the Environment

Verify your OneNote COM automation and backup discovery anytime using the diagnostics tool:

```powershell
# Option A: PowerShell
powershell -ExecutionPolicy Bypass -File .\scripts\test_connection.ps1

# Option B: One-click launcher (bypasses PowerShell ExecutionPolicy restrictions)
.\test_connection.cmd
```

**Expected output:**
```
============================================================
    Microsoft OneNote MCP Environment Diagnostics Tool     
============================================================

[OK] PowerShell Apartment State: STA (Required for OneNote COM)
[OK] OneNote desktop UI process is running (PID: 12345)

Testing OneNote COM API connection...
[OK] COM GetHierarchy succeeded! Found 3 active notebook(s).
     - Notebook: Notes-2026
         * Section: Update-Notes-26
         * Section: Work-Notes

Checking OneNote local backup files...
[OK] Backup directory found: C:\Users\...\AppData\Local\Microsoft\OneNote\16.0\Backup
[OK] Discovered 35 backup (.one) file(s) for offline reading.

============================================================
Diagnostics Complete: Environment is 100% HEALTHY! 🎉
============================================================
```

---

## ⚙️ Manual Configuration for AI Clients

If you prefer to configure your AI assistant manually rather than using `setup_mcp.cmd`:

### 1. Google Antigravity IDE

Open `%USERPROFILE%\.gemini\antigravity\mcp_config.json` and register the `onenote` server (replace `<path-to-repo>` with your absolute directory, e.g. `C:\\Projects\\onenote-mcp`):

```json
{
  "mcpServers": {
    "onenote": {
      "command": "<path-to-repo>\\.venv\\Scripts\\python.exe",
      "args": [
        "<path-to-repo>\\server.py"
      ],
      "env": {
        "ONENOTE_BACKUP_DIR": "%LOCALAPPDATA%\\Microsoft\\OneNote\\16.0\\Backup"
      }
    }
  }
}
```

*Tip: Copy all JSON files from `.\schemas\` to `%USERPROFILE%\.gemini\antigravity\mcp\onenote\` so the IDE eagerly exposes lazy schemas, and copy `.\skills\onenote-mcp\` to `%USERPROFILE%\.gemini\config\skills\onenote-mcp\`.*

### 2. Claude Code CLI

Inside your cloned repository directory, run:

```powershell
claude mcp add --transport stdio onenote -- "$PWD\.venv\Scripts\python.exe" "$PWD\server.py"
```

Verify status:
```powershell
claude mcp list
```

### 3. Claude Desktop / Cursor

Edit `%APPDATA%\Claude\claude_desktop_config.json` (or `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "onenote": {
      "command": "<path-to-repo>\\.venv\\Scripts\\python.exe",
      "args": [
        "<path-to-repo>\\server.py"
      ],
      "env": {
        "ONENOTE_BACKUP_DIR": "%LOCALAPPDATA%\\Microsoft\\OneNote\\16.0\\Backup"
      }
    }
  }
}
```

---

## 📖 MCP Tool Reference

| Tool Name | Parameters | Engine | Purpose & Description |
|:---|:---|:---:|:---|
| **`list_live_notebooks`** | *None* | COM | Lists all notebooks and sections currently open and active in the OneNote desktop GUI. |
| **`list_live_pages`** | `notebook_name`, `section_name` | COM | Lists all page titles and their persistent OneNote page IDs (`{GUID}{version}{id}`). |
| **`create_page`** | `notebook_name`, `section_name`, `title`, `content` | COM | Creates a brand-new page with rich HTML formatting in **< 1.0 second**. Auto-creates the section if it doesn't exist. |
| **`append_to_page`** | `page_id`, `content` | COM | Appends an additional rich HTML outline block to the bottom of an existing page. |
| **`update_page_content`**| `page_id`, `content` | COM | Replaces the entire outline content of an existing page with new rich HTML. |
| **`read_live_page`** | `page_id` (or `notebook_name`, `section_name`, `page_title`), `raw_xml` | COM | Reads a live page and converts headings, tables, and nested sub-bullets into structured Markdown. Set `raw_xml=true` to retrieve raw OneNote XML. |
| **`list_notebooks`** | *None* | Backup | Lists local notebook backup folders and section counts. |
| **`list_sections`** | `notebook_name` | Backup | Lists sections in a backup notebook with their file sizes. |
| **`list_all_sections`** | *None* | Backup | Recursively lists all notebooks and sections found in backup storage. |
| **`read_section`** | `notebook_name`, `section_name` | Backup | Extracts all plaintext from a section backup (`.one` file). |
| **`search_notes`** | `query` | Backup | Full-text keyword search across all local backup files with 160-character context snippets. |
| **`get_notebook_summary`**| `notebook_name` | Backup | Returns section outlines with ~200-character content previews. |

---

## 🎨 HTML Formatting & Typography Standards

When sending `content` to `create_page` or `append_to_page`, use standard HTML tags. The server automatically maps them to Microsoft OneNote XML:

### 1. Supported Tags & Visual Mapping

| HTML Element | OneNote XML Translation | Visual Output in OneNote |
|:---|:---|:---|
| `<h1>Title</h1>` | `<one:OE><one:T>` | 24.0pt bold text in Navy (`#003366`) with spacing |
| `<h2>Heading</h2>` | `<one:OE><one:T>` | 18.0pt bold text in Blue (`#004080`) with spacing |
| `<h3>Subhead</h3>` | `<one:OE><one:T>` | 14.0pt bold text in Slate (`#0059B3`) with spacing |
| `<p>Text</p>` | `<one:OE><one:T>` | 12.0pt clean body text |
| `<ul><li>...</li></ul>` | `<one:List><one:Bullet>` | Native OneNote bullet points |
| `<ul><li>Parent<ul><li>Child</li></ul></li></ul>` | Nested `<one:OEChildren>` | **True hierarchical sub-bullet indentation** |
| `<hr />` or `<br /><hr /><br />` | `<one:OE><one:T>` | Formatted divider (`──────────────────────────────────────────────────`) with vertical padding |
| `<table bordersVisible="true">` | `<one:Table>` | **Native OneNote grid table** with border lines |
| `<th>Header</th>` | `<one:Cell shadingColor="#EBF2FA">` | Table header cell with soft blue background shading |
| `<pre><code>code</code></pre>` | `<one:Table>` single cell | Monospace code block in Consolas font with shaded background (`#F5F7FA`) |
| `<b>`, `<i>`, `<u>`, `<span>` | CDATA inline styles | Bold, italic, underline, custom color styling |

### 2. Daily Work Report Architecture Template

For consistent engineering notes, sprint logs, and daily work reports:

```html
<h2>🔧 Service Architecture - Backend/API</h2>
<p><span style="font-family:Consolas, monospace;font-size:9.5pt;color:#666666;">my-project · branch: main</span></p>
<p><b>2026-09-30 (Wednesday)</b></p>
<ul>
  <li><b>Feature Area Title:</b>
    <ul>
      <li>Technical description bullet point 1</li>
      <li>Technical description bullet point 2</li>
    </ul>
  </li>
  <li><b>Impact:</b>
    <ul>
      <li>✅ Measurable outcome 1</li>
      <li>✅ Measurable outcome 2</li>
    </ul>
  </li>
</ul>

<br /><hr /><br />

<h2>🖥️ Frontend Web Application</h2>
<p><span style="font-family:Consolas, monospace;font-size:9.5pt;color:#666666;">web-client · branch: main</span></p>
<p><b>2026-09-30 (Wednesday)</b></p>
<ul>
  <li><b>UI Enhancements:</b>
    <ul>
      <li>Implemented responsive settings drawer</li>
    </ul>
  </li>
</ul>

<br /><hr /><br />

<h2>📊 Summary Metrics</h2>
<table bordersVisible="true">
  <tr>
    <th style="background-color:#EBF2FA;">Metric / Dimension</th>
    <th style="background-color:#EBF2FA;">Value / Outcome</th>
  </tr>
  <tr><td><b>Working Day</b></td><td>Wednesday, 30 September, 2026</td></tr>
  <tr><td><b>Total Commits</b></td><td>7</td></tr>
  <tr><td><b>Key Deliverables</b></td><td>Dynamic labels, Storage permissions, Webhook protection</td></tr>
  <tr><td><b>Repos Active</b></td><td>2</td></tr>
</table>

<p><i>Report generated with OneNote MCP</i></p>
```

---

## 🔧 Troubleshooting & Recovery Discipline

### 1. OneNote Desktop Shows Safe Mode Prompt (*"Start normally"*)
- **Symptom**: OneNote hangs on startup or displays a modal asking to *Start normally*, *Delete notebook cache*, or *Delete settings*.
- **Cause**: OneNote processes were forcefully killed (`Stop-Process -Force`) while holding file locks.
- **Remedy**:
  1. Click **"Start normally"** on the OneNote desktop window.
  2. Never blindly kill all `ONENOTE` processes. The server's built-in `_cleanup_orphan_onenote()` function selectively terminates **only headless background instances** (`MainWindowHandle == 0`), leaving visible user windows untouched.

### 2. COM Error `0x80042009` (*UpdatePageContent failed*)
- **Cause**: Passing unescaped block HTML tags (`<div>`, `<p>`, `<table>`) directly inside a single `<one:T><![CDATA[...]]></one:T>`.
- **Remedy**: The server's `_html_to_onenote_xml` parser automatically decomposes complex HTML into separate `<one:OE>` elements. Use standard semantic HTML tags and let the parser structure the XML.

### 3. KERNELBASE.dll Crash (`0xc06d007e`)
- **Cause**: Inserting literal `<br/>` tags inside OneNote CDATA text nodes.
- **Remedy**: In OneNote XML, line breaks between separate blocks must be represented as distinct `<one:OE>` elements or spacers, never unescaped HTML tags in CDATA.

### 4. PowerShell Apartment State Error
- **Cause**: PowerShell running in Multi-Threaded Apartment (MTA) mode.
- **Remedy**: All COM calls must execute in Single-Threaded Apartment mode (`powershell.exe -STA ...`). Both `server.py` and `scripts/read_onenote_page.ps1` enforce `-STA` by default.

---

## 📜 License & Attribution

- **Project Lead & Author**: [**Umang Kathiyara**](https://github.com/umangnine) (`@umangnine`)
- **License**: [MIT License](LICENSE) — free and open-source for personal and commercial use.
