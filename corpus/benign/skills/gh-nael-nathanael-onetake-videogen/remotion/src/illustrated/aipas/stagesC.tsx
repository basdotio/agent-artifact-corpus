// Beats 7–9: the owl on its branch, the whale in the sea, the four piles of GPU.
// Each beat is drawn in world coordinates (kit: P, HOME, SHOT) and receives the composition frame.
import React from "react";
import { Easing, random } from "remotion";
import {
  Ant, at, B, BeatProps, bounce, Burst, C, depart, Draw, Eagle, Flash, FONT, FPS, GPU_CAP, GpuCube, GROUND, HIT, HOME, Label, lerp, mixC, MONO,
  Owl, P, pileLayout, punch, ramp, Residents, SEA, settle, sp, stretchBy, vel2, Whale,
} from "./kit";

const TAU = 2 * Math.PI;
const u01 = (v: number) => Math.max(0, Math.min(1, v));
// Area-preserving scale pair, as the kit's actors use: s > 0 flattens, s < 0 stretches.
const sq = (s: number): [number, number] => (s >= 0 ? [1 + s, 1 / (1 + s)] : [1 / (1 - s), 1 - s]);
/** The crouch before an event on frame E: flattens to `amt` over `wind` frames, holds for the hit-pause, lets go on E. */
const crouch = (fr: number, E: number, amt: number, wind = 8) => (fr >= E ? 0 : amt * ramp(fr, E - HIT - wind, E - HIT));
/** A small hop off the spot on frame E: crouch, a ballistic rise of `h`, a landing squash. */
const HOP = 10;
const hopAt = (fr: number, E: number, h: number) => {
  const u = (fr - E) / HOP, air = u > 0 && u < 1 ? 4 * u * (1 - u) : 0;
  return { lift: h * air, squash: crouch(fr, E, 0.08, 4) - 0.06 * air + bounce(fr, E + HOP, 1.6, 4, 10) };
};

// ---------- GPU heap ----------

const FALL = 7;
type Pt = { x: number; y: number };

/**
 * A heap of GPU cubes like the kit's GpuPile, with both ends timed: `drop` lands it bottom row first within
 * `span` frames (plus the last cube's fall), `pour` sends it off top first, each cube on an arc to a point.
 */
const Heap: React.FC<{
  x: number; y: number; count: number; fr: number; size?: number; seed?: string; opacity?: number;
  drop?: { at: number; span: number }; pour?: { at: number; span: number; flight: number; to: Pt };
}> = ({ x, y, count, fr, size = 30, seed = "pile", opacity = 1, drop, pour }) => {
  const id = "h" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
  const { cubes, width, height } = pileLayout(count, size, seed), n = cubes.length;
  let here = 0;
  const drawn = cubes.map((c, i) => {
    const s0 = drop ? drop.at + (i * drop.span) / n : -1e6;
    if (fr < s0) return null;
    const px = x + c.x, py = y + c.y;
    const leave = pour ? pour.at + ((n - 1 - i) * pour.span) / n : 1e9;
    if (pour && fr >= leave) {
      const u = (fr - leave) / pour.flight;
      if (u >= 1) return null;
      const e = Math.pow(u, 1.3), arc = (60 + 50 * random(`${seed}arc${i}`)) * 4 * e * (1 - e);
      return <GpuCube key={i} x={lerp(px, pour.to.x, e)} y={lerp(py, pour.to.y, e) - arc} size={size * lerp(1, 0.7, ramp(u, 0.6, 1))} glow={0} />;
    }
    here++;
    const u = ramp(fr, s0, s0 + FALL, Easing.in(Easing.quad));
    return <GpuCube key={i} x={px} y={py - (1 - u) * size * 4} size={size} squash={bounce(fr, s0 + FALL, 2.4, 3.5, 9)} glow={0} opacity={Math.min(1, (fr - s0) / 2)} />;
  });
  if (!here && drawn.every((d) => !d)) return null;
  return (
    <div style={{ opacity }}>
      <Draw>
        <defs>
          <radialGradient id={id}><stop offset="0%" stopColor={C.gold} stopOpacity={1} /><stop offset="100%" stopColor={C.gold} stopOpacity={0} /></radialGradient>
        </defs>
        <ellipse cx={x} cy={y - height * 0.45} rx={width * 0.6 + size * 1.2} ry={height * 0.6 + size * 1.2} fill={`url(#${id})`} opacity={(0.34 * here) / n} style={{ mixBlendMode: "screen" }} />
      </Draw>
      {drawn}
    </div>
  );
};
const heapTop = (count: number, size: number) => pileLayout(count, size).height;

