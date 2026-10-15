#!/usr/bin/env node
/**
 * motion-video-skill pipeline.
 *
 *   node engine/make.mjs <project> all            everything below, in order
 *   node engine/make.mjs <project> prepare        build/ folder, media frames
 *   node engine/make.mjs doctor                   what is installed and what is missing
 *   node engine/make.mjs <project> voices         time the voice files in voices/ (or placeholders)
 *   node engine/make.mjs <project> stills [t...]  PNG stills + contact sheet, timeline, warnings
 *   node engine/make.mjs <project> frames         every frame, for the video
 *   node engine/make.mjs <project> audio          music + sound effects + voices -> soundtrack.wav
 *   node engine/make.mjs <project> encode         out/<name>.mp4 + a contact sheet of it
 *   node engine/make.mjs <project> check          transcribes the final mix (faster-whisper), per line
 *   node engine/make.mjs gallery [folder]         every sound effect and music style as MP3s (docs/sounds)
 *
 * Options: --fps 30 (faster; default story.format.fps or 60), --import (re-time every voice file),
 *          --force (render even with problems left; never for a video you deliver).
 * Env: FFMPEG, PYTHON, CHROME_PATH, WHISPER_MODEL.
 */
import { execFileSync, spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { findBrowser, launchBrowser, NO_BROWSER } from "./browser.mjs";

const ENGINE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(ENGINE, "..");
const args = process.argv.slice(2);
const flag = (name) => { const i = args.indexOf(`--${name}`); if (i < 0) return null; const v = args[i + 1]; args.splice(i, v && !v.startsWith("--") ? 2 : 1); return v ?? true; };
const fpsFlag = flag("fps");
const reimport = flag("import");
const forceRender = flag("force");
const [projectArg, step = "all", ...rest] = args;
if (projectArg === "doctor") {
  // Everything the engine needs, found or missing, with the fix for each.
  const ok = (good, label, fix) => { console.log(`${good ? "✓" : "✗"} ${label}${good ? "" : `  →  ${fix}`}`); return good; };
  const py = [process.env.PYTHON, join(ROOT, ".venv/bin/python"), "python3", "python"].find((p) => p && spawnSync(p, ["-c", "import sys"]).status === 0);
  const pyHas = (mod) => py && spawnSync(py, ["-c", `import ${mod}`]).status === 0;
  const ff = process.env.FFMPEG || (spawnSync("ffmpeg", ["-version"]).status === 0 ? "ffmpeg" : pyHas("imageio_ffmpeg") ? "imageio-ffmpeg" : null);
  let all = true;
  all &= ok(Number(process.versions.node.split(".")[0]) >= 18, `Node ${process.versions.node}`, "Node 18 or newer");
  all &= ok(existsSync(join(ROOT, "node_modules/playwright-core")), "Node dependencies", `npm install (in ${ROOT})`);
  all &= ok(Boolean(findBrowser()), `Browser: ${findBrowser() ?? "none"}`, NO_BROWSER);
  all &= ok(Boolean(py), `Python: ${py ?? "none"}`, "Python 3");
  all &= ok(pyHas("numpy") && pyHas("scipy"), "numpy + scipy", "pip install -r requirements.txt");
  all &= ok(Boolean(ff), `ffmpeg: ${ff ?? "none"}`, "install ffmpeg, or pip install imageio-ffmpeg");
  ok(pyHas("faster_whisper"), "faster-whisper (optional: precise voice timings, voice checks)", "pip install faster-whisper");
  console.log(all ? "ready" : "missing pieces above");
  process.exit(all ? 0 : 1);
}
if (projectArg === "gallery") {
  // Every sound effect and music style, as MP3s, into docs/sounds (or a folder you name).
  const py = [process.env.PYTHON, join(ROOT, ".venv/bin/python"), "python3"].find((p) => p && spawnSync(p, ["-c", "import numpy"]).status === 0);
  const r = spawnSync(py, [join(ENGINE, "sound.py"), "--gallery", resolve(step === "all" ? join(ROOT, "docs/sounds") : step)], { stdio: "inherit" });
  process.exit(r.status ?? 1);
}
if (!projectArg) { console.log(readFileSync(fileURLToPath(import.meta.url), "utf8").split("*/")[0]); process.exit(1); }

const PROJECT = resolve(projectArg);
const BUILD = join(PROJECT, "build");
const story = JSON.parse(readFileSync(join(PROJECT, "story.json"), "utf8"));
const FPS = Number(fpsFlag ?? story.format?.fps ?? 60);
const W = story.format?.width ?? 1080, H = story.format?.height ?? 1920;
const slug = (story.title ?? basename(PROJECT)).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "video";

/* ---------------------------------------------------------------- tools */
function findPython() {
  for (const p of [process.env.PYTHON, join(ROOT, ".venv/bin/python"), join(ROOT, ".venv/Scripts/python.exe"), "python3", "python"]) {
    if (!p) continue;
    const r = spawnSync(p, ["-c", "import sys; print(sys.version_info[0])"], { encoding: "utf8" });
    if (r.status === 0) return p;
  }
  throw new Error("Python 3 not found. Create the venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt");
}
let PY = null;
const python = () => (PY ??= findPython());
function findFfmpeg() {
  if (process.env.FFMPEG) return process.env.FFMPEG;
  if (spawnSync("ffmpeg", ["-version"]).status === 0) return "ffmpeg";
  const r = spawnSync(python(), ["-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"], { encoding: "utf8" });
  if (r.status === 0) return r.stdout.trim();
  throw new Error("ffmpeg not found. Install it (brew install ffmpeg / apt install ffmpeg) or: pip install imageio-ffmpeg");
}
let FF = null;
const ffmpeg = (...a) => execFileSync((FF ??= findFfmpeg()), ["-hide_banner", "-loglevel", "error", "-y", ...a], { stdio: ["ignore", "inherit", "inherit"] });
const probe = (file) => spawnSync((FF ??= findFfmpeg()), ["-hide_banner", "-i", file], { encoding: "utf8" }).stderr;
const run = (cmd, a) => { const r = spawnSync(cmd, a, { stdio: "inherit" }); if (r.status !== 0) throw new Error(`${cmd} ${a.join(" ")} failed`); };
const log = (...m) => console.log("›", ...m);

/* ---------------------------------------------------------------- prepare */
const IMAGE = new Set([".png", ".jpg", ".jpeg", ".webp"]);
const VIDEO = new Set([".mp4", ".mov", ".webm", ".m4v", ".mkv", ".gif"]);
function extractMedia() {
  const manifestPath = join(BUILD, "media.json");
  const old = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, "utf8")) : {};
  const out = {};
  for (const [id, spec] of Object.entries(story.media ?? {})) {
    const variants = typeof spec === "string" ? { full: spec } : spec;
    out[id] = {};
    for (const [variant, rel] of Object.entries(variants)) {
      const src = resolve(PROJECT, rel);
      if (!existsSync(src)) throw new Error(`media ${id}.${variant}: ${rel} not found`);
      const dir = `frames/${id}-${variant}`;
      const abs = join(BUILD, dir);
      const stamp = `${src}:${statSync(src).mtimeMs}`;
      if (old[id]?.[variant]?.stamp === stamp && existsSync(abs)) { out[id][variant] = old[id][variant]; continue; }
      rmSync(abs, { recursive: true, force: true });
      mkdirSync(abs, { recursive: true });
      const ext = extname(src).toLowerCase();
      let fps = 24, frameExt = "jpg";
      if (statSync(src).isDirectory()) {
        const files = readdirSync(src).filter((f) => IMAGE.has(extname(f).toLowerCase())).sort();
        files.forEach((f, i) => ffmpeg("-i", join(src, f), "-q:v", "3", join(abs, `${String(i + 1).padStart(4, "0")}.jpg`)));
        fps = variants.fps ?? 24;
      } else if (IMAGE.has(ext)) {
        // PNG stays PNG so a transparent logo keeps its transparency.
        frameExt = ext === ".png" ? "png" : "jpg";
        ffmpeg("-i", src, ...(frameExt === "jpg" ? ["-q:v", "2"] : []), join(abs, `0001.${frameExt}`));
      } else if (VIDEO.has(ext)) {
        const m = probe(src).match(/(\d+(?:\.\d+)?) fps/);
        fps = m ? Number(m[1]) : 24;
        ffmpeg("-i", src, "-q:v", "3", join(abs, "%04d.jpg"));
      } else throw new Error(`media ${id}.${variant}: unsupported file type ${ext}`);
      const count = readdirSync(abs).length;
      out[id][variant] = { dir, count, fps, ext: frameExt, stamp };
      log(`media ${id}.${variant}: ${count} frame(s) @ ${fps} fps`);
    }
  }
  writeFileSync(manifestPath, JSON.stringify(out, null, 1));
  writeFileSync(join(BUILD, "media.js"), `window.MEDIA = ${JSON.stringify(out)};\n`);
}
function writeVoicesJs() {
  const p = join(PROJECT, "voices", "voices.json");
  const v = existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : {};
  writeFileSync(join(BUILD, "voices.js"), `window.VOICES = ${JSON.stringify(v)};\n`);
}
function prepare() {
  mkdirSync(BUILD, { recursive: true });
  const font = story.style?.font ?? "Geist";
  const weights = story.style?.fontWeights ?? [500, 600, 700, 800];
  const html = readFileSync(join(ENGINE, "player.html"), "utf8").replace(/family=[^"]+&display=block/, `family=${encodeURIComponent(font).replace(/%20/g, "+")}:wght@${weights.join(";")}&display=block`);
  writeFileSync(join(BUILD, "player.html"), html);
  copyFileSync(join(ENGINE, "engine.js"), join(BUILD, "engine.js"));
  writeFileSync(join(BUILD, "story.js"), `window.STORY = ${JSON.stringify(story)};\n`);
  writeVoicesJs();
  extractMedia();
  log(`build ready: ${join(BUILD, "player.html")}`);
}

/* ---------------------------------------------------------------- browser */
async function withPage(fn) {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage({ viewport: { width: W, height: H } });
    page.on("pageerror", (e) => console.error("page error:", e.message));
    await page.goto(`file://${join(BUILD, "player.html")}?capture=1`);
    await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
    const info = await page.evaluate(() => ({ cues: window.cues, meta: window.meta, timeline: window.timeline, warnings: window.warnings, problems: window.problems }));
    writeFileSync(join(BUILD, "cues.json"), JSON.stringify(info.cues, null, 1));
    writeFileSync(join(BUILD, "meta.json"), JSON.stringify(info.meta, null, 1));
    return await fn(page, info);
  } finally { await browser.close(); }
}
function printTimeline(info) {
  console.log("\n  scene        type        start    len   voice");
  for (const s of info.timeline) console.log(`  ${s.key.padEnd(12)} ${s.type.padEnd(10)} ${s.start.toFixed(2).padStart(6)} ${s.len.toFixed(2).padStart(6)}   ${s.voice == null ? "-" : s.voice.toFixed(2) + "s"}`);
  console.log(`  total ${info.meta.duration.toFixed(2)}s\n`);
  if (info.warnings.length) { console.log("  NOTES (fixed automatically, better fixed in story.json)"); info.warnings.forEach((w) => console.log("  · " + w)); console.log(); }
  if (info.problems.length) { console.log("  PROBLEMS (fix every one in story.json; the video will not render until you do)"); info.problems.forEach((w) => console.log("  ✗ " + w)); console.log(); }
}
const shot = (page, path) => page.locator("#frame").screenshot({ path, type: "jpeg", quality: 92 });

async function stills(times) {
  const dir = join(BUILD, "stills");
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  await withPage(async (page, info) => {
    printTimeline(info);
    // Default: two moments per scene (just after it settles, and near its end).
    const ts = times.length ? times.map(Number) : info.timeline.flatMap((s) => [s.start + Math.min(0.9, s.len * 0.35), s.start + s.len * 0.85]);
    for (const [i, t] of ts.entries()) { await page.evaluate((x) => window.seek(x), t); await shot(page, join(dir, `${String(i).padStart(3, "0")}-t${t.toFixed(2)}.jpg`)); }
    const cols = Math.min(10, ts.length);
    const tw = Math.round(270 * (W / Math.max(W, H)) * (H > W ? 1 : 1.6)), th = Math.round((tw * H) / W);
    ffmpeg("-pattern_type", "glob", "-i", join(dir, "*.jpg"), "-vf", `scale=${tw}:${th},tile=${cols}x${Math.ceil(ts.length / cols)}:padding=4:color=white`, "-frames:v", "1", join(BUILD, "contact-sheet.jpg"));
    log(`${ts.length} stills in ${dir}`);
    log(`contact sheet: ${join(BUILD, "contact-sheet.jpg")} (times: ${ts.map((t) => t.toFixed(2)).join(", ")})`);
  });
}

async function frames() {
  const dir = join(BUILD, "frames-out");
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  await withPage(async (page, info) => {
    printTimeline(info);
    if (info.problems.length && !forceRender) throw new Error(`${info.problems.length} problem(s) above: fix them in story.json, then run again`);
    const n = Math.round(info.meta.duration * FPS);
    const t0 = Date.now();
    for (let f = 0; f < n; f++) {
      await page.evaluate((x) => window.seek(x), f / FPS);
      await shot(page, join(dir, `${String(f).padStart(5, "0")}.jpg`));
      if (f % Math.round(FPS * 5) === 0) process.stdout.write(`\r› frames ${f}/${n}  (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
    }
    process.stdout.write(`\r› frames ${n}/${n} done in ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
    writeFileSync(join(dir, "fps.txt"), String(FPS));
  });
}

function audio() {
  if (!existsSync(join(BUILD, "meta.json"))) throw new Error("run stills or frames first (they export the cues)");
  run(python(), [join(ENGINE, "sound.py"), PROJECT]);
  const levels = join(BUILD, "voice-levels.json");
  const low = existsSync(levels) ? JSON.parse(readFileSync(levels, "utf8")).filter((r) => r.voiceOverBackgroundDb < 12) : [];
  if (low.length && !forceRender) throw new Error(`voice buried under the music in: ${low.map((r) => r.key).join(", ")}. Lower music.volume or remove sounds under those lines, then run audio again.`);
}

function encode() {
  const dir = join(BUILD, "frames-out");
  const fps = Number(readFileSync(join(dir, "fps.txt"), "utf8"));
  mkdirSync(join(PROJECT, "out"), { recursive: true });
  const out = join(PROJECT, "out", `${slug}.mp4`);
  const wav = join(BUILD, "soundtrack.wav");
  const audioArgs = existsSync(wav) ? ["-i", wav, "-c:a", "aac", "-b:a", "192k", "-shortest"] : [];
  ffmpeg("-framerate", String(fps), "-i", join(dir, "%05d.jpg"), ...audioArgs, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out);
  const every = Math.max(1, Math.round(fps * 1.5));
  const shots = Math.ceil(readdirSync(dir).filter((f) => f.endsWith(".jpg")).length / every);
  const cols = W > H ? 6 : 10;
  ffmpeg("-i", out, "-vf", `select='not(mod(n\\,${every}))',scale=${W > H ? 360 : 216}:-2,tile=${cols}x${Math.ceil(shots / cols)}:padding=4:color=white`, "-frames:v", "1", join(PROJECT, "out", `${slug}-sheet.jpg`));
  log(`video: ${out}`);
  log(`sheet: ${join(PROJECT, "out", `${slug}-sheet.jpg`)} (one frame every 1.5 s)`);
}

/* ---------------------------------------------------------------- steps */
const steps = {
  prepare,
  voices: () => { run(python(), [join(ENGINE, "voices.py"), PROJECT, ...(reimport ? ["--import"] : [])]); prepare(); },
  stills: () => stills(rest),
  frames,
  audio,
  encode,
  check: () => run(python(), [join(ENGINE, "voices.py"), PROJECT, "--check", join(BUILD, "soundtrack.wav")]),
  all: async () => { prepare(); await steps.voices(); await frames(); audio(); encode(); },
};
if (!steps[step]) { console.error(`unknown step "${step}". Steps: ${Object.keys(steps).join(", ")}`); process.exit(1); }
if (["stills", "frames"].includes(step)) prepare();
try { await steps[step](); } catch (e) { console.error("✗", e.message); process.exit(1); }
