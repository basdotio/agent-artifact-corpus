// Windows implementation of the platform layer.
import { spawnSync, type SpawnOptions } from "node:child_process";
import { statSync } from "node:fs";
import { homedir } from "node:os";
import { delimiter, join } from "node:path";
import { Platform } from "./base.js";

const HINTS: Record<string, string> = {
  ctags: "Install Universal Ctags (`winget install UniversalCtags.Ctags` or `scoop bucket add extras; scoop install universal-ctags`). Note: `scoop install ctags` is the old Exuberant Ctags without JSON. Or run `scripts\\install.ps1`.",
  rg: "Install ripgrep (`winget install BurntSushi.ripgrep.MSVC` or `scoop install ripgrep`), or run `scripts\\install.ps1`.",
  global: "Install GNU Global (`scoop install global`), or run `scripts\\install.ps1`. Optional: without it StaticSight falls back to ripgrep.",
  gtags: "Install GNU Global (`scoop install global`), or run `scripts\\install.ps1`. Optional: without it StaticSight falls back to ripgrep.",
  cppcheck: "Install cppcheck (`winget install Cppcheck.Cppcheck` or `scoop install cppcheck`), or run `scripts\\install.ps1`.",
  git: "Install Git for Windows (`winget install Git.Git`) and make sure the workspace is a git repository.",
};

// Only real executables: `.cmd`/`.bat` shims would need cmd.exe, which re-introduces shell quoting risks.
const EXTENSIONS = [".exe", ".com"];

export class WindowsPlatform extends Platform {
  readonly name = "windows";
  readonly caseSensitive = false;

  findExecutable(tool: string): string | null {
    const names = EXTENSIONS.some((e) => tool.toLowerCase().endsWith(e)) ? [tool] : EXTENSIONS.map((e) => tool + e);
    for (let dir of (process.env.PATH ?? "").split(delimiter)) {
      dir = dir.trim().replace(/^"|"$/g, "");
      if (!dir) continue;
      for (const n of names) {
        const cand = join(dir, n);
        try {
          if (statSync(cand).isFile()) return cand;
        } catch {
          /* not here */
        }
      }
    }
    return null;
  }

  spawnOptions(): SpawnOptions {
    return { detached: false, windowsHide: true };
  }

  killTree(pid: number | undefined): void {
    if (pid === undefined) return;
    try {
      spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], { windowsHide: true, stdio: "ignore", timeout: 10000 });
    } catch {
      /* fall through */
    }
    try {
      process.kill(pid);
    } catch {
      /* already gone */
    }
  }

  defaultCacheDir(): string {
    const base = process.env.LOCALAPPDATA;
    return join(base ? base : join(homedir(), "AppData", "Local"), "staticsight");
  }

  installHint(tool: string): string | undefined {
    return HINTS[tool];
  }

  toPosix(path: string): string {
    const p = path.replace(/\\/g, "/");
    return p.startsWith("./") ? p.slice(2) : p;
  }
}
