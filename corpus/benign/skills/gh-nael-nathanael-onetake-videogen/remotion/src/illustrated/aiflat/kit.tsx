// Timeline, palette, motion helpers and the shared actors (Nadia, the AI, story shapes) for AiFlat.
import React from "react";
import { Easing, interpolate, interpolateColors, random, SpringConfig } from "remotion";
import { POP, rig } from "../../motion";

export const FPS = 60;
export const DURATION = 4744;
/** Frame of a spoken-word start (s). Every event is forced onto this frame. */
export const f = (s: number) => Math.round(s * FPS);

// Word starts from vo/words-captions.json (s).
export const T = {
  nadia: 0.95, stories: 2.11, ai: 4.33,
  good: 6.55, clean: 7.07, kind: 7.73, flat: 9.35,
  again: 11.61, isntNew: 15.13, eighty: 18.97, ninety: 19.49, human: 21.67, thirty: 23.09,
  nadiaQ: 24.48, closer: 24.86, feelings: 26.16, there: 26.98, quieter: 27.4,
  conflict: 28.46, of: 30.18, eight: 31.52, neutral: 32.24, climb: 33.04, fortyFive: 33.52,
  itself: 36.52, theme: 38.22, subplots: 39.24, bow: 41.5,
  strange: 43.3, writes: [44.2, 44.88, 45.36, 45.8, 46.04, 46.34], detector: 47.54, says: 49.72,
  sixtyOne: 51.74, word: 56.2, aiText: 57.18, varied: 58.28,
  drafts: 61.82, moral: 64.62, open: 66.02, fight: 67.28, people: 68.74, places: 69.36,
  life: 72.04, research: 73.7, url: 75.36,
};

export const C = {
  paper: "#F3EEE2", deep: "#EBE4D2", ink: "#1B110B", orange: "#FB884E", teal: "#4EC6AE",
  orangeText: "#B64900", tealText: "#007B66",
  // Ink tints: same hue as ink, so the palette stays at four hues.
  pale: "#D6CDBB", grey: "#A39A8A", shadow: "#DED5C1", card: "#FBF8F1",
  orangeLight: "#FDB28A", tealLight: "#8ADBCB", inkLight: "#3A2D24",
};

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const arrive = Easing.bezier(0.2, 0, 0, 1);
export const depart = Easing.bezier(0.3, 0, 1, 1);
export const inOut = Easing.bezier(0.65, 0, 0.35, 1);
export const lerp = (a: number, b: number, u: number) => a + (b - a) * u;

/** 0 → 1 between frames a and b (a < b) with an easing. */
export const ramp = (fr: number, a: number, b: number, ease: (x: number) => number = inOut) =>
  interpolate(fr, [a, b], [0, 1], { ...clamp, easing: ease });

/** Spring progress and velocity (per second) starting at frame `start`. */
export const sp = (fr: number, start: number, cfg: Partial<SpringConfig> = POP) => {
  const d = fr - start;
  if (d <= 0) return { v: 0, vel: 0 };
  if (d > 300) return { v: 1, vel: 0 };
  return rig(d, FPS, cfg);
};

/** Inertial bounce after an impulse (Dan Ebberts). */
export const bounce = (fr: number, E: number, v: number, freq = 3, decay = 5) => {
  const t = (fr - E) / FPS;
  if (t < 0) return 0;
  const w = freq * 2 * Math.PI;
  return (v * Math.sin(t * w)) / Math.exp(decay * t) / w;
};
export const decay = (fr: number, E: number, rate: number) => (fr < E ? 0 : Math.exp(-((fr - E) / FPS) * rate));

/** Area-preserving scale pair from a signed velocity: positive stretches along, negative squashes. */
export const stretch = (vel: number, k = 0.025, lo = -0.16, hi = 0.18) => {
  const s = 1 + Math.max(lo, Math.min(hi, vel * k));
  return [s, 1 / s] as const;
};

/** SVG transform: squash along a 2D velocity (px/s), area kept. */
export const along = (vx: number, vy: number, k = 1 / 2400, max = 0.2) => {
  const sp_ = Math.hypot(vx, vy);
  if (sp_ < 1) return "";
  const s = Math.min(max, sp_ * k);
  const dir = (Math.atan2(vy, vx) * 180) / Math.PI;
  return `rotate(${dir}) scale(${1 + s} ${1 / (1 + s)}) rotate(${-dir})`;
};

/** Velocity (px/s) of a 2D path at frame fr, by finite difference. */
export const vel2 = (p: (fr: number) => [number, number], fr: number): [number, number] => {
  const a = p(fr - 0.5), b = p(fr + 0.5);
  return [(b[0] - a[0]) * FPS, (b[1] - a[1]) * FPS];
};

