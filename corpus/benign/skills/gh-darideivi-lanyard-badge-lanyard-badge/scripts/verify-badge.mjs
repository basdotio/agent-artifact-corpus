#!/usr/bin/env node
// Verify a LanyardBadge in a running site: screenshots each card front/back and
// logs the automatic timeline (which card, front/back, at what second).
// Needs puppeteer from the project or the skill folder (npm i puppeteer --prefix ~/.claude/skills/lanyard-badge).
//
// Usage (from the project root, dev server running):
//   node ~/.claude/skills/lanyard-badge/scripts/verify-badge.mjs [--url http://localhost:3000] [--seconds 75] [--out screenshots/badge]

import { mkdir } from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { createRequire } from "node:module";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith("--") ? [...acc, [a.slice(2), all[i + 1]]] : acc), []),
);
const url = args.url ?? "http://localhost:3000";
const seconds = Number(args.seconds ?? 75);
const out = args.out ?? "screenshots/badge";

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
const browser = await puppeteer.launch();
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
  await page.goto(url, { waitUntil: "networkidle0" });
  await page.evaluate(() => document.fonts.ready);

  const state = () =>
    page.evaluate(() => {
      const slide = document.querySelector('[aria-roledescription="slide"]')?.getAttribute("aria-label")?.split(" (")[0];
      const back = document.querySelector('button[aria-pressed]')?.getAttribute("aria-pressed") === "true";
      return slide ? `${slide} ${back ? "BACK" : "front"}` : null;
    });
  if (!(await state())) throw new Error("No badge found (expected a [aria-roledescription=slide] element).");

  // 1) Screenshots of every card, front and back.
  const dots = await page.$$('button[aria-label$=" badge"]');
  const region = await page.$('[aria-roledescription="carousel"]');
  for (let i = 0; i < dots.length; i++) {
    await dots[i].click();
    await page.mouse.move(5, 5);
    await wait(1300);
    await region.screenshot({ path: `${out}/card-${i}-front.png` });
    await page.click("button[aria-pressed]");
    await wait(1000);
    await region.screenshot({ path: `${out}/card-${i}-back.png` });
    await page.click("button[aria-pressed]");
    await wait(900);
  }

  // 2) Manual flip must toggle both ways by clicking the badge itself.
  await dots[0].click();
  await page.mouse.move(5, 5);
  await wait(1200);
  const box = await region.boundingBox();
  const clicks = [];
  for (let i = 0; i < 2; i++) {
    await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.35);
    await wait(900);
    clicks.push(await state());
  }
  await page.mouse.move(5, 5);
  console.log("manual click toggles:", clicks.join(" -> "));

  // 3) Automatic timeline from a fresh load.
  await page.reload({ waitUntil: "networkidle0" });
  const t0 = Date.now();
  let prev = "";
  console.log(`timeline (${seconds}s):`);
  while (Date.now() - t0 < seconds * 1000) {
    const s = await state();
    if (s !== prev) {
      console.log(`${((Date.now() - t0) / 1000).toFixed(1).padStart(6)}s  ${s}`);
      prev = s;
    }
    await wait(100);
  }
  console.log(`screenshots: ${out}/card-*-{front,back}.png`);
} finally {
  await browser.close();
}
