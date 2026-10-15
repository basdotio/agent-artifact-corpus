#!/usr/bin/env node
// Unpacks Claude Design project files that were read through the browser pane (reference/claude-design.md, "Reading a project").
//
// The files never go through a download: the page's own API returns them to a `javascript_tool` call, and a result
// that large is saved whole by the harness as a `tool-results/*.txt` file: a JSON array `[{type, text}]` whose `text`
// is the JSON-quoted return value of the snippet:
//   JSON.stringify({ "<path>": { status, contentType, content: <base64> }, … })
//
// Usage: node unpack.mjs <tool-result.txt> <out-dir>
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const [source, outDir] = process.argv.slice(2);
if (!source || !outDir) { console.error("usage: node unpack.mjs <tool-result.txt> <out-dir>"); process.exit(2); }
const fail = (message) => { console.error(`unpack: ${message}`); process.exit(1); };

const raw = JSON.parse(await readFile(source, "utf8"));
const parts = Array.isArray(raw) ? raw.filter((part) => part?.type === "text" && typeof part.text === "string") : [];
if (parts.length === 0) fail("not a saved tool result (expected a JSON array with a text part)");

// One part per tool call; a batch prefixes each with "[tool:action] ". The tool appends a note after the value, so
// take the leading JSON string only, and the first part that holds the files.
function filesOf(text) {
  const quoted = /^\s*(?:\[[\w:.-]+\]\s*)?("(?:[^"\\]|\\.)*")/s.exec(text);
  if (!quoted) return null;
  try {
    const value = JSON.parse(JSON.parse(quoted[1]));
    const entries = value && typeof value === "object" && !Array.isArray(value) ? Object.values(value) : [];
    return entries.length > 0 && entries.every((file) => file && typeof file === "object" && "status" in file) ? value : null;
  } catch { return null; }
}
const files = parts.map((part) => filesOf(part.text)).find(Boolean);
if (!files) fail("no part of the result is the snippet's JSON: return JSON.stringify({ path: { status, contentType, content } }) from it");

await mkdir(outDir, { recursive: true });
const root = path.resolve(outDir);
for (const [name, file] of Object.entries(files)) {
  const target = path.resolve(root, name);
  if (target !== root && !target.startsWith(root + path.sep)) fail(`refusing a path outside the output directory: ${name}`);
  if (file?.status !== 200 || typeof file.content !== "string") fail(`${name}: status ${file?.status ?? "?"}, no content`);
  const bytes = Buffer.from(file.content, "base64");
  await mkdir(path.dirname(target), { recursive: true });
  await writeFile(target, bytes);
  console.log(`${name}  ${file.contentType ?? "?"}  ${bytes.length} bytes`);
}
