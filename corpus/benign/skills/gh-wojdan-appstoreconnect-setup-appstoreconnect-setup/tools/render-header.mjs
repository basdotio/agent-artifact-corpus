#!/usr/bin/env node
// Renders the App Store product page header (21:9, 3840 x 1646, PNG without alpha) for one language, from
// store/header/template.html, store/header/header.css and store/header/texts/<lang>.json.
// Usage: node render-header.mjs <lang> [out.png]        (run from the project's root; the default is store/out/<lang>/header.png)
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { config, direction, escape, fill, fontLinks, htmlAttributes, inStore, openPage, readJson, rtlCss, scriptCss, sharp, shown, styles } from "./lib.mjs";

const [lang, outArg] = process.argv.slice(2);
if (!lang) { console.error("usage: node render-header.mjs <lang> [out.png]"); process.exit(2); }
const cfg = await config(), h = cfg.header ?? {};
const [width, height] = h.css ?? [1920, 823], scale = h.scale ?? 2;
// What an iPhone shows of the canvas' width. Measured in the preview of App Store Connect in October 2026: the full
// height and the middle 84% of the width. Apple publishes no safe area in pixels; look at the preview.
const visible = h.visible ?? [Math.round(width * 0.08), Math.round(width * 0.92)];
const out = path.resolve(outArg ?? inStore("out", lang, "header.png"));

const texts = await readJson(inStore("header", "texts", `${lang}.json`));
// A line is {"text", "tone"}; the tone becomes a class (h-line--quiet, h-line--full, or whatever header.css defines).
const lines = texts.lines.map((line) => `<span class="h-line h-line--${escape(line.tone ?? "full")}">${escape(line.text)}</span>`).join("");
const template = await readFile(inStore("header", "template.html"), "utf8");

const html = `<!DOCTYPE html><html ${htmlAttributes(lang)}><head><meta charset="utf-8">
${fontLinks(cfg)}
${await styles(cfg, "header/header.css")}<style>
html, body { margin: 0; }
#stage { position: relative; overflow: hidden; width: ${width}px; height: ${height}px; }
.h-line { display: block; white-space: nowrap; }
${scriptCss(cfg, lang, "#title")}
${await rtlCss(lang)}
</style></head><body><div ${cfg.rootAttributes ?? ""}>${fill(template, texts, `header/texts/${lang}.json`, { lines })}</div></body></html>`;

const { browser, page } = await openPage(html, { width, height }, scale);
try {
  const stage = await page.$("#stage");
  if (!stage || !(await page.$("#title"))) throw new Error('header/template.html needs an element with id="stage" and the slogan in an element with id="title"');
  const box = await page.evaluate(() => {
    const ink = (e) => { const range = document.createRange(); range.selectNodeContents(e); return range.getBoundingClientRect(); };
    const lines = [...document.querySelectorAll(".h-line")].map(ink);
    // Every `data-keep-clear` element is a shape the slogan must stay away from; "circle" measures to a circle's edge.
    const gaps = [...document.querySelectorAll("[data-keep-clear]")].flatMap((shape) => {
      const s = shape.getBoundingClientRect(), round = shape.dataset.keepClear === "circle";
      return lines.map((l) => {
        if (round) {
          const cx = s.left + s.width / 2, cy = s.top + s.height / 2;
          const dx = Math.max(l.left - cx, 0, cx - l.right), dy = Math.max(l.top - cy, 0, cy - l.bottom);
          return Math.hypot(dx, dy) - s.width / 2;
        }
        const dx = Math.max(l.left - s.right, s.left - l.right), dy = Math.max(l.top - s.bottom, s.top - l.bottom);
        return dx < 0 && dy < 0 ? Math.max(dx, dy) : Math.hypot(Math.max(dx, 0), Math.max(dy, 0));
      });
    });
    return { left: Math.round(Math.min(...lines.map((l) => l.left))), right: Math.round(Math.max(...lines.map((l) => l.right))), count: lines.length, gap: gaps.length ? Math.round(Math.min(...gaps)) : null };
  });
  await mkdir(path.dirname(out), { recursive: true });
  await sharp()(await stage.screenshot({ type: "png", omitBackground: false })).removeAlpha().png({ compressionLevel: 9 }).toFile(out);
  const made = await sharp()(out).metadata();
  console.log(`${shown(out)}  ${made.width} x ${made.height}  slogan in ${box.count} line(s), ${box.left}..${box.right} of ${width}` + (box.gap === null ? "" : `, at least ${box.gap} px from the shapes`));
  let warnings = 0;
  if (box.left < visible[0] || box.right > visible[1]) { warnings++; console.error(`warning: an iPhone shows ${visible[0]}..${visible[1]} of the width; the slogan will be cut`); }
  if (box.gap !== null && box.gap < (h.minGap ?? 40)) { warnings++; console.error("warning: the slogan touches or nearly touches a shape"); }
  if (direction(lang) === "rtl") console.log("right to left: the shapes should sit in the other corner (store/rtl.css)");
  console.log(warnings ? `${warnings} warning(s)` : "no warnings");
} finally { await browser.close(); }
