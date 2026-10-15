// Seeded randomness + smooth noise, so every render is identical.

export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function hash1(n) {
  let x = Math.imul((n | 0) ^ 0x9e3779b9, 0x85ebca6b);
  x ^= x >>> 13;
  x = Math.imul(x, 0xc2b2ae35);
  x ^= x >>> 16;
  return (x >>> 0) / 4294967296;
}

/** 1D value noise, smooth (quintic), range -1..1. */
export function noise1(x, seed = 0) {
  const i = Math.floor(x);
  const f = x - i;
  const u = f * f * f * (f * (f * 6 - 15) + 10);
  const a = hash1(i * 7919 + seed * 104729) * 2 - 1;
  const b = hash1((i + 1) * 7919 + seed * 104729) * 2 - 1;
  return a + (b - a) * u;
}

/** Fractal 1D noise, range roughly -1..1. */
export function fbm1(x, seed = 0, oct = 3) {
  let v = 0,
    amp = 0.5,
    freq = 1,
    norm = 0;
  for (let o = 0; o < oct; o++) {
    v += amp * noise1(x * freq, seed + o * 31);
    norm += amp;
    amp *= 0.5;
    freq *= 2.03;
  }
  return v / norm;
}

/** Smooth 2D drift: returns [dx, dy] in -1..1 for time t. */
export function drift2(t, seed = 0, speed = 0.25) {
  return [fbm1(t * speed, seed, 2), fbm1(t * speed + 100, seed + 17, 2)];
}
