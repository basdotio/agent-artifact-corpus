// "Why AI stories feel flat": one continuous paper world, camera pans and 45° wipes, captions on top.
// Beat sheet: OneTake/storage/jobs/ai-flat-story/beats.md. Event times live in kit.ts (T).
import React, { useMemo } from "react";
import { AbsoluteFill, interpolateColors, useCurrentFrame } from "remotion";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { POP, rig, SOFT } from "../../motion";
import { toLines } from "../../Captions";
import { fontFamily, Word } from "../../theme";
import { trailingShift } from "../shared";
import data from "../../../public/illustrated/aiflat/words.json";
import { C, DURATION, f, FPS, inOut, lerp, ramp, T } from "./kit";
import { Flagged, GC, Home1, Home3, hit, nudge, Quieter, Tidy, ZG } from "./stages";

export const aiFlatDuration = DURATION;
export const aiFlatFps = FPS;

const WORDS: Word[] = data.words.map((w) => ({ text: w.text, start: w.start, end: w.end }));

// Stage centres in world coordinates. Q and TI rise on the 45° diagonal from home.
const H = { x: 960, y: 540 };
const Q = { x: 2260, y: -760 };
const TI = { x: 3560, y: -2060 };
const F = { x: 960, y: 4500 };

type Cam = { x: number; y: number; z: number };
const lin = (x: number) => x;

// Framing per stage: centre offset from the stage centre and zoom, chosen so the action fills the frame
// above the captions.
const HOME = { dx: 0, dy: 20, z: 1.2 };
const TIDY = { dx: 40, dy: -70, z: 1.18 };
const FLAG = { dx: 45, dy: -30, z: 1.3 };

// Shot A: home → pan and push into the arc (quieter) → pan to the tidy line.
const camA = (fr: number): Cam => {
  let z = HOME.z * (1 + 0.03 * ramp(fr, 0, f(24.6), lin));
  const u1 = ramp(fr, f(24.62), f(25.8));
  let x = lerp(H.x + HOME.dx, Q.x, u1), y = lerp(H.y + HOME.dy, Q.y, u1);
  z = lerp(z, 1.3, ramp(fr, f(T.closer) - 30, f(26.3)));
  const u2 = ramp(fr, f(34.3), f(35.35));
  x = lerp(x, TI.x + TIDY.dx, u2); y = lerp(y, TI.y + TIDY.dy, u2); z = lerp(z, TIDY.z, u2);
  z *= 1 + 0.025 * ramp(fr, f(35.35), f(42.6), lin);
  return { x, y, z };
};
// Shot B: flagged, then pull back to the grid of 100 writers.
const camB = (fr: number): Cam => {
  const u = ramp(fr, f(50.5), f(51.68));
  const z0 = FLAG.z * (1 + 0.02 * ramp(fr, f(42), f(50.5), lin));
  const z = Math.exp(lerp(Math.log(z0), Math.log(ZG), u)) * (1 + 0.02 * ramp(fr, f(51.68), f(59.9), lin));
  return { x: lerp(F.x + FLAG.dx, F.x + GC.x - 960, u), y: lerp(F.y + FLAG.dy, F.y + GC.y - 540, u), z };
};
// Shot C: back home for the fix, the payoff and the mark.
const camC = (fr: number): Cam => ({
  x: H.x + HOME.dx, y: H.y + HOME.dy, z: HOME.z * (1 + 0.02 * ramp(fr, f(59.3), f(73), lin)) * (1 + 0.04 * ramp(fr, f(73), DURATION, lin)),
});

const W1 = [f(42.0), f(42.6)] as const;
const W2 = [f(59.3), f(59.9)] as const;

// Fast moves get motion blur; everything else renders once.
const BLUR: [number, number][] = [
  [f(T.ai), f(T.ai) + 26],
  [f(24.62), f(25.8)],
  [f(T.quieter) + 4, f(T.quieter) + 66],
  [f(34.3), f(35.35)],
  [f(50.5), f(51.68)],
  [f(T.research) - 20, f(T.research) - 1],
];
const SHUTTER = 180;
const SAMPLES = 6;
const SHIFT = trailingShift(SHUTTER, SAMPLES);

const place = (s: { x: number; y: number }) => `translate(${s.x - 960} ${s.y - 540})`;

const ShotView: React.FC<{ shot: "A" | "B" | "C"; fr: number; uid: string }> = ({ shot, fr, uid }) => {
  const cam = shot === "A" ? camA(fr) : shot === "B" ? camB(fr) : camC(fr);
  const ny = nudge(fr);
  return (
    <g transform={`translate(0 ${ny})`}>
      <g transform={`translate(960 540) scale(${cam.z}) translate(${-cam.x} ${-cam.y})`}>
        {shot === "A" && fr < f(26) && <g transform={place(H)}><Home1 fr={fr} uid={`${uid}a`} /></g>}
        {shot === "A" && fr >= f(24.5) && fr < f(35.5) && <g transform={place(Q)}><Quieter fr={fr} uid={`${uid}q`} /></g>}
        {shot === "A" && fr >= f(34.2) && <g transform={place(TI)}><Tidy fr={fr} uid={`${uid}t`} /></g>}
        {shot === "B" && <g transform={place(F)}><Flagged fr={fr} uid={`${uid}f`} /></g>}
        {shot === "C" && <g transform={place(H)}><Home3 fr={fr} uid={`${uid}c`} /></g>}
      </g>
    </g>
  );
};

