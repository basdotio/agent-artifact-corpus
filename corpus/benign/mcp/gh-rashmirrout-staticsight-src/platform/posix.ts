// Linux / macOS implementation of the platform layer.
import type { SpawnOptions } from "node:child_process";
import { accessSync, constants, statSync } from "node:fs";
import { homedir } from "node:os";
import { delimiter, join } from "node:path";
import { Platform } from "./base.js";

const HINTS: Record<string, string> = {
  ctags: "Install Universal Ctags >= 5.9 with JSON support (`apt-get install universal-ctags`, `tdnf install ctags`, `brew install universal-ctags`), or run `scripts/install.sh`.",
  rg: "Install ripgrep (`apt-get install ripgrep`, `tdnf install ripgrep`, `brew install ripgrep`), or run `scripts/install.sh`.",
  global: "Install GNU Global (`apt-get install global`, `brew install global`, or build from https://www.gnu.org/software/global/), or run `scripts/install.sh`.",
  gtags: "Install GNU Global (`apt-get install global`, `brew install global`, or build from https://www.gnu.org/software/global/), or run `scripts/install.sh`.",
  cppcheck: "Install cppcheck (`apt-get install cppcheck`, `tdnf install cppcheck`, `brew install cppcheck`), or run `scripts/install.sh`.",
  git: "Install git and make sure the workspace is a git repository.",
};

export class PosixPlatform extends Platform {
  readonly name = "posix";
  readonly caseSensitive = true;

  findExecutable(tool: string): string | null {
    for (const dir of (process.env.PATH ?? "").split(delimiter)) {
      if (!dir) continue;
      const cand = join(dir, tool);
      try {
        if (statSync(cand).isFile()) {
          accessSync(cand, constants.X_OK);
          return cand;
        }
      } catch {
        /* not here / not executable */
      }
    }
    return null;
  }

  spawnOptions(): SpawnOptions {
    return { detached: true }; // own process group so killTree reaches grandchildren
  }

  killTree(pid: number | undefined): void {
    if (pid === undefined) return;
    try {
      process.kill(-pid, "SIGKILL");
    } catch {
      try {
        process.kill(pid, "SIGKILL");
      } catch {
        /* already gone */
      }
    }
  }

  defaultCacheDir(): string {
    const xdg = process.env.XDG_CACHE_HOME;
    return join(xdg ? xdg : join(homedir(), ".cache"), "staticsight");
  }

  installHint(tool: string): string | undefined {
    return HINTS[tool];
  }

  toPosix(path: string): string {
    // A backslash is a legal file-name character on POSIX, so paths are returned unchanged.
    return path.startsWith("./") ? path.slice(2) : path;
  }
}