export const mixC = (a: string, b: string, u: number) => interpolateColors(Math.max(0, Math.min(1, u)), [0, 1], [a, b]);

// ---------- Story shapes ----------

export type Kind = "tri" | "circle" | "star" | "zigzag" | "square" | "ring" | "diamond";

const starPts = (r: number, inner: number, n = 5, rot = -90) =>
  Array.from({ length: n * 2 }, (_, i) => {
    const a = ((rot + (i * 180) / n) * Math.PI) / 180;
    const rr = i % 2 ? inner : r;
    return `${(Math.cos(a) * rr).toFixed(1)},${(Math.sin(a) * rr).toFixed(1)}`;
  }).join(" ");

/** A story shape centred on 0,0 with radius r. `gap` opens a ring into a C; `spikes` grows a circle into a spiky burst. */
export const Shape: React.FC<{ kind: Kind; r: number; color: string; gap?: number; spikes?: number; opacity?: number }> = ({
  kind, r, color, gap = 0, spikes = 0, opacity = 1,
}) => {
  if (spikes > 0.001 && kind === "circle") {
    const n = 9;
    const pts = Array.from({ length: n * 2 }, (_, i) => {
      const a = (i * Math.PI) / n - Math.PI / 2;
      const rr = i % 2 ? r * (1 - 0.12 * spikes) : r * (1 + 0.5 * spikes);
      return `${(Math.cos(a) * rr).toFixed(1)},${(Math.sin(a) * rr).toFixed(1)}`;
    }).join(" ");
    return <polygon points={pts} fill={color} stroke={color} strokeWidth={r * 0.12} strokeLinejoin="round" opacity={opacity} />;
  }
  switch (kind) {
    case "tri":
      return <polygon points={`0,${-r} ${r * 0.95},${r * 0.68} ${-r * 0.95},${r * 0.68}`} fill={color} stroke={color} strokeWidth={r * 0.22} strokeLinejoin="round" opacity={opacity} />;
    case "star":
      return <polygon points={starPts(r * 1.1, r * 0.5)} fill={color} stroke={color} strokeWidth={r * 0.12} strokeLinejoin="round" opacity={opacity} />;
    case "zigzag": {
      const w = r * 1.05, h = r * 0.55;
      return <polyline points={`${-w},${h} ${-w / 2},${-h} 0,${h} ${w / 2},${-h} ${w},${h}`} fill="none" stroke={color} strokeWidth={r * 0.32} strokeLinejoin="round" strokeLinecap="round" opacity={opacity} />;
    }
    case "square":
      return <rect x={-r * 0.85} y={-r * 0.85} width={r * 1.7} height={r * 1.7} rx={r * 0.22} fill={color} opacity={opacity} />;
    case "diamond":
      return <rect x={-r * 0.72} y={-r * 0.72} width={r * 1.44} height={r * 1.44} rx={r * 0.18} fill={color} transform="rotate(45)" opacity={opacity} />;
    case "ring": {
      const rr = r * 0.82, sw = r * 0.34;
      if (gap < 0.5) return <circle r={rr} fill="none" stroke={color} strokeWidth={sw} opacity={opacity} />;
      const g = (Math.min(gap, 300) * Math.PI) / 180;
      const a0 = g / 2, a1 = 2 * Math.PI - g / 2;
      const large = a1 - a0 > Math.PI ? 1 : 0;
      return (
        <path d={`M ${rr * Math.cos(a0)} ${rr * Math.sin(a0)} A ${rr} ${rr} 0 ${large} 1 ${rr * Math.cos(a1)} ${rr * Math.sin(a1)}`}
          fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" opacity={opacity} />
      );
    }
    default:
      return <circle r={r} fill={color} opacity={opacity} />;
  }
};

/** Nadia's five story shapes: messy, mixed colours. */
export const STORY: { kind: Kind; color: string; r: number; rot: number }[] = [
  { kind: "tri", color: C.orange, r: 30, rot: -12 },
  { kind: "circle", color: C.teal, r: 26, rot: 0 },
  { kind: "star", color: C.orange, r: 30, rot: 10 },
  { kind: "zigzag", color: C.ink, r: 30, rot: -18 },
  { kind: "square", color: C.teal, r: 25, rot: 14 },
];

// ---------- Orbit around Nadia ----------

