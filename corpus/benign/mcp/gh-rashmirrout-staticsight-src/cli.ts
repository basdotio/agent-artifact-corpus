// Command-line entry points besides the MCP server: semantic index management, search, model download.
import { loadConfig } from "./config.js";
import { StaticSightError } from "./core/errors.js";
import { downloadModel, missingModelFiles, modelDir, modelId } from "./engines/embedder.js";
import { getSemanticIndex } from "./semantic/index.js";
import { semanticSearchReport, similarCodeReport, statusSection } from "./semantic/search.js";

export const USAGE = `staticsight-ts [COMMAND]

  (no command)                                   run the MCP server (stdio)
  doctor                                         check engines and workspace
  index build [--full]                           build/refresh the semantic index (blocking, with progress)
  index refresh                                  incremental refresh (only changed files)
  index status                                   show semantic index status
  search "query" [--glob G] [--language L] [--kind K] [--top N]
  similar FILE LINE [--end N] [--top N]
  model download | status                        fetch / verify the pinned embedding model
  tool --list                                    list the 16 review tools and their parameters
  tool NAME [ARGS] [--param VALUE ...]           run one tool, print the Markdown an agent receives

Global option: --repo PATH selects the repository (same as WORKSPACE_ROOT). Default: the nearest folder above
the current directory that holds .staticsight/ or .git. Indexes live in <repo>/.staticsight/ (git-ignored).`;

const progress = (m: string) => process.stderr.write(`  … ${m}\n`);

/**
 * A command-line process exits after one answer, so a background refresh would die with it: refresh in the
 * foreground instead, whatever the drift (the MCP server keeps its 200-file threshold).
 */
export function oneShotSemantic(): void {
  process.env.STATICSIGHT_SEMANTIC_AUTO_REFRESH_FILES = String(10 ** 9);
}

/** First use in a terminal: build the index now, with progress, instead of answering keyword-only. */
export async function ensureSemanticBuilt(): Promise<void> {
  const cfg = loadConfig();
  const idx = getSemanticIndex(cfg);
  if (!cfg.semanticAutoRefresh || (idx.exists() && idx.compatible())) return;
  progress("building the semantic index (first run in this repository)");
  try {
    await idx.refresh(false, progress);
  } catch (e) {
    if (!(e instanceof StaticSightError)) throw e; // the tool itself reports what is missing
  }
}

function opt(argv: string[], name: string, dflt: string): string {
  const i = argv.indexOf(name);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : dflt;
}

function positional(argv: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith("--")) {
      if (argv[i] !== "--full") i++;
      continue;
    }
    out.push(argv[i]);
  }
  return out;
}

export async function runCli(argv: string[]): Promise<number> {
  const [cmd, ...rest] = argv;
  const pos = positional(rest);
  oneShotSemantic();
  try {
    if ((cmd === "search" && pos[0]) || (cmd === "similar" && pos[0] && pos[1])) await ensureSemanticBuilt();
    const cfg = loadConfig();
    if (cmd === "index") {
      const action = pos[0];
      if (action === "build" || action === "refresh") {
        const idx = getSemanticIndex(cfg);
        process.stderr.write(`Semantic index for ${cfg.workspaceRoot}\n`);
        let last = "";
        const timer = setInterval(() => {
          const n = idx.progressNote(true);
          if (n !== last && idx.state.status === "building") {
            progress(n);
            last = n;
          }
        }, 2000);
        try {
          process.stdout.write((await idx.refresh(rest.includes("--full"), progress)) + "\n");
        } finally {
          clearInterval(timer);
        }
        return 0;
      }
      if (action === "status") {
        process.stdout.write((await statusSection(cfg)).join("\n").trim() + "\n");
        return 0;
      }
    } else if (cmd === "search" && pos[0]) {
      process.stdout.write(
        (await semanticSearchReport(cfg, pos[0], opt(rest, "--glob", ""), opt(rest, "--language", ""), opt(rest, "--kind", ""), Number(opt(rest, "--top", "10")))) + "\n",
      );
      return 0;
    } else if (cmd === "similar" && pos[0] && pos[1]) {
      process.stdout.write((await similarCodeReport(cfg, pos[0], Number(pos[1]), Number(opt(rest, "--end", "0")), Number(opt(rest, "--top", "8")))) + "\n");
      return 0;
    } else if (cmd === "model" && (pos[0] === "download" || pos[0] === "status")) {
      if (cfg.embedModel === "test-hash" && !cfg.embedModelDir) {
        process.stdout.write("test-hash needs no download\n");
        return 0;
      }
      if (pos[0] === "download") {
        const d = await downloadModel(cfg, progress);
        process.stdout.write(`model ${modelId(cfg)} ready in ${d}\n`);
        return 0;
      }
      const missing = await missingModelFiles(cfg);
      process.stdout.write(`model ${modelId(cfg)} in ${modelDir(cfg)}: ` + (missing.length ? "missing " + missing.join(", ") : "OK (verified)") + "\n");
      return missing.length ? 1 : 0;
    }
  } catch (e) {
    if (e instanceof StaticSightError) {
      process.stderr.write(`error: ${e.message}` + (e.hint ? `\nhint: ${e.hint}` : "") + "\n");
      return 1;
    }
    throw e;
  }
  process.stdout.write(USAGE + "\n");
  return 2;
}