// ---------- Beat 7: the owl sorts three complaints ----------

const RISE = at(7, "Memilah");
const DROP = at(7, "keluhan");
const NAMED = at(7, "tanpa");
const READ = at(7, "kalimat");
const CLEAR = at(7, "Cukup");
// One note per word, the one nearest the owl first.
const SORT = [at(7, "kecil"), at(7, "hantu"), at(7, "burung")];
const TOSS = 13;
const SORTED = SORT[0] + TOSS;
const FEED7 = at(7, "model");
const QWEN = at(7, "ringan");

const NOTE_W = 116, NOTE_H = 146, TRAY_W = 200, TRAY_H = 66, IN_TRAY = 0.86;
const PAPER = mixC(C.ink, C.cream, 0.45), PAPER_FOLD = mixC(C.cream, C.ground, 0.28);
const TEXT_LINE = mixC(C.mute, C.ground, 0.3), READ_LINE = mixC(C.sky, C.ground, 0.38);
const TRAYS = ["Tagihan", "Pengiriman", "Layanan"].map((label, i) => ({ label, x: P.branch.x - 580 + 230 * i }));
const NOTES = [[0.8, 0.55, 0.7], [0.7, 0.9], [0.6, 0.85, 0.45]].map((lines, i) => ({
  lines, x: P.branch.x - 700 + 170 * i, y: P.branch.y - 200 + [0, -22, 8][i], rot: [-5, 3, -3][i], rest: [3, -4, 2][i],
}));
const OWL_HEAP = { x: P.branch.x + 430, y: GROUND, count: 21, size: 30, seed: "owl", drop: { at: FEED7, span: 6 } };

// A note's whole life: flutter down like a leaf, hover, pull back, an arc into its tray, a landing dip.
const noteAt = (i: number, fr: number) => {
  const n = NOTES[i], s = DROP + 5 * i, E = SORT[i], t = fr / FPS;
  const fall = ramp(fr, s, s + 26, Easing.out(Easing.cubic)), rock = 1 - fall, ph = TAU * 1.2 * ((fr - s) / FPS) + i * 2;
  const back = ramp(fr, E - HIT - 6, E - HIT), u = ramp(fr, E, E + TOSS, Easing.in(Easing.quad)), air = Math.sin(Math.PI * u);
  const idle = 1 - u;
  const x0 = n.x + 80 * rock * Math.sin(ph) - 14 * back;
  const y0 = n.y - 640 * rock + bounce(fr, s + 22, 260, 2.2, 6) + idle * 5 * Math.sin((TAU * t) / (4.1 + 0.7 * i) + i) - 26 * back;
  const rot0 = n.rot + 18 * rock * Math.cos(ph) + idle * 1.2 * Math.sin((TAU * t) / (5.3 + i) + i) - 8 * back;
  return {
    x: lerp(x0, TRAYS[i].x, u),
    y: lerp(y0, GROUND - 36 - (NOTE_H * IN_TRAY) / 2, u) - 70 * air + bounce(fr, E + TOSS, 200, 3.5, 9),
    rot: lerp(rot0, n.rest, u) + 22 * air,
    k: lerp(1, IN_TRAY, u),
    squash: -0.1 * air + bounce(fr, E + TOSS, 2, 4, 10),
    opacity: u01((fr - s) / 3),
  };
};

