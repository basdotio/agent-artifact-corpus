// WorkspaceIndexer: builds/updates the GNU Global (gtags) index in the background (see the Python twin for rules).
import { existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { type Config, loadConfig, workspaceDataDir } from "./config.js";
import { StaticSightError } from "./core/errors.js";
import * as gnuGlobal from "./engines/gnuGlobal.js";
import { rgFiles } from "./engines/rg.js";

let infoLogs = true;
/** The command line prints the tool's Markdown only; informational indexer messages are for server logs. */
export function setIndexerInfoLogs(on: boolean): void {
  infoLogs = on;
}

function info(msg: string): void {
  if (infoLogs) log(msg);
}

function log(msg: string): void {
  process.stderr.write(`[staticsight.indexer] ${msg}\n`);
}

export class WorkspaceIndexer {
  state: "not_started" | "building" | "ready" | "failed" | "unavailable" = "not_started";
  detail = "";
  dbPath: string | null = null;
  lastBuilt: number | null = null;
  lastDuration: number | null = null;
  private task: Promise<void> | null = null;
  private running = false;

  constructor(public cfg: Config) {}

  get root(): string {
    return this.cfg.workspaceRoot;
  }

  start(): Promise<void> {
    if (!this.running) {
      this.running = true;
      this.task = this.run().finally(() => {
        this.running = false;
      });
    }
    return this.task!;
  }

  async ensureReady(graceS = 2.0): Promise<boolean> {
    if (this.state === "not_started") this.start();
    if ((this.state === "building" || this.state === "not_started") && this.task) {
      await Promise.race([this.task, new Promise((r) => setTimeout(r, graceS * 1000))]);
    }
    if (this.state === "ready" && this.cfg.reindexAfterS && this.lastBuilt) {
      if (Date.now() / 1000 - this.lastBuilt > this.cfg.reindexAfterS && !this.running) this.start();
    }
    return this.state === "ready" || (this.state === "building" && this.lastBuilt !== null);
  }

  env(): Record<string, string> {
    const env: Record<string, string> = { GTAGSFORCECPP: "1", GTAGSROOT: this.root };
    if (this.dbPath !== null) env.GTAGSDBPATH = this.dbPath;
    return env;
  }

  status(): { state: string; detail: string; dbPath: string; ageS: number | null; durationS: number | null } {
    return {
      state: this.state,
      detail: this.detail,
      dbPath: this.dbPath ?? "",
      ageS: this.lastBuilt === null ? null : Math.floor(Date.now() / 1000 - this.lastBuilt),
      durationS: this.lastDuration === null ? null : Math.round(this.lastDuration * 10) / 10,
    };
  }

  private cacheDbPath(): string {
    return workspaceDataDir(this.cfg)[0];
  }

  private async run(): Promise<void> {
    if (!gnuGlobal.available()) {
      this.state = "unavailable";
      this.detail = "GNU Global (`gtags`/`global`) is not installed; graph tools use the ripgrep fallback.";
      log(this.detail);
      return;
    }
    const prev = this.state;
    this.state = "building";
    const started = Date.now() / 1000;
    try {
      let res;
      let action: string;
      if (existsSync(join(this.root, "GTAGS"))) {
        this.dbPath = this.root;
        res = await gnuGlobal.updateInPlace(this.root, this.env());
        action = "global -u (in-repo database)";
      } else {
        if (this.cfg.gtagsInRepo) this.dbPath = this.root;
        else {
          this.dbPath = this.cacheDbPath();
          mkdirSync(this.dbPath, { recursive: true });
        }
        const files = await rgFiles(this.cfg);
        const incremental = existsSync(join(this.dbPath, "GTAGS"));
        [res, action] = await gnuGlobal.build(this.root, this.dbPath, this.env(), files, incremental);
      }
      if (res.returncode !== 0) throw new StaticSightError(`gtags exited with ${res.returncode}: ${res.stderr.trim().slice(0, 300)}`);
      this.state = "ready";
      this.lastBuilt = Date.now() / 1000;
      this.lastDuration = this.lastBuilt - started;
      this.detail = `Indexed via \`${action}\` in ${this.lastDuration.toFixed(1)}s.`;
      info(this.detail);
    } catch (e) {
      if (e instanceof StaticSightError) {
        this.state = prev === "ready" ? "ready" : "failed";
        this.detail = `Indexing failed: ${e.message}`;
      } else {
        this.state = "failed";
        this.detail = `Indexing failed: ${String(e)}`;
      }
      log(this.detail);
    }
  }
}

const indexers = new Map<string, WorkspaceIndexer>();

export function getIndexer(cfg?: Config): WorkspaceIndexer {
  const c = cfg ?? loadConfig();
  let idx = indexers.get(c.workspaceRoot);
  if (!idx) {
    idx = new WorkspaceIndexer(c);
    indexers.set(c.workspaceRoot, idx);
  }
  return idx;
}

export function resetIndexers(): void {
  indexers.clear();
}
