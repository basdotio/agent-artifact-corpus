# Google Drive MCP Server Instructions

## Overview
The Google Drive MCP server provides two main tools for interacting with Google Drive files:
1. gdrive_search - Find files in your Google Drive
2. gdrive_read_file - Read file contents directly using a file ID

## Available Tools

### 1. Search Tool
Search for files in Google Drive:
```xml
<use_mcp_tool>
<server_name>gdrive</server_name>
<tool_name>gdrive_search</tool_name>
<arguments>
{
  "query": "your search term"
}
</arguments>
</use_mcp_tool>
```
Returns: List of files with their names, MIME types, and IDs

### 2. Read File Tool
Read a file's contents using its ID:
```xml
<use_mcp_tool>
<server_name>gdrive</server_name>
<tool_name>gdrive_read_file</tool_name>
<arguments>
{
  "file_id": "the-file-id-from-search"
}
</arguments>
</use_mcp_tool>
```

## File Format Handling
The server automatically handles different file types:
- Google Docs → Markdown
- Google Sheets → CSV
- Google Presentations → Plain text
- Google Drawings → PNG
- Text/JSON files → UTF-8 text
- Binary files → Base64 encoded

## Common Usage Pattern

1. First, search for the file you want to read:
```xml
<use_mcp_tool>
<server_name>gdrive</server_name>
<tool_name>gdrive_search</tool_name>
<arguments>
{
  "query": "project proposal"
}
</arguments>
</use_mcp_tool>
```

2. Then, use the file ID from the search results to read its contents:
```xml
<use_mcp_tool>
<server_name>gdrive</server_name>
<tool_name>gdrive_read_file</tool_name>
<arguments>
{
  "file_id": "file-id-from-search-results"
}
</arguments>
</use_mcp_tool>
```

## Best Practices
1. Always use search first to find the correct file ID
2. Search results include file types (MIME types) to help identify the right file
3. Search is limited to 10 results per query, so use specific search terms
4. The server has read-only access to Google Drive

## Error Handling
If you encounter errors:
1. Verify the file ID is correct
2. Ensure you have access to the file
3. Check if the file format is supported
4. Verify the server is properly configured

Remember: Always use the tools in sequence - search first to get the file ID, then read_file to access the contents.
