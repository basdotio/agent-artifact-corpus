// Jelly need blob: a deterministic 2D soft body, precomputed once per render worker.
// Position-based dynamics as in ../cell/sim.ts: a ring of particles with edge, bending and area
// constraints and a weak pull toward an art-directed outline, plus a floor and a split into two.
import { Easing, interpolate } from "remotion";
import { lerpArr, sampleAt } from "../shared";

const N = 40;
const SUB = 8;
/** Frames the whole body freezes right before a hit or a split. */
export const HIT = 4;
const ANT = 9; // frames of squeeze the opposite way before the pinch starts
const K_GOAL = 170; // pull toward the outline; with C_GOAL it sets how far the jelly lags and how long it rings
const C_GOAL = 7;
const ABSORB = 9; // extra damping per second while the jelly touches the floor: it lands, it does not bounce away

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Unit step response of an underdamped spring: one visible overshoot of about 13%. */
export const settle = (t: number) => {
  if (t <= 0) return 0;
  const z = 0.55, w = 12, wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
};

export type Pt = { x: number; y: number };
export type BlobScript = {
  /** First and last simulated frame. Outside this span the nearest frame is held. */
  from: number;
  to: number;
  /** Art-directed centre and radius at a (fractional) frame. The jelly lags, overshoots and settles around it. */
  path: (fr: number) => Pt & { r: number };
  /** World y the jelly cannot pass: it flattens on it when it lands. */
  floor?: number;
  /** Frames of impact: the body freezes for HIT frames before each. Hold the path still over those frames. */
  hits?: number[];
  /** Volume-keeping wobble impulses (px/s): oval and three-lobe modes, oval axis angle in radians. */
  kicks?: { at: number; oval?: number; lobe?: number; angle?: number }[];
  split?: {
    /** Frame the blob becomes two. Squeeze, pinch and a HIT-frame hold are laid out before it. */
    at: number;
    /** Frames the pinch takes to close. */
    wind?: number;
    /** Split axis in radians: 0 parts the halves left and right. */
    axis?: number;
    /** Resting half-distance between the halves, in parent radii. */
    gap?: number;
    /** Where each half goes after the split, given its resting place beside the other. Default: stay there. */
    to?: [(fr: number, rest: Pt) => Pt, (fr: number, rest: Pt) => Pt];
  };
};
export type BlobRing = { pts: number[]; x: number; y: number; r: number; side: number };
export type BlobFrame = { rings: BlobRing[] };

type Ring = { x: Float64Array; y: Float64Array; vx: Float64Array; vy: Float64Array; ang: Float64Array; side: -1 | 0 | 1 };

const polyArea = (xs: ArrayLike<number>, ys: ArrayLike<number>) => {
  let a = 0;
  for (let i = 0, n = xs.length; i < n; i++) {
    const j = (i + 1) % n;
    a += xs[i] * ys[j] - xs[j] * ys[i];
  }
  return a / 2;
};

