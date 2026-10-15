// Beats 4–6: the ants on their trail, the eagle on its perch, the four kinds of specialist.
// Each beat is drawn in world coordinates (kit: P, HOME, SHOT) and receives the composition frame.
import React from "react";
import { Easing } from "remotion";
import {
  Ant, arrive, at, B, BeatProps, blob, bounce, Burst, C, decay, depart, Draw, Eagle, Flash, FONT, FPS, GpuCube, GpuPile, GROUND, HIT, HOME, KIND,
  Label, lerp, mixC, MONO, NeedBlob, P, punch, ramp, Residents, settle, SOFT, sp, Tag, vel2,
} from "./kit";

type V = [number, number];
const u01 = (v: number) => Math.max(0, Math.min(1, v));
const line = (v: number) => v;
// Area-preserving scale pair, as the kit's actors use: s > 0 flattens, s < 0 stretches.
const sq = (s: number): [number, number] => (s >= 0 ? [1 + s, 1 / (1 + s)] : [1 / (1 - s), 1 - s]);
/** 0 → 1 → 0: up between a and b, back down between b and c. */
const hump = (fr: number, a: number, b: number, c: number) => ramp(fr, a, b) * (1 - ramp(fr, b, c));
/** The crouch before an event on frame E: flattens to `amt`, holds for the hit-pause, lets go on E. */
const crouch = (fr: number, E: number, amt: number, wind = 12) => (fr >= E ? 0 : amt * ramp(fr, E - HIT - wind, E - HIT));
const paused = (fr: number, ...events: number[]) => events.some((e) => fr >= e - HIT && fr < e);
const firstFrame = (from: number, to: number, hit: (fr: number) => boolean) => {
  for (let q = from; q < to; q++) if (hit(q)) return q;
  return to;
};
const bez = (p: V[], t: number): V => {
  const m = 1 - t, w = [m * m * m, 3 * m * m * t, 3 * m * t * t, t * t * t];
  return [p.reduce((s, q, j) => s + w[j] * q[0], 0), p.reduce((s, q, j) => s + w[j] * q[1], 0)];
};
/** Tilt (nose along the travel) and squash (long along the travel) of a flier from its velocity in px/s. */
const lean = ([vx, vy]: V) => {
  const speed = Math.hypot(vx, vy);
  return {
    tilt: Math.max(-26, Math.min(26, (Math.atan2(vy, Math.abs(vx) + 1) * 90) / Math.PI)) * Math.min(1, speed / 500),
    squash: Math.max(-0.12, Math.min(0.12, (Math.abs(vx) - Math.abs(vy)) / 7000)),
  };
};

/** A paper turn about the vertical line through x: `face` 1 faces right, -1 left, 0 is edge-on. */
const Turn: React.FC<{ x: number; face: number; children?: React.ReactNode }> = ({ x, face, children }) =>
  face >= 1 ? <>{children}</> : (
    <div style={{ position: "absolute", left: 0, top: 0, width: 0, height: 0, transformOrigin: `${x}px 0px`, transform: `scaleX(${face})` }}>{children}</div>
  );

const Check: React.FC<{ x: number; y: number; r: number; v: number }> = ({ x, y, r, v }) => v <= 0.001 ? null : (
  <g transform={`translate(${x} ${y}) scale(${v})`}>
    <circle r={r} fill={C.gold} />
    <path d={`M ${-r * 0.45} ${r * 0.04} L ${-r * 0.1} ${r * 0.38} L ${r * 0.48} ${-r * 0.32}`} fill="none" stroke={C.ground} strokeWidth={r * 0.26} strokeLinecap="round" strokeLinejoin="round" />
  </g>
);

const mono = (size: number, fill: string): React.SVGProps<SVGTextElement> => ({ fontFamily: MONO, fontWeight: 500, fontSize: size, fill, letterSpacing: "0.06em" });

// ======================= Beat 4: the ants =======================

const ROLL = at(4, "Laporan");
const REST = at(4, "pasti");
const RULES = at(4, "aturannya");
const LIFT = at(4, "semut");
const ARRIVE = at(4, "aturan");
const CRUMB = at(4, "Hampir");
const EAT = at(4, "GPU");
// The column heads home as the camera leaves for the perch.
const HOMEWARD = B[5].start;
const GONE = HOMEWARD + 44;
const stride = Easing.bezier(0.35, 0, 0.8, 0.7); // a walk: up to pace, then steady

const TRAIL_Y = GROUND + 34; // the dotted trail runs in front of the ants: the report rolls on it
const REPORT_R = 90;
const ROLL_X0 = -100;
const CARRY_X = (HOME.ants[2].x + HOME.ants[3].x) / 2;
const CARRY_Y = GROUND - 160;
const MARCH = 380; // the camera's pan from "semut" to "aturan", so the column stays put on screen
const LEAVE = 600;
const LAG = [8, 4, 0, 0]; // the rear ants set off a few frames after the carriers

