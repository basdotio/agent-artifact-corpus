#!/usr/bin/env node
// Renders the App Store search-results video (3:2, a seamless loop) for one language: builds a page from the kit,
// store/video/scenario.json, the card templates in store/video/cards/ and store/video/texts/<lang>.json, captures it
// frame by frame and encodes it with ffmpeg, with store/video/bgm.wav as the soundtrack when the file is there.
// Usage (from the project's root):
//   node render-video.mjs <lang> [scale] [out.mp4]     scale 1 is the scenario's size (1920 x 1280), 2 doubles it
//   node render-video.mjs <lang> stills [out-dir]      only scene-1.png … (the middle of each scene), nothing encoded:
//                                                      a look at a language's line breaks and cards in seconds
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { copyFile, mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { config, direction, escape, fill, fontLinks, htmlAttributes, inStore, openPage, readJson, rtlCss, scriptCss, shown, styles, toolsDir } from "./lib.mjs";

const [lang, modeArg = "1", outArg] = process.argv.slice(2);
if (!lang) { console.error("usage: node render-video.mjs <lang> [scale] [out.mp4]  |  node render-video.mjs <lang> stills [out-dir]"); process.exit(2); }
const stills = modeArg === "stills", scale = stills ? 1 : Number(modeArg);
if (!stills && scale !== 1 && scale !== 2) { console.error(`"${modeArg}" is not a scale: 1 (the scenario's size), 2 (twice that) or "stills"`); process.exit(2); }
if (!stills && spawnSync("ffmpeg", ["-version"]).error) { console.error("error: ffmpeg is not on the path; install it first (the stills need none)"); process.exit(1); }
const cfg = await config();
const s = {
  fps: 30, sceneSeconds: 3.75, transitionSeconds: 1.1, size: [1920, 1280],
  // The content block: text on one side, one card on the other. 1084 x 515 shown at 1.5 is what was used in October
  // 2026 and nothing was cut in the preview of App Store Connect; Apple publishes no safe area in pixels.
  block: [1084, 515], blockZoom: 1.5, textWidth: 560, cardsWidth: 476,
  card: [340, 358], cardZoom: 1.4, cardTitle: ".card__title", maxTitleLines: 2, gainDb: 0,
  ...(await readJson(inStore("video", "scenario.json"))),
};
const SCENES = s.scenes, [W, H] = s.size;
const out = path.resolve(outArg ?? (stills ? inStore("out", lang, "scenes") : inStore("out", lang, scale === 1 ? "search-video.mp4" : `search-video-${W * scale}.mp4`)));

const texts = await readJson(inStore("video", "texts", `${lang}.json`));
if (texts.scenes.length !== SCENES.length) throw new Error(`video/texts/${lang}.json needs ${SCENES.length} scenes`);
const card = async (name) => fill(await readFile(inStore("video", "cards", `${name}.html`), "utf8"), texts.cards?.[name] ?? {}, `video/texts/${lang}.json: cards.${name}`);
// The first scene comes back at the end, so the last frame equals the first and the loop has no seam.
const order = [...SCENES.keys(), 0];
const layers = { bg: "", text: "", card: "" };
for (const [i, n] of order.entries()) {
  layers.bg += `<div class="v-bg v-tone--${SCENES[n].tone}" data-i="${i}"><span class="v-shape"></span></div>`;
  layers.text += `<div class="v-text v-tone--${SCENES[n].tone}" data-i="${i}"><h1 class="v-title">${texts.scenes[n].map((line) => `<span>${escape(line)}</span>`).join("")}</h1></div>`;
  layers.card += `<div class="v-card" data-i="${i}">${await card(SCENES[n].card)}</div>`;
}

// Right to left: the text on the right, the card on the left, and the card flips from the left.
const rtl = direction(lang) === "rtl";
// How the scenes move: the project's own store/video/motion.js, or the default (the card flips, the background fades,
// the text fades with a slight scale).
const ownMotion = inStore("video", "motion.js");
const motion = await readFile(existsSync(ownMotion) ? ownMotion : path.join(toolsDir, "motion-default.js"), "utf8");
const html = `<!DOCTYPE html><html ${htmlAttributes(lang)}><head><meta charset="utf-8">
${fontLinks(cfg)}
${await styles(cfg)}<style>
html, body { margin: 0; }
.v-stage { position: relative; overflow: hidden; isolation: isolate; width: ${W}px; height: ${H}px; }
.v-bg { position: absolute; inset: 0; overflow: hidden; background: var(--scene-bg, #eee); }
.v-wrap { position: absolute; inset: 0; z-index: 10; display: grid; place-items: center; }
.v-block { position: relative; zoom: ${s.blockZoom}; width: ${s.block[0]}px; height: ${s.block[1]}px; }
.v-texts { position: absolute; ${rtl ? "right" : "left"}: 0; top: 0; bottom: 0; width: ${s.textWidth}px; }
.v-text { position: absolute; inset: 0; display: flex; align-items: center; background: none; transform-origin: ${rtl ? "100%" : "0"} 50%; }
.v-title { margin: 0; font: 800 86px/1 system-ui, sans-serif; color: var(--scene-ink, #111); }
.v-title > span { display: block; white-space: nowrap; }
.v-cards { position: absolute; ${rtl ? "left" : "right"}: 0; top: 0; bottom: 0; width: ${s.cardsWidth}px; perspective: 1800px; }
.v-card { position: absolute; inset: 0; display: flex; align-items: center; backface-visibility: hidden; }
.v-card > * { zoom: ${s.cardZoom}; flex: none; box-sizing: border-box; width: ${s.card[0]}px; height: ${s.card[1]}px; }
</style>
${await styles({}, "video/video.css")}<style>
${scriptCss(cfg, lang, `.v-title, ${s.cardTitle}`)}
${await rtlCss(lang)}
</style></head><body><div ${cfg.rootAttributes ?? ""}><div class="v-stage" id="stage">${layers.bg}<div class="v-wrap"><div class="v-block"><div class="v-texts">${layers.text}</div><div class="v-cards">${layers.card}</div></div></div></div></div>
<script>
const N = ${SCENES.length}, D = ${s.sceneSeconds}, TR = ${s.transitionSeconds}, RTL = ${rtl};
${motion}
window.renderAt(0);
</script></body></html>`;

const frames = await mkdtemp(path.join(tmpdir(), "store-video-"));
const { browser, page } = await openPage(html, { width: W, height: H }, scale);
let warnings = 0;
const warn = (text) => { warnings++; console.error(`warning: ${text}`); };
try {
  const stage = await page.$("#stage");
  // The cards have one height, made for the source language. A language whose tallest card needs more gets all of
  // its cards that much taller, still centred; a language that fits is not touched.
  const needs = () => page.evaluate((scenes) => Math.max(...[...document.querySelectorAll(".v-card")].slice(0, scenes).map((c) => c.firstElementChild.scrollHeight - c.firstElementChild.clientHeight)), SCENES.length);
  let grown = 0;
  for (let more = await needs(), round = 0; more > 0 && round < 4; more = await needs(), round++) {
    grown += more;
    await page.addStyleTag({ content: `.v-card > * { height: ${s.card[1] + grown}px; }` });
  }
  if (grown) {
    const over = Math.round((s.card[1] + grown) * s.cardZoom - s.block[1]);
    console.log(`the cards are ${s.card[1] + grown} px high, ${grown} more than ${s.card[1]}` + (over > 0 ? `; they stand ${over} px taller than the content block` : ""));
  }
  // What does not fit: a line of a scene text wider than the text column, a card title in too many lines, a card
  // whose content is taller than the card even after the cards grew.
  const fit = await page.evaluate(({ scenes, titleSelector, maxLines, textWidth }) => {
    const ink = (e) => { const range = document.createRange(); range.selectNodeContents(e); return range; };
    const column = document.querySelector(".v-texts").getBoundingClientRect().width, wide = [], tall = [];
    for (const text of [...document.querySelectorAll(".v-text")].slice(0, scenes)) for (const line of text.querySelectorAll(".v-title > span")) {
      const share = ink(line).getBoundingClientRect().width / column;
      if (share > 1) wide.push(`${line.textContent} (${Math.round(share * textWidth)} px)`);
    }
    const cards = [...document.querySelectorAll(".v-card")].slice(0, scenes);
    for (const title of cards.flatMap((c) => [...c.querySelectorAll(titleSelector)])) {
      const lines = new Set([...ink(title).getClientRects()].map((r) => Math.round(r.top))).size;
      if (lines > maxLines) tall.push(`${title.textContent} (${lines} lines)`);
    }
    const cut = cards.map((c, n) => {
      const box = c.firstElementChild, edge = box.getBoundingClientRect().bottom;
      const text = [...box.querySelectorAll("*")].find((e) => !e.closest("svg") && [...e.childNodes].some((x) => x.nodeType === 3 && x.textContent.trim()) && ink(e).getBoundingClientRect().bottom > edge + 0.5);
      return { n: n + 1, by: box.scrollHeight - box.clientHeight, text: text?.textContent.trim() ?? null };
    }).filter((c) => c.by > 0);
    return { wide, tall, cut };
  }, { scenes: SCENES.length, titleSelector: s.cardTitle, maxLines: s.maxTitleLines, textWidth: s.textWidth });
  for (const line of fit.wide) warn(`the line "${line}" is wider than the ${s.textWidth} px text column`);
  for (const title of fit.tall) warn(`the card title "${title}" is in more than ${s.maxTitleLines} lines`);
  for (const c of fit.cut) warn(`the card of scene ${c.n} still needs ${c.by} px more` + (c.text ? `: "${c.text}" is cut` : ""));

  if (stills) {
    await mkdir(out, { recursive: true });
    for (const n of SCENES.keys()) {
      await page.evaluate((t) => window.renderAt(t), (n + 0.4) * s.sceneSeconds);
      await stage.screenshot({ path: path.join(out, `scene-${n + 1}.png`) });
    }
    console.log(`${shown(path.join(out, "scene-1.png"))} … scene-${SCENES.length}.png`);
  } else {
    const count = Math.round(SCENES.length * s.sceneSeconds * s.fps), name = (n) => path.join(frames, `f${String(n).padStart(5, "0")}.png`);
    for (let n = 0; n < count; n++) {
      await page.evaluate((t) => window.renderAt(t), n / s.fps);
      await stage.screenshot({ path: name(n) });
    }
    // The last frame has to be the first one, or the loop shows a seam. The browser now and then paints a text that
    // has been scaled and has landed again with one column of an edge a shade off. A difference that small (under a
    // hundredth of a percent of the picture) is the browser's, not the scenario's: the first frame then stands in as
    // the last. Anything larger is a real seam and stays as painted, with the warning.
    const first = await readFile(name(0)), last = await readFile(name(count - 1));
    if (!first.equals(last)) {
      const seam = await page.evaluate(async ([a, b]) => {
        const pixels = async (png) => {
          const bitmap = await createImageBitmap(await (await fetch("data:image/png;base64," + png)).blob(), { colorSpaceConversion: "none", premultiplyAlpha: "none" });
          const context = new OffscreenCanvas(bitmap.width, bitmap.height).getContext("2d", { willReadFrequently: true });
          context.drawImage(bitmap, 0, 0);
          return context.getImageData(0, 0, bitmap.width, bitmap.height).data;
        };
        const one = await pixels(a), other = await pixels(b);
        let differing = 0;
        for (let i = 0; i < one.length; i += 4) if (one[i] !== other[i] || one[i + 1] !== other[i + 1] || one[i + 2] !== other[i + 2]) differing++;
        return { differing, all: one.length / 4 };
      }, [first.toString("base64"), last.toString("base64")]);
      if (seam.differing <= seam.all / 10000) {
        await copyFile(name(0), name(count - 1));
        console.log(`the browser painted ${seam.differing} pixels of the last frame a shade off; the first frame stands in for it, the loop point is exact`);
      } else warn(`the last frame differs from the first in ${seam.differing} pixels, the loop will show a seam`);
    }
    await browser.close();
    await mkdir(path.dirname(out), { recursive: true });
    const music = inStore("video", "bgm.wav");
    const args = ["-y", "-loglevel", "error", "-framerate", String(s.fps), "-i", path.join(frames, "f%05d.png")];
    if (existsSync(music)) args.push("-i", music, "-map", "0:v", "-map", "1:a", "-af", `volume=${s.gainDb}dB`, "-c:a", "aac", "-b:a", "256k", "-ar", "48000");
    // H.264 stops at level 5.2 (36864 macroblocks). Above that size the video is HEVC: Apple's hardware decoder
    // dropped frames on an H.264 level 6.0 encode of 3840 x 2560, which showed as stutter.
    const h264 = W * scale * H * scale <= 36864 * 256;
    args.push(...(h264 ? ["-c:v", "libx264", "-preset", "slow", "-crf", "14"] : ["-c:v", "libx265", "-preset", "medium", "-crf", "16", "-tag:v", "hvc1", "-x265-params", "log-level=error"]),
              "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
              "-t", String(SCENES.length * s.sceneSeconds), "-movflags", "+faststart", out);
    const encoded = spawnSync("ffmpeg", args, { stdio: "inherit" });
    if (encoded.error || encoded.status !== 0) throw new Error(`ffmpeg failed${encoded.error ? ` (${encoded.error.code})` : ""}; nothing was written`);
    console.log(`${shown(out)}  ${count} frames, ${W * scale} x ${H * scale}, ${h264 ? "H.264" : "HEVC"}${existsSync(music) ? ", with bgm.wav" : ", silent"}`);
  }
  console.log(warnings ? `${warnings} warning(s)` : "no warnings");
} finally {
  await browser.close().catch(() => {});
  await rm(frames, { recursive: true, force: true });
}
