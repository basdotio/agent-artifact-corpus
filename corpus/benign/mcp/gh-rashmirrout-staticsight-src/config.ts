// Runtime configuration, read from environment variables on every call so tests and clients can override it.
import { createHash, randomBytes } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, realpathSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { current as currentPlatform } from "./platform/index.js";

export const CPP_EXTENSIONS = [
  ".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hh", ".hpp", ".hxx", ".h++", ".inl", ".ipp", ".tpp", ".tcc",
];
export const HEADER_EXTENSIONS = [".h", ".hh", ".hpp", ".hxx", ".h++", ".inl", ".ipp", ".tpp", ".tcc"];
export const CPP_GLOBS = CPP_EXTENSIONS.map((e) => `*${e}`);

export const DEFAULT_EXCLUDES = [
  "**/.git/**",
  "**/build/**",
  "**/out/**",
  "**/third_party/**",
  "**/external/**",
  "**/node_modules/**",
  "*.pb.h",
  "*.pb.cc",
  "**/.staticsight/**",
];
export const DATA_DIR_NAME = ".staticsight";
const DATA_GITIGNORE = "# StaticSight data (indexes); safe to delete, rebuilt on demand. Ignores itself.\n*\n";

export interface Config {
  workspaceRoot: string;
  maxResults: number;
  maxChars: number;
  reviewMaxChars: number;
  timeoutS: number;
  cppcheckTimeoutS: number;
  baseRef: string;
  excludes: string[];
  gtagsInRepo: boolean;
  cacheDir: string;
  reindexAfterS: number;
  embedModel: string;
  embedModelDir: string;
  semanticAutoRefresh: boolean;
  semanticAutoRefreshFiles: number;
  semanticMaxFileKb: number;
  semanticAllowDownload: boolean;
  embedBatch: number;
  embedThreads: number;
  dataDirMode: string; // repo | cache | <absolute path>
  rootExplicit: boolean; // WORKSPACE_ROOT / --repo given (vs discovered from the current folder)
}

function boolEnv(name: string, dflt: boolean): boolean {
  const raw = (process.env[name] ?? "").trim().toLowerCase();
  if (!raw) return dflt;
  return !["0", "false", "no", "off"].includes(raw);
}

function intEnv(name: string, dflt: number): number {
  const raw = (process.env[name] ?? "").trim();
  if (!raw) return dflt;
  if (!/^[+-]?\d+$/.test(raw)) return dflt;
  return parseInt(raw, 10);
}

function realpathOr(p: string): string {
  try {
    return realpathSync.native(p);
  } catch {
    return resolve(p);
  }
}

/** Nearest folder at or above `start` holding `.staticsight/` or `.git` (dir, or file in worktrees); else `start`. */
export function findRepoRoot(start: string): string {
  let cur = realpathOr(resolve(start));
  const first = cur;
  for (;;) {
    let isData = false;
    try {
      isData = statSync(join(cur, DATA_DIR_NAME)).isDirectory();
    } catch {
      isData = false;
    }
    if (isData || existsSync(join(cur, ".git"))) return cur;
    const parent = dirname(cur);
    if (parent === cur) return first;
    cur = parent;
  }
}

export function loadConfig(): Config {
  const explicit = process.env.WORKSPACE_ROOT;
  let root: string;
  if (explicit) {
    root = explicit.startsWith("~") ? join(homedir(), explicit.slice(1)) : explicit;
    root = realpathOr(resolve(root));
  } else root = findRepoRoot(process.cwd());
  const extra = (process.env.STATICSIGHT_EXCLUDES ?? "")
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
  const ignoreFile = join(root, ".staticsightignore");
  try {
    if (existsSync(ignoreFile) && statSync(ignoreFile).isFile()) {
      for (const ln of readFileSync(ignoreFile, "utf8").split(/\r?\n/)) {
        const t = ln.trim();
        if (t && !t.startsWith("#")) extra.push(t);
      }
    }
  } catch {
    /* ignore */
  }
  const cache = process.env.STATICSIGHT_CACHE_DIR;
  return {
    workspaceRoot: root,
    maxResults: Math.max(1, intEnv("STATICSIGHT_MAX_RESULTS", 15)),
    maxChars: Math.max(500, intEnv("STATICSIGHT_MAX_CHARS", 6000)),
    reviewMaxChars: Math.max(1000, intEnv("STATICSIGHT_REVIEW_MAX_CHARS", 16000)),
    timeoutS: Math.max(1, intEnv("STATICSIGHT_TIMEOUT", 20)),
    cppcheckTimeoutS: Math.max(1, intEnv("STATICSIGHT_CPPCHECK_TIMEOUT", 60)),
    baseRef: (process.env.STATICSIGHT_BASE_REF ?? "").trim(),
    excludes: [...DEFAULT_EXCLUDES, ...extra],
    gtagsInRepo: ["1", "true", "yes"].includes(process.env.STATICSIGHT_GTAGS_IN_REPO ?? ""),
    cacheDir: cache ? (cache.startsWith("~") ? join(homedir(), cache.slice(1)) : cache) : currentPlatform().defaultCacheDir(),
    reindexAfterS: Math.max(0, intEnv("STATICSIGHT_REINDEX_SECONDS", 300)),
    embedModel: (process.env.STATICSIGHT_EMBED_MODEL ?? "").trim() || "jina-code",
    embedModelDir: (process.env.STATICSIGHT_EMBED_MODEL_DIR ?? "").trim(),
    semanticAutoRefresh: boolEnv("STATICSIGHT_SEMANTIC_AUTO_REFRESH", true),
    semanticAutoRefreshFiles: Math.max(0, intEnv("STATICSIGHT_SEMANTIC_AUTO_REFRESH_FILES", 200)),
    semanticMaxFileKb: Math.max(1, intEnv("STATICSIGHT_SEMANTIC_MAX_FILE_KB", 512)),
    semanticAllowDownload: boolEnv("STATICSIGHT_SEMANTIC_ALLOW_DOWNLOAD", true),
    embedBatch: Math.max(1, intEnv("STATICSIGHT_EMBED_BATCH", 16)),
    embedThreads: Math.max(0, intEnv("STATICSIGHT_EMBED_THREADS", 0)),
    dataDirMode: (process.env.STATICSIGHT_DATA_DIR ?? "").trim() || "repo",
    rootExplicit: Boolean(explicit),
  };
}