/** Position on Nadia's orbit for shape i: a tilted ellipse, back half drawn behind her. */
export const orbit = (i: number, fr: number, cx: number, cy: number, grow = 1) => {
  const t = fr / FPS;
  const a = (i / 5) * Math.PI * 2 + 0.6 + t * ((2 * Math.PI) / 15) * (0.9 + 0.2 * random(`orb${i}`));
  // Wide and flat, so the front pass crosses her body below the face.
  const rx = (180 + 30 * random(`orx${i}`)) * grow, ry = (62 + 12 * random(`ory${i}`)) * grow;
  const bob = 7 * Math.sin(t * (1.1 + 0.5 * random(`ob${i}`)) + i * 2);
  return { x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry + bob, back: Math.sin(a) < 0, depth: Math.sin(a) };
};

// ---------- Nadia ----------

// Irregular blinks: gaps of 2.1–4.9 s, seeded, so they never fall into a rhythm.
const BLINKS = (() => {
  const out: number[] = [];
  let t = 1.8;
  for (let i = 0; t < 90; i++) {
    out.push(t);
    t += 2.1 + 2.8 * random(`blink${i}`);
  }
  return out;
})();
const blinkAt = (t: number, seed: number) => {
  const tt = t + seed * 1.37;
  for (const b of BLINKS) {
    const d = tt - b;
    if (d >= 0 && d < 0.16) return Math.sin((d / 0.16) * Math.PI);
    if (b > tt) break;
  }
  return 0;
};

// Irregular eye saccades: small jumps every 0.9–2.5 s, seeded per character.
const SACCADES = new Map<number, number[]>();
const saccade = (t: number, seed: number): [number, number] => {
  let a = SACCADES.get(seed);
  if (!a) {
    a = [];
    let tt = 0.6;
    for (let i = 0; tt < 90; i++) {
      a.push(tt, (random(`sx${seed}${i}`) - 0.5) * 5, (random(`sy${seed}${i}`) - 0.5) * 3);
      tt += 0.9 + 1.6 * random(`st${seed}${i}`);
    }
    SACCADES.set(seed, a);
  }
  let j = -3;
  while (j + 3 < a.length && a[j + 3] <= t) j += 3;
  if (j < 0) return [0, 0];
  const px = j >= 3 ? a[j - 2] : 0, py = j >= 3 ? a[j - 1] : 0;
  const u = Easing.out(Easing.quad)(Math.min(1, (t - a[j]) / 0.07));
  return [lerp(px, a[j + 1], u), lerp(py, a[j + 2], u)];
};

// ---------- Lighting ----------

type Tone = { base: string; shade: string; rim: string };
const mixTone = (a: Tone, b: Tone, u: number): Tone =>
  u <= 0.001 ? a : { base: mixC(a.base, b.base, u), shade: mixC(a.shade, b.shade, u), rim: mixC(a.rim, b.rim, u) };
const SKIN: Tone = { base: "#B9603A", shade: "#9A472C", rim: "#CF7A4E" };
const HAIR: Tone = { base: "#17110F", shade: "#080605", rim: "#33271F" };
const SWEATER: Tone = { base: C.orange, shade: "#D9652F", rim: "#FDA273" };
const TROUSERS: Tone = { base: C.teal, shade: "#2F9E88", rim: "#78D5C2" };
const SHOE: Tone = { base: "#482A1F", shade: "#2B1811", rim: "#7C5242" };
const EYE: Tone = { base: "#FFFDF8", shade: "#E4D9C9", rim: "#FFFFFF" };
const BOT: Tone = { base: "#22170F", shade: "#0B0705", rim: "#665040" };
const SCREEN: Tone = { base: "#FDF6E3", shade: "#EBD9B2", rim: "#FFFFFF" };
const ALARM: Tone = { base: "#EA753A", shade: "#BF511E", rim: "#FFB58C" };
const ALARM_BODY: Tone = { base: "#F98346", shade: "#CF5E28", rim: "#FFC4A2" };

const circ = (cx: number, cy: number, r: number) => `M ${cx - r} ${cy} A ${r} ${r} 0 1 0 ${cx + r} ${cy} A ${r} ${r} 0 1 0 ${cx - r} ${cy} Z`;
const ell = (cx: number, cy: number, rx: number, ry: number) => `M ${cx - rx} ${cy} A ${rx} ${ry} 0 1 0 ${cx + rx} ${cy} A ${rx} ${ry} 0 1 0 ${cx - rx} ${cy} Z`;
const rrect = (x: number, y: number, w: number, h: number, r: number) =>
  `M ${x + r} ${y} H ${x + w - r} A ${r} ${r} 0 0 1 ${x + w} ${y + r} V ${y + h - r} A ${r} ${r} 0 0 1 ${x + w - r} ${y + h} H ${x + r} A ${r} ${r} 0 0 1 ${x} ${y + h - r} V ${y + r} A ${r} ${r} 0 0 1 ${x + r} ${y} Z`;

