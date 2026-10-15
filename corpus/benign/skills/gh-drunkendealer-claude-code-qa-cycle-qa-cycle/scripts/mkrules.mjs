#!/usr/bin/env node
// mkrules.mjs [--config qa.config.json] [--out dir]
// Fills references/fixer-rules.template.md and verifier-rules.template.md from the project config.
// {{a.b}} scalar · {{join:a}} array joined with "; " ("none yet" when empty) · {{lines:a}} array as "- " bullets (line dropped when empty).
// An existing output that differs is kept once as <name>.bak. Unresolved placeholders are an error.
import { readFileSync, writeFileSync, existsSync, copyFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { configPath } from "./lib.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const a = process.argv.slice(2);
const opt = (n, d) => (a.includes(n) ? a[a.indexOf(n) + 1] : d);
const cfgPath = resolve(opt("--config", configPath()));
const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
cfg.main ??= "main";
cfg.sandboxDir ??= "sbx";
cfg.sandboxRoot = resolve(process.env.QA_SCRATCH ?? cfg.scratch ?? "", cfg.sandboxDir);
const out = resolve(opt("--out", cfg.tooling ?? dirname(cfgPath)));
const get = (path) => path.split(".").reduce((o, k) => o?.[k], cfg);

const fill = (tpl, missing) => {
  const expand = (s) => s.replace(/\{\{([\w.]+)\}\}/g, (_, p) => { const v = get(p); if (v == null || typeof v === "object") { missing.add(p); return _; } return expand(String(v)); });
  return tpl
    .replace(/^\{\{lines:([\w.]+)\}\}\n/gm, (_, p) => { const v = get(p); if (v != null && !Array.isArray(v)) missing.add(p); return (v ?? []).map((l) => "- " + expand(l)).join("\n") + (v?.length ? "\n" : ""); })
    .replace(/\{\{join:([\w.]+)\}\}/g, (_, p) => { const v = get(p); if (v != null && !Array.isArray(v)) missing.add(p); return v?.length ? expand(v.join("; ")) : "none yet"; })
    .replace(/\{\{signin\}\}/g, () => (cfg.signin ? `\n  Sign-in helper: \`${expand(cfg.signin)}\`.` : ""))
    .replace(/\{\{([\w.]+)\}\}/g, (_, p) => { const v = get(p); if (v == null || typeof v === "object") { missing.add(p); return _; } return expand(String(v)); });
};

for (const [tpl, name] of [["fixer-rules.template.md", "FIXRULES.md"], ["verifier-rules.template.md", "VERIFYRULES.md"]]) {
  const missing = new Set();
  const text = fill(readFileSync(join(here, "../references", tpl), "utf8"), missing);
  if (missing.size) { console.error(`${name}: config is missing ${[...missing].join(", ")}`); process.exit(1); }
  const dest = join(out, name);
  if (existsSync(dest) && readFileSync(dest, "utf8") !== text && !existsSync(dest + ".bak")) copyFileSync(dest, dest + ".bak");
  writeFileSync(dest, text);
  console.log("wrote", dest);
}
