// The stages of the AiFlat world. Each is authored in its own 1920×1080 frame (as seen by the camera at
// zoom 1) and placed in the world by AiFlat.tsx. `fr` is the (possibly fractional) frame; `uid` keeps SVG ids
// unique per motion-blur sample.
import React from "react";
import { Easing, random } from "remotion";
import { fontFamily } from "../../theme";
import { loadFont } from "@remotion/google-fonts/JetBrainsMono";
import { POP, SOFT } from "../../motion";
import {
  AiBot, AiFace, along, bounce, Burst, C, clamp, decay, depart, f, Flash, FPS, inOut, Kind, lerp, MARK, mixC, Nadia, orbit,
  ramp, Scissors, Shape, sp, STORY, stretch, T, vel2,
} from "./kit";
import { interpolate } from "remotion";

const { fontFamily: mono } = loadFont("normal", { weights: ["500", "700"], subsets: ["latin"] });

type P = { fr: number; uid: string };
const FLOOR = 800;
const NX = 440;
const AX = 1480;
const ORBIT_Y = FLOOR - 110; // her waist: the orbit's back pass stays behind her body, clear of her head
const AI_SCREEN: [number, number] = [AX, FLOOR - 150];
/** Spring weight that rises at `on` and settles back after `off`. */
const hold = (fr: number, on: number, off: number) => sp(fr, on).v * (1 - sp(fr, off, SOFT).v);
const u01 = (v: number) => Math.max(0, Math.min(1, v));

const Ground: React.FC = () => (
  <rect x={-520} y={FLOOR} width={2960} height={760} rx={90} fill={C.deep} />
);

/** Orbiting story shapes around Nadia, split into the layer behind her and the layer in front. */
type Orb = { key: string; x: number; y: number; back: boolean; depth: number; node: React.ReactNode; xf: string };
const drawOrbs = (orbs: Orb[], back: boolean) =>
  orbs.filter((o) => o.back === back).sort((a, b) => a.depth - b.depth).map((o) => (
    <g key={o.key} transform={`translate(${o.x} ${o.y}) ${o.xf}`} opacity={o.back ? 0.88 : 1}>{o.node}</g>
  ));

// ======================= Beats 1–3: home =======================

const ROW1_Y = 380;
const ROW2_Y = 500;
const SLOTS = [720, 840, 960, 1080, 1200];
const VENN = { x: 960, y: 400, r: 170 };

/** Overlap of two equal circles as a fraction of one circle's area. */
const lensFrac = (d: number, r: number) => {
  if (d >= 2 * r) return 0;
  const a = 2 * r * r * Math.acos(d / (2 * r)) - (d / 2) * Math.sqrt(4 * r * r - d * d);
  return a / (Math.PI * r * r);
};
const dFor = (frac: number, r: number) => {
  let lo = 0, hi = 2 * r;
  for (let i = 0; i < 40; i++) {
    const m = (lo + hi) / 2;
    if (lensFrac(m, r) > frac) lo = m; else hi = m;
  }
  return (lo + hi) / 2;
};
const D40 = dFor(0.4, VENN.r), D80 = dFor(0.8, VENN.r), D85 = dFor(0.85, VENN.r);

