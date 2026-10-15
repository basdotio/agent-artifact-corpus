/**
 * Endpoint discovery WITHOUT opening a CDP connection.
 *
 * Opening a WebSocket to a browser in "approval mode" (chrome://inspect toggle)
 * pops the "Allow remote debugging?" dialog. Everything in this module only
 * reads local files and does a raw TCP connect, which does NOT trigger the
 * dialog — so it is safe to call as often as you like.
 */

import { readFile, stat } from "node:fs/promises";
import { connect as tcpConnect } from "node:net";
import { join } from "node:path";
import { knownBrowsers, type BrowserProfile } from "./browsers.ts";

export interface ActivePort {
  port: number;
  /** Browser target path, e.g. "/devtools/browser/<uuid>". */
  browserPath: string;
  /** When the browser last wrote the file (helps spot stale files). */
  writtenAt: Date;
}

export type EndpointState =
  /** No DevToolsActivePort file: debugging never enabled, or never launched with it. */
  | "no-port-file"
  /** File exists but nothing listens on that port: browser closed or toggle off (stale file). */
  | "not-listening"
  /** Something listens on the port: connect to `endpoint` (expect the Allow dialog). */
  | "listening";

export interface Inspection {
  browser: BrowserProfile;
  /** Whether the user data dir exists at all (≈ browser installed and used). */
  installed: boolean;
  /**
   * The chrome://inspect "Allow remote debugging for this browser instance" toggle,
   * read from `Local State`. `undefined` when the key is absent (never touched,
   * or a browser build without the feature).
   */
  toggleEnabled: boolean | undefined;
  activePort: ActivePort | null;
  state: EndpointState;
  /** Browser-level WebSocket URL, present when state === "listening". */
  endpoint?: string;
}

export interface DiscoverOptions {
  host?: string;
  /** Timeout for the TCP liveness probe. Local probes answer in <5 ms. */
  probeTimeoutMs?: number;
}

/**
 * Parse `DevToolsActivePort`: line 1 = port, line 2 = browser target path.
 * Returns null when the file is missing or malformed.
 */
export async function readActivePort(userDataDir: string): Promise<ActivePort | null> {
  const file = join(userDataDir, "DevToolsActivePort");
  try {
    const [text, info] = await Promise.all([readFile(file, "utf8"), stat(file)]);
    const [portLine, pathLine] = text.split(/\r?\n/).map((l) => l.trim());
    const port = Number(portLine);
    if (!Number.isInteger(port) || port <= 0 || port > 65535) return null;
    if (!pathLine?.startsWith("/devtools/browser")) return null;
    return { port, browserPath: pathLine, writtenAt: info.mtime };
  } catch {
    return null;
  }
}

/** Read `devtools.remote_debugging.user-enabled` from the browser's `Local State`. */
export async function readToggle(userDataDir: string): Promise<boolean | undefined> {
  try {
    const json = JSON.parse(await readFile(join(userDataDir, "Local State"), "utf8"));
    const value = json?.devtools?.remote_debugging?.["user-enabled"];
    return typeof value === "boolean" ? value : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Raw TCP connect: tells whether a port is open without speaking HTTP or
 * WebSocket, so the browser never shows a permission dialog.
 */
export function probeTcp(host: string, port: number, timeoutMs = 300): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = tcpConnect({ host, port });
    const done = (open: boolean) => {
      socket.removeAllListeners();
      socket.destroy();
      resolve(open);
    };
    socket.setTimeout(timeoutMs, () => done(false));
    socket.once("connect", () => done(true));
    socket.once("error", () => done(false));
  });
}

async function dirExists(path: string): Promise<boolean> {
  try {
    return (await stat(path)).isDirectory();
  } catch {
    return false;
  }
}

/** Inspect one browser profile: installed? toggle? port file? actually listening? */
export async function inspect(browser: BrowserProfile, opts: DiscoverOptions = {}): Promise<Inspection> {
  const host = opts.host ?? "127.0.0.1";
  const [installed, toggleEnabled, activePort] = await Promise.all([
    dirExists(browser.userDataDir),
    readToggle(browser.userDataDir),
    readActivePort(browser.userDataDir),
  ]);

  const base = { browser, installed, toggleEnabled, activePort };
  if (!activePort) return { ...base, state: "no-port-file" };

  const listening = await probeTcp(host, activePort.port, opts.probeTimeoutMs);
  if (!listening) return { ...base, state: "not-listening" };

  return { ...base, state: "listening", endpoint: `ws://${host}:${activePort.port}${activePort.browserPath}` };
}

/** Inspect every catalogued browser that is installed on this machine. */
export async function discover(
  browsers: BrowserProfile[] = knownBrowsers(),
  opts: DiscoverOptions = {},
): Promise<Inspection[]> {
  const all = await Promise.all(browsers.map((b) => inspect(b, opts)));
  return all.filter((i) => i.installed);
}

/**
 * Pick the endpoint to connect to. Prefers an explicitly requested browser id;
 * otherwise the first listening browser in catalog order. Returns null if none.
 */
export function pickEndpoint(inspections: Inspection[], preferredId?: string): Inspection | null {
  const listening = inspections.filter((i) => i.state === "listening");
  if (preferredId) return listening.find((i) => i.browser.id === preferredId) ?? null;
  return listening[0] ?? null;
}

/** One-line, actionable explanation of why a browser cannot be attached to. */
export function explain(i: Inspection): string {
  const { name, inspectUrl } = i.browser;
  switch (i.state) {
    case "listening":
      return `${name}: ready at ${i.endpoint} — connecting will show an "Allow remote debugging?" dialog.`;
    case "not-listening":
      return i.toggleEnabled
        ? `${name}: remote debugging is enabled but the browser is not running (stale DevToolsActivePort). Start ${name}.`
        : `${name}: remote debugging is off. Open ${inspectUrl} and tick "Allow remote debugging for this browser instance".`;
    case "no-port-file":
      return `${name}: remote debugging was never enabled. Open ${inspectUrl} and tick "Allow remote debugging for this browser instance".`;
  }
}
