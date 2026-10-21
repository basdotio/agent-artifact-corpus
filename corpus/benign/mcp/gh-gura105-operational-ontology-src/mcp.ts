/**
 * operational-ontology · MCP surface
 *
 * Generates an MCP server from an ontology definition. Because the model is
 * data, the agent-facing tool surface is derived, not hand-written:
 *
 *   - per object type:  search/get/aggregate and set algebra
 *   - per link type:    traverse_<link>, pivot_<link> (both directions)
 *   - per action:       <action>, guarded by the same preconditions as
 *                       every other caller
 *   - per function:     <function>, a model-defined read
 *   - plus:             read_audit_log
 *
 * There is intentionally no raw SQL tool and no generic update tool.
 * The absence is the point: the operation space an agent gets is exactly
 * the operation space the model defines.
 *
 * This file adapts JSON inputs and outputs, derives schemas, and supplies the
 * session actor. Runtime still executes queries and checks Action plans;
 * transport handlers do not reproduce domain rules or write directly to SQLite.
 * Clients filter results in their own code execution environment; no code is
 * accepted or executed by this server.
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { z } from 'zod'
import { objectSet } from './core.js'
import type { ObjectInstance, Runtime, OntologyDef } from './core.js'
import { fieldKind } from './query.js'
import pkg from '../package.json' with { type: 'json' }

/**
 * Enumerate a model to publish its choices as tool schemas. These guide and
 * validate agent inputs independently of the application's TypeScript types.
 */