const Note: React.FC<{ i: number; fr: number }> = ({ i, fr }) => {
  const a = noteAt(i, fr);
  if (a.opacity <= 0) return null;
  const [sx, sy] = sq(a.squash), w = NOTE_W / 2, h = NOTE_H / 2, ear = 26, r = 10;
  return (
    <g transform={`translate(${a.x} ${a.y}) rotate(${a.rot}) scale(${a.k * sx} ${a.k * sy})`} opacity={a.opacity}>
      <path d={`M ${-w + r} ${-h} H ${w - ear} L ${w} ${-h + ear} V ${h - r} Q ${w} ${h} ${w - r} ${h} H ${-w + r} Q ${-w} ${h} ${-w} ${h - r} V ${-h + r} Q ${-w} ${-h} ${-w + r} ${-h} Z`} fill={PAPER} />
      <path d={`M ${w - ear} ${-h} L ${w} ${-h + ear} H ${w - ear} Z`} fill={PAPER_FOLD} />
      <circle cx={-w + 24} cy={-h + 26} r={9} fill={C.coral} />
      {NOTES[i].lines.map((len, j) => {
        // Read left to right, note by note and line by line.
        const full = (NOTE_W - 36) * len, lit = ramp(fr, READ + 3 + 5 * i + 2 * j, READ + 8 + 5 * i + 2 * j);
        return (
          <g key={j}>
            <rect x={-w + 18} y={-h + 50 + 26 * j} width={full} height={10} rx={5} fill={TEXT_LINE} />
            {lit > 0.05 && <rect x={-w + 18} y={-h + 50 + 26 * j} width={full * lit} height={10} rx={5} fill={READ_LINE} />}
          </g>
        );
      })}
    </g>
  );
};

// A tray in two halves, so a note can sit between its back and its front.
const Tray: React.FC<{ i: number; fr: number; front?: boolean }> = ({ i, fr, front }) => {
  const v = sp(fr, RISE + 5 * i).v, land = SORT[i] + TOSS;
  if (v <= 0.001) return null;
  const [sx, sy] = sq(bounce(fr, land, 1.5, 4, 10)), lit = ramp(fr, land, land + 6), w = TRAY_W, h = TRAY_H;
  return (
    <g transform={`translate(${TRAYS[i].x} ${GROUND}) scale(${(0.86 + 0.14 * v) * sx} ${v * sy})`}>
      {!front && <rect x={-w / 2 + 10} y={-h - 16} width={w - 20} height={h + 16} rx={10} fill={mixC(C.wood, C.ground, 0.5)} />}
      {front && (
        <>
          <rect x={-w / 2} y={-h} width={w} height={h} rx={12} fill={C.wood} />
          <rect x={-w / 2} y={-h} width={w} height={8} rx={4} fill={mixC(C.woodLight, C.sky, 0.6 * lit)} />
          <text x={0} y={-h / 2 + 12} textAnchor="middle" fontFamily={MONO} fontWeight={500} fontSize={22} letterSpacing="0.06em" fill={mixC(C.cream, C.sky, lit)}>
            {TRAYS[i].label.toUpperCase()}
          </text>
        </>
      )}
    </g>
  );
};

/** Everything of beat 7 but the owl. Beat 8 draws it too, at rest, until the camera has left it behind. */
const Stage07: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Draw>
      {TRAYS.map((_, i) => <Tray key={i} i={i} fr={fr} />)}
      {NOTES.map((_, i) => <Note key={i} i={i} fr={fr} />)}
      {TRAYS.map((_, i) => <Tray key={i} i={i} fr={fr} front />)}
    </Draw>
    <div style={{ opacity: 1 - ramp(fr, CLEAR, CLEAR + 10, depart) }}>
      <Label text="Keluhan pelanggan" x={NOTES[1].x} y={NOTES[1].y - NOTE_H / 2 - 44} size={22} fr={fr} start={NAMED} />
    </div>
    <Burst fr={fr} E={SORTED} seed="sorted" n={8} x={TRAYS[0].x} y={GROUND - TRAY_H - 70} arc={[200, 340]} colors={[C.sky, C.ink]} speed={[160, 340]} size={[6, 11]} />
    <Heap {...OWL_HEAP} fr={fr} />
    <Label text="GPU menengah" x={OWL_HEAP.x} y={GROUND - heapTop(OWL_HEAP.count, OWL_HEAP.size) - 44} size={22} color={C.gold} fr={fr} start={FEED7 + OWL_HEAP.drop.span + FALL + 4} />
    <Label text="contoh: Qwen versi ringan" x={P.branch.x - 60} y={P.branch.y + 62} size={22} fr={fr} start={QWEN} />
  </>
);

