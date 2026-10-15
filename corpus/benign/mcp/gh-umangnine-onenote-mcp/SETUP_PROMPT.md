# 🤖 AI Agent One-Shot Setup Prompt

This prompt is designed for **AI coding assistants** (Google Antigravity, Claude Code, Cursor, Windsurf) to automatically set up, configure, and verify the **Microsoft OneNote MCP Server** on any Windows PC without manual intervention.

---

## 📋 Copy & Paste This Prompt to Your AI Agent:

```text
You are tasked with setting up and configuring the Microsoft OneNote MCP Server on this Windows machine.
Assume you are running inside the root directory of the cloned `onenote-mcp` repository.

Execute the following steps in sequence:

### Step 1: Detect Environment & Setup Virtual Environment
1. Check the current directory ($PWD) and confirm files `server.py`, `pyproject.toml`, and `scripts/` exist.
2. Verify Python 3.12+ is installed:
   - If Astral `uv` is installed, run: `uv sync`
   - Otherwise, create a virtual environment: `python -m venv .venv` and install:
     `.\.venv\Scripts\python.exe -m pip install "mcp[cli]>=1.26.0" "pyonenote>=0.0.2"`
3. Confirm that the virtual environment Python exists at `.\.venv\Scripts\python.exe`.

### Step 2: Automated Configuration via setup_mcp.ps1
Run the bundled setup script which automatically detects client configurations, copies schemas, and registers skills:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_mcp.ps1
```
*Alternatively, you can manually verify / configure:*
- **Google Antigravity**:
  - Update `%USERPROFILE%\.gemini\antigravity\mcp_config.json` with:
    ```json
    {
      "mcpServers": {
        "onenote": {
          "command": "<ABSOLUTE_PATH_TO_REPO>\\.venv\\Scripts\\python.exe",
          "args": ["<ABSOLUTE_PATH_TO_REPO>\\server.py"],
          "env": {
            "ONENOTE_BACKUP_DIR": "%LOCALAPPDATA%\\Microsoft\\OneNote\\16.0\\Backup"
          }
        }
      }
    }
    ```
  - Copy all `.json` files from `.\schemas\` to `%USERPROFILE%\.gemini\antigravity\mcp\onenote\`.
  - Copy folder `.\skills\onenote-mcp\` to `%USERPROFILE%\.gemini\config\skills\onenote-mcp\`.
- **Claude Code**:
  - Run: `claude mcp add --transport stdio onenote -- "<ABSOLUTE_PATH_TO_REPO>\.venv\Scripts\python.exe" "<ABSOLUTE_PATH_TO_REPO>\server.py"`
- **Claude Desktop / Cursor**:
  - Add to `%APPDATA%\Claude\claude_desktop_config.json` or `.cursor/mcp.json` using the absolute path to `<REPO_PATH>\.venv\Scripts\python.exe` and `<REPO_PATH>\server.py`.

### Step 3: Run Diagnostics & Verification Suite
1. Run the connection diagnostic tool:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\test_connection.ps1
   ```
2. Verify that:
   - PowerShell apartment state reports STA.
   - OneNote COM connection succeeds and lists active notebooks. (If it reports a lock or modal dialog, ensure Microsoft OneNote Desktop is launched on the taskbar and safe mode/login dialogs are cleared).
   - Local backup files (.one) are discovered in `%LOCALAPPDATA%\Microsoft\OneNote\16.0\Backup`. (If missing, instruct the user to open OneNote Desktop and click: File -> Options -> Save & Backup -> 'Back Up All Notebooks Now').
3. Run a smoke test to ensure `server.py` starts and loads cleanly:
   ```powershell
   .\.venv\Scripts\python.exe -c "import server; print('OneNote MCP Server initialized successfully!')"
   ```
4. Query live pages from OneNote to verify COM read functionality:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\read_onenote_page.ps1 -Notebook "<FirstNotebookName>" -Section "<FirstSectionName>"
   ```

### Step 4: Final Summary Report
Provide a concise summary table confirming:
- Python Virtual Environment Path
- Registered MCP Config Location
- Copied Schemas Count
- Copied Skills Location
- COM Hierarchy Health & Discovered Notebooks Count
- Backup Directory & .one File Count
```
