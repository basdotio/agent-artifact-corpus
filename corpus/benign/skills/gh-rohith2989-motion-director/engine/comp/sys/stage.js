// Stages (full-frame backgrounds) and the panel grammar between sections: the incoming panel slides over the
// outgoing one, which recedes and rounds its corners. Colours come from the theme's CSS variables.
import { h, clamp, css } from "../core/anim.js";
import { bezier, inOutSoft, expoOut } from "../core/ease.js";
import { W, H } from "../core/runtime.js";

/** Background recipes, built from theme tokens (--bg, --bg-2, --accent, --accent-2, --night …). */
const BG = {
  page: "radial-gradient(60% 55% at 8% -6%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 70%), radial-gradient(50% 50% at 96% 0%, color-mix(in srgb, var(--accent-2) 12%, transparent), transparent 70%), var(--bg)",
  soft: "radial-gradient(70% 60% at 50% 0%, rgba(255,255,255,.45), transparent 70%), var(--bg-2)",
  ink: "radial-gradient(60% 70% at 50% 48%, rgba(255,255,255,.035), transparent 72%), var(--ink-bg)",
  brand: "radial-gradient(44% 38% at 10% 8%, rgba(255,255,255,.16), transparent 72%), radial-gradient(38% 32% at 90% 12%, color-mix(in srgb, var(--accent-2) 30%, transparent), transparent 72%), var(--accent)",
  night: "radial-gradient(70% 30% at 50% 104%, color-mix(in srgb, var(--accent) 35%, transparent), transparent 72%), linear-gradient(180deg, var(--night), color-mix(in srgb, var(--night) 70%, var(--accent)))",
  dawn: "radial-gradient(62% 48% at 50% 102%, color-mix(in srgb, var(--accent-2) 85%, white), transparent 78%), linear-gradient(180deg, color-mix(in srgb, var(--night) 60%, var(--accent)), var(--accent) 60%, color-mix(in srgb, var(--accent) 60%, white))",
};

/** stage(kind, {pools, dots}) → { el, update(t) }. pools: two slow drifting pools of light. */
export function stage(kind = "page", { pools = kind === "night" || kind === "dawn" || kind === "brand", dots = false } = {}) {
  const el = h("div", { class: "fill", style: { background: BG[kind] ?? kind } });
  if (dots) el.appendChild(h("div", { class: "fill", style: { backgroundImage: "radial-gradient(circle, rgba(255,255,255,.07) 1.3px, transparent 1.8px)", backgroundSize: "26px 26px" } }));
  let pa = null, pb = null;
  if (pools) {
    pa = h("div", { style: { position: "absolute", left: "-10%", width: "120%", height: "70%", bottom: "-22%", background: "radial-gradient(50% 50% at 50% 50%, color-mix(in srgb, var(--accent-2) 55%, transparent), transparent 70%)" } });
    pb = h("div", { style: { position: "absolute", right: "-12%", top: "-18%", width: "70%", height: "62%", background: "radial-gradient(50% 50% at 50% 50%, color-mix(in srgb, var(--accent) 40%, transparent), transparent 70%)" } });
    el.append(pa, pb);
  }
  return {
    el,
    update(t) {
      if (!pa) return;
      css(pa, { transform: `translate(${(Math.sin((t / 17) * Math.PI * 2) * 60).toFixed(1)}px, ${(Math.cos((t / 17) * Math.PI * 2) * 24).toFixed(1)}px)` });
      css(pb, { transform: `translate(${(Math.cos((t / 23) * Math.PI * 2) * 70).toFixed(1)}px, ${(Math.sin((t / 23) * Math.PI * 2) * 40).toFixed(1)}px)` });
    },
  };
}

/** The slide-over: a panel arriving from below, decelerating like a page settling. */
export const SLIDE = bezier(0.5, 0, 0.1, 1);

export function slideIn(t, t0, dur = 1.0, { from = H + 40 } = {}) {
  const u = SLIDE(clamp((t - t0) / dur));
  return { y: (1 - u) * from, r: 40 * (1 - clamp((t - t0 - dur * 0.7) / (dur * 0.3))), u, done: t >= t0 + dur };
}
/** The outgoing panel: recedes and rounds as the next one covers it. */
export function recede(t, t0, dur = 1.0, { s1 = 0.92, y1 = -36 } = {}) {
  const u = inOutSoft(clamp((t - t0) / dur));
  return { s: 1 + (s1 - 1) * u, y: y1 * u, r: 40 * clamp(u * 3), u };
}
/** Apply a panel state (origin at the frame centre). */
export function panelTf(el, { y = 0, s = 1, r = 0 }, extra = {}) {
  css(el, { transform: `translateY(${y.toFixed(2)}px) scale(${s.toFixed(5)})`, borderRadius: `${r.toFixed(2)}px`, ...extra });
}

/** A circular wipe from a point (e.g. out of a button that was pressed): clip-path for the incoming layer. */
export function circleWipe(el, t, t0, dur, cx, cy, ease = expoOut) {
  const u = ease(clamp((t - t0) / dur));
  const R = Math.hypot(Math.max(cx, W - cx), Math.max(cy, H - cy)) * 1.02;
  css(el, { clipPath: u >= 1 ? "none" : `circle(${(R * u).toFixed(2)}px at ${cx}px ${cy}px)` });
  return u;
}

/** A soft directional mask reveal (left→right by default) for type or panels. */
export function maskReveal(el, t, t0, dur, { dir = "right", feather = 12, ease = expoOut } = {}) {
  const u = ease(clamp((t - t0) / dur));
  const a = (u * (100 + feather)).toFixed(2);
  const b = (u * (100 + feather) - feather).toFixed(2);
  const to = { right: "to right", left: "to left", down: "to bottom", up: "to top" }[dir];
  const m = `linear-gradient(${to}, #000 ${b}%, transparent ${a}%)`;
  css(el, { webkitMaskImage: u >= 1 ? "none" : m, maskImage: u >= 1 ? "none" : m });
  return u;
}
