#!/usr/bin/env node
/**
 * Set up (or refresh) a film project: a HyperFrames project with the kit and
 * vendored runtimes, so nothing loads from the network at render time.
 *
 *   node scripts/setup.mjs videos/<film> [--size 1080x1920] [--katex] [--no-three] [--force]
 *
 * - runs `npx hyperframes init` if the folder has no hyperframes.json
 * - copies templates/kit/*.js into <film>/kit/ and templates/index.html,
 *   cues.js into <film>/ (only when missing, unless --force)
 * - vendors gsap and Three.js with its add-ons (unless --no-three; KaTeX with --katex)
 *   from npm into <film>/vendor/
 * - rewrites any CDN <script src> for gsap to the vendored file
 * - writes a .gitignore for renders, snapshots and licensed audio
 */
import { execFileSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const GSAP = "3.14.2";
const KATEX = "0.16.22";
const THREE = "0.181.2";
const skill = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const dir = args.find((a) => !a.startsWith("--"));
const flag = (n) => args.includes(n);
const value = (n, d) => (args.includes(n) ? args[args.indexOf(n) + 1] : d);
if (!dir) {
  console.error("usage: node scripts/setup.mjs <film-dir> [--size 1080x1920] [--katex] [--no-three] [--force]");
  process.exit(1);
}
const film = resolve(dir);
const [W, H] = value("--size", "1080x1920").split("x").map(Number);
const run = (cmd, list, cwd) => execFileSync(cmd, list, { cwd, stdio: ["ignore", "pipe", "inherit"], encoding: "utf8" });

if (!existsSync(join(film, "hyperframes.json"))) {
  mkdirSync(dirname(film), { recursive: true });
  if (existsSync(film) && readdirSync(film).length) {
    console.error(`${film} is not empty and has no hyperframes.json. Use an empty folder.`);
    process.exit(1);
  }
  console.log("hyperframes init ...");
  run("npx", ["-y", "hyperframes@latest", "init", film, "--non-interactive"], dirname(film));
}

// kit
mkdirSync(join(film, "kit"), { recursive: true });
cpSync(join(skill, "templates", "kit"), join(film, "kit"), { recursive: true });

// starter files
const copyTemplate = (name, transform = (s) => s) => {
  const to = join(film, name);
  const fresh = !existsSync(to) || flag("--force");
  const initStub = existsSync(to) && readFileSync(to, "utf8").includes("// Example: tl.fromTo");
  if (fresh || initStub) writeFileSync(to, transform(readFileSync(join(skill, "templates", name), "utf8")));
};
copyTemplate("index.html", (s) => s.replaceAll("__W__", String(W)).replaceAll("__H__", String(H)));
copyTemplate("cues.js", (s) => s.replaceAll("__W__", String(W)).replaceAll("__H__", String(H)));

// vendored runtimes from npm tarballs
const vendor = join(film, "vendor");
mkdirSync(vendor, { recursive: true });
const unpack = (spec) => {
  const tmp = mkdtempSync(join(tmpdir(), "pf-"));
  const tgz = run("npm", ["pack", spec, "--silent"], tmp).trim().split("\n").pop();
  run("tar", ["-xzf", tgz], tmp);
  return { root: join(tmp, "package"), done: () => rmSync(tmp, { recursive: true, force: true }) };
};
if (!existsSync(join(vendor, "gsap.min.js")) || flag("--force")) {
  const p = unpack(`gsap@${GSAP}`);
  cpSync(join(p.root, "dist", "gsap.min.js"), join(vendor, "gsap.min.js"));
  p.done();
  console.log(`vendored gsap ${GSAP}`);
}
if (flag("--katex") && (!existsSync(join(vendor, "katex", "katex.min.js")) || flag("--force"))) {
  const p = unpack(`katex@${KATEX}`);
  mkdirSync(join(vendor, "katex"), { recursive: true });
  for (const f of ["katex.min.js", "katex.min.css"]) cpSync(join(p.root, "dist", f), join(vendor, "katex", f));
  cpSync(join(p.root, "dist", "fonts"), join(vendor, "katex", "fonts"), { recursive: true });
  p.done();
  console.log(`vendored katex ${KATEX}`);
}

if (!flag("--no-three") && (!existsSync(join(vendor, "three", "three.module.min.js")) || flag("--force"))) {
  const p = unpack(`three@${THREE}`);
  mkdirSync(join(vendor, "three"), { recursive: true });
  for (const f of ["three.module.min.js", "three.core.min.js", "three.module.js", "three.core.js"]) cpSync(join(p.root, "build", f), join(vendor, "three", f));
  // add-ons for the rich look: post-processing (bloom), studio environment, shaders, geometry utils
  for (const d of ["postprocessing", "shaders", "environments", "utils", "geometries", "math", "lines"]) {
    cpSync(join(p.root, "examples", "jsm", d), join(vendor, "three", "addons", d), { recursive: true });
  }
  p.done();
  console.log(`vendored three ${THREE}`);
}

// no CDN at render time
const index = join(film, "index.html");
if (existsSync(index)) {
  const html = readFileSync(index, "utf8").replace(/https:\/\/cdn\.jsdelivr\.net\/npm\/gsap@[^"']+\/gsap\.min\.js/g, "vendor/gsap.min.js");
  writeFileSync(index, html);
}

const ignore = join(film, ".gitignore");
const lines = ["renders/", "snapshots/", "review/", "out/", "node_modules/", "assets/audio/licensed/"];
const have = existsSync(ignore) ? readFileSync(ignore, "utf8") : "";
writeFileSync(ignore, have + lines.filter((l) => !have.includes(l)).map((l) => l + "\n").join(""));
console.log(`ready: ${film}  (${W}x${H})`);
