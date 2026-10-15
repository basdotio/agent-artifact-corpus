#!/usr/bin/env node
// Renders the App Store screenshots ("frames": a claim over a drawn screen of the app) for one language, as PNG
// without alpha, from store/frames/template/frame-<n>.html and store/frames/texts/<lang>.json.
// Usage: node render-frames.mjs <lang> [out-dir] [--set <name>]
//   Run from the project's root; the default is store/out/<lang>. --set renders a further set (another platform or
//   display, frames.sets.<name> in the configuration) into store/out/<lang>/<name>, from the same texts.
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { config, direction, escape, fill, fontLinks, frameSet, htmlAttributes, inStore, openPage, readJson, rtlCss, scriptCss, sharp, shown, styles, takeSet } from "./lib.mjs";

const args = process.argv.slice(2), set = takeSet(args), [lang, outArg] = args;
if (!lang) { console.error("usage: node render-frames.mjs <lang> [out-dir] [--set <name>]"); process.exit(2); }
const cfg = await config(), f = frameSet(cfg, set);
// A frame is drawn in CSS px and painted at a whole scale: 440 x 956 at 3 is 1320 x 2868 (the 6.9-inch iPhone),
// 402 x 874 at 3 is 1206 x 2622 (the 6.3-inch one). A whole scale keeps every edge on the pixel grid.
const [width, height] = f.css ?? [440, 956], scale = f.scale ?? 3;
const select = { frame: ".store-frame", claimLines: ".store-frame__title > span", screen: ".store-frame__screen", clip: "button", ...f.selectors };
const claimWidth = f.claimWidth ?? width - 48;
const templates = f.template ?? "template";
const outDir = path.resolve(outArg ?? inStore("out", lang, ...(set ? [set] : [])));

const texts = await readJson(inStore("frames", "texts", `${lang}.json`));
const count = texts.frames.length, gap = 40;
let slots = "";
for (let n = 1; n <= count; n++) {
  const fields = texts.frames[n - 1], where = `frames/texts/${lang}.json: frame ${n}`;
  if (!Array.isArray(fields.claim) || !fields.claim.length) throw new Error(`${where} needs a claim (a list of lines)`);
  const template = (await readFile(inStore("frames", templates, `frame-${n}.html`), "utf8")).trim();
  const claim = fields.claim.map((line) => `<span>${escape(line)}</span>`).join(" ");
  slots += `<div class="f-slot" data-n="${n}" style="top:${(height + gap) * (n - 1)}px">${fill(template, fields, where, { claim })}</div>`;
}

const html = `<!DOCTYPE html><html ${htmlAttributes(lang)}><head><meta charset="utf-8">
${fontLinks(cfg)}
${await styles(cfg, "frames/frames.css")}<style>
html, body { margin: 0; }
.f-page { position: relative; height: ${(height + gap) * count}px; }
.f-slot { position: absolute; left: 0; width: ${width}px; height: ${height}px; --frame-width: ${width}px; --frame-height: ${height}px; }
${scriptCss(cfg, lang, select.claimLines.split(">")[0].trim())}
${await rtlCss(lang)}
</style></head><body><div class="f-page" ${cfg.rootAttributes ?? ""}>${slots}</div></body></html>`;

const { browser, page } = await openPage(html, { width: Math.max(width, 800), height: 1200 }, scale);
try {
  await mkdir(outDir, { recursive: true });
  let warnings = 0;
  const warn = (text) => { warnings++; console.error(`warning: ${text}`); };
  for (let n = 1; n <= count; n++) {
    const element = await page.$(`.f-slot[data-n="${n}"] > ${select.frame}`);
    if (!element) throw new Error(`frame ${n}: the template's root is not "${select.frame}" (frames.selectors.frame in store.config.json)`);
    // What does not fit: a claim line wider than the frame's inner width, a text of the screen that leaves its place
    // sideways, a text the frame's bottom edge runs through.
    const report = await element.evaluate((frame, { select, claimWidth }) => {
      const inked = (e) => { const range = document.createRange(); range.selectNodeContents(e); return range.getBoundingClientRect(); };
      const box = frame.getBoundingClientRect();
      const lines = [...frame.querySelectorAll(select.claimLines)].map((span) => Math.round(inked(span).width));
      const screenElement = frame.querySelector(select.screen), screen = (screenElement ?? frame).getBoundingClientRect(), cut = [], halved = [];
      for (const e of (screenElement ?? frame).querySelectorAll("*")) {
        if (e.closest("svg") || ![...e.childNodes].some((c) => c.nodeType === 3 && c.textContent.trim())) continue;
        const text = inked(e), clip = e.closest(select.clip)?.getBoundingClientRect() ?? screen;
        if (text.left < Math.max(screen.left, clip.left) - 0.5 || text.right > Math.min(screen.right, clip.right) + 0.5 || e.scrollWidth > e.clientWidth + 1) cut.push(e.textContent.trim());
        if (text.top < box.bottom - 1 && text.bottom > box.bottom + 1) halved.push(e.textContent.trim());
      }
      return { size: [Math.round(box.width), Math.round(box.height)], lines, cut, halved };
    }, { select, claimWidth });
    if (report.size[0] !== width || report.size[1] !== height) warn(`frame ${n} is ${report.size.join(" x ")} CSS px, the configuration says ${width} x ${height}`);
    const target = path.join(outDir, `frame-${n}.png`);
    await sharp()(await element.screenshot({ type: "png", omitBackground: false })).removeAlpha().png({ compressionLevel: 9 }).toFile(target);
    const made = await sharp()(target).metadata();
    console.log(`${shown(target)}  ${made.width} x ${made.height}  claim ${report.lines.join(" and ")} of ${claimWidth} px`);
    if (report.lines.some((w) => w > claimWidth)) warn(`frame ${n}: a line of the claim is wider than ${claimWidth} px`);
    for (const text of report.cut) warn(`frame ${n}: "${text}" does not fit its place on the screen`);
    for (const text of report.halved) warn(`frame ${n}: the frame's bottom edge cuts through "${text}"`);
  }
  if (direction(lang) === "rtl") console.log("right to left: look at every frame, the kit's own left/right placements need store/rtl.css");
  console.log(warnings ? `${warnings} warning(s)` : "no warnings");
} finally { await browser.close(); }
