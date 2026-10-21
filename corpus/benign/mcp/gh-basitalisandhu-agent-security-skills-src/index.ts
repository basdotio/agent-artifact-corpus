#!/usr/bin/env node
/**
 * agent-incidents: a read-only MCP server over the AI agent incident dataset.
 *
 * Transport: stdio only. It never binds a port and never makes a network request. It reads one JSON
 * file (AGENT_INCIDENTS_DATA, or the plugin's bundled snapshot of site/incidents.json) at start-up and answers:
 *   search_incidents  filter and search the dataset
 *   get_incident      one record in full
 *   stats             counts by field
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { realpathSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { z } from "zod";
import { FILTER_FIELDS, STATS_FIELDS, getIncident, loadDataset, primaryUrl, searchIncidents, stats, type Dataset } from "./data.js";

export const SERVER_NAME = "agent-incidents";
export const SERVER_VERSION = "0.5.0";

function json(value: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(value, null, 1) }] };
}

export function createServer(dataset?: Dataset): McpServer {
  const ds = dataset ?? loadDataset();
  const vocab = (field: (typeof FILTER_FIELDS)[number] | "owasp_agentic" | "vendor") => ds.fields[field]?.join(", ") ?? "";

  const server = new McpServer(
    { name: SERVER_NAME, version: SERVER_VERSION },
    {
      instructions:
        `Read-only access to ${ds.count} publicly documented AI agent security incidents, vulnerability disclosures and threat reports ` +
        `(${ds.date_range?.from} to ${ds.date_range?.to}), coded by vector, input channel, authority held by the agent, output channel and outcome, ` +
        `and mapped to the OWASP Top 10 for Agentic Applications (ASI01..ASI10), the OWASP Top 10 for LLM Applications (LLM01..LLM10) and MITRE ATLAS. ` +
        `Use search_incidents to find precedents for a design or a vulnerability class, get_incident for the full record, and stats for the distribution. ` +
        `Vocabularies: vector [${vocab("vector")}]; channel_in [${vocab("channel_in")}]; authority [${vocab("authority")}]; outcome [${vocab("outcome")}]; ` +
        `owasp_agentic [${vocab("owasp_agentic")}]. Source: ${ds.source} (${ds.licence}). Every record carries its primary source URL; cite it.`,
    },
  );

  const readOnly = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false };
  const filterShape = {
    vector: z.string().max(60).optional(),
    outcome: z.string().max(60).optional(),
    channel_in: z.string().max(60).optional().describe("where untrusted input entered, e.g. 'web page', 'repo issue/pr', 'email'"),
    authority: z.string().max(60).optional().describe("what the agent could do, e.g. 'shell/exec', 'send-message', 'cloud-creds'"),
    channel_out: z.string().max(60).optional(),
    lens: z.enum(["surface", "target", "weapon"]).optional(),
    type: z.enum(["incident", "vulnerability-disclosure", "threat-report"]).optional(),
    vendor: z.string().max(60).optional().describe("substring of affected.vendors or the name, e.g. 'Cursor', 'OpenAI'"),
    product: z.string().max(60).optional().describe("substring of affected.products"),
    framework: z.string().max(60).optional().describe("substring of affected.frameworks, e.g. 'LangChain', 'MCP'"),
    owasp_agentic: z.string().regex(/^ASI(0[1-9]|10)$/).optional().describe("OWASP Agentic Top 10 id, e.g. ASI01"),
    owasp_llm: z.string().regex(/^LLM(0[1-9]|10)$/).optional().describe("OWASP LLM Top 10 id, e.g. LLM01"),
    mitre_atlas: z.string().regex(/^AML\.T\d{4}(\.\d{3})?$/).optional().describe("MITRE ATLAS technique id, e.g. AML.T0051"),
    tag: z.string().max(60).optional(),
    status: z.enum(["confirmed", "reported", "disputed"]).optional(),
    since: z.string().regex(/^\d{4}-\d{2}$/).optional().describe("YYYY-MM inclusive"),
    until: z.string().regex(/^\d{4}-\d{2}$/).optional().describe("YYYY-MM inclusive"),
    cve_only: z.boolean().optional(),
    adversarial: z.boolean().optional(),
  };

  server.registerTool(
    "search_incidents",
    {
      title: "Search AI agent incidents",
      description:
        "Filter the incident dataset. All filters are optional and combine with AND. Coded fields are exact (case-insensitive): " +
        `vector [${vocab("vector")}]; channel_in [${vocab("channel_in")}]; authority [${vocab("authority")}]; outcome [${vocab("outcome")}]. ` +
        "vendor, product, framework and tag are substring matches; owasp_agentic, owasp_llm and mitre_atlas are exact ids; query searches name, summary, sources, affected, tags and CVEs. " +
        "Returns newest first with the total count before the limit and each record's primary source URL.",
      inputSchema: {
        query: z.string().max(200).optional().describe("free-text substring"),
        ...filterShape,
        limit: z.number().int().min(1).max(100).optional().describe("default 20"),
      },
      annotations: readOnly,
    },
    async (input) => {
      const result = searchIncidents(ds, input);
      return json({
        total: result.total,
        returned: result.incidents.length,
        incidents: result.incidents.map((i) => ({
          id: i.id, date: i.date, name: i.name, type: i.type, vector: i.vector, channel_in: i.channel_in, authority: i.authority,
          channel_out: i.channel_out, outcome: i.outcome, cve: i.cve, mappings: i.mappings, affected: i.affected, status: i.status, primary_source: primaryUrl(i),
        })),
      });
    },
  );

  server.registerTool(
    "get_incident",
    {
      title: "Get one incident",
      description: "Return the full record of one incident by id (for example '030' or '30'): coded fields, summary, every source, OWASP and ATLAS mappings, affected vendors, products and frameworks, tags and status.",
      inputSchema: { id: z.string().min(1).max(20) },
      annotations: readOnly,
    },
    async ({ id }) => {
      const found = getIncident(ds, id);
      if (!found) {
        return { content: [{ type: "text" as const, text: `No incident with id ${JSON.stringify(id)}. Ids are zero-padded three-digit strings such as "030".` }], isError: true };
      }
      return json({ ...found, primary_source: primaryUrl(found) });
    },
  );

  server.registerTool(
    "stats",
    {
      title: "Incident statistics",
      description:
        `Count incidents by one field: ${STATS_FIELDS.join(", ")}. Optional filters narrow the set first (same meaning as in search_incidents). ` +
        "Use it to answer 'how common is X' and to describe the dataset.",
      inputSchema: {
        by: z.enum(STATS_FIELDS).optional().describe("default: vector"),
        ...filterShape,
      },
      annotations: readOnly,
    },
    async ({ by, ...filters }) => json({ ...stats(ds, by ?? "vector", filters), date_range: ds.date_range, source: ds.source }),
  );

  return server;
}

async function main(): Promise<void> {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

// Compare real paths: an installed bin (npx, npm i -g) is a symlink, so argv[1] differs from import.meta.url.
function isInvokedDirectly(): boolean {
  const entry = process.argv[1];
  if (entry === undefined) return false;
  try {
    return import.meta.url === pathToFileURL(realpathSync(entry)).href;
  } catch {
    return false;
  }
}

const invokedDirectly = isInvokedDirectly();
if (invokedDirectly) {
  main().catch((err) => {
    console.error(`[agent-incidents] fatal: ${err instanceof Error ? err.message : String(err)}`);
    process.exit(1);
  });
}
