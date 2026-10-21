/**
 * Catalog-driven tool engine.
 *
 * Instead of hand-writing a handler for every endpoint, this module compiles
 * declarative catalog entries into fully-functional MCP tools.  Each catalog
 * describes its endpoints as data – the engine does the rest.
 */

import { z } from "zod"
import { request, sanitizeSegment } from "./gateway.js"
import type { GatewayResult } from "./gateway.js"
import { zodToJsonSchema } from "./validation.js"

// ---------------------------------------------------------------------------
// Types – catalog authors work with these
// ---------------------------------------------------------------------------

/** A single endpoint within a grouped tool. */
export interface CommandSpec {
  /** Command name – becomes the discriminator value. */
  name: string
  /** URL template, e.g. "/api/stock/{ticker}/info". Path slots are extracted automatically. */
  route: string
  /** Zod schema for this command's parameters (excluding the `command` field). */
  params: z.ZodObject<any>
  /** Map schema keys to different query-param names (e.g. { expirations: "expirations[]" }). */
  queryRenames?: Record<string, string>
  /** If true, command is hidden unless the operator opts in via UW_ENABLE_PREMIUM_TOOLS or UW_PREMIUM_TOOLS (using "<catalog_id>.<command>" form). */
  premium?: boolean
}

/** A grouped tool that exposes multiple commands via a `command` discriminator. */
export interface ToolCatalog {
  /** MCP tool name, e.g. "uw_stock". */
  id: string
  /** Human-readable description shown to MCP clients. */
  summary: string
  /** Endpoint definitions. */
  commands: CommandSpec[]
  /** Optional MCP annotations. */
  hints?: { readOnlyHint?: boolean; idempotentHint?: boolean; openWorldHint?: boolean }
  /** Optional Zod output schema. */
  outputSchema?: z.ZodType
  /** If true, tool is hidden unless the operator opts in via UW_ENABLE_PREMIUM_TOOLS or UW_PREMIUM_TOOLS. */
  premium?: boolean
}

/** A standalone tool with its own dedicated schema (no command discriminator). */
export interface StandaloneSpec {
  id: string
  summary: string
  route: string
  params: z.ZodObject<any>
  queryRenames?: Record<string, string>
  hints?: { readOnlyHint?: boolean; idempotentHint?: boolean; openWorldHint?: boolean }
  premium?: boolean
}

// ---------------------------------------------------------------------------
// Compiled tool – ready for MCP registration
// ---------------------------------------------------------------------------

export interface ToolOutput {
  text: string
  structuredContent?: unknown
}

export type ToolHandler = (args: Record<string, unknown>) => Promise<string | ToolOutput>

export interface CompiledTool {
  name: string
  description: string
  inputSchema: { type: "object"; properties: Record<string, unknown>; required: string[] }
  zodInputSchema: any
  outputSchema?: { type: "object"; properties: Record<string, unknown>; required?: string[] }
  annotations?: Record<string, boolean>
  handler: ToolHandler
  premium?: boolean
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Extract `{param}` placeholder names from a route template. */
function pathSlots(template: string): string[] {
  const hits = template.match(/\{([^}]+)\}/g)
  if (!hits) return []
  return hits.map((m) => m.slice(1, -1))
}

/** Substitute path slots and separate remaining fields into a query map. */
function resolveRoute(
  template: string,
  data: Record<string, unknown>,
  renames?: Record<string, string>,
): { url: string; query: Record<string, any> } {
  const slots = pathSlots(template)
  let url = template

  for (const slot of slots) {
    url = url.replace(`{${slot}}`, sanitizeSegment(data[slot]))
  }

  const query: Record<string, any> = {}
  for (const [key, val] of Object.entries(data)) {
    if (key === "command" || slots.includes(key)) continue
    if (val === undefined) continue
    const apiKey = renames?.[key] ?? key
    query[apiKey] = val
  }

  return { url, query }
}

function faultResponse(msg: string): ToolOutput {
  return { text: JSON.stringify({ error: msg }, null, 2) }
}

function gatewayToOutput(result: GatewayResult): ToolOutput {
  if (result.fault) return faultResponse(result.fault)
  return {
    text: JSON.stringify(result.payload, null, 2),
    structuredContent: result.payload,
  }
}

// ---------------------------------------------------------------------------
// Compile a ToolCatalog → CompiledTool
// ---------------------------------------------------------------------------

export function compileCatalog(catalog: ToolCatalog): CompiledTool {
  // Build the discriminated union: each variant has a `command` literal field
  const variants = catalog.commands.map((cmd) =>
    cmd.params.extend({ command: z.literal(cmd.name) }),
  )

  const union = z.discriminatedUnion("command", variants as any)

  // Index commands by name for O(1) lookup
  const lookup = new Map(catalog.commands.map((c) => [c.name, c]))

  const handler: ToolHandler = async (args) => {
    const parsed = union.safeParse(args)
    if (!parsed.success) {
      return faultResponse(
        `Validation failed: ${parsed.error.issues.map((i) => i.message).join(", ")}`,
      )
    }

    const input = parsed.data as Record<string, unknown> & { command: string }
    const spec = lookup.get(input.command)
    if (!spec) return faultResponse(`Unknown command: ${input.command}`)

    try {
      const { url, query } = resolveRoute(spec.route, input, spec.queryRenames)
      const result = await request(url, query)
      return gatewayToOutput(result)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      return faultResponse(`${input.command} failed: ${msg}`)
    }
  }

  const compiled: CompiledTool = {
    name: catalog.id,
    description: catalog.summary,
    inputSchema: zodToJsonSchema(union),
    zodInputSchema: union,
    annotations: catalog.hints || { readOnlyHint: true, idempotentHint: true, openWorldHint: true },
    handler,
    premium: catalog.premium,
  }

  if (catalog.outputSchema) {
    compiled.outputSchema = zodToJsonSchema(catalog.outputSchema)
  }

  return compiled
}

// ---------------------------------------------------------------------------
// Compile a StandaloneSpec → CompiledTool
// ---------------------------------------------------------------------------

export function compileStandalone(spec: StandaloneSpec): CompiledTool {
  const handler: ToolHandler = async (args) => {
    const parsed = spec.params.safeParse(args)
    if (!parsed.success) {
      return faultResponse(
        `Validation failed: ${parsed.error.issues.map((i) => i.message).join(", ")}`,
      )
    }

    try {
      const { url, query } = resolveRoute(spec.route, parsed.data as Record<string, unknown>, spec.queryRenames)
      const result = await request(url, query)
      return gatewayToOutput(result)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      return faultResponse(`Request failed: ${msg}`)
    }
  }

  return {
    name: spec.id,
    description: spec.summary,
    inputSchema: zodToJsonSchema(spec.params),
    zodInputSchema: spec.params,
    annotations: spec.hints || { readOnlyHint: true, idempotentHint: true, openWorldHint: true },
    handler,
    premium: spec.premium,
  }
}
