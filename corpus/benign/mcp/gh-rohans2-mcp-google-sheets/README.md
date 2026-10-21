# MCP-Google-Sheets

A TypeScript Model Context Protocol (MCP) server that lets AI agents securely interact with Google Sheets via well-typed “tools.” Built on Bun and the `@modelcontextprotocol/sdk`, it supports both OAuth2 and Service-Account flows.

---

## 🚀 Features

- **Authentication**  
  - **Service-Account** via base64-encoded `CREDENTIALS_CONFIG`  
  - **OAuth2** using `credentials.json` + `token.json` for user-scoped access  
- **Tools**  
  - `create`  
    Creates a new spreadsheet (and moves it into your Drive folder if configured).  
  - `listSheets`  
    Lists all sheet tabs in a given spreadsheet.  
  - `renameSheet`  
    Renames an existing sheet tab.  
  - `createSheet`  
    Adds a new sheet tab to a spreadsheet.  
  - `spreadsheetInfo`  
    Fetches metadata (title, sheet IDs, grid properties) for a spreadsheet.  
  - `listSpreadsheets`  
    Lists all spreadsheets in your configured Drive folder (or My Drive).  
  - `shareSpreadsheet`  
    Shares a spreadsheet with users (reader/commenter/writer) and sends notifications.  
  - `sheetData`  
    Reads cell values from a sheet and range (or whole sheet).  
  - `updateCells`  
    Writes a 2D array of values into an A1-style range.  
  - `batchUpdate`  
    Applies multiple range updates in a single request.  
  - `addRows` / `addColumns`  
    Inserts rows or columns at a specified index.  
  - `copySheet`  
    Copies a sheet tab between spreadsheets (optionally renaming it).

---

## 📋 Prerequisites

- **Bun** (v1.0+) installed and on your `PATH`  
- A **Google Cloud** project with:
  - **Sheets API** & **Drive API** enabled  
  - An **OAuth2 Client ID** (download `credentials.json`) **or** a **Service Account** key (download `service_account.json`)  
- (Optional) A Drive folder ID if you want new sheets moved out of My Drive  

---

## ⚙️ Setup

1. **Clone the repo**  
   ```bash
   git clone https://github.com/yourusername/mcp-google-sheets.git
   cd mcp-google-sheets
2. **Install dependencies**

```bash
bun install
```
3. **Configure environment**
   
Create a .env (or export) with:
```bash
# Base64-encoded service-account key JSON (optional)
CREDENTIALS_CONFIG=BASE-64 ENCODED SERVICE_ACCOUNT.JSON


# Or put your OAuth2 JSON files next to index.ts:
#   credentials.json  (OAuth client secret)
#   token.json        (generated after first OAuth run)

# The google email address that you'll use to access the spreadsheet
EMAIL_ID="Enter the email address you’ll use to access the spreadsheet"
# (Optional) ID of the Drive folder to store new sheets
DRIVE_FOLDER_ID=1a2B3c4D5e6F...
```
Tip: On Linux/macOS you can do

```bash
export CREDENTIALS_CONFIG=$(base64 service_account.json | tr -d '\n')
```
## ▶️ Running the Server
```bash
bun index.ts
```
On first OAuth2 run (if using credentials.json), you’ll see a URL. Visit it, grant access, then paste the code back into your terminal. A token.json will be generated automatically.

## 🔧 How It Works

**Initialization**

- initContext() picks your auth method (Service-Account → OAuth2 → error).

- Builds google.sheets & google.drive clients and stores them in a shared context.

**MCP Tool Registration**

- Each “tool” (e.g. create, listSheets, sheetData) is registered via server.tool(...).

**Transport**

- Uses StdioServerTransport so Claude can invoke tools over stdin/stdout.

**Invocation**

The agent sends a JSON request:

```json
{ "tool": "create", "args": { "title": "Budget Q2" } }
```
The server runs your handler, calls Google APIs, and returns JSON-wrapped results.

## 🛠️ Try It Out

Clone & configure as above.

Start the server:

```bash
bun index.ts
Invoke a tool via Claude
```
## Demo

<img width="1274" alt="mcp-google-sheets" src="https://github.com/user-attachments/assets/979d4fec-f5f1-42ff-bdc6-765b992f98a9" />
<img width="1274" alt="mcp-google-sheets" src="https://github.com/user-attachments/assets/7285ad5b-96c9-4960-9290-7be1ba9728f0" />


## ❤️ Contributing

Feel free to open issues or PRs for new tools, bug fixes, and enhancements.

