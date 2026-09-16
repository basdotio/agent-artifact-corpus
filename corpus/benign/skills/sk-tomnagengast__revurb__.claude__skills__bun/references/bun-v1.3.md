# Bun 1.3

Bun 1.3 is our biggest release yet.

**curl**

```bash
curl -fsSL https://bun.sh/install | bash
```

**powershell**

```bash
powershell -c "irm bun.sh/install.ps1 | iex"
```

**docker**

```bash
docker run --rm --init --ulimit memlock=-1:-1 oven/bun
```

Bun 1.3 turns Bun into a batteries‑included full‑stack JavaScript runtime. We’ve added first-class support for frontend development with all the features you expect from modern JavaScript frontend tooling.

The highlights:

- Full‑stack dev server (with hot reloading, browser -> terminal console logs) built into `Bun.serve()`
- Builtin MySQL client, alongside our existing Postgres and SQLite clients
- Builtin Redis client
- Better routing, cookies, WebSockets, and HTTP ergonomics
- Isolated installs, catalogs, `minimumRelease`, and more for workspaces
- Many, many Node.js compatibility improvements

This is the start of a 1.3 series focused on making Bun the best way to build backend and frontend applications with JavaScript.

The web starts with HTML, and so does building frontend applications with Bun. You can now run HTML files directly with Bun.

```
Bun v1.3
ready in 6.62 ms
→ http://localhost:3000/
Routes:
/ -> ./index.html
/dashboard -> ./dashboard.html
Press h + Enter to show shortcuts
```

This isn't a static file server. This uses Bun's native JavaScript & CSS transpilers & bundler to bundle your React, CSS, JavaScript, and HTML files. Every day, we hear from developers switching from tools like Vite to Bun.

Bun's frontend dev server has builtin support for Hot Module Replacement, including React Fast Refresh. This lets you test your changes as you write them, without having to reload the page, and the [`import.meta.hot`](https://bun.com/docs/bundler/hmr) API lets framework authors implement hot reloading support in their frameworks on top of Bun's frontend dev server.

We implemented the filesystem watcher in native code using the fastest platform-specific APIs available (`kqueue` on macOS, `inotify` on Linux, and `ReadDirectoryChangesW` on Windows).

When it's time to build for production, run `bun build --production` to bundle your app.

```bash
bun build ./index.html --production --outdir=dist
```

To get started, run `bun init --react` to scaffold a new project:

```
? Select a project template - Press return to submit.
❯   Blank
    React
    Library

# Or use any of these variants:
```

```bash
bun init --react=tailwind
```

Bun is used for frontend development by companies like Midjourney.

