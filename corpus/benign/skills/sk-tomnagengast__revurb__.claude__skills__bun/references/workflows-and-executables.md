# Bun Workflows and Executables

Guidance for common day-to-day workflows, scaffolding flows, and bundling applications into deployable artifacts.

## Common Workflows

### Starting a New Project

Initialize a new project with:

```bash
bun init
```

This scaffolds TypeScript configuration files, entry points, and installs type definitions.

For React projects:

```bash
bun init --react
```

Template options include Tailwind CSS and shadcn/ui presets for rapid UI setup.

### Running Scripts from package.json

Execute package.json scripts with:

```bash
bun run <script-name>
```

Benefits:

- Approximately 28x faster overhead compared to npm
- Works with existing Node.js-style scripts
- Compatible with TypeScript entry points

### Creating Standalone Executables

Compile applications into single binaries:

```bash
bun build --compile ./index.ts --outfile myapp
```

Targets:

- Linux x64/arm64
- Windows x64
- macOS (Intel and Apple Silicon)

Use flags like `--minify`, `--sourcemap`, and `--bytecode` for production optimizations.

### Working with Databases

Bun provides native database integrations:

**SQLite**

```typescript
import { Database } from "bun:sqlite"
const db = new Database("mydb.sqlite")
```

You can also import SQLite databases directly:

```typescript
import db from "./mydb.sqlite" with { type: "sqlite" }
```

**Redis**

- Built-in Redis client for caching and data storage
- Includes pub/sub support

**PostgreSQL/MySQL**

- Support for PostgreSQL and MySQL connections through `Bun.sql`
- Use prepared statements and connection pooling for performance

## Deployment-oriented Workflows

### Hot Reloading and Watch Mode

- `bun --watch entry.ts` for automatic restarts on file changes
- `bun --hot entry.ts` for hot module replacement during development

### Environment Configuration

- `.env` files load automatically
- Use `.env.local`, `.env.development`, etc., for environment-specific overrides

### Full-stack Apps

- Bun bundles frontend assets with HTML imports
- `bun build --compile` packages backend + frontend into a single binary

### Using bunx

Run one-off CLIs without local installation:

```bash
bunx <package> <args>
```

Helpful for scaffolding (e.g., `bunx create-next-app`) or running project-specific tools.
