# Project knowledge

Chlorpromazine MCP Server (Buzz Killington): MCP-compliant server providing anti-hallucination prompts/tools. Grounds LLMs by reading project files (.env, README, CHANGELOG) and searching docs via SerpAPI.

## Quickstart
- **Setup**: `npm install`; create `.env` with `SERPAPI_KEY` (req, from serpapi.com); opt: `SITE_FILTER` (domains), `PORT=3000`, `API_KEY`.
- **Dev**: `npm run dev` (tsx watch src/server.ts)
- **Test**: `npm run test` (node test/index.js)
- **Build & Start**: `npm run build` (tsc); `npm run start` (node dist/src/server.js)
- **Clean**: `npm run clean` (rimraf dist)

## Architecture
- **Entry**: src/server.ts (MCP StreamableHTTPServerTransport on /mcp)
- **Key directories**:
  | Dir | Purpose |
  |-----|---------|
  | src/config/ | Env validation, constants |
  | src/handlers/ | MCP JSON-RPC: message-handler.ts, prompts-handler.ts, tools-handler.ts |
  | src/services/ | file-reader.ts, rate-limiter.ts, serpapi.ts |
  | src/tools/ | kill-trip/, sober-thinking/ (schemas, handlers) |
  | src/prompts/ | buzzkill.ts, sober-thinking.ts |
  | src/types/ | app-types.ts, mcp-types.ts, tool-types.ts |
  | src/utils/ | logger.ts, security.ts |
- **Data flow**: HTTP JSON-RPC → handlers → services/tools/prompts → Zod-validated responses.

## Conventions
- **Formatting/linting**: TypeScript 5.8+, tsc; tsx for dev; no 'any' types.
- **Patterns**: Modular (one concern/file); Zod schemas everywhere; structured logging; security-first (sanitization, rate-limits, timeouts, secrets masking).
- **Gotchas**:
  - Node >=18 (ES modules, .js extensions in imports).
  - MCP SDK ^1.12.0; full protocol compliance.
  - Prod: Set API_KEY; deploy via Smithery.ai (env secrets).
  - Tests: Basic (test/index.js); no full suite.
  - Health: GET /healthz
