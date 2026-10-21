// `staticsight tool …`: run any MCP tool from the command line and print the exact Markdown an agent would receive.
// Arguments are validated against shared/tool-spec.json. Twin of staticsight-py/src/staticsight/toolrun.py
// (help, errors and output are byte-identical).
import { existsSync } from "node:fs";
import { join } from "node:path";
import { loadConfig, workspaceDataDir } from "./config.js";
import { ensureSemanticBuilt, oneShotSemantic } from "./cli.js";
import { getIndexer, setIndexerInfoLogs } from "./indexer.js";
import { getSemanticIndex } from "./semantic/index.js";
import type { ParamSpec, ToolSpec } from "./server.js";

type Handler = (args: Record<string, unknown>) => Promise<string>;
/** Supplied by server.ts (a static import back into server.ts would deadlock its top-level await). */
export interface ToolHost {
  tools: ToolSpec[];
  handlers: Record<string, Handler>;
  safeTool: (name: string, fn: Handler) => Handler;
}

const SEMANTIC_TOOLS = new Set(["semantic_search", "find_similar_code", "refresh_semantic_index"]);

class UsageError extends Error {}

const q = (v: unknown): string => JSON.stringify(v);

/** --json values must already have the parameter's JSON type (identical rule in toolrun.py). */
function fromJson(p: ParamSpec, v: unknown): unknown {
  const ok =
    p.type === "string" ? typeof v === "string" : p.type === "boolean" ? typeof v === "boolean" : typeof v === "number" && Number.isInteger(v);
  if (!ok) {
    const want = p.type === "string" ? "a string" : p.type === "boolean" ? "true or false" : "an integer";
    throw new UsageError(`${flag(p.name)} expects ${want}, got ${q(v)}`);
  }
  return v;
}
const flag = (name: string): string => "--" + name.replaceAll("_", "-");
const meta = (p: ParamSpec): string => (p.type === "integer" ? "N" : p.type === "boolean" ? "" : "TEXT");
const hasDefault = (p: ParamSpec): boolean => "default" in p;

function synopsis(t: ToolSpec): string {
  const parts = [t.name];
  for (const p of t.params) {
    const f = flag(p.name) + (meta(p) ? ` ${meta(p)}` : "");
    parts.push(hasDefault(p) ? `[${f}]` : f);
  }
  return parts.join(" ");
}

function firstSentence(text: string, limit = 110): string {
  const i = text.indexOf(". ");
  const s = (i >= 0 ? text.slice(0, i) : text).replace(/\.+$/, "") + ".";
  return s.length <= limit ? s : s.slice(0, limit - 1).trimEnd() + "…";
}

export function listText(tools: ToolSpec[]): string {
  const out = [`${tools.length} tools, the same ones the MCP server offers. Details: tool NAME --help`, ""];
  for (const t of tools) out.push(synopsis(t), "    " + firstSentence(t.description));
  out.push(
    "",
    "Required parameters can also be given positionally, in order.",
    "Boolean parameters: --flag (true) or --no-flag (false). --json '{...}' passes raw MCP arguments.",
  );
  return out.join("\n");
}

export function helpText(t: ToolSpec): string {
  const out = [synopsis(t), "", t.description, ""];
  if (!t.params.length) out.push("No parameters.");
  else {
    out.push("Parameters:");
    for (const p of t.params) {
      const left = flag(p.name) + (meta(p) ? ` ${meta(p)}` : "");
      const dflt = hasDefault(p) ? `default ${q(p.default)}` : "required";
      out.push(`  ${left.padEnd(24)} (${p.type}, ${dflt}) ${p.description ?? ""}`.trimEnd());
    }
    const req = t.params.filter((p) => !hasDefault(p)).map((p) => p.name);
    if (req.length) out.push("", "Positional order: " + req.join(" "));
  }
  return out.join("\n");
}

function coerce(p: ParamSpec, raw: unknown): unknown {
  if (p.type === "integer") {
    if (typeof raw === "boolean") throw new UsageError(`${flag(p.name)} expects an integer, got ${q(raw)}`);
    if (typeof raw === "number" && Number.isInteger(raw)) return raw;
    const text = String(raw).trim();
    if (!/^[+-]?[0-9]+$/.test(text)) throw new UsageError(`${flag(p.name)} expects an integer, got ${q(String(raw))}`);
    return Number.parseInt(text, 10);
  }
  if (p.type === "boolean") {
    if (typeof raw === "boolean") return raw;
    const v = String(raw).trim().toLowerCase();
    if (["1", "true", "yes", "on"].includes(v)) return true;
    if (["0", "false", "no", "off"].includes(v)) return false;
    throw new UsageError(`${flag(p.name)} expects true or false, got ${q(String(raw))}`);
  }
  return typeof raw === "string" ? raw : String(raw);
}