const rollX = (fr: number) => lerp(ROLL_X0, CARRY_X, ramp(fr, ROLL, REST, Easing.out(Easing.quad)));
const leaveAt = (fr: number) => LEAVE * ramp(fr, HOMEWARD + 9, GONE, stride);
const marchAt = (fr: number) => MARCH * ramp(fr, LIFT, ARRIVE) - leaveAt(fr);
const report = blob({
  from: B[4].start, to: GONE, floor: TRAIL_Y, hits: [LIFT],
  kicks: [{ at: EAT, oval: 70, angle: Math.PI / 2 }],
  path: (fr) => ({ x: rollX(fr) + marchAt(fr), y: lerp(TRAIL_Y - REPORT_R, CARRY_Y, punch(fr, LIFT, 12, 0.12)), r: REPORT_R }),
});

// Each ant bobs as the report rolls past it.
const PASS = HOME.ants.map((a) => (a.x < CARRY_X ? firstFrame(ROLL, REST, (q) => rollX(q) >= a.x) : Infinity));

const SIGN_X = [1080, 1230, 1380];
const SIGN_Y = GROUND - 322;
const TICK = SIGN_X.map((x) => firstFrame(LIFT, ARRIVE, (q) => CARRY_X + marchAt(q) >= x - 40));

const LEAD = HOME.ants[3];
const MOUTH: V = [78, -52]; // the lead ant's jaws from its anchor
const CRUMB_X = LEAD.x + MARCH + MOUTH[0] + 36;
const lunge = (fr: number) =>
  -9 * crouch(fr, EAT, 1, 10) + 32 * (ramp(fr, EAT, EAT + 4, Easing.out(Easing.cubic)) - ramp(fr, EAT + 5, EAT + 14)) * (fr >= EAT ? 1 : 0);

const antAt = (i: number, fr: number) => {
  const carrier = i >= 2, lag = LAG[i], lead = i === 3;
  const walk = Math.max(ramp(fr, LIFT + lag, LIFT + lag + 8) * (1 - ramp(fr, ARRIVE + lag - 6, ARRIVE + lag + 6)), ramp(fr, HOMEWARD + 4, HOMEWARD + 12));
  const heave = fr < LIFT ? crouch(fr, LIFT, carrier ? 0.16 : 0.05) : carrier ? -0.14 * decay(fr, LIFT, 9) + bounce(fr, LIFT + 6, 2.2, 3.5, 8) : 0;
  const gulp = lead ? -0.07 * crouch(fr, EAT, 1, 10) + 0.1 * decay(fr, EAT, 16) + bounce(fr, EAT + 4, 3.2, 4, 7) : 0;
  return {
    ...HOME.ants[i], x: HOME.ants[i].x + MARCH * ramp(fr - lag, LIFT, ARRIVE) - leaveAt(fr) + (lead ? lunge(fr) : 0),
    walk, squash: heave + gulp + bounce(fr, PASS[i], 1.6, 4, 8), idle: paused(fr, LIFT) || (lead && paused(fr, EAT)) ? 0 : 1,
    tilt: lead ? 7 * hump(fr, EAT, EAT + 4, EAT + 12) : 0,
    face: 1 - 2 * ramp(fr, HOMEWARD + 2 * i, HOMEWARD + 2 * i + 5),
  };
};

// A signpost with one rule on it. The arrow is drawn, so it does not depend on the font's glyphs.
const Sign: React.FC<{ x: number; fr: number; i: number }> = ({ x, fr, i }) => {
  const up = sp(fr, RULES + 5 * i).v, away = ramp(fr, HOMEWARD + 4 * i, HOMEWARD + 4 * i + 12, depart);
  if (up <= 0.001 || away >= 1) return null;
  const lit = ramp(fr, TICK[i], TICK[i] + 5);
  const [sx, sy] = sq(bounce(fr, TICK[i], 1.8, 4, 9));
  const edge = mixC(C.line, C.gold, lit), ink = mixC(C.mute, C.gold, lit);
  return (
    <g transform={`translate(${x} ${GROUND + 40 * away}) scale(1 ${up})`} opacity={1 - away}>
      <rect x={-5} y={SIGN_Y - GROUND + 30} width={10} height={GROUND - SIGN_Y - 30} rx={4} fill={C.wood} />
      <g transform={`translate(0 ${SIGN_Y - GROUND}) scale(${sx} ${sy})`}>
        <rect x={-58} y={-39} width={116} height={78} rx={13} fill={C.card} stroke={edge} strokeWidth={3.5} />
        <text x={0} y={-6} textAnchor="middle" {...mono(21, mixC(C.mute, C.cream, lit))}>JIKA</text>
        <path d="M -42 17 H -22 M -29 10 L -21 17 L -29 24" fill="none" stroke={ink} strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" />
        <text x={-13} y={25} {...mono(21, ink)}>MAKA</text>
        <Check x={52} y={-36} r={15} v={sp(fr, TICK[i]).v} />
      </g>
    </g>
  );
};

