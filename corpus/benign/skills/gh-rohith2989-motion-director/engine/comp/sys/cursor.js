// A desktop cursor with intent: it travels on gentle arcs, decelerates into its target, turns into a
// hand over anything clickable, and dips when it clicks. Hotspot = (0, 0) of the glyph.
import { h, clamp } from "../core/anim.js";
import { bezier } from "../core/ease.js";

const ARROW = "M0 0 L0 17.2 L4.1 13.4 L6.9 19.7 L9.6 18.6 L6.9 12.4 L12.2 12.4 Z";
const HAND =
  "M-2.2 1.9a2.2 2.2 0 0 1 4.4 0V8.3a1.9 1.9 0 0 1 3.8 0V9.1a1.9 1.9 0 0 1 3.8 0V9.9a1.8 1.8 0 0 1 3.6 0V14.6" +
  "c0 3.4-2.4 5.6-5.6 5.6H1.7c-2 0-3.3-.9-4.3-2.2L-6.8 12.5c-.8-1-.5-2.3.5-2.8.9-.5 2-.2 2.6.6L-2.2 12.2Z";
const HAND_LINES = "M2.2 8.3v3.2M6 9.1v2.9M9.8 9.9v2.6";

/** Move ease: quick to leave, long soft arrival (a hand landing on a target). */
const MOVE = bezier(0.3, 0.02, 0.12, 1);

export function createCursor(parent, { scale = 1.35 } = {}) {
  const arrow = h("svg", { width: 40, height: 40, viewBox: "0 0 20 20", style: { width: `${20 * scale}px`, height: `${20 * scale}px` } },
    h("path", { d: ARROW, fill: "#ffffff", stroke: "#15131c", "stroke-width": 1.15, "stroke-linejoin": "round" }));
  const hand = h("svg", { viewBox: "-8 -1 22 22", style: { width: `${22 * scale}px`, height: `${22 * scale}px`, left: `${-8 * scale}px`, top: `${-1 * scale}px` } },
    h("path", { d: HAND, fill: "#ffffff", stroke: "#15131c", "stroke-width": 1.1, "stroke-linejoin": "round" }),
    h("path", { d: HAND_LINES, fill: "none", stroke: "#15131c", "stroke-width": 0.9, "stroke-linecap": "round" }));
  const el = h("div", { class: "cur" }, arrow, hand);
  parent.appendChild(el);

  const pts = []; // [{t, x, y, arc, ease}]
  const clicks = [];
  const hands = [];
  const vis = []; // visibility windows [t0, t1]; none = always shown

  const api = {
    el,
    /** Start (or teleport) at x, y at time t. */
    at(t, x, y) {
      pts.push({ t, x, y, jump: true });
      return api;
    },
    /** Travel to x, y arriving at t1 (leaving the previous point at t0). arc: sideways bow (fraction of distance). */
    to(t0, t1, x, y, { arc = 0.1, ease = MOVE } = {}) {
      pts.push({ t: t0, hold: true });
      pts.push({ t: t1, x, y, arc, ease });
      return api;
    },
    click(t) {
      clicks.push(t);
      return api;
    },
    hand(t0, t1) {
      hands.push([t0, t1]);
      return api;
    },
    show(t0, t1) {
      vis.push([t0, t1]);
      return api;
    },
    pos(t) {
      // resolve the list into segments
      let cur = null;
      let lastXY = null;
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        if (p.jump) {
          if (t >= p.t || !lastXY) lastXY = { x: p.x, y: p.y };
          continue;
        }
        if (p.hold) continue;
        const start = pts[i - 1]?.hold ? pts[i - 1].t : p.t;
        if (t < start) break;
        const from = lastXY;
        if (t >= p.t) {
          lastXY = { x: p.x, y: p.y };
          continue;
        }
        const u = clamp((t - start) / (p.t - start));
        const e = p.ease(u);
        const dx = p.x - from.x, dy = p.y - from.y;
        const d = Math.hypot(dx, dy) || 1;
        const bow = Math.sin(Math.PI * e) * p.arc * d;
        cur = { x: from.x + dx * e + (-dy / d) * bow, y: from.y + dy * e + (dx / d) * bow };
        return cur;
      }
      return lastXY ?? { x: 0, y: 0 };
    },
    /** map: world → screen (the cursor is drawn in screen space at a constant size). */
    update(t, map = null) {
      const w = api.pos(t);
      const p = map ? map(w.x, w.y) : w;
      let s = 1;
      for (const c of clicks) {
        const k = t - c;
        if (k > -0.05 && k < 0.2) s = Math.min(s, 1 - 0.14 * (k < 0 ? (k + 0.05) / 0.05 : 1 - k / 0.2));
      }
      const onHand = hands.some(([a, b]) => t >= a && t < b);
      const a = vis.length ? Math.max(...vis.map(([a0, a1]) => clamp((t - a0) / 0.25) * clamp((a1 - t) / 0.25))) : 1;
      el.style.transform = `translate(${p.x.toFixed(2)}px,${p.y.toFixed(2)}px) scale(${s.toFixed(3)})`;
      el.style.opacity = a.toFixed(3);
      arrow.style.display = onHand ? "none" : "block";
      hand.style.display = onHand ? "block" : "none";
    },
    /** Screen speed helper for motion blur (world px/s). */
    speed(t) {
      const a = api.pos(t - 1 / 120), b = api.pos(t + 1 / 120);
      return Math.hypot(b.x - a.x, b.y - a.y) * 60;
    },
    clicks,
  };
  return api;
}
