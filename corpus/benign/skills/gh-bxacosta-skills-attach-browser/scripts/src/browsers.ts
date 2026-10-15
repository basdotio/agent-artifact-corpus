/**
 * Catalog of Chromium-based browsers and where each one keeps its user data
 * directory (the folder that contains `DevToolsActivePort` and `Local State`).
 *
 * This is pure data + path resolution: no I/O. Add a browser by adding a row.
 */

import { homedir } from "node:os";
import { join } from "node:path";

export type Platform = "win32" | "darwin" | "linux";

export interface BrowserProfile {
  /** Stable identifier, e.g. "chrome", "edge-beta", "brave". */
  id: string;
  /** Human-readable name for messages. */
  name: string;
  /** Absolute path of the user data directory ("User Data" on Windows). */
  userDataDir: string;
  /** URL the user opens to enable remote debugging on this browser. */
  inspectUrl: string;
}

interface CatalogEntry {
  id: string;
  name: string;
  scheme: string; // "chrome" | "edge" | "brave" ... used for the inspect URL
  /** Path relative to the platform base dir; omit a platform if the browser does not exist there. */
  paths: Partial<Record<Platform, string>>;
}

// Windows paths are relative to %LOCALAPPDATA% (Opera: %APPDATA%, see baseDirs).
// macOS paths are relative to ~/Library/Application Support.
// Linux paths are relative to $XDG_CONFIG_HOME (default ~/.config).
const CATALOG: CatalogEntry[] = [
  { id: "chrome",        name: "Google Chrome",        scheme: "chrome", paths: { win32: "Google/Chrome/User Data",        darwin: "Google/Chrome",        linux: "google-chrome" } },
  { id: "chrome-beta",   name: "Google Chrome Beta",   scheme: "chrome", paths: { win32: "Google/Chrome Beta/User Data",   darwin: "Google/Chrome Beta",   linux: "google-chrome-beta" } },
  { id: "chrome-dev",    name: "Google Chrome Dev",    scheme: "chrome", paths: { win32: "Google/Chrome Dev/User Data",    darwin: "Google/Chrome Dev",    linux: "google-chrome-unstable" } },
  { id: "chrome-canary", name: "Google Chrome Canary", scheme: "chrome", paths: { win32: "Google/Chrome SxS/User Data",    darwin: "Google/Chrome Canary", linux: "google-chrome-canary" } },
  { id: "chromium",      name: "Chromium",             scheme: "chrome", paths: { win32: "Chromium/User Data",             darwin: "Chromium",             linux: "chromium" } },
  { id: "edge",          name: "Microsoft Edge",       scheme: "edge",   paths: { win32: "Microsoft/Edge/User Data",       darwin: "Microsoft Edge",       linux: "microsoft-edge" } },
  { id: "edge-beta",     name: "Microsoft Edge Beta",  scheme: "edge",   paths: { win32: "Microsoft/Edge Beta/User Data",  darwin: "Microsoft Edge Beta",  linux: "microsoft-edge-beta" } },
  { id: "edge-dev",      name: "Microsoft Edge Dev",   scheme: "edge",   paths: { win32: "Microsoft/Edge Dev/User Data",   darwin: "Microsoft Edge Dev",   linux: "microsoft-edge-dev" } },
  { id: "edge-canary",   name: "Microsoft Edge Canary",scheme: "edge",   paths: { win32: "Microsoft/Edge SxS/User Data",   darwin: "Microsoft Edge Canary" } },
  { id: "brave",         name: "Brave",                scheme: "brave",  paths: { win32: "BraveSoftware/Brave-Browser/User Data", darwin: "BraveSoftware/Brave-Browser", linux: "BraveSoftware/Brave-Browser" } },
  { id: "vivaldi",       name: "Vivaldi",              scheme: "vivaldi",paths: { win32: "Vivaldi/User Data",              darwin: "Vivaldi",              linux: "vivaldi" } },
  { id: "opera",         name: "Opera",                scheme: "opera",  paths: { win32: "Opera Software/Opera Stable",    darwin: "com.operasoftware.Opera", linux: "opera" } },
];

type Env = Record<string, string | undefined>;

function baseDir(platform: Platform, entryId: string, env: Env): string | undefined {
  const home = env.HOME ?? env.USERPROFILE ?? homedir();
  switch (platform) {
    case "win32":
      // Opera is the odd one out: it lives in Roaming, not Local.
      return entryId === "opera" ? env.APPDATA : env.LOCALAPPDATA;
    case "darwin":
      return join(home, "Library", "Application Support");
    case "linux":
      return env.XDG_CONFIG_HOME || join(home, ".config");
  }
}

/** All catalogued browsers for the given platform, with absolute user data dirs. */
export function knownBrowsers(
  platform: Platform = process.platform as Platform,
  env: Env = process.env,
): BrowserProfile[] {
  const result: BrowserProfile[] = [];
  for (const entry of CATALOG) {
    const rel = entry.paths[platform];
    const base = baseDir(platform, entry.id, env);
    if (!rel || !base) continue;
    result.push({
      id: entry.id,
      name: entry.name,
      userDataDir: join(base, ...rel.split("/")),
      inspectUrl: `${entry.scheme}://inspect/#remote-debugging`,
    });
  }
  return result;
}

/** Wrap a user-supplied data dir (e.g. a dedicated automation profile) as a profile. */
export function customBrowser(userDataDir: string, name = "custom"): BrowserProfile {
  return { id: name, name, userDataDir, inspectUrl: "chrome://inspect/#remote-debugging" };
}
