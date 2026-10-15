// Easing library. Every curve is a pure function [0,1] -> number.

export const linear = (t) => t;

export const inQuad = (t) => t * t;
export const outQuad = (t) => 1 - (1 - t) * (1 - t);
export const inOutQuad = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
export const inCubic = (t) => t * t * t;
export const outCubic = (t) => 1 - Math.pow(1 - t, 3);
export const inOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const inQuart = (t) => t * t * t * t;
export const outQuart = (t) => 1 - Math.pow(1 - t, 4);
export const inOutQuart = (t) => (t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2);
export const inQuint = (t) => t * t * t * t * t;
export const outQuint = (t) => 1 - Math.pow(1 - t, 5);
export const inOutQuint = (t) => (t < 0.5 ? 16 * t ** 5 : 1 - Math.pow(-2 * t + 2, 5) / 2);
export const inExpo = (t) => (t <= 0 ? 0 : Math.pow(2, 10 * t - 10));
export const outExpo = (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));
export const inOutExpo = (t) =>
  t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2;
export const inCirc = (t) => 1 - Math.sqrt(1 - t * t);
export const outCirc = (t) => Math.sqrt(1 - Math.pow(t - 1, 2));
export const inOutCirc = (t) =>
  t < 0.5 ? (1 - Math.sqrt(1 - Math.pow(2 * t, 2))) / 2 : (Math.sqrt(1 - Math.pow(-2 * t + 2, 2)) + 1) / 2;
export const inSine = (t) => 1 - Math.cos((t * Math.PI) / 2);
export const outSine = (t) => Math.sin((t * Math.PI) / 2);
export const inOutSine = (t) => -(Math.cos(Math.PI * t) - 1) / 2;

export const outBack = (s = 1.70158) => (t) => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2);
export const inBack = (s = 1.70158) => (t) => (s + 1) * t * t * t - s * t * t;

/** CSS-style cubic-bezier(x1,y1,x2,y2), solved with Newton + bisection. */
export function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1,
    bx = 3 * (x2 - x1) - cx,
    ax = 1 - cx - bx;
  const cy = 3 * y1,
    by = 3 * (y2 - y1) - cy,
    ay = 1 - cy - by;
  const sx = (u) => ((ax * u + bx) * u + cx) * u;
  const sy = (u) => ((ay * u + by) * u + cy) * u;
  const dx = (u) => (3 * ax * u + 2 * bx) * u + cx;
  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let u = x;
    for (let i = 0; i < 8; i++) {
      const e = sx(u) - x;
      if (Math.abs(e) < 1e-7) return sy(u);
      const d = dx(u);
      if (Math.abs(d) < 1e-6) break;
      u -= e / d;
    }
    let lo = 0,
      hi = 1;
    u = x;
    for (let i = 0; i < 40; i++) {
      const v = sx(u);
      if (Math.abs(v - x) < 1e-7) break;
      if (v < x) lo = u;
      else hi = u;
      u = (lo + hi) / 2;
    }
    return sy(u);
  };
}

// The site's own curves (globals.css), so the film moves like the product.
export const expoOut = bezier(0.16, 1, 0.3, 1);
export const quintOut = bezier(0.22, 1, 0.36, 1);
export const inOutSoft = bezier(0.65, 0, 0.35, 1);
export const snap = bezier(0.34, 1.56, 0.64, 1);
// Cinematic moves.
export const swiftOut = bezier(0.2, 0.9, 0.1, 1);
export const heavyInOut = bezier(0.76, 0, 0.24, 1);
export const anticipate = bezier(0.6, -0.28, 0.73, 0.04);

/**
 * Damped spring step response, t in seconds. Returns ~0 -> 1 with overshoot.
 * freq = natural frequency in Hz, damping = zeta (0..1 underdamped).
 */
export function spring(t, freq = 3, damping = 0.45) {
  if (t <= 0) return 0;
  const w = 2 * Math.PI * freq;
  const z = damping;
  if (z >= 1) {
    return 1 - Math.exp(-w * t) * (1 + w * t);
  }
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
}

/** Spring as a normalized easing over a duration (settles by the end). */
export function springEase(freq = 3, damping = 0.45, dur = 1) {
  return (u) => (u >= 1 ? 1 : spring(u * dur, freq, damping));
}
