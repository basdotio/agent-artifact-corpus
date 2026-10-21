#!/usr/bin/env node
// StaticSight MCP server entrypoint (TypeScript): tool registration from shared/tool-spec.json, prompt, indexer startup.
import { readFileSync, realpathSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z, type ZodTypeAny } from "zod";
import { loadConfig } from "./config.js";
import * as md from "./core/md.js";
import { StaticSightError } from "./core/errors.js";
import { probeAll } from "./engines/capabilities.js";
import { current as currentPlatform } from "./platform/index.js";
import { getIndexer } from "./indexer.js";
import { get_diff_scopes } from "./tools/diffScopes.js";
import { get_symbol_contract, get_symbol_definition, get_upstream_callers } from "./tools/graphGtags.js";
import { review_changes } from "./tools/review.js";
import { find_similar_code, refresh_semantic_index, semantic_search } from "./tools/semantic.js";
import { statusSection } from "./semantic/search.js";
import { sharedFile as sharedFileImpl } from "./shared.js";
import { get_include_blast_radius, track_struct_risks } from "./tools/ripgrepMem.js";
import { track_state_mutations } from "./tools/stateMutation.js";
import { track_lock_order } from "./tools/lockOrder.js";
import { run_file_static_audit } from "./tools/staticCpp.js";
import { get_branch_skeleton, get_enclosing_scope } from "./tools/syntaxCtags.js";

export interface ParamSpec {
  name: string;
  type: "string" | "integer" | "boolean";
  required?: boolean;
  default?: unknown;
  description: string;
}
export interface ToolSpec {
  name: string;
  description: string;
  params: ParamSpec[];
  annotations?: Record<string, boolean>;
}
interface Spec {
  server: { name: string; instructions: string };
  tools: ToolSpec[];
  prompts: Array<{ name: string; description: string; file: string }>;
}


export function sharedFile(name: string): string | null {
  return sharedFileImpl(name);
}

export function loadSpec(): Spec {
  const p = sharedFile("tool-spec.json");
  if (!p) throw new Error("tool-spec.json not found (run `npm run build`)");
  return JSON.parse(readFileSync(p, "utf8"));
}

export async function get_index_status(): Promise<string> {
  const cfg = loadConfig();
  const st = getIndexer(cfg).status();
  const statuses = await probeAll();
  const engines = statuses.map((e) => `\`${e.name}\` ${e.ok ? "✅" : "❌"}`).join(", ");
  const out = ["### 🗂️ INDEX STATUS", `- **Workspace:** \`${cfg.workspaceRoot}\``, `- **State:** ${st.state}`];
  if (st.detail) out.push(`- **Detail:** ${st.detail}`);
  if (st.dbPath) out.push(`- **Database:** \`${st.dbPath}\``);
  if (st.ageS !== null) out.push(`- **Age:** ${st.ageS}s (auto-refresh after ${cfg.reindexAfterS}s)`);
  out.push(`- **Engines:** ${engines}`);
  out.push(`- **Platform:** ${currentPlatform().name}`);
  for (const e of statuses) {
    if (e.ok && e.version) out.push(`  - \`${e.name}\`: ${e.version}`);
    else if (!e.ok) out.push(`  - \`${e.name}\` (${e.level}): ${e.problem}` + (e.hint ? `. 💡 ${e.hint}` : ""));
  }
  out.push(...(await statusSection(cfg)));
  return out.join("\n");
}

type Handler = (args: any) => Promise<string>;

export const TOOLS: Record<string, Handler> = {
  review_changes,
  get_diff_scopes,
  get_enclosing_scope,
  get_branch_skeleton,
  get_upstream_callers,
  get_symbol_definition,
  get_symbol_contract,
  track_struct_risks,
  get_include_blast_radius,
  track_state_mutations,
  track_lock_order,
  run_file_static_audit,
  semantic_search,
  find_similar_code,
  refresh_semantic_index,
  get_index_status,
};

/** Convert every failure into a Markdown card and enforce the output budget. */
export function safeTool(name: string, fn: Handler): Handler {
  return async (args: any) => {
    const cfg = loadConfig();
    const limit = name === "review_changes" ? cfg.reviewMaxChars : cfg.maxChars;
    let result: string;
    try {
      result = await fn(args ?? {});
    } catch (e) {
      if (e instanceof StaticSightError) return md.errorCard(e.title, e.message, e.hint);
      process.stderr.write(`[staticsight] tool ${name} failed: ${(e as Error)?.stack ?? String(e)}\n`);
      const err = e as Error;
      return md.errorCard("Internal error", `\`${name}\` failed: ${err?.name ?? "Error"}: ${err?.message ?? String(e)}`, "This is a StaticSight bug; the other tools are still usable.");
    }
    return md.enforceBudget(result, limit);
  };
}

