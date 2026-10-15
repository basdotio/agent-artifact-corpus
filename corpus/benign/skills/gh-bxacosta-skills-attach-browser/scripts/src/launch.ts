/**
 * Dedicated-browser mode: launch a Chromium browser with its OWN profile and
 * remote debugging enabled by flag. No approval dialog, no user interaction,
 * but none of the user's sessions/cookies either (unless you log in once and
 * reuse the same profile dir).
 *
 * `--remote-debugging-port` is ignored on the default user data dir since
 * Chrome 136, so a non-default `--user-data-dir` is mandatory.
 */

import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, rm } from "node:fs/promises";
import { join } from "node:path";
import type { Platform } from "./browsers.ts";
import { CdpClient } from "./cdp-client.ts";
import { readActivePort } from "./discovery.ts";

type Env = Record<string, string | undefined>;

/** Candidate executable paths per browser id and platform. First existing wins. */
function executableCandidates(id: string, platform: Platform, env: Env): string[] {
  const pf = env.ProgramFiles ?? "C:\\Program Files";
  const pf86 = env["ProgramFiles(x86)"] ?? "C:\\Program Files (x86)";
  const la = env.LOCALAPPDATA ?? "";
  const table: Record<string, Partial<Record<Platform, string[]>>> = {
    chrome: {
      win32: [`${pf}\\Google\\Chrome\\Application\\chrome.exe`, `${pf86}\\Google\\Chrome\\Application\\chrome.exe`, `${la}\\Google\\Chrome\\Application\\chrome.exe`],
      darwin: ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
      linux: ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/opt/google/chrome/chrome"],
    },
    edge: {
      win32: [`${pf86}\\Microsoft\\Edge\\Application\\msedge.exe`, `${pf}\\Microsoft\\Edge\\Application\\msedge.exe`],
      darwin: ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
      linux: ["/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable", "/opt/microsoft/msedge/msedge"],
    },
    brave: {
      win32: [`${pf}\\BraveSoftware\\Brave-Browser\\Application\\brave.exe`, `${la}\\BraveSoftware\\Brave-Browser\\Application\\brave.exe`],
      darwin: ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
      linux: ["/usr/bin/brave-browser", "/usr/bin/brave", "/opt/brave.com/brave/brave"],
    },
    chromium: {
      win32: [`${la}\\Chromium\\Application\\chrome.exe`],
      darwin: ["/Applications/Chromium.app/Contents/MacOS/Chromium"],
      linux: ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium"],
    },
  };
  return table[id]?.[platform] ?? [];
}

export function findExecutable(
  id: string,
  platform: Platform = process.platform as Platform,
  env: Env = process.env,
): string | null {
  return executableCandidates(id, platform, env).find((p) => existsSync(p)) ?? null;
}

export interface LaunchOptions {
  /** Browser executable. Use `findExecutable("chrome")` or pass an explicit path. */
  executablePath: string;
  /** Dedicated profile dir. Reuse the same dir to keep logins between runs. */
  userDataDir: string;
  /** 0 = let the browser pick a free port (recommended; read it from DevToolsActivePort). */
  port?: number;
  headless?: boolean;
  /** Extra flags, e.g. ["--window-size=1280,800"]. */
  args?: string[];
  /** URL to open on start. */
  url?: string;
  /** Max time to wait for the debugging endpoint. */
  timeoutMs?: number;
}

export interface LaunchedBrowser {
  process: ChildProcess;
  port: number;
  endpoint: string;
  /** Closes the browser we launched (kills the process if it does not exit). */
  close: () => Promise<void>;
}

export async function launchDedicated(opts: LaunchOptions): Promise<LaunchedBrowser> {
  const { executablePath, userDataDir, port = 0, headless = false, args = [], url = "about:blank", timeoutMs = 30_000 } = opts;

  await mkdir(userDataDir, { recursive: true });
  // The profile is ours: remove a stale port file so we never read the previous run's port.
  await rm(join(userDataDir, "DevToolsActivePort"), { force: true });

  const flags = [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    ...(headless ? ["--headless=new"] : []),
    ...args,
    url,
  ];
  const child = spawn(executablePath, flags, { stdio: "ignore" });

  let exited = false;
  child.once("exit", () => (exited = true));

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (exited) {
      throw new Error(
        `Browser exited before opening the debugging port. If an instance with the same --user-data-dir ` +
          `is already running, the launch is handed to it and the flag is ignored.`,
      );
    }
    const active = await readActivePort(userDataDir);
    if (active) {
      const endpoint = `ws://127.0.0.1:${active.port}${active.browserPath}`;
      return { process: child, port: active.port, endpoint, close: () => closeGracefully(child, endpoint) };
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  child.kill();
  throw new Error(`Timed out after ${timeoutMs} ms waiting for DevToolsActivePort in ${userDataDir}`);
}

/**
 * Graceful shutdown: `Browser.close` lets the browser flush cookies/profile to disk.
 * Killing the process is the fallback only (it can lose recent profile writes).
 * Allowed here because WE launched this browser; never do this to the user's browser.
 */
// Edge can take >5 s to exit after Browser.close on a fresh profile; 10 s avoids killing a clean shutdown.
async function closeGracefully(child: ChildProcess, endpoint: string, graceMs = 10_000): Promise<void> {
  if (child.exitCode !== null) return;
  const exited = new Promise<void>((r) => child.once("exit", () => r()));
  try {
    const cdp = await CdpClient.connect(endpoint, { connectTimeoutMs: 3_000 });
    await cdp.send("Browser.close", undefined, { timeoutMs: 3_000 }).catch(() => {});
  } catch {
    child.kill();
  }
  const timer = new Promise<"timeout">((r) => setTimeout(() => r("timeout"), graceMs));
  if ((await Promise.race([exited, timer])) === "timeout") child.kill("SIGKILL");
}
