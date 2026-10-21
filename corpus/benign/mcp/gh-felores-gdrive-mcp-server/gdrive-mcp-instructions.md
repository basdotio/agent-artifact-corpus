# Google Drive MCP Server Instructions

## Overview
The Google Drive MCP server provides access to Google Drive files and documents through two main interfaces:
1. Resources - for direct file access and reading
2. Tools - for searching files

## Capabilities

### Document Reading
The server can read and export various file types:

#### Google Workspace Documents
- Google Docs → Markdown
- Google Sheets → CSV
- Google Presentations → Plain text
- Google Drawings → PNG
- Other Google Apps files → Plain text

#### Regular Files
- Text files → UTF-8 text
- JSON files → UTF-8 text
- Binary files → Base64 encoded blob

### Search Functionality
Search through your entire Google Drive content using fullText search queries.

## How to Use

### 1. Listing Files
To get a list of files from Google Drive:
```
List my Google Drive files
```
This will return up to 10 files with their IDs, names, and MIME types.

### 2. Reading Documents
There are two ways to read documents:

#### Using File ID
If you know the file ID:
```
Read the Google Drive file with URI gdrive:///[file-id]
```

#### Using File Name
If you want to find and read a file by name:
```
List my Google Drive files and then read the document named "[document-name]"
```

### 3. Searching Files
To search for specific files:
```
Use the Google Drive search tool to find files containing "[search-term]"
```

## Example Commands

1. Read a specific Google Doc as markdown:
```
List my Google Drive files and then read the document named "Project Proposal"
```

2. Search for documents about a specific topic:
```
Use the Google Drive search tool to find files containing "quarterly report"
```

3. List recent files:
```
List my Google Drive files
```

## Notes
- The server has read-only access to Google Drive
- File listings are paginated with 10 files per page
- Google Docs are automatically exported as markdown
- Searches use Google Drive's fullText search capability
- All file access is read-only; no modifications are possible

## Error Handling
If you encounter any errors:
1. Verify the file ID or name is correct
2. Ensure you have access to the file
3. Check if the file format is supported
4. Verify the authentication credentials are valid

## Best Practices
1. When searching for files, use specific terms to narrow down results
2. For Google Docs, prefer reading them directly as they'll be automatically converted to markdown
3. When listing files, be aware that only 10 files are shown at a time
4. Use file IDs when possible as they're unique and more reliable than names
