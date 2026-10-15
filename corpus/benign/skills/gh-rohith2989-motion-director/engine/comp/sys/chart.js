// Data that performs: bars that grow with their values counting up, lines that draw themselves, donuts that
// fill. SVG/DOM, deterministic. Style through CSS variables; numbers use tabular figures.
import { h, clamp, css } from "../core/anim.js";
import { expoOut, inOutSoft } from "../core/ease.js";
import { countUp, fmt } from "./ui.js";

let uid = 0; // ids are counters, never random: two renders must produce identical documents

/** Vertical bars. set(t, t0, stagger) grows bar i from t0 + i*stagger; labels count up with their bar. */
export function barChart({ values, labels = [], width = 640, height = 300, max = null, format = fmt.int, highlight = -1, gap = 0.28 } = {}) {
  const M = max ?? Math.max(...values) * 1.08;
  const el = h("div", { class: "ch-bars", style: { width: `${width}px`, height: `${height}px` } });
  const bw = width / values.length;
  const bars = values.map((v, i) => {
    const bar = h("div", { class: `ch-bar${i === highlight ? " hi" : ""}`, style: { height: `${(v / M) * 100}%` } });
    const val = h("div", { class: "ch-val", text: format(0) });
    const lab = h("div", { class: "ch-lab", text: labels[i] ?? "" });
    const col = h("div", { class: "ch-col", style: { width: `${bw}px`, padding: `0 ${(bw * gap) / 2}px` } }, val, bar, lab);
    el.appendChild(col);
    return { bar, val, v };
  });
  return {
    el,
    set(t, t0, stagger = 0.08, dur = 0.9) {
      bars.forEach((b, i) => {
        const s = t0 + i * stagger;
        const u = expoOut(clamp((t - s) / dur));
        css(b.bar, { transform: `scaleY(${u.toFixed(4)})` });
        countUp(b.val, t, s, dur, 0, b.v, format);
        css(b.val, { opacity: clamp((t - s) / 0.25).toFixed(3) });
      });
    },
  };
}

/** A line that draws itself left→right, with a soft area and a dot riding its head. set(u 0..1). */
export function lineChart({ values, width = 640, height = 260, min = null, max = null, stroke = "var(--accent)", area = true } = {}) {
  const lo = min ?? Math.min(...values), hi = max ?? Math.max(...values);
  const pts = values.map((v, i) => [(i / (values.length - 1)) * width, height - ((v - lo) / (hi - lo || 1)) * height * 0.9 - height * 0.05]);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  const id = `lg${uid++}`;
  const path = h("path", { d, fill: "none", stroke, "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round", pathLength: 1, "stroke-dasharray": "1 1", "stroke-dashoffset": 1 });
  const fill = h("path", { d: `${d} L${width} ${height} L0 ${height} Z`, fill: `url(#${id})`, opacity: 0 });
  const dot = h("circle", { r: 7, fill: stroke, stroke: "#fff", "stroke-width": 3, opacity: 0 });
  const clip = h("rect", { x: 0, y: 0, width: 0, height });
  const el = h("svg", { width, height, viewBox: `0 0 ${width} ${height}`, style: { overflow: "visible", display: "block" } },
    h("defs", {}, h("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2: 1 }, h("stop", { offset: "0%", "stop-color": stroke, "stop-opacity": 0.28 }), h("stop", { offset: "100%", "stop-color": stroke, "stop-opacity": 0 })),
      h("clipPath", { id: `${id}c` }, clip)),
    area ? h("g", { "clip-path": `url(#${id}c)` }, fill) : null, path, dot);
  return {
    el,
    set(u) {
      u = clamp(u);
      path.setAttribute("stroke-dashoffset", (1 - u).toFixed(4));
      clip.setAttribute("width", (width * u).toFixed(1));
      fill.setAttribute("opacity", (0.9 * clamp(u * 3)).toFixed(3));
      const f = u * (pts.length - 1), i = Math.min(pts.length - 2, Math.floor(f)), k = f - i;
      const x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k;
      dot.setAttribute("cx", x.toFixed(1));
      dot.setAttribute("cy", y.toFixed(1));
      dot.setAttribute("opacity", (u > 0.01 ? 1 : 0).toString());
    },
  };
}

/** A donut that fills to `value` (0..1). set(u 0..1). */
export function donut({ value, size = 220, width = 22, color = "var(--accent)", track = "color-mix(in srgb, var(--ink) 10%, transparent)" } = {}) {
  const r = size / 2 - width / 2;
  const arc = h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: color, "stroke-width": width, "stroke-linecap": "round", pathLength: 1, "stroke-dasharray": "1 1", "stroke-dashoffset": 1, transform: `rotate(-90 ${size / 2} ${size / 2})` });
  const el = h("svg", { width: size, height: size, viewBox: `0 0 ${size} ${size}`, style: { display: "block" } },
    h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: track, "stroke-width": width }), arc);
  return { el, set(u) { arc.setAttribute("stroke-dashoffset", (1 - value * inOutSoft(clamp(u))).toFixed(4)); } };
}