export const Home1: React.FC<P> = ({ fr, uid }) => {
  const t = fr / FPS;
  // Beat 1: Nadia springs up through the floor line.
  const nE = f(T.nadia);
  const riseY = (q: number) => 420 * (1 - sp(q, nE).v);
  const rise = sp(fr, nE);
  const bump = 18 * ramp(fr, nE - 22, nE - 4) * (1 - ramp(fr, nE, nE + 5));
  const flatE = f(T.flat);
  const vE0 = f(T.isntNew);
  // Her whole performance as a function of frame, so hair and arms can trail it.
  const nadiaAt = (q: number) => {
    const r = sp(q, nE);
    const venn = hold(q, vE0, f(T.human));
    const shocked = hold(q, f(T.ninety), f(T.human));
    return {
      x: NX, y: FLOOR + riseY(q), sy: stretch(r.vel, 0.03)[0], headDY: (riseY(q - 5) - riseY(q)) * 0.3,
      armL: 120 * hold(q, f(T.stories), f(2.9)) + 30 * hold(q, flatE + 10, f(11.3)),
      armR: 140 * hold(q, f(T.stories) + 3, f(2.9)) + 30 * hold(q, flatE + 12, f(11.3)),
      tilt: 13 * hold(q, flatE + 8, f(11.3)) + 9 * hold(q, f(T.eighty), f(T.human)) - 6 * shocked,
      puzzled: Math.min(1, hold(q, flatE + 6, f(11.3)) + 0.6 * venn + 0.4 * hold(q, f(T.eighty), f(T.ninety))) * (1 - shocked),
      shock: 0.8 * shocked,
      happy: 0.6 * hold(q, f(T.thirty), f(24.3)),
      look: 6 * ramp(q, f(T.ai), f(T.ai) + 14), lookY: -4 * venn,
      lean: 6 * venn + 7 * sp(q, f(T.nadiaQ)).v,
    };
  };

  // Story shapes pop out of her head one by one, then orbit.
  const sE = f(T.stories);
  const orbs: Orb[] = STORY.map((s, i) => {
    const start = sE + 5 * i;
    const pos = (q: number): [number, number] => {
      const p = sp(q, start).v;
      const o = orbit(i, q, NX, ORBIT_Y);
      return [lerp(NX, o.x, p), lerp(ORBIT_Y + 10, o.y, p) - 90 * Math.sin(Math.PI * u01(p))];
    };
    const p = sp(fr, start).v;
    const [x, y] = pos(fr);
    const [vx, vy] = vel2(pos, fr);
    const o = orbit(i, fr, NX, ORBIT_Y);
    const back = p > 0.6 && o.back;
    return {
      key: `s${i}`, x, y, back, depth: o.depth,
      xf: `${along(vx, vy)} scale(${Math.max(0, p) * (back ? 0.84 : 1)}) rotate(${s.rot + 8 * Math.sin(t * 0.7 + i)})`,
      node: p > 0.001 ? <Shape kind={s.kind} r={s.r} color={s.color} /> : null,
    };
  });

  // The AI slides in on a 45° path and lands with a neat click.
  const aE = f(T.ai);
  // AI reacts to each emission with a tiny, even dip.
  const emits = [f(T.good), f(T.good) + 5, f(T.clean), f(T.clean) + 5, f(T.kind)];
  const emits2 = SLOTS.map((_, j) => f(T.again) + 4 * j);
  const aiIdle = aE + 26;
  const aiAt = (q: number) => {
    const b = 1 - ramp(q, aE, aE + 24, Easing.bezier(0.2, 0, 0, 1));
    return {
      x: AX + 540 * b, y: FLOOR - 540 * b,
      sy: 1 - bounce(q, aE + 22, 1.6, 6, 14) - [...emits, ...emits2].reduce((a, e) => a + bounce(q, e, 0.5, 4, 10), 0),
      reach: Math.min(1, [...emits, ...emits2].reduce((a, e) => a + 0.45 * hold(q, e - 4, e + 10), 0)),
      // Caught repeating itself: the screen flashes orange on "new".
      alarm: hold(q, vE0, vE0 + 50),
    };
  };

  // Flat rows from the AI.
  const vE = f(T.isntNew);
  const from = AI_SCREEN;
  const row = (rowY: number, starts: number[], flatStarts: number[] | null, rowIdx: number) =>
    SLOTS.map((sx, j) => {
      const path = (q: number): [number, number] => {
        const p = sp(q, starts[j]).v;
        return [lerp(from[0], sx, p), lerp(from[1], rowY, p) - 170 * Math.sin(Math.PI * u01(p))];
      };
      const p = sp(fr, starts[j]).v;
      if (p <= 0.001) return null;
      let [x, y] = path(fr);
      const [vx, vy] = vel2(path, fr);
      let sxk = 1, syk = 1;
      if (flatStarts) {
        const E = flatStarts[j];
        if (fr < E) {
          const w = ramp(fr, E - 18, E - 4, Easing.inOut(Easing.quad));
          syk = 1 + 0.08 * w; sxk = 1 / syk;
        } else {
          const q = sp(fr, E).v;
          syk = lerp(1.08, 0.42, q); sxk = lerp(1 / 1.08, 1.45, q);
        }
      } else { syk = 0.42; sxk = 1.45; }
      // Beat 3: each row pours into its Venn circle.
      const m = ramp(fr, vE + 2 * j, vE + 2 * j + 16, Easing.in(Easing.cubic));
      if (m >= 1) return null;
      const cx = rowIdx === 0 ? VENN.x - 170 : VENN.x + 170;
      x = lerp(x, cx, m); y = lerp(y, VENN.y, m);
      return (
        <g key={`${rowIdx}${j}`} transform={`translate(${x} ${y}) ${along(vx, vy)} scale(${Math.min(1.15, p) * (1 - 0.6 * m)})`} opacity={1 - m}>
          <ellipse rx={40 * sxk} ry={40 * syk} fill={C.pale} />
        </g>
      );
    });

  // Venn: the two rows become two translucent circles that slide into each other.
  const rA = VENN.r * sp(fr, vE + 8).v, rB = VENN.r * sp(fr, vE + 12).v;
  const d = 340 + (D40 - 340) * ramp(fr, vE + 34, f(16.7)) + (D80 - D40) * sp(fr, f(T.eighty), POP).v + (D85 - D80) * sp(fr, f(T.ninety), POP).v;
  const overlap = Math.round(Math.max(0, lensFrac(d, VENN.r)) * 100);
  const counterIn = sp(fr, vE + 32).v;

  // Two human writers drift in and barely overlap.
  const hE = f(T.human);
  const triU = ramp(fr, hE, hE + 54, Easing.bezier(0.2, 0, 0, 1));
  const starU = ramp(fr, hE + 8, hE + 62, Easing.bezier(0.2, 0, 0, 1));
  const thirty = sp(fr, f(T.thirty)).v;

  return (
    <g>
      {drawOrbs(orbs, true)}
      {fr >= nE && <Nadia fr={fr} at={nadiaAt} x={NX} y={FLOOR} shadow={false} />}
      <Ground />
      <path d={`M -520 ${FLOOR} L ${NX - 110} ${FLOOR} Q ${NX} ${FLOOR - 2 * bump} ${NX + 110} ${FLOOR} L 2440 ${FLOOR}`} stroke={C.ink} strokeOpacity={0.18} strokeWidth={3} fill="none" />
      {fr >= nE && <ellipse cx={NX} cy={FLOOR + 2} rx={70 * Math.min(1, rise.v)} ry={10} fill={C.shadow} />}
      {drawOrbs(orbs, false)}
      {fr >= aE && <AiBot fr={fr} at={aiAt} x={AX} y={FLOOR} idleFrom={aiIdle} />}
      {row(ROW1_Y, emits, SLOTS.map((_, j) => flatE + 3 * j), 0)}
      {row(ROW2_Y, emits2, null, 1)}
      {rA > 1 && (
        <g>
          <circle cx={VENN.x - d / 2} cy={VENN.y} r={rA} fill={C.ink} fillOpacity={0.2} stroke={C.ink} strokeOpacity={0.55} strokeWidth={4} />
          <circle cx={VENN.x + d / 2} cy={VENN.y} r={rB} fill={C.ink} fillOpacity={0.2} stroke={C.ink} strokeOpacity={0.55} strokeWidth={4} />
          {counterIn > 0.01 && (
            <g transform={`translate(${VENN.x} ${VENN.y}) scale(${counterIn})`}>
              <rect x={-78} y={-38} width={156} height={76} rx={38} fill={C.card} stroke={C.ink} strokeOpacity={0.15} strokeWidth={2} />
              <text y={18} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={50} fill={C.ink}>{overlap}%</text>
            </g>
          )}
        </g>
      )}
      {triU > 0 && (
        <g>
          <g transform={`translate(${1340 + 700 * (1 - triU)} 330) rotate(${-24 * (1 - triU)})`}><Shape kind="tri" r={110} color={C.orange} /></g>
          <g transform={`translate(${1536 + 760 * (1 - starU)} 330) rotate(${30 * (1 - starU)})`} style={{ mixBlendMode: "multiply" }}><Shape kind="star" r={106} color={C.teal} /></g>
          {thirty > 0.01 && (
            <g transform={`translate(1440 478) scale(${thirty})`}>
              <rect x={-74} y={-38} width={148} height={76} rx={38} fill={C.card} stroke={C.ink} strokeOpacity={0.15} strokeWidth={2} />
              <text y={18} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={50} fill={C.ink}>30%</text>
            </g>
          )}
        </g>
      )}
    </g>
  );
};

// ======================= Beat 4: quieter =======================

