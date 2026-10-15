// Desktop windows for product walkthroughs: a clean browser (URL pill, loading bar) and a plain app window.
// Place them in the world (the camera frames them); chapters build real UI into `body`.
import { h, css, clamp } from "../core/anim.js";
import { bezier } from "../core/ease.js";

export const WIN_IN = bezier(0.25, 0.9, 0.12, 1);
export const WIN_OUT = bezier(0.6, 0, 0.8, 0.2);

const LOCK = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M7 11h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2z M8 11V7a4 4 0 0 1 8 0v4" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

/** A browser window at world (x, y), size w×h. setUrl(text), setLoad(u 0..1). top = chrome height. */
export function browserWindow({ x, y, w, h: hh, url = "" }) {
  const urlText = h("span", { text: url });
  const load = h("div", { class: "win-load" });
  const bar = h("div", { class: "win-bar" },
    h("i", { style: { background: "#ff5f57" } }), h("i", { style: { background: "#febc2e" } }), h("i", { style: { background: "#28c840" } }),
    h("div", { class: "win-url" }, h("span", { class: "lock", html: LOCK }), urlText, load));
  const body = h("div", { class: "win-body" });
  const el = h("div", { class: "win", style: { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${hh}px` } }, bar, body);
  return {
    el, body, x, y, w, h: hh, top: 44,
    setUrl(text) { if (urlText.textContent !== text) urlText.textContent = text; },
    setLoad(u) { css(load, { width: `${(clamp(u) * 100).toFixed(1)}%`, opacity: u > 0 && u < 1 ? "1" : "0" }); },
  };
}

/** A plain app window (title bar with traffic lights and an optional title). */
export function appWindow({ x, y, w, h: hh, title = "", dark = false }) {
  const bar = h("div", { class: `win-bar${dark ? " dark" : ""}` },
    h("i", { style: { background: "#ff5f57" } }), h("i", { style: { background: "#febc2e" } }), h("i", { style: { background: "#28c840" } }),
    title ? h("div", { class: "win-title", text: title }) : null);
  const body = h("div", { class: "win-body" });
  const el = h("div", { class: `win${dark ? " dark" : ""}`, style: { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${hh}px` } }, bar, body);
  return { el, body, x, y, w, h: hh, top: 44 };
}

/**
 * Window poses as pure functions of t. Push functions (t) => ({x, y, s, o}) | null; the first that answers
 * wins, else the rest pose. Call apply(t) every frame — never leave a window where the last frame put it.
 */
export function poser(el) {
  const list = [];
  return {
    list,
    push(f) { list.push(f); },
    apply(t, post = null) {
      let p = null;
      for (const f of list) {
        p = f(t);
        if (p) break;
      }
      p = { x: 0, y: 0, s: 1, o: 1, ...(p || {}) };
      if (post) p = post(p, t);
      css(el, { transform: `translate(${p.x.toFixed(2)}px, ${p.y.toFixed(2)}px) scale(${p.s.toFixed(5)})`, opacity: p.o.toFixed(3), display: p.o > 0.001 ? "block" : "none" });
      return p;
    },
  };
}

/** A window that slides in from the right at tIn and out at tOut (x offset in px). */
export function slideX(t, tIn, tOut = 1e9, { dist = 1650, dur = 0.8 } = {}) {
  if (t < tOut) return (1 - WIN_IN(clamp((t - tIn) / dur))) * dist;
  return WIN_OUT(clamp((t - tOut) / (dur * 0.88))) * dist;
}
