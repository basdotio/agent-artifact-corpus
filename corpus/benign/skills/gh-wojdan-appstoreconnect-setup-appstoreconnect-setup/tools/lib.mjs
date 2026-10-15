// Shared by the three renderers: where the project's store folder is, its configuration, the browser, and what a
// language changes on a page besides its texts (lang, dir, the faces of its script, where its lines may break).
import { createRequire } from "node:module";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const toolsDir = path.dirname(fileURLToPath(import.meta.url));
// A missing file or field is the user's to fix: say it in one line, without a stack.
process.on("uncaughtException", (error) => { console.error(`error: ${error.message}`); process.exit(1); });
/** The project's store folder: `store/` under the current directory, or STORE_DIR. */
export const storeDir = path.resolve(process.env.STORE_DIR ?? "store");
export const inStore = (...parts) => path.join(storeDir, ...parts);
export const shown = (file) => (path.relative(process.cwd(), file).startsWith("..") ? file : path.relative(process.cwd(), file));

export async function readJson(file) {
  try { return JSON.parse(await readFile(file, "utf8")); }
  catch (error) { throw new Error(`${shown(file)}: ${error.code === "ENOENT" ? "no such file" : error.message}`); }
}
export const config = async () => readJson(inStore("store.config.json"));

/** Takes `--set <name>` out of the arguments: a further set of screenshots (another platform or display), or none. */
export function takeSet(args) {
  const at = args.indexOf("--set");
  if (at < 0) return null;
  const [, name] = args.splice(at, 2);
  if (!name) throw new Error("--set needs a name: one of frames.sets in store.config.json");
  return name;
}
/** The frames' settings: the first set's, or a named set's on top of them. A set has a size and a claim width of its own. */
export function frameSet(cfg, set) {
  const { sets = {}, ...first } = cfg.frames ?? {};
  if (!set) return first;
  if (!sets[set]) throw new Error(`store.config.json has no frames.sets.${set}` + (Object.keys(sets).length ? ` (it has: ${Object.keys(sets).join(", ")})` : ""));
  if (!Array.isArray(sets[set].css)) throw new Error(`frames.sets.${set} in store.config.json needs "css": the frame's size in CSS px`);
  const { css, claimWidth, ...shared } = first;
  return { ...shared, ...sets[set] };
}

/** A package from the tools' own node_modules, or from the workspace STORE_KIT_MODULES names. */
export function need(...names) {
  for (const base of [process.env.STORE_KIT_MODULES, toolsDir, process.cwd()].filter(Boolean)) {
    const require = createRequire(path.join(path.resolve(base), "package.json"));
    for (const name of names) try { return require(name); } catch { /* the next place */ }
  }
  throw new Error(`cannot find ${names.join(" or ")}: run "npm install" and "npx playwright install chromium" in ${shown(toolsDir)}, or set STORE_KIT_MODULES to a workspace that has them`);
}
export const chromium = () => need("playwright", "@playwright/test").chromium;
export const sharp = () => need("sharp");

export const escape = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** Fills `{{field}}` in a template; `special` maps a field to ready HTML (the claim, the header's lines). */
export function fill(template, fields, where, special = {}) {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (key in special) return special[key];
    if (!(key in fields)) throw new Error(`${where}: "${key}" is missing`);
    return escape(fields[key]);
  });
}

/** `<style>` blocks of the kit's files (config `css`), then of the project's own files that exist. */
export async function styles(cfg, ...own) {
  let out = "";
  for (const file of cfg.css ?? []) out += `<style>${await readFile(inStore(file), "utf8")}</style>\n`;
  for (const file of own) if (existsSync(inStore(file))) out += `<style>${await readFile(inStore(file), "utf8")}</style>\n`;
  return out;
}
export const fontLinks = (cfg) => (cfg.fontLinks ?? []).map((href) => `<link rel="stylesheet" href="${escape(href)}">`).join("\n");

