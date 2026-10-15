// Timeline, palette, motion helpers, shared actors, the world and the camera for AiPas.
// Scene authors: README.md in this folder lists every export.
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, interpolateColors, random, SpringConfig, staticFile } from "remotion";
import { loadFont as loadGeist } from "@remotion/google-fonts/Geist";
import { loadFont as loadGeistMono } from "@remotion/google-fonts/GeistMono";
import { POP, rig, SOFT } from "../../motion";
import words from "../../../public/illustrated/aipas/words-captions.json";
import lines from "../../../public/illustrated/aipas/lines.json";
import { BlobFrame, BlobScript, blobSim, HIT, settle } from "./blob";

export { breathe, depart, exit, POP, SOFT, stagger } from "../../motion";
export { HIT, settle } from "./blob";
export type { BlobFrame, BlobScript, Pt } from "./blob";

export const FONT = loadGeist("normal", { weights: ["500", "700"], subsets: ["latin"] }).fontFamily;
export const MONO = loadGeistMono("normal", { weights: ["500"], subsets: ["latin"] }).fontFamily;

// ---------- Timeline ----------

export const FPS = 30;
export const DURATION = 5105;
export const f = (s: number) => Math.round(s * FPS);

export type SpokenWord = { text: string; start: number; end: number; para: number; guess?: boolean };
export const WORDS: SpokenWord[] = words.words;

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
/**
 * Frame the nth `word` of a beat starts on, from the voice timings. Every event is forced onto such a frame.
 * Case and punctuation are ignored: at(4, "GPU"), at(9, "empat", 1). Throws when the beat has no such word.
 */
export const at = (beat: number, word: string, nth = 0) => {
  const hit = WORDS.filter((w) => w.para === beat - 1 && norm(w.text) === norm(word))[nth];
  if (!hit) throw new Error(`AiPas: beat ${beat} has no word "${word}" (#${nth})`);
  return f(hit.start);
};

export type Span = { start: number; end: number; mid: number; until: number };
/** Per beat (1–15): first and last narrated frame, their midpoint, and `until`, the frame the next beat mounts on. */
export const B: Record<number, Span> = Object.fromEntries(
  lines.map((l, i) => [l.n, {
    start: f(l.start), end: f(l.end), mid: Math.round((f(l.start) + f(l.end)) / 2),
    until: i + 1 < lines.length ? f(lines[i + 1].start) : DURATION,
  }]),
);
/** What every beat component receives: the composition frame. Beat n is mounted from B[n].start to B[n].until. */
export type BeatProps = { fr: number };
/** The beat mounted at a frame. */
export const beatAt = (fr: number) => {
  let n = 1;
  while (B[n + 1] && fr >= B[n + 1].start) n++;
  return n;
};

// ---------- Palette ----------

export const C = {
  ground: "#141400", deep: "#0b0b00", card: "#211f10", line: "#3d3a22", mute: "#b9ae8f", ink: "#fef9e3",
  gold: "#ddb15b", coral: "#ff6b5e", cream: "#e9dfc2", sky: "#7dd3fc",
  // Tints of the above for the set: same hues, so the palette stays at four.
  farHill: "#1a1a05", midHill: "#1e1d0a", strata: "#191809", wood: "#5a4925", woodLight: "#7b6534", leaf: "#262a12", leafLight: "#2e3316",
  sea: "#0d1f28", seaFront: "#143240", goldLight: "#f6d488", goldDark: "#a87f35", skin: "#d2a06a", skinShade: "#b98752", hair: "#2a2412",
};

/** The four kinds of AI: name on screen and colour. */
export const KIND = {
  cerdas: { name: "Sistem Cerdas", color: C.cream },
  spesialis: { name: "AI spesialis", color: C.gold },
  ringan: { name: "Model bahasa ringan", color: C.sky },
  besar: { name: "Model bahasa besar", color: C.coral },
};

// ---------- Motion ----------

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const arrive = Easing.bezier(0.2, 0, 0, 1);
export const inOut = Easing.bezier(0.65, 0, 0.35, 1);
export const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
const u01 = (v: number) => Math.max(0, Math.min(1, v));

/** 0 → 1 between frames a and b (a < b) with an easing. */
export const ramp = (fr: number, a: number, b: number, ease: (x: number) => number = inOut) =>
  interpolate(fr, [a, b], [0, 1], { ...clamp, easing: ease });

/** Spring progress and velocity (per second) starting at frame `start`. */
export const sp = (fr: number, start: number, cfg: Partial<SpringConfig> = POP) => {
  const d = fr - start;
  if (d <= 0) return { v: 0, vel: 0 };
  if (d > 150) return { v: 1, vel: 0 };
  return rig(d, FPS, cfg);
};

/**
 * A big event on frame E as one curve: winds up the opposite way to -back over `wind` frames, holds for the
 * HIT-frame hit-pause, releases on E, overshoots 1 once and settles.
 */
export const punch = (fr: number, E: number, wind = 12, back = 0.08) =>
  fr >= E ? settle((fr - E) / FPS) : -back * ramp(fr, E - HIT - wind, E - HIT);

/** Inertial bounce after an impulse on frame E (Dan Ebberts). */
export const bounce = (fr: number, E: number, v: number, freq = 3, decayRate = 5) => {
  const t = (fr - E) / FPS;
  if (t < 0) return 0;
  const w = freq * 2 * Math.PI;
  return (v * Math.sin(t * w)) / Math.exp(decayRate * t) / w;
};
export const decay = (fr: number, E: number, rate: number) => (fr < E ? 0 : Math.exp(-((fr - E) / FPS) * rate));

/** Velocity (px/s) of a 2D path at frame fr, by finite difference. */
export const vel2 = (p: (fr: number) => [number, number], fr: number): [number, number] => {
  const a = p(fr - 0.5), b = p(fr + 0.5);
  return [(b[0] - a[0]) * FPS, (b[1] - a[1]) * FPS];
};

/** `squash` prop value from a speed (px/s) along the body's long axis: negative, so the actor stretches. */
export const stretchBy = (speed: number, k = 1 / 2400, max = 0.2) => -Math.min(max, Math.abs(speed) * k);

export const mixC = (a: string, b: string, u: number) => interpolateColors(u01(u), [0, 1], [a, b]);

// Area-preserving scale pair: s > 0 flattens, s < 0 stretches.
const sq = (s: number): [number, number] => (s >= 0 ? [1 + s, 1 / (1 + s)] : [1 / (1 - s), 1 - s]);

// One blink per 3.6 s window at a seeded moment inside it, so no two actors blink in a rhythm.
const blinkAt = (t: number, seed: number) => {
  const span = 3.6, q = t + seed * 1.37, i = Math.floor(q / span);
  const d = q - (i + 0.12 + 0.72 * random(`blink${seed}-${i}`)) * span;
  return d >= 0 && d < 0.2 ? Math.sin((d / 0.2) * Math.PI) : 0;
};

// ---------- Drawing ----------

/** An SVG layer in world coordinates for code-drawn shapes. Paint order follows JSX order, as with every actor. */
export const Draw: React.FC<{ children?: React.ReactNode; opacity?: number; blend?: React.CSSProperties["mixBlendMode"] }> = ({ children, opacity, blend }) => (
  <svg width={1} height={1} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", opacity, mixBlendMode: blend }}>{children}</svg>
);

