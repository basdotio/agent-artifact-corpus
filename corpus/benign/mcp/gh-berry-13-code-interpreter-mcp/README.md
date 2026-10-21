# WIP
# LibreChat Code Interpreter MCP Server

A Model Context Protocol (MCP) server that wraps the [LibreChat Code Interpreter API](https://code.librechat.ai/docs), exposing code-execution and file-management endpoints as MCP tools. Easily integrate sandboxed code execution into any MCP-compatible client.

---

## Features

* **executeCode** — Run arbitrary code (Python, JavaScript, TS, Go, C, C++, Java, PHP, Rust, Fortran, R, D, F90) in a secure sandbox
* **downloadFile** — Retrieve binary or text files generated during execution
* **uploadFiles** — Send files (binary or text) to a session for inclusion in code runs
* **getFilesInfo** — List metadata for files in a session (names, sizes, timestamps)
* **deleteFile** — Remove a file from a session

All operations require an API key from LibreChat Code Interpreter and adhere to MCP’s `tools/list` and `tools/call` schemas

---

## Prerequisites

* Node.js ≥ 16
* npm or yarn
* A valid LibreChat API key (set in `LIBRECHAT_API_KEY`)

---

## Installation

```bash
# Clone this repo
git clone <your-repo-url>
cd <your-repo-folder>

# Install dependencies
yarn install   # or `npm install`
```

---

## Configuration

Create a `.env` in the project root containing:

```
LIBRECHAT_API_KEY=sk-...your_api_key_here...
```

---

## Running the Server

```bash
# If using ts-node:
npx ts-node src/librechat-mcp-server.ts

# Or compile then run:
tsc && node dist/librechat-mcp-server.js
```

By default, the server communicates over stdio (suitable for local MCP playgrounds, IPC, or Docker streams)

---

## MCP Client Quick Start

Below is an example using the official [MCP TypeScript SDK](https://npmjs.com/package/@modelcontextprotocol/sdk) to call `executeCode`:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { ListToolsResultSchema, CallToolResultSchema } from "@modelcontextprotocol/sdk/types";

async function main() {
  const transport = new StdioClientTransport({ command: "node dist/librechat-mcp-server.js" });
  const client = new Client({ name: "example-client", version: "1.0.0" }, {});
  await client.connect(transport);

  // List available tools
  const tools = await client.request(
    { method: "tools/list" },
    ListToolsResultSchema
  );
  console.log("Available MCP tools:", tools.tools.map(t => t.name));

  // Execute Python code
  const codeResult = await client.request(
    {
      method: "tools/call",
      params: {
        name: "executeCode",
        arguments: {
          code: "print(\"Hello from LibreChat!\")",
          lang: "py",
          user_id: "user123",
          entity_id: "assistant_ABC123",
          files: [],
        },
      },
    },
    CallToolResultSchema
  );

  console.log("Execution result:", codeResult.content[0].json);
}

main().catch(console.error);
```

---

## Tool Schemas

| Tool Name    | Input Parameters                                                            |
| ------------ | --------------------------------------------------------------------------- |
| executeCode  | `code` (string), `lang` (enum), `args?`, `user_id?`, `entity_id?`, `files?` |
| downloadFile | `session_id` (string), `fileId` (string)                                    |
| uploadFiles  | `entity_id` (string), `files` (array of `{ name, content, contentType }`)   |
| getFilesInfo | `session_id` (string), `detail?` (`simple` or `detailed`)                   |
| deleteFile   | `session_id` (string), `fileId` (string)                                    |

Combine these via MCP’s standard `tools/list` and `tools/call` messages to build powerful code-automation flows

---

## Development

* **Lint**: `npm run lint`
* **Type-check**: `npm run build`
* **Format**: `npm run format`

Feel free to open issues or pull requests!