// ---- languages -------------------------------------------------------------------------------------------------
const HTML_LANG = { pt: "pt-PT", "pt-br": "pt-BR", zh: "zh-Hans", "zh-hant": "zh-Hant" };
const RTL = ["ar", "he", "fa", "ur"];
// The system's face for a script the kit's faces cannot write, behind the kit's own.
const FACES = {
  ja: `"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Noto Sans JP"`,
  ko: `"Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR"`,
  zh: `"PingFang SC", "Microsoft YaHei", "Noto Sans SC"`,
  "zh-hant": `"PingFang TC", "Microsoft JhengHei", "Noto Sans TC"`,
  ar: `"SF Arabic", "Geeza Pro", "Noto Sans Arabic", "Segoe UI", Tahoma`,
  fa: `"SF Arabic", "Geeza Pro", "Noto Sans Arabic", "Segoe UI", Tahoma`,
  ur: `"SF Arabic", "Geeza Pro", "Noto Nastaliq Urdu", "Segoe UI", Tahoma`,
  he: `"SF Hebrew", "Arial Hebrew", "Noto Sans Hebrew", "Segoe UI"`,
  th: `"Thonburi", "Noto Sans Thai", "Leelawadee UI"`,
  hi: `"Kohinoor Devanagari", "Noto Sans Devanagari", "Nirmala UI"`,
};
// A display face is usually set tight; these scripts need the line let out.
const LEADING = { ja: 1.25, ko: 1.25, zh: 1.25, "zh-hant": 1.25, ar: 1.4, fa: 1.4, ur: 1.6, he: 1.25, th: 1.4, hi: 1.4 };
// Scripts that may break a line between any two characters: without help a title leaves one character alone on its
// last line. Japanese also breaks between phrases, not inside a word; Korean keeps its words whole.
const ANY_BREAK = ["ja", "ko", "zh", "zh-hant"];

export const htmlLang = (code) => HTML_LANG[code] ?? code;
export const direction = (code) => (RTL.includes(code.split("-")[0]) ? "rtl" : "ltr");
export const htmlAttributes = (code) => `lang="${htmlLang(code)}"${direction(code) === "rtl" ? ' dir="rtl"' : ""}`;

/**
 * The CSS a script needs on top of the kit. Empty for a language the kit's faces write, so its page is the kit's own.
 * `cfg.fontVariables` names the kit's font variables and their faces, e.g. {"--font-display": "\"Inter\""};
 * `cfg.balance.titles` and `.hints` are selector lists of the texts that get balanced lines and a taller line.
 */
export function scriptCss(cfg, code, moreTitles = "") {
  const faces = FACES[code] ?? FACES[code.split("-")[0]];
  if (!faces) return "";
  const titles = [cfg.balance?.titles, moreTitles].filter(Boolean).join(", "), hints = cfg.balance?.hints ?? "";
  const balanced = [titles, hints].filter(Boolean).join(", ");
  const variables = Object.entries(cfg.fontVariables ?? {}).map(([name, own]) => `${name}: ${[own, faces, "system-ui", "sans-serif"].filter(Boolean).join(", ")};`).join(" ");
  return `
${variables ? `:root { ${variables} }` : ""}
* { letter-spacing: 0 !important; }
${code === "ko" ? "body { word-break: keep-all; }" : ""}${code === "ja" ? "body { word-break: auto-phrase; }" : ""}
${ANY_BREAK.includes(code) ? `body { text-wrap: pretty; }${balanced ? `\n:is(${balanced}) { text-wrap: balance !important; }` : ""}` : ""}
${titles ? `:is(${titles}) { line-height: ${LEADING[code] ?? LEADING[code.split("-")[0]] ?? 1.25} !important; }` : ""}`;
}

/** The project's own right-to-left rules (`rtl.css`: what its kit places with left and right), when the language needs them. */
export async function rtlCss(code) {
  if (direction(code) !== "rtl" || !existsSync(inStore("rtl.css"))) return "";
  return await readFile(inStore("rtl.css"), "utf8");
}

export async function openPage(html, viewport, scale) {
  const browser = await chromium().launch();
  const page = await (await browser.newContext({ viewport, deviceScaleFactor: scale })).newPage();
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(600);
  return { browser, page };
}