/** Per-workspace folder inside the per-user cache (the `cache` data mode, and the legacy location). */
export function workspaceCacheDir(cfg: Config): string {
  const digest = createHash("sha1").update(currentPlatform().pathKey(cfg.workspaceRoot)).digest("hex").slice(0, 16);
  return join(cfg.cacheDir, digest);
}

export function isCppFile(path: string): boolean {
  const p = path.toLowerCase();
  return CPP_EXTENSIONS.some((e) => p.endsWith(e));
}

export function isHeader(path: string): boolean {
  const p = path.toLowerCase();
  return HEADER_EXTENSIONS.some((e) => p.endsWith(e));
}

function ensureRepoDataDir(d: string): boolean {
  try {
    mkdirSync(d, { recursive: true });
    const gi = join(d, ".gitignore");
    if (!existsSync(gi)) writeFileSync(gi, DATA_GITIGNORE, "utf8");
    const probe = join(d, `.write-test-${process.pid}-${randomBytes(4).toString("hex")}`);
    writeFileSync(probe, "x");
    try {
      unlinkSync(probe);
    } catch {
      /* another process may race on cleanup; the write succeeded */
    }
    return true;
  } catch {
    return false;
  }
}

const LEGACY_FILES = ["semantic.db", "semantic.db-wal", "semantic.db-shm", "GTAGS", "GRTAGS", "GPATH"];

/** Move indexes built by older versions (per-user cache) into `.staticsight/` instead of rebuilding them. */
function migrateLegacy(cfg: Config, d: string): void {
  const old = workspaceCacheDir(cfg);
  if (!existsSync(old) || existsSync(join(d, "semantic.db")) || existsSync(join(d, "GTAGS"))) return;
  for (const name of LEGACY_FILES) {
    const src = join(old, name);
    if (existsSync(src)) {
      try {
        renameSync(src, join(d, name));
      } catch {
        /* cross-device or locked: leave it, the index is rebuilt */
      }
    }
  }
}

/**
 * Where per-repository data (GNU Global database, semantic index) lives, and why. Default `<repo>/.staticsight/`
 * (one index per clone/worktree, ignored by git through its own .gitignore); STATICSIGHT_DATA_DIR=cache keeps data in
 * the per-user cache; any other value is an explicit folder. A read-only repository falls back to the per-user cache.
 */
export function workspaceDataDir(cfg: Config, create = true): [string, string] {
  const mode = cfg.dataDirMode;
  if (mode === "cache") return [workspaceCacheDir(cfg), "per-user cache (STATICSIGHT_DATA_DIR=cache)"];
  if (mode !== "repo") {
    // one sub-folder per repository, so a user-wide setting never mixes indexes of different repositories
    const base = resolve(mode.startsWith("~") ? join(homedir(), mode.slice(1)) : mode);
    return [join(base, basename(workspaceCacheDir(cfg))), "STATICSIGHT_DATA_DIR"];
  }
  const d = join(cfg.workspaceRoot, DATA_DIR_NAME);
  if (!create && existsSync(d)) return [d, "repository"];
  if (!(existsSync(d) || cfg.rootExplicit || existsSync(join(cfg.workspaceRoot, ".git")))) {
    // a folder that is not a repository (e.g. $HOME as an MCP server's start folder) gets no .staticsight/,
    // which would otherwise become a repository-root marker for everything below it
    return [workspaceCacheDir(cfg), "per-user cache (not a git repository)"];
  }
  if (!create) return [d, "repository (not created yet)"];
  if (ensureRepoDataDir(d)) {
    migrateLegacy(cfg, d);
    return [d, "repository"];
  }
  return [workspaceCacheDir(cfg), "per-user cache (repository is not writable)"];
}
