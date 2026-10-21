// `staticsight-ts doctor`: verify engines and workspace before connecting an MCP client.
import { accessSync, constants, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { type Config, loadConfig, workspaceDataDir } from "./config.js";
import { StaticSightError } from "./core/errors.js";
import { dependenciesOk, missingModelFiles, modelDir, modelId } from "./engines/embedder.js";
import { PURPOSE, probeAll } from "./engines/capabilities.js";
import { current } from "./platform/index.js";

async function semanticLines(cfg: Config): Promise<string[]> {
  if (cfg.embedModel === "test-hash" && !cfg.embedModelDir) return ["  OK   model     test-hash (tests only)"];
  const out: string[] = [];
  try {
    await dependenciesOk();
    out.push("  OK   packages  onnxruntime-node, @huggingface/tokenizers");
  } catch (e) {
    if (!(e instanceof StaticSightError)) throw e;
    out.push(`  WARN packages  ${e.message}`);
    if (e.hint) out.push(`       fix: ${e.hint}`);
    return out;
  }
  let missing: string[];
  try {
    missing = await missingModelFiles(cfg);
  } catch (e) {
    if (!(e instanceof StaticSightError)) throw e;
    return [...out, `  WARN model     ${e.message}`];
  }
  if (missing.length) {
    out.push(`  WARN model     ${modelId(cfg)} not downloaded (${missing.length} file(s) missing)`);
    out.push("       fix: downloaded automatically on first use, or run `staticsight-ts model download` (offline: STATICSIGHT_EMBED_MODEL_DIR)");
  } else out.push(`  OK   model     ${modelId(cfg)} (${modelDir(cfg)})`);
  return out;
}

export async function doctorReport(): Promise<[string, number]> {
  const cfg = loadConfig();
  const statuses = await probeAll();
  const lines = [
    "StaticSight doctor",
    `Platform:  ${current().name}`,
    `Runtime:   Node ${process.version} (${process.execPath})`,
    `Workspace: ${cfg.workspaceRoot}`,
  ];
  const isGit = existsSync(join(cfg.workspaceRoot, ".git"));
  lines.push(`  ${isGit ? "OK  " : "WARN"} git repository` + (isGit ? "" : " not found (diff tools need one)"));
  let probeDir = cfg.cacheDir;
  while (!existsSync(probeDir) && dirname(probeDir) !== probeDir) probeDir = dirname(probeDir); // never create anything
  let writable = true;
  try {
    accessSync(probeDir, constants.W_OK);
  } catch {
    writable = false;
  }
  const [data, why] = workspaceDataDir(cfg, false);
  lines.push(`Cache:     ${cfg.cacheDir} (${writable ? "writable" : "NOT writable"}; models)`, `Data:      ${data} (${why}; indexes)`, "", "Engines:");
  let exitCode = 0;
  for (const st of statuses) {
    let mark = "OK  ";
    if (!st.ok && st.level === "required") {
      mark = "FAIL";
      exitCode = 1;
    } else if (!st.ok) mark = "WARN";
    lines.push(`  ${mark} ${st.name.padEnd(9)} [${st.level}] ${st.ok ? st.version : st.problem}`);
    lines.push(`       used for: ${PURPOSE[st.name] ?? ""}`);
    if (!st.ok && st.hint) lines.push(`       fix: ${st.hint}`);
  }
  lines.push("", "Semantic search (optional):", ...(await semanticLines(cfg)));
  lines.push("", "Result: " + (exitCode === 0 ? "all required engines OK" : "missing or unusable required engines (see FAIL)"));
  return [lines.join("\n"), exitCode];
}

export async function runDoctor(): Promise<number> {
  const [text, code] = await doctorReport();
  process.stdout.write(text + "\n");
  return code;
}
