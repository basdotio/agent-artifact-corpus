# OneNote MCP Server — Agent Instructions

## User Identity & Attribution
- **User Name**: **Umang Kathiyara**
- **GitHub**: [@umangnine](https://github.com/umangnine)
- **Identity Rule**: The user and git commit author is strictly **Umang Kathiyara**. Never refer to, address, or attribute work/commits to 'Umang Patel' or any other name. Always use **Umang Kathiyara**.

---

## Project Overview
A Windows-native **Model Context Protocol (MCP)** server providing AI assistants with bi-directional integration into **Microsoft OneNote Desktop**:
- **Offline Reading Engine**: Parses local `.one` binary backup files in `%LOCALAPPDATA%\Microsoft\OneNote\16.0\Backup\` using `pyOneNote` (zero UI overhead, ultra-fast search).
- **Live Automation Engine**: Automates active desktop OneNote via Windows COM (`OneNote.Application`) and PowerShell STA to create, read, append, and update pages in real-time.
- **Rich Text & Typography Engine**: Converts HTML into structured `<one:OE>` XML nodes with native `<one:Table>`, `<one:OEChildren>` nested lists, and strict 12.0pt+ font size guarantees.

---

## Essential Commands

### Environment & Server Execution
```powershell
# Sync Python virtual environment (recommended)
uv sync

# Run the FastMCP server directly
uv run server.py

# Run server with local .venv python
.\.venv\Scripts\python.exe server.py
```

### Diagnostics & Testing
```powershell
# Run environment diagnostics (checks COM API, STA state, UI process, and backup files)
powershell -ExecutionPolicy Bypass -File .\scripts\test_connection.ps1

# Read a live OneNote page via CLI script
powershell -ExecutionPolicy Bypass -File .\scripts\read_onenote_page.ps1 -Notebook "Notes-2026" -Section "Update-Notes-26" -PageTitle "My Page"
```

---

## Architecture & Code Conventions

1. **Stdio Safety for MCP Transport**:
   - `server.py` communicates over stdio using JSON-RPC. **Never** print diagnostic messages to standard output (`sys.stdout`).
   - Direct all logging to `sys.stderr` or the temp log file (`tempfile.gettempdir()/onenote_mcp.log`).

2. **Windows COM Apartment State (STA)**:
   - The OneNote COM automation interface requires Single-Threaded Apartment (STA).
   - Any PowerShell scripts invoking `New-Object -ComObject OneNote.Application` must execute with `-Sta`.

3. **Process Governance & Safety**:
   - OneNote COM calls can leave orphan headless background processes.
   - When cleaning up processes, only kill headless instances (`MainWindowHandle -eq 0`). **Never kill visible user desktop windows**.

4. **OneNote XML & Typography Standards**:
   - **Minimum 12.0pt font size**: Never generate body text below 12.0pt (or 12px). Headings scale from 14pt (h3) to 22pt (h1).
   - **Multi-OE Block Structure**: Each logical block (heading, paragraph, bullet item) must exist in its own `<one:OE>` element inside `<one:Outline><one:OEChildren>`.
   - **Hierarchical List Nesting**: Sub-bullets must use nested `<one:OEChildren>` inside the parent `<one:OE>`, using bullet style 2 for level 2, bullet style 3 for level 3.
   - **Grid Tables**: Use native `<one:Table bordersVisible="true">` with `<one:Columns>`, `<one:Row>`, and `<one:Cell>` elements with minimum 12pt cell content.

5. **Tool Schemas & Skills**:
   - Tool schemas are maintained in [schemas/](file:///D:/www/onenote-mcp/schemas/).
   - Agent skills are defined in [skills/onenote-mcp/SKILL.md](file:///D:/www/onenote-mcp/skills/onenote-mcp/SKILL.md).
