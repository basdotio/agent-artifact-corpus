# Gmail MCP Server + Local LLM Client

A Python-based Model Context Protocol (MCP) server that connects Gmail to Claude Desktop and local Ollama-powered LLMs using the official Gmail API.

This project allows Claude Desktop or a local Ollama LLM to interact with a Gmail account through natural-language instructions.

## Features

- Search Gmail messages
- Get email details
- Read email bodies
- Send emails
- Send emails with attachments
- Delete emails
- Gmail search query support
- Google OAuth 2.0 authentication
- Claude Desktop integration
- Local Ollama LLM support
- Automatic discovery of locally installed Ollama models
- Interactive local model selection
- Ability to switch Ollama models during a session
- MCP client for connecting local LLMs to Gmail tools

---

## Architecture

### Claude Desktop

```text
┌──────────────────────┐
│    Claude Desktop    │
└──────────┬───────────┘
           │
           │ MCP / STDIO
           ▼
┌──────────────────────┐
│    mcp_gmail.py      │
│                      │
│      FastMCP         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      GmailTool       │
│                      │
│ Search / Read        │
│ Send / Delete        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      Gmail API       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Authorized Gmail   │
│       Account        │
└──────────────────────┘
```

### Local Ollama LLM

```text
┌────────────────────────────┐
│       Ollama Models        │
│                            │
│ Qwen / Llama / Ministral   │
│ DeepSeek / Other Models    │
└─────────────┬──────────────┘
              │
              │ Ollama API
              ▼
┌────────────────────────────┐
│         client.py          │
│                            │
│ Model selection            │
│ MCP client                 │
└─────────────┬──────────────┘
              │
              │ MCP / STDIO
              ▼
┌────────────────────────────┐
│       mcp_gmail.py         │
│                            │
│         FastMCP            │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│         GmailTool          │
│                            │
│ Search / Read / Send       │
│ Delete                     │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│         Gmail API          │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│      Authorized Gmail      │
│          Account           │
└────────────────────────────┘
```

The local LLM path keeps model inference on the user's machine. `client.py` acts as the MCP client and connects the selected Ollama model to the Gmail MCP server.

---

## Project Structure

```text
Gmail-MCP/
│
├── mcp_gmail.py
├── client.py
├── client-secret.json
│
├── token files/
│   └── token_gmail_v1.json
│
├── tools/
│   └── google_api/
│       ├── gmail_tools.py
│       └── google_apis.py
│
├── .gitignore
├── README.md
└── LICENSE
```

> `client-secret.json` and `token files/` contain authentication information and must never be committed to GitHub.

---

# Requirements

## Software

- Windows
- Python 3.12
- Claude Desktop
- Ollama
- Local LLM MCP client
- Google Cloud account
- Gmail account

For the local LLM client, you also need:

- Ollama
- At least one locally installed Ollama model

Check installed models:

```powershell
ollama list
```

Install the Ollama Python package:

```powershell
pip install ollama
```

Python 3.12 is recommended for this project.

Check your Python version:

```powershell
python --version
```

Expected:

```text
Python 3.12.x
```

---

# Installation

## 1. Clone the Repository