const Y0 = 430;
const LX0 = 300, LX1 = 1620;
const AMPS = [0, -40, 25, -135, 45, -30, 70, -165, 35, -55, -115, 40, -25, 15, -150, 30, -70, 20, -125, 10, 0];
const PEAKS = [3, 7, 10, 14, 18];
const N = AMPS.length;
const xAt = (i: number) => LX0 + ((LX1 - LX0) * i) / (N - 1);
const gentle = (i: number) => 20 * Math.sin(i * 0.8);
const R = 64;

/** Frame at which an eased ramp from a to b reaches fraction y. */
const invRamp = (a: number, b: number, y: number, ease: (x: number) => number) => {
  let lo = 0, hi = 1;
  for (let i = 0; i < 30; i++) {
    const m = (lo + hi) / 2;
    if (ease(m) < y) lo = m; else hi = m;
  }
  return a + (b - a) * (lo + hi) / 2;
};

const ROLL_A = 4, ROLL_B = 46; // roll frames after the press

export const rollerAt = (fr: number) => {
  const E = f(T.quieter);
  const enter = ramp(fr, E - 36, E - 18, Easing.bezier(0.2, 0, 0, 1));
  const hover = { x: 340, y: 300 };
  const wind = ramp(fr, E - 18, E - 7, Easing.inOut(Easing.quad)) * 34;
  const drop = ramp(fr, E - 3, E, Easing.in(Easing.quad));
  const roll = ramp(fr, E + ROLL_A, E + ROLL_B, inOut);
  const leave = ramp(fr, E + ROLL_B + 2, E + ROLL_B + 20, depart);
  const contact = { x: LX0, y: Y0 - R + 6 };
  let x = lerp(-120, hover.x, enter) - wind * 0.707;
  let y = lerp(-200, hover.y, enter) - wind * 0.707;
  x = lerp(x, contact.x, drop); y = lerp(y, contact.y, drop);
  x += (LX1 - LX0) * roll;
  // Rolls on along the line and out of frame, accelerating away.
  x += 900 * leave;
  return { x, y, visible: enter > 0 && leave < 1, rot: ((x - LX0) / R) * (180 / Math.PI) };
};

export const Quieter: React.FC<P> = ({ fr }) => {
  const E = f(T.quieter);
  const drawA = f(T.feelings), drawB = f(26.85);
  const draw = ramp(fr, drawA, drawB, inOut);
  const passF = (i: number) => {
    const frac = Math.max(0, (xAt(i) - 40 - LX0) / (LX1 - LX0));
    return i === 0 ? E : invRamp(E + ROLL_A, E + ROLL_B, frac, inOut);
  };
  const pts = AMPS.map((a, i) => {
    const k = sp(fr, passF(i), { damping: 10, stiffness: 220 }).v;
    return { x: xAt(i), y: Y0 + lerp(a, gentle(i), k), k };
  });
  // Straight segments while jagged; Catmull-Rom tangents fade in as each segment is pressed.
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < N - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(N - 1, i + 2)];
    const s = u01((p1.k + p2.k) / 2);
    d += ` C ${p1.x + ((p2.x - p0.x) / 6) * s} ${p1.y + ((p2.y - p0.y) / 6) * s} ${p2.x - ((p3.x - p1.x) / 6) * s} ${p2.y - ((p3.y - p1.y) / 6) * s} ${p2.x} ${p2.y}`;
  }
  const rl = rollerAt(fr);
  const rSy = 1 - bounce(fr, E, 2.2, 3, 6);

  const cE = f(T.conflict);
  const cBar = sp(fr, cE), cLab = sp(fr, cE + 4).v, cVal = sp(fr, cE + 8).v;
  const cPct = 20 + (7.7 - 20) * ramp(fr, f(30.3), f(T.eight), Easing.inOut(Easing.cubic));
  const cSy = 1 - bounce(fr, f(T.eight), 1.2, 3, 6);
  const nE = f(T.neutral);
  const nBar = sp(fr, nE), nLab = sp(fr, nE + 4).v, nVal = sp(fr, nE + 8).v;
  const nPct = 29 + 16 * ramp(fr, f(T.climb), f(T.fortyFive), Easing.inOut(Easing.cubic));
  const nSy = 1 - bounce(fr, f(T.fortyFive), 1.2, 3, 6);
  const PX = 20;
  const bar = (y: number, label: string, pct: number, prog: number, lab: number, val: number, color: string, sy: number, txt: string) => (
    <g>
      {lab > 0.01 && <text x={290} y={y + 13} fontFamily={mono} fontWeight={700} fontSize={36} letterSpacing={2} fill={C.ink}
        opacity={u01(lab * 1.5)} transform={`translate(${-20 * (1 - lab)} 0)`}>{label}</text>}
      {prog > 0.001 && <rect x={560} y={y - 28 * sy} width={Math.max(0, pct * PX * prog)} height={56 * sy} rx={28 * sy} fill={color} />}
      {val > 0.01 && <text x={560 + pct * PX * prog + 24} y={y + 18} fontFamily={fontFamily} fontWeight={800} fontSize={52} fill={C.ink}
        opacity={u01(val * 1.5)}>{txt}</text>}
    </g>
  );

  return (
    <g>
      {/* Baseline and empty bar tracks arrive during the pan, so the stage is never blank and the bars have a home. */}
      <line x1={LX0} y1={Y0} x2={LX0 + (LX1 - LX0) * ramp(fr, f(25.0), f(26.0))} y2={Y0} stroke={C.ink} strokeOpacity={0.16} strokeWidth={3} strokeDasharray="2 12" strokeLinecap="round" />
      {[650, 770].map((y, i) => {
        const w = ramp(fr, f(25.4) + 6 * i, f(26.3) + 6 * i, Easing.bezier(0.2, 0, 0, 1));
        return w > 0 && <rect key={y} x={560} y={y - 28} width={45 * PX * w} height={56} rx={28} fill={C.deep} />;
      })}
      {draw > 0 && <path d={d} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - draw} stroke={C.ink} strokeWidth={7} strokeLinejoin="round" strokeLinecap="round" fill="none" />}
      {PEAKS.map((i) => {
        const at = invRamp(drawA, drawB, i / (N - 1), inOut);
        const s = sp(fr, at).v;
        if (s <= 0.001) return null;
        const p = pts[i];
        return <circle key={i} cx={p.x} cy={p.y} r={15 * s * (1 - 0.45 * u01(p.k))} fill={mixC(C.orange, C.orangeLight, p.k)} />;
      })}
      {rl.visible && (
        <g transform={`translate(${rl.x} ${rl.y}) scale(${1 / rSy} ${rSy})`}>
          <ellipse cx={0} cy={R + 4} rx={R * 0.8} ry={6} fill={C.ink} opacity={0.1} />
          <circle r={R} fill={C.ink} />
          <circle r={R - 16} fill="none" stroke={C.inkLight} strokeWidth={6} />
          <g transform={`rotate(${rl.rot})`}>
            {[0, 120, 240].map((a) => <line key={a} x1={0} y1={0} x2={(R - 22) * Math.cos((a * Math.PI) / 180)} y2={(R - 22) * Math.sin((a * Math.PI) / 180)} stroke={C.paper} strokeOpacity={0.35} strokeWidth={6} strokeLinecap="round" />)}
          </g>
          <circle r={9} fill={C.paper} />
          <path d={`M ${-R * 0.62} ${-R * 0.46} A ${R * 0.78} ${R * 0.78} 0 0 1 ${-R * 0.1} ${-R * 0.78}`} stroke={C.inkLight} strokeWidth={8} strokeLinecap="round" fill="none" />
        </g>
      )}
      {bar(650, "CONFLICT", cPct, cBar.v, cLab, cVal, C.orange, cSy, `${cPct < 10 ? cPct.toFixed(1) : Math.round(cPct)}%`)}
      {bar(770, "NEUTRAL", nPct, nBar.v, nLab, nVal, C.grey, nSy, `${Math.round(nPct)}%`)}
    </g>
  );
};

