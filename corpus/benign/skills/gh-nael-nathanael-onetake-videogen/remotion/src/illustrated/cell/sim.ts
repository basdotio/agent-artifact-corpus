// Deterministic 2D soft-body simulation, precomputed once per render worker.
// Position-based dynamics (Müller, "Ten Minute Physics"): membrane = ring of particles with
// edge, bending and area constraints and a weak pull toward a target outline; contents = damped
// particles that collide with the membrane and each other.
import { Easing, interpolate, spring } from "remotion";
import { lerpArr, sampleAt } from "../shared";

export const FPS = 60;
export const DURATION_S = 20;
const SUB = 4;
const N = 64;

export const R0 = 300;
export const R_DAUGHTER = 225;
const SEP_PINCH = 226;
const SEP_END = 270;
const MEMBRANE_INSET = 28; // outline to inner edge of the drawn membrane band
export const ARM = 40; // chromatid arm length

export const T = {
  appear: 0,
  burst: 4,
  centrosomes: 4.9,
  poles: 5.5,
  plate: 6,
  anaphase: 9.5,
  cleaveStart: 10.5,
  pinch: 13.2,
  telophase: 14,
  newNuclei: 14.3,
  title: 16.7,
};
// Frames of hit-pause (whole sim frozen) right before each of these events.
export const HIT = 4;
const HIT_AT = [T.burst, T.anaphase, T.pinch].map((e) => Math.round(e * FPS));
const inHitstop = (f: number) => HIT_AT.some((e) => f >= e - HIT && f < e);

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const arrive = Easing.bezier(0.2, 0, 0, 1);

// Unit step response of an underdamped spring (one visible overshoot).
const settle = (t: number) => {
  const z = 0.5, w = 12, wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
};
// Half-distance between the two lobes: furrow closes, creeps tight (tension), then snaps apart.
export const sep = (t: number) =>
  t >= T.pinch
    ? SEP_PINCH + (SEP_END - SEP_PINCH) * settle(t - T.pinch)
    : interpolate(t, [T.cleaveStart, 12.85, 13.1], [0, 224.5, SEP_PINCH], { ...clamp, easing: Easing.bezier(0.45, 0, 0.2, 1) });
const rho = (t: number) => R0 - (R0 - R_DAUGHTER) * Math.min(1, sep(t) / SEP_PINCH);
const grow = (t: number) => interpolate(t, [0, 0.18], [0.15, 1], { ...clamp, easing: Easing.out(Easing.quad) });

// Volume-preserving radial kicks: oval and three-lobe modes about each ring's centre, or about
// each lobe's centre while the cell is a peanut.
const KICKS: [number, number, number, number, boolean][] = [
  // time, oval amplitude (px/s), three-lobe amplitude, oval axis angle, per lobe
  [T.burst, 260, 110, 0.6, false],
  [T.anaphase, 170, 40, 0, false],
  [T.pinch - 0.3, 150, 0, Math.PI / 2, true], // anticipation: lobes squash sideways before the snap
  [T.pinch + 0.001, 150, 0, Math.PI / 2, false], // recoil, one substep after the split: the cut sides snap back
];
const popCache = new Map<string, number>();
export const popScale = (t: number, start: number, damping = 10) => {
  if (t < start) return 0;
  const frame = Math.round((t - start) * FPS);
  const key = `${frame}:${damping}`;
  let v = popCache.get(key);
  if (v === undefined) popCache.set(key, (v = spring({ frame, fps: FPS, config: { damping, stiffness: 160 } })));
  return v;
};

export type BodySpec = {
  id: string;
  part: string;
  r: number; // collision radius at scale 1
  side: -1 | 0 | 1; // which cell it rides with; 0 = centre until division
  appear: number;
  vanish?: number;
  anchor: (t: number, c: number, s: number) => [number, number]; // c = own cell centre x, s = cell scale
  bond?: string; // held together with this body until anaphase
  chromatid?: boolean;
};

const noise = (t: number, seed: number) => Math.sin(t * 0.7 + seed) * 0.6 + Math.sin(t * 1.3 + seed * 2.1) * 0.4;

const ORG: [string, string, -1 | 1, number, number, number][] = [
  // id, part, side, x, y, collision radius
  ["mitoA", "a03", -1, -115, -150, 50],
  ["mitoV2", "a04", -1, -140, 130, 48],
  ["vesA", "a09", -1, -45, 200, 32],
  ["mitoB", "a05", 1, 110, -150, 50],
  ["mitoC", "a06", 1, 125, 140, 50],
  ["vesB", "a10", 1, 30, -210, 32],
];

