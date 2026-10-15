# Outlook Local MCP Server (`outlook-local`)

A fast, robust **Model Context Protocol (MCP)** server that connects local Microsoft Outlook (Classic Desktop on Windows) directly to AI agents and coding assistants like **Claude Desktop**, **Cursor**, **Antigravity**, **VS Code (GitHub Copilot / Cline / Roo Code)**, and other MCP-compliant clients.

---

## 🌟 Features

- ⚡ **Ultra-Fast Search (`search_emails`)**: Uses native Outlook DASL / Restrict filters. Searches subjects, senders, and recipients in milliseconds across Inbox, Sent Items, and subfolders.
- 📬 **Reliable Email Reader (`get_email_details`, `get_recent_emails`)**: Dual `EntryID` + `StoreID` resolution to open any email without COM client errors, even in shared mailboxes, subfolders, or secondary accounts.
- 📎 **Attachment Management (`list_attachments`, `save_attachments`)**:
  - Lists attachments with file names, sizes, and automatic detection of inline signature logos.
  - Extracts and saves attachments (PDF specs, Excel quotes, etc.) directly to a target directory without overwriting existing files.
- ✍️ **Drafts, Replies & Emails (`create_draft`, `send_email`, `create_reply_draft`, `reply_email`)**:
  - Creates new emails or replies to existing threads (`In-Reply-To`, conversation history, quoted message preserved).
  - Supports `reply_all=True` to reply to all participants.
  - Generates drafts or sends messages silently in the background without stealing focus or opening popup windows.
  - Professional HTML formatting (Arial 10pt).
  - **Dynamic Signature Detection**: Automatically detects and applies the user's default signature from Outlook settings (via Windows Registry / Microsoft 365 Roaming Signatures).
- 📅 **Calendar (`get_calendar_events`)**: Retrieves upcoming appointments and meetings with recurrence support.
- 🛡️ **Unicode & UTF-8 Safe**: Built-in sanitization for non-breaking spaces, currency symbols, and emojis to prevent Windows `cp1252` encoding crashes.

---

## 📋 Prerequisites

1. **Operating System**: Windows 10 or Windows 11.
2. **Microsoft Outlook**: **Classic Desktop Outlook** (included in Microsoft 365, Office 2016, 2019, 2021, 2024).
   > **Note**: The free web-based "New Outlook for Windows" does **not** support the Windows COM MAPI interface. You must use the classic Outlook desktop application.
3. **Python**: Python 3.10 or higher.

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/padimato/outlook-mcp.git
cd outlook-mcp
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

*(Dependencies: `mcp>=1.0.0` and `pywin32>=306`)*

---

## 🔌 Configuration

Add the server to your MCP client configuration file:

### Claude Desktop
File: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "outlook-local": {
      "command": "python",
      "args": [
        "C:/path/to/outlook-mcp/server.py"
      ]
    }
  }
}
```

### Cursor
Add to your Cursor Settings (`Features` > `MCP Servers`):
- **Name**: `outlook-local`
- **Type**: `command`
- **Command**: `python C:/path/to/outlook-mcp/server.py`

### Antigravity
Add to `mcp_config.json`:

```json
{
  "mcpServers": {
    "outlook-local": {
      "command": "python",
      "args": [
        "C:/path/to/outlook-mcp/server.py"
      ]
    }
  }
}
```

---

## 🛠️ Available MCP Tools

| Tool | Description |
|---|---|
| `search_emails` | Rapid search in Subject, Sender, Recipients (DASL filter). Returns `EntryID` and `StoreID`. |
| `get_recent_emails` | Retrieves the most recent emails from the Inbox. |
| `get_email_details` | Retrieves full body text, sender, dates, and attachment list using `entry_id` and optional `store_id`. |
| `list_attachments` | Lists attachments of an email (index, filename, size, inline tag). |
| `save_attachments` | Saves specified or all attachments to a target local folder. |
| `send_email` | Sends a new email with optional attachments (`attachment_paths`), HTML styling, and default signature. |
| `create_draft` | Creates a new email draft with optional attachments (`attachment_paths`) silently (option to display via `open_window=True`). |
| `create_reply_draft` | Creates a reply draft in an existing email thread (quotes history, preserves thread, optional attachments, option for `reply_all`). |
| `reply_email` | Sends an immediate reply in an existing email thread (quotes history, preserves thread, optional attachments, option for `reply_all`). |
| `get_calendar_events` | Retrieves upcoming calendar events for the next N days. |

---

## ⚙️ Advanced Configuration

### Override Default Signature
By default, the server inspects the Windows Registry to identify which signature you chose as default for new messages in Outlook.
If you wish to force a specific signature by name, set the environment variable:

```bash
set OUTLOOK_SIGNATURE_NAME="My Custom Signature"
```

### Recipient Email Format
For maximum reliability with MAPI address resolution, recipient email addresses are automatically formatted as `<user@example.com>`.

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
