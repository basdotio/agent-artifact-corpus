import { Easing, interpolate, spring } from "remotion";

// Copy-paste curves from the Remotion best-practices rules.
export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1); // crisp UI entrance
export const EASE_IN = Easing.bezier(0.7, 0, 0.84, 0); // exits accelerate away
export const EASE_INOUT = Easing.bezier(0.65, 0, 0.35, 1);
export const POP = Easing.bezier(0.34, 1.56, 0.64, 1); // playful overshoot

// Normalised 0..1 progress over [start, start+dur] with an easing.
export const prog = (
  frame: number,
  start: number,
  dur: number,
  easing: (t: number) => number = EASE_OUT,
) =>
  interpolate(frame, [start, start + dur], [0, 1], {
    easing,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

type SpringOpts = {
  damping?: number;
  mass?: number;
  stiffness?: number;
  durationInFrames?: number;
};

// Spring progress guarded for negative frames (safe for look-behind sampling).
export const springAt = (
  frame: number,
  fps: number,
  start: number,
  opts: SpringOpts = {},
): number => {
  if (frame <= start) return 0;
  const { durationInFrames, ...config } = opts;
  return spring({
    frame: frame - start,
    fps,
    durationInFrames,
    config: { damping: 200, ...config },
  });
};

export const riseStyle = (
  p: number,
  dy = 40,
  dx = 0,
): React.CSSProperties => ({
  opacity: p,
  transform: `translate(${(1 - p) * dx}px, ${(1 - p) * dy}px)`,
});

// Typewriter by string slicing (never per-character opacity).
export const typed = (
  text: string,
  frame: number,
  start: number,
  cps: number,
  fps: number,
) => text.slice(0, Math.max(0, Math.floor(((frame - start) * cps) / fps)));

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