// The owl's performance: still for the read, a blink on cue, a head tilt, one flick per note.
const owlAt = (fr: number) => {
  const still = ramp(fr, READ - HIT - 14, READ - HIT - 4) * (1 - ramp(fr, READ + 22, READ + 38));
  return {
    idle: 1 - still,
    lid: ramp(fr, READ - HIT - 3, READ - HIT) * (1 - ramp(fr, READ, READ + 3)) + Math.sin(Math.PI * u01((fr - READ - 11) / 6)),
    tilt: -9 * punch(fr, READ, 10, 0.2) * (1 - settle((fr - SORTED) / FPS)) - SORT.reduce((a, E) => a + bounce(fr, E, 70, 3, 7), 0),
    squash: crouch(fr, READ, 0.05, 10) - bounce(fr, READ, 1.4, 3.5, 8) - bounce(fr, SORTED, 1.2, 3, 7)
      + SORT.reduce((a, E) => a + crouch(fr, E, 0.035, 4) - bounce(fr, E, 0.9, 4, 9), 0),
  };
};

// The owl crop's size, anchor and eye boxes as in the kit's art table: the kit blinks only on its own clock.
const OWL_ART = { w: 376, h: 460, ax: 0.513, ay: 0.965, lid: "#fdedc4", eyes: [[146, 110, 200, 158], [257, 111, 305, 158]] };
/** Eyelids for a blink on cue, laid over the owl at home. They line up only while the owl's `idle` is 0. */
const OwlLids: React.FC<{ close: number; tilt: number; squash: number }> = ({ close, tilt, squash }) => {
  if (close <= 0.03) return null;
  const { w, h, ax, ay } = OWL_ART, [sx, sy] = sq(squash), k = HOME.owl.scale;
  return (
    <div style={{
      position: "absolute", left: HOME.owl.x - w * ax, top: HOME.owl.y - h * ay, width: w, height: h,
      transformOrigin: `${ax * 100}% ${ay * 100}%`, transform: `rotate(${tilt}deg) scale(${k * sx}, ${k * sy})`,
    }}>
      {OWL_ART.eyes.map(([x0, y0, x1, y1], i) => (
        <div key={i} style={{ position: "absolute", left: x0 - 3, top: y0 - 3, width: x1 - x0 + 6, height: (y1 - y0 + 6) * 0.86 * Math.min(1, close), overflow: "hidden" }}>
          <div style={{ width: x1 - x0 + 6, height: y1 - y0 + 6, borderRadius: "50%", background: OWL_ART.lid }} />
        </div>
      ))}
    </div>
  );
};

export const Beat07: React.FC<BeatProps> = ({ fr }) => {
  const o = owlAt(fr);
  return (
    <>
      <Residents t={fr} hide={["owl"]} />
      <Owl {...HOME.owl} t={fr} tilt={o.tilt} squash={o.squash} idle={o.idle} />
      <OwlLids close={o.lid} tilt={o.tilt} squash={o.squash} />
      <Stage07 fr={fr} />
    </>
  );
};

// ---------- Beat 8: the whale answers everyone and eats the mountain ----------

const RAIN = at(8, "apa");
const STAFF = at(8, "semua");
const BREACH = at(8, "paus");
const SPOUT = BREACH + 6;
const MOUNT = at(8, "besar");
const EAT = at(8, "GPU");
const POUR = 26, GULP = 12;
const FULL = EAT + POUR + GULP;

