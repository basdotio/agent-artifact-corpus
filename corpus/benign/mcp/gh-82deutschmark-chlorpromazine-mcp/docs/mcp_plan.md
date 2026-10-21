Chlorpromazine Model Context Protocol (MCP) Server — Single‑Path Build Guide v0.2
(inline fixes for robustness, security, and deployability)

⸻

1  Project setup

```bash

npm init -y
npm install --save @modelcontextprotocol/sdk dotenv
npm install --save-dev typescript ts-node
npx tsc --init            # edit tsconfig as shown below
```

*Node 18+ already ships the global fetch API, so the previous **node‑fetch** dependency is removed.*

⸻

2  Environment variables (.env, **git‑ignored**)

```env
SERPAPI_KEY=PLACEHOLDER_KEY      # key for the Search Engine Results Page API
SITE_FILTER=platform.openai.com/docs
PORT=8080
```

*SITE\_FILTER lets you widen/narrow search scope without code changes.*

Add `.env` and `dist/` to **.gitignore**.

⸻

3  server.ts

```ts
import 'dotenv/config';
import { Server } from '@modelcontextprotocol/sdk/server';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp';
import {
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema
} from '@modelcontextprotocol/sdk/server/schemas';

const SITE_FILTER = process.env.SITE_FILTER!;
const PORT = Number(process.env.PORT) || 3000;

// ---------------------------------------------------------------- helpers --
async function performSearch(query: string): Promise<string> {
  const apiKey = process.env.SERPAPI_KEY;
  if (!apiKey) return 'Search disabled: missing SERPAPI_KEY.';
  const url =
    `https://serpapi.com/search.json?engine=google&q=site:${SITE_FILTER}+${encodeURIComponent(query)}&api_key=${apiKey}`;
  const res = await fetch(url);
  const json: any = await res.json();
  const top = json?.organic_results?.[0];
  return top
    ? `${top.title} — ${top.snippet} (${top.link})`
    : 'No relevant information found.';
}

// ---------------------------------------------------------------- server ---
const server = new Server(
  { name: 'Chlorpromazine', version: '0.1.0' },
  { capabilities: { prompts: {}, tools: {} } }
);

// prompts/list
server.setRequestHandler(ListPromptsRequestSchema, async () => ({
  prompts: [
    {
      name: 'sequential_thinking',
      description: 'Solve problems step‑by‑step.',
      arguments: [{ name: 'QUESTION_TEXT', description: 'Problem statement', required: true }]
    },
    {
      name: 'fact_checked_answer',
      description: 'Answer with strict fact‑checking.',
      arguments: [{ name: 'USER_QUERY', description: 'User question', required: true }]
    }
  ]
}));

// prompts/get
server.setRequestHandler(GetPromptRequestSchema, async req => {
  const { name, arguments: args } = req.params;
  if (name === 'sequential_thinking') {
    return {
      description: 'Step reasoning',
      messages: [
        { role: 'system', content: { type: 'text', text: 'Think step‑by‑step and verify each step.' } },
        { role: 'user',   content: { type: 'text', text: `Problem: ${args['QUESTION_TEXT']}` } }
      ]
    };
  }
  if (name === 'fact_checked_answer') {
    return {
      description: 'Fact check',
      messages: [
        { role: 'system', content: { type: 'text', text: 'Provide only verified facts.' } },
        { role: 'user',   content: { type: 'text', text: `Question: ${args['USER_QUERY']}` } }
      ]
    };
  }
  throw new Error('Unknown prompt');
});

// tools/list
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'kill_trip',
      description: 'Live documentation search.',
      inputSchema: {
        type: 'object',
        properties: { query: { type: 'string' } },
        required: ['query']
      },
      annotations: { title: 'KillTrip Search', readOnlyHint: true, openWorldHint: true }
    }
  ]
}));

// tools/call
server.setRequestHandler(CallToolRequestSchema, async req => {
  try {
    const { name, arguments: args } = req.params;
    if (name !== 'kill_trip') throw new Error('Tool not found');
    const text = await performSearch(args['query']);
    return { content: [{ type: 'text', text }] };
  } catch (err: any) {
    return { content: [{ type: 'text', text: `Error: ${err.message}` }] };
  }
});

// ---------------------------------------------------------------- transport
const transport = new StreamableHTTPServerTransport({ port: PORT });
await server.connect(transport);

// health‑check route
transport.addRoute('GET', '/healthz', (_req, res) => res.end('ok'));

console.log(`Chlorpromazine MCP server listening on ${PORT}`);
```

Enhancements applied:

* null‑safe `performSearch`
* JSON error wrapper for tools/call
* `/healthz` endpoint for uptime monitors
* env‑driven port fallback (suits Cloudflare/Vercel)

⸻

4  TypeScript & package.json

*tsconfig.json* (only relevant diff)

```jsonc
{
  "compilerOptions": {
    "target": "es2020",
    "module": "esnext",
    "outDir": "dist",
    "esModuleInterop": true
  }
}
```

*package.json* script block

```json
"scripts": {
  "dev": "ts-node server.ts",
  "build": "tsc",
  "start": "node dist/server.js",
  "prepare": "npm run build"
},
"type": "module"
```

⸻

5  Local test checklist

1. `npm run dev`
2. Use MCP Inspector (or cURL) against [http://localhost:8080/v1/](http://localhost:8080/v1/)
    • `prompts/list` ⇒ two prompts
    • `prompts/get` ⇒ arguments substituted
    • `tools/list` ⇒ kill\_trip
    • `tools/call` payload `{ "query": "rate limit" }` ⇒ text snippet

⸻

6  Deployment on Smithery.ai

1. Push repo to GitHub.
2. In Smithery dashboard: connect repo.
3. Add secrets SERPAPI\_KEY, SITE\_FILTER, PORT.
4. Build trigger; health probe hits `/healthz`.
5. Register endpoint in your LLM config.

⸻

7  Operational notes

* .env never committed; rely on Smithery or Cloudflare secret store.
* Add semantic‑versioned base path (`/v1/`) now to avoid breaking clients later.
* Keep kill\_trip name if scope remains docs‑only; else rename to reflect broader search.