// The ants, the report on their backs, the rules beside the trail and the crumb: beat 4, and the start of
// beat 5 while the camera still shows them.
const Column: React.FC<BeatProps> = ({ fr }) => {
  if (fr >= GONE) return null;
  const lead = antAt(3, fr);
  const eaten = ramp(fr, EAT + 1, EAT + 5, Easing.in(Easing.quad));
  const fall = ramp(fr, CRUMB, CRUMB + 7, Easing.in(Easing.quad));
  const away = ramp(fr, HOMEWARD, HOMEWARD + 12, depart);
  return (
    <>
      <Draw>{SIGN_X.map((x, i) => <Sign key={i} x={x} fr={fr} i={i} />)}</Draw>
      <div style={{ opacity: 1 - away, transform: `translateY(${-14 * away}px)` }}>
        <Tag text="Bisa diaudit" color={KIND.cerdas.color} x={SIGN_X[1]} y={SIGN_Y - 96} size={30} fr={fr} start={ARRIVE} />
      </div>
      {HOME.ants.map((_, i) => {
        const a = antAt(i, fr);
        return <Turn key={i} x={a.x} face={a.face}><Ant {...a} t={fr} /></Turn>;
      })}
      {fr >= CRUMB && eaten < 1 && (
        <GpuCube x={lerp(CRUMB_X, lead.x + MOUTH[0], eaten)} y={lerp(GROUND, GROUND + MOUTH[1], eaten) - (1 - fall) * 110} size={26 * (1 - 0.8 * eaten)}
          squash={bounce(fr, CRUMB + 7, 2.4, 3.5, 9)} opacity={Math.min(1, (fr - CRUMB) / 2)} />
      )}
      <NeedBlob sim={report} fr={fr} label="Laporan harian" spin={((rollX(fr) - ROLL_X0) / REPORT_R) * (180 / Math.PI)} />
      <Burst fr={fr} E={EAT + 4} seed="crumb" n={4} x={lead.x + MOUTH[0]} y={GROUND + MOUTH[1]} arc={[220, 330]} colors={[C.gold, C.goldLight]} speed={[90, 190]} size={[4, 8]} life={0.9} />
    </>
  );
};

export const Beat04: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Residents t={fr} hide={["ants"]} />
    <Column fr={fr} />
  </>
);

// ======================= Beat 5: the eagle =======================

const ASK = at(5, "penjualan");
const CHART = at(5, "angka");
const STACK = at(5, "disusun");
const CHECKED = at(5, "dicek");
const TRAIN = at(5, "melatih");
const COST = at(5, "spesialis");
const LAUNCH = at(5, "elang");
const AHEAD = at(5, "dilatih");
const DIVE = at(5, "satu");
const LAND = at(5, "buruan");
const SPLIT = at(6, "macamnya");

const NEED_R = 100;
const SALES: V = [P.perch.x - 350, GROUND - NEED_R];
const BLOCKS = 3;
const sales = blob({
  from: B[5].start, to: SPLIT + 40, floor: GROUND,
  kicks: Array.from({ length: BLOCKS }, (_, j) => ({ at: STACK + 5 * j, lobe: 45 })),
  path: (fr) => ({ x: SALES[0], y: SALES[1] - 780 * (1 - ramp(fr, ASK - 18, ASK, Easing.in(Easing.quad))), r: NEED_R }),
});

// The sales chart stands to the right of the perch: five months of history, then next month's point.
const PANEL = { x: P.perch.x + 195, y: GROUND - 285, w: 500, h: 260 };
const BASE_Y = GROUND - 70;
const HIST: V[] = [95, 116, 107, 142, 168].map((h, j) => [P.perch.x + 245 + 80 * j, GROUND - h]);
const NEXT: V = [P.perch.x + 645, GROUND - 225];
const HIST_D = `M ${HIST.map((p) => p.join(" ")).join(" L ")}`;
const PILE_X = P.perch.x + 120;

