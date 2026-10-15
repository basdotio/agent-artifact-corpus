// Shared motion rig: every animated element goes through these so motion stays consistent and calm.
// Principles and sources: references/motion.md.
import { Easing, interpolate, spring, SpringConfig } from "remotion";

/** One visible overshoot, then settle. For arrivals that should feel alive. */
export const POP: Partial<SpringConfig> = { damping: 12, stiffness: 170 };
/** No overshoot. For large surfaces (backgrounds, panels) where a bounce would feel busy. */
export const SOFT: Partial<SpringConfig> = { damping: 22, stiffness: 120 };

/** Accelerates away: exits. */
export const depart = Easing.bezier(0.3, 0, 1, 1);

/** Spring progress and its velocity (progress per second) at a frame. */
export const rig = (frame: number, fps: number, config: Partial<SpringConfig> = POP) => {
  const v = spring({ frame, fps, config });
  return { v, vel: (v - spring({ frame: frame - 1, fps, config })) * fps };
};

/** Volume-preserving squash and stretch: [along the motion, across it]. */
export const squash = (vel: number, amount = 0.02, max = 0.12) => {
  const s = Math.min(max, Math.abs(vel) * amount);
  return [1 + s, 1 / (1 + s)] as const;
};

/** CSS transform: `squash` along a 2D velocity (px/s), times a uniform scale `k`. */
export const squashAlong = (vx: number, vy: number, amount: number, max: number, k = 1) => {
  const [along, across] = squash(Math.hypot(vx, vy), amount, max);
  const dir = (Math.atan2(vy, vx) * 180) / Math.PI;
  return `rotate(${dir}deg) scale(${along * k}, ${k * across}) rotate(${-dir}deg)`;
};

/** Related parts start a few frames apart, so only one thing starts moving at a time. */
export const stagger = (i: number, gap = 5) => i * gap;

/** 1 while alive, easing to 0 over the last `frames` before the end; motion accelerates away. */
export const exit = (framesLeft: number, frames = 15) =>
  1 - depart(interpolate(framesLeft, [0, frames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));

/** Slow ambient breathing. Small amplitude, so it never competes with a real motion onset. */
export const breathe = (t: number, period = 7, amp = 0.012, phase = 0) => 1 + amp * Math.sin((2 * Math.PI * t) / period + phase);