/**
 * A lit form: base fill, a darker crescent lower-right, a thin rim light upper-left (both clipped to the
 * outline), and an optional highlight arc. It lives inside the part's transform, so it follows every squash.
 */
const Lit: React.FC<{ d: string; tone: Tone; s?: number; rim?: number; hi?: string; hiW?: number; flat?: boolean }> = ({
  d, tone, s = 6, rim = 2.5, hi, hiW = 5, flat,
}) => {
  const id = "l" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
  if (flat) return <path d={d} fill={tone.base} />;
  return (
    <g>
      <clipPath id={id}><path d={d} /></clipPath>
      <path d={d} fill={tone.shade} />
      <g clipPath={`url(#${id})`}>
        <path d={d} fill={tone.base} transform={`translate(${-s} ${-s * 0.9})`} />
        <path d={d} fill="none" stroke={tone.rim} strokeWidth={rim * 2} transform={`translate(${rim * 1.3} ${rim * 1.3})`} />
      </g>
      {hi && <path d={hi} fill="none" stroke={tone.rim} strokeWidth={hiW} strokeLinecap="round" opacity={0.6} />}
    </g>
  );
};

// ---------- Nadia ----------

export type NadiaPose = {
  x: number; y: number; // feet on the floor
  sy?: number; // squash: x scale is 1/sy, so area holds
  tilt?: number; lean?: number; look?: number; lookY?: number; headDY?: number; k?: number;
  /** Arm raise in degrees: 0 hangs at the side, 90 points straight out, 160 is up. */
  armL?: number; armR?: number;
  /** Expression weights 0..1; the remainder is her neutral, curious face. */
  happy?: number; puzzled?: number; shock?: number;
};

const HEAD_Y = -244;
const BACK_HAIR = "M -76 -200 C -86 -300 -50 -330 0 -330 C 50 -330 86 -300 76 -200 C 74 -186 54 -184 46 -196 L -46 -196 C -54 -184 -74 -186 -76 -200 Z";
const FRONT_HAIR = "M -76 -204 C -86 -302 -50 -330 0 -330 C 50 -330 86 -302 76 -204 C 72 -194 62 -194 58 -204 C 60 -236 58 -262 48 -278 C 32 -288 14 -284 2 -292 C -12 -284 -34 -290 -50 -278 C -60 -262 -60 -236 -58 -204 C -62 -194 -72 -194 -76 -204 Z";
const SWEATER_D = "M -52 -98 C -66 -128 -66 -176 -42 -192 C -22 -201 22 -201 42 -192 C 66 -176 66 -128 52 -98 C 30 -90 -30 -90 -52 -98 Z";
const TROUSERS_D = "M -50 -106 L 50 -106 C 52 -80 50 -40 46 -12 L 8 -12 C 6 -40 4 -60 0 -66 C -4 -60 -6 -40 -8 -12 L -46 -12 C -50 -40 -52 -80 -50 -106 Z";
const ARM_D = rrect(-15, -13, 30, 76, 15);

const num = (v: number | undefined, d: number) => (v === undefined ? d : v);

/**
 * Nadia: brown skin, black bob with a fringe, orange sweater, teal trousers. Feet at the origin.
 * Pass `at` (pose as a function of frame) to get follow-through: hair, arms and head trail the body by 4–6 frames.
 * Idle is irregular: incommensurate breaths, drifting tilt, uneven blinks and eye saccades.
 */
