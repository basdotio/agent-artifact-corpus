# Bun Runtime and APIs

Detailed guidance for Bun's core capabilities, native APIs, and compatibility layers.

## Core Capabilities

### Runtime Execution

Execute JavaScript, TypeScript, and JSX files directly without configuration:

```bash
bun run index.ts
bun run app.jsx
bun index.js
```

Key features:

- **Native transpilation**: TypeScript and JSX work out of the box with no build step
- **Fast startup**: Processes start approximately 4x faster than Node.js
- **Path mapping**: Automatically respects `tsconfig.json` path mappings
- **Watch mode**: Use `bun --watch` for automatic reloading during development
- **Hot reloading**: Use `bun --hot` for hot module replacement

Environment variables:

- Bun automatically loads `.env` files
- Variants like `.env.local` or `.env.development` are supported without extra tooling

### Package Management

Install and manage dependencies with Bun's fast package manager:

```bash
bun install              # Install all dependencies from package.json
bun add <package>        # Add a package
bun add -d <package>     # Add as dev dependency
bun remove <package>     # Remove a package
bunx <package>           # Execute a package without installing
```

Highlights:

- Works with standard `package.json` files
- Significantly faster than npm, yarn, or pnpm
- Supports the `workspaces` field for monorepos

### Bundling

Bundle applications for production deployment:

```bash
bun build ./index.ts --outdir ./dist           # Basic bundling
bun build ./index.ts --outdir ./dist --minify  # Minified bundle
bun build --compile ./index.ts                 # Standalone executable
```

Key bundling features:

- **HTML support**: Import HTML files and Bun automatically bundles frontend assets
- **Cross-compilation**: Create executables for Linux, macOS, and Windows
- **Full-stack executables**: Bundle both frontend and backend into single binary
- **Sourcemaps**: Use `--sourcemap` for debugging production builds
- **Bytecode**: Use `--bytecode` for approximately 2x faster startup

Recommended production command:

```bash
bun build --compile --minify --sourcemap --bytecode ./index.ts
```

### Testing

Run tests with Bun's built-in test runner:

```bash
bun test                    # Run all tests
bun test <file>             # Run specific test file
bun test --watch            # Watch mode
```

Write tests using the `bun:test` module:

```typescript
import { test, expect, describe } from "bun:test"

describe("example", () => {
  test("addition", () => {
    expect(1 + 1).toBe(2)
  })
})
```

Notes:

- Jest-compatible assertions and syntax
- Approximately 100x faster than Jest in common scenarios
- Watch mode accelerates TDD loops

## Web Standards and Built-in APIs

Bun implements comprehensive Web-standard APIs:

- **Fetch API**: `fetch()` for HTTP requests
- **WebSocket**: Built-in server/client for real-time communication
- **Streams**: `ReadableStream`, `WritableStream`, and `TransformStream`
- **Crypto**: Web Crypto API for hashing and encryption
- **HTTP Server**: `Bun.serve()` for native servers

Example HTTP server:

```typescript
Bun.serve({
  port: 3000,
  fetch(req) {
    return new Response("Hello from Bun!")
  },
})
```

## Node.js Compatibility

Bun prioritizes Node.js API compatibility. Fully implemented modules include:

- `node:fs` for file system operations
- `node:path` for path utilities
- `node:http` / `node:https` for HTTP clients and servers
- `node:net` for TCP networking
- `node:stream` for stream utilities
- `node:crypto` for cryptographic functions
- `node:buffer` for buffer operations

Incomplete or experimental areas:

- Module registration hooks
- Certain inspector APIs
- Trace events

Consult compatibility references when using advanced Node.js features.
