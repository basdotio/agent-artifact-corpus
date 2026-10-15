#!/usr/bin/env node
/**
 * Write the film's <audio> tags from cues.js, so music and every sound effect
 * land exactly on their cues. HyperFrames only mixes <audio> elements that are
 * in the HTML with an id, so this generates static markup between two markers
 * in index.html:
 *
 *   <!-- pf:audio -->  ...generated...  <!-- /pf:audio -->
 *
 *   node scripts/place-audio.mjs videos/<film>
 *
 * cues.js provides:
 *   CUES.music = { src: "assets/audio/bed.wav", volume: 1, start: 0 }       (optional)
 *   CUES.sfx   = { dir: "assets/audio/sfx", peaks: "assets/audio/sfx/peaks.json" }
 *   CUES.events = [{ at: [bar, beat, fraction] | seconds, sfx: "ping", volume: 0.4, what: "..." }]
 * Each effect starts at cue - peak, so its transient lands on the frame.
 */
import { readFileSync, writeFileSync, existsSync, openSync, readSync, closeSync } from "node:fs";
import { join, resolve } from "node:path";
import { loadCues, seconds } from "./cues-lib.mjs";

const film = resolve(process.argv[2] || ".");

/** Seconds of a PCM WAV from its header (no decoder needed). null if unknown. */
function wavSeconds(path) {
  try {
    const fd = openSync(path, "r");
    const head = Buffer.alloc(4096);
    readSync(fd, head, 0, 4096, 0);
    closeSync(fd);
    if (head.toString("ascii", 0, 4) !== "RIFF") return null;
    let off = 12, byteRate = 0;
    while (off + 8 <= head.length) {
      const id = head.toString("ascii", off, off + 4), size = head.readUInt32LE(off + 4);
      if (id === "fmt ") byteRate = head.readUInt32LE(off + 16);
      if (id === "data") return byteRate ? size / byteRate : null;
      off += 8 + size + (size % 2);
    }
  } catch {}
  return null;
}
const cues = loadCues(film);
const indexPath = join(film, "index.html");
const html = readFileSync(indexPath, "utf8");
if (!html.includes("<!-- pf:audio -->") || !html.includes("<!-- /pf:audio -->")) {
  console.error("index.html needs the markers <!-- pf:audio --> and <!-- /pf:audio --> inside the composition root.");
  process.exit(1);
}
const tags = [];
let track = 20;
if (cues.music && cues.music.src) {
  if (!existsSync(join(film, cues.music.src))) console.warn(`warning: ${cues.music.src} does not exist yet`);
  tags.push(
    `<audio id="pf-music" data-timeline-role="music" src="${cues.music.src}" data-start="${cues.music.start || 0}" data-duration="${cues.duration}" data-track-index="${track++}" data-volume="${cues.music.volume ?? 1}"></audio>`,
  );
}
const peaks = cues.sfx && cues.sfx.peaks && existsSync(join(film, cues.sfx.peaks)) ? JSON.parse(readFileSync(join(film, cues.sfx.peaks), "utf8")) : {};
let n = 0;
const lanes = []; // end time of the last effect on each sfx track: effects never overlap on one track
for (const e of (cues.events || []).filter((e) => e.sfx).sort((a, b) => seconds(cues, a.at) - seconds(cues, b.at))) {
  const at = seconds(cues, e.at);
  const peak = peaks[e.sfx] ?? 0;
  const start = Math.max(0, at - peak);
  const src = `${cues.sfx.dir}/${e.sfx}.wav`;
  if (!existsSync(join(film, src))) console.warn(`warning: ${src} does not exist`);
  const len = Math.min(wavSeconds(join(film, src)) ?? 1, cues.duration - start);
  let lane = lanes.findIndex((end) => end <= start);
  if (lane === -1) lane = lanes.push(0) - 1;
  lanes[lane] = start + len;
  tags.push(
    `<audio id="pf-sfx-${String(++n).padStart(2, "0")}-${e.sfx}" src="${src}" data-start="${start.toFixed(4)}" data-duration="${len.toFixed(4)}" data-track-index="${track + lane}" data-volume="${e.volume ?? 0.4}"></audio>`,
  );
}
const block = "<!-- pf:audio -->\n      " + tags.join("\n      ") + "\n      <!-- /pf:audio -->";
writeFileSync(indexPath, html.replace(/<!-- pf:audio -->[\s\S]*?<!-- \/pf:audio -->/, block));
console.log(`placed ${tags.length} audio tags (${n} effects) in index.html`);