export const Nadia: React.FC<NadiaPose & { fr: number; seed?: number; opacity?: number; shadow?: boolean; simple?: boolean; at?: (fr: number) => NadiaPose }> = (props) => {
  const { fr, seed = 0, opacity = 1, shadow = true, simple = false, at } = props;
  const P = at ? at(fr) : props;
  const L = at ? at(fr - 5) : P;
  const t = fr / FPS;
  const k = num(P.k, 1), lean = num(P.lean, 0), tilt = num(P.tilt, 0), headDY = num(P.headDY, 0);
  const happy = num(P.happy, 0), puzzled = num(P.puzzled, 0), shock = num(P.shock, 0);
  const idleTilt = (q: number) => 2.2 * Math.sin((2 * Math.PI * q) / 4.1 + 0.4 + seed) + 1.3 * Math.sin((2 * Math.PI * q) / 2.3 + 2.1 + seed);
  const breath = 1 + 0.013 * Math.sin((2 * Math.PI * t) / 3.3 + seed) + 0.006 * Math.sin((2 * Math.PI * t) / 1.7 + 1.3 + seed * 2);
  const s = num(P.sy, 1) * breath;
  const blink = happy > 0.6 ? 0 : blinkAt(t, seed);
  const [sx, sy2] = saccade(t, seed);
  const look = Math.max(-8, Math.min(8, num(P.look, 0) * 0.9 + sx));
  const lookY = Math.max(-6, Math.min(6, num(P.lookY, 0) + sy2 - 2 * puzzled));

  // Follow-through from the lagged pose: hair swings, arms drag.
  const headAt = (p: NadiaPose) => [p.x + Math.sin((num(p.lean, 0) * Math.PI) / 180) * 250 * num(p.k, 1), p.y - 250 * num(p.k, 1) * num(p.sy, 1) + num(p.headDY, 0)];
  const [hx0, hy0] = headAt(P), [hx1, hy1] = headAt(L);
  const cl = (v: number, m: number) => Math.max(-m, Math.min(m, v));
  const hairDX = cl((hx1 - hx0) * 0.45, 14), hairDY = cl((hy1 - hy0) * 0.45, 12);
  const hairRot = cl((num(L.tilt, 0) - tilt) * 0.6 + (idleTilt(t - 0.12) - idleTilt(t)) * 0.8, 10) + hairDX * 0.35;
  const drag = Math.max(-8, Math.min(22, (P.y - L.y) * 0.4));
  const armL = num(L.armL, 0) + drag + 3 * Math.sin(t * 1.9 + seed);
  const armR = num(L.armR, 0) + drag + 3 * Math.sin(t * 1.6 + seed + 1);

  const arm = (side: -1 | 1, a: number) => (
    <g transform={`translate(${48 * side} -180) rotate(${side * -(a + 8)})`}>
      <Lit d={ARM_D} tone={SWEATER} s={4} rim={2} flat={simple} />
      <Lit d={circ(0, 70, 14)} tone={SKIN} s={3} rim={1.6} flat={simple} />
      <circle cx={-9 * side} cy={63} r={6} fill={SKIN.base} />
    </g>
  );

  const eye = (side: -1 | 1) => {
    const ex = 25 * side, ey = HEAD_Y;
    const es = 1 + 0.2 * shock;
    const open = (1 - 0.95 * blink) * (1 - 0.9 * happy);
    const browDY = -7 * shock - 3 * happy + puzzled * (side < 0 ? -7 : 3);
    const browRot = puzzled * (side < 0 ? -12 : 14) * side;
    return (
      <g key={side}>
        {open > 0.05 && (
          <g transform={`translate(${ex} ${ey}) scale(${es} ${es * open})`}>
            <Lit d={ell(0, 0, 15, 18)} tone={EYE} s={3} rim={0} flat={simple} />
            <circle cx={look} cy={lookY} r={8.5 - 2 * shock} fill="#251712" />
            {!simple && <circle cx={look - 3} cy={lookY - 3.5} r={2.6} fill="#ffffff" />}
          </g>
        )}
        {blink > 0.6 && happy < 0.5 && <path d={`M ${ex - 13} ${ey + 1} Q ${ex} ${ey + 7} ${ex + 13} ${ey + 1}`} stroke="#2A1A12" strokeWidth={3.5} strokeLinecap="round" fill="none" />}
        {happy > 0.01 && <path d={`M ${ex - 12} ${ey + 4} Q ${ex} ${ey - 10} ${ex + 12} ${ey + 4}`} stroke="#2A1A12" strokeWidth={4.5} strokeLinecap="round" fill="none" opacity={happy} />}
        {!simple && (
          <path d={`M ${ex - 9} ${-268} Q ${ex} ${-273} ${ex + 9} ${-269}`} stroke={HAIR.base} strokeWidth={4} strokeLinecap="round" fill="none"
            transform={`translate(0 ${browDY}) rotate(${browRot} ${ex} -270)`} />
        )}
      </g>
    );
  };

  const wN = Math.max(0, 1 - happy - shock - puzzled);
  const mouth = "#6E2C18";
  const hair = `translate(${hairDX} ${hairDY}) rotate(${hairRot} 0 ${HEAD_Y})`;

  return (
    <g opacity={opacity}>
      {shadow && <ellipse cx={P.x} cy={P.y + 2} rx={(70 * k) / Math.sqrt(s)} ry={10 * k} fill={C.shadow} />}
      <g transform={`translate(${P.x} ${P.y}) rotate(${lean}) scale(${k / s} ${k * s})`}>
        <Lit d={ell(-26, -9, 24, 10)} tone={SHOE} s={3} rim={1.5} flat={simple} />
        <Lit d={ell(26, -9, 24, 10)} tone={SHOE} s={3} rim={1.5} flat={simple} />
        <Lit d={TROUSERS_D} tone={TROUSERS} s={7} hi="M -38 -90 L -38 -40" hiW={4} flat={simple} />
        <rect x={-13} y={-206} width={26} height={22} fill={SKIN.shade} />
        <Lit d={SWEATER_D} tone={SWEATER} s={9} hi="M -46 -164 Q -50 -182 -32 -191" flat={simple} />
        {!simple && <path d="M -18 -196 Q 0 -186 18 -196" stroke={SWEATER.shade} strokeWidth={5} strokeLinecap="round" fill="none" />}
        {!simple && <path d="M -50 -104 Q 0 -92 50 -104" stroke={SWEATER.shade} strokeWidth={5} strokeLinecap="round" fill="none" />}
        <g transform={`translate(0 ${headDY}) rotate(${tilt + idleTilt(t)} 0 -196)`}>
          <g transform={hair}><Lit d={BACK_HAIR} tone={HAIR} s={6} rim={0} flat={simple} /></g>
          <Lit d={circ(-61, -236, 12)} tone={SKIN} s={3} rim={1.5} flat={simple} />
          <Lit d={circ(61, -236, 12)} tone={SKIN} s={3} rim={1.5} flat={simple} />
          <Lit d={circ(0, HEAD_Y, 62)} tone={SKIN} s={8} rim={2.5} flat={simple} />
          {!simple && [-1, 1].map((sd) => <ellipse key={sd} cx={40 * sd} cy={-221} rx={10} ry={6} fill="#C9603A" opacity={0.45 + 0.35 * happy} />)}
          {eye(-1)}
          {eye(1)}
          {!simple && (
            <g>
              {wN > 0.01 && <path d="M -9 -214 Q 0 -206 9 -214" stroke={mouth} strokeWidth={3.5} strokeLinecap="round" fill="none" opacity={wN} />}
              {happy > 0.01 && <path d="M -15 -217 Q 0 -197 15 -217 Q 0 -211 -15 -217 Z" fill={mouth} stroke={mouth} strokeWidth={2} strokeLinejoin="round" opacity={happy} />}
              {puzzled > 0.01 && <path d="M -9 -211 Q -3 -215 2 -211 Q 7 -207 11 -212" stroke={mouth} strokeWidth={3.5} strokeLinecap="round" fill="none" opacity={puzzled} />}
              {shock > 0.01 && (
                <g opacity={Math.min(1, shock * 1.5)}>
                  <ellipse cx={0} cy={-209} rx={7 + 2 * shock} ry={9 + 3 * shock} fill="#5A1E12" />
                  <ellipse cx={0} cy={-203 + 2 * shock} rx={5} ry={3} fill="#E0796A" />
                </g>
              )}
            </g>
          )}
          <g transform={hair}><Lit d={FRONT_HAIR} tone={HAIR} s={5} rim={1.8} hi="M -52 -300 Q -34 -320 -6 -322" hiW={6} flat={simple} /></g>
        </g>
        {arm(-1, armL)}
        {arm(1, armR)}
      </g>
    </g>
  );
};