const DEEP = 600;
const HEAD_UP = 7;
// The whale's blowhole at home, measured from its anchor.
const BLOW = { x: HOME.whale.x - 250, y: HOME.whale.y - 85 };
const turned = (dx: number, dy: number, deg: number): Pt => {
  const a = (deg * Math.PI) / 180;
  return { x: HOME.whale.x + dx * Math.cos(a) - dy * Math.sin(a), y: HOME.whale.y + dx * Math.sin(a) + dy * Math.cos(a) };
};
// A little way inside the head: the cubes are painted behind the whale, so they vanish at its lips.
const MOUTH = turned(-465, -34, HEAD_UP);
const SPOUT_H = 240;
const WAVE = 46;
const ANSWER = { x: BLOW.x, y: BLOW.y - SPOUT_H };

const whaleY = (fr: number) => HOME.whale.y + DEEP * (1 - punch(fr, BREACH, 12, 0.07));
// Under the sea until "paus", a breach with one overshoot, then head up for the pour and a squash per gulp.
const whaleAt = (fr: number) => {
  const [, vy] = vel2((q) => [0, whaleY(q)], fr);
  const hold = (E: number) => ramp(fr, E - HIT - 6, E - HIT) * (1 - ramp(fr, E, E + 6));
  const gulps = [0, 1, 2, 3, 4].reduce((a, k) => a + bounce(fr, EAT + GULP + 6 * k, 0.8, 4, 9), 0);
  return {
    y: whaleY(fr),
    tilt: bounce(fr, BREACH, 150, 1.6, 4.5) + HEAD_UP * punch(fr, EAT, 12, 0.2) * (1 - settle((fr - FULL) / FPS)),
    squash: stretchBy(vy, 1 / 30000, 0.12) + bounce(fr, BREACH + 7, 0.9, 2.6, 6) + gulps + bounce(fr, FULL, 1.2, 2.5, 6),
    swim: ramp(fr, BREACH, BREACH + 4) * (1 - ramp(fr, BREACH + 10, BREACH + 34)),
    idle: 1 - hold(BREACH) - hold(EAT),
  };
};

const ASKS = ["?", "doc", "?", "bars", "mail", "?", "clock"];
const ASK_COLORS = [C.cream, C.sky, C.coral, C.mute];
// Offsets from the whale's home on the waterline: clear of its back, its tail, the spout and the cubes' arc.
const BUBBLES = ([
  [-900, -540, 40], [-870, -830, 44], [-740, -640, 58], [-610, -500, 46], [-580, -890, 56], [-420, -510, 36], [-440, -690, 46], [-270, -840, 40],
  [-90, -670, 54], [20, -900, 50], [-20, -560, 44], [150, -710, 40], [320, -840, 60], [520, -740, 38], [620, -890, 42],
] as const).map(([dx, dy, r], i, all) => {
  const x = P.sea.x + dx, y = P.sea.y + dy;
  return {
    x, y, r, ask: ASKS[i % ASKS.length], color: ASK_COLORS[(i * 3) % ASK_COLORS.length],
    start: RAIN + 1.5 * ((i * 7) % all.length), told: SPOUT + 4 + Math.hypot(x - ANSWER.x, y - ANSWER.y) / WAVE,
  };
});
const RAIN_SPRING = { damping: 13, stiffness: 80 };

