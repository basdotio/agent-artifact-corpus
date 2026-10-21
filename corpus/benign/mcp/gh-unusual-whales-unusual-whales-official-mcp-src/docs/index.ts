/**
 * Dynamic documentation resources served via MCP resource protocol.
 */

import type { CompiledTool } from "../engine.js"

export type DocHandler = () => Promise<string>

export interface DocResource {
  uri: string
  name: string
  description: string
  mimeType: string
}

function buildApiReference(tools: CompiledTool[]): string {
  const toc = tools.map((t, i) => `${i + 1}. [${t.name}](#${t.name.replace(/_/g, "")})`).join("\n")

  const sections = tools.map((tool) => {
    const parts = [
      `## ${tool.name}`, "",
      tool.description, "",
      "### Input Schema", "",
      "```json", JSON.stringify(tool.inputSchema, null, 2), "```", "",
    ]

    if (tool.annotations) {
      const hints: string[] = []
      if (tool.annotations.readOnlyHint) hints.push("- Read-only operation")
      if (tool.annotations.idempotentHint) hints.push("- Idempotent operation")
      if (tool.annotations.openWorldHint) hints.push("- Open world (may return unexpected fields)")
      if (tool.annotations.destructiveHint) hints.push("- Destructive operation")
      if (hints.length > 0) parts.push("### Annotations", "", ...hints, "")
    }

    return parts.join("\n")
  })

  return [
    "# Unusual Whales API Reference", "",
    `${tools.length} tools available.`, "",
    toc, "",
    ...sections,
  ].join("\n")
}

function buildToolsSummary(tools: CompiledTool[]): string {
  return JSON.stringify({
    totalTools: tools.length,
    tools: tools.map((t) => ({
      name: t.name,
      description: t.description.split("\n")[0],
      requiredParameters: t.inputSchema.required || [],
      annotations: t.annotations || {},
    })),
  }, null, 2)
}

export function initializeDocs(tools: CompiledTool[]): {
  resources: DocResource[]
  handlers: Record<string, DocHandler>
} {
  const entries: Array<{ def: DocResource; fn: DocHandler }> = [
    {
      def: {
        uri: "docs://api-reference",
        name: "API Reference",
        description: "Complete reference documentation for all Unusual Whales API tools",
        mimeType: "text/markdown",
      },
      fn: async () => buildApiReference(tools),
    },
    {
      def: {
        uri: "docs://tools-summary",
        name: "Tools Summary",
        description: "Summary of available tools with their actions and parameters",
        mimeType: "application/json",
      },
      fn: async () => buildToolsSummary(tools),
    },
  ]

  return {
    resources: entries.map((e) => e.def),
    handlers: Object.fromEntries(entries.map((e) => [e.def.uri, e.fn])),
  }
}
