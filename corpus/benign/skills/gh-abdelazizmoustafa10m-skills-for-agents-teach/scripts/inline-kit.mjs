#!/usr/bin/env node
// inline-kit.mjs — inline the shared visual kit into a lesson's <style id="kit"> and
// <script id="kit"> tags, producing a self-contained, offline lesson file.
// Write the lesson body with empty `<style id="kit"></style>` and `<script id="kit"></script>`,
// then run:  node scripts/inline-kit.mjs ./lessons/NNNN-name.html [more.html ...]
// Re-running keeps a lesson in sync with the current kit. Dependency-free, offline.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(resolve(here, "../assets/lesson-kit.css"), "utf8").trim();
const js  = readFileSync(resolve(here, "../assets/lesson-kit.js"), "utf8").trim();

const files = process.argv.slice(2);
if (files.length === 0) {
  console.error("usage: node inline-kit.mjs <lesson.html> [...]");
  process.exit(2);
}

// Replace inner content of <TAG id="kit">…</TAG>. Uses a replacer function so that
// `$` in the kit source can't be interpreted as a replacement pattern.
function inlineTag(html, tag, payload) {
  const re = new RegExp(`(<${tag}[^>]*\\bid=["']kit["'][^>]*>)[\\s\\S]*?(</${tag}>)`, "i");
  if (!re.test(html)) return null;
  return html.replace(re, (_m, open, close) => open + "\n" + payload + "\n" + close);
}

let failed = false;
for (const file of files) {
  let html;
  try { html = readFileSync(resolve(file), "utf8"); }
  catch (e) { console.error(`✗ ${file}: ${e.message}`); failed = true; continue; }

  const withCss = inlineTag(html, "style", css);
  if (withCss === null) { console.error(`✗ ${file}: no <style id="kit"> tag to inline into`); failed = true; continue; }
  const withJs = inlineTag(withCss, "script", js);
  if (withJs === null) { console.error(`✗ ${file}: no <script id="kit"> tag to inline into`); failed = true; continue; }

  writeFileSync(resolve(file), withJs);
  console.log(`✓ ${file} — kit inlined (${(Buffer.byteLength(withJs) / 1024).toFixed(1)} KB, self-contained)`);
}
process.exit(failed ? 1 : 0);