const Chart: React.FC<BeatProps> = ({ fr }) => {
  const open = sp(fr, CHART, SOFT).v, gone = ramp(fr, SPLIT + 12, SPLIT + 26, depart);
  if (open <= 0.001 || gone >= 1) return null;
  const drawn = ramp(fr, CHART + 6, CHART + 34);
  const ahead = ramp(fr, AHEAD, DIVE - 4, arrive), [lx, ly] = HIST[HIST.length - 1];
  const ring = sp(fr, DIVE - 6).v, hit = ramp(fr, LAND, LAND + 4);
  return (
    <Draw opacity={1 - gone}>
      <g transform={`translate(0 ${18 * gone})`}>
        <g transform={`translate(${PANEL.x + PANEL.w / 2} ${PANEL.y + PANEL.h}) scale(${0.9 + 0.1 * open} ${open}) translate(${-PANEL.x - PANEL.w / 2} ${-PANEL.y - PANEL.h})`}>
          <rect x={PANEL.x} y={PANEL.y} width={PANEL.w} height={PANEL.h} rx={22} fill={C.card} stroke={C.line} strokeWidth={3} />
          <text x={PANEL.x + 24} y={PANEL.y + 38} {...mono(18, C.mute)} opacity={sp(fr, CHART + 5, SOFT).v}>PENJUALAN</text>
          <line x1={PANEL.x + 24} y1={BASE_Y} x2={PANEL.x + PANEL.w - 24} y2={BASE_Y} stroke={C.line} strokeWidth={3} strokeLinecap="round" />
          {[...HIST, NEXT].map(([x], j) => <line key={j} x1={x} y1={BASE_Y} x2={x} y2={BASE_Y + 9} stroke={C.line} strokeWidth={3} strokeLinecap="round" />)}
        </g>
        <path d={HIST_D} fill="none" stroke={C.gold} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - drawn} opacity={drawn > 0 ? 1 : 0} />
        {HIST.map(([x, y], j) => <circle key={j} cx={x} cy={y} r={8 * sp(fr, CHART + 6 + 7 * j).v} fill={C.goldLight} />)}
        {ahead > 0 && <line x1={lx} y1={ly} x2={lerp(lx, NEXT[0], ahead)} y2={lerp(ly, NEXT[1], ahead)} stroke={mixC(C.mute, C.gold, hit)} strokeWidth={5} strokeLinecap="round" strokeDasharray="4 13" />}
        <circle cx={NEXT[0]} cy={NEXT[1]} r={13 * ring} fill={mixC(C.card, C.gold, hit)} stroke={C.gold} strokeWidth={4.5} />
        <text x={NEXT[0] - 16} y={BASE_Y + 34} textAnchor="middle" {...mono(17, C.gold)} opacity={sp(fr, LAND + 5, SOFT).v}>BULAN DEPAN</text>
      </g>
    </Draw>
  );
};

// Data blocks leave the need, stack beside the perch, are checked, then feed the eagle.
const STACK_X = P.perch.x - 135;
const CHEST: V = [P.perch.x - 20, P.perch.y - 150];
const HOP = 13, FEED = 14;
const slot = (j: number): V => [STACK_X, GROUND - 22 - 46 * j];
const fedAt = (j: number) => TRAIN + 5 * (BLOCKS - 1 - j) + FEED;

const Blocks: React.FC<BeatProps> = ({ fr }) => (
  <Draw>
    {Array.from({ length: BLOCKS }, (_, j) => {
      const s = STACK + 5 * j, [tx, ty] = slot(j);
      const p = sp(fr, s, { damping: 16, stiffness: 150 }).v, q = ramp(fr, fedAt(j) - FEED, fedAt(j));
      if (p <= 0.001 || q >= 1) return null;
      const rise = u01(p), x = lerp(lerp(SALES[0], tx, p), CHEST[0], q), y = lerp(lerp(SALES[1], ty, p) - 120 * Math.sin(Math.PI * rise), CHEST[1], q) - 70 * Math.sin(Math.PI * q);
      const [sx, sy] = sq(bounce(fr, s + HOP, 2, 3.5, 9));
      const k = Math.min(1, rise * 1.5) * (1 - 0.7 * q), ok = ramp(fr, CHECKED + 4 * j, CHECKED + 4 * j + 6);
      return (
        <g key={j} transform={`translate(${x} ${y}) scale(${k * sx} ${k * sy})`} opacity={1 - ramp(fr, fedAt(j) - 3, fedAt(j))}>
          <rect x={-59} y={-20} width={118} height={40} rx={10} fill={mixC(C.cream, C.goldLight, ok)} />
          {[-40, -8, 24].map((cx) => <rect key={cx} x={cx} y={-7} width={22} height={14} rx={5} fill={mixC(C.mute, C.goldDark, ok)} />)}
        </g>
      );
    })}
    <Check x={STACK_X + 62} y={GROUND - 46 * BLOCKS - 4} r={20} v={sp(fr, CHECKED).v * (1 - ramp(fr, TRAIN - 2, TRAIN + 8, depart))} />
  </Draw>
);

// The hunt: off the perch, up, a hang over the chart, then down onto next month's point.
const GAP = 14; // the talons hang this far above their mark through a hit-pause
const HUNT: V[] = [[P.perch.x, P.perch.y], [P.perch.x + 40, P.perch.y - 160], [NEXT[0] - 290, NEXT[1] - 135], [NEXT[0], NEXT[1] - GAP]];
const huntAt = (fr: number): V => {
  const u = 0.5 * ramp(fr, LAUNCH, DIVE, Easing.out(Easing.cubic)) + 0.5 * ramp(fr, DIVE, LAND - HIT, Easing.in(Easing.quad));
  const back = hump(fr, DIVE - 9, DIVE - 1, DIVE + 3), [x, y] = bez(HUNT, u);
  return [x - 10 * back, y - 12 * back];
};