// ---------- The AI ----------

/** The brand "rising line" path in a 256 box. Only for the closing mark, never for the AI. */
export const MARK = "M255 0 L255 255 L213 255 L213 110 L68 255 L0 255 Z";

/**
 * The AI's screen face, centred on cx, cy with radius r: the one place to change how the AI looks.
 * Flat and even on purpose: dot eyes, a straight mouth, a metronomic blink every 3 s (Nadia's are uneven).
 * `alarm` (0..1, eased by the caller) opens the eyes into rings and eases the mouth into a wave.
 */
export const AiFace: React.FC<{ fr: number; cx: number; cy: number; r: number; color: string; alarm?: number }> = ({
  fr, cx, cy, r, color, alarm = 0,
}) => {
  const ph = (((fr / FPS) % 3) + 3) % 3;
  const blink = alarm > 0.5 ? 0 : ph < 0.16 ? Math.sin((ph / 0.16) * Math.PI) : 0;
  const er = r * 0.17 * (1 + 0.6 * alarm);
  const ey = cy - r * 0.22 - r * 0.06 * alarm;
  const my = cy + r * 0.42, mx = r * 0.48, amp = r * 0.14 * alarm;
  let mouth = `M ${cx - mx} ${my}`;
  for (let i = 1; i <= 6; i++) mouth += ` Q ${cx - mx + ((i - 0.5) * 2 * mx) / 6} ${my + (i % 2 ? -amp : amp) * 2} ${cx - mx + (i * 2 * mx) / 6} ${my}`;
  return (
    <g>
      {[-1, 1].map((s) => (
        <ellipse key={s} cx={cx + s * r * 0.46} cy={ey} rx={er} ry={er * (1 - 0.9 * blink)}
          fill={color} fillOpacity={1 - alarm} stroke={color} strokeOpacity={alarm} strokeWidth={r * 0.1} />
      ))}
      <path d={mouth} stroke={color} strokeWidth={r * 0.13} strokeLinecap="round" fill="none" />
    </g>
  );
};