const useUid = () => "p" + React.useId().replace(/[^a-zA-Z0-9]/g, "");

// A lit flat form: darker fill, the base colour offset up-left and clipped to the outline, so a shading
// crescent sits lower-right.
const Lit: React.FC<{ d: string; base: string; shade: string; s?: number }> = ({ d, base, shade, s = 5 }) => {
  const id = useUid();
  return (
    <g>
      <clipPath id={id}><path d={d} /></clipPath>
      <path d={d} fill={shade} />
      <g clipPath={`url(#${id})`}><path d={d} fill={base} transform={`translate(${-s} ${-s * 0.9})`} /></g>
    </g>
  );
};

// ---------- Creatures ----------

export type ActorProps = {
  /** World position of the actor's anchor (see each actor). */
  x: number;
  y: number;
  /** Frame, may be fractional. Drives idle motion, blinks and cycles. */
  t: number;
  scale?: number;
  /** Area-preserving squash: above 0 flattens (wider, shorter), below 0 stretches. 0.1 is clearly visible. */
  squash?: number;
  /** Degrees, clockwise on screen, about the anchor. */
  tilt?: number;
  opacity?: number;
  /** Mirror the art so the actor faces the other way. */
  flip?: boolean;
  /** Idle phase. Give each instance its own, so no two move in sync. */
  seed?: number;
  /** 1 by default. 0 freezes breathing, bob and blinks, for hit-pauses. */
  idle?: number;
};

type Art = { name: string; w: number; h: number; ax: number; ay: number; lid: string; eyes: [number, number, number, number][] };
// Anchor as a fraction of the crop; eye boxes in crop pixels; lid colour sampled beside each eye.
const ART = {
  whale: { name: "whale", w: 1168, h: 804, ax: 0.5, ay: 0.55, lid: "#fe684f", eyes: [[779, 465, 824, 492]] },
  owl: { name: "owl", w: 376, h: 460, ax: 0.513, ay: 0.965, lid: "#fdedc4", eyes: [[146, 110, 200, 158], [257, 111, 305, 158]] },
  ant: { name: "ant", w: 652, h: 432, ax: 0.5, ay: 0.963, lid: "#feedc2", eyes: [[475, 157, 518, 194]] },
  eaglePerch: { name: "eagle-perch", w: 348, h: 396, ax: 0.575, ay: 0.965, lid: "#feefc8", eyes: [[245, 26, 269, 50]] },
  eagleFly: { name: "eagle-fly", w: 564, h: 400, ax: 0.358, ay: 0.95, lid: "#fdefc8", eyes: [[404, 246, 428, 270]] },
} satisfies Record<string, Art>;

const pose = (k: number, s: number, rot: number, flip?: boolean) => {
  const [sx, sy] = sq(s);
  return `rotate(${rot}deg) scale(${(flip ? -1 : 1) * k * sx}, ${k * sy})`;
};

// A sprite pinned by its anchor. `inner` is a second transform about `pivot` (fractions of the crop), for
// cycles that turn about the body instead of the feet.
const Sprite: React.FC<{ art: Art; x: number; y: number; xf: string; opacity?: number; blink?: number; inner?: string; pivot?: [number, number] }> = ({
  art, x, y, xf, opacity = 1, blink = 0, inner, pivot,
}) => {
  if (opacity <= 0.001) return null;
  return (
    <div style={{
      position: "absolute", left: x - art.w * art.ax, top: y - art.h * art.ay, width: art.w, height: art.h,
      transformOrigin: `${art.ax * 100}% ${art.ay * 100}%`, transform: xf, opacity,
    }}>
      <div style={{ width: art.w, height: art.h, transformOrigin: pivot ? `${pivot[0] * 100}% ${pivot[1] * 100}%` : undefined, transform: inner }}>
        <Img src={staticFile(`illustrated/aipas/${art.name}.png`)} style={{ display: "block", width: art.w, height: art.h }} />
        {blink > 0.03 && art.eyes.map(([x0, y0, x1, y1], i) => (
          <div key={i} style={{ position: "absolute", left: x0 - 3, top: y0 - 3, width: x1 - x0 + 6, height: (y1 - y0 + 6) * 0.86 * blink, overflow: "hidden" }}>
            <div style={{ width: x1 - x0 + 6, height: y1 - y0 + 6, borderRadius: "50%", background: art.lid }} />
          </div>
        ))}
      </div>
    </div>
  );
};

const TAU = 2 * Math.PI;

/**
 * The whale (model bahasa besar). Anchor: body centre. The art faces right. Idle: slow bob, breath and a faint
 * roll. `swim` 0..1 rocks and stretches the whole body in a 1.1 Hz cycle, which reads as the tail pumping.
 */
export const Whale: React.FC<ActorProps & { swim?: number }> = ({
  x, y, t, scale = 1, squash = 0, tilt = 0, opacity, flip, seed = 0, idle = 1, swim = 0,
}) => {
  const s = t / FPS, ph = seed * 1.9, cyc = TAU * 1.1 * s + ph;
  const bob = idle * 7 * Math.sin((TAU * s) / 5.3 + ph);
  const breath = idle * 0.012 * Math.sin((TAU * s) / 6.1 + ph + 1);
  const rot = tilt + idle * 1.1 * Math.sin((TAU * s) / 7.7 + ph) + swim * 2.6 * Math.sin(cyc);
  return (
    <Sprite art={ART.whale} x={x} y={y + bob * scale} xf={pose(scale, squash + breath + swim * 0.025 * Math.sin(cyc + 1.6), rot, flip)}
      opacity={opacity} blink={idle * blinkAt(s, 11 + seed)} />
  );
};

/** The owl (model bahasa ringan). Anchor: feet. The art faces the viewer. Idle: breath, a slow head sway, blinks. */
export const Owl: React.FC<ActorProps> = ({ x, y, t, scale = 1, squash = 0, tilt = 0, opacity, flip, seed = 0, idle = 1 }) => {
  const s = t / FPS, ph = seed * 2.3 + 0.7;
  const breath = idle * 0.016 * Math.sin((TAU * s) / 3.9 + ph);
  const rot = tilt + idle * 1.3 * Math.sin((TAU * s) / 6.3 + ph + 2);
  return <Sprite art={ART.owl} x={x} y={y} xf={pose(scale, squash + breath, rot, flip)} opacity={opacity} blink={idle * blinkAt(s, 23 + seed)} />;
};

/**
 * An ant (Sistem Cerdas). Anchor: feet, mid-body. The art faces right. Idle: a small rock and breath.
 * `walk` 0..1 adds a 4 Hz rock and hop, which stands in for the legs stepping.
 */
export const Ant: React.FC<ActorProps & { walk?: number }> = ({
  x, y, t, scale = 1, squash = 0, tilt = 0, opacity, flip, seed = 0, idle = 1, walk = 0,
}) => {
  const s = t / FPS, ph = seed * 1.7 + 0.3, cyc = TAU * 4 * s + ph * 3;
  const breath = idle * 0.012 * Math.sin((TAU * s) / 2.9 + ph);
  const rot = tilt + idle * 0.8 * Math.sin((TAU * s) / 2.3 + ph) + walk * 2.4 * Math.sin(cyc);
  const hop = walk * 4 * Math.abs(Math.sin(cyc));
  return (
    <Sprite art={ART.ant} x={x} y={y - hop * scale} xf={pose(scale, squash + breath + walk * 0.03 * Math.sin(cyc * 2), rot, flip)}
      opacity={opacity} blink={idle * blinkAt(s, 37 + seed)} />
  );
};