const CHR: [number, number, number][] = [
  // scatter x, scatter y, plate y
  [-60, -55, -168],
  [55, -70, -56],
  [-45, 60, 56],
  [70, 45, 168],
];

export const BODIES: BodySpec[] = [
  ...ORG.map(([id, part, side, x, y, r], i): BodySpec => ({
    id, part, r, side, appear: 0.3 + 0.07 * i,
    anchor: (t, c, s) => [c + x * s + 12 * noise(t, i), y * s + 12 * noise(t, i + 7)],
  })),
  { id: "nucleus", part: "a00", r: 80, side: 0, appear: 0.15, vanish: T.burst, anchor: () => [0, 0] },
  ...CHR.flatMap(([sx, sy, py], i) =>
    ([-1, 1] as const).map((side): BodySpec => ({
      id: `chr${i}${side}`, part: "chromatid", r: 20, side, appear: T.burst, vanish: T.newNuclei + 0.05, chromatid: true,
      bond: side < 0 ? `chr${i}1` : undefined,
      anchor: (t, c) => {
        if (t < T.plate + 0.12 * i) return [sx + 6 * noise(t, i), sy + 6 * noise(t, i + 3)];
        if (t < T.anaphase) return [0, py];
        // Pulled to the pole, then ride with the daughter centre where the new nucleus forms.
        const pull = interpolate(t, [T.anaphase, T.anaphase + 0.9], [0, 135], { ...clamp, easing: Easing.bezier(0.3, 0, 0.2, 1) });
        const k = interpolate(t, [T.anaphase, T.anaphase + 1.4, T.telophase, T.newNuclei], [1, 0.6, 0.6, 0.2], { ...clamp, easing: arrive });
        // Fan: outer chromatids lag toward the equator.
        const fan = 25 * (Math.abs(py) / 168) * interpolate(t, [T.anaphase, T.anaphase + 1, T.telophase, T.newNuclei], [0, 1, 1, 0], clamp);
        return [side * (Math.max(pull, Math.abs(c)) - fan), py * k];
      },
    })),
  ),
  ...([-1, 1] as const).map((side): BodySpec => ({
    id: `centro${side}`, part: "centrosome", r: 0, side, appear: T.centrosomes, vanish: T.telophase + 0.6,
    // Spiral out of the old nucleus to opposite poles along an arc.
    anchor: (t, c, s) => {
      const p = interpolate(t, [T.centrosomes, T.poles], [0, 1], { ...clamp, easing: arrive });
      const phi = (Math.PI / 2) * (1 - p);
      const rp = (50 + (0.62 * R0 - 50) * p) * s;
      return [c + side * rp * Math.cos(phi), -rp * Math.sin(phi)];
    },
  })),
  ...([-1, 1] as const).map((side): BodySpec => ({
    id: `nucleus${side}`, part: "a00", r: 64, side, appear: T.newNuclei, anchor: (t, c) => [c, 0],
  })),
];

type Ring = { x: Float64Array; y: Float64Array; vx: Float64Array; vy: Float64Array; ang: Float64Array; side: -1 | 0 | 1 };
export type BodyFrame = { x: number; y: number; vx: number; vy: number; scale: number; alive: boolean; tips: number[] | null };
export type Frame = {
  rings: { pts: number[]; side: number }[]; // flat x,y
  bodies: BodyFrame[];
};

const makeRing = (side: -1 | 0 | 1, pts: [number, number][], vel: [number, number][], cx: number): Ring => {
  const n = pts.length;
  const r: Ring = { x: new Float64Array(n), y: new Float64Array(n), vx: new Float64Array(n), vy: new Float64Array(n), ang: new Float64Array(n), side };
  pts.forEach(([x, y], i) => {
    r.x[i] = x; r.y[i] = y; r.vx[i] = vel[i][0]; r.vy[i] = vel[i][1];
    r.ang[i] = Math.atan2(y, x - cx);
  });
  return r;
};

