// Pure functions of time. Every value on screen is computed from t, so any frame renders on its own.

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const mix = (a, b, t) => a + (b - a) * t;
export const inv = (a, b, x) => (a === Infinity ? 0 : a === -Infinity ? 1 : clamp((x - a) / (b - a)));
export const smooth = (a, b, x) => {
  const t = inv(a, b, x);
  return t * t * (3 - 2 * t);
};

export const ease = {
  linear: (t) => t,
  inCubic: (t) => t * t * t,
  outCubic: (t) => 1 - (1 - t) ** 3,
  inOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2),
  outQuint: (t) => 1 - (1 - t) ** 5,
  inOutQuint: (t) => (t < 0.5 ? 16 * t ** 5 : 1 - (-2 * t + 2) ** 5 / 2),
  outExpo: (t) => (t >= 1 ? 1 : 1 - 2 ** (-10 * t)),
  inExpo: (t) => (t <= 0 ? 0 : 2 ** (10 * t - 10)),
  inOutExpo: (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? 2 ** (20 * t - 10) / 2 : (2 - 2 ** (-20 * t + 10)) / 2),
  inOutSine: (t) => -(Math.cos(Math.PI * t) - 1) / 2,
  outSine: (t) => Math.sin((t * Math.PI) / 2),
};

// Damped spring step response 0 → 1 for a step at t = 0 (closed form, no simulation).
export function spring(t, { w, z }) {
  if (t <= 0) return 0;
  if (z < 1) {
    const wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
  }
  if (z === 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const s = Math.sqrt(z * z - 1);
  const r1 = -w * (z - s);
  const r2 = -w * (z + s);
  return 1 + (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r1 - r2);
}

export const SP = {
  ui: { w: 24, z: 0.72 }, // buttons, toggles: a hair of overshoot
  def: { w: 14, z: 0.86 }, // cards, containers
  heavy: { w: 9.5, z: 1 }, // big type, logo: no overshoot
  playful: { w: 16, z: 0.55 }, // stickers, pop-outs: visible overshoot
  camera: { w: 4.2, z: 1 }, // slow camera moves
  soft: { w: 6.5, z: 1 },
};

// A value that changes target several times: one spring per change, each from its own start time.
export function track(t, keys, p = SP.def) {
  let v = keys[0][1];
  for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], p);
  return v;
}

// Eased tween between two times.
export const tw = (t, t0, t1, v0, v1, e = ease.inOutCubic) => mix(v0, v1, e(inv(t0, t1, t)));

// Keyframes: [[time, value, easeIntoThisKey?], ...]
export function kf(t, keys) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1, e = ease.inOutCubic] = keys[i];
    const [t0, v0] = keys[i - 1];
    if (t <= t1) return mix(v0, v1, e(inv(t0, t1, t)));
  }
  return keys[keys.length - 1][1];
}

// Visibility window with eased fades.
export const win = (t, a, b, fin = 0.4, fout = 0.4) => Math.min(smooth(a, a + fin, t), 1 - smooth(b - fout, b, t));

export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let x = a;
    x = Math.imul(x ^ (x >>> 15), x | 1);
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

// Apply transform/opacity/filter in one go.
export function set(el, { x = 0, y = 0, s = 1, sx, sy, r = 0, rx = 0, ry = 0, o = 1, blur = 0, bright, z = 0, origin } = {}) {
  if ([x, y, s, r, rx, ry, o, blur].some((v) => !Number.isFinite(v))) console.error("[stage] NaN in set()", el.className, el.id, JSON.stringify({ x, y, s, r, o, blur }));
  const scale = sx !== undefined || sy !== undefined ? `scale(${sx ?? s}, ${sy ?? s})` : `scale(${s})`;
  const rot = (rx ? ` rotateX(${rx}deg)` : "") + (ry ? ` rotateY(${ry}deg)` : "") + (r ? ` rotate(${r}deg)` : "");
  el.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, ${z}px)${rot} ${scale}`;
  el.style.opacity = o <= 0.001 ? "0" : o >= 0.999 ? "1" : o.toFixed(4);
  const f = [];
  if (blur > 0.05) f.push(`blur(${blur.toFixed(2)}px)`);
  if (bright !== undefined && Math.abs(bright - 1) > 0.005) f.push(`brightness(${bright.toFixed(3)})`);
  el.style.filter = f.length ? f.join(" ") : "none";
  if (origin) el.style.transformOrigin = origin;
  el.style.visibility = o <= 0.001 ? "hidden" : "visible";
}
