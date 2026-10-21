#!/usr/bin/env node
// validate-lesson.mjs — enforce the HTML Lesson Contract (references/HTML-LESSON.md).
// Dependency-free, offline. Usage: node scripts/validate-lesson.mjs <file.html> [more.html ...]
// Exit 0 = all pass, 1 = any failure. Warnings never fail the build.
import { readFileSync } from "node:fs";

const files = process.argv.slice(2);
if (files.length === 0) {
  console.error("usage: node validate-lesson.mjs <lesson.html> [...]");
  process.exit(2);
}

// Strip HTML comments and CSS/JS block comments so that a lesson merely *mentioning*
// a forbidden token in prose/comments (e.g. "no @import", a taught `TODO`) doesn't fail.
const stripComments = h => h.replace(/<!--[\s\S]*?-->/g, "").replace(/\/\*[\s\S]*?\*\//g, "");

const attrValue = (attrs, name) => {
  const re = new RegExp(`\\b${name}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s"'=<>` + "`" + `]+))`, "i");
  const m = attrs.match(re);
  return m ? (m[1] ?? m[2] ?? m[3] ?? "") : null;
};
const hasAttr = (attrs, name) => new RegExp(`\\b${name}\\b`, "i").test(attrs);
const classHas = (attrs, name) => {
  const value = attrValue(attrs, "class");
  return value ? new RegExp(`(^|\\s)${name}(\\s|$)`).test(value) : false;
};
const pageStyle = h => {
  const blocks = [];
  for (const m of h.matchAll(/<style\b[^>]*\bid\s*=\s*["']page["'][^>]*>([\s\S]*?)<\/style>/gi)) {
    blocks.push(m[1]);
  }
  return blocks.join("\n");
};
const labelForIds = h => {
  const ids = new Set();
  for (const m of h.matchAll(/<label\b([^>]*)>/gi)) {
    const id = attrValue(m[1], "for");
    if (id) ids.add(id);
  }
  return ids;
};
const isWrappedByLabel = (h, index) => {
  const before = h.slice(0, index).toLowerCase();
  const open = before.lastIndexOf("<label");
  const close = before.lastIndexOf("</label");
  return open > close && h.toLowerCase().indexOf("</label", index) !== -1;
};
const controlsHaveLabels = h => {
  const labelledIds = labelForIds(h);
  const controlRe = /<(input|textarea)\b([^>]*)>/gi;
  for (const m of h.matchAll(controlRe)) {
    const tag = m[1].toLowerCase();
    const attrs = m[2];
    if (tag === "input" && (attrValue(attrs, "type") || "").toLowerCase() === "hidden") continue;
    if (hasAttr(attrs, "aria-label") || hasAttr(attrs, "aria-labelledby")) continue;
    const id = attrValue(attrs, "id");
    if (id && labelledIds.has(id)) continue;
    if (isWrappedByLabel(h, m.index)) continue;
    return false;
  }
  return true;
};
const imagesHaveAlt = h => {
  for (const m of h.matchAll(/<img\b([^>]*)>/gi)) {
    if (!hasAttr(m[1], "alt")) return false;
  }
  return true;
};
const svgsHaveNames = h => {
  for (const m of h.matchAll(/<svg\b([^>]*)>([\s\S]*?)<\/svg>/gi)) {
    const attrs = m[1];
    const body = m[2];
    const roleImgWithLabel = (attrValue(attrs, "role") || "").toLowerCase() === "img" && hasAttr(attrs, "aria-label");
    const titleChild = /<title\b[^>]*>\s*[^<\s][\s\S]*?<\/title>/i.test(body);
    if (!roleImgWithLabel && !titleChild) return false;
  }
  return true;
};

// PRESENCE checks run on the raw HTML (a landmark inside a comment shouldn't count anyway,
// but these are structural and safe on raw). {name, test, msg, level}.
const PRESENCE = [
  ["non-empty <title>",        h => /<title>\s*\S[^<]*<\/title>/i.test(h), "missing or empty <title>", "error"],
  ["meta teach:lesson",        h => /<meta[^>]+name=["']teach:lesson["']/i.test(h), "missing <meta name=\"teach:lesson\">", "error"],
  ["meta teach:contract",      h => /<meta[^>]+name=["']teach:contract["']/i.test(h), "missing <meta name=\"teach:contract\">", "error"],
  ["a .lede win",              h => /class=["'][^"']*\blede\b/.test(h), "missing the .lede (one-sentence tangible win)", "error"],
  [".cite footer",             h => /class=["'][^"']*\bcite\b/.test(h), "missing the .cite footer (primary source)", "error"],
  ["citation link present",    h => /class=["'][^"']*\bcite\b[\s\S]{0,600}?<a[^>]+href=["']https?:/i.test(h), "no primary-source link inside .cite", "error"],
  ["≥1 recall widget",         h => /class=["'][^"']*\b(quiz|cloze|flip|worked|sequence|match|predict)\b/.test(h), "no recall surface (need a .quiz / .cloze / .flip / .worked / .sequence / .match / .predict)", "error"],
  ["inlined kit present",      h => /<style[^>]*id=["']kit["'][^>]*>[\s\S]*:root[\s\S]*<\/style>/i.test(h), "kit CSS not inlined into <style id=\"kit\">", "error"],
  ["html lang set",            h => /<html[^>]+lang=/i.test(h), "no lang on <html> (a11y)", "warn"],
  ["viewport meta",            h => /<meta[^>]+name=["']viewport["']/i.test(h), "no viewport meta (mobile)", "warn"],
  ["prefers-reduced-motion",   h => /prefers-reduced-motion/i.test(h), "no reduced-motion handling", "warn"],
  ["print styles",             h => /@media\s+print/i.test(h), "no @media print block", "warn"],
];

// FORBIDDEN checks run on comment-stripped HTML (real code only, not prose about code).
const FORBIDDEN = [
  ["no unresolved markers",    h => !/\bREPLACE_?ME\b/i.test(h) && !/\{\{/.test(h) && !/__KIT_/.test(h), "unresolved placeholder ({{…}} / REPLACE_ME / __KIT_)", "error"],
  ["no remote <script src>",   h => !/<script[^>]+src\s*=\s*["']?(https?:)?\/\//i.test(h), "external <script src> — inline it instead (offline rule)", "error"],
  ["no remote <link href>",    h => !/<link[^>]+href\s*=\s*["']?(https?:)?\/\//i.test(h), "external <link href> (CSS/font/CDN) — inline it (offline rule)", "error"],
  ["no remote <img src>",      h => !/<img[^>]+src\s*=\s*["']?(https?:)?\/\//i.test(h), "external <img src> — use inline SVG or a data: URI", "error"],
  ["no @import rule",          h => !/@import\s+(url\(|["'])/i.test(h), "@import pulls an external sheet — inline it (offline rule)", "error"],
  ["no url(http…)",            h => !/url\(\s*["']?https?:/i.test(h), "url(http…) fetches a remote asset (offline rule)", "error"],
  ["<img> alt text",           imagesHaveAlt, "<img> without alt text", "error"],
  ["inline SVG name",          svgsHaveNames, "inline <svg> needs role=\"img\" + aria-label, or a <title> child", "error"],
  ["form labels",              controlsHaveLabels, "<input>/<textarea> without an associated label", "error"],
  ["page style token colors",  h => !/(^|[^\\])#[0-9a-f]{3,8}\b/i.test(pageStyle(h)), "raw hex colour in <style id=\"page\">; prefer kit tokens", "warn"],
  ["page style token lengths", h => !/\b\d*\.?\d+px\b/i.test(pageStyle(h)), "raw px value in <style id=\"page\">; prefer kit tokens", "warn"],
];
const CHECKS_RAW = PRESENCE;
const CHECKS_STRIPPED = FORBIDDEN;

let hadError = false;
for (const file of files) {
  let html;
  try { html = readFileSync(file, "utf8"); }
  catch (e) { console.error(`\n✗ ${file}\n  cannot read: ${e.message}`); hadError = true; continue; }

  const stripped = stripComments(html);
  const errors = [], warns = [];
  const run = (checks, src) => {
    for (const [name, test, msg, level] of checks) {
      let ok = false;
      try { ok = test(src); } catch { ok = false; }
      if (!ok) (level === "error" ? errors : warns).push(msg);
    }
  };
  run(CHECKS_RAW, html);
  run(CHECKS_STRIPPED, stripped);

  if (errors.length === 0) {
    console.log(`\n✓ ${file}  —  contract OK${warns.length ? ` (${warns.length} warning${warns.length>1?"s":""})` : ""}`);
  } else {
    hadError = true;
    console.log(`\n✗ ${file}  —  ${errors.length} error${errors.length>1?"s":""}`);
    for (const m of errors) console.log(`    error:  ${m}`);
  }
  for (const m of warns) console.log(`    warn:   ${m}`);
}

console.log("");
process.exit(hadError ? 1 : 0);