// Target outline radius along angle a around the ring's centre.
const targetR = (ring: Ring, a: number, t: number) => {
  if (ring.side !== 0) return R_DAUGHTER * (1 + 0.012 * Math.sin(3 * a + 1.3 * t + ring.side) + 0.008 * Math.sin(5 * a - 1.5 * t));
  const d = sep(t);
  const p = rho(t);
  // Ripple fades during cleavage so the outline is mirror-symmetric and a point sits on each neck tip.
  const calm = 1 - interpolate(t, [T.cleaveStart, T.cleaveStart + 1], [0, 1], clamp);
  const ripple = 1 + calm * (0.012 * Math.sin(3 * a + 1.1 * t) + 0.008 * Math.sin(5 * a - 1.7 * t));
  // Smoothed |cos a| rounds the neck into an hourglass instead of a cusp.
  return (d * Math.sqrt(Math.cos(a) ** 2 + 0.012) + Math.sqrt(Math.max(0, p * p - d * d * Math.sin(a) ** 2))) * grow(t) * ripple;
};
const ringCentre = (ring: Ring, t: number) => ring.side * sep(t);

// Goal positions. The single cell spaces its goals at equal arc length so the closing neck never
// crowds points into a fold; daughters keep fixed angles.
const M = 256;
const goals = (ring: Ring, t: number, gx: Float64Array, gy: Float64Array) => {
  const n = ring.x.length, cx = ringCentre(ring, t);
  if (ring.side !== 0) {
    for (let i = 0; i < n; i++) {
      const tr = targetR(ring, ring.ang[i], t);
      gx[i] = cx + tr * Math.cos(ring.ang[i]); gy[i] = tr * Math.sin(ring.ang[i]);
    }
    return;
  }
  const sx = new Float64Array(M + 1), sy = new Float64Array(M + 1), cum = new Float64Array(M + 1);
  for (let k = 0; k <= M; k++) {
    const a = (k / M) * Math.PI * 2, tr = targetR(ring, a, t);
    sx[k] = tr * Math.cos(a); sy[k] = tr * Math.sin(a);
    if (k) cum[k] = cum[k - 1] + Math.hypot(sx[k] - sx[k - 1], sy[k] - sy[k - 1]);
  }
  let k = 0;
  for (let i = 0; i < n; i++) {
    const target = (i / n) * cum[M];
    while (k < M - 1 && cum[k + 1] < target) k++;
    const f = (target - cum[k]) / (cum[k + 1] - cum[k] || 1);
    gx[i] = sx[k] + (sx[k + 1] - sx[k]) * f; gy[i] = sy[k] + (sy[k + 1] - sy[k]) * f;
    ring.ang[i] = Math.atan2(gy[i], gx[i]);
  }
};

const polyArea = (xs: ArrayLike<number>, ys: ArrayLike<number>) => {
  let a = 0;
  for (let i = 0, n = xs.length; i < n; i++) {
    const j = (i + 1) % n;
    a += xs[i] * ys[j] - xs[j] * ys[i];
  }
  return a / 2;
};

// Cut the peanut at the neck into two closed rings, resampled to N points each.
const splitRing = (ring: Ring, t: number): Ring[] =>
  ([-1, 1] as const).map((side) => {
    // Use each point's goal angle, not its x: the neck can fold across x = 0.
    const idx: number[] = [];
    const n = ring.x.length;
    const onSide = (i: number) => Math.cos(ring.ang[i]) * side > 1e-6; // neck-tip points join neither
    const start = [...Array(n).keys()].find((i) => !onSide(i) && onSide((i + 1) % n))!;
    for (let k = 1; k <= n; k++) {
      const i = (start + k) % n;
      if (!onSide(i)) break;
      idx.push(i);
    }
    const P = idx.map((i) => [ring.x[i], ring.y[i], ring.vx[i], ring.vy[i]]);
    const len = P.map((p, k) => Math.hypot(P[(k + 1) % P.length][0] - p[0], P[(k + 1) % P.length][1] - p[1]));
    const total = len.reduce((a, b) => a + b, 0);
    const pts: [number, number][] = [];
    const vel: [number, number][] = [];
    let k = 0, acc = 0;
    for (let s = 0; s < N; s++) {
      const target = (s / N) * total;
      while (k < P.length - 1 && acc + len[k] < target) acc += len[k++];
      const f = len[k] > 1e-9 ? Math.min(1, (target - acc) / len[k]) : 0;
      const a = P[k], b = P[(k + 1) % P.length];
      pts.push([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]);
      vel.push([a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f]);
    }
    return makeRing(side, pts, vel, side * sep(t));
  });