// ======================= Beat 5: tidy =======================

const LY = 620, TX0 = 260, TX1 = 1480;
const BRANCH = "M 560 620 C 620 500, 720 420, 840 420 C 960 420, 1030 330, 970 290 C 910 250, 860 340, 930 400 C 1000 460, 1110 470, 1180 540";

/** Tidy gift box with ribbon and a two-triangle bow, centred on 0,0. */
const GiftBox: React.FC<{ s: number; bow: number; bowSy?: number }> = ({ s, bow, bowSy = 1 }) => (
  <g transform={`scale(${s})`}>
    <rect x={-65} y={-65} width={130} height={130} rx={14} fill={C.pale} stroke={C.ink} strokeWidth={5} />
    <rect x={-9} y={-63} width={18} height={126} fill={C.orange} />
    <rect x={-63} y={-9} width={126} height={18} fill={C.orange} />
    {bow > 0.001 && (
      <g transform={`translate(0 -66) scale(${bow / bowSy} ${bow * bowSy})`}>
        <polygon points="-4,-14 -50,-44 -50,10" fill={C.orange} stroke={C.orange} strokeWidth={8} strokeLinejoin="round" />
        <polygon points="4,-14 50,-44 50,10" fill={C.orange} stroke={C.orange} strokeWidth={8} strokeLinejoin="round" />
        <circle cy={-14} r={13} fill={C.orangeText} />
      </g>
    )}
  </g>
);

export const Tidy: React.FC<P> = ({ fr, uid }) => {
  const lineDraw = ramp(fr, f(T.itself) - 3, f(T.itself) + 33, inOut);
  const branchDraw = ramp(fr, f(37.0), f(37.75), inOut);
  const bE = f(T.bow);
  const boxP = sp(fr, bE);
  const endX = fr < bE ? TX1 - 40 * ramp(fr, bE - 22, bE - 7, Easing.inOut(Easing.quad)) : TX1 - 40 * (1 - boxP.v);
  const [bsy] = stretch(boxP.vel, 0.012, -0.14, 0.14);
  const bow = sp(fr, bE + 4);
  const [bowSy] = stretch(bow.vel, 0.012, -0.16, 0.16);

  const thE = f(T.theme);
  const tag = sp(fr, thE).v;
  const swing = bounce(fr, thE, 70, 1.4, 2.4);

  const sE = f(T.subplots);
  // Cut loose, the branch springs up off the line and floats there, faint: detached, still readable at "bow".
  const drop = sp(fr, sE, { damping: 9, stiffness: 120 }).v;
  const fallY = -80 * drop + 6 * Math.sin((fr - sE) / 40) * u01(drop);
  const fallRot = -5 * drop;
  const branchOp = 0.75 - 0.4 * ramp(fr, sE, sE + 40);

  return (
    <g>
      {branchDraw > 0 && branchOp > 0.01 && (
        <path d={BRANCH} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - branchDraw} stroke={C.teal} strokeWidth={8}
          strokeLinecap="round" fill="none" opacity={branchOp} transform={`translate(0 ${fallY}) rotate(${fallRot} 560 620)`} />
      )}
      {lineDraw > 0 && <line x1={TX0} y1={LY} x2={TX0 + (endX - TX0) * lineDraw} y2={LY} stroke={C.ink} strokeWidth={8} strokeLinecap="round" />}
      {tag > 0.001 && (
        <g transform={`translate(820 ${LY}) rotate(${swing}) scale(${tag})`}>
          <line x1={0} y1={0} x2={0} y2={40} stroke={C.ink} strokeWidth={3} />
          <circle r={7} fill={C.ink} />
          <rect x={-82} y={40} width={164} height={52} rx={26} fill={C.ink} />
          <text y={75} textAnchor="middle" fontFamily={mono} fontWeight={700} fontSize={26} letterSpacing={3} fill={C.paper}>THEME</text>
        </g>
      )}
      <Scissors fr={fr} E={sE} x={560} y={LY} rot={-45} />
      <Flash fr={fr} E={sE} x={560} y={LY} r={120} amp={0.8} id={`tsf${uid}`} />
      <Burst fr={fr} E={sE} seed="snip" n={8} x={560} y={LY} speed={[160, 320]} size={[6, 11]} colors={[C.teal, C.ink, C.tealLight]} life={1.2} />
      {boxP.v > 0.001 && (
        <g transform={`translate(${TX1 + 65} ${LY}) scale(${1 / bsy} ${bsy})`}>
          <GiftBox s={boxP.v} bow={bow.v} bowSy={bowSy} />
        </g>
      )}
      <Flash fr={fr} E={bE} x={TX1 + 65} y={LY - 40} r={240} amp={0.75} id={`tbf${uid}`} />
      <Burst fr={fr} E={bE} seed="bow" n={10} x={TX1 + 65} y={LY - 60} colors={[C.orange, C.teal, C.orangeLight]} life={1.6} />
    </g>
  );
};

// ======================= Beat 6: flagged =======================

