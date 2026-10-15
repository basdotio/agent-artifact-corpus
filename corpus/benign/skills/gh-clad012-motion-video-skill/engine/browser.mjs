/**
 * Finds a Chrome-family browser already on the machine and launches it
 * headless through playwright-core, which never downloads one itself.
 *
 * Order: CHROME_PATH, the usual install paths of Google Chrome, Chromium and
 * Microsoft Edge on Linux, macOS and Windows, then any browser Playwright has
 * downloaded before.
 */
import { existsSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const KNOWN = [
  "/opt/google/chrome/google-chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "/snap/bin/chromium",
  "/usr/bin/microsoft-edge",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

/** Browsers Playwright downloaded earlier, newest first. */
function playwrightBrowsers() {
  const roots = [process.env.PLAYWRIGHT_BROWSERS_PATH, join(homedir(), ".cache/ms-playwright"), join(homedir(), "Library/Caches/ms-playwright"), join(homedir(), "AppData/Local/ms-playwright")].filter(Boolean);
  const inside = [
    "chrome-linux/chrome", "chrome-linux64/chrome", "chrome-mac/Chromium.app/Contents/MacOS/Chromium",
    "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing", "chrome-win/chrome.exe",
    "chrome-headless-shell-linux64/chrome-headless-shell", "chrome-headless-shell-mac-arm64/chrome-headless-shell", "chrome-linux/headless_shell",
  ];
  const found = [];
  for (const root of roots) {
    if (!existsSync(root)) continue;
    for (const dir of readdirSync(root).filter((d) => d.startsWith("chromium")).sort().reverse()) {
      for (const rel of inside) if (existsSync(join(root, dir, rel))) found.push(join(root, dir, rel));
    }
  }
  return found;
}

export function findBrowser() {
  if (process.env.CHROME_PATH) return existsSync(process.env.CHROME_PATH) ? process.env.CHROME_PATH : null;
  return KNOWN.find((p) => existsSync(p)) ?? playwrightBrowsers()[0] ?? null;
}

export const NO_BROWSER = "No Chrome, Chromium or Edge found. Install one, set CHROME_PATH to it, or run: npx playwright install chromium";

export async function launchBrowser() {
  let chromium;
  try {
    ({ chromium } = await import("playwright-core"));
  } catch {
    throw new Error("Node dependencies missing: run npm install in the engine folder");
  }
  const executablePath = findBrowser();
  if (!executablePath) throw new Error(NO_BROWSER);
  return chromium.launch({ executablePath, headless: true, args: ["--disable-gpu", "--no-first-run", "--hide-scrollbars"] });
}
