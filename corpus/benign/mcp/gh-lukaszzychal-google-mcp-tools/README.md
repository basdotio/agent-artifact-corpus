# 🔗 Google Multi-Account MCP Server

**Author:** [Łukasz Zychal](https://lukaszzychal.dev/) | [LinkedIn](https://www.linkedin.com/in/lukaszzychal/?isSelfProfile=true)
A custom **MCP (Model Context Protocol)** server in Python that gives Claude and Gemini access to multiple Google accounts simultaneously — without external intermediaries, 100% privately.

**Supported services:** Gmail · Google Drive · Calendar · YouTube · Sheets · Analytics · AdSense · Fitness

### 🛠️ Full CRUD Support (Create, Read, Update, Delete):
| Service | 👁️ Read | ➕ Create | ✏️ Update | 🗑️ Delete |
|---|---|---|---|---|
| **Calendar** | `calendar_list_events`, `calendar_get_event`, `calendar_list_calendars` | `calendar_create_event` (+ Google Meet) | `calendar_update_event` (time, title, description) | `calendar_delete_event` |
| **Google Drive** | `drive_list_files`, `drive_search_files`, `drive_get_file_info`, `drive_read_text_file`, `drive_list_folders` | `drive_create_folder`, `drive_upload_text_file` | `drive_rename_file` | `drive_trash_file`, `drive_delete_file` |
| **Gmail** | `gmail_list_emails`, `gmail_get_email`, `gmail_search_emails` | `gmail_send_email`, `gmail_create_draft` | `gmail_mark_as_read` | `gmail_trash_email`, `gmail_untrash_email` |
| **Google Sheets** | `sheets_read_range`, `sheets_list_sheets` | `sheets_create`, `sheets_add_sheet` | `sheets_write_range`, `sheets_append_row` | `sheets_clear_range`, `sheets_delete_sheet` |
| **Google Accounts**| `list_accounts` | `python auth.py add <id>` | — | `revoke_account_access` |

---

## 📋 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Google Cloud Console Configuration](#2-google-cloud-console-configuration)
3. [Project Installation](#3-project-installation)
4. [Claude Desktop Integration](#4-claude-desktop-integration)
5. [Gemini (Google AI Studio) Integration](#5-gemini-google-ai-studio-integration)
6. [First Login — OAuth2](#6-first-login--oauth2)
7. [Example Prompts](#7-example-prompts)
8. [Account Management](#8-account-management)
9. [Extending with New APIs](#9-extending-with-new-apis)
10. [Open-Source Version](#10-open-source-version)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

| Requirement | Minimum Version | Verification |
|-----------|-----------------|-------------|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Claude Desktop | latest | [download](https://claude.ai/download) |
| Google Account | any | — |

---

## 2. Google Cloud Console Configuration

> ⏱ Time: **approx. 15 minutes** | You do this **once**.

### Step 2.1 — Create a project

1. Go to **[console.cloud.google.com](https://console.cloud.google.com/)**
2. Click the project selector (top bar) → **"NEW PROJECT"**
3. Project name: `google-mcp-server` (any name)
4. Click **"CREATE"** and wait for initialization (~10 seconds)
5. Ensure the new project is selected in the selector

---

### Step 2.2 — Enable necessary APIs

1. In the side menu, go to **"APIs & Services"** → **"Library"**
2. Search for and enable **each** of the following APIs (click → "ENABLE"):

| API to enable | Where to search |
|-----------------|--------------|
| **Gmail API** | search: `gmail` |
| **Google Drive API** | search: `drive` |
| **Google Calendar API** | search: `calendar` |
| **YouTube Data API v3** | search: `youtube data` |
| **YouTube Analytics API** | search: `youtube analytics` |
| **YouTube Reporting API** | search: `youtube reporting` |
| **Google Sheets API** | search: `sheets` |
| **Google Analytics Data API** | search: `analytics data` |
| **AdSense Management API** | search: `adsense` |
| **Fitness API** | search: `fitness` |

> 💡 **Tip:** You can enable only those APIs that you will actually use. The rest will be inactive even if they are in the SCOPES.

---

### Step 2.3 — OAuth Consent Screen Configuration

1. In the side menu: **"APIs & Services"** → **"OAuth consent screen"**
2. Select User Type: **"External"** → click **"CREATE"**

**Fill out the form:**

| Field | Value |
|------|---------|
| App name | `Google MCP Server` (any name) |
| User support email | Your email address |
| App logo | (optional, skip) |
| App domain | (empty — skip the entire section) |
| Developer contact | Your email address |

3. Click **"SAVE AND CONTINUE"**

**"Scopes" Tab:**

4. Click **"ADD OR REMOVE SCOPES"**
5. In the search box, sequentially enter and check:
   - `gmail.readonly`, `gmail.send`, `gmail.modify`
   - `drive.readonly`
   - `calendar.readonly`, `calendar`
   - `youtube.readonly`, `yt-analytics.readonly`
   - `spreadsheets`
   - `analytics.readonly`
   - `adsense.readonly`
   - `fitness.activity.read`
6. Click **"UPDATE"** → **"SAVE AND CONTINUE"**

> ⚠️ You do not have to select all of them. Choose only the ones you plan to use.

**"Test users" Tab:**

7. Click **"ADD USERS"**
8. Enter **your email addresses** — **every Google account** you want to use, e.g.:
   ```
   john.doe@gmail.com
   john.doe@company.com
   ```
9. Click **"ADD"** → **"SAVE AND CONTINUE"**

> 🔐 **Why?** Your app is in "Testing" mode. Google only lets addresses from this list through it. This is not necessary after moving to "In production" status (required for a commercial version).

---

### Step 2.4 — Create Credentials (credentials.json)

1. In the side menu: **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. Application type: **"Desktop app"**
4. Name: `MCP Local Client`
5. Click **"CREATE"**
6. In the popup window, click **"DOWNLOAD JSON"**
7. Save the downloaded file as:
   ```
   GoogleMCP/credentials/credentials.json
   ```

> 🚨 **NEVER upload this file to GitHub or share it!** It contains your private app key.

---

## 3. Project Installation

```bash
# 1. Clone or download the project
cd /path/to/GoogleMCP

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the environment
source venv/bin/activate          # macOS / Linux
# or: venv\Scripts\activate       # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Check if everything works
python -c "import mcp; import googleapiclient; print('OK')"
```

Ensure the credentials file is in place:
```
credentials/credentials.json   ← downloaded in step 2.4
```

### Docker Option 🐳
If you prefer not to set up a local Python environment, you can build a Docker image and run the server inside a container. Make sure to mount the `credentials` directory as a volume to persist your tokens across restarts.

```bash
# Build the image (from the project directory)
docker build -t google-mcp-server .

# Test the server (it should wait for stdio input)
docker run -i -v $(pwd)/credentials:/app/credentials google-mcp-server
```

---

## 4. Claude Integration

> **Why doesn't Claude in the browser (claude.ai) have access to MCP?**  
> Claude running in the browser operates **in the cloud** — it has no visibility into your local computer. This MCP server runs **locally**. For Claude to access it, you need to use a local client: **Claude Desktop** (app) or **Claude Code CLI** (terminal).

---

### Option A — Claude Code CLI (terminal, same as Antigravity IDE)

Claude Code CLI works just like Antigravity IDE — it launches the MCP server as a local child process.

#### Installation
```bash
npm install -g @anthropic-ai/claude-code
```

#### Register the MCP server
```bash
claude mcp add --scope user google-multi-account -- \
  /Users/YOUR_NAME/mcp-servers/google-mcp-tools/venv/bin/python \
  /Users/YOUR_NAME/mcp-servers/google-mcp-tools/server.py
```

#### Launch
```bash
claude
```
Then in the chat ask e.g. `"List available Google accounts"` — the tools will be fully available.

---

### Option B — Claude Desktop (app)

#### Step 4.1 — Find the configuration file

| System | Path |
|--------|---------|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/claude/claude_desktop_config.json` |

```bash
# macOS — open the folder in Finder
open ~/Library/Application\ Support/Claude/
```

#### Step 4.2 — Add server configuration

Open the `claude_desktop_config.json` file and add (or complete an existing one):

```json
{
  "mcpServers": {
    "google-multi-account": {
      "command": "/Users/YOUR_NAME/mcp-servers/google-mcp-tools/venv/bin/python",
      "args": [
        "/Users/YOUR_NAME/mcp-servers/google-mcp-tools/server.py"
      ]
    }
  }
}
```

> ⚠️ **Important:** Use the **full path** to Python from the virtual environment (`venv/bin/python`), not the system `python`.

Quick path check:
```bash
cd /Users/YOUR_NAME/mcp-servers/google-mcp-tools
source venv/bin/activate
which python
# Copy this output to the "command" field in the JSON above
```

#### Step 4.3 — Verification

1. **Fully restart Claude Desktop** (don't just close the window — use Quit from the menu bar)
2. Open a **new** chat
3. Look for the 🔨 (hammer/tools) icon in the interface
4. Click it → a list of tools with `google-multi-account` should appear
5. Test by asking Claude:
   > `"What Google accounts do I have connected?"`  
   You should get the list: `praca_dev`, `prywatne`, `prywatne2`, `publiczne`

---

## 5. Gemini and Antigravity IDE Integration

### Path 0 — Antigravity IDE (Gemini in IDE) — ✅ CONFIGURED

In **Antigravity IDE**, MCP servers are configured in the file:
`~/.gemini/config/mcp_config.json`

The server has already been added to your configuration:
```json
"google-multi-account": {
  "command": "/Users/lukaszzychal/PhpstormProjects/GoogleMCP/venv/bin/python",
  "args": [
    "/Users/lukaszzychal/PhpstormProjects/GoogleMCP/server.py"
  ],
  "env": {}
}
```

> **NOTE — Do you need a Gemini API key in Antigravity IDE?**
> **NO.** In Antigravity IDE, the agent uses the built-in subscription / session of the IDE environment. The MCP server runs locally as a child process via stdio.
> 
> **Then what is the `GEMINI_API_KEY` key for?**
> The Gemini API key (`GEMINI_API_KEY`) from [Google AI Studio](https://aistudio.google.com/apikey) is **only** needed if you run external developer Python scripts (e.g., `gemini_client.py`) outside the Antigravity environment that connect directly to the Gemini API via the `google-genai` SDK.

---

### Path A — Gemini CLI (local, via terminal)

Google provides the `gemini` CLI tool that supports the MCP protocol.

#### Install Gemini CLI
```bash
# Requires Node.js 18+
npm install -g @google/gemini-cli

# Login
gemini auth login
```

#### MCP configuration in Gemini CLI
Create or edit the config file:
```bash
nano ~/.gemini/settings.json
```

Add the MCP server configuration similarly to Claude Desktop.

---

## 6. First Login — OAuth2

Upon the **first use** of any new account (`account_id`), the server automatically opens the browser.

### What happens step by step:

```
Claude/Gemini → calls gmail_list_emails(account_id='work')
     ↓
server.py → looks for the file credentials/token_work.json
     ↓
File does not exist → opens browser with Google login screen
     ↓
You log in to your account (e.g., john@gmail.com)
     ↓
Google asks: "Allow Google MCP Server to access...?"
     ↓
You click "Allow"
     ↓
Token saved in: credentials/token_work.json
     ↓
Subsequent uses → automatically, without a browser (token refreshed hourly)
```

### What is `account_id` (e.g., `"work"`, `"private"`)?

`account_id` is **your own short alias (label)** that you assign to a given Google account:
- **You do not need to provide the full email address** in prompts. Instead of writing *"Check mail on lukasz.kowalski.firma@gmail.com"*, you tell the model: *"Check mail on the **work** account"*.
- Each alias creates a separate token file in the `credentials/token_<alias>.json` directory (e.g., `token_work.json`, `token_private.json`).
- You can use any name: `work`, `private`, `company`, `marketing`, `youtube-channel`, etc.

### Two ways to log in / add accounts:

#### Method A — Via terminal (CLI – recommended at the start):
You can log in an account upfront before starting the chat:
```bash
source venv/bin/activate
python auth.py add work
```

#### Method B — Automatically via a chat query (Claude / Gemini):
Just use the account name in a query:
```
"Check emails on the 'work' account"
```
The server will detect the missing token, open a browser window, and automatically save the token after logging in.

---

## 7. Example Prompts

### Gmail
- "Show my 10 latest unread emails on the 'work' account"
- "Do I have any emails from boss@company.com on the 'work' account?"
- "Send an email to john@example.com from the 'work' account with the subject 'Offer'"

### Google Drive
- "Show files from Drive on the 'work' account modified recently"
- "Find PDF files on my 'private' drive"
- "Create a folder 'Reports 2026' on the 'work' drive"

### Google Calendar
- "What do I have planned over the next 7 days? Account: 'work'"
- "Create a 'Stand-up' meeting tomorrow at 9:00 on the 'work' account with a Google Meet link"
- "Delete the meeting with ID 'abc123' and notify participants"

### YouTube
- "Provide stats for my YouTube channel (account: 'work')"
- "Search for videos on 'Python MCP tutorial'"

### Google Sheets
- "Read data from the range 'Sheet1!A1:D20' in file '1xyz...'"
- "Add row ['John', 'Doe', '500', '2026-09-27'] to the sheet"

---

## 8. Account Management

### Checking logged-in accounts
```bash
python auth.py list
```
Or ask in chat: "List available Google accounts".

### Logging in / adding a new account
```bash
python auth.py add work
```

### Logging out / removing an account
Method 1 (CLI):
```bash
python auth.py revoke work
```
Method 2 (Chat): "Log out the 'work' account".

---

## 9. Extending with New APIs

Add new services by enabling the API in Google Cloud Console, adding the scope to `config.py`, creating a tools module, and registering it in `server.py`.

---

## 10. Open-Source Version

If you want to share the project on GitHub:
- Ensure your `.gitignore` protects your keys (`credentials/` and `credentials.json`).
- Provide instructions and `.env.example` templates.

---

## 11. Troubleshooting

- **`FileNotFoundError: credentials.json`**: Make sure you downloaded the client secret from Google Cloud Console and placed it in `credentials/`.
- **`Error 403: access_denied`**: Your email address is not in the Test Users list in the OAuth consent screen.
- **`Error 400: redirect_uri_mismatch`**: Incorrect credentials type — you must use "Desktop app".
- **Claude doesn't see tools**: Ensure the path in `claude_desktop_config.json` points to the correct virtual environment `venv/bin/python`.

## 🔒 Security Summary

| File | Where | Security |
|------|-------|---------------|
| `credentials.json` | `credentials/` | 🔴 NEVER commit! |
| `token_*.json` | `credentials/` | 🔴 NEVER commit! |

## 📄 License
MIT License.

## 🤝 Roadmap
- [x] Gmail, Google Drive, Calendar, YouTube, Google Sheets, Analytics, AdSense
- [ ] Google Tasks, Contacts, Forms
- [ ] Docker container
