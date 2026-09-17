---
name: project-coding
description: Project-specific coding guidelines, naming conventions, architecture patterns, and code examples
---

# Project Coding Guidelines

This project is a YouTube Transcript MCP server built with TypeScript (strict mode, ESM) on Bun runtime, using `@modelcontextprotocol/sdk` v1.x, Zod v4, undici, and Vitest.

---

## Code Style

### Formatting

- **Indentation**: 2 spaces (no tabs).
- **Quotes**: Double quotes for all strings.
- **Semicolons**: Always use semicolons.
- **Trailing commas**: Use trailing commas in multi-line constructs (arrays, objects, parameters).
- **Line length**: Keep lines under 100 characters where practical.
- **Braces**: K&R style (opening brace on same line as statement).

### Types

- TypeScript strict mode is mandatory (`"strict": true` in tsconfig).
- Prefer `interface` for object shapes; use `type` for unions, intersections, and mapped types.
- Use Zod schemas as the single source of truth for runtime validation; derive TypeScript types with `z.infer<typeof MySchema>`.
- Avoid `any`. Use `unknown` when the type is genuinely unknown, then narrow with type guards.
- Use `as const` for literal values that should not widen.
- Export types with `export type` when only the type is needed (required by `isolatedModules: true`).
- Use the `satisfies` operator to validate object literals match a type without widening (TS 4.9+).

### Functions

- Prefer `function` declarations for top-level named functions (hoistable, clear intent).
- Use arrow functions for inline callbacks and short expressions.
- Keep functions small and focused — one responsibility per function.
- Use `async`/`await` over raw Promises.
- Always type function parameters and return types explicitly for exported functions.

---

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Files | `kebab-case.ts` | `transcript-cache.ts` |
| Variables / functions | `camelCase` | `extractVideoId` |
| Classes | `PascalCase` | `TranscriptFetcher` |
| Interfaces / Types | `PascalCase` (no `I` prefix) | `TranscriptSegment` |
| Constants | `UPPER_SNAKE_CASE` for true constants | `MAX_RESPONSE_SIZE` |
| Derived values | `camelCase` | `defaultTimeout` |
| Zod schemas | `PascalCase` + `Schema` suffix | `VideoIdSchema` |
| Test files | Same name + `.test.ts` suffix, co-located | `utils.test.ts` |
| Generics | Single uppercase letter or descriptive `PascalCase` | `T`, `TResult` |

---

## Import Ordering

Use ESM `import`/`export` syntax exclusively. No `require()`.

Imports must follow this order, separated by blank lines:

1. **Node built-ins** (e.g., `node:fs`, `node:path`)
2. **External packages** (e.g., `zod`, `@modelcontextprotocol/sdk`, `undici`)
3. **Local modules** (relative imports)

### Rules

- Use explicit `.js` extensions in ALL relative imports: `import { foo } from "./utils.js"`.
- Prefer named exports over default exports.
- Use `import type` for type-only imports (required by `isolatedModules: true`).

```typescript
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { extractVideoId } from "./utils.js";
import type { TranscriptSegment } from "./types.js";
```

---

## Error Handling

- Throw descriptive `Error` instances with clear messages.
- Use specific error classes for distinct failure modes when appropriate.
- MCP tool handlers must catch errors and return user-friendly error responses using `isError: true` in the tool result.
- Never swallow errors silently. Always log or propagate.
- Use early returns for guard clauses.
- **`console.log()` is FORBIDDEN** — for stdio MCP servers, stdout is the MCP transport. Use `console.error()` ONLY for any diagnostic logging.

```typescript
export function extractVideoId(input: string): string {
  const match = input.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  if (!match) {
    throw new Error(`Could not extract video ID from: ${input}`);
  }
  return match[1];
}
```

### MCP Tool Error Pattern

```typescript
async ({ url, lang, plain }) => {
  try {
    const result = await fetchTranscript(url, { lang, plain });
    return { content: [{ type: "text" as const, text: result }] };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text" as const, text: message }],
      isError: true,
    };
  }
}
```

### Error Sanitization

Error messages are sanitized before returning to MCP clients via a `USER_SAFE_PREFIXES` allowlist. Only errors with messages starting with a known-safe prefix are returned verbatim. All other errors produce a generic "An unexpected error occurred" message. This prevents leaking internal state, file paths, or environment variables.

---

## Patterns & Architecture

### Project Architecture

```
Entry (index.ts) → Server Factory (server.ts) → Core Logic (transcript.ts)
                                                  Shared Types (types.ts)
                                                  Utilities (utils.ts)
                                                  Caching (cache.ts) — planned, not yet implemented
```

