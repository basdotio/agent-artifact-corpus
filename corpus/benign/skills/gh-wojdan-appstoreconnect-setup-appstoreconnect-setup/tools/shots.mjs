#!/usr/bin/env node
// Screenshots each top-level <section> of an exported design page to a JPEG, so the page can be looked at (and
// compared with a brief) without opening it by hand.
// Usage: node shots.mjs <dir> <page.html> <out-dir> [scale]
import http from "node:http";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "./lib.mjs";

const [dirArg, file, outArg, scaleArg] = process.argv.slice(2);
if (!dirArg || !file || !outArg) { console.error("usage: node shots.mjs <dir> <page.html> <out-dir> [scale]"); process.exit(2); }
const dir = path.resolve(dirArg), out = path.resolve(outArg);
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".woff2": "font/woff2" };

// The page is served from this machine only, and only files inside <dir>.
const server = http.createServer(async (request, response) => {
  try {
    const target = path.resolve(dir, decodeURIComponent(new URL(request.url, "http://localhost").pathname).replace(/^\/+/, ""));
    if (!target.startsWith(dir + path.sep)) throw new Error("outside");
    const body = await readFile(target);
    response.writeHead(200, { "content-type": TYPES[path.extname(target)] ?? "application/octet-stream" });
    response.end(body);
  } catch { response.writeHead(404); response.end("not found"); }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const url = `http://127.0.0.1:${server.address().port}/${encodeURIComponent(file)}`;
const browser = await chromium().launch();
try {
  const probe = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await probe.goto(url, { waitUntil: "networkidle" });
  const natural = await probe.evaluate(() => document.documentElement.scrollWidth);
  await probe.close();
  const page = await (await browser.newContext({ viewport: { width: natural, height: 1200 }, deviceScaleFactor: Number(scaleArg ?? 1) })).newPage();
  await page.goto(url, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(800);
  await mkdir(out, { recursive: true });
  const sections = await page.evaluate(() => {
    const top = [...document.querySelectorAll("section")].filter((s) => !s.parentElement?.closest("section"));
    return (top.length ? top : [document.body]).map((s) => {
      const b = s.getBoundingClientRect();
      return { y: b.top + scrollY, h: b.height, title: (s.querySelector("h1,h2,h3")?.innerText ?? "").trim() };
    });
  });
  for (const [i, s] of sections.entries()) {
    const name = `${String(i + 1).padStart(2, "0")}.jpg`;
    await page.screenshot({ path: path.join(out, name), type: "jpeg", quality: 80, fullPage: true, clip: { x: 0, y: Math.max(0, Math.round(s.y - 20)), width: natural, height: Math.round(s.h + 40) } });
    console.log(`${name}  ${natural} x ${Math.round(s.h + 40)}  ${s.title}`);
  }
} finally { await browser.close(); server.close(); }
