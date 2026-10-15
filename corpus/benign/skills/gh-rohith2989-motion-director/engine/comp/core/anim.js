// Pure time -> value helpers. No clocks: everything is a function of t.
import { linear } from "./ease.js";

export const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
export const lerp = (a, b, u) => a + (b - a) * u;
export const invLerp = (a, b, x) => (b === a ? 0 : (x - a) / (b - a));
export const remap = (x, a, b, c, d, ease = linear) => lerp(c, d, ease(clamp(invLerp(a, b, x))));
export const smoothstep = (a, b, x) => {
  const u = clamp((x - a) / (b - a));
  return u * u * (3 - 2 * u);
};
export const mix = (a, b, u) =>
  Array.isArray(a) ? a.map((v, i) => lerp(v, b[i], u)) : lerp(a, b, u);

/** Progress 0..1 of t across [t0, t1], eased. */
export const prog = (t, t0, t1, ease = linear) => ease(clamp((t - t0) / (t1 - t0)));

/** Tween a value from->to across [t0,t1]. */
export const tween = (t, t0, t1, from, to, ease = linear) => mix(from, to, prog(t, t0, t1, ease));

/**
 * Keyframes: [[time, value, easeIntoThisKey?], ...] sorted by time.
 * The ease on key i shapes the segment (i-1 -> i).
 */
export function keys(t, ks) {
  if (t <= ks[0][0]) return ks[0][1];
  const last = ks[ks.length - 1];
  if (t >= last[0]) return last[1];
  for (let i = 1; i < ks.length; i++) {
    const [t1, v1, e] = ks[i];
    const [t0, v0] = ks[i - 1];
    if (t <= t1) {
      const u = (e || linear)(clamp((t - t0) / (t1 - t0)));
      return mix(v0, v1, u);
    }
  }
  return last[1];
}

/** A pulse that rises over `a`, holds, falls over `r`: 0 -> 1 -> 0. */
export function pulse(t, t0, a, hold, r, easeA = linear, easeR = linear) {
  if (t < t0) return 0;
  if (t < t0 + a) return easeA((t - t0) / a);
  if (t < t0 + a + hold) return 1;
  if (t < t0 + a + hold + r) return 1 - easeR((t - t0 - a - hold) / r);
  return 0;
}

export const px = (v) => `${v}px`;
export const deg = (v) => `${v}deg`;

/** Build a CSS transform string from a small object. */
export function tf({ x = 0, y = 0, z = 0, s = 1, sx = 1, sy = 1, r = 0, rx = 0, ry = 0, skx = 0 } = {}) {
  let out = `translate3d(${x}px,${y}px,${z}px)`;
  if (rx) out += ` rotateX(${rx}deg)`;
  if (ry) out += ` rotateY(${ry}deg)`;
  if (r) out += ` rotate(${r}deg)`;
  if (skx) out += ` skewX(${skx}deg)`;
  if (s !== 1 || sx !== 1 || sy !== 1) out += ` scale(${s * sx},${s * sy})`;
  return out;
}

/** Set styles only when they change (keeps the renderer honest and fast). */
export function css(el, props) {
  const cache = el.__css || (el.__css = {});
  for (const k in props) {
    const v = props[k];
    if (cache[k] !== v) {
      cache[k] = v;
      if (k.startsWith("--")) el.style.setProperty(k, v);
      else el.style[k] = v;
    }
  }
}

export function h(tag, attrs = {}, ...children) {
  const svgTags = new Set([
    "svg", "path", "g", "circle", "ellipse", "rect", "line", "defs", "clipPath", "linearGradient",
    "radialGradient", "stop", "mask", "filter", "feGaussianBlur", "feOffset", "feMerge", "feMergeNode",
    "feColorMatrix", "polyline", "polygon", "text", "tspan", "use", "feFlood", "feComposite", "feBlend",
  ]);
  const el = svgTags.has(tag)
    ? document.createElementNS("http://www.w3.org/2000/svg", tag)
    : document.createElement(tag);
  for (const k in attrs) {
    const v = attrs[k];
    if (v == null || v === false) continue;
    if (k === "class") el.setAttribute("class", v);
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k === "html") el.innerHTML = v;
    else if (k === "text") el.textContent = v;
    else el.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return el;
}
