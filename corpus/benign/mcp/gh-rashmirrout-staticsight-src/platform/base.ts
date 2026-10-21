// Platform interface. This folder is the ONLY place in StaticSight that knows which OS it runs on.
// Everything above it (engines/, tools/) works with POSIX-style workspace-relative paths and calls run().
import { spawn, type SpawnOptions } from "node:child_process";
import { existsSync } from "node:fs";
import { basename } from "node:path";
import { StaticSightError, ToolTimeout } from "../core/errors.js";
import { fnmatch } from "../core/fnmatch.js";

export const MAX_STDOUT_BYTES = 8 * 1024 * 1024;
export const MAX_STDERR_BYTES = 64 * 1024;

export interface CmdResult {
  argv: string[];
  returncode: number;
  stdout: string;
  stderr: string;
  truncated: boolean;
}

export interface RunOptions {
  cwd: string;
  timeout: number;
  env?: Record<string, string>;
  stdinData?: string;
  maxBytes?: number;
  displayName?: string;
}

export abstract class Platform {
  abstract readonly name: string;
  abstract readonly caseSensitive: boolean;

  /** Absolute path of a runnable executable for `tool`, or null. */
  abstract findExecutable(tool: string): string | null;
  /** Extra spawn options (process group, hidden window, ...). */
  abstract spawnOptions(): SpawnOptions;
  /** Forcefully terminate a process and all of its children. */
  abstract killTree(pid: number | undefined): void;
  /** Per-user cache directory for StaticSight data (GNU Global databases). */
  abstract defaultCacheDir(): string;
  /** How to install `tool` on this OS. */
  abstract installHint(tool: string): string | undefined;
  /** Convert a path printed by a native tool into StaticSight's internal '/'-separated form. */
  abstract toPosix(path: string): string;

  pathKey(path: string): string {
    const p = this.toPosix(path);
    return this.caseSensitive ? p : p.toLowerCase();
  }

  samePath(a: string, b: string): boolean {
    return this.pathKey(a) === this.pathKey(b);
  }

  fnmatch(name: string, pattern: string): boolean {
    return this.caseSensitive ? fnmatch(name, pattern) : fnmatch(name.toLowerCase(), pattern.toLowerCase());
  }

  /** Run `exe args...` without a shell. Non-zero exit codes are returned, not raised. */
  run(exe: string, args: string[], opts: RunOptions): Promise<CmdResult> {
    const name = opts.displayName || basename(exe);
    const argv = [exe, ...args.map(String)];
    if (!existsSync(opts.cwd)) return Promise.reject(new StaticSightError(`Working directory \`${opts.cwd}\` does not exist.`));
    const maxBytes = opts.maxBytes ?? MAX_STDOUT_BYTES;
    return new Promise((resolvePromise, reject) => {
      const child = spawn(exe, args, {
        ...this.spawnOptions(),
        cwd: opts.cwd,
        env: { ...process.env, ...(opts.env ?? {}) },
        stdio: [opts.stdinData !== undefined ? "pipe" : "ignore", "pipe", "pipe"],
        shell: false,
      });
      const out: Buffer[] = [];
      const err: Buffer[] = [];
      let outSize = 0;
      let errSize = 0;
      let truncated = false;
      let timedOut = false;
      let settled = false;
      const timer = setTimeout(() => {
        timedOut = true;
        this.killTree(child.pid);
      }, opts.timeout * 1000);
      child.stdout!.on("data", (chunk: Buffer) => {
        if (truncated) return;
        if (outSize + chunk.length >= maxBytes) {
          out.push(chunk.subarray(0, maxBytes - outSize));
          outSize = maxBytes;
          truncated = true;
          this.killTree(child.pid);
          return;
        }
        out.push(chunk);
        outSize += chunk.length;
      });
      child.stderr!.on("data", (chunk: Buffer) => {
        if (errSize < MAX_STDERR_BYTES) {
          err.push(chunk.subarray(0, MAX_STDERR_BYTES - errSize));
          errSize += chunk.length;
        }
      });
      child.on("error", (e: NodeJS.ErrnoException) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        const failure = new StaticSightError(`\`${name}\` could not start: ${e.message}`);
        (failure as StaticSightError & { code?: string }).code = e.code;
        reject(failure);
      });
      if (opts.stdinData !== undefined && child.stdin) {
        child.stdin.on("error", () => undefined);
        child.stdin.end(opts.stdinData);
      }
      child.on("close", (code) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (timedOut && !truncated) {
          reject(new ToolTimeout(`\`${name}\` did not finish within ${opts.timeout}s.`, "Narrow the query (path_glob / file_path) or raise STATICSIGHT_TIMEOUT."));
          return;
        }
        resolvePromise({
          argv,
          returncode: truncated ? 0 : code ?? -1,
          stdout: Buffer.concat(out).toString("utf8"),
          stderr: Buffer.concat(err).toString("utf8"),
          truncated,
        });
      });
    });
  }
}