// Rest direction of a chromatid arm (up = -1 upper arm, 1 lower arm). Before anaphase the arms point
// toward the own pole (the pair reads as an X), are tugged open just before release, then trail.
const armRest = (t: number, side: number, up: number): [number, number] => {
  let toward = 1, th = 35;
  if (t >= T.anaphase - 0.3 && t < T.anaphase) th = interpolate(t, [T.anaphase - 0.3, T.anaphase - 0.07], [35, 58], { ...clamp, easing: Easing.in(Easing.quad) }) + 3 * Math.sin(t * 70);
  if (t >= T.anaphase) { toward = -1; th = 62; }
  const r = (th * Math.PI) / 180;
  return [side * toward * Math.sin(r), up * Math.cos(r)];
};

const simulate = (): Frame[] => {
  const h = 1 / (FPS * SUB);
  const init = Array.from({ length: N }, (_, i): [number, number] => {
    const a = (i / N) * Math.PI * 2;
    return [Math.cos(a) * R0 * 0.15, Math.sin(a) * R0 * 0.15];
  });
  let rings: Ring[] = [makeRing(0, init, init.map(() => [0, 0]), 0)];
  const B = BODIES.map((spec) => ({
    x: 0, y: 0, vx: 0, vy: 0, scale: 0, alive: false, born: false,
    tips: spec.chromatid ? new Float64Array(8) : null, // upper x,y,vx,vy then lower
  }));
  const frames: Frame[] = [];
  const total = DURATION_S * FPS;
  let kicked = 0;

  for (let f = 0; f < total; f++) {
    if (inHitstop(f) && frames.length) { frames.push(frames[frames.length - 1]); continue; }
    for (let sub = 0; sub < SUB; sub++) {
      const t = (f * SUB + sub) * h;
      const s = rho(t) / R0;

      // Spawning.
      BODIES.forEach((spec, i) => {
        const b = B[i];
        b.scale = popScale(t, spec.appear);
        const alive = t >= spec.appear && (spec.vanish === undefined || t < spec.vanish);
        if (alive && !b.born) {
          b.born = true;
          const a = spec.anchor(t, spec.side * sep(t), s);
          if (spec.chromatid) {
            // Spill out of the bursting nucleus.
            b.x = a[0] * 0.2; b.y = a[1] * 0.2;
            const n = Math.hypot(a[0], a[1]) || 1;
            b.vx = (a[0] / n) * 320; b.vy = (a[1] / n) * 320;
          } else { b.x = a[0]; b.y = a[1]; }
          if (b.tips) for (const [o, up] of [[0, -1], [4, 1]]) {
            const d = armRest(t, spec.side, up);
            b.tips[o] = b.x + d[0] * 4; b.tips[o + 1] = b.y + d[1] * 4;
            b.tips[o + 2] = b.vx; b.tips[o + 3] = b.vy;
          }
        }
        b.alive = alive;
      });
      while (kicked < KICKS.length && t >= KICKS[kicked][0]) {
        const [, oval, lobe, ph, perLobe] = KICKS[kicked++];
        for (const r of rings) {
          for (let i = 0; i < r.x.length; i++) {
            const cx = perLobe ? Math.sign(r.x[i]) * sep(t) : ringCentre(r, t);
            const a = Math.atan2(r.y[i], r.x[i] - cx);
            // Per-lobe kicks fade out toward the neck so it keeps closing.
            const w = perLobe ? Math.min(1, Math.abs(r.x[i]) / sep(t)) ** 3 : 1;
            const v = w * (oval * Math.cos(2 * (a - ph)) + lobe * Math.cos(3 * a + 1));
            r.vx[i] += Math.cos(a) * v; r.vy[i] += Math.sin(a) * v;
          }
        }
      }

      // Membrane: goal spring + damping, predict.
      const pred = rings.map((r) => {
        const n = r.x.length;
        const px = new Float64Array(n), py = new Float64Array(n);
        const gx = new Float64Array(n), gy = new Float64Array(n);
        goals(r, t, gx, gy);
        for (let i = 0; i < n; i++) {
          r.vx[i] += h * (90 * (gx[i] - r.x[i]) - 2 * r.vx[i]);
          r.vy[i] += h * (90 * (gy[i] - r.y[i]) - 2 * r.vy[i]);
          px[i] = r.x[i] + h * r.vx[i]; py[i] = r.y[i] + h * r.vy[i];
        }
        const rest = new Float64Array(n);
        for (let i = 0; i < n; i++) rest[i] = Math.hypot(gx[(i + 1) % n] - gx[i], gy[(i + 1) % n] - gy[i]);
        return { px, py, gx, gy, rest, area: polyArea(gx, gy) };
      });

      // Bodies: anchor spring + damping, predict.
      const bp = B.map((b, i) => {
        if (!b.alive) return null;
        const spec = BODIES[i];
        const a = spec.anchor(t, spec.side * sep(t), s);
        b.vx += h * (60 * (a[0] - b.x) - 5.4 * b.vx);
        b.vy += h * (60 * (a[1] - b.y) - 5.4 * b.vy);
        return { x: b.x + h * b.vx, y: b.y + h * b.vy, r: spec.r * b.scale, side: spec.side };
      });

      for (let it = 0; it < 3; it++) {
        rings.forEach((r, ri) => {
          const { px, py, gx, gy, rest, area } = pred[ri];
          const n = px.length;
          // Edge lengths, each toward its own goal edge length.
          for (let i = 0; i < n; i++) {
            const j = (i + 1) % n;
            const dx = px[j] - px[i], dy = py[j] - py[i];
            const len = Math.hypot(dx, dy) || 1e-6;
            const k = ((len - rest[i]) / len) * 0.25;
            px[i] += dx * k; py[i] += dy * k; px[j] -= dx * k; py[j] -= dy * k;
          }
          // Bending: damp curvature that the goal outline does not have (kinks), keep low wobble modes.
          for (let i = 0; i < n; i++) {
            const pv = (i - 1 + n) % n, nx = (i + 1) % n;
            const lx = px[i] - 0.5 * (px[pv] + px[nx]) - (gx[i] - 0.5 * (gx[pv] + gx[nx]));
            const ly = py[i] - 0.5 * (py[pv] + py[nx]) - (gy[i] - 0.5 * (gy[pv] + gy[nx]));
            const kb = 0.12;
            px[i] -= lx * kb * (2 / 3); py[i] -= ly * kb * (2 / 3);
            px[pv] += lx * kb / 3; py[pv] += ly * kb / 3;
            px[nx] += lx * kb / 3; py[nx] += ly * kb / 3;
          }
          // Area (internal pressure).
          const A = polyArea(px, py);
          let g2 = 0;
          const gxs = new Float64Array(n), gys = new Float64Array(n);
          for (let i = 0; i < n; i++) {
            const nx = (i + 1) % n, pv = (i - 1 + n) % n;
            gxs[i] = 0.5 * (py[nx] - py[pv]); gys[i] = 0.5 * (px[pv] - px[nx]);
            g2 += gxs[i] ** 2 + gys[i] ** 2;
          }
          const lambda = (-(A - area) / (g2 || 1)) * 0.06;
          for (let i = 0; i < n; i++) { px[i] += lambda * gxs[i]; py[i] += lambda * gys[i]; }
          // Contractile ring: a stiff local pull at the furrow that pressure cannot reopen.
          if (r.side === 0 && t > T.cleaveStart) {
            const ring = 0.3 * Math.min(1, (t - T.cleaveStart) / 0.5);
            for (let i = 0; i < n; i++) {
              const w = ring * Math.exp(-((gx[i] / 45) ** 2));
              px[i] += (gx[i] - px[i]) * w; py[i] += (gy[i] - py[i]) * w;
            }
          }
          // Contents push the membrane outward; the membrane is lighter, so it bulges.
          bp.forEach((b) => {
            if (!b || b.r <= 0 || (r.side !== 0 && b.side !== r.side && b.side !== 0)) return;
            const min = b.r + MEMBRANE_INSET;
            for (let i = 0; i < n; i++) {
              const dx = px[i] - b.x, dy = py[i] - b.y;
              const dd = dx * dx + dy * dy;
              if (dd >= min * min) continue;
              const d = Math.sqrt(dd) || 1e-6, push = (min - d) / d;
              px[i] += dx * push * 0.8; py[i] += dy * push * 0.8;
              b.x -= dx * push * 0.2; b.y -= dy * push * 0.2;
            }
          });
          // Daughters collide with each other across the midline (the pair is mirror-symmetric).
          if (r.side !== 0) for (let i = 0; i < n; i++) if (r.side * px[i] < 6) px[i] = r.side * 6;
        });
        // Body-body collisions and chromatid bonds.
        for (let i = 0; i < bp.length; i++) {
          const a = bp[i];
          if (!a) continue;
          const bondId = BODIES[i].bond;
          for (let j = i + 1; j < bp.length; j++) {
            const b = bp[j];
            if (!b) continue;
            const dx = b.x - a.x, dy = b.y - a.y;
            const d = Math.hypot(dx, dy) || 1e-6;
            if (bondId === BODIES[j].id) {
              if (t < T.anaphase) { const k = 0.5; a.x += dx * k; a.y += dy * k; b.x -= dx * k; b.y -= dy * k; }
              continue;
            }
            const min = a.r + b.r;
            if (a.r <= 0 || b.r <= 0 || d >= min) continue;
            const k = ((min - d) / d) * 0.5;
            a.x -= dx * k; a.y -= dy * k; b.x += dx * k; b.y += dy * k;
          }
        }
      }

      // Velocities from corrected positions.
      rings.forEach((r, ri) => {
        const { px, py } = pred[ri];
        for (let i = 0; i < px.length; i++) {
          r.vx[i] = (px[i] - r.x[i]) / h; r.vy[i] = (py[i] - r.y[i]) / h;
          r.x[i] = px[i]; r.y[i] = py[i];
        }
      });
      bp.forEach((p, i) => {
        if (!p) return;
        const b = B[i];
        b.vx = (p.x - b.x) / h; b.vy = (p.y - b.y) / h; b.x = p.x; b.y = p.y;
        // Chromatid arms: dragged tips on a fixed-length tether to the centromere.
        if (!b.tips) return;
        const L = ARM * b.scale, k = t < T.anaphase ? 90 : 50;
        const tp = b.tips, old = Array.from(tp);
        const q: number[] = [];
        for (const [o, up] of [[0, -1], [4, 1]]) {
          const d = armRest(t, BODIES[i].side, up);
          tp[o + 2] += h * (k * (b.x + d[0] * L - tp[o]) - 4 * tp[o + 2]);
          tp[o + 3] += h * (k * (b.y + d[1] * L - tp[o + 1]) - 4 * tp[o + 3]);
          q.push(tp[o] + h * tp[o + 2], tp[o + 1] + h * tp[o + 3]);
        }
        // The arms are bulky: their tips keep apart, so a dragged chromatid stays a V, never a rod.
        const sx = q[2] - q[0], sy = q[3] - q[1], sd = Math.hypot(sx, sy);
        const minGap = 0.85 * L;
        if (sd < minGap) {
          const ux = sd > 1e-6 ? sx / sd : 0, uy = sd > 1e-6 ? sy / sd : 1, push = (minGap - sd) / 2;
          q[0] -= ux * push; q[1] -= uy * push; q[2] += ux * push; q[3] += uy * push;
        }
        for (const [o, j] of [[0, 0], [4, 2]]) {
          const dx = q[j] - b.x, dy = q[j + 1] - b.y, dl = Math.hypot(dx, dy) || 1e-6;
          tp[o] = b.x + (dx / dl) * L; tp[o + 1] = b.y + (dy / dl) * L;
          tp[o + 2] = (tp[o] - old[o]) / h; tp[o + 3] = (tp[o + 1] - old[o + 1]) / h;
        }
      });

      // Pinch-off on the beat, right after the hit-pause.
      if (rings.length === 1 && t >= T.pinch) rings = splitRing(rings[0], t);
    }

    frames.push({
      rings: rings.map((r) => ({ pts: Array.from(r.x).flatMap((x, i) => [x, r.y[i]]), side: r.side })),
      bodies: B.map((b) => ({ x: b.x, y: b.y, vx: b.vx, vy: b.vy, scale: b.scale, alive: b.alive, tips: b.tips ? Array.from(b.tips) : null })),
    });
  }
  return frames;
};

let cache: Frame[] | null = null;
export const getFrames = () => (cache ??= simulate());

// State at a fractional frame: linear blend of the neighbouring sim frames.
// Where topology differs (pinch-off ring count, a body spawning or vanishing) the nearer frame wins.
export const frameAt = (f: number): Frame => sampleAt(getFrames(), f, (a, b, u) => {
  const near = u < 0.5 ? a : b;
  return {
    rings: a.rings.length === b.rings.length
      ? a.rings.map((r, k) => ({ side: r.side, pts: lerpArr(r.pts, b.rings[k].pts, u) }))
      : near.rings,
    bodies: a.bodies.map((p, k) => {
      const q = b.bodies[k];
      if (p.alive !== q.alive) return near.bodies[k];
      return {
        x: p.x + (q.x - p.x) * u, y: p.y + (q.y - p.y) * u, vx: p.vx + (q.vx - p.vx) * u, vy: p.vy + (q.vy - p.vy) * u,
        scale: p.scale + (q.scale - p.scale) * u, alive: p.alive,
        tips: p.tips && q.tips ? lerpArr(p.tips, q.tips, u) : p.tips,
      };
    }),
  };
});
