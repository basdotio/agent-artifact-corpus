# Google Sheets MCP

A Model Context Protocol (MCP) connector for Google Sheets that allows AI agents to interact with spreadsheets directly.

## Demo

https://github.com/user-attachments/assets/cc4729d9-4e6e-437b-848b-6da9a09418c3

## Setup

1. Clone this repository:
```bash
git clone https://github.com/mkummer225/google-sheets-mcp
cd google-sheets-mcp
```


2. Install dependencies:
`npm install`


3. Build:
`npm run build`


4. Create OAuth credentials in Google Cloud Platform:
   - Create a new project in [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the [Google Sheets API](https://console.cloud.google.com/marketplace/product/google/sheets.googleapis.com)
   - Configure the OAuth consent screen
   - Create OAuth client ID credentials (Desktop application) with an appropriate redirect URI (ex: http://localhost:3000/oauth2callback)
   - Download the credentials and save as `gcp-oauth.keys.json` in the `dist` subdirectory


5. Start the MCP server (you'll automatically be prompted to authenticate/re-authenticate your Google account when necessary):
`npm run start`


## Usage

Sample config:
```json
{
    "mcpServers": {
    "google-sheets-mcp": {
      "command": "node",
      "args": [
        "/{path_to_dir}/google-sheets-mcp/dist/index.js"
      ]
    }
  }
}
```

Then you should be able to simply specify your spreadsheetId or ask your agent to create a new one for you.

## Available Actions

| Action | Description |
|--------|-------------|
| `refresh_auth` | Re-authenticate your Google Account when credentials expire |
| `list_sheets` | List all sheets/tabs in a Google Spreadsheet |
| `create_sheet` | Create a new sheet/tab in a Google Spreadsheet |
| `create_spreadsheet` | Create a new Google Spreadsheet |
| `read_all_from_sheet` | Read all data from a specified sheet |
| `read_headings` | Read the column headings from a sheet |
| `read_rows` | Read specific rows from a sheet |
| `read_columns` | Read specific columns from a sheet |
| `edit_cell` | Edit a single cell in a sheet |
| `edit_row` | Edit an entire row in a sheet |
| `edit_column` | Edit an entire column in a sheet |
| `insert_row` | Insert a new row at specified position |
| `insert_column` | Insert a new column at specified position |
| `rename_sheet` | Rename a sheet/tab in a spreadsheet |
| `rename_doc` | Rename a Google Spreadsheet |


## License

MIT