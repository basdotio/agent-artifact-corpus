// pantry MCP server (stdio).
//
// A thin Model Context Protocol server over the same PantryClient + demo runner
// the CLI uses. It exposes four tools so any MCP client (Claude Desktop, Cursor,
// or another harness) can list, fetch, run, and push pantry recipes.
//
// Trust posture, stated plainly so a client author cannot miss it:
//   - pantry stores and returns code. It never runs a recipe.
//   - `pantry_run` executes fetched code in THIS server's own process using the
//     demo runner. That runner is NOT a sandbox. Running a fetched recipe is the
//     caller's decision and the caller's risk. Untrusted recipes need a real
//     isolate (a Worker Loader, a separate Worker, a child process, or a vetted
//     JS sandbox).
//   - capability tags are metadata a caller reasons about, not permissions
//     pantry enforces.
//
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { checkRecipe, runRecipe } from '../examples/run-recipe.ts';
import { RUN_CAVEAT, describeError, makeClient } from './surface.ts';

type TextResult = { content: Array<{ type: 'text'; text: string }>; isError?: boolean };

const ok = (value: unknown): TextResult => ({
  content: [
    { type: 'text', text: typeof value === 'string' ? value : JSON.stringify(value, null, 2) },
  ],
});
const fail = (text: string): TextResult => ({ content: [{ type: 'text', text }], isError: true });

type Pantry = ReturnType<typeof makeClient>['client'];

export function createPantryMcpServer(opts: { client?: Pantry; url?: string } = {}): McpServer {
  const server = new McpServer({ name: 'pantry', version: '0.1.0' });
  const { client, url } = opts.client
    ? { client: opts.client, url: opts.url ?? 'injected' }
    : makeClient();

  server.registerTool(
    'pantry_list',
    {
      title: 'List recipes',
      description:
        'List recipe names, descriptions, input schemas, and capability tags. Never returns code. Use scope "shared" to list opt-in shared recipes from other owners. Filter with q (keyword over name+description) or capability (a capability tag) so discovery stays cheap as the cookbook grows.',
      inputSchema: {
        scope: z.enum(['owner', 'shared']).optional(),
        q: z.string().optional(),
        capability: z.string().optional(),
      },
    },
    async ({ scope, q, capability }) => {
      try {
        const recipes = await client.list({ scope, q, capability });
        return ok(recipes);
      } catch (err) {
        return fail(describeError(err, url));
      }
    },
  );

  server.registerTool(
    'pantry_get',
    {
      title: 'Get a recipe',
      description:
        'Fetch one recipe by name, including its exact saved code and provenance (author, version, visibility). Returns null when the recipe does not exist for this owner.',
      inputSchema: { name: z.string() },
    },
    async ({ name }) => {
      try {
        const recipe = await client.get(name);
        return ok(recipe ?? { found: false, name });
      } catch (err) {
        return fail(describeError(err, url));
      }
    },
  );

  server.registerTool(
    'pantry_run',
    {
      title: 'Run a recipe (caller-side, not a sandbox)',
      description:
        'Fetch a recipe and run its code in this server process over { input }. This executes fetched code and is NOT a sandbox; running it is the caller\u2019s decision and risk. Untrusted recipes need a real isolate.',
      inputSchema: { name: z.string(), input: z.record(z.string(), z.unknown()).optional() },
    },
    async ({ name, input }) => {
      try {
        const recipe = await client.get(name);
        if (!recipe) return fail(`recipe not found: ${name}`);
        // Pre-flight the recipe's required host interfaces (E-WIDEN-3). This MCP
        // server provides no host bindings, so a recipe that requires e.g.
        // machine.shell is refused HONESTLY, naming what it needs, rather than
        // failing with an opaque runtime error. Pure recipes run as before.
        const preflight = checkRecipe(recipe);
        if (!preflight.ok) {
          return fail(
            `recipe '${name}' requires host interface(s) [${preflight.requires.join(', ')}] that this MCP server does not provide (missing [${preflight.missing.join(', ')}]). Run it in a harness that binds those interfaces.`,
          );
        }
        const result = runRecipe(recipe, { input: input ?? {} });
        return ok({ caveat: RUN_CAVEAT, result });
      } catch (err) {
        return fail(describeError(err, url));
      }
    },
  );

  server.registerTool(
    'pantry_push',
    {
      title: 'Push a recipe',
      description:
        'Upsert a recipe for this owner. Provide name, description, inputSchema, code, and at least one capability tag. Set shared to publish it as an opt-in shared recipe; it stays private by default.',
      inputSchema: {
        recipe: z.object({
          name: z.string(),
          description: z.string(),
          inputSchema: z.record(z.string(), z.unknown()),
          code: z.string(),
          capabilities: z.array(z.string()),
        }),
        shared: z.boolean().optional(),
      },
    },
    async ({ recipe, shared }) => {
      try {
        const saved = await client.push({
          ...recipe,
          ...(shared ? { visibility: 'shared' } : {}),
        } as Parameters<typeof client.push>[0]);
        return ok(saved);
      } catch (err) {
        return fail(describeError(err, url));
      }
    },
  );

  return server;
}

export async function runStdio(): Promise<void> {
  const server = createPantryMcpServer();
  await server.connect(new StdioServerTransport());
}

if (import.meta.main) {
  runStdio().catch((err) => {
    console.error(`pantry mcp failed: ${err instanceof Error ? err.message : String(err)}`);
    process.exit(1);
  });
}
