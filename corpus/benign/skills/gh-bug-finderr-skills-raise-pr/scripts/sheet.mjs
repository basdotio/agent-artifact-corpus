// Contact sheet of a recorded video, to check captions and steps without watching it.
// Usage: node sheet.mjs <video.webm> [stepSeconds=1.5] [from=0] [to=9999]  ->  <video.webm>.sheet-<from>.png
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { launch } from "./vlib.mjs";

const [file, step = "1.5", from = "0", to = "9999"] = process.argv.slice(2);
const abs = path.resolve(file);
const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1708, height: 800 } });
await page.goto(pathToFileURL(path.dirname(abs) + path.sep).href);
const { height, duration } = await page.evaluate(
  async ({ src, step, from, to }) => {
    const v = document.createElement("video");
    v.src = src;
    v.muted = true;
    await new Promise((r) => (v.onloadeddata = r));
    // Playwright's webm reports no duration until played through; seeking far reveals it.
    v.currentTime = 1e6;
    await new Promise((r) => (v.onseeked = r));
    const duration = v.currentTime || v.duration;
    const times = [];
    for (let t = from; t < Math.min(to, duration); t += step) times.push(t);
    const cols = 4;
    const w = 1680 / cols;
    const h = w * 0.625;
    const c = document.createElement("canvas");
    c.width = cols * w;
    c.height = Math.ceil(times.length / cols) * h;
    const g = c.getContext("2d");
    for (const [i, t] of times.entries()) {
      v.currentTime = t;
      await new Promise((r) => (v.onseeked = r));
      const x = (i % cols) * w;
      const y = Math.floor(i / cols) * h;
      g.drawImage(v, x, y, w, h);
      g.fillStyle = "red";
      g.font = "bold 20px sans-serif";
      g.fillText(t.toFixed(1), x + 6, y + 22);
    }
    document.body.replaceChildren(c);
    document.body.style.margin = "0";
    return { height: c.height, duration };
  },
  { src: pathToFileURL(abs).href, step: Number(step), from: Number(from), to: Number(to) },
);
await page.setViewportSize({ width: 1680, height: Math.max(200, height) });
await page.screenshot({ path: `${abs}.sheet-${from}.png`, fullPage: true });
console.log(`duration ${duration.toFixed(1)}s, ${(fs.statSync(abs).size / 1e6).toFixed(1)} MB`);
await browser.close();