/**
 * The eagle (AI spesialis). Anchor: talons, perched and flying alike, so it can land on a point. The art faces
 * right. `fly` 0 is the perched sprite, 1 the flying one; they cross over between 0.3 and 0.7, so drive it with
 * a 2–3 frame ramp under a crouch-and-launch squash. `flap` 0..1 (default: `fly`) squashes the spread wings
 * about the body in a 3 Hz cycle with a counter-bob, which reads as a wingbeat; 0 glides.
 */
export const Eagle: React.FC<ActorProps & { fly?: number; flap?: number }> = ({
  x, y, t, scale = 1, squash = 0, tilt = 0, opacity = 1, flip, seed = 0, idle = 1, fly = 0, flap,
}) => {
  const s = t / FPS, ph = seed * 2.1 + 1.1, u = u01((fly - 0.3) / 0.4), beat = flap ?? fly;
  const blink = idle * blinkAt(s, 53 + seed);
  const breath = idle * 0.014 * Math.sin((TAU * s) / 4.4 + ph);
  const sway = idle * 1.0 * Math.sin((TAU * s) / 5.9 + ph);
  const cyc = TAU * 3 * s + ph;
  const fold = 1 - 0.22 * beat * (0.5 + 0.5 * Math.sin(cyc));
  return (
    <>
      <Sprite art={ART.eaglePerch} x={x} y={y} xf={pose(scale, squash + breath, tilt + sway, flip)} opacity={opacity * (1 - u)} blink={blink} />
      <Sprite art={ART.eagleFly} x={x} y={y - (beat * 8 * Math.sin(cyc - 0.9) + idle * (1 - beat) * 5 * Math.sin((TAU * s) / 3.1 + ph)) * scale}
        xf={pose(scale, squash, tilt + beat * 2.5 * Math.cos(cyc), flip)} opacity={opacity * u} blink={blink}
        inner={`scale(${1 / fold}, ${fold})`} pivot={[0.53, 0.72]} />
    </>
  );
};

// ---------- The need: a jelly blob ----------

/**
 * A need blob's soft body from a script: an art-directed path it lags behind, an optional floor to land on,
 * wobble kicks, and an optional split with squeeze, pinch, HIT-frame hold and overshoot. Call once at module
 * level; the result is a pure function of frame for <NeedBlob sim>.
 */
export const blob = (script: BlobScript) => blobSim(script, FPS);

const smooth = (p: number[]) => {
  const n = p.length / 2;
  const P = (i: number) => [p[((i + n) % n) * 2], p[((i + n) % n) * 2 + 1]];
  let d = `M ${P(0)[0].toFixed(1)} ${P(0)[1].toFixed(1)}`;
  for (let i = 0; i < n; i++) {
    const a = P(i - 1), b = P(i), c = P(i + 1), e = P(i + 2);
    d += ` C ${(b[0] + (c[0] - a[0]) / 6).toFixed(1)} ${(b[1] + (c[1] - a[1]) / 6).toFixed(1)} ${(c[0] - (e[0] - b[0]) / 6).toFixed(1)} ${(c[1] - (e[1] - b[1]) / 6).toFixed(1)} ${c[0].toFixed(1)} ${c[1].toFixed(1)}`;
  }
  return d + " Z";
};

// A label in at most two balanced lines.
const twoLines = (s: string) => {
  const w = s.split(" ");
  if (s.length <= 11 || w.length < 2) return [s];
  let best = [s], len = s.length;
  for (let i = 1; i < w.length; i++) {
    const a = w.slice(0, i).join(" "), b = w.slice(i).join(" ");
    if (Math.max(a.length, b.length) < len) { best = [a, b]; len = Math.max(a.length, b.length); }
  }
  return best;
};

/**
 * A need: a cream jelly blob with a short label. Shape and position come from `sim` (see `blob`).
 * After a split, pass two labels, left half first. `spin` (degrees) turns the inner bubbles, which reads as
 * rolling while the label stays upright: use (distance travelled / radius) in degrees.
 */