Visit [the docs](https://bun.com/docs/bundler/html) to learn more!

One of the things that makes JavaScript great is that you can write both the frontend and backend in the same language.

In Bun v1.2, we introduced [HTML imports](https://bun.com/docs/bundler/html) and in Bun v1.3, we've expanded that to include hot reloading support and built-in routing.

```ts
import homepage from "./index.html"
import dashboard from "./dashboard.html"
import { serve } from "bun"

serve({
  development: {
    // Enable Hot Module Reloading
    hmr: true,

    // Echo console logs from the browser to the terminal
    console: true,
  },

  routes: {
    "/": homepage,
    "/dashboard": dashboard,
  },
})
```

#### CORS is simpler now

Today, many apps have to deal with Cross-Origin Resource Sharing (CORS) issues caused by running the backend and the frontend on different ports. In Bun, we make it easy to run your entire app in the same server process.

We've added support for parameterized and catch-all routes in Bun.serve(), so you can use the same API for both the frontend and backend.

```ts
import { serve, sql } from "bun"
import App from "./myReactSPA.html"

serve({
  port: 3000,
  routes: {
    "/*": App,

    "/api/users": {
      GET: async () => Response.json(await sql`SELECT * FROM users LIMIT 10`),

      POST: async (req) => {
        const { name, email } = await req.json()
        const [user] = await sql`
          INSERT INTO users ${sql({ name, email })}
          RETURNING *;
        `
        return Response.json(user)
      },
    },

    "/api/users/:id": async (req) => {
      const { id } = req.params
      const [user] = await sql`SELECT * FROM users WHERE id = ${id} LIMIT 1`
      if (!user) return new Response("User not found", { status: 404 })
      return Response.json(user)
    },

    "/healthcheck.json": Response.json({ status: "ok" }),
  },
})
```

Routes support dynamic path parameters like `:id`, different handlers for different HTTP methods, and serving static files or HTML imports alongside API routes. Everything runs in a single process. Just define your routes, and Bun matches them for you.

Bun's bundler can now bundle both frontend and backend applications in the same build. And we've expanded support for [single-file executables](https://bun.com/docs/bundler/executables) to include full-stack apps.

```bash
bun build --compile ./index.html --outfile myapp
```

You can use standalone executables with other Bun features like `Bun.serve()` routes, `Bun.sql`, `Bun.redis`, or any other Bun APIs to create portable self-contained applications that run anywhere.

Bun.SQL goes from builtin a PostgreSQL client to a unified MySQL/MariaDB, PostgreSQL, and SQLite API. One incredibly fast builtin database library supporting the most popular database adapters, with zero extra dependencies.

```ts
import { sql, SQL } from "bun"

// Connect to any database with the same API
const postgres = new SQL("postgres://localhost/mydb")
const mysql = new SQL("mysql://localhost/mydb")
const sqlite = new SQL("sqlite://data.db")

// Defaults to connection details from env vars
const seniorAge = 65
const seniorUsers = await sql`
  SELECT name, age FROM users
  WHERE age >= ${seniorAge}
`
```

While existing npm packages like `postgres` and `mysql2` packages perform great in Bun, offering a builtin API for such common database needs brings incredible performance gains, and reduces the number of dependencies your project needs to get started.

Bun 1.3 also adds a `sql.array` helper in `Bun.SQL` , making it easy to work with PostgreSQL array types. You can insert arrays into array columns and specify the PostgreSQL data type for proper casting.

```ts
import { sql } from "bun"

// Insert an array of text values
await sql`
  INSERT INTO users (name, roles)
  VALUES (${"Alice"}, ${sql.array(["admin", "user"], "TEXT")})
`

// Update with array values using sql object notation
await sql`
  UPDATE users
  SET ${sql({
    name: "Bob",
    roles: sql.array(["moderator", "user"], "TEXT"),
  })}
  WHERE id = ${userId}
`

// Works with JSON/JSONB arrays
const jsonData = await sql`
  SELECT ${sql.array([{ a: 1 }, { b: 2 }], "JSONB")} as data
`

// Supports various PostgreSQL types
await sql`SELECT ${sql.array([1, 2, 3], "INTEGER")} as numbers`
await sql`SELECT ${sql.array([true, false], "BOOLEAN")} as flags`
await sql`SELECT ${sql.array([new Date()], "TIMESTAMP")} as dates`
```

The `sql.array` helper supports all major PostgreSQL array types including `TEXT`, `INTEGER`, `BIGINT`, `BOOLEAN`, `JSON`, `JSONB`, `TIMESTAMP`, `UUID`, `INET`, and many more.

Bun's built-in PostgreSQL client has received comprehensive enhancements that make it more powerful and production-ready.

**Simple query protocol for multi-statement queries.** You can now use the simple query protocol by calling `.simple()` on your query:

```sql
await sql`
  SELECT 1;
  SELECT 2;
`.simple();
```

This is particularly useful for database migrations:

```sql
await sql`
  CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
  );

  CREATE INDEX idx_users_email ON users(email);

  INSERT INTO users (name, email)
  VALUES ('Admin', 'admin@example.com');
`.simple();
```

**Disable prepared statements with `prepare: false`.** Useful for working with PGBouncer in transaction mode or debugging query execution plans:

```ts
const sql = new SQL({
  prepare: false, // Disable prepared statements
})
```

**Connect via Unix domain sockets.** For applications running on the same machine as your PostgreSQL server, Unix domain sockets provide better performance:

```ts
await using sql = new SQL({
  path: "/tmp/.s.PGSQL.5432", // Full path to socket
  user: "postgres",
  password: "postgres",
  database: "mydb",
})
```

**Runtime configuration through connection options.** Set runtime parameters via the connection URL or options object:

```ts
// Via URL
await using db = new SQL("postgres://user:pass@localhost:5432/mydb?search_path=information_schema", { max: 1 })

// Via connection object
await using db = new SQL("postgres://user:pass@localhost:5432/mydb", {
  connection: {
    search_path: "information_schema",
    statement_timeout: "30s",
    application_name: "my_app",
  },
  max: 1,
})
```

**Dynamic column operations.** Building SQL queries dynamically is now easier with powerful helpers:

```sql
const user = { name: "Alice", email: "alice@example.com", age: 30 };

// Insert only specific columns
await sql`INSERT INTO users ${sql(user, "name", "email")}`;

// Update specific fields
const updates = { name: "Alice Smith", email: "alice.smith@example.com" };
await sql`UPDATE users SET ${sql(
  updates,
  "name",
  "email",
)} WHERE id = ${userId}`;

// WHERE IN with arrays
await sql`SELECT * FROM users WHERE id IN ${sql([1, 2, 3])}`;

// Extract field from array of objects
const users = [{ id: 1 }, { id: 2 }, { id: 3 }];
await sql`SELECT * FROM orders WHERE user_id IN ${sql(users, "id")}`;
```

**PostgreSQL array type support.** The `sql.array()` helper makes inserting and working with PostgreSQL arrays straightforward:

```sql
// Insert a text array
await sql`
  INSERT INTO users (name, roles)
  VALUES (${"Alice"}, ${sql.array(["admin", "user"], "TEXT")})
`;

// Supported types: INTEGER, REAL, TEXT, BLOB, BOOLEAN, TIMESTAMP, JSONB, UUID
await sql`SELECT ${sql.array([1, 2, 3], "INTEGER")} as numbers`;
```

**Proper null handling in array results.** Bun 1.3 now correctly preserves null values in array results:

```sql
const result = await sql`SELECT ARRAY[0, 1, 2, NULL]::integer[]`;
console.log(result[0].array); // [0, 1, 2, null]
```

Other improvements we've made to PostgreSQL:

- **Binary data types and custom OIDs** - Now handled correctly
- **Improved prepared statement lifecycle** - Better error messages for parameter mismatches
- **Pipelined query error handling** - No longer causes connection disconnection
- **TIME and TIMETZ column support** - Correctly decoded in binary protocol
- **All error classes exported** - `PostgresError`, `SQLiteError`, `MySQLError` for type-safe error handling
- **String arrays in WHERE IN clauses** - Now work correctly
- **Connection failure handling** - Throws catchable errors instead of crashing
- **Large batch inserts fixed** - No longer fail with "index out of bounds" errors
- **Process shutdown improvements** - No longer hangs with pending queries
- **NUMERIC value parsing** - Correctly handles values with many digits
- **`flush()` method** - Properly implemented
- **DATABASE_URL options precedence** - Handled correctly

**`Database.deserialize()` with configuration options.** When deserializing SQLite databases, you can now specify additional options:

```ts
import { Database } from "bun:sqlite"

const serialized = db.serialize()

const deserialized = Database.deserialize(serialized, {
  readonly: true, // Open in read-only mode
  strict: true, // Enable strict mode
  safeIntegers: true, // Return BigInt for large integers
})
```

**Column type introspection with `columnTypes` and `declaredTypes`.** Statement objects now expose type information about result columns:

```ts
import { Database } from "bun:sqlite"

const db = new Database(":memory:")
db.run("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
db.run("INSERT INTO users VALUES (1, 'Alice', 30)")

const stmt = db.query("SELECT * FROM users")

// Get declared types from the schema
console.log(stmt.declaredTypes) // ["INTEGER", "TEXT", "INTEGER"]

// Get actual types from values
console.log(stmt.columnTypes) // ["integer", "text", "integer"]

const row = stmt.get()
```

The `declaredTypes` array shows the types as defined in your `CREATE TABLE` statement, while `columnTypes` shows the actual SQLite storage class of the values returned.

![Redis Benchmark, showing more than 7.9X the performance of
ioredis](https://bun.com/images/bun-redis-perf-1.3.png)

Redis is a widely-used in-memory database, cache, and message broker and in Bun 1.3 introduces first-class support for Redis (and Valkey -- its BSD-licensed fork) and it's incredibly fast.

```ts
import { redis, RedisClient } from "bun"

// Connects to process.env.REDIS_URL or localhost:6379 if not set.
await redis.set("foo", "bar")
const value = await redis.get("foo")
console.log(value) // "bar"

console.log(await redis.ttl("foo")) // -1 (no expiration set)
```

All standard operations are supported, including hashes (`HSET`/`HGET`), lists (`LPUSH`/`LRANGE`) and sets -- totaling 66 commands. With automatic reconnects, command timeouts and message queuing, the Redis client handles high throughput and recovers from network failures.

Pub/Sub messaging is fully supported:

```ts
import { RedisClient } from "bun"

// You can create your own client instead of using `redis`.
const myRedis = new RedisClient("redis://localhost:6379")

// Subscribers can't publish, so duplicate the connection.
const publisher = await myRedis.duplicate()

await myRedis.subscribe("notifications", (message, channel) => {
  console.log("Received:", message)
})

await publisher.publish("notifications", "Hello from Bun!")
```

Bun's Redis client is significantly faster than `ioredis`, with the advantage increasing as batch size grows.

Support for clusters, streams and Lua scripting is in the works.

See the [Bun Redis documentation](https://bun.com/docs/api/redis) for more details and examples.

Bun 1.3 brings improvements to WebSocket support, making the implementation more compliant with web standards and adding powerful new capabilities.

**RFC 6455 Compliant Subprotocol Negotiation**

WebSocket clients now properly implement RFC 6455 compliant subprotocol negotiation. When you create a WebSocket connection, you can specify an array of subprotocols you'd like to use:

```ts
const ws = new WebSocket("ws://localhost:3000", ["chat", "superchat"])

ws.onopen = () => {
  console.log(`Connected with protocol: ${ws.protocol}`) // "chat"
}
```

The `ws.protocol` property is now properly populated with the server's selected subprotocol.

**Override Special WebSocket Headers**

Bun 1.3 now allows you to override special WebSocket headers when creating a connection:

```ts
const ws = new WebSocket("ws://localhost:8080", {
  headers: {
    Host: "custom-host.example.com",
    "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
  },
})
```

This is particularly useful using WebSocket clients that are proxied.

**Automatic `permessage-deflate` Compression**

Bun 1.3 now automatically negotiates and enables `permessage-deflate` compression when connecting to WebSocket servers that support it. This happens transparently—compression and decompression are handled automatically.

```ts
const ws = new WebSocket("wss://echo.websocket.org")

ws.onopen = () => {
  console.log("Extensions:", ws.extensions)
  // "permessage-deflate"
}
```

This feature is enabled by default and will be automatically negotiated with servers that support it. Bun's builtin WebSocket server supports permessage-deflate compression. For applications that send repetitive or structured data like JSON, `permessage-deflate` can reduce message sizes by 60-80% or more.

Bun's S3 client gets additional features:

- **`S3Client.list()`**: ListObjectsV2 support for listing objects in a bucket
- **Storage class support**: Specify `storageClass` option for S3 operations like `STANDARD_IA` or `GLACIER`

```ts
import { s3 } from "bun"

// List objects
const objects = await s3.list({ prefix: "uploads/" })
for (const obj of objects) {
  console.log(obj.key, obj.size)
}

// Upload with storage class
await s3.file("archive.zip").write(data, {
  storageClass: "GLACIER",
})

// Use virtual hosted-style URLs (bucket in hostname)
const s3VirtualHosted = new S3Client({
  virtualHostedStyle: true,
})
// Requests go to https://bucket-name.s3.region.amazonaws.com
// instead of https://s3.region.amazonaws.com/bucket-name
```

Bun's bundler adds programmatic compilation, cross-platform builds, and smarter minification in 1.3.

Create standalone executables programmatically with the `Bun.build()` API. This was previously only possible with the `bun build` CLI command.

```ts
import { build } from "bun"

await build({
  entrypoints: ["./app.ts"],
  compile: true,
  outfile: "myapp",
})
```

This produces a standalone executable without needing the CLI.

Bun now supports code signing for Windows and macOS executables:

- **Windows**: Authenticode signature stripping for post-build signing
- **macOS**: Code signing for standalone executables

```bash
bun build --compile ./app.ts --outfile myapp
```

```
codesign --sign "Developer ID" ./myapp
```

```bash
bun build --compile ./app.ts --outfile myapp.exe
```

```
signtool sign /f certificate.pfx myapp.exe
```

Build executables for different operating systems and architectures.

```bash
bun build --compile --target=linux-x64 ./app.ts --outfile myapp-linux
```

```bash
bun build --compile --target=darwin-arm64 ./app.ts --outfile myapp-macos
```

```bash
bun build --compile --target=windows-x64 ./app.ts --outfile myapp.exe
```

This lets you build for Windows, macOS, and Linux from any platform.

Set executable metadata on Windows builds with `--title`, `--publisher`, `--version`, `--description`, and `--copyright`.

```bash
bun build --compile --target=windows-x64 \\
  --title="My App" \\
  --publisher="My Company" \\
  --version="1.0.0" \\
  ./app.ts
```

Bun's minifier is even smarter in 1.3:

- Remove unused function and class names (override with `-keep-names`)
- Optimize `new Object()`, `new Array()`, `new Error()` expressions
- Minify `typeof undefined` checks
- Remove unused `Symbol.for()` calls
- Eliminate dead `try...catch...finally` blocks

```bash
bun build ./app.ts --minify
```

Configure JSX transformation in `Bun.build()` with a centralized `jsx` object.

```ts
await build({
  entrypoints: ["./app.tsx"],
  jsx: {
    factory: "h",
    fragment: "Fragment",
    importSource: "preact",
  },
})
```

- **`jsxSideEffects` option**: Preserve JSX with side effects during tree-shaking
- **`onEnd` hook**: Plugin hook that runs after build completion
- **Glob patterns in sideEffects**: `package.json` supports glob patterns like `"sideEffects": ["*.css"]`
- **Top-level await improvements**: Better handling of cyclic dependencies
- **`-compile-exec-argv`**: Embed runtime flags into executables

Bun's package manager gets more powerful with isolated installs, interactive updates, dependency catalogs, and security auditing.

Bun 1.3 makes it easier to work with monorepos.

Bun centralizes version management across monorepo packages with dependency `catalogs`. Define versions once in your root `package.json` and reference them in workspace packages.

package.json

```
{
  "name": "monorepo",
  "workspaces": ["packages/*"],
  "catalog": {
    "react": "^18.0.0",
    "typescript": "^5.0.0"
  }
}
```

Reference catalog versions in workspace packages:

package.json

```
{
  "name": "@company/ui",
  "dependencies": {
    "react": "catalog:"
  }
}
```

Now all packages use the same version of React. Update the catalog once to update everywhere. This is inspired by [pnpm's catalog feature](https://pnpm.io/catalogs).

Bun 1.3 introduces [isolated installs](https://bun.com/docs/install/isolated). This prevents packages from accessing dependencies they don't declare in their `package.json`, addressing the #1 issue users faced with Bun in large monorepos. Unlike hoisted installs (npm/Yarn's flat structure where all dependencies live in a single `node_modules`), isolated installs ensure each package only has access to its own declared dependencies.

And if you use `"workspaces"` in your `package.json`, we're making it the default behavior.

To opt out do one of the folowing:

```bash
bun install --linker=hoisted
```

bunfig.toml

```
[install]
linker = "hoisted"
```

In Bun 1.3, we’ve expanded automatic lockfile conversion to support migrating from yarn (`yarn.lock`) and pnpm (`pnpm-lock.yaml`) to Bun’s lockfile. Your dependency tree stays the same, and Bun preserves the resolved versions from your original lockfile. You can commit the new lockfile to your repository without any surprises. This makes it easy to try `bun install` at work without asking your team to upgrade to Bun.

Bun 1.3 introduces the Security Scanner API, enabling you to scan packages for vulnerabilities before installation. Security scanners analyze packages during `bun install`, `bun add`, and other package operations to detect known CVEs, malicious packages, and license compliance issues. We're excited to be working with [Socket](https://socket.dev/) to launch with their [official security scanner: `@socketsecurity/bun-security-scanner`](https://www.npmjs.com/package/@socketsecurity/bun-security-scanner).

_“We’re excited to see the Bun team moving so quickly to protect developers at the package manager level. By opening up the Security Scanner API, they’ve made it possible for tools like Socket to deliver real-time threat detection directly in the install process. It’s a great step forward for making open source development safer by default.”_

— Ahmad Nassri, CTO of Socket

**Configure a security scanner in `bunfig.toml`:**

Many security companies publish Bun security scanners as npm packages.

```bash
bun add -d @acme/bun-security-scanner # This is an example
```

Next, configure in your `bunfig.toml`:

bunfig.toml

```
[install.security]
scanner = "@acme/bun-security-scanner"
```

Now, Bun will scan all packages before installation, display security warnings, and cancel installation if critical advisories are found.

**Scanners report issues at two severity levels:**

- `fatal` : Installation stops immediately, exits with non-zero code
- `warn` — In interactive terminals, prompts to continue; in CI, exits immediately

Enterprise scanners may support authentication through environment variables:

```ts
export SECURITY_API_KEY="your-api-key"
```

```bash
bun install # Scanner uses credentials automatically
```

For teams with specific security requirements, you can build custom security scanners. See the [official template](https://github.com/oven-sh/security-scanner-template) for a complete example with tests and CI setup.

In Bun 1.3, you can protect yourself against supply chain attacks by requiring packages to be published for a minimum time before installation.

bunfig.toml

```
[install]
minimumReleaseAge = 604800 # 7 days in seconds
```

This prevents installing packages that were just published, giving the community time to identify malicious packages before they reach your codebase.

Control which platform-specific `optionalDependencies` install with `--cpu` and `--os` flags:

```bash
bun install --os linux --cpu arm64
```

```bash
bun install --os darwin --os linux --cpu x64
```

```bash
bun install --os '*' --cpu '*'
```

Control workspace package linking behavior with `linkWorkspacePackages`:

bunfig.toml

```
[install]
linkWorkspacePackages = false
```

When `false`, Bun installs workspace dependencies from the registry instead of linking locally—useful in CI where pre-built packages are faster than building from source.

Bun 1.3 adds several commands that make package management easier:

**`bun why`** explains why a package is installed:

```
[0.05ms] ".env"
tailwindcss@3.4.17
  └─ peer @tailwindcss/typography@0.5.16 (requires >=3.0.0 || insiders || >=4.0.0-alpha.20 || >=4.0.0-beta.1)

tailwindcss@3.3.2
  └─ tw-to-css@0.0.12 (requires 3.3.2)
```

It shows you the full dependency chain: _which_ of your dependencies depends on tailwindcss, and _why_ it's in your `node_modules`. This is especially useful when you're trying to figure out why a package you didn't explicitly install is showing up in your project.

**`bun update --interactive`** lets you choose which dependencies to update:

```
  dependencies                             Current        Target   Latest
  ❯ □ @tailwindcss/typography              0.5.16         0.5.19   0.5.19
    □ lucide-react                         0.473.0        0.473.0  0.544.0
    □ prettier                             2.8.8          2.8.8    3.6.2
    □ prettier-plugin-tailwindcss          0.2.8          0.2.8    0.6.14
    □ react                                18.3.1         18.3.1   19.1.1
    □ react-dom                            18.3.1         18.3.1   19.1.1
    □ satori                               0.12.2         0.12.2   0.18.3
    □ semver                               7.7.0          7.7.2    7.7.2
    □ shiki                                0.10.1         0.10.1   3.13.0
    □ tailwindcss                          3.4.17         3.4.18   4.1.14
    □ zod                                  3.24.1         3.25.76  4.1.11
```

Instead of updating everything at once, you can scroll through your dependencies and select which ones to update. This gives you control over breaking changes. You can update your test framework separately from your production dependencies, or update one major version at a time.

In monorepos, you can scope updates to specific workspaces with the `--filter` flag:

```
# Update dependencies only in the @myapp/frontend workspace
```

```bash
bun update -i --filter @myapp/frontend
```

```

# Update multiple workspaces
```

```bash
bun update -i --filter @myapp/frontend --filter @myapp/backend
```

You can also run commands recursively across all workspace packages:

```bash
bun outdated --recursive    # Check all workspaces
```

```
┌─────────────────────────────┬─────────┬─────────┬─────────┬───────────┐
│ Package                     │ Current │ Update  │ Latest  │ Workspace │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ @tailwindcss/typography     │ 0.5.16  │ 0.5.19  │ 0.5.19  │           │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ lucide-react                │ 0.473.0 │ 0.473.0 │ 0.544.0 │           │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ prettier                    │ 2.8.8   │ 2.8.8   │ 3.6.2   │ catalog:  │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ prettier-plugin-tailwindcss │ 0.2.8   │ 0.2.8   │ 0.6.14  │           │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ react                       │ 18.3.1  │ 18.3.1  │ 19.1.1  │ my-app    │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ react-dom                   │ 18.3.1  │ 18.3.1  │ 19.1.1  │ my-app    │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ satori                      │ 0.12.2  │ 0.12.2  │ 0.18.3  │           │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ semver                      │ 7.7.0   │ 7.7.2   │ 7.7.2   │           │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ shiki                       │ 0.10.1  │ 0.10.1  │ 3.13.0  │           │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ tailwindcss                 │ 3.4.17  │ 3.4.18  │ 4.1.14  │           │
├─────────────────────────────┼─────────┼─────────┼─────────┼───────────┤
│ zod                         │ 3.24.1  │ 3.25.76 │ 4.1.11  │           │
└─────────────────────────────┴─────────┴─────────┴─────────┴───────────┘
```

The **Workspace** column shows which workspace package each dependency belongs to, making it easy to track dependencies across your monorepo. When using `bun update -i`, this column helps you understand the scope of your updates.

Both `bun outdated` and `bun update -i` now fully support catalog dependencies defined in your root `package.json`, so you can see and update catalog versions just like regular dependencies.

```bash
bun update -i --recursive  # Update all workspaces
```

`bun info` lets you view package metadata

```bash
bun info react
react@19.2.0 | MIT | deps: 0 | versions: 2536
React is a JavaScript library for building user interfaces.
https://react.dev/
keywords: react

dist
 .tarball: https://registry.npmjs.org/react/-/react-19.2.0.tgz
 .shasum: d33dd1721698f4376ae57a54098cb47fc75d93a5
 .integrity: sha512-tmbWg6W31tQLeB5cdIBOicJDJRR2KzXsV7uSK9iNfLWQ5bIZfxuPEHp7M8wiHyHnn0DD1i7w3Zmin0FtkrwoCQ==
 .unpackedSize: 171.60 KB

dist-tags:
beta: 19.0.0-beta-26f2496093-20240514
rc: 19.0.0-rc.1
latest: 19.2.0
next: 19.3.0-canary-4fdf7cf2-20251003
canary: 19.3.0-canary-4fdf7cf2-20251003
experimental: 0.0.0-experimental-4fdf7cf2-20251003

maintainers:
- fb <opensource+npm@fb.com>
- react-bot <react-core@meta.com>

Published: 2025-10-01T21:38:32.757Z
```

This shows package versions, dependencies, dist-tags, and more. This is useful for quickly checking what's available before installing.

`bun install --analyze` lets you scans your code for imports that aren't in `package.json` and installs them. This is useful when you've added imports but forgot to install the packages.

`bun audit` scans dependencies for known vulnerabilities using the same database as `npm audit`

```bash
bun audit --severity=high
```

```bash
bun audit --json > report.json
```

- **`bun pm version`**: Bump package.json versions with pre/post version scripts
- **`bun pm pkg`**: Edit package.json with `get`, `set`, `delete`, and `fix` commands
- **Platform filtering**: Use `--cpu` and `--os` flags to filter optional dependencies by platform
- **Quiet pack mode**: Use `bun pm pack --quiet` for scripting
- **Custom pack output**: Use `bun pm pack --filename <path>` to specify the output tarball name and location
- `bun install --lockfile-only` has been optimized to only fetch package manifests, not tarballs

```
# Create tarball with custom name and location
bun pm pack --filename ./dist/my-package-1.0.0.tgz
```

Bun's test runner gets more powerful with VS Code integration, concurrent tests, type testing, and better output.

We've worked closely with WebKit to add support for richer async stack traces in JavaScriptCore. Previously, errors in async functions failed to preserve the async call trace. For example:

```ts
async function foo() {
  return await bar()
}

async function bar() {
  return await baz()
}

async function baz() {
  await 1 // ensure it's a real async function
  throw new Error("oops")
}

try {
  await foo()
} catch (e) {
  console.log(e)
}
```

In Bun 1.3, this now outputs:

```ts
❯ bun async.js
 6 |   return await baz();
 7 | }
 8 |
 9 | async function baz() {
10 |   await 1; // ensure it's a real async function
11 |   throw new Error("oops");
             ^
error: oops
      at baz (async.js:11:9)
      at async bar (async.js:6:16)
      at async foo (async.js:2:16)
```

This feature also benefits Safari and other JavaScriptCore-based runtimes.

Bun's test runner now integrates with VS Code's Test Explorer UI. Tests appear in the sidebar, and you can run, debug, and view results without leaving your editor. Run individual tests with one click and see inline error messages directly in your code.

Install the [Bun for Visual Studio Code extension](https://marketplace.visualstudio.com/items?itemName=oven.bun-vscode) to get started.

`bun test` now supports running multiple asynchronous tests concurrently within the same file, using `test.concurrent`. This can significantly speed up test suites that are I/O-bound, such as those making network requests or interacting with a database.

```ts
import { test } from "bun:test"

test.concurrent("fetch user 1", async () => {
  const res = await fetch("https://api.example.com/users/1")
  expect(res.status).toBe(200)
})

describe.concurrent("server tests", () => {
  test("sends a request to server 1", async () => {
    const response = await fetch("https://example.com/server-1")
    expect(response.status).toBe(200)
  })
})

test("serial test", () => {
  expect(1 + 1).toBe(2)
})
```

By default, a maximum of 20 tests will run concurrently. You can change this with the `--max-concurrency` flag.

To make specific files run concurrently, you can use the `concurrentTestGlob` option in `bunfig.toml`.

bunfig.toml

```
[test]
concurrentTestGlob = "**/integration/**/*.test.ts"

# You can also provide an array of patterns.
# concurrentTestGlob = [
#   "**/integration/**/*.test.ts",
#   "**/*-concurrent.test.ts",
# ]
```

When using `concurrentTestGlob`, all tests in the files matching the glob will run concurrently.

When you use `describe.concurrent`, `--concurrent`, or `concurrentTestGlob`, you might still want to leave some tests sequential. You can do this by using the new `test.serial` modifier.

```ts
import { test, expect } from "bun:test"

describe.concurrent("concurrent tests", () => {
  test("async test", async () => {
    await fetch("<https://example.com/server-1>")
    expect(1 + 1).toBe(2)
  })

  test("async test #2", async () => {
    await fetch("<https://example.com/server-2>")
    expect(1 + 1).toBe(2)
  })

  test.serial("serial test", () => {
    expect(1 + 1).toBe(2)
  })
})
```

Concurrent tests sometimes expose unexpected test dependencies on execution order or shared state. You can use the `--randomize` flag to run tests in a random order to make it easier to find these dependencies.

When you use `--randomize`, Bun will output the seed for that specific run. To reproduce the exact same test order for debugging, you can use the `--seed` flag with the printed value. Using `--seed` automatically enables randomization.

```
# Run tests in a random order
```

```

# The seed is printed in the test summary
# ... test output ...
#  --seed=12345
# 2 pass
# 8 fail
# Ran 10 tests across 2 files. [50.00ms]

# Reproduce the same run order using the seed
```

You can now chain qualifiers like `.failing`, `.skip`, `.only`, and `.each` on `test` and `describe`. Previously, this would result in an error.

```ts
import { test, expect } from "bun:test"

// This test is expected to fail, and it runs for each item in the array.
test.failing.each([1, 2, 3])("each %i", (i) => {
  if (i > 0) {
    throw new Error("This test is expected to fail.")
  }
})
```

The test runner's execution logic has been rewritten for improved reliability and predictability. This resolves a large number of issues where `describe` blocks and hooks (`beforeAll`, `afterAll`, etc.) would execute in a slightly unexpected order. The new behavior is more consistent with test runners like Vitest.

- `expect.assertions()` and `expect.hasAssertions()` are not supported when using `test.concurrent` or `describe.concurrent`.
- `toMatchSnapshot()` is not supported, but `toMatchInlineSnapshot()` is.
- `beforeAll` and `afterAll` hooks are not executed concurrently.

To prevent accidental commits, `bun test` will now throw an error in CI environments in two new scenarios:

- If a test file contains `test.only()`.
- If a snapshot test (`.toMatchSnapshot()` or `.toMatchInlineSnapshot()`) tries to create a new snapshot without the `--update-snapshots` flag.

This helps prevent temporarily focused tests or unintentional snapshot changes from being merged. To disable this behavior, you can set the environment variable `CI=false`.

Use `test.failing()` to mark tests that are expected to fail. This is useful for documenting known bugs or practicing Test-Driven Development (TDD) where you write the test before the implementation:

```ts
import { test, expect } from "bun:test"

test.failing("known bug: division by zero", () => {
  expect(divide(10, 0)).toBe(Infinity)
  // This test currently fails but is expected to fail
  // Remove .failing when the bug is fixed
})

test.failing("TDD: feature not yet implemented", () => {
  expect(newFeature()).toBe("working")
  // Remove .failing once you implement newFeature()
})
```

When a `test.failing()` test passes, Bun reports it as a failure (since you expected it to fail). This helps you remember to remove the `.failing` modifier once you fix the bug or implement the feature.

Test TypeScript types alongside unit tests using `expectTypeOf()`. These assertions can be checked by the TypeScript compiler:

```ts
import { expectTypeOf, test } from "bun:test"

test("types are correct", () => {
  expectTypeOf<string>().toEqualTypeOf<string>()
  expectTypeOf({ foo: 1 }).toHaveProperty("foo")
  expectTypeOf<Promise<number>>().resolves.toBeNumber()
})
```

Verify type tests by running `bunx tsc --noEmit`.

Bun 1.3 adds new matchers for testing return values:

- `toHaveReturnedWith(value)`: Check if a mock returned a specific value
- `toHaveLastReturnedWith(value)`: Check the last return value
- `toHaveNthReturnedWith(n, value)`: Check the nth return value

```ts
import { test, expect, mock } from "bun:test"

test("mock return values", () => {
  const fn = mock(() => 42)
  fn()
  fn()

  expect(fn).toHaveReturnedWith(42)
  expect(fn).toHaveLastReturnedWith(42)
  expect(fn).toHaveNthReturnedWith(1, 42)
})
```

Inline snapshots now support automatic indentation detection and preservation, matching Jest's behavior. When you use `.toMatchInlineSnapshot()`, Bun automatically formats the snapshot to match your code's indentation level:

```ts
import { test, expect } from "bun:test"

test("formats user data", () => {
  const user = { name: "Alice", age: 30, email: "alice@example.com" }

  expect(user).toMatchInlineSnapshot(`
    {
      "name": "Alice",
      "age": 30,
      "email": "alice@example.com",
    }
  `)
})
```

The snapshot content is automatically indented to align with your test code, making snapshots more readable and easier to maintain.

- **`mock.clearAllMocks()`**: Clear all mocks at once
- **Coverage filtering**: Use `test.coveragePathIgnorePatterns` to exclude paths from coverage
- **Variable substitution**: Use `$variable` and `$object.property` in `test.each` titles
- **Improved diffs** Better visualization with whitespace highlighting
- **Stricter CI mode**: Errors on `test.only()` and new snapshots without `--update-snapshots`
- **Compact AI output**: Condensed output for AI coding assistants

Bun 1.3 expands support for modern web standards and APIs, making it easier to build applications that work across different JavaScript environments.

In Bun 1.3, you can parse and stringify YAML directly with `Bun.YAML`.

```ts
import { YAML } from "bun"

const obj = YAML.parse("key: value")
console.log(obj) // { key: "value" }

const yaml = YAML.stringify({ key: "value" }, 0, 2)
console.log(yaml) // "key: value"
```

You can also import YAML files directly:

```ts
import config from "./config.yaml"
console.log(config)
```

The parser powering YAML in Bun is written from scratch and currently passes 90% of the official [yaml-test-suite](https://github.com/yaml/yaml-test-suite). It supports all features except for literal chomping (`|+` and `|-`) and cyclic references. In the near future we will get it to 100% passing.

Most production web applications read and write cookies. Usually in server-side JavaScript, you must choose either a single-purpose cookie parsing library like `tough-cookie`, or adopting a web framework like Express or Elysia. Cookie parsing & serialization is a well-understood problem.

Bun 1.3 simplifies this. Bun's HTTP server now includes built-in cookie support with a powerful, Map-like API. The new `request.cookies` API automatically detects when you make changes to cookies and intelligently adds the appropriate `Set-Cookie` headers to your response.

```ts
import { serve, randomUUIDv7 } from "bun"

serve({
  routes: {
    "/api/users/sign-in": (request) => {
      request.cookies.set("sessionId", randomUUIDv7(), {
        httpOnly: true,
        sameSite: "strict",
      })
      return new Response("Signed in")
    },
    "/api/users/sign-out": (request) => {
      request.cookies.delete("sessionId")
      return new Response("Signed out")
    },
  },
})
```

When you call `request.cookies.set()`, Bun adds the appropriate `Set-Cookie` header to your response. When you call `request.cookies.delete()`, it generates the correct header to tell the browser to remove that cookie.

One key design principle is that this API has zero performance overhead when you're not using cookies. The `Cookie` header from incoming requests isn't parsed until the moment you access `request.cookies`.

You have full control over all standard cookie attributes:

```
request.cookies.set("preferences", JSON.stringify(userPrefs), {
  httpOnly: false, // Allow JavaScript access
  secure: true, // Only send over HTTPS
  sameSite: "lax", // Allow some cross-site requests
  maxAge: 60 * 60 * 24 * 365, // 1 year in seconds
  path: "/", // Available on all paths
  domain: ".example.com", // Available on all subdomains
});
```

You can also read and write cookies outside of Bun.serve() using the `Bun.Cookie` and `Bun.CookieMap` classes.

```ts
const cookie = new Bun.Cookie("sessionId", "123")
cookie.value = "456"
console.log(cookie.value) // "456"
console.log(cookie.serialize()) // "sessionId=456; Path=/; SameSite=lax"

const cookieMap = new Bun.CookieMap("sessionId=321; token=aaaa")
console.log(cookieMap.get("sessionId")) // 321
console.log(cookieMap.get("token")) // aaaa
cookieMap.set("user1", "hello")
cookieMap.set("user2", "world")
console.log(cookieMap.toSetCookieHeaders())
// => [ "user1=hello; Path=/; SameSite=Lax", "user2=world; Path=/; SameSite=Lax" ]
```

Consume `ReadableStream`s directly with helpful `.text()`, `.json()`, `.bytes()`, and `.blob()` methods.

```ts
const stream = new ReadableStream({
  start(controller) {
    controller.enqueue(new TextEncoder().encode("Hello"))
    controller.close()
  },
})

const text = await stream.text() // "Hello"
```

This matches the upcoming Web Streams standard and makes it easier to work with streams.

- **Compression**: Client-side `permessage-deflate` support for reduced bandwidth
- **Subprotocol negotiation**: RFC 6455 compliant protocol negotiation
- **Header overrides**: Override `Host`, `Sec-WebSocket-Key`, and other headers

```ts
const ws = new WebSocket("wss://example.com", {
  headers: {
    "User-Agent": "MyApp/1.0",
  },
  perMessageDeflate: true,
})
```

Compile and instantiate WebAssembly modules from streams with `WebAssembly.compileStreaming()` and `instantiateStreaming()`.

```ts
const response = fetch("module.wasm")
const module = await WebAssembly.compileStreaming(response)
const instance = await WebAssembly.instantiate(module)
```

This is more efficient than loading the entire WASM file into memory first.

Bun 1.3 adds full support for Zstandard (zstd) compression, including automatic decompression of HTTP responses and manual compression APIs.

**Automatic decompression in `fetch()`.** When a server sends a response with `Content-Encoding: zstd`, Bun automatically decompresses it:

```ts
// Server sends zstd-compressed response
const response = await fetch("https://api.example.com/data")
const data = await response.json() // Automatically decompressed
```

**Manual compression and decompression.** Use Bun's APIs or the `node:zlib` module for direct compression:

```ts
import { zstdCompressSync, zstdDecompressSync } from "node:zlib"

const compressed = zstdCompressSync("Hello, world!")
const decompressed = zstdDecompressSync(compressed)
console.log(decompressed.toString()) // "Hello, world!"

// Or use Bun's async APIs
import { zstdCompress, zstdDecompress } from "bun"
const compressed2 = await zstdCompress("Hello, world!")
const decompressed2 = await zstdDecompress(compressed2)
```

Bun 1.3 implements `DisposableStack` and `AsyncDisposableStack` from the TC39 Explicit Resource Management proposal. These stack-based containers help manage disposable resources that use the `using` and `await using` declarations.

```ts
const stack = new DisposableStack()

stack.use({
  [Symbol.dispose]() {
    console.log("Cleanup!")
  },
})

// Dispose all resources at once
stack.dispose() // "Cleanup!"
```

`DisposableStack` aggregates multiple disposable resources into a single container, ensuring all resources are properly cleaned up when the stack is disposed. `AsyncDisposableStack` provides the same functionality for asynchronous cleanup with `Symbol.asyncDispose`. If any resource throws during disposal, the error is collected and rethrown after all resources are disposed.

Bun 1.3 introduces the `Bun.secrets` API, allowing you to use your OS's native credential storage:

```ts
import { secrets } from "bun"

await secrets.set({
  service: "my-app",
  name: "api-key",
  value: "secret-value",
})
const key: string | null = await secrets.get({
  service: "my-app",
  name: "api-key",
})
```

Secrets are stored in Keychain on macOS, libsecret on Linux, and Windows Credential Manager on Windows. They're encrypted at rest and separate from environment variables.

Bun 1.3 adds `Bun.CSRF` for cross-site request forgery protection by letting you generate and verify XSRF/CSRF tokens.

```ts
import { CSRF } from "bun"

const secret = "your-secret-key"
const token = CSRF.generate({ secret, encoding: "hex", expiresIn: 60 * 1000 })
const isValid = CSRF.verify(token, { secret })
```

Bun 1.3 includes major performance improvements to Node.js crypto APIs:

- **DiffieHellman**: ~400x faster
- **Cipheriv/Decipheriv**: ~400x faster
- **scrypt**: ~6x faster

These improvements make cryptographic operations significantly faster for password hashing, encryption, and key derivation.

```
clk: ~4.74 GHz
cpu: AMD Ryzen AI 9 HX 370 w/ Radeon 890M
runtime: bun 1.3.0 (x64-linux)

benchmark                            avg (min … max)
----------------------------------------------------
createDiffieHellman - 512             103.90 ms/iter
                              (39.30 ms … 237.74 ms)

Cipheriv and Decipheriv - aes-256-gcm   2.25 µs/iter
                                 (1.90 µs … 2.63 µs)

scrypt - N=16384, p=1, r=1             36.94 ms/iter
                               (35.98 ms … 38.04 ms)
```

```
clk: ~4.86 GHz
cpu: AMD Ryzen AI 9 HX 370 w/ Radeon 890M
runtime: bun 1.2.0 (x64-linux)

benchmark                            avg (min … max)
----------------------------------------------------
createDiffieHellman - 512               41.15 s/iter
                              (366.85 ms … 136.49 s)

Cipheriv and Decipheriv - aes-256-gcm 912.65 µs/iter
                               (804.29 µs … 6.12 ms)

scrypt - N=16384, p=1, r=1            224.92 ms/iter
                             (222.30 ms … 232.52 ms)
```

Other crypto improvements:

- **X25519 curve**: Elliptic curve support in `crypto.generateKeyPair()`
- **HKDF**: `crypto.hkdf()` and `crypto.hkdfSync()` for key derivation
- **Prime number functions**: `crypto.generatePrime()`, `crypto.checkPrime()` and sync variants
- **System CA certificates**: `--use-system-ca` flag to use OS trusted certificates
- **`crypto.KeyObject` hierarchy**: Full implementation with `structuredClone` support

Bun now runs 800 more tests from the Node.js test suite on every commit of Bun. We're continuing making progress toward full Node.js compatibility. In Bun 1.3, we've added support for the VM module, `node:test`, performance monitoring, and more.

We made Bun's `worker_threads` implementation more compatible with Node.js. You can use the `getEnvironmentData` and `setEnvironmentData` methods to share data between parent threads and workers with the `environmentData` API:

```ts
// Share data between workers with environmentData
import { Worker, getEnvironmentData, setEnvironmentData } from "node:worker_threads"

// Set data in parent thread
setEnvironmentData("config", { timeout: 1000 })

// Create a worker
const worker = new Worker("./worker.js")

// In worker.js:
import { getEnvironmentData } from "node:worker_threads"
const config = getEnvironmentData("config")
console.log(config.timeout) // 1000
```

```ts
import { Worker, setEnvironmentData, getEnvironmentData } from "worker_threads"

setEnvironmentData("config", { debug: true })

const worker = new Worker("./worker.js")

// In worker.js
import { getEnvironmentData } from "worker_threads"
const config = getEnvironmentData("config")
console.log(config.debug) // true
```

Bun now includes initial support for the `node:test` module, leveraging `bun:test` under the hood to provide a unified testing experience. This implementation allows you to run Node.js tests with the same performance benefits of Bun's native test runner.

```ts
import { test, describe } from "node:test"
import assert from "node:assert"

describe("Math", () => {
  test("addition", () => {
    assert.strictEqual(1 + 1, 2)
  })
})
```

The `node:vm` module gets major improvements in Bun 1.3:

- **`vm.SourceTextModule`**: Evaluate ECMAScript modules
- **`vm.SyntheticModule`**: Create synthetic modules
- **`vm.compileFunction`**: Compile JavaScript into functions
- **`vm.Script` bytecode caching**: Use `cachedData` for faster compilation
- **`vm.constants.DONT_CONTEXTIFY`**: Support for non-contextified values

```ts
import vm from "node:vm"

const script = new vm.Script('console.log("Hello from VM")')
script.runInThisContext()
```

These APIs enable advanced use cases like code evaluation sandboxes, plugin systems, and custom module loaders.

Bun now supports Node.js's [`require.extensions`](https://nodejs.org/api/modules.html#requireextensions) API, allowing packages that rely on custom file loaders to work in Bun.

```ts
require.extensions[".txt"] = (module, filename) => {
  const content = require("fs").readFileSync(filename, "utf8")
  module.exports = content
}

const text = require("./file.txt")
console.log(text) // File contents as string
```

This is a legacy Node.js API that enables loading non-JavaScript files with `require()`. While we don't recommend using it in new code (use import attributes or loaders instead), supporting it ensures compatibility with existing packages in the npm ecosystem.

Use the `--no-addons` flag to disable Node.js native addons at runtime:

When disabled, attempts to load native addons will throw an `ERR_DLOPEN_DISABLED` error. This is useful for security-sensitive environments where you want to ensure no native code can be loaded.

Bun also supports the `"node-addons"` export condition in `package.json` for conditional package resolution:

package.json

```
{
  "exports": {
    ".": {
      "node-addons": "./native.node",
      "default": "./fallback.js"
    }
  }
}
```

#### Core Module Improvements

**`node:fs`**:

- `fs.glob()`, `fs.globSync()`, and `fs.promises.glob()` with array patterns and exclude options
- Support for embedded files in Single-File Executables
- `fs.Stats` constructor matches Node.js behavior (undefined values instead of zeros)
- `fs.fstatSync` bigint option support
- EINTR handling in `fs.writeFile` and `fs.readFile` for interrupted system calls
- `fs.watchFile` emits 'stop' event and ignores access time changes
- `fs.mkdirSync` Windows NT prefix support
- `fs.Dir` validation improvements
- `process.binding('fs')` implementation

**`node:http` and `node:http2`**:

- `http.Server.closeIdleConnections()` for graceful shutdown
- `http.ClientRequest#flushHeaders` correctly sends request body
- Array-based `Set-Cookie` header format in `writeHead()`
- CONNECT method support for HTTP proxies
- Numeric header names support
- WebSocket, CloseEvent, and MessageEvent exports from `node:http`
- HTTP/2 stream management, response handling, and window size configuration improvements
- `maxSendHeaderBlockLength` option
- `setNextStreamID` support
- `remoteSettings` event for default settings
- Type validation for client request options
- `util.promisify(http2.connect)` support

**`node:net`**:

- `net.BlockList` class for IP address blocking
- `net.SocketAddress` class with `parse()` method
- `AbortSignal` support in `net.createServer()` and `server.listen()`
- `resetAndDestroy()` method
- `server.maxConnections` support
- Port as string support in `listen()`
- Improved validation for `localAddress`, `localPort`, `keepAlive` options
- Major rework adding 43 new passing tests
- Handle leak and connection management fixes
- `socket.write()` accepts Uint8Array

**`node:crypto`**:

- X25519 curve support in `crypto.generateKeyPair()`
- Native C++ implementation of Sign and Verify classes (34x faster)
- Native C++ implementation of Hash and Hmac classes
- `hkdf` and `hkdfSync` for key derivation
- `generatePrime`, `generatePrimeSync`, `checkPrime`, `checkPrimeSync`
- Native implementations: Cipheriv, Decipheriv, DiffieHellman, DiffieHellmanGroup, ECDH, randomFill(Sync), randomBytes
- Full KeyObject class hierarchy with structuredClone support
- Lowercase algorithm names support
- `crypto.verify()` defaults to SHA256 for RSA keys
- `crypto.randomInt` callback support

**`node:buffer`**:

- Resizable and growable shared ArrayBuffers
- `--zero-fill-buffers` flag support
- `Buffer.prototype.toLocaleString` alias
- `Buffer.prototype.inspect()` hexadecimal output
- `Buffer.isAscii()` fix
- `process.binding('buffer')` implementation

**`node:process`**:

- `process.stdin.ref()` and `process.stdin.unref()` fixes
- `process.stdout.write` preventing process exit fix
- `process.ref()` and `process.unref()` for event loop control
- `process.emit('worker')` event for worker creation
- `process._eval` property for `-e`/`--eval` code
- `process.on('rejectionHandled')` event support
- `--unhandled-rejections` flag (throw, strict, warn, none modes)
- `process.report.getReport()` on Windows
- `process.features.typescript`, `process.features.require_module`, `process.features.openssl_is_boringssl`
- `process.versions.llhttp`

**`node:child_process`**:

- `execArgv` option in `child_process.fork()`
- Race condition fixes for multiple sockets
- Empty IPC message handling
- Inherited stdin returns null instead of process.stdin
- `spawnSync` RangeError fix
- stdin, stdout, stderr, stdio properties now enumerable
- `execFile` stdout/stderr fixes
- stdio streams fix for quick destruction

**`node:timers`**:

- Unref'd `setImmediate` no longer keeps event loop alive
- Edge cases for millisecond values fixed
- Stringified timer IDs support in `clearTimeout`
- `clearImmediate` no longer clears timeouts and intervals
- AbortController support in `timers/promises`
- 98.4% of Node's timers test suite passes

**`node:dgram`**:

- `reuseAddr` and `reusePort` options fixes
- `addMembership()` and `dropMembership()` work without interface address

**`node:util`**:

- `parseArgs()` allowNegative option and default to `process.argv`
- `util.promisify` preserves function name and emits warnings
- `Buffer.prototype.inspect()` improvements

**`node:tls`**:

- `tls.getCACertificates()` returns bundled CA certificates
- Full certificate bundle support from `NODE_EXTRA_CA_CERTS`
- `translatePeerCertificate` function
- ERR_TLS_INVALID_PROTOCOL_VERSION and ERR_TLS_PROTOCOL_VERSION_CONFLICT errors
- TLSSocket allowHalfOpen behavior fix
- Windows TTY raw mode VT control sequences

**`node:worker_threads`**:

- Worker emits Error objects instead of stringified messages
- `Worker.getHeapSnapshot()` for heap tracking
- MessagePort communication after transfer fixes

**`node:readline/promises`**:

- `readline.createInterface()` implements `[Symbol.dispose]`
- Error handling promise rejection fixes

**`node:stream`**:

- `[Symbol.asyncIterator]` for `process.stdout` and `process.stderr`

**`node:perf_hooks`**:

- `monitorEventLoopDelay()` creates IntervalHistogram
- `createHistogram()` for statistical distributions

**`node:dns`**:

- `dns.resolve` callback fix (removed extra hostname argument)
- `dns.promises.resolve` returns array of strings for A/AAAA records

**`node:os`**:

- `os.networkInterfaces()` correctly returns scopeid for IPv6

**`node:cluster`**:

**`node:module`**:

- `module.children` array tracking
- `require.resolve` paths option
- `require.extensions` support
- `module._compile` correctly assigned
- `--preserve-symlinks` flag and NODE_PRESERVE_SYMLINKS=1
- `node:module.SourceMap` class and `findSourceMap()` function

**`node:zlib`**:

- Zstandard (zstd) compression/decompression with sync, async, and streaming APIs

**`node:ws`**:

- WebSocket upgrade abort/fail TypeError fixes

**Low-level APIs**:

- HTTPParser binding via `process.binding('http_parser')` using llhttp
- libuv functions: `uv_mutex_*`, `uv_hrtime`, `uv_once`
- v8 C++ API: `v8::Array::New`, `v8::Object::Get/Set`, `v8::Value::StrictEquals`

**N-API improvements**:

- `napi_async_work` creation and cancellation improvements
- `napi_cancel_async_work` support after queueing
- Correct ArrayBuffer and TypedArray handling in `napi_is_buffer()` and `napi_is_typedarray()`
- `process.exit()` notification in Workers
- `napi_create_buffer` ~30% faster, uses uninitialized memory
- `napi_create_buffer_from_arraybuffer` shares memory instead of cloning
- Assertion failure fixes with node-sqlite3 and lmdb
- IPC error handling improvements
- 98%+ of Node.js N-API tests now pass

**DOMException**:

- name and cause properties through options object

Bun 1.3 includes several improvements to make daily development easier and more productive.

Bun's default TypeScript configuration now uses `"module": "Preserve"` instead of `"module": "ESNext"`. This preserves the exact module syntax you write rather than transforming it, which true to Bun's design as a runtime that natively supports ES modules.

tsconfig.json

```
{
  "compilerOptions": {
    "module": "Preserve"
  }
}
```

Control how deeply `console.log()` inspects objects with the `--console-depth` flag or `bunfig.toml` config.

```bash
bun --console-depth=5 ./app.ts
```

`@types/bun` now auto-detects whether to use Node.js or DOM types based on your project. This prevents type conflicts when using browser APIs or Node.js APIs. Note that enabling TypeScript's DOM types alongside Bun will always prefer DOM types, which makes usage of some Bun-specific APIs show errors (for example, Bun's `WebSocket` class supports extra options not in the DOM spec).

We now run [an integration test](https://github.com/oven-sh/bun/tree/6e3359dd16aced2f6fca2a8e2de71f09e0bcb3cb/test/integration/bun-types) on every commit of Bun, to detect regressions and conflicts in Bun's type definitions.

Set default CLI arguments with the `BUN_OPTIONS` environment variable.

```ts
export BUN_OPTIONS="--watch --hot"
```

```
# Equivalent to: bun --watch --hot run ./app.ts
```

Set a custom User-Agent for `fetch()` requests with the `--user-agent` flag.

```bash
bun --user-agent="MyApp/1.0" ./app.ts
```

**`BUN_INSPECT_PRELOAD` environment variable.** An alternative to the `--preload` flag for specifying files to load before running your script:

```ts
export BUN_INSPECT_PRELOAD="./setup.ts"
```

```
# Equivalent to: bun --preload ./setup.ts run ./app.ts
```

**`--sql-preconnect` flag.** Establish a PostgreSQL connection at startup using `DATABASE_URL` to reduce first-query latency:

```ts
export DATABASE_URL="postgres://localhost/mydb"
```

```bash
bun --sql-preconnect ./app.ts
```

The connection is established immediately when Bun starts, so your first database query doesn't need to wait for connection handshake and authentication.

**`BUN_BE_BUN` environment variable.** When running a single-file executable created with `bun build --compile`, set this variable to run the Bun binary itself instead of the embedded entry point:

```bash
bun build --compile ./app.ts --outfile myapp
```

```

# Run the embedded app (default)
```

```

# Run Bun itself, ignoring the embedded app
```

```
BUN_BE_BUN=1 ./myapp --version
```

This is useful for debugging compiled executables or accessing Bun's built-in commands.

You can now use the `--package` (or `-p`) flag with `bunx` to run a binary from a package where the binary's name differs from the package's name. This is useful for packages that ship multiple binaries or for scoped packages. This brings `bunx`'s functionality in line with `npx` and `yarn dlx`.

```
# Run the 'eslint' binary from the '@typescript-eslint/parser' package
```

```bash
bunx --package=@typescript-eslint/parser eslint ./src
```

```bash
bunx --package=typescript@5.0.0 tsc --version
```

If you have feedback, `bun feedback` sends feedback directly to the Bun team. This opens a form to report bugs, request features, or share suggestions.

Bun 1.3 ships utility functions for common tasks.

`Bun.stripANSI()` is a 6-57x faster drop-in replacement for the `strip-ansi` npm package. Remove ANSI escape codes from strings with SIMD-accelerated performance.

![benchmark](https://bun.com/bun-strip-ansi.png)

`Bun.stripANSI()` also includes numerous improvements to escape sequence parsing, correctly handling cases known to fail in `strip-ansi`, like [XTerm-style OSC sequences](https://github.com/chalk/strip-ansi/issues/43).

To get started, just replace `import { stripANSI } from "strip-ansi"` with `import { stripANSI } from "bun"`.

app.ts

```ts
import { stripANSI } from "bun"

const colored = "\\x1b[31mRed text\\x1b[0m"
const plain = stripANSI(colored) // "Red text"
```

Use the Rapidhash algorithm for fast non-cryptographic hashing.

```ts
import { hash } from "bun"

const hashValue = hash.rapidhash("hello")
// => 9166712279701818032n
```

[**`postMessage`**](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage) is the most common way to send data between multiple worker threads in JavaScript. In Bun 1.3, we’re making `postMessage` significantly faster:

- **Strings**: 500x faster
- **Simple objects**: 240x faster

This improves performance for worker communication and deep object cloning.

![postMessage benchmark showing more than 500X for postMessage in Bun 1.3](https://bun.com/bun-postmessage.png)

By avoiding serialization for strings we know are safe to share across threads, it's **up to 500x faster** and uses **~22x less peak memory** in [**this benchmark**](https://github.com/oven-sh/bun/blob/b1417f494d389f4c75c21cfc6303d2a7a08a66d1/bench/postMessage/postMessage-string.mjs).

The optimization kicks in automatically when you send strings between workers:

```ts
// Common pattern: sending JSON between workers
const response = await fetch("https://api.example.com/data")
const json = await response.text()
postMessage(json) // Now 500x faster for large strings
```

This is particularly useful for applications that pass large JSON payloads between workers, like API servers, data processing pipelines, and real-time applications.

Bun 1.3 improves process spawning and shell scripting.

Kill spawned processes after a timeout with the `timeout` option.

```ts
import { spawn } from "bun"

const proc = spawn({
  cmd: ["sleep", "10"],
  timeout: 1000, // 1 second
})

await proc.exited // Killed after 1 second
```

The `maxBuffer` option in `Bun.spawn`, `spawnSync`, and `node:child_process` methods automatically kills the spawned process if its output exceeds the specified byte limit. This prevents runaway processes from consuming excessive memory:

```ts
import { spawn } from "bun"

const proc = spawn({
  cmd: ["yes"],
  maxBuffer: 1024 * 1024, // 1 MB limit
  stdout: "pipe",
})

await proc.exited // Killed after 1 MB of output
```

This is particularly useful when running untrusted commands or processing user input where output size is unpredictable.

`Bun.connect()` sockets now expose additional network information through new properties:

```ts
import { connect } from "bun"

const socket = await connect({
  hostname: "example.com",
  port: 80,
})

console.log({
  localAddress: socket.localAddress, // Local IP address
  localPort: socket.localPort, // Local port number
  localFamily: socket.localFamily, // 'IPv4' or 'IPv6'
  remoteAddress: socket.remoteAddress, // Remote IP address (previously available)
  remotePort: socket.remotePort, // Remote port number
  remoteFamily: socket.remoteFamily, // 'IPv4' or 'IPv6'
})
```

These properties provide complete visibility into both ends of a socket connection, useful for debugging, logging, and network diagnostics.

Pipe streams to spawned processes with ReadableStream `stdin`

```ts
import { spawn } from "bun"

const response = await fetch("https://example.com/data.json")

const proc = spawn({
  cmd: ["jq", "."],
  stdin: response.body,
})
```

- **`execArgv` in `child_process.fork()`**: Pass runtime arguments to forked processes
- **`process.ref()` / `process.unref()`**: Control event loop references
- **Bun Shell reliability improvements**: More robust shell implementation

Bun 1.3 includes performance improvements across the runtime.

- **Idle CPU usage reduced**: Fixed GC over-scheduling; Bun.serve timer only active during in-flight requests
- **JavaScript memory down 10-30%**: Better GC timer scheduling (Next.js -28%, Elysia -11%)
- **`Bun.build` 60% faster on macOS**: I/O threadpool optimization
- **Express 9% faster, Fastify 5.4% faster**: `node:http` improvements
- **`AbortSignal.timeout` 40x faster**: Rewritten using setTimeout implementation
- **`Headers.get()` 2x faster**: Optimized for common headers
- **`Headers.has()` 2x faster**: Optimized for common headers
- **`Headers.delete()` 2x faster**: Optimized for common headers
- **`setTimeout`/`setImmediate` 8-15% less memory**: Memory usage optimization
- **Startup 1ms faster, 3MB less memory**: Low-level Zig optimizations
- **SIMD multiline comments**: Faster parsing of large comments
- **Inline sourcemap ~40% faster**: SIMD lexing
- **`bun install` 2.5x faster for node-gyp packages**
- **`bun install` ~20ms faster in large monorepos**: Buffered summary output
- **`bun install` faster in workspaces**: Fixed bug that re-evaluated workspace packages multiple times
- **`bun install --linker=isolated`**: Significant performance improvements on Windows
- **`bun install --lockfile-only` much faster**: Only fetches package manifests, not tarballs
- **Faster WebAssembly**: IPInt (in-place interpreter) reduces startup time and memory usage
- **`next build` 10% faster on macOS**: setImmediate performance fix
- **`napi_create_buffer` ~30% faster**: Uses uninitialized memory for large allocations, matching Node.js behavior
- **NAPI: node-sdl 100x faster**: Fixed napi_create_double encoding
- **Faster sliced string handling in N-API**: No longer clones strings when encoding allows it
- **Highway SIMD library**: Runtime-selected optimal SIMD implementations narrow the performance gap between baseline and non-baseline builds
- **Faster number handling**: Uses tagged 32-bit integers for whole numbers returned from APIs like `fs.statSync()`, `performance.now()`, reducing memory overhead and improving performance
- **`fs.stat` uses less memory and is faster**
- **Improved String GC Reporting Accuracy**: Fixed reference counting for correct memory usage reporting
- **Reduced memory usage in `fs.readdir`**: Optimized Dirent class implementation with withFileTypes option
- **`Bun.file().stream()` reduced memory usage**: Lower memory usage when reading large amounts of data or long-running streams
- **Bun.SQL memory leak fixed**: Improved memory usage for many/large queries
- **`Array.prototype.includes` 1.2x to 2.8x faster**: Native C++ implementation
- **`Array.prototype.includes` ~4.7x faster**: With untyped elements in Int32 arrays
- **`Array.prototype.indexOf` ~5.2x faster**: With untyped elements in Int32 arrays
- **`Number.isFinite()` ~1.6x faster**: C++ implementation instead of JavaScript
- **`Number.isSafeInteger` ~16% faster**: JIT compilation
- **Polymorphic array access optimizations**: Calling same function on Float32Array, Float64Array, Array gets faster
- **Improved NaN handling**: Lower globalThis.isNaN to Number.isNaN when input is double
- **Improved NaN constant folding**: JavaScriptCore upgrade
- **Optimized convertUInt32ToDouble and convertUInt32ToFloat**: For ARM64 and x64 architectures
- **`server.reload()` 30% faster**: Improved server-side hot reload performance
- **TextDecoder initialization 30% faster**
- **`request.method` getter micro-optimized**: Caches 34 HTTP methods as common strings
- **Numeric hot loops optimization**: WebKit update with loop unrolling
- **Reduced memory usage for child process IPC**: When repeatedly spawning processes
- **Embedded native addons cleanup**: Delete temporary files immediately after loading in `bun build --compile`
- **Zero-copy JSON stringifier**: Eliminates memory allocation/copying for large JSON strings
- **String concatenation optimizations**: Patterns like `str += str` generate more efficient JIT code
- **`String.prototype.charCodeAt()` and `charAt()` folded at JIT compile-time**: When string and index are constants
- **`Array.prototype.toReversed()` optimized**: More efficient algorithms for arrays with holes
- **Reduced memory usage for large fetch() and S3 uploads**: Proper backpressure handling prevents unbounded buffering
- **WebKit updates**: Optimized MarkedBlock::sweep with BitSet for better GC performance
- **WebKit updates**: JIT Worklist load balancing and concurrent CodeBlockHash computation
- **WebKit updates**: String concatenation like `str += "abc" + "deg" + var` optimized to `str += "abcdeg" + var`
- **WebKit updates**: Delayed CachedCall initialization and improved `new Function` performance with sliced strings
- **Optimized internal WaitGroup synchronization**: Replaced mutex locks with atomic operations for high concurrent tasks
- **Threadpool memory management**: Releases memory more aggressively after 10 seconds of inactivity

Bun 1.3 includes hundreds of bug fixes. Here are the highlights:

**Package manager:**

- bun.lock now formats with proper newlines and spacing
- bun pm pack now correctly includes files starting with "./" from package.json
- Fixed bun.lock parsing with workspace overrides when package names differ
- Fixed assertion failure from invalid Semver versions with extra wildcards during package installation
- Fixed bun install --frozen-lockfile bug when using overrides (now sorts overrides consistently and includes unused overrides in lockfile)
- Fixed bun pack directory-specific pattern exclusion (exclusion patterns now work for nested files, not just top level)
- Fixed global package postinstall scripts not running even when explicitly opted in via trustedDependencies
- Fixed bun --install=force <script.ts> not respecting the --install=force flag
- Fixed cache invalidation issue with "browser" field in package.json being ignored after server import
- bun install no longer crashes when printing HTTP errors
- Fixed crash with very long package names in package.json parsing
- Fixed HTTPS client proxy reliability issue causing hangs when installing dependencies (impacted Codex)
- Fixed potential infinite loop when installing packages in projects with very large number of dependencies
- Fixed error handling for private git dependencies in bun install
- Fixed dependency resolution priority to devDependencies > optionalDependencies > dependencies > peerDependencies for consistency with other package managers
- Fixed bun install bug when passing multiple packages via CLI with certain dependency types
- Fixed bun install lifecycle script failures when directory deleted during install
- Fixed bun shell $-prefixed variables in package.json scripts
- Fixed crash during bun install permissions errors in non-interactive environments
- Fixed bun install assertion failure with malformed/oversized integrity hash in bun.lockb
- Fixed assertion failure parsing package.json with top-level catalog configurations
- Fixed non-deterministic module resolution for packages with both CJS and ESM
- Fixed panic installing global package with --trust if dependencies already trusted
- Fixed crash during bun install with malformed patch file
- bun install integer overflow parsing package versions fixed (affected @google/gemini-cli@nightly, @scratch/paper)
- bun install ETXTBUSY error when linking package binaries fixed
- Fixed catalog dependencies not handled correctly in bun update
- Fixed bun init listing CLAUDE.md twice in summary

**Runtime:**

- Fixed bytesWritten calculation in node:net when handling buffered string writes
- Fixed process.stdin buffering issue on macOS where input wasn't emitted incrementally
- Fixed potential exit signal hanging in loops
- Fixed SharedArrayBuffer crashing on transfer
- Fixed crash when accessing cookies before proper initialization
- Fixed "undefined is not an object" error when interrupting Next.js dev server with Ctrl+C
- Fixed Worker events not being emitted in some cases (e.g., "close" event)
- Fixed Worker terminate Promise not resolving in some cases
- Fixed fs.Dir.close regression
- Fixed Symbol() and Symbol("") formatting in Bun.inspect to correctly show Symbol()
- Fixed AbortSignal being garbage collected too early when passed to fetch or Bun.spawn without event listener
- Buffer.copy(), Buffer.from(), and multiple write/compare/indexOf methods now pass more Node.js tests
- Fixed automatic flushing of pending filesystem writes before process exit for Bun.file(path).writer()
- Fixed dynamic imports of "bun" package to return proper named exports instead of {default: globalThis.Bun}
- Fixed createRequire() to work with virtual paths that don't exist on disk (fixes Nuxt in Vite 6)
- Fixed vite build issue that caused incorrect or interleaved file writes
- Fixed DuckDB native module crashes from null-returning modules in napi_register_module_v1
- Fixed os.loadavg() to return accurate system CPU load averages on macOS
- Fixed S3 multipart upload edge case that could crash the process
- Fixed Bun.deepEquals() comparison of empty objects with same prototype but different internal types
- Fixed loader: "object" plugin to correctly handle \_\_esModule property
- Bun.Glob: Fixed bugs with directory matching and \*\* patterns
- File writer no longer prematurely closes file descriptors it doesn't own
- FormData boundary in fetch Content-Type header no longer includes quotes (matches Node.js)
- React JSX runtime correctly loads react-jsx vs react-jsxdev based on NODE_ENV
- process.stdin correctly resumes after unref/ref cycles
- Bun.file().stat() and .delete() now work correctly with non-ASCII paths
- Fixed hang when calling pause() on process.stdin - paused stdin streams no longer prevent process exit
- Fixed net.Socket error handlers receiving JSC::Exception objects instead of proper Error instances
- Fixed process.argv in --print and --eval modes to exclude [eval] argument (now matches Node.js)
- Fixed glob pattern parsing for nested braces like {a,{d,e}b}/c
- Fixed Node-API compatibility: each module now gets its own napi_env, preventing conflicts when loading multiple modules
- Fixed Node-API error handling to return error codes instead of crashing on null pointers
- Fixed Node-API object properties to have correct flags
- Fixed Node-API version detection for APIs like finalizers
- Fixed node:net connect() infinite loop when called with null/undefined arguments
- Fixed node:net socket.write() argument validation to throw appropriate errors for invalid types
- Fixed node:net allowHalfOpen to properly close writable side when readable side ends
- Fixed node:net socket timeout validation for invalid values (negative, Infinity, non-numbers)
- Fixed node:net server.unref() to persist when called before listen()
- Fixed node:net server.close() callback handling to properly register as one-time event listener
- Fixed node:net ipv6Only option to properly disable dual-stack support
- Fixed console.log() to display String objects as [String: "value"] matching Node.js behavior
- Fixed EventEmitter captureRejections validation for better error messaging
- Fixed setImmediate performance issue causing unnecessary event loop idling with setInterval timers
- Fixed Unicode property escapes in RegExp (e.g., \p{Script=Hangul}) affecting webpack compatibility
- Fixed WebSocket close() and terminate() error handling when internal instance is unavailable
- Fixed socket error messages to include syscall, address, and port properties
- Fixed WebSocket upgrades with Bun.serve() explicit route handlers
- Fixed ReadableStream error messages for type: "direct" to be more descriptive
- Fixed File() constructor to handle empty body with specified name
- Fixed memory error in ED25519 crypto key generation from private keys that could cause unpredictable behavior or crashes
- Fixed UDP socket address not resetting after connection in both Bun.udpSocket and node:dgram module
- Fixed bun-plugin-svelte not properly handling "svelte" export condition for packages like @threlte/core
- Fixed setTimeout incorrectly emitting TimeoutNaNWarning when delay parameter not specified
- Fixed trailing slashes in Bun.s3 presign causing incorrect URL generation
- Fixed global catch-all routes with callback handlers in Bun.serve() not working properly
- Fixed node: prefix not being maintained in module resolution
- Fixed module.id for entrypoints not correctly reporting "." for entry point module
- Fixed N-API string conversion edge cases in napi*get_value_string*_ and napi*create_string*_ functions
- Fixed shell crash when spawning many processes very quickly using Bun's shell API ($)
- Fixed ReferenceError message format to match Node.js behavior ("X is not defined" vs "Can't find variable: X")
- Fixed node:crypto hash names returned in uppercase instead of lowercase in getHashes() and getCiphers()
- Fixed node:vm options handling where undefined values would throw errors instead of using defaults
- Improved error messages for unsupported libuv functions in NAPI modules (previously showed cryptic "missing symbol called" crashes)
- Fixed Bun.write() to correctly throw error when called on Blob created from Buffer or TypedArray
- Fixed Bun.write() to properly handle creating directory trees when writing empty files
- Fixed Object.assign() to correctly copy properties from StatFs class instances
- Fixed AbortSignal static methods (timeout, abort, any) to work in environments without DOM
- Fixed crypto.Hmac regression where options.encoding set to undefined would throw instead of using default 'utf8'
- Fixed crypto.DiffieHellman issue where verifyError on prototype threw invalid this error
- Fixed Bun.serve redirects with empty streams not including response body
- Fixed node:crypto.createCipheriv throwing INVALID_ARG_VALUE with empty options object (now infers authTagLength)
- Fixed node:net.Server.prototype.address() returning incorrect result when listening on localhost (now properly resolves hostname)
- Fixed garbage collection edge case in node:fs where input buffers could be collected too early causing crashes
- Fixed HTML imports with custom loaders - can now use type: "text" with HTML files
- Fixed bytecode compilation with 'bun' module imports - all import styles now work
- Fixed node:crypto setAAD undefined checks - handles undefined options.encoding and options.plaintextLength
- Fixed string finalizers in N-API - finalizers no longer execute while other JavaScript code is running
- Fixed require.extensions index out of bounds crash when assigning and removing multiple custom extension handlers
- Fixed queueMicrotask error handling to throw ERR_INVALID_ARG_TYPE for invalid arguments
- Fixed typo in ReadableStream.prototype.tee() (fllags → flags) that could cause incorrect canceled stream state checks
- Fixed rare crash when importing invalid file URLs
- Fixed crash in Bun.plugin with recursive plugin calls through proper exception handling
- Fixed TextDecoder encoding label handling to properly throw errors for invalid labels with null bytes and return normalized encoding names
- Fixed TextDecoder 'fatal' option to properly coerce values to boolean instead of requiring strict boolean types
- Fixed worker_threads stability issues (multiple bug fixes)
- Fixed new TextDecoder("utf-8", undefined) throwing error instead of ignoring undefined argument
- Fixed BroadcastChannel.prototype.unref() returning undefined instead of the BroadcastChannel instance
- Fixed ERR_EVENT_RECURSION not being thrown when expected
- Fixed /\* wildcard route having higher precedence than method-specific routes
- Fixed crash with await in rare cases (JavaScriptCore upgrade)
- Fixed spec edgecase in eval (JavaScriptCore upgrade)
- Fixed spec edgecase with bitshifting right on objects implementing toString (JavaScriptCore upgrade)
- Fixed stability issue with Bun.plugin module resolution that could lead to crashes
- Fixed BunRequest.clone() not preserving cookies and params
- Fixed new Bun.CookieMap(object) incorrectly validating input object as HTTP header
- Fixed net.Socket constructor validation for fd option
- Fixed missing async in function declarations when top-level await present in circular dependencies
- Fixed rare crash in Bun.spawn
- Added missing JavaScript exception checks in native code with automated detection to prevent future regressions
- Fixed console warning in Bun's runtime error page
- Fixed crash when calling napi_delete_async_work multiple times on same work handle
- Fixed crash when exiting Worker inside N-API addon
- Fixed potential crash in N-API class constructors via Reflect.construct or when subclassed
- Fixed crash in process.env when invalid environment variables passed at startup
- Fixed potential invalid UTF-8 output in console.log and other APIs
- Fixed hypothetical stdout truncation from Bun.spawn on Linux/macOS when child exits before data fully read
- Fixed crash when writing to already-closed Bun.connect socket
- Fixed crash when ReadableStream garbage-collected during Worker termination
- Fixed missing default export in browser polyfills for Node.js addons (crypto, http, https, net, tty, util)
- Fixed Request constructor to store redirect option, preventing fetch() from incorrectly allowing redirects with redirect: "manual"
- Fixed bug where Content-Type header could be removed after accessing request.body from FormData or certain ReadableStream objects
- Fixed unref'd setTimeout/setInterval not executing in very tiny applications
- Fixed WebSocket "error" event to include Error object instead of string
- Fixed Bun.S3 presigned URLs to sort query parameters alphabetically for valid signature generation
- Fixed fetch() to allow overriding Connection header instead of always setting to keep-alive
- Fixed Bun.S3 HTTP-only S3_ENDPOINT loading from environment variables
- Fixed bun shell EPIPE error handling
- Fixed rare crash in Bun.which()
- Fixed Bun.inspect to show file size for Response objects with Bun.file
- Fixed thread-safety issue in zlib module when using Zstandard streams
- Fixed potential crash in node:crypto X509Certificate with invalid input
- Fixed crash in bun shell when using pipelines with built-in commands that exit immediately
- Fixed $.braces() support for Unicode characters and deeply nested expansions
- Fixed --linker=isolated bug with lifecycle scripts containing non-ASCII characters
- Fixed .write(), .writer(), .unlink(), .delete() on read-only Blob not throwing error (now throws correctly)
- Fixed Bun.resolve() and Bun.resolveSync() throwing raw values instead of Error objects
- Fixed crash in Bun.s3.unlink() when S3 credentials not configured
- Fixed string coercion of statusText to Response constructor
- Fixed Response.redirect() not throwing RangeError with invalid status codes
- Fixed environment variables from .env being truncated if longer than 4096 characters (also prevented crash)
- Fixed Invalid source map errors incorrectly logged in next dev --turbopack
- Fixed hypothetical bug where uncaught exception in process.nextTick or microtask not reported
- Fixed assertion failure reading files with odd number of bytes using utf16le or ucs2 encoding
- Fixed assertion failure when Worker calls process.exit
- Fixed bug in Error.prepareStackTrace when called with null, undefined, or non-array second argument
- Fixed bug where N-API exceptions propagated to JavaScript too quickly causing crashes
- Fixed structuredClone bugs with non-transferable objects
- Fixed Bun.hash.xxHash64 to correctly handle BigInt seeds larger than 32-bits
- Fixed server.stop() bug when called while requests still processing
- Fixed Bun.serve adding duplicate Date headers
- Fixed stack traces missing frames after accessing error.stack
- Fixed Error subclasses showing constructor frame instead of throw location as first frame
- Fixed ESPIPE error when reading from TTY stream after stdin closes
- Fixed child_process.spawnSync RangeError with process.stderr/stdout in stdio option
- Fixed socket.write() throwing exception with Uint8Array
- Fixed crypto.verify() error when null/undefined algorithm passed for RSA key
- Fixed N-API napi_strict_equals using Object.is instead of === operator
- Fixed N-API napi_call_function crash when recv argument is null pointer
- Fixed napi_create_array_with_length handling of negative/oversized lengths
- Fixed child_process stdin/stdout/stderr/stdio properties not enumerable
- Fixed Request body streaming with node-fetch buffering large bodies in memory
- Fixed Buffer.from(string, 'utf-16le') producing incorrect output in rare cases
- Fixed N-API assertion failure when napi_reference_unref called during garbage collection
- Fixed new Buffer.isAscii() using wrong implementation (was using isUtf8)
- Fixed async_hooks noisy warning when using React/Next.js
- Fixed crypto.randomInt not calling callback
- Fixed onResolve and onLoad plugin hooks not running for entrypoint files
- Fixed runtime plugins onResolve not resolving dynamic import() calls
- Fixed modules with top-level await missing async keyword
- Fixed crypto.subtle.importKey exception with RSA private keys with CRT parameters
- Fixed HTMLRewriter errors not propagating as catchable JavaScript errors
- Fixed assertion failure with BUN_INSPECT_CONNECT_TO and .env file loading
- Fixed crash when using Bun.secrets on Linux
- Fixed fetch() throwing Decompression error: ShortRead with empty gzip/brotli/zstd responses
- Fixed structuredClone() failing with nested objects/arrays containing Blob/File
- Fixed structuredClone() not preserving File.name property
- Fixed error stack traces being truncated
- Fixed WebSocket not emitting error event before close on handshake failure
- Fixed bun --watch crash when file is deleted
- Fixed bun --watch not handling swap file changes
- Fixed shell crash with environment variable assignments in pipeline
- Fixed bun patch internal data structure line indexing
- fetch() now handles multi-frame zstd-compressed responses with Transfer-Encoding: chunked
- fetch() with AbortSignal now aborts during socket connection (not just after)
- console.log Error object truncated stack trace fixed
- Infinite loop logging Error with circular reference fixed (error.stack = error, circular error.cause)
- Rare crash in Bun.serve during garbage collection fixed
- Crash when Bun.plugin onResolve returned undefined/null fixed
- UDP socket crash when process exiting fixed
- Rare race condition in fetch() with many simultaneous redirects and AbortSignal fixed
- Bun.serve stability issue with large request bodies fixed
- BUN_CONFIG_VERBOSE_FETCH=curl now prints request body for application/x-www-form-urlencoded
- Crash with large number of command-line arguments when accessing process.argv fixed
- Fixed NODE_NO_WARNINGS environment variable to be respected
- Fixed shell lexer incorrectly displaying = token as + in error messages
- Fixed namespace import objects incorrectly inheriting from Object.prototype
- Fixed bun:ffi new CString() ignoring byteOffset argument when byteLength not provided
- Fixed crash in bun:ffi with pointers encoded as 32-bit integers

**Bundler/transpiler:**

- Nested objects in macros with numeric property keys now work correctly
- Crash when macro returned complex/deeply-nested object or array fixed
- Fixed crash when parsing invalid shell syntax
- Fixed stack overflow in JavaScript parser with deeply nested expressions (refactored to use less stack space)
- Fixed build.module() failing to parse TypeScript with loader: 'ts'
- Fixed banner option with format: "cjs" and target: "bun" producing syntax error with shebang
- Bundler syntax error messages improved for invalid escape sequences outside string literals
- `require.main === module` with --target=node no longer incorrectly rewritten to `require.main === require.module`
- bun build --compile smarter about default output filenames, avoids attempting to write to directories
- Fixed bundler identifier collisions with block-scoped variables during minification
- Fixed inconsistent floating point math results in JavaScript transpiler vs runtime
- Fixed util.inherits missing in bun build --target=browser
- Fixed bundler onLoad plugins with loader: "file"
- Fixed sourcemap: true in Bun.build to actually generate sourcemaps (previously only accepted string enum)
- Fixed bun build generating invalid code for cyclic imports with top-level await
- Fixed bundler plugins unable to intercept entry points with onResolve
- bun build hanging with cyclic asynchronous module dependencies fixed
- Missing async keyword in bundled modules with top-level await in certain edge cases fixed
- Fixed assertion failure in JavaScript lexer when parsing invalid template string in JSX
- Fixed dead code elimination for unused pure function calls in comma expressions during minification
- Fixed parsing JSX namespaced attributes with numeric identifiers

**Test runner:**

- Fixed Jest globals (expect, test, describe) availability in imported test files
- Fixed VS Code extension test running with special characters in test names
- Fixed test runner to accept non-string describe labels (numbers, functions, classes)
- Fixed test timeout behavior with spawnSync - tests now properly timeout and terminate child processes
- Fixed test.failing with done callbacks - properly handles error passing and throwing
- Fixed bun:test -t filter to hide skipped and todo tests from output
- Fixed bun:test memory corruption causing test names to corrupt when beforeEach hook threw error
- Fixed beforeAll hooks running for describe blocks with no matching tests
- Fixed expect(() => { throw undefined }).toThrow(ErrorClass)
- Fixed jest.fn().mockRejectedValue() causing unhandled rejection when never called
- Fixed bun test not filtering tests correctly when directory name passed as argument
- Fixed bun test displaying wrong line for test.failing() warnings
- Fixed toIncludeRepeated checking for at least N occurrences instead of exactly N (now matches Jest)
- Fixed bun test failing with multiple test files using node:test module
- Fixed expect(...).toBeCloseTo(...) not counted in total expect calls in bun test
- Test execution order rewritten for improved reliability and predictability, especially for describe blocks and hooks (beforeAll, afterAll)
- Uncaught promise rejection in async test no longer causes test runner to hang
- test() and afterAll() inside another test() callback now throw error instead of being ignored
- test.only nested inside describe.only now executes only innermost .only tests
- describe.only now correctly skips beforeAll hooks in non-.only describe blocks
- Async beforeEach hook failure now prevents corresponding test from running
- Test hooks (beforeAll, beforeEach) now support timeout option and fail if exceeded
- afterAll hook now runs even if beforeAll hook fails (aligns with Jest)
- Error in beforeAll hook from --preload now correctly halts test execution across all files
- Error in describe block now correctly skips nested describe blocks
- describe.todo() incorrectly executed when nested inside describe.only() fixed
- Passing test inside describe.todo() block now handled correctly
- Error in async beforeEach hook now reported correctly instead of "unhandled error between tests"
- Custom matchers from jest-dom now work (this.utils.RECEIVED_COLOR, this.utils.EXPECTED_COLOR)
- vi.resetAllMocks, vi.useFakeTimers, vi.useRealTimers now stubbed
- Clearer error messages for --reporter and --coverage-reporter flags
- bun test loading files with . in path now works correctly
- Fixed toMatchInlineSnapshot to properly recognize hard tabs in indentation matching
- expect().toEqual() now handles error.cause and enumerable properties
- Fixed expect(...).toHaveBeenCalledWith() now showing colorful diff on failure

**Memory usage:**

- Fixed N-API handle scopes race condition and memory leak in garbage collection
- Fixed Bun.spawn stdio memory leak when piped stdio was never read
- Fixed memory leaks in development server by properly deinitializing resources on shutdown
- Fixed memory leak in Bun.spawn when stdout or stderr set to "pipe"
- Fixed memory leak in Bun.pathToFileURL caused by incorrect reference counting
- Fixed memory leak in Bun.serve() for requests with certain URLs
- Fixed memory leak with some strings caused by reference count not being decremented
- Fixed memory leak with AbortSignal in node:fs operations (fs.promises.writeFile, readFile, etc.)
- Fixed memory leak in DNS resolution error handling from c-ares (node:dns)
- Fixed memory leaks in Bun Shell
- Fixed sourcemap parsing with names field and potential memory leak on parsing failure
- Fixed memory leak in fs.mkdir and fs.mkdirSync with { recursive: true }
- Fixed HTMLRewriter crash when element handler throws exception, also fixed CSS selector memory leak
- Fixed memory leak in Bun.plugin onLoad filters using regex

**SQL:**

- Fixed Bun.SQL reliability issues causing queries to hang or fail when executing many prepared statements simultaneously
- SQL client must be called as tagged template literal (throws ERR_POSTGRES_NOT_TAGGED_CALL if called as function)
- SQL numeric values now returned as strings in binary format for safety/consistency with postgres.js
- SQL idle timeout no longer disconnects during active query processing
- SQL connection strings now properly handle URL-encoded usernames, passwords, and database names
- SQL template literal fragments properly handle nesting and parameter concatenation
- SQL ReadyForQuery state bug fixed (prevented premature disconnection)
- SQL verify-full and verify-ca SSL modes now correctly handle certificate verification
- Fixed binary data types and custom type OIDs in PostgreSQL client
- Fixed Bun.sql PostgreSQL parameter validation and error messaging
- Fixed PostgreSQL flush() method being undefined
- Fixed Bun.SQL sql() helper TypeScript types for column name overloads
- Fixed crash in Bun.SQL when database connection fails
- Fixed index out of bounds error during large batch inserts in Bun.SQL
- Fixed Bun.sql client hanging indefinitely during shutdown with pending queries
- Fixed Bun.SQL Unix domain socket connection failures with PostgreSQL
- Fixed Bun.SQL WHERE IN clause support for string arrays
- Fixed DATABASE_URL options precedence in Bun.SQL connection string parsing
- Bun.sql postgres driver NUMERIC parsing with many digits fixed

**HTTP/TLS:**

- Fixed TLS server identity verification improvements
- Fixed proper handling of IP range normalization (e.g., "8.8.8.0/24")
- Fixed ERR_SSL_NO_CIPHER_MATCH with unsupported/invalid cipher suites in TLS
- Fixed Bun.serve() incorrectly rejecting tls array with single configuration object
- Fixed certificate verification error spelling: UNKKNOW_CERTIFICATE_VERIFICATION_ERROR → UNKNOWN_CERTIFICATE_VERIFICATION_ERROR
- Fixed HTTP/2 flow control and protocol handling issues
- Fixed node:http2 sending multiple RST frames when only one should be sent
- Fixed duplicate Transfer-Encoding header in node:http
- Fixed Strict-Transport-Security headers to be sent over HTTP (for proxy deployments)
- Fixed Fastify websockets registration issue in node:http
- Fixed ERR_HTTP_SOCKET_ASSIGNED in Next.js
- Fixed rejectNonStandardBodyWrites behavior in node:http module - properly handles undefined and false values
- Fixed node:http Agent abort handling edge cases
- Fixed node:http extra arguments handling in http.request URLs
- Fixed HTTP/1.1 chunked encoding extensions being incorrectly rejected
- Fixed ERR_STREAM_ALREADY_FINISHED error when cancelling HTTP requests (e.g., page refresh in next dev)
- Fixed fetch() with large bodies failing with ECONNRESET when using HTTP proxy for HTTPS
- Fixed fetch() hanging with 101 Switching Protocols response

**CSS parser:**

- Fixed CSS calc() expressions causing stack overflow with nested calculations
- Fixed radians incorrectly converted to degrees in CSS transform functions
- Fixed CSS parser bugs (mentioned in description, no specific details in notes)
- CSS: Fixed light/dark mode handling, color down-leveling, and box-shadow minification
- CSS: @-webkit-keyframes rule now parsed correctly
- Added 275+ CSS parser tests and fixed several subtle bugs for improved stability
- Improved CSS floating point precision by always printing to 6 decimal places for smaller bundle sizes
- Updated CSS vendor prefixing to latest autoprefixer version
- Fixed :global() selector in CSS modules not being processed correctly
- Fixed CSS parser handling of infinity values to render properly in Safari (3.40282e38px vs 1e999px for Tailwind v4 rounded-full)
- Fixed CSS custom property parser edgecase
- Fixed code splitting bug where CSS imports in dynamic ES modules pointed to CSS instead of JavaScript
- Fixed CSS parser bugs with calc() and color-mix() involving hsl()
- Fixed assertion failure in CSS parser with large floating-point values from TailwindCSS
- Fixed parsing linear-gradient() with turn angle units

**Windows:**

- Fixed WebKit and libpas dependencies updated for Windows builds
- bunx no longer throws "exec" error on Windows
- Fixed stat() assertion failure on Windows in node:fs
- Fixed .npmrc file parsing to handle Byte Order Mark (BOM) conversions, particularly for UTF-16 encoded files on Windows
- Fixed bun run --filter ignoring NO_COLOR on Windows
- Fixed fs.accessSync() and fs.existsSync() handling of relative paths with "../" segments on Windows
- Fixed assertion failure on Windows with invalid file paths
- Windows icon now properly set in executable
- bunx now works on Windows when installed with npm
- Fixed bunx yarn failing on Windows due to unnecessary postinstall script
- Fixed Windows crash with async macros in bundler affecting OpenCode
- Fixed crash in Windows file watcher when many files change at once (e.g., git branch switch)
- Fixed integer cast panic when reading large files on Windows
- Fixed Bun.which on Windows failing to find executables in paths with non-ASCII characters
- Fixed Windows install.ps1 incorrectly joining PATH with spaces instead of semicolons
- Fixed bun shell pipelines on Windows
- Fixed tarball extraction with unusual package names producing invalid temp filename on Windows
- Windows crash in bun outdated/bun install from race condition fixed
- Windows assertion failure from incorrect file path fixed

**TypeScript types:**

- Fixed TypeScript type conflicts between Bun, Node.js, and DOM type definitions (Buffer.equals() type errors)
- Fixed TypeScript declarations so Bun.Env types correctly apply to process.env
- Fixed generic type parameters for ReadableStream and WritableStream
- Fixed URLSearchParams type definitions for better @types/node compatibility
- Fixed TypeScript support for using Bun.$ as a type annotation
- Fixed spyOn type inference for optional methods (TypeScript types)
- Fixed CryptoKeyPair global type (TypeScript types)
- TypeScript legacy decorators now work with computed property names
- Fixed @types/bun for better TypeScript support (\*.svg modules, ShellError types)
- TypeScript non-null assertions with new operator now work: `new obj!.a()`
- Fixed type confusion bug with async generator function as readable stream body
- Fixed require.main being readonly in TypeScript type definitions
- Fixed db.transaction() TypeScript types to correctly infer return type and argument types

**Other:**

- Fixed typo in bun upgrade error message (extra closing parenthesis)
- Fixed terminal syntax highlighter adding extra closing brace } to template literal errors
- Fixed assertion failure in Bun's logger when processing source locations
- Sourcemap line numbers off-by-one in Chrome DevTools fixed
- install.sh now prioritizes ~/.bash_profile over ~/.bashrc for PATH updates
- npm install bun on Alpine Linux arm64 fixed
- Stack traces now dim current working directory for better readability
- Fixed bun run attempting to execute JSON files (e.g., index.json)
- Fixed TOML parser incorrectly handling table array headers after inline tables
- Fixed Bun to report ResolveMessage and BuildMessage errors as native errors (allows pnpm to work)
- Fixed file:// URL encoding issue
- Fixed bun init -h to show help text
- Changed SIGPWR signal on Linux for GC thread suspension instead of SIGUSR1 to avoid application conflicts
- Reliability improvements for filesystem operations - fixed Zig standard library error propagation from system calls
- CLI help flags now show =<val> to indicate they accept values

- Bun.serve() TypeScript types were reworked:
  - **Defining the WebSocket data in `Bun.serve()` has changed** to using a pattern popularised by XState. See the [new docs here](https://bun.sh/docs/api/websockets#contextual-data). This is due to a [limitation in TypeScript](https://github.com/microsoft/TypeScript/issues/26242).
  - `Bun.Server<T>` is now generic, with the one type parameter representing the WebSocket `.data` type (use `undefined` or `unknown` if not using WebSockets)
  - `Bun.ServeOptions` is now deprecated in favor of `Bun.Serve.Options`
- **TypeScript default**: `"module": "Preserve"` (was auto-detected)
- **GC signal**: SIGPWR instead of SIGUSR1 on Linux
- **`require('./file.unknown-extension')`**: requiring files with unknown extensions defaults to the JavaScript loader instead of file loader for Node.js compatibility
- **`bun info` aliased to `bun pm view`**
- **`Bun.serve()` routes**: The `static` option has been renamed to `routes`
- **SQL client**: Now throws error if called as function instead of tagged template literal (use `sql`query``or`sql.unsafe()`)
- **`Bun.build` errors**: Now throws `AggregateError` by default on build failures (set `{ throw: false }` to revert)
- **Minifier**: Removes unused function and class expression names by default (use `--keep-names` to preserve)
- TypeScript types for `bun:test`'s expect matchers were made stricter. Some matchers support relaxing the strictness by passing a type parameter. For example `expect(null).toBe<string | null>("hello")`
- **`bun test` filter**: Now fails with error when no tests match the `-t <filter>` regex (previously succeeded silently)
- **`os.networkInterfaces()`**: Returns `scopeid` instead of `scope_id` for IPv6 interfaces (matches Node.js)
- **Namespace imports**: Objects from `import * as ns` no longer inherit from `Object.prototype`
- **`bun test` nesting**: `test()` and `afterAll()` inside another `test()` callback now throw error instead of being silently ignored
- **Node.js version**: Bun now reports as Node.js v24.3.0 instead of v22.6.0 (affects `process.version`, `process.versions.node`, and N-API version)

---

Bun 1.3 is the biggest release yet. Try it today:

```bash
bun upgrade
```

Or install Bun for the first time:

```bash
curl -fsSL https://bun.sh/install | bash
```

We're excited to see what you build with Bun 1.3. Join us on [Discord](https://bun.sh/discord) and share your projects!
