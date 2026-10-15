// The film's clock. renderAt(t) poses every active scene for time t — deterministically, from nothing but t.
// Scenes register with scene({...}); sounds are declared with cue(...) so the mix is driven by the picture.
import { h } from "./anim.js";
import { createFinish } from "./fx.js";

/** The format (comp/config.json is the single source of truth; the renderer reads the same file). */
export const CONFIG = await (await fetch(new URL("../config.json", import.meta.url))).json();
export const W = CONFIG.width;
export const H = CONFIG.height;
export const FPS = CONFIG.fps;
export const DURATION = CONFIG.duration;
export const BPM = CONFIG.bpm ?? 120;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
/** Time of bar n / beat n on the music grid (sections should start on bars). */
export const bar = (n) => (CONFIG.gridOffset ?? 0) + n * BAR;
export const beat = (n) => (CONFIG.gridOffset ?? 0) + n * BEAT;

const scenes = [];
const cues = [];
const cuts = [];
const pending = new Set();
let finish = null;

/**
 * scene({ id, start, end, z, samples, softEdges, build(root, s), update(localT, t, s) })
 *  - build runs once after fonts load (measure layout here, while the scene is displayed)
 *  - update must pose EVERYTHING it owns for time t (never rely on the previous frame)
 *  - samples: motion-blur samples this scene needs at t (number or fn(localT, t, s))
 */
export function scene(def) {
  scenes.push(def);
  return def;
}

/** A sound cue at t (seconds). The mix renders one sound per cue; params are free-form. */
export function cue(t, type, params = {}) {
  cues.push({ t: +t.toFixed(5), type, ...params });
}

/** A hard cut at t: the shutter never integrates across it. */
export function cut(t) {
  cuts.push(t);
}

/** Register an async decode (image, video frame) the current frame must wait for. */
export function waitFor(promise) {
  pending.add(promise);
  promise.finally(() => pending.delete(promise));
}

export async function boot() {
  const stage = document.getElementById("stage");
  document.documentElement.style.setProperty("--W", `${W}px`);
  document.documentElement.style.setProperty("--H", `${H}px`);
  Object.assign(stage.style, { width: `${W}px`, height: `${H}px` });
  // every declared face must be loaded before anything is measured or drawn
  await Promise.all([...document.fonts].map((f) => f.load().catch(() => null)));
  await document.fonts.ready;
  scenes.sort((a, b) => (a.z ?? 0) - (b.z ?? 0));
  for (const s of scenes) {
    s.root = h("div", { class: "scene", id: s.id });
    s.root.style.zIndex = String(s.z ?? 0);
    stage.appendChild(s.root);
    if (s.build) {
      s.root.style.display = "block"; // lay out while building, so measurements are real
      await s.build(s.root, s);
      s.root.style.display = "";
    }
  }
  finish = createFinish(stage, CONFIG.finish ?? {});
  await finish.ready;
  window.__ready = true;
}

export async function renderAt(t) {
  for (const s of scenes) {
    const active = t >= s.start && t < s.end;
    if (active !== s._active) {
      s.root.style.display = active ? "block" : "none";
      s._active = active;
    }
    if (active && s.update) s.update(t - s.start, t, s);
  }
  finish.update(t, FPS);
  if (pending.size) await Promise.all([...pending]);
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
}

window.renderAt = renderAt;
window.__config = CONFIG;
window.__scenes = scenes;
/** Motion-blur samples the frame at t needs: the most any active scene asks for. */
window.samplesAt = (t) => {
  let n = 1;
  for (const s of scenes) {
    if (t >= s.start && t < s.end) {
      const v = typeof s.samples === "function" ? s.samples(t - s.start, t, s) : s.samples ?? 1;
      n = Math.max(n, v);
    }
  }
  return n;
};
window.getCues = () => cues.slice().sort((a, b) => a.t - b.t);
/** Keep each shutter sample on the same side of every cut (and hard scene edge) as its frame. */
window.shutterClamp = (t0, list) => {
  const all = cuts.slice();
  for (const s of scenes) if (!s.softEdges) all.push(s.start, s.end);
  return list.map((ts) => {
    let v = ts;
    if (ts > t0) for (const c of all) if (c > t0 && c <= v) v = Math.max(t0, c - 1e-4);
    if (ts < t0) for (const c of all) if (c <= t0 && c > v) v = c;
    return v;
  });
};

/** ?debug — a scrubber: drag, ▶/❚❚ (space), ←/→ one frame, shift+←/→ one second. ?t=12.5 opens there. */
export function mountDebug() {
  const bar_ = h("div", {
    style: {
      position: "fixed", left: "0", right: "0", bottom: "0", height: "44px", background: "rgba(10,8,30,.92)",
      display: "flex", alignItems: "center", gap: "12px", padding: "0 14px", zIndex: 99999,
      fontFamily: "monospace", color: "#fff", fontSize: "14px",
    },
  });
  const play = h("button", { text: "▶", style: { width: "40px", height: "28px" } });
  const range = h("input", { type: "range", min: 0, max: DURATION, step: 1 / FPS, value: 0, style: { flex: 1 } });
  const label = h("span", { text: "0.000" });
  bar_.append(play, range, label);
  document.body.style.height = `${H + 44}px`;
  document.body.appendChild(bar_);
  let playing = false, t0 = 0, s0 = 0;
  const go = async (t) => {
    t = Math.max(0, Math.min(DURATION - 1 / FPS, t));
    range.value = t;
    label.textContent = t.toFixed(3);
    await renderAt(t);
  };
  const toggle = () => {
    playing = !playing;
    play.textContent = playing ? "❚❚" : "▶";
    t0 = performance.now();
    s0 = +range.value;
    const loop = async () => {
      if (!playing) return;
      await go((s0 + (performance.now() - t0) / 1000) % DURATION);
      requestAnimationFrame(loop);
    };
    loop();
  };
  range.oninput = () => go(+range.value);
  play.onclick = toggle;
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space") { e.preventDefault(); toggle(); }
    if (e.code === "ArrowRight") go(+range.value + (e.shiftKey ? 1 : 1 / FPS));
    if (e.code === "ArrowLeft") go(+range.value - (e.shiftKey ? 1 : 1 / FPS));
  });
  const q = new URLSearchParams(location.search);
  go(+(q.get("t") || 0));
}