export const NeedBlob: React.FC<{
  sim: (fr: number) => BlobFrame; fr: number; label?: string | [string, string]; color?: string; spin?: number; opacity?: number; glow?: number;
}> = ({ sim, fr, label, color = C.cream, spin = 0, opacity = 1, glow = 1 }) => {
  const id = useUid();
  const { rings } = sim(fr);
  const light = mixC(color, "#ffffff", 0.42), shade = mixC(color, C.ground, 0.2), rim = mixC(color, "#ffffff", 0.75);
  return (
    <Draw opacity={opacity}>
      {rings.map((ring, k) => {
        const d = smooth(ring.pts), r = ring.r, cx = ring.x, cy = ring.y;
        const text = Array.isArray(label) ? (rings.length > 1 ? label[k] : label[0]) : label;
        const rowsOf = text ? twoLines(text) : [];
        const fs = Math.min(0.4 * r, (1.62 * r) / (0.56 * Math.max(1, ...rowsOf.map((l) => l.length))));
        // The highlight follows the outline: its own upper-left points pulled toward the centre.
        const arc: [number, number][] = [];
        for (let i = 0; i < ring.pts.length; i += 2) {
          const a = (Math.atan2(ring.pts[i + 1] - cy, ring.pts[i] - cx) * 180) / Math.PI;
          if (a > -168 && a < -98) arc.push([cx + (ring.pts[i] - cx) * 0.76, cy + (ring.pts[i + 1] - cy) * 0.76]);
        }
        arc.sort((m, n) => Math.atan2(m[1] - cy, m[0] - cx) - Math.atan2(n[1] - cy, n[0] - cx));
        return (
          <g key={k}>
            {glow > 0.01 && <path d={d} fill={color} opacity={0.16 * glow} style={{ filter: `blur(${(r * 0.22).toFixed(1)}px)` }} />}
            <clipPath id={`${id}${k}`}><path d={d} /></clipPath>
            <g clipPath={`url(#${id}${k})`}>
              <path d={d} fill={shade} />
              <path d={d} fill={color} transform={`translate(${-r * 0.07} ${-r * 0.08})`} />
              <path d={d} fill={light} opacity={0.5} transform={`translate(${cx} ${cy}) scale(0.78) translate(${-cx - r * 0.1} ${-cy - r * 0.12})`} />
              {[[0.52, 0, 0.1], [0.4, 150, 0.065]].map(([rad, off, size], j) => {
                const a = ((spin + off) * Math.PI) / 180;
                return <circle key={j} cx={cx + Math.cos(a) * rad * r} cy={cy + Math.sin(a) * rad * r} r={size * r} fill={rim} opacity={0.5} />;
              })}
              <path d={d} fill="none" stroke={rim} strokeWidth={r * 0.06} opacity={0.75} />
            </g>
            {arc.length > 2 && (
              <path d={`M ${arc.map((q) => `${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(" L ")}`} fill="none" stroke={rim} strokeWidth={r * 0.07}
                strokeLinecap="round" strokeLinejoin="round" opacity={0.8} />
            )}
            {rowsOf.map((l, i) => (
              <text key={i} x={cx} y={cy + fs * 0.35 + (i - (rowsOf.length - 1) / 2) * fs * 1.08} textAnchor="middle"
                fontFamily={FONT} fontWeight={700} fontSize={fs} fill={C.ground}>{l}</text>
            ))}
          </g>
        );
      })}
    </Draw>
  );
};

// ---------- GPU cubes ----------

/** The most cubes a pile draws. A larger `count` draws this many: make a mountain with a bigger `size`. */
export const GPU_CAP = 120;

const cubeFaces = (w: number) => {
  const a = w / 2, q = w / 4, h = w * 0.56;
  return {
    left: `0,0 ${-a},${-q} ${-a},${-q - h} 0,${-h}`,
    right: `0,0 ${a},${-q} ${a},${-q - h} 0,${-h}`,
    top: `0,${-h} ${-a},${-q - h} 0,${-2 * q - h} ${a},${-q - h}`,
    height: 2 * q + h,
  };
};
const CubeShape: React.FC<{ w: number }> = ({ w }) => {
  const c = cubeFaces(w);
  return (
    <g strokeLinejoin="round" strokeWidth={w * 0.05}>
      <polygon points={c.left} fill={C.gold} stroke={C.gold} />
      <polygon points={c.right} fill={C.goldDark} stroke={C.goldDark} />
      <polygon points={c.top} fill={C.goldLight} stroke={C.goldLight} />
    </g>
  );
};
const Glow: React.FC<{ id: string; x: number; y: number; rx: number; ry: number; color: string; opacity: number }> = ({ id, x, y, rx, ry, color, opacity }) => (
  <>
    <defs>
      <radialGradient id={id}><stop offset="0%" stopColor={color} stopOpacity={1} /><stop offset="100%" stopColor={color} stopOpacity={0} /></radialGradient>
    </defs>
    <ellipse cx={x} cy={y} rx={rx} ry={ry} fill={`url(#${id})`} opacity={opacity} style={{ mixBlendMode: "screen" }} />
  </>
);

/** One GPU: a small glowing gold cube. Anchor: the bottom corner it rests on. `size` is its width. */
export const GpuCube: React.FC<{ x: number; y: number; size?: number; squash?: number; glow?: number; opacity?: number }> = ({
  x, y, size = 30, squash = 0, glow = 1, opacity = 1,
}) => {
  const id = useUid();
  const [sx, sy] = sq(squash);
  return (
    <Draw opacity={opacity}>
      {glow > 0.01 && <Glow id={id} x={x} y={y - size * 0.5} rx={size * 1.7} ry={size * 1.7} color={C.gold} opacity={0.4 * glow} />}
      <g transform={`translate(${x} ${y}) scale(${sx} ${sy})`}><CubeShape w={size} /></g>
    </Draw>
  );
};

/** Where the cubes of a pile of `count` sit, relative to its base centre, bottom row first. */
export const pileLayout = (count: number, size = 30, seed = "pile") => {
  const n = Math.max(0, Math.min(GPU_CAP, Math.round(count)));
  const base = Math.ceil((Math.sqrt(8 * n + 1) - 1) / 2);
  const out: { x: number; y: number; row: number }[] = [];
  for (let row = 0, left = n; left > 0; row++) {
    const m = Math.min(left, base - row);
    for (let i = 0; i < m; i++) {
      out.push({
        x: (i - (m - 1) / 2) * size * 1.04 + (random(`${seed}x${out.length}`) - 0.5) * size * 0.08,
        y: -row * size * 0.62, row,
      });
    }
    left -= m;
  }
  return { cubes: out, width: base * size * 1.04, height: (out.length ? out[out.length - 1].row * 0.62 + 1.06 : 0) * size };
};

/**
 * A pile of GPU cubes: 1 is a crumb, GPU_CAP a mountain. Anchor: base centre on the ground. With `start`, the
 * cubes drop in one by one from that frame, bottom row first, each with a landing squash; the whole pile lands
 * within about 1.5 s whatever the count. Without it the pile is at rest.
 */
export const GpuPile: React.FC<{
  x: number; y: number; count: number; fr: number; start?: number; size?: number; seed?: string; glow?: number; opacity?: number;
}> = ({ x, y, count, fr, start, size = 30, seed = "pile", glow = 1, opacity = 1 }) => {
  const id = useUid();
  const { cubes, width, height } = pileLayout(count, size, seed);
  const gap = Math.min(3, 40 / Math.max(1, cubes.length));
  const FALL = 7;
  const landed = start === undefined ? 1 : ramp(fr, start + FALL, start + FALL + gap * cubes.length + 1, (v) => v);
  return (
    <Draw opacity={opacity}>
      {glow > 0.01 && landed > 0 && (
        <Glow id={id} x={x} y={y - height * 0.45} rx={width * 0.6 + size * 1.2} ry={height * 0.6 + size * 1.2} color={C.gold} opacity={0.34 * glow * (0.3 + 0.7 * landed)} />
      )}
      {cubes.map((c, i) => {
        const s0 = start === undefined ? -1e6 : start + i * gap;
        if (fr < s0) return null;
        const u = ramp(fr, s0, s0 + FALL, Easing.in(Easing.quad));
        const [sx, sy] = sq(bounce(fr, s0 + FALL, 2.4, 3.5, 9));
        return (
          <g key={i} transform={`translate(${x + c.x} ${y + c.y - (1 - u) * size * 4}) scale(${sx} ${sy})`} opacity={Math.min(1, (fr - s0) / 2)}>
            <CubeShape w={size} />
          </g>
        );
      })}
    </Draw>
  );
};

// ---------- People ----------

export type Who = "rina" | "budi" | "dinda";
const PEOPLE: Record<Who, { k: number; body: string; shade: string }> = {
  rina: { k: 1, body: C.cream, shade: "#c9bd98" },
  budi: { k: 1.04, body: C.mute, shade: "#958a6c" },
  dinda: { k: 0.74, body: "#d8cdae", shade: "#b5a987" },
};
const BODY_D = "M -58 -30 V -112 A 58 56 0 0 1 58 -112 V -30 A 30 30 0 0 1 28 0 H -28 A 30 30 0 0 1 -58 -30 Z";
const HEAD_Y = -212;
const circ = (cx: number, cy: number, r: number) => `M ${cx - r} ${cy} A ${r} ${r} 0 1 0 ${cx + r} ${cy} A ${r} ${r} 0 1 0 ${cx - r} ${cy} Z`;

/** Head and face of a person, centred on 0, 0 with radius 46. Used by Person and by Card's `who`. */
export const PersonHead: React.FC<{ who: Who; t: number; happy?: number; look?: number; seed?: number }> = ({ who, t, happy = 0, look = 0, seed = 0 }) => {
  const blink = happy > 0.6 ? 0 : blinkAt(t / FPS, 71 + seed + who.length);
  const lx = 6 * Math.max(-1, Math.min(1, look));
  return (
    <g>
      {who === "rina" && <circle cx={0} cy={-56} r={18} fill={C.hair} />}
      {who === "dinda" && [-1, 1].map((sd) => <circle key={sd} cx={sd * 48} cy={-22} r={15} fill={C.hair} />)}
      <Lit d={circ(0, 0, 46)} base={C.skin} shade={C.skinShade} s={5} />
      <path d={who === "budi" ? "M -46.8 -8 A 47.5 47.5 0 0 1 46.8 -8 Q 26 -34 0 -34 Q -26 -34 -46.8 -8 Z" : "M -48 0 A 48 48 0 0 1 48 0 Q 36 -30 0 -30 Q -36 -30 -48 0 Z"} fill={C.hair} />
      {[-1, 1].map((sd) => (
        <g key={sd}>
          <ellipse cx={sd * 16 + lx} cy={2} rx={4.6} ry={4.6 * (1 - 0.9 * blink) * (1 - happy)} fill={C.hair} />
          {happy > 0.01 && <path d={`M ${sd * 16 + lx - 7} 4 Q ${sd * 16 + lx} -6 ${sd * 16 + lx + 7} 4`} stroke={C.hair} strokeWidth={3.4} strokeLinecap="round" fill="none" opacity={happy} />}
        </g>
      ))}
      <path d={`M ${-9 - 3 * happy + lx} 17 Q ${lx} ${24 + 8 * happy} ${9 + 3 * happy + lx} 17`} stroke={C.hair} strokeWidth={3.2} strokeLinecap="round" fill="none" />
    </g>
  );
};

/**
 * A person of the bank case: round head on a rounded body. Anchor: feet. `who`: "rina" (gold scarf), "budi",
 * "dinda" (smaller). Idle: breath, a slow sway, blinks. `happy` 0..1 closes the eyes into arcs and widens the
 * smile; `look` -1..1 shifts the face left or right.
 */
export const Person: React.FC<ActorProps & { who: Who; happy?: number; look?: number }> = ({
  x, y, t, who, scale = 1, squash = 0, tilt = 0, opacity = 1, flip, seed = 0, idle = 1, happy = 0, look = 0,
}) => {
  const p = PEOPLE[who], s = t / FPS, ph = seed * 1.3 + who.length;
  const [sx, sy] = sq(squash + idle * 0.012 * Math.sin((TAU * s) / 3.7 + ph));
  const k = scale * p.k;
  const rot = tilt + idle * 0.8 * Math.sin((TAU * s) / 5.1 + ph);
  return (
    <Draw opacity={opacity}>
      <ellipse cx={x} cy={y + 3} rx={64 * k * sx} ry={9 * k} fill={C.deep} opacity={0.55} />
      <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${(flip ? -1 : 1) * k * sx} ${k * sy})`}>
        <Lit d={BODY_D} base={p.body} shade={p.shade} s={7} />
        {who === "budi" && <path d="M -20 -166 L 0 -138 L 20 -166" stroke={p.shade} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round" fill="none" />}
        {who === "rina" && (
          <g>
            <rect x={20} y={-168} width={24} height={56} rx={11} fill={C.goldDark} transform="rotate(-8 32 -168)" />
            <rect x={-44} y={-178} width={88} height={24} rx={12} fill={C.gold} />
          </g>
        )}
        <g transform={`translate(0 ${HEAD_Y})`}><PersonHead who={who} t={idle ? t : 0} happy={happy} look={look} seed={seed} /></g>
      </g>
    </Draw>
  );
};

// ---------- UI: card, chips, bubble ----------

/**
 * A chip. Inline by default (inside a Card or your own layout); with x, y it is centred on that world point.
 * With `fr` and `start` it pops in on that frame.
 */
export const Tag: React.FC<{ text: string; color?: string; x?: number; y?: number; fr?: number; start?: number; size?: number }> = ({
  text, color = C.gold, x, y, fr, start, size = 26,
}) => {
  const v = fr === undefined || start === undefined ? 1 : sp(fr, start).v;
  if (v <= 0.001) return x === undefined ? <span style={{ display: "inline-block", visibility: "hidden", fontSize: size, padding: `${size * 0.3}px ${size * 0.7}px` }}>{text}</span> : null;
  const chip = (
    <span style={{
      display: "inline-block", fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.15, color, whiteSpace: "nowrap",
      background: mixC(color, C.card, 0.84), border: `${Math.max(1.5, size * 0.07)}px solid ${color}`, borderRadius: 999,
      padding: `${size * 0.3}px ${size * 0.7}px`, transform: `scale(${v})`,
    }}>{text}</span>
  );
  if (x === undefined || y === undefined) return chip;
  return <div style={{ position: "absolute", left: x, top: y, transform: "translate(-50%, -50%)" }}>{chip}</div>;
};

/** A small mono label, upper case, centred on a world point (or left-aligned from it). With `fr` and `start` it rises in. */
export const Label: React.FC<{ text: string; x: number; y: number; color?: string; size?: number; align?: "center" | "left"; fr?: number; start?: number }> = ({
  text, x, y, color = C.mute, size = 20, align = "center", fr, start,
}) => {
  const v = fr === undefined || start === undefined ? 1 : sp(fr, start, SOFT).v;
  if (v <= 0.001) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y + (1 - v) * size * 0.5, transform: `translate(${align === "center" ? "-50%" : "0"}, -50%)`, opacity: v }}>
      <span style={{ fontFamily: MONO, fontWeight: 500, fontSize: size, letterSpacing: "0.06em", textTransform: "uppercase", color, whiteSpace: "nowrap" }}>{text}</span>
    </div>
  );
};

/**
 * A UI card on the card colour: title row (with an optional face), label–value rows, chips, then `children`.
 * Anchor: top centre. It springs open downward on `start`, its shadow 4 frames behind; rows and chips follow
 * 5 frames apart unless each carries its own `at` frame.
 */
export const Card: React.FC<{
  x: number; y: number; fr: number; start?: number; w?: number; title: string; sub?: string; who?: Who;
  rows?: { k: string; v: string; at?: number }[]; tags?: { text: string; color?: string; at?: number }[];
  children?: React.ReactNode; opacity?: number; scale?: number;
}> = ({ x, y, fr, start = -1e6, w = 600, title, sub, who, rows = [], tags = [], children, opacity = 1, scale = 1 }) => {
  const open = sp(fr, start).v, shadow = sp(fr, start + 4).v;
  if (open <= 0.001) return null;
  const xf = (v: number) => `scale(${scale * (0.86 + 0.14 * v)}, ${scale * v})`;
  const rise = (v: number): React.CSSProperties => ({ opacity: u01(v * 1.5), transform: `translateY(${(1 - v) * 10}px)` });
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y, width: w, opacity }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 24, background: "#000", opacity: 0.45 * u01(shadow), filter: "blur(18px)", transformOrigin: "50% 0", transform: `translateY(16px) ${xf(shadow)}` }} />
      <div style={{
        position: "relative", boxSizing: "border-box", width: w, padding: 28, borderRadius: 24, background: C.card, border: `1.5px solid ${C.line}`,
        transformOrigin: "50% 0", transform: xf(open), fontFamily: FONT, color: C.ink,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {who && <svg width={76} height={76} viewBox="-60 -66 120 120" style={{ flex: "none", overflow: "visible" }}><PersonHead who={who} t={fr} /></svg>}
          <div>
            <div style={{ fontWeight: 700, fontSize: 42, lineHeight: 1.15 }}>{title}</div>
            {sub && <div style={{ fontFamily: MONO, fontWeight: 500, fontSize: 21, letterSpacing: "0.06em", textTransform: "uppercase", color: C.mute, marginTop: 6 }}>{sub}</div>}
          </div>
        </div>
        {rows.map((r, i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16, borderTop: `1.5px solid ${C.line}`, marginTop: 16, paddingTop: 14, ...rise(sp(fr, r.at ?? start + 8 + 5 * i).v) }}>
            <span style={{ fontFamily: MONO, fontWeight: 500, fontSize: 21, letterSpacing: "0.06em", textTransform: "uppercase", color: C.mute }}>{r.k}</span>
            <span style={{ fontWeight: 500, fontSize: 31 }}>{r.v}</span>
          </div>
        ))}
        {tags.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 20 }}>
            {tags.map((g, j) => <Tag key={j} text={g.text} color={g.color} fr={fr} start={g.at ?? start + 8 + 5 * (rows.length + j)} />)}
          </div>
        )}
        {children}
      </div>
    </div>
  );
};

/** A speech bubble that pops out of its tail tip (x, y) on `start`. `side` is the way the bubble leans. */
export const SpeechBubble: React.FC<{ x: number; y: number; text: string; fr: number; start?: number; side?: "left" | "right"; size?: number; color?: string }> = ({
  x, y, text, fr, start = -1e6, side = "right", size = 38, color = C.ink,
}) => {
  const { v, vel } = sp(fr, start);
  if (v <= 0.001) return null;
  const dir = side === "right" ? 1 : -1;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: 0, height: 0, transform: `rotate(${-dir * vel * 1.2}deg) scale(${v})` }}>
      <div style={{ position: "absolute", left: dir * 14 - size * 0.3, bottom: size * 0.42, width: size * 0.6, height: size * 0.6, background: color, transform: "rotate(45deg)", borderRadius: size * 0.1 }} />
      <div style={{
        position: "absolute", bottom: size * 0.62, [side === "right" ? "left" : "right"]: -size * 0.9, whiteSpace: "nowrap",
        fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.1, color: C.ground, background: color, borderRadius: size * 0.6,
        padding: `${size * 0.42}px ${size * 0.72}px`,
      }}>{text}</div>
    </div>
  );
};

// ---------- Juice ----------

/** Bits that fly out from a point between two angles (degrees, 0 = right, -90 = up), slow down, then linger and drift. */
export const Burst: React.FC<{
  fr: number; E: number; seed: string; n: number; x: number; y: number; colors: string[];
  speed?: [number, number]; size?: [number, number]; life?: number; arc?: [number, number];
}> = ({ fr, E, seed, n, x, y, colors, speed = [220, 480], size = [7, 14], life = 1.6, arc = [0, 360] }) => {
  const tau = (fr - E) / FPS;
  if (tau < 0 || tau > life) return null;
  return (
    <Draw>
      {Array.from({ length: n }, (_, i) => {
        const r = (k: string) => random(`${seed}${k}${i}`);
        const a = ((arc[0] + ((i + r("a") * 0.8) / n) * (arc[1] - arc[0])) * Math.PI) / 180;
        const travel = ((speed[0] + r("v") * (speed[1] - speed[0])) * (1 - Math.exp(-4 * tau))) / 4;
        const s = (size[0] + r("s") * (size[1] - size[0])) * interpolate(tau, [0, 0.1, life], [0.3, 1, 0.5], clamp);
        return (
          <circle key={i} cx={x + Math.cos(a) * travel + 8 * Math.sin(tau * 0.9 + i)} cy={y + Math.sin(a) * travel - 16 * tau} r={s / 2}
            fill={colors[i % colors.length]} opacity={interpolate(tau, [0, 0.04, 0.5, life], [0, 1, 0.85, 0], clamp)} />
        );
      })}
    </Draw>
  );
};

/** A soft flash of light at a point on frame E, for payoffs. */
export const Flash: React.FC<{ fr: number; E: number; x: number; y: number; r: number; color?: string; amp?: number }> = ({ fr, E, x, y, r, color = C.ink, amp = 0.7 }) => {
  const id = useUid();
  const o = decay(fr, E, 8) * amp;
  if (o < 0.01) return null;
  return <Draw><Glow id={id} x={x} y={y} rx={r * (1.3 - (0.3 * o) / amp)} ry={r * (1.3 - (0.3 * o) / amp)} color={color} opacity={o} /></Draw>;
};

// ---------- The world ----------

/** World y of the land surface every creature stands on, of the waterline, and of the bank floor. */
export const GROUND = 1000;
export const SEA = 1040;
export const DESK_FLOOR = 3900;

/** Anchor points in world coordinates. Position against these, never against raw numbers. */
export const P = {
  /** The ant trail's start (the anthill) and end, on the ground. */
  trail0: { x: 220, y: GROUND },
  trail1: { x: 1500, y: GROUND },
  /** Middle of the ant column, on the ground. */
  ants: { x: 770, y: GROUND },
  /** Top of the eagle's perch: where its talons rest. */
  perch: { x: 1750, y: GROUND - 200 },
  /** Top of the owl's branch: where its feet rest. */
  branch: { x: 3000, y: GROUND - 260 },
  /** The home shore, on the ground: the first blob lands here and the server rack will stand here. */
  shore: { x: 3750, y: GROUND },
  /** The whale's home, on the waterline. */
  sea: { x: 5100, y: SEA },
  /** Far across the sea, in the sky: where data leaves to. */
  far: { x: 5750, y: 380 },
  /** Centre of the sky in the wide shot: where needs, data and titles land when the whole world shows. */
  wide: { x: 2950, y: -400 },
  /** The bank, below the landscape: desk centre on its floor, Bu Rina's feet, top centres of two cards. */
  desk: { x: 2450, y: DESK_FLOOR },
  rina: { x: 2130, y: DESK_FLOOR },
  card: { x: 3060, y: 3250 },
  card2: { x: 3720, y: 3250 },
};

/** Home pose of each creature: spread into the actor to stand it where it lives. */
export const HOME = {
  ants: [440, 660, 880, 1100].map((x, i) => ({ x, y: GROUND, scale: 0.3, seed: i + 1 })),
  eagle: { x: P.perch.x, y: P.perch.y, scale: 0.85 },
  owl: { x: P.branch.x, y: P.branch.y, scale: 0.8 },
  whale: { x: P.sea.x, y: SEA - 150, scale: 0.95, flip: true },
};

export type Resident = "ants" | "eagle" | "owl" | "whale";
/**
 * The four kinds at home, idle. Every beat draws them, so the world stays inhabited across beats; `hide` the
 * ones a beat animates itself. Their idle is a function of the frame alone, so two beats that both draw a
 * creature at home hand it over without a jump.
 */
export const Residents: React.FC<{ t: number; hide?: Resident[]; opacity?: number }> = ({ t, hide = [], opacity }) => (
  <>
    {!hide.includes("ants") && HOME.ants.map((a) => <Ant key={a.seed} {...a} t={t} opacity={opacity} />)}
    {!hide.includes("eagle") && <Eagle {...HOME.eagle} t={t} opacity={opacity} />}
    {!hide.includes("owl") && <Owl {...HOME.owl} t={t} opacity={opacity} />}
    {!hide.includes("whale") && <Whale {...HOME.whale} t={t} opacity={opacity} />}
  </>
);

const REF_X = 2950;
const SHORE_X = 4130;

// A rolling ridge as a filled path: two sines, sampled.
const ridge = (seed: string, x0: number, x1: number, lo: number, hi: number, len: number) => {
  const p1 = random(`${seed}a`) * 6, p2 = random(`${seed}b`) * 6;
  let d = `M ${x0} ${GROUND + 3000}`;
  for (let x = x0; x <= x1; x += 60) {
    const h = lo + (hi - lo) * (0.5 + 0.32 * Math.sin(x / len + p1) + 0.18 * Math.sin(x / (len * 0.37) + p2));
    d += ` L ${x} ${(GROUND - h).toFixed(0)}`;
  }
  return `${d} L ${x1} ${GROUND + 3000} Z`;
};
const FAR_HILLS = ridge("far", REF_X - 2600, REF_X + 2600, 90, 300, 420);
const MID_HILLS = ridge("mid", REF_X - 4000, REF_X + 1150, 30, 170, 300);
const STARS = Array.from({ length: 64 }, (_, i) => ({
  x: REF_X + (random(`sx${i}`) - 0.5) * 3300, y: GROUND - 60 - random(`sy${i}`) * 1050, r: 1.6 + random(`sr${i}`) * 2.6, o: 0.07 + random(`so${i}`) * 0.16, ph: random(`sp${i}`) * 6,
}));
const PEBBLES = Array.from({ length: 26 }, (_, i) => ({
  x: -300 + random(`px${i}`) * 4300, y: GROUND + 190 + random(`py${i}`) * 420, w: 24 + random(`pw${i}`) * 50,
}));
const MOTES = Array.from({ length: 9 }, (_, i) => ({ x: REF_X + (random(`mx${i}`) - 0.5) * 4200, y: GROUND - 120 - random(`my${i}`) * 520, r: 10 + random(`mr${i}`) * 16, ph: random(`mp${i}`) * 6 }));

const wave = (t: number, y: number, amp: number, len: number, speed: number, x0: number, x1: number) => {
  let d = `M ${x0} ${y + 6500} L ${x0} ${y}`;
  for (let x = x0; x <= x1; x += 48) d += ` L ${x} ${(y + amp * Math.sin(x / len + t * speed) + amp * 0.4 * Math.sin(x / (len * 0.43) - t * speed * 1.3)).toFixed(1)}`;
  return `${d} L ${x1} ${y + 6500} Z`;
};

// The land surface runs flat to the shore, then slopes away under the sea as the seabed.
const SEABED = `C ${SHORE_X + 100} ${GROUND} ${SHORE_X + 160} ${SEA + 60} ${SHORE_X + 330} ${SEA + 150} C ${SHORE_X + 700} ${SEA + 350} ${SHORE_X + 1100} 2000 ${SHORE_X + 2000} 2300 L 9000 2300`;
const LAND_TOP = `M -5000 ${GROUND} L ${SHORE_X} ${GROUND} ${SEABED}`;
const LAND_D = `${LAND_TOP} L 9000 7500 L -5000 7500 Z`;
const WATER_D = `M ${SHORE_X} ${SEA - 200} L ${SHORE_X} ${GROUND} ${SEABED} L 9000 ${SEA - 200} Z`;

/** The set on the playfield, behind the actors: sea, land, the ant trail, the perch, the owl's tree, the bank. */
const Set: React.FC<{ t: number }> = ({ t }) => {
  const px = P.perch.x, py = P.perch.y, bx = P.branch.x, by = P.branch.y;
  return (
    <Draw>
      <path d={wave(t, SEA, 5, 110, 0.7, SHORE_X, 9000)} fill={C.sea} />
      <path d={LAND_D} fill={C.card} />
      <clipPath id="aipas-land"><path d={LAND_D} /></clipPath>
      <g clipPath="url(#aipas-land)">
        <path d={`M -5000 ${GROUND + 150} Q -2000 ${GROUND + 120} 0 ${GROUND + 160} T 2200 ${GROUND + 150} T ${SHORE_X + 400} ${GROUND + 260} L 9000 ${GROUND + 900} L 9000 7500 L -5000 7500 Z`} fill={C.strata} />
        {PEBBLES.map((p, i) => <rect key={i} x={p.x} y={p.y} width={p.w} height={p.w * 0.36} rx={p.w * 0.18} fill={C.line} opacity={0.35} />)}
      </g>
      <path d={LAND_TOP} fill="none" stroke={C.line} strokeWidth={3} strokeLinecap="round" />

      {/* Ant trail: the anthill and a dotted path to the foot of the perch. */}
      <path d={`M ${P.trail0.x - 120} ${GROUND} Q ${P.trail0.x - 60} ${GROUND - 104} ${P.trail0.x} ${GROUND - 104} Q ${P.trail0.x + 60} ${GROUND - 104} ${P.trail0.x + 120} ${GROUND} Z`} fill="#2b2914" stroke={C.line} strokeWidth={3} />
      <ellipse cx={P.trail0.x} cy={GROUND - 34} rx={26} ry={22} fill={C.deep} />
      {Array.from({ length: 31 }, (_, i) => {
        const x = P.trail0.x + 150 + i * 44;
        return <circle key={i} cx={x} cy={GROUND + 34} r={6.5} fill={C.cream} opacity={0.5 * (1 - ramp(x, P.trail1.x - 220, P.trail1.x + 60, (v) => v))} />;
      })}

      {/* Eagle's perch. */}
      <ellipse cx={px} cy={GROUND + 2} rx={54} ry={12} fill={C.strata} />
      <rect x={px - 10} y={py + 10} width={20} height={GROUND - py - 8} rx={8} fill={C.wood} />
      <rect x={px - 82} y={py} width={164} height={24} rx={12} fill={C.woodLight} />
      <rect x={px - 70} y={py + 4} width={90} height={5} rx={2.5} fill={C.goldDark} opacity={0.6} />

      {/* Owl's tree: crown behind, trunk, the branch it sits on. */}
      {[[bx + 290, by - 430, 190, C.leaf], [bx + 440, by - 340, 140, C.leaf], [bx + 180, by - 510, 130, C.leaf], [bx + 300, by - 470, 120, C.leafLight]].map(([cx, cy, r, c], i) => (
        <circle key={i} cx={cx as number} cy={cy as number} r={(r as number) * (1 + 0.012 * Math.sin(t * 0.5 + i * 1.7))} fill={c as string} />
      ))}
      <path d={`M ${bx + 130} ${GROUND + 4} Q ${bx + 150} ${GROUND - 300} ${bx + 142} ${by - 420} L ${bx + 190} ${by - 420} Q ${bx + 186} ${GROUND - 300} ${bx + 214} ${GROUND + 4} Z`} fill={C.wood} />
      <path d={`M ${bx + 160} ${by + 30} Q ${bx} ${by + 2} ${bx - 190} ${by + 13}`} fill="none" stroke={C.wood} strokeWidth={26} strokeLinecap="round" />
      <path d={`M ${bx + 120} ${by + 15} Q ${bx} ${by - 4} ${bx - 170} ${by + 6}`} fill="none" stroke={C.woodLight} strokeWidth={5} strokeLinecap="round" opacity={0.7} />

      {/* The bank, below the landscape: a dark room, its floor, a desk and a screen. */}
      <rect x={1100} y={2400} width={3900} height={2300} rx={90} fill={C.deep} />
      <rect x={1100} y={DESK_FLOOR} width={3900} height={800} fill="#161507" />
      <line x1={1100} y1={DESK_FLOOR} x2={5000} y2={DESK_FLOOR} stroke={C.line} strokeWidth={3} />
      <g transform={`translate(${P.desk.x} ${DESK_FLOOR})`}>
        <rect x={-150} y={-150} width={22} height={150} rx={8} fill={C.line} />
        <rect x={128} y={-150} width={22} height={150} rx={8} fill={C.line} />
        <rect x={-200} y={-172} width={400} height={26} rx={13} fill="#4a4628" />
        <rect x={-14} y={-216} width={28} height={46} fill={C.line} />
        <rect x={-70} y={-184} width={140} height={14} rx={7} fill={C.line} />
        <rect x={-150} y={-390} width={300} height={186} rx={18} fill={C.card} stroke={C.line} strokeWidth={5} />
        <rect x={-126} y={-366} width={150} height={12} rx={6} fill={C.gold} opacity={0.5 + 0.08 * Math.sin(t * 0.9)} />
        <rect x={-126} y={-336} width={220} height={10} rx={5} fill={C.line} />
        <rect x={-126} y={-312} width={180} height={10} rx={5} fill={C.line} />
      </g>
    </Draw>
  );
};

/** The water in front of whatever is in the sea: actors below the waterline show through it, dimmed. */
const SeaFront: React.FC<{ t: number }> = ({ t }) => (
  <Draw>
    <clipPath id="aipas-water"><path d={WATER_D} /></clipPath>
    <g clipPath="url(#aipas-water)">
      <path d={wave(t, SEA + 20, 6, 130, -0.55, SHORE_X, 9000)} fill={C.seaFront} opacity={0.8} />
      {Array.from({ length: 9 }, (_, i) => {
        const x = SHORE_X + 330 + i * 430 + 40 * Math.sin(t * 0.3 + i * 2.1);
        return <rect key={i} x={x} y={SEA + 62 + (i % 3) * 58} width={120 + (i % 2) * 70} height={7} rx={3.5} fill={C.sky} opacity={0.13} />;
      })}
    </g>
  </Draw>
);

// ---------- Camera ----------

/** World point at the centre of the frame, and zoom. */
export type Cam = { x: number; y: number; z: number };

/** Screen y above which a beat keeps its action: the caption pill sits below. */
export const SAFE_Y = 960;

/** A camera that shows world x0..x1 across the frame with the world y `floor` on screen row `floorAt`. */
export const fit = (x0: number, x1: number, floor = GROUND, floorAt = 830): Cam => {
  const z = 1920 / (x1 - x0);
  return { x: (x0 + x1) / 2, y: floor - (floorAt - 540) / z, z };
};

/** The world rectangle a camera shows. */
export const view = (cam: Cam) => ({
  x0: cam.x - 960 / cam.z, x1: cam.x + 960 / cam.z, y0: cam.y - 540 / cam.z, y1: cam.y + 540 / cam.z, safe: cam.y + (SAFE_Y - 540) / cam.z,
});
export const toScreen = (cam: Cam, p: { x: number; y: number }) => ({ x: 960 + (p.x - cam.x) * cam.z, y: 540 + (p.y - cam.y) * cam.z });

const WIDE = fit(100, 5800, GROUND, 760);
/** Default framing per beat: its home area fills the frame above the captions. */
export const SHOT: Record<number, Cam> = {
  1: fit(3250, 4650),
  2: fit(3350, 5750),
  3: WIDE,
  4: fit(40, 1560),
  5: fit(1200, 2820),
  6: fit(1210, 2810),
  7: fit(2150, 3850),
  8: fit(3600, 6000, GROUND, 800),
  9: WIDE,
  10: fit(1900, 3700, DESK_FLOOR, 850),
  11: fit(1850, 4130, DESK_FLOOR, 850),
  12: WIDE,
  13: WIDE,
  14: fit(3300, 6000),
  15: fit(2970, 4530),
};

export type CamKey = { from: number; to: number; cam: Cam };
/**
 * A keyframed camera: it eases from wherever it is to each key's `cam` between `from` and `to`, then holds it
 * with a slow push of `push` (3%) until the next move starts. Zoom is blended in log space. No hard cuts.
 */
export const camTrack = (keys: CamKey[], push = 0.03) => {
  const held = (i: number, fr: number): Cam => {
    const k = keys[i], next = keys[i + 1]?.from ?? DURATION;
    return { ...k.cam, z: k.cam.z * (1 + push * ramp(fr, k.to, Math.max(k.to + 1, next), (v) => v)) };
  };
  return (fr: number): Cam => {
    let i = 0;
    while (i + 1 < keys.length && fr >= keys[i + 1].from) i++;
    const k = keys[i];
    if (i === 0 || fr >= k.to) return held(i, fr);
    const a = held(i - 1, k.from), u = ramp(fr, k.from, k.to);
    return { x: lerp(a.x, k.cam.x, u), y: lerp(a.y, k.cam.y, u), z: Math.exp(lerp(Math.log(a.z), Math.log(k.cam.z), u)) };
  };
};

/**
 * The one continuous world under a camera. Five depth layers: stars and horizon glow, far hills, near hills,
 * the playfield (set, then `children`, then the sea's front water), and blurred foreground motes. Children are
 * positioned in world coordinates and painted in JSX order.
 */
export const World: React.FC<{ cam: Cam; fr: number; children?: React.ReactNode }> = ({ cam, fr, children }) => {
  const t = fr / FPS;
  // Far layers pan and zoom by a fraction of the camera's move, but stay locked to the ground line.
  const layer = (p: number) => {
    const zp = Math.pow(cam.z, p);
    return `translate(${960 - zp * (REF_X + (cam.x - REF_X) * p)} ${540 + cam.z * (GROUND - cam.y) - zp * GROUND}) scale(${zp})`;
  };
  const full: React.CSSProperties = { position: "absolute", left: 0, top: 0 };
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={full}>
        <defs>
          <radialGradient id="aipas-horizon"><stop offset="0%" stopColor={C.gold} stopOpacity={1} /><stop offset="100%" stopColor={C.gold} stopOpacity={0} /></radialGradient>
        </defs>
        <g transform={layer(0.12)}>
          <ellipse cx={REF_X + 700} cy={GROUND} rx={1500} ry={560} fill="url(#aipas-horizon)" opacity={0.07} />
          {STARS.map((s, i) => <circle key={i} cx={s.x} cy={s.y} r={s.r} fill={C.ink} opacity={s.o * (0.75 + 0.25 * Math.sin(t * 0.6 + s.ph))} />)}
        </g>
        <g transform={layer(0.3)}><path d={FAR_HILLS} fill={C.farHill} /></g>
        <g transform={layer(0.6)}><path d={MID_HILLS} fill={C.midHill} /></g>
      </svg>
      <div style={{ ...full, width: 0, height: 0, transformOrigin: "0 0", transform: `translate(960px, 540px) scale(${cam.z}) translate(${-cam.x}px, ${-cam.y}px)` }}>
        <Set t={t} />
        {children}
        <SeaFront t={t} />
      </div>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ ...full, filter: "blur(5px)" }}>
        <g transform={layer(1.35)}>
          {MOTES.map((m, i) => (
            <circle key={i} cx={m.x + 30 * Math.sin(t * 0.17 + m.ph)} cy={m.y + 22 * Math.sin(t * 0.13 + m.ph * 2)} r={m.r} fill={C.gold} opacity={0.05} />
          ))}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
