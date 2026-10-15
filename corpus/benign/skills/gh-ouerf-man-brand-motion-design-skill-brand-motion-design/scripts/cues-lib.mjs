/** Shared by the scripts: read a film's cues.js (a browser script) in Node. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import vm from "node:vm";

export function loadCues(film) {
  const source = readFileSync(join(film, "cues.js"), "utf8");
  const sandbox = { window: {} };
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox);
  const cues = sandbox.window.CUES;
  if (!cues) throw new Error("cues.js must set window.CUES");
  return cues;
}

/** [bar, beat, fraction] or seconds -> seconds, on the film's grid. */
export function seconds(cues, at) {
  if (typeof at === "number") return at;
  if (typeof at === "string" && /^\d+(\.\d+)?$/.test(at)) return Number(at);
  if (typeof at === "string") at = at.replace(/^b/, "").split(/[.:]/).map(Number);
  const [bar, beat = 1, fraction = 0] = at;
  const g = cues.grid;
  const spb = 60 / g.bpm;
  return (g.firstBeat || 0) + ((g.pickupBeats || 0) + (bar - 1) * (g.beatsPerBar || 4) + (beat - 1) + fraction) * spb;
}

export function label(cues, t) {
  const g = cues.grid;
  const i = (t - (g.firstBeat || 0)) / (60 / g.bpm) - (g.pickupBeats || 0);
  const bpb = g.beatsPerBar || 4;
  const bar = Math.floor(i / bpb) + 1;
  return `${bar}.${(i - (bar - 1) * bpb + 1).toFixed(2)}`;
}