```powershell
git clone https://github.com/YOUR_USERNAME/Gmail-MCP.git
cd Gmail-MCP
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## 2. Install Dependencies

This project currently uses MCP 1.x and the `FastMCP` API.

Install the required packages:

```powershell
pip install "mcp==1.30.0" google-api-python-client google-auth-httplib2 google-auth-oauthlib pydantic ollama
```

Verify MCP:

```powershell
pip show mcp
```

You should see:

```text
Name: mcp
Version: 1.30.0
```

> This project currently uses the MCP 1.x `FastMCP` API. Do not install MCP 2.x unless the server implementation is migrated to the MCP 2.x API.

---

# Google Cloud Setup

The Gmail MCP server uses the Gmail API and Google OAuth 2.0.

## 1. Create a Google Cloud Project

Open:

https://console.cloud.google.com/

Create a new project or use an existing Google Cloud project.

---

## 2. Enable Gmail API

Open the Google Cloud API Library and enable:

```text
Gmail API
```

---

## 3. Configure OAuth Consent Screen

Configure the OAuth consent screen for your application.

If the application is in testing mode, add the Gmail account that you want to use as a test user.

---

## 4. Create OAuth Credentials

Create an OAuth Client ID for a desktop application.

Download the credentials JSON file.

Rename it to:

```text
client-secret.json
```

Place it in the root directory of the project:

```text
Gmail-MCP/
└── client-secret.json
```

### Security Warning

Never upload `client-secret.json` to GitHub.

---

# Gmail OAuth Permissions

The project currently uses the following Gmail OAuth scope:

```python
SCOPES = ['https://mail.google.com/']
```

This is a broad Gmail permission.

It allows the application to perform operations such as:

- Read Gmail messages
- Send Gmail messages
- Modify Gmail messages
- Delete Gmail messages

Only authorize the application if you trust the code and understand the permissions being granted.

---

# First Run

Navigate to the project directory:

```powershell
cd D:\Gmail-MCP
```

Run:

```powershell
python mcp_gmail.py
```

On the first run, Google OAuth authentication will open in your browser.

Select the Google account whose Gmail mailbox you want the MCP server to access.

After successful authentication, the OAuth token will be stored locally:

```text
token files/
```

For example:

```text
token files/token_gmail_v1.json
```

The token allows subsequent executions to reuse the Google authorization.

---

# Running the MCP Server

Run:

```powershell
python mcp_gmail.py
```

The server uses MCP STDIO transport and should remain running.

The server entry point is:

```python
if __name__ == "__main__":
    mcp.run()
```

---

# Local Ollama LLM Client

The project includes `client.py`, which allows a locally running Ollama model to use the Gmail MCP tools.

The architecture is:

```text
Local Ollama Model
        │
        ▼
    client.py
        │
        │ MCP / STDIO
        ▼
   mcp_gmail.py
        │
        ▼
     Gmail API
```

## 1. Install Ollama

Install Ollama and make sure it is running.

Check installed models:

```powershell
ollama list
```

For example:

```text
qwen3-coder:30b
```

## 2. Install the Ollama Python package

```powershell
pip install ollama
```

## 3. Run the Local LLM Client

From the project directory:

```powershell
cd D:\Gmail-MCP-Local
python client.py
```

The client starts the Gmail MCP server automatically and retrieves the available Gmail MCP tools.

## 4. Select a Local Model

`client.py` can discover locally installed Ollama models and lets the user select one.

Example:

```text
========================================
       LOCAL OLLAMA MODELS
========================================

1. qwen3:8b
2. ministral-3:8b
3. qwen3-coder:30b

========================================

