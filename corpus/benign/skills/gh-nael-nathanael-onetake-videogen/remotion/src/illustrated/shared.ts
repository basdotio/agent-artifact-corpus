// Helpers shared by illustrated (simulated, motion-blurred) compositions.

export const lerpArr = (a: number[], b: number[], u: number) => a.map((v, i) => v + (b[i] - v) * u);

/** State at a fractional frame (motion-blur samples): `blend` the neighbouring precomputed frames. */
export const sampleAt = <F>(frames: F[], f: number, blend: (a: F, b: F, u: number) => F): F => {
  const c = Math.min(Math.max(f, 0), frames.length - 1);
  const i = Math.floor(c), u = c - i;
  const a = frames[i], b = frames[Math.min(i + 1, frames.length - 1)];
  if (u === 0 || a === b) return a;
  return blend(a, b, u);
};

/**
 * Frame offset for children of <CameraMotionBlur>, which samples f + 1 - (shutter/360)·k/samples, k = 1..samples.
 * Subtracting it from useCurrentFrame() makes the newest sample land on f: a trailing shutter, so movers lead
 * at their unblurred position and hit-pauses stay sharp.
 */
export const trailingShift = (shutterAngle: number, samples: number) => 1 - shutterAngle / 360 / samples;