/** The one eagle through beat 5 and up to the split in beat 6. */
const hunter = (fr: number) => {
  const [x, y] = huntAt(fr);
  const dyn = lean(vel2(huntAt, Math.min(fr, LAND - HIT - 1)));
  const air = fr >= LAUNCH ? 1 - ramp(fr, LAND, LAND + 3) : 0;
  const fed = Array.from({ length: BLOCKS }, (_, j) => bounce(fr, fedAt(j), 1.6, 4, 8)).reduce((a, b) => a + b, 0);
  return {
    x, y: y + (fr >= LAND ? GAP : 0), scale: HOME.eagle.scale, idle: paused(fr, LAUNCH, LAND, SPLIT) ? 0 : 1,
    fly: ramp(fr, LAUNCH, LAUNCH + 1, line) * (1 - ramp(fr, LAND - 1, LAND, line)),
    flap: (1 - 0.6 * ramp(fr, LAUNCH + 14, LAUNCH + 26)) * (1 - ramp(fr, DIVE - 2, DIVE + 3)),
    squash: crouch(fr, LAUNCH, 0.16) + (fr >= LAND ? crouch(fr, SPLIT, 0.16) : 0) + air * dyn.squash + fed + bounce(fr, LAND, 4.5, 3.5, 7),
    tilt: air * dyn.tilt - 9 * hump(fr, DIVE - 9, DIVE - 1, DIVE + 3),
  };
};

const Pile: React.FC<BeatProps & { opacity?: number }> = ({ fr, opacity = 1 }) => (
  <div style={{ opacity }}>
    <GpuPile x={PILE_X} y={GROUND} count={6} fr={fr} start={COST} seed="eagle" />
    <Label text="GPU kecil" x={PILE_X} y={GROUND + 56} size={22} fr={fr} start={COST + 26} />
  </div>
);

export const Beat05: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Column fr={fr} />
    <Residents t={fr} hide={["ants", "eagle"]} />
    <Chart fr={fr} />
    <Pile fr={fr} />
    <Burst fr={fr} E={ASK} seed="ask" n={8} x={SALES[0]} y={GROUND - 6} arc={[195, 345]} colors={[C.mute, C.line]} speed={[260, 520]} />
    <NeedBlob sim={sales} fr={fr} label="Penjualan bulan depan" />
    <Blocks fr={fr} />
    <Flash fr={fr} E={fedAt(0)} x={CHEST[0]} y={CHEST[1]} r={190} color={C.gold} amp={0.35} />
    <Eagle {...hunter(fr)} t={fr} />
    <Flash fr={fr} E={LAND} x={NEXT[0]} y={NEXT[1]} r={210} color={C.gold} />
    <Burst fr={fr} E={LAND} seed="land" n={9} x={NEXT[0]} y={NEXT[1]} colors={[C.gold, C.goldLight, C.cream]} speed={[200, 420]} size={[6, 12]} />
  </>
);

// ======================= Beat 6: four specialists =======================

const CATCH = [at(6, "memprediksi"), at(6, "menandai"), at(6, "skor"), at(6, "melihat")];
const REGROUP = at(6, "produk");
// Each set leaves once its catch has been held, and the next one waits for the spot to clear.
const EXIT = CATCH.map((e, i) => (i < 3 ? Math.max(e + 22, CATCH[i + 1] - 60) : REGROUP - 34));
const SET_IN = CATCH.map((e, i) => (i ? Math.max(e - 36, EXIT[i - 1] + 10) : e - 36));
const RET = 22;

const SX = P.perch.x + 600; // where every catch is staged
const GRAB: V[] = [[SX, GROUND - 136], [SX, GROUND - 80], [SX, GROUND - 163], [SX, GROUND - 116]];
const RISE = [34, 34, 0, 34]; // how far a caught thing is lifted; the dial is landed on instead
const SET_LABEL = ["Permintaan besok", "Transaksi janggal", "Skor risiko", "Cacat produk"];

const HOVER: V[] = [[-410, -255], [-110, -285], [190, -255], [490, -285]].map(([dx, dy]) => [P.perch.x + dx, P.perch.y + dy]);
const SMALL = 0.45, NEAR = 0.62;
const SWOOP = [18, 16, 14, 12];
const FAN = { damping: 18, stiffness: 140 };
const fanAt = (i: number) => SPLIT + 4 * (3 - i); // the nearest leaves first
const landAt = (i: number) => REGROUP + 5 * [1, 0, 2, 3][i]; // the one above the perch lands first, the rest fold into it
const HOMER = 1;
const CALM = B[6].until - 1;

const flockXY = (i: number, fr: number, gap = true): V => {
  const E = CATCH[i], [kx, ky] = GRAB[i], go = E - HIT - SWOOP[i], out = EXIT[i] + 4;
  const p = sp(fr, fanAt(i), FAN).v;
  const hx = HOVER[i][0] + 7 * Math.sin(fr / 47 + i * 1.9), hy = HOVER[i][1] + 5 * Math.sin(fr / 31 + i * 2.7);
  let x = lerp(NEXT[0], hx, p), y = lerp(NEXT[1], hy, p) - 15 * Math.sin(Math.PI * u01(p));
  // Drop first, then skim: the stoop passes under the others.
  const w = ramp(fr, go, E - HIT, Easing.in(Easing.quad)) - ramp(fr, out, out + RET);
  const back = hump(fr, go - 9, go - 1, go + 3);
  const held = 1 - ramp(fr, out, out + RET);
  const ty = ky - (gap && fr < E ? GAP : 0) - RISE[i] * settle((fr - E) / FPS) * held;
  x = lerp(x, kx, Math.pow(w, 1.8)) - 22 * back;
  y = lerp(y, ty, 1 - Math.pow(1 - w, 1.8)) - 12 * back;
  const q = ramp(fr, landAt(i) - 18, landAt(i));
  return [lerp(x, P.perch.x, q), lerp(y, P.perch.y, q) - 46 * Math.sin(Math.PI * q)];
};

