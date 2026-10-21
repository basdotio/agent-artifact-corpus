#!/usr/bin/env node
// Verify the framework-free badge (assets/vanilla) in a running site with headless Chrome.
// Checks: it renders, click flips and HOLDS, the back flips back, the timer auto-flips, it docks on
// scroll and returns, mobile has no dock and no horizontal scroll, reduced motion snaps, and the
// page logs no errors. Saves screenshots. Exits 1 if any check fails.
//
// Needs puppeteer from the project or the skill folder (npm i puppeteer --prefix ~/.claude/skills/lanyard-badge).
//
// Usage (dev server running):
//   node ~/.claude/skills/lanyard-badge/scripts/verify-vanilla.mjs --url http://localhost:5173 [--out screenshots/badge] [--auto-flip 5000] [--hero "#hero"]
//   --hero is a selector of the section holding the badge (default: the badge slot itself).

import { mkdir } from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { createRequire } from "node:module";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith("--") ? [...acc, [a.slice(2), all[i + 1]]] : acc), []),
);
const url = args.url ?? "http://localhost:5173";
const out = args.out ?? "screenshots/badge";
const autoFlip = Number(args["auto-flip"] ?? 5000);
const heroSel = args.hero ?? "[data-badge-slot]";

let puppeteer;
for (const base of [path.join(process.cwd(), "package.json"), path.join(os.homedir(), ".claude/skills/lanyard-badge/package.json")]) {
  try {
    puppeteer = createRequire(base)("puppeteer");
    break;
  } catch {}
}
if (!puppeteer) {
  console.error("puppeteer is not installed (only this check needs it). Run: npm i puppeteer --prefix ~/.claude/skills/lanyard-badge");
  process.exit(1);
}

await mkdir(out, { recursive: true });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const check = (name, ok, extra = "") => {
  results.push({ name, ok: !!ok });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? "  " + extra : ""}`);
};
const errors = [];

const browser = await puppeteer.launch();
try {
  // ---------- Desktop ----------
  const page = await browser.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => r.status() >= 400 && !r.url().includes("favicon") && errors.push(`${r.status()} ${r.url()}`));
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
  await page.goto(url, { waitUntil: "networkidle0" });

  const heroTop = await page.evaluate((sel) => document.querySelector(sel).getBoundingClientRect().top + scrollY, heroSel);
  await page.evaluate((y) => scrollTo(0, y), heroTop);
  await wait(2300);
  const present = await page.$("[data-badge]");
  check("badge renders", present);
  if (!present) throw new Error("No [data-badge] element found: is initBadge() called and [data-badge-slot] in the page?");

  const faceInert = (f) => page.evaluate((f) => document.querySelector(`[data-badge-face="${f}"]`).inert, f);
  check("photo loaded", await page.evaluate(() => { const i = document.querySelector(".badge-photo img"); return !i || (i.complete && i.naturalWidth > 0); }));
  await page.screenshot({ path: `${out}/page-front.png` });
  const flipEl = await page.$(".badge-flip");
  await flipEl.screenshot({ path: `${out}/card-front.png` });

  // click flips to the back and holds
  await page.evaluate(() => document.querySelector("[data-badge-front-hit]").click());
  await wait(1100);
  await page.mouse.move(5, 5);
  check("click flips to back", (await faceInert("front")) && !(await faceInert("back")));
  await flipEl.screenshot({ path: `${out}/card-back.png` });
  await wait(autoFlip + 600);
  check("manual flip holds past the auto-flip interval", !(await faceInert("back")));
  await page.evaluate(() => document.querySelector("[data-badge-back-hit]").click());
  await wait(1000);
  check("back button returns to front", !(await faceInert("front")));

  if (autoFlip > 0) {
    await wait(autoFlip + 800);
    check("auto-flips on the timer", !(await faceInert("back")));
    await page.evaluate(() => document.querySelector("[data-badge-back-hit]").click());
    await wait(900);
  }

  // dock on scroll, return on scroll up
  await page.evaluate((y) => scrollTo(0, y + 800), heroTop);
  await wait(2800);
  const docked = await page.evaluate(() => {
    const r = document.querySelector("[data-badge]");
    const b = r.getBoundingClientRect();
    return { floating: r.classList.contains("is-floating"), right: b.right, vw: innerWidth };
  });
  check("docks while scrolled", docked.floating, `(right edge ${Math.round(docked.right)} of ${docked.vw})`);
  await page.screenshot({ path: `${out}/page-docked.png` });
  await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
  await wait(1500);
  check("stays docked at page bottom", await page.evaluate(() => document.querySelector("[data-badge]").classList.contains("is-floating")));
  await page.evaluate((y) => scrollTo(0, y), heroTop);
  await wait(2500);
  check("returns to its slot when scrolled back up", !(await page.evaluate(() => document.querySelector("[data-badge]").classList.contains("is-floating"))));

  // ---------- Mobile ----------
  const m = await browser.newPage();
  m.on("pageerror", (e) => errors.push("mobile: " + e.message));
  await m.setViewport({ width: 390, height: 844 });
  await m.goto(url, { waitUntil: "networkidle0" });
  const mTop = await m.evaluate((sel) => document.querySelector(sel).getBoundingClientRect().top + scrollY, heroSel);
  await m.evaluate((y) => scrollTo(0, y + 500), mTop);
  await wait(2200);
  await m.screenshot({ path: `${out}/mobile.png` });
  const mob = await m.evaluate(() => ({
    floating: document.querySelector("[data-badge]").classList.contains("is-floating"),
    hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  }));
  check("mobile: no floating dock", !mob.floating);
  check("mobile: no horizontal scroll", !mob.hscroll);

  // ---------- Reduced motion ----------
  const ctx = await browser.createBrowserContext();
  const r = await ctx.newPage();
  r.on("pageerror", (e) => errors.push("reduced: " + e.message));
  await r.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await r.setViewport({ width: 1440, height: 900 });
  await r.goto(url, { waitUntil: "networkidle0" });
  await r.evaluate((y) => scrollTo(0, y + 800), heroTop);
  await wait(800);
  check("reduced motion: docks immediately (no spring)", await r.evaluate(() => document.querySelector("[data-badge]").classList.contains("is-floating")));

  check("no page errors", errors.length === 0, errors.length ? JSON.stringify(errors) : "");
} catch (e) {
  console.error(e.message);
  results.push({ name: "script", ok: false });
} finally {
  await browser.close();
}
const failed = results.filter((x) => !x.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed. Screenshots: ${out}/`);
process.exit(failed ? 1 : 0);