function zodFor(p: ParamSpec): ZodTypeAny {
  let t: ZodTypeAny = p.type === "string" ? z.string() : p.type === "integer" ? z.number().int() : z.boolean();
  t = t.describe(p.description);
  if (!p.required) t = t.default(p.default as never);
  return t;
}

export function buildServer(): McpServer {
  const spec = loadSpec();
  const server = new McpServer(
    { name: spec.server.name || "StaticSight", version: "0.1.0" },
    { instructions: spec.server.instructions || undefined },
  );
  for (const ts of spec.tools) {
    const fn = TOOLS[ts.name];
    if (!fn) throw new Error(`tool ${ts.name} from tool-spec.json has no implementation`);
    const shape: Record<string, ZodTypeAny> = {};
    for (const p of ts.params) shape[p.name] = zodFor(p);
    const wrapped = safeTool(ts.name, fn);
    server.registerTool(
      ts.name,
      {
        description: ts.description,
        inputSchema: shape,
        annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false, ...(ts.annotations ?? {}) },
      },
      async (args: Record<string, unknown>) => ({ content: [{ type: "text" as const, text: await wrapped(args) }] }),
    );
  }
  const promptFile = sharedFile("prompts/review_cpp_changes.md");
  const promptText = promptFile ? readFileSync(promptFile, "utf8") : "Review the C++ changes using the StaticSight tools.";
  const ps = spec.prompts.find((p) => p.name === "review_cpp_changes");
  server.registerPrompt(
    "review_cpp_changes",
    { description: ps?.description ?? "", argsSchema: { focus: z.string().optional() } },
    ({ focus }) => {
      const extra = focus && focus.trim() ? `Pay special attention to: ${focus.trim()}.` : "";
      const text = promptText.replace("{focus}", extra).replace(/[ \t]+\n/g, "\n");
      return { messages: [{ role: "user" as const, content: { type: "text" as const, text } }] };
    },
  );
  return server;
}

export async function main(): Promise<void> {
  const server = buildServer();
  await server.connect(new StdioServerTransport());
  void getIndexer(loadConfig()).start(); // background: the MCP handshake must not wait for gtags
}

function isEntrypoint(): boolean {
  if (!process.argv[1]) return false;
  try {
    const self = realpathSync.native(fileURLToPath(import.meta.url));
    const invoked = realpathSync.native(process.argv[1]);
    return currentPlatform().samePath(self, invoked);
  } catch {
    return false;
  }
}

/** Strip a global `--repo PATH` / `--repo=PATH` (any position) and make it the workspace, like WORKSPACE_ROOT. */
export function applyRepoOption(argv: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--repo" || a.startsWith("--repo=")) {
      let val: string;
      if (a === "--repo") {
        if (i + 1 >= argv.length) {
          process.stderr.write("error: --repo needs a folder\n");
          process.exit(2);
        }
        val = argv[++i];
      } else val = a.slice("--repo=".length);
      const p = resolve(val.startsWith("~") ? join(homedir(), val.slice(1)) : val);
      let ok = false;
      try {
        ok = statSync(p).isDirectory();
      } catch {
        ok = false;
      }
      if (!ok) {
        process.stderr.write(`error: --repo ${val}: not a folder\n`);
        process.exit(2);
      }
      process.env.WORKSPACE_ROOT = p;
      continue;
    }
    out.push(a);
  }
  return out;
}

if (isEntrypoint()) process.argv.splice(2, process.argv.length, ...applyRepoOption(process.argv.slice(2)));

if (isEntrypoint() && process.argv[2] === "tool") {
  const { runToolCli } = await import("./toolRun.js");
  process.exitCode = await runToolCli(process.argv.slice(3), { tools: loadSpec().tools, handlers: TOOLS, safeTool });
} else if (isEntrypoint() && process.argv[2] === "doctor") {
  const { runDoctor } = await import("./doctor.js");
  process.exitCode = await runDoctor();
} else if (isEntrypoint() && ["index", "search", "similar", "model", "help", "--help", "-h"].includes(process.argv[2])) {
  const { runCli, USAGE } = await import("./cli.js");
  if (["help", "--help", "-h"].includes(process.argv[2])) process.stdout.write(USAGE + "\n");
  else process.exitCode = await runCli(process.argv.slice(2));
} else if (isEntrypoint()) {
  main().catch((e) => {
    process.stderr.write(`[staticsight] fatal: ${String(e)}\n`);
    process.exit(1);
  });
}