export type AiPose = {
  x: number; y: number; sy?: number; k?: number; lean?: number;
  /** 0..1: the left hand reaches out toward Nadia. */
  reach?: number;
  /** 0..1: the screen (and hands) turn orange. */
  alarm?: number;
};

/**
 * The AI: an ink monitor floating over a soft teal glow, the brand mark on its cream screen, two floating hands
 * that trail on a 6-frame lag. Idle is a perfectly even bob, period 2 s, so it reads slightly too neat.
 */
export const AiBot: React.FC<AiPose & { fr: number; idleFrom?: number; opacity?: number; at?: (fr: number) => AiPose; simple?: boolean }> = (props) => {
  const { fr, idleFrom = 0, opacity = 1, at, simple = false } = props;
  const P = at ? at(fr) : props;
  const L = at ? at(fr - 6) : P;
  const gid = "g" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
  const bobAt = (q: number) => {
    const t = (q - idleFrom) / FPS;
    return t > 0 ? -8 * Math.sin((2 * Math.PI * t) / 2) * Math.min(1, t / 0.5) : 0;
  };
  const k = num(P.k, 1), sy = num(P.sy, 1), alarm = num(P.alarm, 0), lean = num(P.lean, 0);
  const bob = bobAt(fr);
  const screen = mixTone(SCREEN, ALARM, alarm);
  const hands = mixTone(BOT, ALARM_BODY, alarm);
  const reach = num(L.reach, 0);
  return (
    <g opacity={opacity}>
      {!simple && (
        <>
          <defs>
            <radialGradient id={gid}><stop offset="0%" stopColor={C.teal} stopOpacity={0.55} /><stop offset="100%" stopColor={C.teal} stopOpacity={0} /></radialGradient>
          </defs>
          <ellipse cx={P.x} cy={P.y - 2} rx={130 * k} ry={26 * k} fill={`url(#${gid})`} opacity={0.85 + bob * 0.02} />
        </>
      )}
      <ellipse cx={P.x} cy={P.y + 2} rx={66 * k * (1 + bob / 90)} ry={8 * k} fill={C.shadow} opacity={0.9} />
      <g transform={`translate(${P.x} ${P.y + bob * k}) rotate(${lean}) scale(${k / sy} ${k * sy})`}>
        <Lit d={ell(0, -54, 34, 14)} tone={BOT} s={4} rim={1.5} flat={simple} />
        <Lit d={rrect(-96, -228, 192, 178, 50)} tone={BOT} s={9} rim={2.2} hi="M -74 -190 Q -78 -212 -56 -219" hiW={5} flat={simple} />
        <path d={rrect(-75, -210, 150, 126, 28)} fill="#070403" />
        {!simple && <path d={rrect(-75, -210, 150, 126, 28)} fill="none" stroke={screen.base} strokeOpacity={0.22} strokeWidth={7} />}
        <Lit d={rrect(-70, -205, 140, 116, 24)} tone={screen} s={7} rim={2} flat={simple} />
        <AiFace fr={fr} cx={0} cy={-147} r={40} color={mixC(C.ink, "#FFF4E2", alarm)} alarm={alarm} />
      </g>
      {([-1, 1] as const).map((side) => {
        const hx = L.x + (side * 128 - (side < 0 ? 72 * reach : 0)) * k;
        const hy = L.y + (-86 + bobAt(fr - 12) - (side < 0 ? 46 * reach : 0)) * k;
        // While reaching, a short sagging arm links the hand to the body so it doesn't read as a loose ball.
        const sx0 = P.x - (90 * k) / sy, sy0 = P.y + bob * k - 118 * k * sy;
        const arm = side < 0 && reach > 0.03 && !simple && (
          <path d={`M ${sx0} ${sy0} Q ${(sx0 + hx) / 2} ${(sy0 + hy) / 2 + 26 * k} ${hx} ${hy}`}
            stroke={hands.base} strokeWidth={11 * k} strokeLinecap="round" fill="none" opacity={Math.min(1, reach * 3)} />
        );
        return (
          <g key={side}>
            {arm}
            <g transform={`translate(${hx} ${hy}) scale(${k})`}>
              {!simple && <Lit d={circ(-15 * side, -10, 9)} tone={hands} s={2} rim={1.2} />}
              <Lit d={circ(0, 0, 23)} tone={hands} s={4} rim={1.5} hi="M -14 -8 Q -12 -16 -4 -18" hiW={3.5} flat={simple} />
            </g>
          </g>
        );
      })}
    </g>
  );
};