Select a model [1-3]:
```

## 5. Change Models During a Session

Type:

```text
model
```

at the `You:` prompt to display the available models again and switch to another local Ollama model without restarting the application.

## 6. Example Requests

```text
Search my Gmail inbox for the 5 most recent emails.
```

```text
Find the latest email and tell me its subject and sender.
```

```text
Read the body of the latest email.
```

The local model decides which Gmail MCP tool is required, `client.py` executes the MCP tool, and the tool result is returned to the local model for the final response.

### Important

The current local client uses Ollama models. It does not automatically detect models managed by other local runtimes such as LM Studio or standalone llama.cpp installations.

The Gmail MCP server remains independent of the LLM runtime and can continue to be used with Claude Desktop.

---

# Claude Desktop Configuration

The MCP server can be connected to Claude Desktop using the Claude Desktop MCP configuration.

A typical configuration looks like:

```json
{
  "mcpServers": {
    "Gmail": {
      "command": "C:\\Users\\USERNAME\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
      "args": [
        "D:\\Gmail-MCP\\mcp_gmail.py"
      ]
    }
  }
}
```

Replace:

```text
USERNAME
```

with your Windows username.

Also replace the Python executable path if Python is installed somewhere else.

---

# Find Your Python Executable

Run:

```powershell
python -c "import sys; print(sys.executable)"
```

Example output:

```text
C:\Users\USERNAME\AppData\Local\Programs\Python\Python312\python.exe
```

Use this path as the `command` in the Claude Desktop configuration.

---

# Claude Desktop MSIX Installation

On some Windows installations, Claude Desktop is installed as a Microsoft Store/MSIX application.

In that case, the normal command:

```powershell
mcp install mcp_gmail.py
```

may return:

```text
Claude app not found
```

If this happens, locate the Claude Desktop package:

```powershell
Get-ChildItem "$env:LOCALAPPDATA\Packages" |
Where-Object { $_.Name -like "Claude*" }
```

The Claude configuration may be located inside the package directory under:

```text
LocalCache\Roaming\Claude\
```

Look for:

```text
claude_desktop_config.json
```

Add the Gmail MCP configuration to the existing `mcpServers` object.

---

# Available MCP Tools

The server currently exposes the following tools.

## Gmail-Send-Email

Sends an email using Gmail.

Supports:

- Plain text
- HTML
- File attachments

Example:

```text
Send an email to example@gmail.com with the subject "Test Email" and the body "Hello from Gmail MCP."
```

---

## Gmail-Search-Emails

Searches emails in Gmail.

Example:

```text
Search my Gmail inbox for the latest 5 emails.
```

Gmail search queries can also be used.

Example:

```text
Search my Gmail for emails from example@gmail.com.
```

Another example:

```text
Search my Gmail for emails with the subject "Gmail MCP Test Email".
```

---

## Gmail-Get-Email-Message-Details

Retrieves details about a Gmail message using its message ID.

The returned information can include:

- Message ID
- Subject
- Sender
- Recipients
- Snippet
- Attachment information
- Date
- Star status
- Labels

Example:

```text
Get the details of email MESSAGE_ID.
```

---

## Get-Email-Message-Body

Retrieves the body of a Gmail message using its message ID.

Example:

```text
Read the body of email MESSAGE_ID.
```

---

## Gmail-Delete-Email-Message

Deletes a Gmail message using its message ID.

Example:

```text
Delete email MESSAGE_ID.
```

> This is a destructive operation. Use this tool carefully.

---

# Testing the Local LLM Client

After confirming the Gmail MCP server works, test the local Ollama client.

## Test 1: Search Gmail

Run:

```powershell
python client.py
```

Then ask:

```text
Search my Gmail inbox for the 5 most recent emails.
```

The client should show an MCP tool call similar to:

```text
[MCP TOOL CALL] Gmail-Search-Emails
```

## Test 2: Read an Email

Ask:

```text
Find the latest email and read its body.
```

The local model should use the Gmail search/details/body tools as required.

## Test 3: Exit

Type:

```text
exit
```

to close the local client.

> Start with read-only operations. Test sending or deleting emails only after verifying that the local LLM and MCP tool-calling flow works correctly.

---

# Testing the Gmail MCP

After connecting the MCP server to Claude Desktop or running the local Ollama client, test the read operations first.

## Test 1: Search

Ask Claude:

```text
Search my Gmail inbox for the 5 most recent emails.
```

Claude should use:

```text
Gmail-Search-Emails
```

---

## Test 2: Email Details

Ask Claude to retrieve the details of one of the returned messages:

```text
Get the details of the most recent email.
```

---

## Test 3: Email Body

Then ask:

```text
Read the body of that email.
```

---

# Test Email

You can send yourself a test email.

### Subject

```text
Gmail MCP Test Email
```

### Body

```text
Hello!

This is a test email for my Gmail MCP project.

I am testing whether the MCP server can:

1. Find this email
2. Read the email details
3. Read the email body
4. Extract the subject, sender, recipient, date, and labels

Test ID: GMAIL-MCP-001

Regards,
Adithya
```

Then ask Claude:

```text
Search my Gmail for an email with the subject "Gmail MCP Test Email".
```

After finding it:

```text
Read the body of that email.
```

---

# Security

## Never Commit Credentials

The following files must never be committed to GitHub:

```text
client-secret.json
token files/
.env
API keys
OAuth tokens
private credentials
```

The `.gitignore` file should contain:

```gitignore
client-secret.json
token files/