export function parseToolArgs(t: ToolSpec, argv: string[]): Record<string, unknown> {
  const params = new Map(t.params.map((p) => [p.name, p]));
  const given: Record<string, unknown> = {};
  const positional: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--json") {
      if (i + 1 >= argv.length) throw new UsageError("--json needs a value");
      let obj: unknown;
      try {
        obj = JSON.parse(argv[i + 1]);
      } catch {
        throw new UsageError("--json is not valid JSON");
      }
      if (typeof obj !== "object" || obj === null || Array.isArray(obj)) throw new UsageError("--json must be a JSON object");
      for (const [k, v] of Object.entries(obj)) {
        const p = params.get(k);
        if (!p) throw new UsageError(`unknown parameter ${q(k)} for ${t.name}`);
        given[k] = fromJson(p, v);
      }
      i++;
      continue;
    }
    if (a.startsWith("--") && a.length > 2) {
      const eqAt = a.indexOf("=", 2);
      const key = eqAt >= 0 ? a.slice(2, eqAt) : a.slice(2);
      const hasEq = eqAt >= 0;
      let val = hasEq ? a.slice(eqAt + 1) : "";
      let name = key.replaceAll("-", "_");
      let neg = false;
      if (!params.has(name) && name.startsWith("no_") && params.get(name.slice(3))?.type === "boolean") {
        name = name.slice(3);
        neg = true;
      }
      const p = params.get(name);
      if (!p) throw new UsageError(`unknown option --${key} for ${t.name} (see: tool ${t.name} --help)`);
      if (p.type === "boolean") {
        given[name] = !hasEq ? !neg : (coerce(p, val) as boolean) !== neg;
        continue;
      }
      if (!hasEq) {
        if (i + 1 >= argv.length) throw new UsageError(`${flag(name)} needs a value`);
        val = argv[++i];
      }
      given[name] = coerce(p, val);
      continue;
    }
    positional.push(a);
  }
  const free = t.params.filter((p) => !hasDefault(p) && !(p.name in given));
  if (positional.length > free.length) {
    throw new UsageError(`too many positional arguments for ${t.name}: ${positional.slice(free.length).join(" ")}`);
  }
  free.forEach((p, k) => {
    if (k < positional.length) given[p.name] = coerce(p, positional[k]);
  });
  const missing = t.params.filter((p) => !hasDefault(p) && !(p.name in given)).map((p) => flag(p.name));
  if (missing.length) throw new UsageError(`${t.name} needs ${missing.join(", ")} (see: tool ${t.name} --help)`);
  return given;
}

/** A one-shot process cannot rely on the server's background indexing: build/update the indexes first. */
async function prepare(name: string): Promise<void> {
  if (SEMANTIC_TOOLS.has(name)) {
    if (name !== "refresh_semantic_index") await ensureSemanticBuilt();
    return;
  }
  const cfg = loadConfig();
  if (!existsSync(join(workspaceDataDir(cfg, false)[0], "GTAGS"))) {
    process.stderr.write("  … building the GNU Global index (first run; large repositories take a few minutes)\n");
  }
  await getIndexer(cfg).start();
}

/** The MCP answer may say a build continues in the background; a one-shot process must not cut it short. */
async function finishBackground(): Promise<void> {
  const idx = getSemanticIndex(loadConfig());
  if (idx.building) {
    process.stderr.write("  … waiting for the background index build to finish (Ctrl+C stops it; it resumes next time)\n");
    await idx.waitForBackground();
  }
}

export async function runToolCli(argv: string[], host: ToolHost): Promise<number> {
  setIndexerInfoLogs(false);
  const tools = host.tools;
  const byName = new Map(tools.map((t) => [t.name, t]));
  if (!argv.length || ["--list", "-l", "list", "-h", "--help", "help"].includes(argv[0])) {
    process.stdout.write(listText(tools) + "\n");
    return 0;
  }
  const [name, ...rest] = argv;
  const t = byName.get(name);
  if (!t) {
    process.stderr.write(`error: unknown tool ${q(name)}. Available: ${[...byName.keys()].join(", ")}\n`);
    return 2;
  }
  if (rest.some((a) => a === "-h" || a === "--help")) {
    process.stdout.write(helpText(t) + "\n");
    return 0;
  }
  let args: Record<string, unknown>;
  try {
    args = parseToolArgs(t, rest);
  } catch (e) {
    if (e instanceof UsageError) {
      process.stderr.write(`error: ${e.message}\n`);
      return 2;
    }
    throw e;
  }
  oneShotSemantic();
  await prepare(name);
  const text = await host.safeTool(name, host.handlers[name])(args);
  if (SEMANTIC_TOOLS.has(name)) await finishBackground();
  process.stdout.write(text + "\n");
  return text.startsWith("### ❌") ? 1 : 0;
}