const Ask: React.FC<{ kind: string; r: number }> = ({ kind, r }) => {
  const line = { fill: "none", stroke: C.ground, strokeWidth: r * 0.13, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  if (kind === "doc") return <>{[0.9, 0.9, 0.55].map((len, j) => <rect key={j} x={-0.45 * r} y={(-0.4 + 0.3 * j) * r} width={len * r} height={0.16 * r} rx={0.08 * r} fill={C.ground} />)}</>;
  if (kind === "bars") return <>{[0.35, 0.6, 0.85].map((v, j) => <rect key={j} x={(-0.42 + 0.32 * j) * r} y={(0.42 - v) * r} width={0.2 * r} height={v * r} rx={0.05 * r} fill={C.ground} />)}</>;
  if (kind === "mail") return <g {...line}><rect x={-0.5 * r} y={-0.34 * r} width={r} height={0.68 * r} rx={0.08 * r} /><path d={`M ${-0.5 * r} ${-0.28 * r} L 0 ${0.08 * r} L ${0.5 * r} ${-0.28 * r}`} /></g>;
  if (kind === "clock") return <g {...line}><circle r={0.5 * r} /><path d={`M 0 ${-0.3 * r} V 0 L ${0.22 * r} ${0.1 * r}`} /></g>;
  return <text y={r * 0.4} textAnchor="middle" fontFamily={FONT} fontWeight={700} fontSize={r * 1.15} fill={C.ground}>?</text>;
};

/** A question bubble: rains in on its own frame, bobs, and turns to a gold tick when the answer wave reaches it. */
const Bubble: React.FC<{ i: number; fr: number; out: number }> = ({ i, fr, out }) => {
  const b = BUBBLES[i], r = b.r;
  if (fr < b.start) return null;
  const path = (q: number): [number, number] => [b.x, b.y - 760 * (1 - sp(q, b.start, RAIN_SPRING).v)];
  const [x, y] = path(fr), [, vy] = vel2(path, fr);
  const [sx, sy] = sq(stretchBy(vy, 1 / 5000, 0.18)), told = ramp(fr, b.told, b.told + 6), k = 1 + bounce(fr, b.told, 2.4, 4, 9);
  const color = mixC(b.color, C.gold, told), bob = 6 * Math.sin((TAU * fr) / FPS / (4.3 + 0.37 * i) + i * 1.7);
  return (
    <g transform={`translate(${x} ${y + bob - 70 * out}) scale(${k * sx} ${k * sy})`} opacity={1 - out}>
      {told > 0.01 && <circle r={r * 1.5} fill={C.gold} opacity={0.22 * told} style={{ filter: `blur(${(r * 0.35).toFixed(1)}px)` }} />}
      <path d={`M ${-0.5 * r} ${0.72 * r} L ${-0.95 * r} ${1.15 * r} L ${-0.12 * r} ${0.93 * r} Z`} fill={color} />
      <circle r={r} fill={color} />
      <path d={`M ${-0.72 * r} ${-0.26 * r} A ${0.77 * r} ${0.77 * r} 0 0 1 ${-0.26 * r} ${-0.72 * r}`} fill="none" stroke={mixC(color, "#ffffff", 0.55)} strokeWidth={0.09 * r} strokeLinecap="round" />
      <g opacity={1 - told}><Ask kind={b.ask} r={r} /></g>
      <path d={`M ${-0.4 * r} ${0.02 * r} L ${-0.1 * r} ${0.32 * r} L ${0.44 * r} ${-0.3 * r}`} fill="none" stroke={C.ground} strokeWidth={0.17 * r} strokeLinecap="round" strokeLinejoin="round" opacity={told} />
    </g>
  );
};

const CREW = Array.from({ length: 9 }, (_, i) => ({
  x: P.shore.x - 85 + 54 * i, k: 0.9 + 0.25 * random(`crew${i}`), color: [C.cream, C.mute, mixC(C.cream, C.mute, 0.45)][i % 3],
}));
/** The employees: small round figures that pop up along the shore, and hop once they have their answers. */
const Crew: React.FC<{ fr: number; out: number }> = ({ fr, out }) => (
  <Draw>
    {CREW.map((p, i) => {
      const v = sp(fr, STAFF + 3 * i).v;
      if (v <= 0.001) return null;
      const hop = hopAt(fr, SPOUT + 24 + 3 * i, 18);
      const [sx, sy] = sq(hop.squash + 0.012 * Math.sin((TAU * fr) / FPS / (3.1 + 0.3 * i) + i));
      return (
        <g key={i} transform={`translate(${p.x} ${GROUND - hop.lift}) scale(${p.k * (0.8 + 0.2 * v) * sx} ${p.k * v * sy * (1 - out)})`}>
          <rect x={-17} y={-48} width={34} height={48} rx={15} fill={p.color} />
          <circle cy={-62} r={13} fill={C.skin} />
          <path d="M -13 -63 A 13 13 0 0 1 13 -63 Q 0 -71 -13 -63 Z" fill={C.hair} />
        </g>
      );
    })}
  </Draw>
);

const MOUNTAIN = { x: P.shore.x + 110, y: GROUND, count: GPU_CAP, size: 28, seed: "whale", drop: { at: MOUNT, span: 20 }, pour: { at: EAT, span: POUR, flight: GULP, to: MOUTH } };

/** Beat 8 behind the whale: the bulge and spout of the breach, the mountain and its pour, the crew in front of it. */
const Shore08: React.FC<{ fr: number; out?: number }> = ({ fr, out = 0 }) => {
  const bulge = ramp(fr, BREACH - HIT - 12, BREACH - HIT) * (1 - ramp(fr, BREACH, BREACH + 8));
  const jet = sp(fr, SPOUT).v, spray = 1 - ramp(fr, SPOUT + 20, SPOUT + 34, depart);
  const x = BLOW.x, y = BLOW.y + whaleY(fr) - HOME.whale.y, h = SPOUT_H * jet;
  return (
    <>
      <Draw>
        {bulge > 0.01 && <ellipse cx={HOME.whale.x - 80} cy={SEA + 4} rx={470} ry={30 * bulge} fill={C.sea} />}
        {jet > 0.001 && spray > 0.001 && (
          <g fill="none" stroke={C.sky} strokeLinecap="round" opacity={spray}>
            <path d={`M ${x} ${y} V ${y - h}`} strokeWidth={26} />
            {[-1, 1].map((sd) => <path key={sd} d={`M ${x} ${y - h * 0.6} C ${x} ${y - h * 1.05} ${x + sd * 34} ${y - h * 1.08} ${x + sd * 92 * jet} ${y - h * 0.8}`} strokeWidth={16} />)}
            <path d={`M ${x - 5} ${y - 8} V ${y - h * 0.9}`} stroke={C.ink} strokeWidth={6} opacity={0.5} />
          </g>
        )}
        {fr > SPOUT + 4 && <circle cx={ANSWER.x} cy={ANSWER.y} r={WAVE * (fr - SPOUT - 4)} fill="none" stroke={C.gold} strokeWidth={10} opacity={0.32 * (1 - ramp(fr, SPOUT + 4, SPOUT + 28))} />}
      </Draw>
      <Heap {...MOUNTAIN} fr={fr} />
      <div style={{ opacity: 1 - out }}>
        <Label text="GPU besar" x={MOUNTAIN.x} y={GROUND - heapTop(MOUNTAIN.count, MOUNTAIN.size) - 46} size={26} color={C.gold} fr={fr} start={MOUNT + 4} />
      </div>
      <Crew fr={fr} out={out} />
    </>
  );
};

/** Beat 8 in front of the whale: spray, the flash of the answer, the bubbles. */
const Sky08: React.FC<{ fr: number; out?: number }> = ({ fr, out = 0 }) => (
  <>
    <Burst fr={fr} E={BREACH} seed="breach" n={12} x={HOME.whale.x - 160} y={SEA} arc={[200, 340]} colors={[C.sky, C.ink, C.seaFront]} speed={[320, 720]} size={[8, 18]} life={0.8} />
    <Burst fr={fr} E={BREACH + 4} seed="tail" n={6} x={HOME.whale.x + 330} y={SEA} arc={[220, 320]} colors={[C.sky, C.seaFront]} speed={[240, 520]} size={[8, 15]} life={1.1} />
    <Burst fr={fr} E={SPOUT + 3} seed="spout" n={8} x={ANSWER.x} y={ANSWER.y} arc={[190, 350]} colors={[C.sky, C.ink]} speed={[200, 460]} size={[6, 13]} life={1.2} />
    <Flash fr={fr} E={SPOUT + 3} x={ANSWER.x} y={ANSWER.y} r={340} color={C.gold} amp={0.45} />
    <Draw>{BUBBLES.map((_, i) => <Bubble key={i} i={i} fr={fr} out={out} />)}</Draw>
  </>
);

export const Beat08: React.FC<BeatProps> = ({ fr }) => {
  const w = whaleAt(fr);
  return (
    <>
      <Residents t={fr} hide={["whale"]} />
      {fr < RAIN && <Stage07 fr={fr} />}
      <Shore08 fr={fr} />
      <Whale {...HOME.whale} y={w.y} t={fr} tilt={w.tilt} squash={w.squash} swim={w.swim} idle={w.idle} />
      <Sky08 fr={fr} />
    </>
  );
};

// ---------- Beat 9: four kinds, four piles ----------

const NOD = at(9, "empat", 1);
const FEED9 = at(9, "GPU-nya");
const SIZED = at(9, "ukurannya");
const SIZE_LABEL = 46;
// Crumb to mountain, beside each kind, sized for the wide shot. They start 6 frames apart and come to rest one
// after another, the mountain on "ukurannya".
const PILES = [
  { x: P.trail1.x - 170, count: 1, size: 60, seed: "ants", label: "GPU hampir nol" },
  { x: P.perch.x + 330, count: 6, size: 60, seed: "eagle", label: "GPU kecil" },
  { x: P.branch.x - 380, count: 21, size: 60, seed: "owl", label: "GPU menengah" },
  { x: P.shore.x - 140, count: GPU_CAP, size: 46, seed: "whale", label: "GPU besar" },
].map((p, i, all) => {
  const start = FEED9 + 6 * i, land = Math.round(lerp(FEED9 + FALL + 1, SIZED, i / (all.length - 1)));
  return { ...p, land, drop: { at: start, span: land - FALL - start } };
});

export const Beat09: React.FC<BeatProps> = ({ fr }) => {
  const out = ramp(fr, B[9].start, B[9].start + 16, depart);
  const w = whaleAt(fr), hops = [0, 1, 2, 3].map((k) => hopAt(fr, NOD + 4 * k, k ? 44 : 30));
  return (
    <>
      {HOME.ants.map((a, i) => {
        const h = hopAt(fr, NOD + i, 30);
        return <Ant key={a.seed} {...a} y={a.y - h.lift} squash={h.squash} t={fr} />;
      })}
      <Eagle {...HOME.eagle} y={HOME.eagle.y - hops[1].lift} squash={hops[1].squash} t={fr} />
      <Owl {...HOME.owl} y={HOME.owl.y - hops[2].lift} squash={hops[2].squash} t={fr} />
      {out < 1 && <Shore08 fr={fr} out={out} />}
      <Whale {...HOME.whale} y={w.y - hops[3].lift} t={fr} tilt={w.tilt} squash={w.squash + hops[3].squash} swim={w.swim} idle={w.idle} />
      {out < 1 && <Sky08 fr={fr} out={out} />}
      {PILES.map((p) => (
        <React.Fragment key={p.seed}>
          <Heap x={p.x} y={GROUND} count={p.count} size={p.size} seed={p.seed} drop={p.drop} fr={fr} />
          <Label text={p.label} x={p.x} y={GROUND + 84} size={SIZE_LABEL} color={C.gold} fr={fr} start={p.land + 4} />
        </React.Fragment>
      ))}
      <Flash fr={fr} E={SIZED} x={PILES[3].x} y={GROUND - 220} r={620} color={C.gold} amp={0.4} />
    </>
  );
};

/** Camera nudge in screen px for beats 7–9, added to the camera by AiPas: the last note, the breach, the mountains landing. */
export const nudgeC = (fr: number): [number, number] => [
  0,
  bounce(fr, SORTED, 35, 3, 8) - bounce(fr, BREACH, 80, 3, 7) + bounce(fr, MOUNT + MOUNTAIN.drop.span + FALL, 45, 3, 8) + bounce(fr, SIZED, 50, 3, 8),
];
