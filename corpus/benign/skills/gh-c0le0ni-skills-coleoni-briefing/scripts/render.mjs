#!/usr/bin/env node
/**
 * Coleoni · renders a scope document (markdown) as a client-ready HTML and PDF.
 *
 *   node render.mjs scope.md [--out folder] [--accent "#2f6fed"] [--logo logo.svg] [--by "Studio"] [--no-pdf]
 *
 * The HTML is self-contained (fonts and logo embedded), so it can be emailed or
 * hosted as is. The PDF is A4, printed by the system Chrome or Edge.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { marked } from "marked";

const HERE = dirname(fileURLToPath(import.meta.url));

const HELP = `
node render.mjs <scope.md> [options]

  --out <folder>     output folder (default: next to the markdown)
  --accent "#hex"    accent color for rules, numbers and highlights (default #2f6fed)
  --logo <file>      logo on the cover (svg, png or jpg)
  --by "Name"        who prepared it, shown on the cover and in the footer
  --lang en|pt       document language for the cover labels (default: detected)
  --no-pdf           only write the HTML
`;

// ---------------------------------------------------------------- arguments
function parseArgs(argv) {
  const o = { file: null, out: null, accent: "#2f6fed", logo: null, by: null, pdf: true, lang: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const val = () => argv[++i] ?? "";
    if (!a.startsWith("--")) {
      o.file = a;
      continue;
    }
    if (a === "--help") {
      console.log(HELP);
      process.exit(0);
    } else if (a === "--out") o.out = val();
    else if (a === "--accent") o.accent = val();
    else if (a === "--logo") o.logo = val();
    else if (a === "--by") o.by = val();
    else if (a === "--no-pdf") o.pdf = false;
    else if (a === "--lang") o.lang = val().toLowerCase();
    else {
      console.error(`unknown option: ${a}`);
      process.exit(1);
    }
  }
  if (!o.file) {
    console.log(HELP);
    process.exit(1);
  }
  if (!/^#[0-9a-f]{3,8}$/i.test(o.accent)) {
    console.error(`--accent must be a hex color, got ${o.accent}`);
    process.exit(1);
  }
  return o;
}

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// ---------------------------------------------------------------- document
/** Splits the markdown into title, the bold "Label: value" lines under it, and the body. */
function splitDoc(md) {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  let i = 0;
  while (i < lines.length && !lines[i].startsWith("# ")) i++;
  const title = i < lines.length ? lines[i].slice(2).trim() : "Scope";
  i++;
  const meta = [];
  for (; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const m = line.match(/^\*\*(.+?):\*\*\s*(.*)$/);
    if (!m) break;
    meta.push([m[1], m[2]]);
  }
  return { title, meta, body: lines.slice(i).join("\n") };
}

function logoTag(file) {
  if (!file) return "";
  const ext = extname(file).toLowerCase();
  const type = ext === ".svg" ? "image/svg+xml" : ext === ".png" ? "image/png" : "image/jpeg";
  const b64 = readFileSync(file).toString("base64");
  return `<img class="logo" src="data:${type};base64,${b64}" alt="">`;
}

