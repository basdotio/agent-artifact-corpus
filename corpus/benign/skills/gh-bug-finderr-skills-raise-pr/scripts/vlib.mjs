// Shared helpers for captioned PR flow videos on local dev. Run flow scripts with Node, not Bun.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const CACHE = path.join(os.homedir(), ".bun/install/cache");
// Newest cached playwright-core; bun keeps several versions side by side.
const core = fs
  .readdirSync(CACHE)
  .filter((dir) => dir.startsWith("playwright-core@"))
  .sort()
  .at(-1);
const { chromium } = await import(pathToFileURL(path.join(CACHE, core, "index.mjs")).href);

export const BASE = process.env.BASE_URL ?? "http://localhost:3000";
export const DESKTOP = { width: 1280, height: 800 };

export const consoleErrors = [];

export function launch() {
  return chromium.launch({ channel: "chrome" });
}

/** A page whose context records a video into `<outDir>/<name>/` until `finishVideo`. */
export async function recordedPage(browser, outDir, name, viewport = DESKTOP) {
  const dir = path.join(outDir, name);
  fs.rmSync(dir, { recursive: true, force: true });
  const context = await browser.newContext({ viewport, recordVideo: { dir, size: viewport } });
  const page = await context.newPage();
  page.setDefaultTimeout(25000);
  page.on("pageerror", (e) => consoleErrors.push(`[${name}] ${String(e).slice(0, 300)}`));
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(`[${name}] ${m.text().slice(0, 300)}`));
  return page;
}

/** A page without video, for setup and cleanup steps that should not be in the recording. */
export async function plainPage(browser, viewport = DESKTOP) {
  const page = await (await browser.newContext({ viewport })).newPage();
  page.setDefaultTimeout(25000);
  return page;
}

/** Shows a caption bar at the bottom of the page so the video explains itself. */
export async function say(page, text, ms = 2200) {
  await page
    .evaluate((t) => {
      let el = document.getElementById("__caption");
      if (!el) {
        el = document.createElement("div");
        el.id = "__caption";
        el.style.cssText =
          "position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:2147483647;max-width:90%;" +
          "background:rgba(10,10,20,.88);color:#fff;font:600 16px/1.35 system-ui,sans-serif;padding:10px 16px;" +
          "border-radius:8px;box-shadow:0 4px 18px rgba(0,0,0,.35);pointer-events:none;text-align:center";
        document.body.appendChild(el);
      }
      el.textContent = t;
    }, text)
    .catch(() => {});
  await page.waitForTimeout(ms);
}

export async function settle(page, extra = 900) {
  await page.waitForLoadState("domcontentloaded");
  await page
    .waitForFunction(() => document.querySelector("main") && !document.querySelector("main [aria-busy=true]"), null, {
      timeout: 20000,
    })
    .catch(() => {});
  await page.waitForTimeout(extra);
}

export async function go(page, url, caption) {
  await page.goto(BASE + url, { waitUntil: "domcontentloaded" });
  await settle(page);
  if (caption) await say(page, caption);
}

/**
 * Email and password sign-in with a seeded test account on a local or staging build. Pass selectors for
 * projects whose /auth page differs from the defaults. Read the password from the project's seed file, never hardcode it.
 */
export async function signIn(
  page,
  { email, password, next = "/dashboard", path: authPath = "/auth", emailSel = "#auth-email", passwordSel = "#auth-password", submit = "Sign in" },
) {
  // The dev server's lookups of the backend fail now and then; a reload recovers.
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await page.goto(`${BASE}${authPath}?next=${encodeURIComponent(next)}`, { waitUntil: "domcontentloaded" });
    await settle(page, 600);
    if (await page.locator(emailSel).isVisible().catch(() => false)) break;
  }
  await page.fill(emailSel, email);
  await page.fill(passwordSel, password);
  await page.getByRole("button", { name: submit, exact: true }).click();
  await page.waitForURL((url) => url.pathname === next.split("?")[0], { timeout: 30000 });
  await settle(page, 1200);
}

export async function openTab(page, name) {
  await page.getByRole("tab", { name, exact: true }).click();
  await page.waitForTimeout(800);
}

/** Closes the recording and saves it as `<outDir>/<name>.webm`. */
export async function finishVideo(page, outDir, name) {
  const video = page.video();
  await page.context().close();
  if (video) {
    fs.renameSync(await video.path(), path.join(outDir, `${name}.webm`));
    fs.rmSync(path.join(outDir, name), { recursive: true, force: true });
  }
}
