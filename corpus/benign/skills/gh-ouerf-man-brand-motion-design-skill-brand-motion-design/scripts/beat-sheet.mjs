#!/usr/bin/env node
/**
 * The beat sheet the product owner reads, generated from cues.js.
 *
 *   node scripts/beat-sheet.mjs videos/<film> > videos/<film>/BEATSHEET.md
 */
import { resolve } from "node:path";
import { label, loadCues, seconds } from "./cues-lib.mjs";

const film = resolve(process.argv[2] || ".");
const cues = loadCues(film);
const g = cues.grid;
const rows = [];
for (const s of cues.scenes || []) rows.push({ t: seconds(cues, s.from), end: seconds(cues, s.to), kind: "scene", what: `**${s.name}**${s.what ? ": " + s.what : ""}` });
for (const e of cues.events || []) rows.push({ t: seconds(cues, e.at), kind: e.sfx ? `event + ${e.sfx}` : "event", what: e.what || "" });
rows.sort((a, b) => a.t - b.t || (a.kind === "scene" ? -1 : 1));

const out = [];
out.push(`# Beat sheet: ${cues.title || "film"}`);
out.push("");
out.push(`${cues.width}x${cues.height}, ${cues.duration}s, ${g.bpm} BPM ${g.beatsPerBar || 4}/4: a beat is ${(60 / g.bpm).toFixed(3)}s, a bar ${((60 / g.bpm) * (g.beatsPerBar || 4)).toFixed(3)}s.` + (cues.music ? ` Music: ${cues.music.src}${cues.music.license ? " (" + cues.music.license + ")" : ""}.` : " Silent."));
out.push("");
out.push("| bar.beat | seconds | frame @60 | kind | what |");
out.push("|---|---|---|---|---|");
for (const r of rows) {
  const span = r.end !== undefined ? `${r.t.toFixed(2)} to ${r.end.toFixed(2)}` : r.t.toFixed(2);
  out.push(`| ${label(cues, r.t)} | ${span} | ${Math.round(r.t * 60)} | ${r.kind} | ${r.what} |`);
}
// dead-bar check: every bar should have at least one event
// whole bars only: a partial last bar is the ring-out, allowed to be still
const bars = Math.floor((cues.duration - (g.firstBeat || 0)) / ((60 / g.bpm) * (g.beatsPerBar || 4)) + 1e-6);
const busy = new Set(rows.filter((r) => r.kind !== "scene").map((r) => Math.floor(Number(label(cues, r.t).split(".")[0]))));
const dead = [];
for (let b = 1; b <= bars; b++) if (!busy.has(b)) dead.push(b);
out.push("");
out.push(dead.length ? `Bars with no event (check they are not dead): ${dead.join(", ")}` : "Every bar has at least one event.");
console.log(out.join("\n"));
