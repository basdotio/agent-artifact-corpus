// Cameras: key tracks (zoom in log space) and the transform that frames a world point.
import { clamp } from "../core/anim.js";
import { inOutSoft } from "../core/ease.js";

/** Scalar keys [[t, v, ease?]] (ease shapes the segment arriving at that key). */
export function track(t, ks, { log = false } = {}) {
  if (t <= ks[0][0]) return ks[0][1];
  const last = ks[ks.length - 1];
  if (t >= last[0]) return last[1];
  for (let i = 1; i < ks.length; i++) {
    if (t <= ks[i][0]) {
      const [t0, v0] = ks[i - 1];
      const [t1, v1, e] = ks[i];
      const u = (e || inOutSoft)(clamp((t - t0) / (t1 - t0)));
      return log ? Math.exp(Math.log(v0) + (Math.log(v1) - Math.log(v0)) * u) : v0 + (v1 - v0) * u;
    }
  }
  return last[1];
}

/**
 * Camera keys [[t, {x, y, z}, ease?]]: x, y = the world point at frame centre, z = zoom.
 * Position and log-zoom share one eased parameter per segment.
 */
export function camAt(t, ks) {
  if (t <= ks[0][0]) return ks[0][1];
  const last = ks[ks.length - 1];
  if (t >= last[0]) return last[1];
  for (let i = 1; i < ks.length; i++) {
    if (t <= ks[i][0]) {
      const [t0, a] = ks[i - 1];
      const [t1, b, e] = ks[i];
      const u = (e || inOutSoft)(clamp((t - t0) / (t1 - t0)));
      return {
        x: a.x + (b.x - a.x) * u,
        y: a.y + (b.y - a.y) * u,
        z: Math.exp(Math.log(a.z) + (Math.log(b.z) - Math.log(a.z)) * u),
      };
    }
  }
  return last[1];
}

/** CSS transform (origin 0 0) that puts world point (x, y) at screen (cx, cy) at zoom z. */
export function camTf({ x, y, z }, cx = 960, cy = 540) {
  return `translate(${cx.toFixed(3)}px,${cy.toFixed(3)}px) scale(${z.toFixed(5)}) translate(${(-x).toFixed(3)}px,${(-y).toFixed(3)}px)`;
}

/** World → screen for a camera state. */
export function toScreen(c, px, py, cx = 960, cy = 540) {
  return [cx + (px - c.x) * c.z, cy + (py - c.y) * c.z];
}

/** How fast the camera moves at t (screen px per second) — drives motion-blur samples. */
export function camSpeed(t, ks, dt = 1 / 120) {
  const a = camAt(t - dt, ks), b = camAt(t + dt, ks);
  const dz = Math.abs(Math.log(b.z) - Math.log(a.z)) * 900;
  const dp = Math.hypot((b.x - a.x) * b.z, (b.y - a.y) * b.z);
  return (dz + dp) / (2 * dt);
}

/** Blur samples for a given screen speed (px/s): ~1 sample per 4 px of travel in a 1/120 s shutter. */
export function samplesFor(speed, min = 1, max = 16) {
  return Math.max(min, Math.min(max, Math.ceil(speed / 120 / 3)));
}
