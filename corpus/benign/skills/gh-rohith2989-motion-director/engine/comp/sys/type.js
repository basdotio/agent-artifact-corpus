// Human typing: a schedule of key times with rhythm (longer after words and punctuation), and the
// cues the score uses for the wooden keyboard.
import { mulberry32 } from "../core/rand.js";
import { cue } from "../core/runtime.js";

export function schedule(text, t0, { cps = 16, jitter = 0.38, seed = 7, until = null } = {}) {
  const r = mulberry32(seed);
  const base = 1 / cps;
  const times = [];
  let t = t0;
  for (let i = 0; i < text.length; i++) {
    times.push(t);
    const c = text[i];
    let d = base * (1 + (r() - 0.5) * 2 * jitter);
    if (c === " ") d += base * 0.45;
    if (/[,.?!—:]/.test(c)) d += base * 1.1;
    t += d;
  }
  if (until != null && times.length > 1) {
    // fit the whole run into [t0, until]
    const k = (until - t0) / (times[times.length - 1] - t0);
    for (let i = 0; i < times.length; i++) times[i] = t0 + (times[i] - t0) * k;
    t = until;
  }
  return { text, times, end: times[times.length - 1] ?? t0 };
}

export function countAt(s, t) {
  let lo = 0, hi = s.times.length;
  while (lo < hi) {
    const m = (lo + hi) >> 1;
    if (s.times[m] <= t) lo = m + 1;
    else hi = m;
  }
  return lo;
}

export const typedAt = (s, t) => s.text.slice(0, countAt(s, t));

/** Register key cues for a schedule (the mix renders a wooden-case key for each). */
export function keyCues(s, { pan = 0, gain = 0, kind = "key" } = {}) {
  s.times.forEach((t, i) => {
    const ch = s.text[i];
    cue(t, kind, { ch: ch === " " ? "space" : ch, pan, gain, i });
  });
}

/** Caret blink: solid while typing (within 0.5 s of a key), blinking at 1.06 Hz when idle. */
export function caretOn(s, t, t0 = -1e9) {
  if (t < t0) return false;
  const last = s.times.filter((x) => x <= t).pop();
  if (last != null && t - last < 0.5) return true;
  const k = t - (last ?? t0);
  return Math.floor(k / 0.53) % 2 === 0;
}