- **`index.ts`**: Entry point. Creates the MCP server, sets up stdio transport, connects. Fatal errors call `process.exit(1)`.
- **`server.ts`**: Factory function `createServer()` that instantiates `McpServer` and registers tools. Contains `sanitizeErrorMessage()`.
- **`transcript.ts`**: Core transcript fetching logic with dual-strategy (InnerTube API primary, HTML scrape fallback).
- **`types.ts`**: Shared TypeScript interfaces (`TranscriptSegment`, `TranscriptResult`, `CaptionTrack`).
- **`utils.ts`**: Utility functions (video ID extraction, timestamp formatting, HTML entity decoding).
- **`cache.ts`** (planned — not yet implemented): Transcript caching for OS-appropriate directories.

### MCP Server Patterns

- **Always use `server.registerTool()`** — `server.tool()` is deprecated in v1.x.
- Pass `inputSchema` as a **plain object of Zod fields** — NOT `z.object({...})`. The SDK wraps it internally.
- Tool handlers are async and return `{ content: [{ type: "text" as const, text: "..." }] }`.
- Use `.describe()` on all Zod schema fields to document parameters for LLMs.
- Keep tool descriptions concise but informative (LLMs use them for tool selection).

```typescript
server.registerTool(
  "get_transcript",
  {
    description: "Fetch the transcript of a YouTube video",
    inputSchema: {
      url: z.string().max(2048).describe("YouTube video URL or video ID"),
      lang: z.string().optional().describe("Language code (e.g., 'en')"),
      plain: z.boolean().optional().describe("Return plain text without timestamps"),
    },
  },
  async ({ url, lang, plain }) => {
    // handler implementation
    return { content: [{ type: "text" as const, text: transcript }] };
  },
);
```

### Zod v4 Patterns

- Import: `import { z } from "zod"` (standard import path for Zod v4).
- **BREAKING in v4**: The `message` param is renamed to `error` in refinements/constraints: `z.string().min(5, { error: "Too short." })`.
- **BREAKING in v4**: Use `z.ZodType` (not `z.ZodTypeAny`) as the generic constraint in functions.
- Define schemas at module level for reuse (not inside functions).
- Use `PascalCase` + `Schema` suffix for schema naming.
- `z.object()` strips unknown keys by default in v4; use `.passthrough()` to preserve, `.strict()` to throw.
- Use `safeParse` at API/tool boundaries for graceful error handling; `parse` internally when data is trusted.
- Validate only at boundaries — do not re-validate trusted internal data.
- Export both the schema and its inferred type: `export type MyType = z.infer<typeof MySchema>`.

```typescript
// Module-level schema definition
const VideoUrlSchema = z.string().max(2048).describe("YouTube video URL or 11-character video ID");

// Type inference from schema
type VideoUrl = z.infer<typeof VideoUrlSchema>;

// safeParse at MCP tool boundary
const result = VideoUrlSchema.safeParse(input);
if (!result.success) {
  return { content: [{ type: "text" as const, text: "Invalid URL" }], isError: true };
}
```

### Transcript Fetching Strategy

The transcript fetcher uses a dual-strategy approach:

1. **Primary**: InnerTube ANDROID API (`POST /youtubei/v1/player`) — bypasses consent pages and age restrictions. 10s timeout, 0 redirects.
2. **Fallback**: HTML page scraping (`GET /watch?v=...`) — extracts `ytInitialPlayerResponse` from page source via brace-counting (no `eval()`).

Both strategies extract `captionTracks`, then fetch the transcript XML from `baseUrl`. Two XML formats are supported:
- **Classic**: `<text start="..." dur="...">...</text>`
- **SRV3**: `<p t="..." d="...">...</p>` (milliseconds)

Track selection: prefer non-ASR (manual) track; fallback to ASR. The `lang` param does exact `languageCode` match.

### Dependency Guidelines

- Use `undici` for HTTP requests — never the Node `http` module directly.
- Use `zod` for all runtime validation and schema definitions.
- Minimize dependencies — prefer standard library and Bun built-ins.
- Do NOT add `env-paths` (was removed from the project — it is NOT in `package.json`).

---

## Code Examples

### Tool Input Schema (current `get_transcript` tool)

```typescript
{
  url: z.string().max(2048).describe("YouTube video URL or 11-character video ID"),
  lang: z
    .string()
    .regex(/^[a-zA-Z]{2,3}(-[a-zA-Z]{2,8})?$/)
    .max(10)
    .optional()
    .describe("BCP 47 language tag (e.g. 'en', 'pt-BR')"),
  plain: z.boolean().optional().describe("If true, return plain text without timestamps"),
}
```

### HTTP Request with undici (security requirements)

```typescript
import { request } from "undici";

// Always: HTTPS only, maxRedirections: 0, response size cap (5MB)
const response = await request("https://www.youtube.com/youtubei/v1/player", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
  maxRedirections: 0,
  signal: AbortSignal.timeout(10_000),
});
```

### HTML Entity Decoding Order

Strip HTML tags first → decode `&lt;`, `&gt;`, `&quot;`, `&#39;`, `&apos;` → numeric `&#NNN;` → hex `&#xNNN;` → `&amp;` last (prevents double-decode). Replace `\n` with space.