export const FN = { x: 600, y: 780 }; // Nadia's feet in this stage
const CELL = 360;
export const ZG = 0.23;
// Camera centre (stage coords) for the zoomed-out grid: puts the grid centre at screen (700, 480).
export const GC = { x: FN.x + 1.5 * CELL + 260 / ZG, y: FN.y - 165 - 0.5 * CELL + 60 / ZG };
const PAGE = { x0: 800, y0: 230, x1: 1480, y1: 740 };
const WRITE = [
  { x: 920, y: 360, kind: "tri" as Kind, color: C.orange, r: 46, rot: -8 },
  { x: 1090, y: 345, kind: "circle" as Kind, color: C.teal, r: 40, rot: 0 },
  { x: 1262, y: 385, kind: "star" as Kind, color: C.orange, r: 46, rot: 12 },
  { x: 945, y: 585, kind: "zigzag" as Kind, color: C.ink, r: 46, rot: -6 },
  { x: 1125, y: 600, kind: "square" as Kind, color: C.teal, r: 40, rot: -14 },
  { x: 1330, y: 570, kind: "ring" as Kind, color: C.orange, r: 44, rot: 0 },
];
const NADIA_CELL = 5 * 10 + 3;
const STAMPED = (() => {
  const order = Array.from({ length: 100 }, (_, i) => i).filter((i) => i !== NADIA_CELL).sort((a, b) => random(`pick${a}`) - random(`pick${b}`));
  return [...order.slice(0, 60), NADIA_CELL].sort((a, b) => a - b);
})();

const MiniStamp: React.FC<{ s: number; o: number; rot: number }> = ({ s, o, rot }) => (
  <g transform={`rotate(${rot}) scale(${s})`} opacity={o}>
    <rect x={-100} y={-62} width={200} height={124} rx={20} fill={C.card} fillOpacity={0.55} stroke={C.orangeText} strokeWidth={13} />
    <text y={33} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={96} fill={C.orangeText}>AI</text>
  </g>
);