__pycache__/
*.py[cod]

.venv/
venv/
env/

.vscode/
.idea/

.env
.env.*
```

Before pushing to GitHub, verify:

```powershell
git status --ignored
```

Make sure:

```text
client-secret.json
token files/
```

appear under ignored files.

You can also verify tracked files with:

```powershell
git ls-files
```

The output should not contain:

```text
client-secret.json
token files/token_gmail_v1.json
```

---

# Credential Exposure

If `client-secret.json` or an OAuth token is accidentally committed to a public GitHub repository:

1. Treat the credentials as compromised.
2. Revoke or rotate the affected credentials.
3. Remove the credentials from Git history.
4. Check GitHub security and secret-scanning alerts.
5. Generate new credentials if necessary.

Simply deleting a credential file from the latest commit does not necessarily remove it from Git history.

---

# Troubleshooting

## MCP 2.x Error

If you see:

```text
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

check the installed MCP version:

```powershell
pip show mcp
```

This project uses:

```text
mcp 1.30.0
```

Install it with:

```powershell
pip install "mcp==1.30.0"
```

---

## Google Authentication Error

If Google authentication does not complete, run:

```powershell
python mcp_gmail.py
```

and complete the browser authorization.

The browser should eventually display a message indicating that the authentication flow has completed.

---

## Claude Reports "Server disconnected"

Check the Claude Desktop MCP logs.

Common causes include:

- Python process exiting
- Missing `mcp.run()`
- Incorrect Python executable
- Missing dependencies
- Missing `client-secret.json`
- Missing OAuth token
- Incorrect working directory
- Permission errors

Make sure the end of `mcp_gmail.py` contains:

```python
if __name__ == "__main__":
    mcp.run()
```

---

## PermissionError: Windows System32

If you see:

```text
PermissionError: [WinError 5] Access is denied:
'C:\Windows\system32\token files'
```

the application is using the wrong working directory.

The Google API helper should determine the working directory from the client secret file:

```python
working_dir = os.path.dirname(os.path.abspath(client_secret_file))
```

This ensures the token directory is created relative to the project:

```text
D:\Gmail-MCP\token files\
```

instead of:

```text
C:\Windows\system32\token files\
```

---

# Development

Clone the repository:

```powershell
git clone https://github.com/YOUR_USERNAME/Gmail-MCP.git
```

Enter the project:

```powershell
cd Gmail-MCP
```

Install dependencies:

```powershell
pip install "mcp==1.30.0" google-api-python-client google-auth-httplib2 google-auth-oauthlib pydantic ollama
```

Add your Google OAuth credentials:

```text
client-secret.json
```

Run the server:

```powershell
python mcp_gmail.py
```

---

# Future Improvements

Possible future improvements include:

- Reply to emails
- Support for additional local LLM runtimes such as LM Studio and llama.cpp
- Forward emails
- Create drafts
- Mark emails as read/unread
- Archive emails
- Star/unstar messages
- Add/remove Gmail labels
- Download attachments
- Better nested attachment detection
- Improved HTML email parsing
- Better MIME parsing
- Batch email operations
- More granular Gmail OAuth scopes
- Automated tests
- Environment-based configuration
- Improved logging
- Docker support

---

# Disclaimer

This project interacts with Gmail using the Gmail API.

Use it at your own risk.

The author is not responsible for:

- Accidental email deletion
- Accidental email transmission
- Unauthorized Gmail access
- Exposure of OAuth credentials
- Loss or modification of Gmail data
- Improper configuration of the MCP server

Always review the permissions granted to the application before using it with an important Gmail account.

---

# License

This project is licensed under the MIT License.

See the `LICENSE` file for details.

---

# Author

Adithya

Built with:

- Python
- Model Context Protocol
- Gmail API
- Google OAuth 2.0
- Claude Desktop
- Ollama Local Models