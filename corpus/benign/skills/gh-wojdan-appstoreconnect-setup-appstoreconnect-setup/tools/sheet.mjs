#!/usr/bin/env node
// Puts a language's frames side by side at a third of their width, the size they have in the store's search results:
// the claim has to read there. Writes store/out/<lang>/sheet.jpg, or store/out/<lang>/<set>/sheet.jpg with --set.
// Usage: node sheet.mjs <lang> [more languages…] [--set <name>]        (run from the project's root)
import { readdir } from "node:fs/promises";
import path from "node:path";
import { inStore, sharp, shown, takeSet } from "./lib.mjs";

const langs = process.argv.slice(2), set = takeSet(langs);
if (!langs.length) { console.error("usage: node sheet.mjs <lang> [more languages…] [--set <name>]"); process.exit(2); }
for (const lang of langs) {
  const dir = inStore("out", lang, ...(set ? [set] : []));
  const files = (await readdir(dir)).filter((f) => /^frame-\d+\.png$/.test(f)).sort((a, b) => parseInt(a.slice(6)) - parseInt(b.slice(6)));
  if (!files.length) { console.error(`${shown(dir)}: no frames, render them first`); process.exitCode = 1; continue; }
  const first = await sharp()(path.join(dir, files[0])).metadata();
  const width = Math.round(first.width / 3), height = Math.round(first.height / 3), gap = 12;
  const tiles = await Promise.all(files.map(async (f, i) => ({ input: await sharp()(path.join(dir, f)).resize(width, height).toBuffer(), left: gap + i * (width + gap), top: gap })));
  const out = path.join(dir, "sheet.jpg");
  await sharp()({ create: { width: gap + files.length * (width + gap), height: height + 2 * gap, channels: 3, background: "#ffffff" } }).composite(tiles).jpeg({ quality: 86 }).toFile(out);
  console.log(`${shown(out)}  ${files.length} frames at ${width} x ${height}`);
}