export const Flagged: React.FC<P> = ({ fr, uid }) => {
  const sayE = f(T.says);
  const writes = T.writes.map(f);
  // She writes (right arm out to the page, a flick per word), squints at the scan, jolts at the stamp.
  const nadiaAt = (q: number) => {
    const writing = ramp(q, f(43.8), f(44.15)) * (1 - ramp(q, f(47.2), f(47.6)));
    const shock = hold(q, sayE + 2, f(51.2));
    const fade = ramp(q, colA, colA + 24);
    return {
      x: FN.x, y: FN.y,
      lean: (5 * writing + writes.reduce((a, e) => a + bounce(q, e, 30, 2.5, 6), 0)) * (1 - fade) - 5 * shock,
      armR: 75 * writing + writes.reduce((a, e) => a + bounce(q, e, 260, 3, 6), 0) + 50 * shock,
      armL: 50 * shock,
      look: 7 * (1 - fade), lookY: 3 * writing,
      puzzled: hold(q, f(T.detector), sayE) * 0.8,
      shock,
      sy: 1 - bounce(q, sayE + 1, 2.2, 3, 6),
    };
  };

  // Page collapses into Nadia before the zoom-out; its contents ride with it.
  const colA = f(50.45);
  const col = ramp(fr, colA, colA + 24, depart);

  // Detector beam: a 45° band sweeping the page.
  const bmE = f(T.detector);
  const beam = ramp(fr, bmE, bmE + 84, inOut);
  const c = lerp(PAGE.x0 + PAGE.y0 - 140, PAGE.x1 + PAGE.y1 + 40, beam);

  // Stamp: rises (wind-up), holds 4 frames, drops in 3 so the impact lands on "AI".
  const appear = ramp(fr, sayE - 30, sayE - 22, Easing.bezier(0.2, 0, 0, 1));
  const lift = -150 - 40 * ramp(fr, sayE - 22, sayE - 7, Easing.inOut(Easing.quad));
  const drop = ramp(fr, sayE - 3, sayE, Easing.in(Easing.quad));
  const stampY = lift * (1 - drop);
  const stampK = lerp(1.3, 1, drop);
  const stampSy = 1 - bounce(fr, sayE, 3, 3, 7);

  // Grid of writers, revealed as the camera pulls back; 61 get stamped in a fast cascade.
  const gridA = f(50.9);
  const s61 = f(T.sixtyOne);
  const vE = f(T.varied);
  const stampedCount = STAMPED.filter((_, k) => fr >= s61 + k).length;

  const word = sp(fr, f(T.word), SOFT).v;
  const ours = Array.from({ length: 7 }, (_, j) => ({ kind: (j % 2 ? "square" : "circle") as Kind, color: j % 3 === 2 ? C.ink : C.grey }));
  const VARIED: { kind: Kind; color: string }[] = [
    { kind: "tri", color: C.orange }, { kind: "star", color: C.teal }, { kind: "zigzag", color: C.ink }, { kind: "ring", color: C.orange },
    { kind: "diamond", color: C.teal }, { kind: "circle", color: C.orange }, { kind: "square", color: C.ink }, { kind: "star", color: C.orange },
    { kind: "tri", color: C.teal }, { kind: "ring", color: C.ink },
  ];
  const aiMini = sp(fr, f(T.aiText));
  const aiSq = fr < vE ? 1 - 0.18 * ramp(fr, vE - 18, vE - 4, Easing.inOut(Easing.quad)) : 1 - 0.18 * (1 - sp(fr, vE).v);
  const n61 = sp(fr, s61);

  return (
    <g>
      {Array.from({ length: 100 }, (_, i) => {
        if (i === NADIA_CELL) return null;
        const col_ = i % 10, row_ = Math.floor(i / 10);
        const at = gridA + Math.hypot(col_ - 3, row_ - 5) * 2.4;
        const p = sp(fr, at);
        if (p.v <= 0.001) return null;
        const [msy] = stretch(p.vel, 0.02);
        return <Nadia key={i} fr={fr} x={FN.x + (col_ - 3) * CELL} y={FN.y + (row_ - 5) * CELL} k={p.v} sy={msy} seed={i * 0.73} look={4 * Math.sin(i)} simple />;
      })}
      <Nadia fr={fr} at={nadiaAt} x={FN.x} y={FN.y} seed={3.1} />
      {col < 1 && (
        <g opacity={1 - col} transform={`translate(${FN.x} ${FN.y - 130}) scale(${1 - col}) translate(${-FN.x} ${-(FN.y - 130)})`}>
          <rect x={PAGE.x0 + 10} y={PAGE.y0 + 14} width={PAGE.x1 - PAGE.x0} height={PAGE.y1 - PAGE.y0} rx={22} fill={C.ink} opacity={0.06} />
          <rect x={PAGE.x0} y={PAGE.y0} width={PAGE.x1 - PAGE.x0} height={PAGE.y1 - PAGE.y0} rx={22} fill={C.card} stroke={C.ink} strokeOpacity={0.7} strokeWidth={3} />
          {WRITE.map((w, i) => {
            const p = sp(fr, writes[i]);
            if (p.v <= 0.001) return null;
            const [wsy] = stretch(p.vel, 0.015);
            return (
              <g key={i} transform={`translate(${w.x} ${w.y}) rotate(${w.rot}) scale(${p.v / wsy} ${p.v * wsy})`}>
                <Shape kind={w.kind} r={w.r} color={w.color} />
              </g>
            );
          })}
          {beam > 0 && beam < 1 && (
            <g>
              <defs>
                <clipPath id={`pg${uid}`}><rect x={PAGE.x0} y={PAGE.y0} width={PAGE.x1 - PAGE.x0} height={PAGE.y1 - PAGE.y0} rx={22} /></clipPath>
                <linearGradient id={`bm${uid}`} gradientUnits="userSpaceOnUse" x1={c - PAGE.y1} y1={PAGE.y1} x2={c - PAGE.y0} y2={PAGE.y0}>
                  <stop offset="0%" stopColor={C.orange} /><stop offset="100%" stopColor={C.teal} />
                </linearGradient>
              </defs>
              <g clipPath={`url(#pg${uid})`}>
                <polygon points={`${c - 2000},2000 ${c + 2000},-2000 ${c - 120 + 2000},-2000 ${c - 120 - 2000},2000`} fill={C.teal} opacity={0.14} />
                <line x1={c - 2000} y1={2000} x2={c + 2000} y2={-2000} stroke={`url(#bm${uid})`} strokeWidth={9} />
              </g>
            </g>
          )}
          {appear > 0 && (
            <g transform={`translate(1140 ${480 + stampY}) rotate(-9) scale(${stampK / stampSy} ${stampK * stampSy})`} opacity={appear}>
              <rect x={-160} y={-100} width={320} height={200} rx={26} fill={C.card} fillOpacity={0.6} stroke={C.orangeText} strokeWidth={14} />
              <text y={56} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={160} fill={C.orangeText}>AI</text>
            </g>
          )}
          <Flash fr={fr} E={sayE} x={1140} y={480} r={300} amp={0.35} id={`fsf${uid}`} />
          <Burst fr={fr} E={sayE} seed="stamp" n={10} x={1140} y={480} speed={[260, 520]} size={[8, 15]} colors={[C.orangeText, C.orange, C.ink]} life={1.4} />
        </g>
      )}
      {STAMPED.map((i, k) => {
        const at = s61 + k;
        const p = sp(fr, at, { damping: 14, stiffness: 260 }).v;
        if (p <= 0.001) return null;
        const fade = ramp(fr, vE + 6 + k * 0.5, vE + 20 + k * 0.5, depart);
        if (fade >= 1) return null;
        const col_ = i % 10, row_ = Math.floor(i / 10);
        return (
          <g key={i} transform={`translate(${FN.x + (col_ - 3) * CELL} ${FN.y + (row_ - 5) * CELL - 150})`}>
            <MiniStamp s={lerp(1.7, 1, p)} o={u01(p * 3) * (1 - fade)} rot={-10 + 10 * random(`sr${i}`)} />
          </g>
        );
      })}
      {/* Overlay authored in the zoomed-out camera's screen space. */}
      <g transform={`translate(${GC.x} ${GC.y}) scale(${1 / ZG}) translate(-960 -540)`}>
        {n61.v > 0.001 && (
          <g transform={`translate(1560 ${lerp(470, 300, word)}) scale(${n61.v * lerp(1, 0.62, word)})`}>
            <text y={70} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={230} fill={C.ink}>{stampedCount}%</text>
          </g>
        )}
        {word > 0.01 && (
          <g>
            <text x={1260} y={480} fontFamily={mono} fontWeight={700} fontSize={26} letterSpacing={2} fill={C.ink} opacity={u01(sp(fr, f(T.word) + 6).v * 1.5)}>OURS</text>
            {ours.map((o, j) => {
              const p = sp(fr, f(T.word) + 10 + 3 * j).v;
              return p > 0.001 && <g key={j} transform={`translate(${1290 + 76 * j} 540) scale(${p})`}><Shape kind={o.kind} r={22} color={o.color} /></g>;
            })}
          </g>
        )}
        {aiMini.v > 0.001 && (
          <g>
            <text x={1260} y={652} fontFamily={mono} fontWeight={700} fontSize={26} letterSpacing={2} fill={C.ink} opacity={u01(aiMini.v * 1.5)}>AI</text>
            <g transform={`translate(1296 730) scale(${aiMini.v / aiSq} ${aiMini.v * aiSq})`}>
              <rect x={-34} y={-34} width={68} height={68} rx={12} fill={C.ink} />
              <AiFace fr={fr} cx={0} cy={0} r={20} color={C.paper} />
            </g>
            {VARIED.map((v, j) => {
              const E = vE + 2 * j;
              const path = (q: number): [number, number] => {
                const p = sp(q, E).v;
                return [lerp(1296, 1388 + 50 * j, p), lerp(730, 730, p) - 60 * Math.sin(Math.PI * u01(p))];
              };
              const p = sp(fr, E).v;
              if (p <= 0.001) return null;
              const [x, y] = path(fr);
              const [vx, vy] = vel2(path, fr);
              return <g key={j} transform={`translate(${x} ${y}) ${along(vx, vy)} scale(${p})`}><Shape kind={v.kind} r={20} color={v.color} /></g>;
            })}
            <Burst fr={fr} E={vE} seed="varied" n={10} x={1296} y={730} speed={[180, 360]} size={[5, 10]} colors={[C.orange, C.teal, C.ink]} life={1.4} />
          </g>
        )}
      </g>
    </g>
  );
};

// ======================= Beats 7–9: fix, alive, CTA =======================