export function buildMcpServer<Model extends OntologyDef>(rt: Runtime<Model>, opts: { agent?: string } = {}): McpServer {
  // The version an agent sees is the package's — one place to bump.
  const server = new McpServer({ name: `operational-ontology:${rt.ontology.name}`, version: pkg.version })
  // Tool names are derived from model names, so two model names can collide
  // after snake-casing (object `Order` ⇒ search_order, action `searchOrder`
  // ⇒ search_order). Fail at build time with both origins named.
  const claimed = new Map<string, string>()
  const toolName = (name: string, origin: string): string => {
    const holder = claimed.get(name)
    if (holder !== undefined) {
      throw new Error(`MCP tool name collision: "${name}" is derived from both ${holder} and ${origin} — rename one`)
    }
    claimed.set(name, origin)
    return name
  }
  // Over stdio there is no session id, so every caller collapses to one
  // identity — pass opts.agent to name the agent this server serves.
  // This supplies a visibility label; it is not an authentication mechanism.
  const actorOf = (extra?: { sessionId?: string }) => `agent:${extra?.sessionId ?? opts.agent ?? 'mcp'}`
  const asJson = (value: unknown) => ({
    content: [{ type: 'text' as const, text: JSON.stringify(value, null, 2) }],
  })
  // Every handler — reads included — surfaces crashes in the same
  // machine-readable shape as refusals. No stack dumps in an agent's context.
  // A preserves the handler's argument tuple (inputs and session context);
  // R preserves its normal result alongside the added error envelope.
  const guarded =
    <A extends unknown[], R>(fn: (...args: A) => Promise<R>) =>
    async (...args: A): Promise<R | (ReturnType<typeof asJson> & { isError: true })> => {
      try {
        return await fn(...args)
      } catch (e) {
        return {
          ...asJson({ error: { code: 'INTERNAL', message: e instanceof Error ? e.message : String(e) } }),
          isError: true as const,
        }
      }
    }
  // IDs select current snapshots, not authority to read them. Missing or hidden
  // objects drop out; caller-supplied properties never replace the stored values.
  const hydrate = (type: string, pks: readonly string[], actor: string) => objectSet(type,
    pks.map((pk) => rt.get(type, pk, { actor })).filter((object) => object !== undefined))
  for (const [typeName, def] of Object.entries(rt.ontology.objects)) {
    server.registerTool(
      toolName(`search_${snake(typeName)}`, `object type ${typeName}`),
      {
        description: `Read ${typeName} objects visible to this session. Filter the returned objects in client-side code, then pass selected IDs to pivot, set or aggregate tools.`,
        inputSchema: z.object({}).strict(),
      },
      guarded(async (_args: Record<string, never>, extra: { sessionId?: string }) =>
        asJson(rt.search(typeName, { actor: actorOf(extra) }))),
    )
    server.registerTool(
      toolName(`get_${snake(typeName)}`, `object type ${typeName}`),
      {
        description: `Fetch a single ${typeName} by primary key (${def.primaryKey}).`,
        inputSchema: { [def.primaryKey]: z.string() },
      },
      guarded(async (args: Record<string, unknown>, extra: { sessionId?: string }) =>
        asJson(rt.get(typeName, String(args[def.primaryKey]), { actor: actorOf(extra) }) ?? null)),
    )

    // Per-type tools make both ID lists use the same object identity namespace.
    for (const op of ['union', 'intersect', 'subtract'] as const) {
      server.registerTool(
        toolName(`${op}_${snake(typeName)}`, `${op} ${typeName}`),
        { description: `${op} two ${typeName} sets, identified by primary keys and reloaded for this session.`,
          inputSchema: z.object({ left: z.array(z.string()), right: z.array(z.string()) }).strict() },
        guarded(async (args: { left: string[]; right: string[] }, extra: { sessionId?: string }) =>
          asJson(rt[op](hydrate(typeName, args.left, actorOf(extra)), hydrate(typeName, args.right, actorOf(extra))))),
      )
    }
    // Reuse query's field classification so agent choices match local validation:
    // supported scalar properties for groups, numeric properties for sums.
    const propertyKeys = Object.entries(def.properties).filter(([, schema]) => fieldKind(schema as z.ZodType)).map(([key]) => key) as [string, ...string[]]
    const numericKeys = Object.entries(def.properties).filter(([, schema]) => fieldKind(schema as z.ZodType) === 'number').map(([key]) => key)
    const aggregateShape: Record<string, z.ZodType> = {
      pks: z.array(z.string()), group_by: z.enum(propertyKeys).optional(),
    }
    if (numericKeys.length > 0) aggregateShape.sum = z.enum(numericKeys as [string, ...string[]]).optional()
    server.registerTool(
      toolName(`aggregate_${snake(typeName)}`, `aggregate ${typeName}`),
      {
        description: `Count the selected ${typeName} objects and optionally sum a numeric property. Omit group_by for one whole-set total (key: null, zero metrics for an empty set), or group by a property. Returns set and values; each row has a key, member pks and numeric metrics. Filter rows in client-side code and use their pks to continue exploring.`,
        inputSchema: z.object(aggregateShape).strict(),
      },
      guarded(async (rawArgs: Record<string, unknown>, extra: { sessionId?: string }) => {
        const args = rawArgs as { pks: string[]; group_by?: string; sum?: string }
        const set = hydrate(typeName, args.pks, actorOf(extra))
        return asJson(rt.aggregate(set, { groupBy: args.group_by, sum: args.sum }))
      }),
    )
  }

  // A link's endpoints determine whether direction is required. With different
  // endpoint types, Runtime still checks an explicit direction against source.type.
  for (const [linkName, link] of Object.entries(rt.ontology.links)) {
    server.registerTool(
      toolName(`traverse_${snake(linkName)}`, `link type ${linkName}`),
      {
        description:
          `Traverse the ${link.from} → ${link.to} link "${linkName}" (${link.kind}). ` +
          'Pass an instance returned by get or search; its properties are a snapshot, not authority. ' +
          (link.from === link.to
            ? 'Choose direction=forward or reverse for this self-type link.'
            : 'Direction is inferred from source.type; an explicit direction must agree.'),
        inputSchema: {
          source: z.object({
            type: z.enum([link.from, link.to]),
            pk: z.string(),
            properties: z.record(z.string(), z.unknown()),
          }),
          direction: link.from === link.to
            ? z.enum(['forward', 'reverse'])
            : z.enum(['forward', 'reverse']).optional(),
        },
      },
      guarded(async (args: { source: ObjectInstance; direction?: 'forward' | 'reverse' }, extra: { sessionId?: string }) =>
        // The runtime checks the instance, link and direction together.
        asJson(rt.traverse(args.source, linkName, {
          actor: actorOf(extra), direction: args.direction,
        }))),
    )
  }

  for (const [linkName, link] of Object.entries(rt.ontology.links)) {
    server.registerTool(
      toolName(`pivot_${snake(linkName)}`, `pivot ${linkName}`),
      {
        description: `Follow ${linkName} from a set of ${link.from} or ${link.to}. Duplicate target identities are removed. Direction is required when both ends have the same type.`,
        inputSchema: {
          source: z.object({ type: z.enum([link.from, link.to]), pks: z.array(z.string()) }).strict(),
          direction: link.from === link.to ? z.enum(['forward', 'reverse']) : z.enum(['forward', 'reverse']).optional(),
        },
      },
      guarded(async (args: { source: { type: string; pks: string[] }; direction?: 'forward' | 'reverse' }, extra: { sessionId?: string }) => {
        const actor = actorOf(extra)
        return asJson(rt.pivot(hydrate(args.source.type, args.source.pks, actor), linkName,
          { actor, direction: args.direction }))
      }),
    )
  }

  // Invoke Actions through execute, preserving the same validation, write-back and
  // audit path as local callers. A business refusal becomes an MCP tool error.
  for (const [actionName, action] of Object.entries(rt.ontology.actions)) {
    server.registerTool(
      toolName(snake(actionName), `action ${actionName}`),
      {
        description:
          `${action.description ?? `Action on ${action.object}.`} ` +
          'Writes are gated: if a business rule rejects this call, the error is ' +
          'machine-readable ({ code, message }) and the attempt is recorded in the audit log.',
        inputSchema: action.params,
      },
      guarded(async (params: Record<string, unknown>, extra: { sessionId?: string }) => {
        const result = rt.execute(actionName, params, { actor: actorOf(extra) })
        if (!result.ok) {
          return { ...asJson({ error: result.error }), isError: true }
        }
        return asJson({ applied: result.edits })
      }),
    )
  }

  // Read-only is a Function authoring contract; the MCP hint advertises it.
  // Await supports both synchronous values and asynchronous Function results.
  for (const [name, fn] of Object.entries(rt.ontology.functions ?? {})) {
    server.registerTool(
      toolName(snake(name), `function ${name}`),
      {
        description: fn.description ?? `Read through the model's ${name} function.`,
        inputSchema: fn.params,
        annotations: { readOnlyHint: true },
      },
      guarded(async (params: Record<string, unknown>, extra: { sessionId?: string }) =>
        asJson(await rt.call(name, params, { actor: actorOf(extra) }))),
    )
  }

  server.registerTool(
    toolName('read_audit_log', 'the built-in audit view'),
    {
      description:
        'Read the append-only audit log: every applied and rejected action, with actor and params. ' +
        'This is an unscoped administrative view — entries are not filtered by visibility (fail-open, declared).',
      inputSchema: {
        action: z.string().optional(),
        status: z.enum(['applied', 'rejected']).optional(),
        target: z.string().optional(),
      },
    },
    guarded(async (filter: Record<string, unknown>) =>
      asJson(rt.auditLog(prune(filter) as Parameters<typeof rt.auditLog>[0]))),
  )

  return server
}

const snake = (name: string) => name.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase()

const prune = <T extends Record<string, unknown>>(obj: T): T =>
  Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined)) as T