const simulate = (s: BlobScript, fps: number): BlobFrame[] => {
  const h = 1 / (fps * SUB);
  const sp = s.split;
  const E = sp?.at ?? Infinity, wind = sp?.wind ?? 28, axis = sp?.axis ?? 0, gap = sp?.gap ?? 1.25;
  const ux = Math.cos(axis), uy = Math.sin(axis);
  const hits = [...(s.hits ?? []), ...(sp ? [E] : [])];
  const inHit = (fr: number) => hits.some((e) => fr >= e - HIT && fr < e);

  // Half-distance between the lobes in parent radii: closes to the pinch, holds, then springs apart. The
  // release is damped harder than `settle`, because the jelly's own spring adds to its overshoot.
  const PINCH = 0.712;
  const release = (t: number) => {
    const z = 0.76, w = 11, wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
  };
  const sep = (fr: number) =>
    !sp ? 0 : fr >= E
      ? PINCH + (gap - PINCH) * release((fr - E) / fps)
      : interpolate(fr, [E - HIT - wind, E - HIT - 2, E - HIT], [0, PINCH * 0.985, PINCH], { ...clamp, easing: Easing.bezier(0.45, 0, 0.2, 1) });
  // Wind-up: squeezed along the split axis first, the opposite of pulling apart.
  const squeeze = (fr: number) =>
    !sp ? 0 : interpolate(fr, [E - HIT - wind - ANT, E - HIT - wind, E - HIT - wind * 0.5], [0, 1, 0], { ...clamp, easing: Easing.inOut(Easing.quad) });

  const centre = (ring: Ring, fr: number): Pt & { r: number } => {
    const p = s.path(fr);
    if (ring.side === 0) return p;
    const d = sep(fr) * p.r * ring.side;
    const rest = { x: p.x + ux * d, y: p.y + uy * d };
    const q = sp?.to ? sp.to[ring.side < 0 ? 0 : 1](fr, rest) : rest;
    return { x: q.x, y: q.y, r: p.r / Math.SQRT2 };
  };

  // Outline radius along angle a from the ring's centre. The single blob is a peanut while it pinches;
  // the smoothed |cos| keeps the neck an hourglass instead of a cusp.
  const targetR = (ring: Ring, a: number, fr: number, r: number) => {
    const t = fr / fps;
    if (ring.side !== 0) return r * (1 + 0.012 * Math.sin(3 * a + 1.3 * t + ring.side));
    const d = sep(fr) * r;
    const rho = r - (r - r / Math.SQRT2) * Math.min(1, sep(fr) / PINCH);
    const b = a - axis;
    const calm = 1 - Math.min(1, sep(fr) * 4);
    const ripple = 1 + calm * 0.012 * Math.sin(3 * a + 1.1 * t) - 0.1 * squeeze(fr) * Math.cos(2 * b);
    return (d * Math.sqrt(Math.cos(b) ** 2 + 0.012) + Math.sqrt(Math.max(0, rho * rho - d * d * Math.sin(b) ** 2))) * ripple;
  };

  // Goal positions. The single blob spaces its goals at equal arc length so a closing neck never
  // crowds points into a fold; halves keep fixed angles.
  const M = 160;
  const goals = (ring: Ring, fr: number, gx: Float64Array, gy: Float64Array) => {
    const n = ring.x.length, c = centre(ring, fr);
    if (ring.side !== 0) {
      for (let i = 0; i < n; i++) {
        const tr = targetR(ring, ring.ang[i], fr, c.r);
        gx[i] = c.x + tr * Math.cos(ring.ang[i]); gy[i] = c.y + tr * Math.sin(ring.ang[i]);
      }
      return;
    }
    const sx = new Float64Array(M + 1), sy = new Float64Array(M + 1), cum = new Float64Array(M + 1);
    for (let k = 0; k <= M; k++) {
      const a = (k / M) * Math.PI * 2, tr = targetR(ring, a, fr, c.r);
      sx[k] = tr * Math.cos(a); sy[k] = tr * Math.sin(a);
      if (k) cum[k] = cum[k - 1] + Math.hypot(sx[k] - sx[k - 1], sy[k] - sy[k - 1]);
    }
    let k = 0;
    for (let i = 0; i < n; i++) {
      const target = (i / n) * cum[M];
      while (k < M - 1 && cum[k + 1] < target) k++;
      const u = (target - cum[k]) / (cum[k + 1] - cum[k] || 1);
      const lx = sx[k] + (sx[k + 1] - sx[k]) * u, ly = sy[k] + (sy[k + 1] - sy[k]) * u;
      gx[i] = c.x + lx; gy[i] = c.y + ly;
      ring.ang[i] = Math.atan2(ly, lx);
    }
  };

  const makeRing = (side: -1 | 0 | 1, pts: [number, number][], vel: [number, number][], c: Pt): Ring => {
    const n = pts.length;
    const r: Ring = { x: new Float64Array(n), y: new Float64Array(n), vx: new Float64Array(n), vy: new Float64Array(n), ang: new Float64Array(n), side };
    pts.forEach(([x, y], i) => {
      r.x[i] = x; r.y[i] = y; r.vx[i] = vel[i][0]; r.vy[i] = vel[i][1];
      r.ang[i] = Math.atan2(y - c.y, x - c.x);
    });
    return r;
  };

  // Cut the peanut at the neck into two closed rings, resampled to N points each. Sides come from each
  // point's goal angle, never its position: a pinched neck folds across the midline.
  const splitRing = (ring: Ring, fr: number): Ring[] =>
    ([-1, 1] as const).map((side) => {
      const n = ring.x.length;
      const onSide = (i: number) => Math.cos(ring.ang[i] - axis) * side > 1e-6;
      const start = [...Array(n).keys()].find((i) => !onSide(i) && onSide((i + 1) % n)) ?? 0;
      const idx: number[] = [];
      for (let k = 1; k <= n; k++) {
        const i = (start + k) % n;
        if (!onSide(i)) break;
        idx.push(i);
      }
      const P = idx.map((i) => [ring.x[i], ring.y[i], ring.vx[i], ring.vy[i]]);
      const len = P.map((p, k) => Math.hypot(P[(k + 1) % P.length][0] - p[0], P[(k + 1) % P.length][1] - p[1]));
      const total = len.reduce((a, b) => a + b, 0);
      const pts: [number, number][] = [], vel: [number, number][] = [];
      let k = 0, acc = 0;
      for (let q = 0; q < N; q++) {
        const target = (q / N) * total;
        while (k < P.length - 1 && acc + len[k] < target) acc += len[k++];
        const u = len[k] > 1e-9 ? Math.min(1, (target - acc) / len[k]) : 0;
        const a = P[k], b = P[(k + 1) % P.length];
        pts.push([a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]);
        vel.push([a[2] + (b[2] - a[2]) * u, a[3] + (b[3] - a[3]) * u]);
      }
      const half = makeRing(side, pts, vel, { x: 0, y: 0 });
      const c = centre(half, fr);
      for (let i = 0; i < N; i++) half.ang[i] = Math.atan2(half.y[i] - c.y, half.x[i] - c.x);
      return half;
    });

  const c0 = s.path(s.from);
  const init = Array.from({ length: N }, (_, i): [number, number] => {
    const a = (i / N) * Math.PI * 2;
    return [c0.x + Math.cos(a) * c0.r, c0.y + Math.sin(a) * c0.r];
  });
  let rings: Ring[] = [makeRing(0, init, init.map(() => [0, 0]), c0)];
  const kicks = [...(s.kicks ?? [])].sort((a, b) => a.at - b.at);
  let kicked = 0;
  const frames: BlobFrame[] = [];

  for (let fi = s.from; fi <= s.to; fi++) {
    if (inHit(fi) && frames.length) { frames.push(frames[frames.length - 1]); continue; }
    for (let sub = 0; sub < SUB; sub++) {
      const fr = fi + sub / SUB;
      while (kicked < kicks.length && fr >= kicks[kicked].at) {
        const { oval = 0, lobe = 0, angle = 0 } = kicks[kicked++];
        for (const r of rings) {
          const c = centre(r, fr);
          for (let i = 0; i < r.x.length; i++) {
            const a = Math.atan2(r.y[i] - c.y, r.x[i] - c.x);
            const v = oval * Math.cos(2 * (a - angle)) + lobe * Math.cos(3 * a + 1);
            r.vx[i] += Math.cos(a) * v; r.vy[i] += Math.sin(a) * v;
          }
        }
      }

      // Goal spring and damping, predict.
      const pred = rings.map((r) => {
        const n = r.x.length;
        const px = new Float64Array(n), py = new Float64Array(n), gx = new Float64Array(n), gy = new Float64Array(n);
        goals(r, fr, gx, gy);
        for (let i = 0; i < n; i++) {
          r.vx[i] += h * (K_GOAL * (gx[i] - r.x[i]) - C_GOAL * r.vx[i]);
          r.vy[i] += h * (K_GOAL * (gy[i] - r.y[i]) - C_GOAL * r.vy[i]);
          px[i] = r.x[i] + h * r.vx[i]; py[i] = r.y[i] + h * r.vy[i];
        }
        const rest = new Float64Array(n);
        for (let i = 0; i < n; i++) rest[i] = Math.hypot(gx[(i + 1) % n] - gx[i], gy[(i + 1) % n] - gy[i]);
        return { px, py, gx, gy, rest, area: polyArea(gx, gy), landed: false };
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
          // Bending: damp kinks the goal outline does not have, keep the low wobble modes.
          for (let i = 0; i < n; i++) {
            const pv = (i - 1 + n) % n, nx = (i + 1) % n;
            const lx = px[i] - 0.5 * (px[pv] + px[nx]) - (gx[i] - 0.5 * (gx[pv] + gx[nx]));
            const ly = py[i] - 0.5 * (py[pv] + py[nx]) - (gy[i] - 0.5 * (gy[pv] + gy[nx]));
            const kb = 0.12;
            px[i] -= lx * kb * (2 / 3); py[i] -= ly * kb * (2 / 3);
            px[pv] += (lx * kb) / 3; py[pv] += (ly * kb) / 3;
            px[nx] += (lx * kb) / 3; py[nx] += (ly * kb) / 3;
          }
          // Area: internal pressure, so a flattened blob bulges sideways.
          const A = polyArea(px, py);
          let g2 = 0;
          const gxs = new Float64Array(n), gys = new Float64Array(n);
          for (let i = 0; i < n; i++) {
            const nx = (i + 1) % n, pv = (i - 1 + n) % n;
            gxs[i] = 0.5 * (py[nx] - py[pv]); gys[i] = 0.5 * (px[pv] - px[nx]);
            g2 += gxs[i] ** 2 + gys[i] ** 2;
          }
          const lambda = (-(A - area) / (g2 || 1)) * 0.1;
          for (let i = 0; i < n; i++) { px[i] += lambda * gxs[i]; py[i] += lambda * gys[i]; }
          // Contractile ring: a stiff local pull at the furrow that pressure cannot reopen.
          if (r.side === 0 && sep(fr) > 0) {
            const c = centre(r, fr);
            const ringK = 0.5 * Math.min(1, sep(fr) * 3);
            for (let i = 0; i < n; i++) {
              const along = (gx[i] - c.x) * ux + (gy[i] - c.y) * uy;
              const w = ringK * Math.exp(-((along / (0.15 * c.r)) ** 2));
              px[i] += (gx[i] - px[i]) * w; py[i] += (gy[i] - py[i]) * w;
            }
          }
          // Halves collide across the midline while they are still neighbours.
          if (r.side !== 0 && rings.length === 2) {
            const a = centre(rings[0], fr), b = centre(rings[1], fr);
            if (Math.hypot(b.x - a.x, b.y - a.y) < 3 * a.r) {
              const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
              for (let i = 0; i < n; i++) {
                const d = ((px[i] - mx) * ux + (py[i] - my) * uy) * r.side;
                if (d < 2) { px[i] += ux * (2 - d) * r.side; py[i] += uy * (2 - d) * r.side; }
              }
            }
          }
          if (s.floor !== undefined) {
            for (let i = 0; i < n; i++) {
              if (py[i] <= s.floor) continue;
              py[i] = s.floor;
              px[i] += (r.x[i] - px[i]) * 0.6;
              pred[ri].landed = true;
            }
          }
        });
      }

      rings.forEach((r, ri) => {
        const { px, py, landed } = pred[ri];
        const keep = landed ? 1 - h * ABSORB : 1;
        for (let i = 0; i < px.length; i++) {
          r.vx[i] = ((px[i] - r.x[i]) / h) * keep; r.vy[i] = ((py[i] - r.y[i]) / h) * keep;
          r.x[i] = px[i]; r.y[i] = py[i];
        }
      });

      // The split lands on its frame, right after the hold.
      if (rings.length === 1 && fr >= E) rings = splitRing(rings[0], fr);
    }

    frames.push({
      rings: rings.map((r) => {
        const n = r.x.length;
        let x = 0, y = 0;
        for (let i = 0; i < n; i++) { x += r.x[i]; y += r.y[i]; }
        return { pts: Array.from(r.x).flatMap((v, i) => [v, r.y[i]]), x: x / n, y: y / n, r: centre(r, fi).r, side: r.side };
      }),
    });
  }
  return frames;
};

/** A blob as a pure function of frame. The timeline is simulated once, on first use. */
export const blobSim = (script: BlobScript, fps: number) => {
  let cache: BlobFrame[] | null = null;
  return (fr: number): BlobFrame =>
    sampleAt((cache ??= simulate(script, fps)), fr - script.from, (a, b, u) => {
      if (a.rings.length !== b.rings.length) return u < 0.5 ? a : b;
      return {
        rings: a.rings.map((p, k) => {
          const q = b.rings[k];
          return { pts: lerpArr(p.pts, q.pts, u), x: p.x + (q.x - p.x) * u, y: p.y + (q.y - p.y) * u, r: p.r + (q.r - p.r) * u, side: p.side };
        }),
      };
    });
};