const flockAt = (i: number, fr: number) => {
  const E = CATCH[i], go = E - HIT - SWOOP[i], out = EXIT[i] + 4, fan = fanAt(i), land = landAt(i), home = i === HOMER;
  const [x, y] = flockXY(i, fr);
  const dyn = lean(vel2((q) => flockXY(i, q, false), paused(fr, E) ? E - HIT - 1 : fr));
  const w = ramp(fr, go, E - HIT, Easing.in(Easing.quad)) - ramp(fr, out, out + RET);
  const q = ramp(fr, land - 18, land);
  const busy = Math.max(1 - ramp(fr, fan + 10, fan + 24), ramp(fr, go - 6, go) * (1 - ramp(fr, out + RET - 4, out + RET + 8)), ramp(fr, land - 20, land - 14));
  const folds = home ? [0, 2, 3].reduce((a, j) => a + bounce(fr, landAt(j), 1.4, 4, 9), bounce(fr, land, 4.5, 3.5, 7)) : 0;
  const leftward = ramp(fr, out - 1, out + 4) - ramp(fr, out + RET - 5, out + RET) + (HOVER[i][0] > P.perch.x ? ramp(fr, land - 19, land - 14) : 0);
  return {
    x, y, idle: paused(fr, E) ? 0 : 1,
    scale: lerp(lerp(lerp(HOME.eagle.scale, SMALL, u01(sp(fr, fan, FAN).v)), NEAR, w), home ? HOME.eagle.scale : 0.6, q),
    fly: home ? 1 - ramp(fr, land - 1, land, line) : 1,
    flap: lerp(0.35, 0.85, busy) * (1 - hump(fr, E - HIT - 6, E - HIT - 1, E + 4)),
    squash: dyn.squash + bounce(fr, E, 3, 3.5, 7) + folds * (1 - ramp(fr, CALM - 9, CALM)),
    tilt: dyn.tilt - 8 * hump(fr, go - 9, go - 1, go + 3),
    opacity: fr < fan ? 0 : home ? 1 : 1 - ramp(fr, land - 4, land),
    face: (-1 + 2 * ramp(fr, fan + 16, fan + 22)) * (1 - 2 * u01(leftward)),
  };
};

/** What a set's parts need: staggered arrival, eased exit, and the caught thing's gold, lift and squash. */
const stage = (i: number, fr: number) => ({
  pop: (j: number, gap = 5) => sp(fr, SET_IN[i] + gap * j).v,
  gone: ramp(fr, EXIT[i], EXIT[i] + 12, depart),
  gold: ramp(fr, CATCH[i], CATCH[i] + 4),
  lift: RISE[i] * settle((fr - CATCH[i]) / FPS),
  grab: sq(bounce(fr, CATCH[i], 3, 3.5, 7)),
});
type Stage = ReturnType<typeof stage>;
type SetProps = { fr: number; s: Stage; i: number };

const Halo: React.FC<{ y: number; r: number; gold: number }> = ({ y, r, gold }) =>
  gold <= 0.01 ? null : <circle cx={0} cy={y} r={r} fill={C.gold} opacity={0.22 * gold} style={{ filter: `blur(${(r * 0.3).toFixed(0)}px)` }} />;

// A drink cup beside tomorrow's thermometer.
const Demand: React.FC<SetProps> = ({ fr, s, i }) => {
  const warm = 0.3 + 0.5 * sp(fr, SET_IN[i] + 5).v, cup = s.pop(2), [gx, gy] = s.grab;
  const body = mixC(C.cream, C.gold, s.gold), band = mixC(C.mute, C.goldDark, s.gold);
  return (
    <>
      <g transform={`translate(${SX - 200} ${GROUND}) scale(${s.pop(0)})`}>
        <rect x={-14} y={-240} width={28} height={206} rx={14} fill={C.card} stroke={C.mute} strokeWidth={5} />
        <circle cy={-30} r={28} fill={C.card} stroke={C.mute} strokeWidth={5} />
        <rect x={-6} y={-44 - 176 * warm} width={12} height={176 * warm + 16} rx={6} fill={C.coral} />
        <circle cy={-30} r={17} fill={C.coral} />
        {[-96, -136, -176, -216].map((y) => <line key={y} x1={24} y1={y} x2={38} y2={y} stroke={C.mute} strokeWidth={4} strokeLinecap="round" />)}
      </g>
      <g transform={`translate(${SX} ${GROUND - s.lift}) scale(${cup * gx} ${cup * gy})`}>
        <Halo y={-66} r={96} gold={s.gold} />
        <line x1={16} y1={-126} x2={34} y2={-190} stroke={band} strokeWidth={9} strokeLinecap="round" />
        <path d="M -46 -118 L 46 -118 L 34 -8 Q 33 0 25 0 L -25 0 Q -33 0 -34 -8 Z" fill={body} />
        <path d="M -42 -82 L 42 -82 L 38 -44 L -38 -44 Z" fill={band} />
        <rect x={-53} y={-134} width={106} height={18} rx={8} fill={mixC(C.ink, C.goldLight, s.gold)} />
      </g>
    </>
  );
};