const ROW = { x: 960, y: 420 };
const RSX = [-270, -150, -30, 90, 210];
const FINAL: { kind: Kind; color: string }[] = [
  { kind: "tri", color: C.orange }, { kind: "ring", color: C.teal }, { kind: "star", color: C.orange },
  { kind: "zigzag", color: C.ink }, { kind: "square", color: C.teal },
];
const PINS = [
  { j: 0, text: "Ibu Rina", at: () => f(T.people) },
  { j: 4, text: "Jakarta", at: () => f(T.places) },
  { j: 1, text: "1998", at: () => f(T.places) + 6 },
];
const MARK_C = { x: 960, y: 392 };
const MARK_K = 330 / 256;
const URL = "miraestudio.id";

export const Home3: React.FC<P> = ({ fr, uid }) => {
  const t = fr / FPS;
  const aiIdle = f(59.3);

  // Hand-over: the AI's row slides to the middle.
  const hE = f(T.drafts);
  const rowPos = (q: number): [number, number] => {
    const p = sp(q, hE).v;
    const bob = -8 * Math.sin((2 * Math.PI * (q - aiIdle)) / FPS / 2) * (1 - u01(p));
    return [lerp(AX, ROW.x, p), lerp(500, ROW.y, p) + bob - 110 * Math.sin(Math.PI * u01(p))];
  };
  const hp = sp(fr, hE).v;
  const [rx, ry] = rowPos(fr);
  const [rvx, rvy] = vel2(rowPos, fr);
  const rowK = lerp(0.6, 1, hp);

  const mE = f(T.moral), oE = f(T.open), fE = f(T.fight), lE = f(T.life), cE = f(T.research);
  const gap = 80 * sp(fr, oE).v;
  // Box falls after the snip, lands on its side, settles, fades.
  const tau = Math.max(0, (fr - mE) / FPS);
  const landT = Math.sqrt((2 * (FLOOR - 55 - ROW.y)) / 2600);
  const boxY = tau < landT ? ROW.y + 0.5 * 2600 * tau * tau : FLOOR - 55 - Math.abs(bounce(fr, mE + landT * FPS, 300, 2.5, 7));
  const boxRot = Math.min(90, (90 * tau) / landT);
  const boxOut = ramp(fr, mE + 62, mE + 80, depart);

  // Life: wind-up squash of the row, release on "life".
  const lifeSq = fr < lE ? 1 - 0.12 * ramp(fr, lE - 18, lE - 4, Easing.inOut(Easing.quad)) : 1;
  const lineOut = ramp(fr, lE, lE + 10, depart);
  // Nadia's happy squash-hop, trailing the release.
  const hop = lE + 4, TJ = 0.38;
  const hopAt = (q: number) => {
    const ht = (q - hop) / FPS;
    if (q >= lE - 2 && ht < 0) return { y: 0, sy: 1 - 0.14 * ramp(q, lE - 2, hop) };
    if (ht >= 0 && ht <= TJ) return { y: -4 * 80 * (ht / TJ) * (1 - ht / TJ), sy: 1 + 0.12 * Math.abs(1 - (2 * ht) / TJ) };
    if (ht > TJ) return { y: 0, sy: 1 - bounce(q, hop + TJ * FPS, 2.4, 3, 6) };
    return { y: 0, sy: 1 };
  };
  // Nadia does each edit herself: a poke of the right arm per action, a cheer on "life", eyes on the mark.
  const actions = [mE, oE, fE, f(T.people), f(T.places)];
  const nadiaAt = (q: number) => {
    const h = hopAt(q);
    const cheer = hold(q, lE, lE + 50);
    const poke = actions.reduce((a, e) => a + hold(q, e - 8, e + 12), 0);
    return {
      x: NX, y: FLOOR + h.y, sy: h.sy,
      armR: 85 * hold(q, hE - 6, hE + 40) + 70 * poke + 150 * cheer, armL: 150 * cheer + 15 * poke,
      lean: 4 * poke + 3 * hold(q, hE - 6, hE + 40),
      happy: Math.min(1, 0.35 * hold(q, hE, mE - 20) + sp(q, lE).v * 0.95),
      look: 6, lookY: -4 * Math.min(1, poke) - 5 * ramp(q, cE, cE + 20),
      tilt: -6 * ramp(q, cE, cE + 30),
    };
  };
  const aiAt = (q: number) => ({
    x: AX, y: FLOOR, sy: 1 - bounce(q, hE, 1.2, 4, 8),
    reach: hold(q, hE - 6, hE + 30),
    // Its moral gets cut: a brief orange alarm.
    alarm: 0.85 * hold(q, mE + 3, mE + 45),
  });

  // CTA: orbit widens (wind-up), holds, then every shape flies into the mark; impact on "research".
  const grow = 1 + 0.1 * ramp(fr, cE - 40, cE - 24, Easing.inOut(Easing.quad));
  const fly = ramp(fr, cE - 20, cE, Easing.in(Easing.cubic));
  const markP = sp(fr, cE);
  const markSy = 1 - bounce(fr, cE, 2.4, 3, 6);

  const shapePos = (j: number, q: number): [number, number] => {
    const base: [number, number] = [ROW.x + RSX[j], ROW.y];
    const q1 = sp(q, lE + 4 * j).v;
    const o = orbit(j, q, NX, ORBIT_Y, q >= cE - 40 ? 1 + 0.1 * ramp(q, cE - 40, cE - 24, Easing.inOut(Easing.quad)) : 1);
    let x = lerp(base[0], o.x, q1), y = lerp(base[1], o.y, q1) - 130 * Math.sin(Math.PI * u01(q1));
    const fl = ramp(q, cE - 20, cE, Easing.in(Easing.cubic));
    x = lerp(x, MARK_C.x, fl); y = lerp(y, MARK_C.y, fl);
    return [x, y];
  };

  const orbs: Orb[] = [];
  const rowShapes: React.ReactNode[] = [];
  FINAL.forEach((fin, j) => {
    const q = sp(fr, lE + 4 * j).v;
    const swap = ramp(fr, lE + 4 * j, lE + 4 * j + 8);
    const spikes = j === 2 || j === 3 ? sp(fr, fE + 5 * (j - 2)).v : 0;
    const paleColor = j === 1 ? mixC(C.pale, C.grey, sp(fr, oE).v) : spikes > 0 ? mixC(C.pale, C.orange, spikes) : C.pale;
    const pale = <Shape kind={j === 1 ? "ring" : "circle"} r={40} color={paleColor} gap={j === 1 ? gap : 0} spikes={spikes} />;
    if (fr < lE) {
      rowShapes.push(<g key={j} transform={`translate(${RSX[j]} 0)`}>{pale}</g>);
      return;
    }
    if (fly >= 1) return;
    const [x, y] = shapePos(j, fr);
    const [vx, vy] = vel2((qq) => shapePos(j, qq), fr);
    const o = orbit(j, fr, NX, ORBIT_Y, grow);
    const back = q > 0.7 && o.back && fly === 0;
    const k = (back ? 0.84 : 1) * lerp(1, 0.35, fly) * (0.75 + 0.25 * Math.min(1, q));
    orbs.push({
      key: `l${j}`, x, y, back, depth: o.depth,
      xf: `${along(vx, vy, 1 / 2000, 0.25)} scale(${k}) rotate(${STORY[j].rot * swap + 8 * Math.sin(t * 0.7 + j)})`,
      node: (
        <g>
          {swap < 1 && <g opacity={1 - swap}>{pale}</g>}
          {swap > 0 && <g opacity={swap} transform={`scale(${0.75 * swap + 0.25})`}><Shape kind={fin.kind} r={42} color={fin.color} gap={j === 1 ? 80 : 0} /></g>}
        </g>
      ),
    });
  });

  const tE = f(T.url);
  let prevOff = 0;

  return (
    <g>
      {drawOrbs(orbs, true)}
      <Ground />
      <line x1={-520} y1={FLOOR} x2={2440} y2={FLOOR} stroke={C.ink} strokeOpacity={0.18} strokeWidth={3} />
      <Nadia fr={fr} at={nadiaAt} x={NX} y={FLOOR} seed={1.7} />
      <AiBot fr={fr} at={aiAt} x={AX} y={FLOOR} idleFrom={aiIdle} />
      {fr < lE + 12 && (
        <g transform={`translate(${rx} ${ry}) ${along(rvx, rvy, 1 / 3000, 0.15)} scale(${rowK / lifeSq} ${rowK * lifeSq})`}>
          <line x1={-330} y1={0} x2={fr >= mE ? 285 : 305} y2={0} stroke={C.ink} strokeOpacity={0.5 * (1 - lineOut)} strokeWidth={4} strokeLinecap="round" />
          {rowShapes}
          {fr < mE && <g transform="translate(360 0) scale(0.85)"><GiftBox s={1} bow={1} /></g>}
          {PINS.map((pin) => {
            const p = sp(fr, pin.at()).v;
            const out = ramp(fr, lE, lE + 10, depart);
            if (p <= 0.001 || out >= 1) return null;
            const w = pin.text.length * 14.4 + 26;
            return (
              <g key={pin.text} transform={`translate(${RSX[pin.j]} ${pin.j === 1 ? -62 : -42}) rotate(${bounce(fr, pin.at(), 50, 1.6, 3)}) scale(${p * (1 - out)})`}>
                <line x1={0} y1={0} x2={0} y2={-46} stroke={C.ink} strokeWidth={3} />
                <circle r={6} fill={C.ink} />
                <rect x={-w / 2} y={-86} width={w} height={42} rx={10} fill={C.card} stroke={C.ink} strokeWidth={2.5} />
                <text y={-57} textAnchor="middle" fontFamily={mono} fontWeight={500} fontSize={24} fill={C.ink}>{pin.text}</text>
              </g>
            );
          })}
        </g>
      )}
      {fr >= mE && boxOut < 1 && (
        <g transform={`translate(${ROW.x + 360} ${boxY}) rotate(${boxRot}) scale(0.85)`} opacity={1 - boxOut}>
          <GiftBox s={1} bow={1} />
        </g>
      )}
      <Scissors fr={fr} E={mE} x={ROW.x + 285} y={ROW.y} rot={-45} />
      <Flash fr={fr} E={mE} x={ROW.x + 285} y={ROW.y} r={110} amp={0.8} id={`hmf${uid}`} />
      {drawOrbs(orbs, false)}
      <Flash fr={fr} E={lE} x={ROW.x} y={ROW.y} r={420} amp={0.8} id={`hlf${uid}`} />
      <Burst fr={fr} E={lE} seed="life" n={12} x={ROW.x} y={ROW.y} speed={[260, 560]} size={[8, 16]} colors={[C.orange, C.teal, C.ink, C.orangeLight]} life={2.2} />
      {markP.v > 0.001 && (
        <g transform={`translate(${MARK_C.x} ${MARK_C.y}) scale(${(MARK_K * lerp(0.55, 1, markP.v) * (1 + 0.012 * Math.sin((2 * Math.PI * (fr - cE)) / FPS / 7))) / markSy} ${MARK_K * lerp(0.55, 1, markP.v) * markSy * (1 + 0.012 * Math.sin((2 * Math.PI * (fr - cE)) / FPS / 7))}) translate(-128 -128)`}>
          <defs>
            <linearGradient id={`mk${uid}`} gradientUnits="userSpaceOnUse" x1={0} y1={255} x2={255} y2={0}>
              <stop offset="0%" stopColor={C.orange} /><stop offset="100%" stopColor={C.teal} />
            </linearGradient>
          </defs>
          <path d={MARK} fill={`url(#mk${uid})`} />
        </g>
      )}
      <Flash fr={fr} E={cE} x={MARK_C.x} y={MARK_C.y} r={360} amp={0.85} id={`hcf${uid}`} />
      <Burst fr={fr} E={cE} seed="mark" n={12} x={MARK_C.x} y={MARK_C.y} speed={[300, 620]} size={[8, 15]} colors={[C.orange, C.teal, C.orangeLight, C.tealLight]} life={2.4} />
      {fr >= tE && (
        <text x={MARK_C.x} y={690} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={66} fill={C.ink}>
          {URL.split("").map((ch, i) => {
            const q = sp(fr, tE + 2.5 * i).v;
            const off = (1 - Math.min(1, q)) * 18;
            const dy = off - prevOff;
            prevOff = off;
            return <tspan key={i} dy={dy} opacity={interpolate(q, [0, 0.4], [0, 1], clamp)}>{ch}</tspan>;
          })}
        </text>
      )}
    </g>
  );
};

/** Camera nudge (px) from big impacts, applied by AiFlat. */
export const nudge = (fr: number) =>
  bounce(fr, f(T.quieter), 40) + bounce(fr, f(T.bow), 34) + bounce(fr, f(T.says), 66) + bounce(fr, f(T.life), 40) + bounce(fr, f(T.research), 46);

/** Saturation/brightness spike on the payoffs, from the frame's own time. */
export const hit = (fr: number) => decay(fr, f(T.life), 5) + 0.8 * decay(fr, f(T.research), 5);