// ---------- Juice ----------

/** Bits that fly out from a point, decelerate, then linger and drift. */
export const Burst: React.FC<{ fr: number; E: number; seed: string; n: number; x: number; y: number; speed?: [number, number]; size?: [number, number]; colors: string[]; life?: number }> = ({
  fr, E, seed, n, x, y, speed = [220, 480], size = [7, 14], colors, life = 1.6,
}) => {
  const tau = (fr - E) / FPS;
  if (tau < 0 || tau > life) return null;
  return (
    <g>
      {Array.from({ length: n }, (_, i) => {
        const r = (k: string) => random(`${seed}${k}${i}`);
        const a = (i / n) * Math.PI * 2 + r("a") * 0.6;
        const v = speed[0] + r("v") * (speed[1] - speed[0]);
        const travel = (v * (1 - Math.exp(-4 * tau))) / 4;
        const px = x + Math.cos(a) * travel + 8 * Math.sin(tau * 0.9 + i);
        const py = y + Math.sin(a) * travel - 16 * tau;
        const s = (size[0] + r("s") * (size[1] - size[0])) * interpolate(tau, [0, 0.1, life], [0.3, 1, 0.5], clamp);
        const o = interpolate(tau, [0, 0.04, 0.5, life], [0, 1, 0.85, 0], clamp);
        const c = colors[i % colors.length];
        return i % 3 === 2
          ? <rect key={i} x={px - s / 2} y={py - s / 2} width={s} height={s} rx={s * 0.2} fill={c} opacity={o} transform={`rotate(${r("r") * 90 + tau * 60} ${px} ${py})`} />
          : <circle key={i} cx={px} cy={py} r={s / 2} fill={c} opacity={o} />;
      })}
    </g>
  );
};

/** Soft white flash at a point, for payoff frames. Driven by the frame's own time. */
export const Flash: React.FC<{ fr: number; E: number; x: number; y: number; r: number; amp?: number; id: string }> = ({ fr, E, x, y, r, amp = 0.7, id }) => {
  const o = decay(fr, E, 8) * amp;
  if (o < 0.01) return null;
  return (
    <g>
      <defs>
        <radialGradient id={id}><stop offset="0%" stopColor="#ffffff" stopOpacity={1} /><stop offset="100%" stopColor="#ffffff" stopOpacity={0} /></radialGradient>
      </defs>
      <circle cx={x} cy={y} r={r * (1 + 0.3 * (1 - o / amp))} fill={`url(#${id})`} opacity={o} />
    </g>
  );
};

/** Scissors centred on a cut point: blades open, wind wider, hold, snap shut at E, then leave. */
export const Scissors: React.FC<{ fr: number; E: number; x: number; y: number; rot?: number }> = ({ fr, E, x, y, rot = 0 }) => {
  const appear = sp(fr, E - 26);
  const leave = ramp(fr, E + 16, E + 30, depart);
  if (appear.v <= 0.001 || leave >= 1) return null;
  // Opens wider (wind-up), holds 4 frames, snaps shut over the 3 frames before E: the cut lands on E.
  const ang = (26 + 14 * ramp(fr, E - 20, E - 7)) * (1 - ramp(fr, E - 3, E, Easing.in(Easing.quad)));
  const k = appear.v * (1 - leave);
  const blade = (s: number) => (
    <g transform={`rotate(${(s * ang) / 2})`}>
      <path d="M 0 0 L 92 -7 Q 100 0 92 7 Z" fill={C.ink} />
      <circle cx={-34} cy={0} r={16} fill="none" stroke={C.ink} strokeWidth={8} />
      <line x1={-20} y1={0} x2={0} y2={0} stroke={C.ink} strokeWidth={8} />
    </g>
  );
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${1.4 * k}) translate(-62 0)`} opacity={1 - leave}>
      {blade(1)}
      {blade(-1)}
      <circle r={6} fill={C.paper} />
    </g>
  );
};