// A row of coins with one that does not belong.
const ODD = 3;
const Coins: React.FC<SetProps> = ({ fr, s, i }) => (
  <>
    {Array.from({ length: 5 }, (_, j) => {
      const odd = j === ODD, k = s.pop(j, 3);
      const [gx, gy] = odd ? s.grab : sq(bounce(fr, CATCH[i] + 3 * Math.abs(j - ODD), 1, 4, 9));
      return (
        <g key={j} transform={`translate(${SX + (j - ODD) * 92} ${GROUND - (odd ? s.lift : 0)}) scale(${k * gx} ${k * gy})`}>
          {odd && <Halo y={-40} r={62} gold={s.gold} />}
          <circle cy={-40} r={38} fill={odd ? mixC(C.mute, C.gold, s.gold) : C.cream} />
          <circle cy={-40} r={26} fill="none" stroke={odd ? mixC(C.coral, C.goldLight, s.gold) : C.mute} strokeWidth={5} strokeDasharray={odd ? "9 8" : undefined} />
          <rect x={-11} y={-45} width={22} height={10} rx={5} fill={odd ? mixC(C.coral, C.goldLight, s.gold) : C.mute} transform={odd ? "rotate(-32 0 -40)" : undefined} />
        </g>
      );
    })}
  </>
);

// A score dial: the needle hunts until the eagle lands on it, then settles.
const DIAL_R = 128, DIAL_Y = -22;
const Dial: React.FC<SetProps> = ({ fr, s, i }) => {
  const E = CATCH[i], [gx, gy] = s.grab, wait = Math.min(fr, E - HIT);
  const needle = lerp(-58 + 9 * Math.sin(wait / 6), 38, settle((fr - E) / FPS));
  const arc = (a0: number, a1: number) => {
    const p = (a: number) => `${(DIAL_R * Math.cos((a * Math.PI) / 180)).toFixed(1)} ${(DIAL_Y + DIAL_R * Math.sin((a * Math.PI) / 180)).toFixed(1)}`;
    return `M ${p(a0)} A ${DIAL_R} ${DIAL_R} 0 0 1 ${p(a1)}`;
  };
  return (
    <g transform={`translate(${SX} ${GROUND}) scale(${s.pop(0) * gx} ${s.pop(0) * gy})`}>
      <Halo y={-80} r={150} gold={s.gold} />
      {[[182, 236, C.line, 0.45], [242, 298, C.mute, 0.7], [304, 358, C.cream, 1]].map(([a0, a1, c, m], j) => (
        <path key={j} d={arc(a0 as number, a1 as number)} fill="none" stroke={mixC(c as string, C.gold, s.gold * (m as number))} strokeWidth={22} strokeLinecap="round" />
      ))}
      <rect x={-152} y={-22} width={304} height={22} rx={11} fill={C.line} />
      <g transform={`translate(0 ${DIAL_Y}) rotate(${needle}) scale(${s.pop(1)})`}>
        <path d="M -7 0 L 0 -98 L 7 0 Z" fill={C.ink} />
        <circle r={14} fill={C.ink} />
      </g>
    </g>
  );
};

// Parts on a small conveyor belt; the cracked one stops under the eagle.
const BELT = { x0: -300, x1: 240, top: -52 };
const Belt: React.FC<SetProps> = ({ fr, s, i }) => {
  const E = CATCH[i], [gx, gy] = s.grab;
  const ride = -160 * (1 - ramp(fr, SET_IN[i], E - HIT, Easing.out(Easing.cubic)));
  return (
    <>
      <g transform={`translate(${SX} ${GROUND}) scale(${s.pop(0)})`}>
        {[-230, 170].map((x) => <rect key={x} x={x - 7} y={-22} width={14} height={22} rx={5} fill={C.line} />)}
        <rect x={BELT.x0} y={BELT.top} width={BELT.x1 - BELT.x0} height={34} rx={17} fill={C.line} stroke={C.mute} strokeWidth={3} />
        {[-270, -150, -30, 90, 210].map((x) => (
          <g key={x} transform={`translate(${x} ${BELT.top + 17}) rotate(${(ride / 11) * (180 / Math.PI)})`}>
            <circle r={11} fill={C.card} stroke={C.mute} strokeWidth={3} />
            <line x1={-7} y1={0} x2={7} y2={0} stroke={C.mute} strokeWidth={3} strokeLinecap="round" />
          </g>
        ))}
      </g>
      {[-270, -135, 0, 135].map((dx, j) => {
        const flawed = dx === 0, x = dx + ride, k = s.pop(1) * ramp(x, BELT.x0 - 10, BELT.x0 + 50);
        const [px, py] = flawed ? [gx, gy] : [1, 1];
        return (
          <g key={j} transform={`translate(${SX + x} ${GROUND + BELT.top - (flawed ? s.lift : 0)}) scale(${k * px} ${k * py})`}>
            {flawed && <Halo y={-31} r={64} gold={s.gold} />}
            <path d={flawed ? "M -31 -10 Q -31 0 -21 0 H 21 Q 31 0 31 -10 V -40 L 9 -62 H -21 Q -31 -62 -31 -52 Z" : "M -31 -10 Q -31 0 -21 0 H 21 Q 31 0 31 -10 V -52 Q 31 -62 21 -62 H -21 Q -31 -62 -31 -52 Z"}
              fill={flawed ? mixC(C.cream, C.gold, s.gold) : C.cream} />
            <circle cy={-31} r={9} fill={flawed ? mixC(C.mute, C.goldDark, s.gold) : C.mute} />
            {flawed && <path d="M 20 -51 L 8 -40 L 16 -30 L 4 -17" fill="none" stroke={C.coral} strokeWidth={4.5} strokeLinecap="round" strokeLinejoin="round" />}
          </g>
        );
      })}
    </>
  );
};