/** 45° wipe: the new shot is revealed behind an edge on the rising diagonal, drawn in the brand gradient. */
const Wipe: React.FC<{ from: "A" | "B"; to: "B" | "C"; fr: number; u: number; uid: string }> = ({ from, to, fr, u, uid }) => {
  const c = lerp(-60, 3060, u);
  const tri = `-2000,-2000 ${c + 2000},-2000 -2000,${c + 2000}`;
  const band = `${c + 2000},-2000 -2000,${c + 2000} -2000,${c + 2034} ${c + 2034},-2000`;
  return (
    <>
      <ShotView shot={from} fr={fr} uid={`${uid}o`} />
      <defs>
        <clipPath id={`wp${uid}`}><polygon points={tri} /></clipPath>
        <linearGradient id={`wg${uid}`} gradientUnits="userSpaceOnUse" x1={0} y1={1080} x2={1920} y2={0}>
          <stop offset="0%" stopColor={C.orange} /><stop offset="100%" stopColor={C.teal} />
        </linearGradient>
      </defs>
      <g clipPath={`url(#wp${uid})`}>
        <rect x={0} y={0} width={1920} height={1080} fill={C.paper} />
        <ShotView shot={to} fr={fr} uid={`${uid}n`} />
      </g>
      <polygon points={band} fill={`url(#wg${uid})`} />
    </>
  );
};

/** Everything that moves with the camera. Inside motion blur, useCurrentFrame() is the sample's frame. */
const World: React.FC<{ blurred: boolean }> = ({ blurred }) => {
  const fr = useCurrentFrame() - (blurred ? SHIFT : 0);
  const uid = `${Math.round(fr * 100)}`;
  let body: React.ReactNode;
  if (fr < W1[0]) body = <ShotView shot="A" fr={fr} uid={uid} />;
  else if (fr < W1[1]) body = <Wipe from="A" to="B" fr={fr} u={ramp(fr, W1[0], W1[1], inOut)} uid={uid} />;
  else if (fr < W2[0]) body = <ShotView shot="B" fr={fr} uid={uid} />;
  else if (fr < W2[1]) body = <Wipe from="B" to="C" fr={fr} u={ramp(fr, W2[0], W2[1], inOut)} uid={uid} />;
  else body = <ShotView shot="C" fr={fr} uid={uid} />;
  return (
    <AbsoluteFill>
      {/* No paper fill here: summing 1/N-opacity copies of it under motion blur shifts its colour. */}
      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
        {body}
      </svg>
    </AbsoluteFill>
  );
};

/** Slim caption pill: ink text on paper, the spoken word eased to the text-safe orange. */
const SlimCaptions: React.FC<{ frame: number }> = ({ frame }) => {
  const t = frame / FPS;
  const lines = useMemo(() => toLines(WORDS), []);
  const line = lines.find((l) => t >= l[0].start - 0.05 && t <= l[l.length - 1].end + 0.25);
  if (!line) return null;
  const lineIn = rig(frame - Math.round(line[0].start * FPS), FPS, SOFT).v;
  return (
    <div style={{ position: "absolute", bottom: 34, width: "100%", display: "flex", justifyContent: "center", transform: `translateY(${(1 - lineIn) * 12}px)`, opacity: lineIn }}>
      <div style={{
        fontFamily, fontWeight: 700, fontSize: 30, lineHeight: 1.2, color: C.ink, background: C.card, padding: "7px 22px",
        borderRadius: 999, border: `1.5px solid rgba(27,17,11,0.14)`, boxShadow: "0 4px 14px rgba(27,17,11,0.10)", maxWidth: 1200, textAlign: "center",
      }}>
        {line.map((w, i) => {
          const on = rig(frame - Math.round(w.start * FPS), FPS, POP).v;
          const off = rig(frame - Math.round((w.end + 0.05) * FPS), FPS, SOFT).v;
          const lit = Math.max(0, Math.min(1, on - off));
          return (
            <span key={i} style={{
              display: "inline-block", marginRight: i < line.length - 1 ? 9 : 0,
              color: interpolateColors(lit, [0, 1], [C.ink, C.orangeText]), transform: `scale(${1 + 0.04 * (on - off)})`,
            }}>{w.text}</span>
          );
        })}
      </div>
    </div>
  );
};

export const AiFlat: React.FC = () => {
  const frame = useCurrentFrame();
  const blurred = BLUR.some(([a, b]) => frame >= a && frame <= b);
  const h = hit(frame);
  // Light: dims on "strange", lifts when the detector is shown wrong.
  const dim = 0.13 * ramp(frame, f(T.strange), f(T.strange) + 30) * (1 - ramp(frame, f(T.varied) + 6, f(T.varied) + 46));
  return (
    <AbsoluteFill style={{ background: C.paper, overflow: "hidden" }}>
      <AbsoluteFill style={h > 0.01 ? { filter: `saturate(${1 + 0.45 * h}) brightness(${1 + 0.05 * h})` } : undefined}>
        {blurred ? (
          <CameraMotionBlur shutterAngle={SHUTTER} samples={SAMPLES}>
            <World blurred />
          </CameraMotionBlur>
        ) : (
          <World blurred={false} />
        )}
      </AbsoluteFill>
      {dim > 0.002 && <AbsoluteFill style={{ background: C.ink, opacity: dim }} />}
      <SlimCaptions frame={frame} />
    </AbsoluteFill>
  );
};