function html({ title, meta, body }, o) {
  // Document language: --lang, or whichever language's common words appear more.
  const count = (re) => (body.match(re) || []).length;
  const pt = o.lang
    ? o.lang.startsWith("pt")
    : count(/(?<!\p{L})(de|n\u00e3o|para|com|uma|que|os|as)(?!\p{L})/giu) > count(/\b(the|and|with|for|that|of|to)\b/gi);
  const font = readFileSync(join(HERE, "..", "fonts", "geist-latin.woff2")).toString("base64");
  let content = marked.parse(body, { gfm: true });
  // The "In one sentence:" line becomes a highlighted statement, in any language
  // the template was translated to.
  content = content.replace(/<h2>(\d+\.)/g, '<h2><span class="num">$1</span>');
  content = content.replace(
    /<p>((?:In one sentence|Em uma frase|En una frase|En une phrase|In einem Satz)\s*:)([\s\S]*?)<\/p>/i,
    '<p class="one"><span>$1</span>$2</p>',
  );
  const metaHtml = meta.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${marked.parseInline(v)}</dd></div>`).join("");
  return `<!doctype html>
<html lang="${pt ? "pt-BR" : "en"}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<style>
@font-face { font-family: "Geist"; font-weight: 100 900; src: url(data:font/woff2;base64,${font}) format("woff2"); }
:root { --accent: ${o.accent}; --ink: #16171a; --ink-2: #4a4d55; --ink-3: #80838c; --line: #e6e7ea; --paper: #ffffff; --tint: color-mix(in srgb, var(--accent) 8%, white); }
* { box-sizing: border-box; }
html { background: #f3f3f4; }
body { margin: 0; color: var(--ink); font: 400 14.5px/1.6 "Geist", system-ui, -apple-system, "Segoe UI", sans-serif; -webkit-font-smoothing: antialiased; }
.sheet { max-width: 820px; margin: 40px auto; padding: 64px 72px; background: var(--paper); border: 1px solid var(--line); border-radius: 10px; }
.cover { display: grid; gap: 22px; padding-bottom: 28px; margin-bottom: 8px; border-bottom: 2px solid var(--ink); }
.logo { height: 30px; width: auto; display: block; }
.kicker { font: 500 11.5px/1 ui-monospace, "SF Mono", Consolas, monospace; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); }
h1 { margin: 0; font-size: 38px; line-height: 1.08; letter-spacing: -0.03em; font-weight: 620; text-wrap: balance; }
dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 32px; margin: 0; }
dl div { display: grid; gap: 1px; }
dt { font-size: 11.5px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.06em; }
dd { margin: 0; font-weight: 500; }
h2 { counter-increment: sec; margin: 34px 0 10px; padding-top: 14px; border-top: 1px solid var(--line); font-size: 19px; letter-spacing: -0.015em; font-weight: 620; break-after: avoid; }
h2 .num { color: var(--accent); margin-right: 2px; }
h3 { margin: 20px 0 6px; font-size: 15px; font-weight: 620; break-after: avoid; }
p { margin: 8px 0; color: var(--ink-2); }
strong { color: var(--ink); font-weight: 620; }
ul, ol { margin: 8px 0; padding-left: 20px; color: var(--ink-2); }
li { margin: 4px 0; }
li::marker { color: var(--accent); }
table { width: 100%; margin: 12px 0; border-collapse: collapse; font-size: 13px; break-inside: avoid; }
th { text-align: left; font-size: 11.5px; font-weight: 600; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.05em; padding: 8px 10px; border-bottom: 2px solid var(--ink); }
td { padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; color: var(--ink-2); }
td:first-child { color: var(--ink); font-weight: 500; }
code { font: 12.5px ui-monospace, "SF Mono", Consolas, monospace; background: #f1f2f4; padding: 1px 5px; border-radius: 4px; }
.one { margin: 16px 0 4px; padding: 14px 16px; border-left: 3px solid var(--accent); background: var(--tint); color: var(--ink); font-size: 16px; font-weight: 520; border-radius: 0 6px 6px 0; }
.one span { display: block; margin-bottom: 2px; font: 500 11px/1.4 ui-monospace, "SF Mono", Consolas, monospace; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); }
.sign { margin-top: 40px; padding-top: 14px; border-top: 1px solid var(--line); font-size: 12px; color: var(--ink-3); }
@media screen and (max-width: 640px) {
  .sheet { margin: 0; padding: 32px 20px 40px; border: 0; border-radius: 0; }
  h1 { font-size: 30px; }
  dl { grid-template-columns: 1fr; }
  table { display: block; overflow-x: auto; }
}
@page { size: A4; margin: 18mm 16mm 20mm; }
@media print {
  html { background: none; }
  .sheet { max-width: none; margin: 0; padding: 0; border: 0; border-radius: 0; }
  h2 { break-after: avoid; }
  li, tr { break-inside: avoid; }
}
</style>
</head>
<body>
<main class="sheet">
<header class="cover">
${logoTag(o.logo)}
<span class="kicker">${pt ? "Escopo" : "Scope"}</span>
<h1>${esc(title)}</h1>
${metaHtml ? `<dl>${metaHtml}</dl>` : ""}
</header>
${content}
${o.by ? `<p class="sign">${esc(o.by)}</p>` : ""}
</main>
</body>
</html>`;
}

// ---------------------------------------------------------------- browser
async function launch() {
  const { chromium } = await import("playwright-core");
  const tries = [{ channel: "chrome" }, { channel: "msedge" }];
  if (process.env.CHROME_PATH) tries.unshift({ executablePath: process.env.CHROME_PATH });
  for (const t of tries) {
    try {
      return await chromium.launch(t);
    } catch {}
  }
  throw new Error("Chrome/Edge not found. Set CHROME_PATH to the Chrome executable.");
}

// ---------------------------------------------------------------- main
const o = parseArgs(process.argv.slice(2));
const src = resolve(o.file);
if (!existsSync(src)) {
  console.error(`not found: ${src}`);
  process.exit(1);
}
const doc = splitDoc(readFileSync(src, "utf8"));
const outDir = resolve(o.out ?? dirname(src));
mkdirSync(outDir, { recursive: true });
const name = basename(src, extname(src));
const htmlFile = join(outDir, `${name}.html`);
writeFileSync(htmlFile, html(doc, o));
console.log("ok", htmlFile);

if (o.pdf) {
  const browser = await launch();
  const page = await browser.newPage();
  await page.goto(pathToFileURL(htmlFile).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  const footer = `<div style="width:100%;padding:0 16mm;font:9px system-ui,sans-serif;color:#80838c;display:flex;justify-content:space-between"><span>${esc(doc.title)}${o.by ? ` · ${esc(o.by)}` : ""}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`;
  const pdfFile = join(outDir, `${name}.pdf`);
  await page.pdf({ path: pdfFile, format: "A4", printBackground: true, displayHeaderFooter: true, headerTemplate: "<span></span>", footerTemplate: footer, preferCSSPageSize: true });
  await browser.close();
  console.log("ok", pdfFile);
}