const SETS = [Demand, Coins, Dial, Belt];

const Sets: React.FC<BeatProps> = ({ fr }) => (
  <Draw>
    {SETS.map((Set, i) => {
      if (fr < SET_IN[i] || fr >= EXIT[i] + 12) return null;
      const s = stage(i, fr);
      return (
        <g key={i} opacity={1 - s.gone} transform={`translate(0 ${16 * s.gone})`}>
          <Set fr={fr} s={s} i={i} />
          <text x={SX - 30} y={GROUND + 64} textAnchor="middle" {...mono(23, C.mute)} opacity={sp(fr, SET_IN[i] + 14, SOFT).v}>{SET_LABEL[i].toUpperCase()}</text>
        </g>
      );
    })}
    {CATCH.map((E, i) => {
      const u = ramp(fr, E, E + 14, Easing.out(Easing.cubic));
      return fr >= E && u < 1 ? <circle key={i} cx={GRAB[i][0]} cy={GRAB[i][1] + 40} r={40 + 110 * u} fill="none" stroke={C.gold} strokeWidth={6 * (1 - u)} opacity={1 - u} /> : null;
    })}
  </Draw>
);

export const Beat06: React.FC<BeatProps> = ({ fr }) => {
  const note = 0.75 * sp(fr, SPLIT + 40, SOFT).v * (1 - ramp(fr, REGROUP - 20, REGROUP - 6));
  return (
    <>
      <Residents t={fr} hide={["eagle"]} />
      <Chart fr={fr} />
      <Pile fr={fr} opacity={1 - ramp(fr, REGROUP + 6, REGROUP + 20, depart)} />
      <NeedBlob sim={sales} fr={fr} label="Penjualan bulan depan" opacity={1 - ramp(fr, SPLIT + 18, SPLIT + 32, depart)} />
      <Sets fr={fr} />
      {fr < SPLIT && <Eagle {...hunter(fr)} t={fr} />}
      {fr >= SPLIT && [0, 2, 3, HOMER].map((i) => {
        const { face, ...e } = flockAt(i, fr);
        return <Turn key={i} x={e.x} face={face}><Eagle {...e} t={fr} seed={i === HOMER ? 0 : i + 1} /></Turn>;
      })}
      <Flash fr={fr} E={SPLIT} x={NEXT[0]} y={NEXT[1] - 120} r={260} color={C.gold} />
      <Burst fr={fr} E={SPLIT} seed="split" n={10} x={NEXT[0]} y={NEXT[1] - 120} colors={[C.gold, C.goldLight, C.cream]} speed={[220, 460]} size={[6, 12]} />
      {CATCH.map((E, i) => (
        <React.Fragment key={i}>
          <Flash fr={fr} E={E} x={GRAB[i][0]} y={GRAB[i][1] + 40} r={170} color={C.gold} amp={0.55} />
          <Burst fr={fr} E={E} seed={`catch${i}`} n={7} x={GRAB[i][0]} y={GRAB[i][1] + 30} colors={[C.gold, C.goldLight]} speed={[160, 340]} size={[5, 10]} life={1.2} />
        </React.Fragment>
      ))}
      <div style={{ position: "absolute", left: P.perch.x + 1010, top: P.perch.y - 450, transform: "translate(-100%, -50%)", opacity: note, fontFamily: FONT, fontWeight: 500, fontSize: 22, color: C.mute, whiteSpace: "nowrap" }}>
        Contoh lengkap: hamra.ai/intro
      </div>
    </>
  );
};

// ---------- Camera ----------

// Small downward nudges on the impacts: the gulp, the landing, each catch.
const KNOCKS: V[] = [[EAT + 4, 60], [LAND, 150], [SPLIT, 110], ...CATCH.map((e): V => [e, 90])];

/** Camera nudge in screen px for beats 4–6, added to the camera by AiPas. */
export const nudgeB = (fr: number): [number, number] => [0, KNOCKS.reduce((a, [e, v]) => a + bounce(fr, e, v, 5, 12), 0)];
