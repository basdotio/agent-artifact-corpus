// UI micro-interactions: ramps, entrances, press dips, hovers, spinners, drawn checks, count-ups, callouts.
import { h, clamp, css } from "../core/anim.js";
import { expoOut, quintOut, outCubic } from "../core/ease.js";

export function rgb(hex) {
  const x = hex.replace("#", "");
  const n = x.length === 3 ? x.split("").map((c) => c + c).join("") : x;
  return [parseInt(n.slice(0, 2), 16), parseInt(n.slice(2, 4), 16), parseInt(n.slice(4, 6), 16)];
}
export function mixHex(a, b, u) {
  const A = rgb(a), B = rgb(b);
  return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * clamp(u))).join(",")})`;
}

/** 0 → 1 over [t0, t0 + d] with an ease. */
export const ramp = (t, t0, d, ease = quintOut) => ease(clamp((t - t0) / d));
/** Rise-in for UI blocks: {a, y, u}. */
export function enter(t, t0, { d = 0.5, dy = 10, ease = expoOut } = {}) {
  const u = ease(clamp((t - t0) / d));
  return { a: clamp((t - t0) / (d * 0.6)), y: (1 - u) * dy, u };
}
/** Press dip for a click at tp: 1 → 1-depth → 1. */
export function pressScale(t, tp, depth = 0.03) {
  const k = t - tp;
  if (k < -0.02 || k > 0.22) return 1;
  if (k < 0.06) return 1 - depth * clamp((k + 0.02) / 0.08);
  return 1 - depth * (1 - outCubic(clamp((k - 0.06) / 0.16)));
}
/** Hover amount for [tIn, tOut). */
export const hoverAt = (t, tIn, tOut = 1e9) => clamp((t - tIn) / 0.12) * (1 - clamp((t - tOut) / 0.16));

/** A hairline spinner (SVG arc). */
export function spinner(size = 16, color = "currentColor", sw = 2) {
  const r = size / 2 - sw;
  const c = 2 * Math.PI * r;
  const arc = h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: color, "stroke-width": sw, "stroke-linecap": "round", "stroke-dasharray": `${c * 0.28} ${c}` });
  const track = h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: color, "stroke-width": sw, opacity: 0.18 });
  const el = h("svg", { width: size, height: size, viewBox: `0 0 ${size} ${size}`, style: { display: "block", flex: "none" } }, track, arc);
  return { el, update(t) { arc.setAttribute("transform", `rotate(${((t * 400) % 360).toFixed(1)} ${size / 2} ${size / 2})`); } };
}

/** A check that draws itself (u 0..1). */
export function drawnCheck(size = 16, color = "currentColor", sw = 2) {
  const p = h("path", { d: "M4 10.5l3.6 3.6L16 5.8", fill: "none", stroke: color, "stroke-width": sw, "stroke-linecap": "round", "stroke-linejoin": "round", pathLength: 1, "stroke-dasharray": "1 1", "stroke-dashoffset": 1 });
  const el = h("svg", { width: size, height: size, viewBox: "0 0 20 20", style: { display: "block", flex: "none" } }, p);
  return { el, set(u) { p.setAttribute("stroke-dashoffset", (1 - clamp(u)).toFixed(4)); } };
}

/** Number formats for count-ups (tabular figures in CSS: font-variant-numeric: tabular-nums). */
export const fmt = {
  int: (v) => Math.round(v).toLocaleString("en-US"),
  pct: (v) => `${Math.round(v)}%`,
  pct1: (v) => `${v.toFixed(1)}%`,
  usd: (v) => `$${Math.round(v).toLocaleString("en-US")}`,
  k1: (v) => `${v.toFixed(1)}k`,
  x: (v) => `${v.toFixed(1)}×`,
};
/** A count-up: writes the formatted value into el. Lands exactly on `to` (no float dust on the final frame). */
export function countUp(el, t, t0, d, from, to, format = fmt.int, ease = expoOut) {
  const u = ease(clamp((t - t0) / d));
  const v = u >= 1 ? to : from + (to - from) * u;
  const s = format(v);
  if (el.__cu !== s) {
    el.textContent = s;
    el.__cu = s;
  }
  return u;
}

/**
 * A callout in screen space: a dot on the target, a hairline that draws to the label, a pill.
 * set(tx, ty, lx, ly, u, out) — target, label anchor, appearance 0..1, disappearance 0..1.
 */
export function createCallout(parent, text, { side = "right", tone = "light" } = {}) {
  const svg = h("svg", { class: "co-line", width: 1, height: 1, style: { overflow: "visible" } });
  const line = h("path", { fill: "none", stroke: tone === "dark" ? "rgba(255,255,255,.7)" : "color-mix(in srgb, var(--ink) 50%, transparent)", "stroke-width": 1.6, "stroke-linecap": "round", pathLength: 1, "stroke-dasharray": "1 1" });
  const ring = h("circle", { r: 9, fill: "none", stroke: "color-mix(in srgb, var(--accent) 45%, transparent)", "stroke-width": 1.5 });
  const dot = h("circle", { r: 4.5, fill: tone === "dark" ? "#fff" : "var(--accent)" });
  svg.append(line, ring, dot);
  const pill = h("div", { class: "co-pill", text });
  const el = h("div", { class: "co" }, svg, pill);
  parent.appendChild(el);
  return {
    el,
    pill,
    set(tx, ty, lx, ly, u, out = 0) {
      const a = clamp(u / 0.3) * (1 - clamp(out));
      dot.setAttribute("cx", tx.toFixed(1));
      dot.setAttribute("cy", ty.toFixed(1));
      ring.setAttribute("cx", tx.toFixed(1));
      ring.setAttribute("cy", ty.toFixed(1));
      ring.setAttribute("r", (5 + 7 * expoOut(clamp(u / 0.5))).toFixed(2));
      dot.setAttribute("opacity", a.toFixed(3));
      ring.setAttribute("opacity", (a * (1 - 0.4 * clamp((u - 0.5) / 0.5))).toFixed(3));
      line.setAttribute("d", `M${tx.toFixed(1)} ${ty.toFixed(1)} L${lx.toFixed(1)} ${ly.toFixed(1)}`);
      line.setAttribute("stroke-dashoffset", (1 - expoOut(clamp((u - 0.1) / 0.45))).toFixed(4));
      line.setAttribute("opacity", (1 - clamp(out)).toFixed(3));
      const pu = expoOut(clamp((u - 0.35) / 0.5));
      const w = pill.offsetWidth, hh = pill.offsetHeight;
      const px = side === "right" ? lx : lx - w;
      css(pill, { transform: `translate(${px.toFixed(1)}px,${(ly - hh / 2 + (1 - pu) * 10).toFixed(1)}px)`, opacity: (clamp((u - 0.35) / 0.3) * (1 - clamp(out))).toFixed(3) });
    },
  };
}
