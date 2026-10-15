// Beats 14–15: your own server on the home shore, then the lockup.
// Each beat is drawn in world coordinates (kit: P, HOME, SHOT) and receives the composition frame.
import React from "react";
import { Easing, Img, staticFile } from "remotion";
import {
  Ant, arrive, at, B, BeatProps, bounce, Burst, C, decay, depart, Draw, Eagle, Flash, FONT, FPS, GpuCube, GROUND, HIT, HOME, Label, lerp,
  mixC, MONO, Owl, P, POP, ramp, Residents, SOFT, sp, Tag, vel2,
} from "./kit";

type V2 = [number, number];
const linear = (v: number) => v;
const u01 = (v: number) => Math.max(0, Math.min(1, v));
// Area-preserving scale pair: s > 0 flattens, s < 0 stretches.
const sq = (s: number): V2 => (s >= 0 ? [1 + s, 1 / (1 + s)] : [1 / (1 - s), 1 - s]);
// Stretch along a velocity (px/s), area kept.
const along = ([vx, vy]: V2, k = 1 / 9000, max = 0.2) => {
  const s = Math.min(max, Math.hypot(vx, vy) * k), dir = (Math.atan2(vy, vx) * 180) / Math.PI;
  return `rotate(${dir}) scale(${1 + s} ${1 / (1 + s)}) rotate(${-dir})`;
};
const quad = (a: V2, b: V2, c: V2, u: number): V2 => [
  (1 - u) * (1 - u) * a[0] + 2 * u * (1 - u) * b[0] + u * u * c[0], (1 - u) * (1 - u) * a[1] + 2 * u * (1 - u) * b[1] + u * u * c[1],
];
const cubic = (a: V2, b: V2, c: V2, d: V2, u: number): V2 => {
  const w = 1 - u, k = [w * w * w, 3 * w * w * u, 3 * w * u * u, u * u * u];
  return [k[0] * a[0] + k[1] * b[0] + k[2] * c[0] + k[3] * d[0], k[0] * a[1] + k[1] * b[1] + k[2] * c[1] + k[3] * d[1]];
};

// ---------- Timeline: every event on its spoken word ----------

const CLOUD_IN = at(14, "Claude");
const CHATGPT = at(14, "ChatGPT");
const FILE_IN = at(14, "Untuk");
const FILE_GO = at(14, "file");
const FILE_OK = at(14, "bisa");
const FILE_OUT = at(14, "Tapi");
const STREAM = at(14, "nasabah");
const BORDER = at(14, "luar");
const ABROAD = at(14, "negeri");
const RACK_IN = at(14, "memasang");
const RACK_WIND = at(14, "server", 1);
const PLANT = at(14, "sendiri");
const HOME_TAG = at(14, "Indonesia");
const SWELL = at(15, "AI");
const LOGO_IN = at(15, "Hamra");

// ---------- Abroad: the cloud server across the sea ----------

const CLOUD = { x: P.far.x - 60, y: P.far.y - 50 };
const BORDER_X = CLOUD.x - 290;
const SHORE_OUT: V2 = [P.shore.x + 210, GROUND - 100];

const fileLane = (u: number) => quad([SHORE_OUT[0], SHORE_OUT[1] - 20], [CLOUD.x - 940, -60], [CLOUD.x - 110, CLOUD.y + 10], u);
const FILE_BACK = 0.045;
const fileAt = (fr: number): V2 => {
  const pop = sp(fr, FILE_IN).v;
  const wind = ramp(fr, FILE_GO - HIT - 10, FILE_GO - HIT);
  const go = ramp(fr, FILE_GO, FILE_OK, Easing.bezier(0.3, 0, 0.25, 1));
  const [x, y] = fileLane(go - FILE_BACK * wind * (1 - go));
  return [x, y + (1 - pop) * 90 + (1 - go) * 6 * Math.sin(fr / 9)];
};

/** The one paper file: pops up on the shore, pulls back, holds, sails to the cloud and slips inside. */
const PaperFile: React.FC<BeatProps> = ({ fr }) => {
  const pop = sp(fr, FILE_IN).v, go = ramp(fr, FILE_GO, FILE_OK, linear);
  if (pop <= 0.001 || fr >= FILE_OK) return null;
  const [x, y] = fileAt(fr), v = vel2(fileAt, fr), free = ramp(fr, FILE_GO, FILE_GO + 3, linear);
  const wound = ramp(fr, FILE_GO - HIT - 10, FILE_GO - HIT) * (1 - free);
  const [sx, sy] = sq(0.12 * wound);
  const k = pop * (1 - 0.6 * ramp(go, 0.8, 1, linear));
  return (
    <Draw>
      <g transform={`translate(${x} ${y}) ${free > 0 ? along(v, 1 / 9000, 0.16) : ""} rotate(${16 * free * u01(Math.hypot(v[0], v[1]) / 900) - 10 * wound}) scale(${k * sx} ${k * sy})`}>
        <path d="M -42 -52 H 18 L 42 -28 V 52 H -42 Z" fill={C.ink} strokeLinejoin="round" stroke={C.ink} strokeWidth={8} />
        <path d="M 18 -52 V -28 H 42 Z" fill={C.mute} />
        {[-12, 8, 28].map((ly, i) => <rect key={i} x={-28} y={ly} width={i === 2 ? 34 : 56} height={8} rx={4} fill={C.mute} />)}
      </g>
    </Draw>
  );
};

// ---------- The stream of customer cards ----------

const N_CARDS = 13;
const EMIT_GAP = 12;
const TRAVEL = 120;
const EASE_OUT = 4;
const cardLane = (u: number) => quad(SHORE_OUT, [CLOUD.x - 910, 120], [CLOUD.x - 130, CLOUD.y + 10], u);

const RACK = { x: P.shore.x, w: 180, h: 250 };
const INLET: V2 = [RACK.x, GROUND - RACK.h + 14];

type Stream = { i: number; emit: number; turn: number; home: number; stop: V2; lead: V2 };
const outAt = (i: number, t: number): V2 => {
  const [x, y] = cardLane(u01((t - STREAM - i * EMIT_GAP) / TRAVEL));
  return [x, y + 7 * Math.sin(t / FPS * 1.3 + i * 1.9)];
};
// The nearest card turns and files in first; the ones already in the cloud come out last.
const CARDS: Stream[] = Array.from({ length: N_CARDS }, (_, i) => {
  const emit = STREAM + i * EMIT_GAP, back = N_CARDS - 1 - i;
  const turn = PLANT + back;
  const stop = outAt(i, turn + EASE_OUT);
  const u = Math.min(0.98, u01((turn + EASE_OUT - emit) / TRAVEL));
  const a = cardLane(u - 0.01), b = cardLane(u + 0.01), len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  return { i, emit, turn, home: PLANT + 11 + Math.round(back * 1.6), stop, lead: [stop[0] + ((b[0] - a[0]) / len) * 170, stop[1] + ((b[1] - a[1]) / len) * 170 - 40] };
});
const ABSORBED = CARDS.filter((c) => c.emit + TRAVEL < PLANT).map((c) => c.emit + TRAVEL);

const cardAt = (c: Stream, fr: number): V2 => {
  if (fr <= c.turn) return outAt(c.i, fr);
  // The outward drift dies away while the curl home takes over, so the turn has no corner.
  const o = outAt(c.i, c.turn + EASE_OUT * (1 - Math.exp(-(fr - c.turn) / EASE_OUT)));
  const q = cubic(c.stop, c.lead, [RACK.x + 70, GROUND - 640], INLET, ramp(fr, c.turn, c.home));
  return [q[0] + o[0] - c.stop[0], q[1] + o[1] - c.stop[1]];
};

/** Tiny customer cards: a round face and two lines. They drift out to the cloud, then curl home into the rack. */
const CardStream: React.FC<BeatProps> = ({ fr }) => (
  <Draw>
    {CARDS.map((c) => {
      if (fr < c.emit || fr >= c.home) return null;
      const [x, y] = cardAt(c, fr), back = ramp(fr, c.turn, c.home, linear);
      const inCloud = ramp((Math.min(fr, c.turn) - c.emit) / TRAVEL, 0.92, 1, linear);
      const k = sp(fr, c.emit).v * Math.max(1 - inCloud, ramp(back, 0, 0.25, linear)) * (1 - 0.6 * ramp(back, 0.72, 1, linear));
      if (k <= 0.01) return null;
      return (
        <g key={c.i} transform={`translate(${x} ${y}) ${along(vel2((t) => cardAt(c, t), fr))} scale(${k})`}>
          <rect x={-58} y={-36} width={116} height={72} rx={14} fill={C.card} stroke={C.mute} strokeWidth={4} />
          <circle cx={-28} cy={2} r={17} fill={C.skin} />
          <path d="M -45 -3 A 17 17 0 0 1 -11 -3 Z" fill={C.hair} />
          <rect x={2} y={-14} width={40} height={9} rx={4.5} fill={C.cream} />
          <rect x={2} y={6} width={27} height={9} rx={4.5} fill={C.mute} />
        </g>
      );
    })}
  </Draw>
);

const Light: React.FC<{ x: number; y: number; rx: number; ry?: number; color?: string; opacity: number }> = ({ x, y, rx, ry = rx, color = C.gold, opacity }) => {
  const id = "e" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
  if (opacity <= 0.005) return null;
  return (
    <>
      <defs>
        <radialGradient id={id}><stop offset="0%" stopColor={color} stopOpacity={1} /><stop offset="100%" stopColor={color} stopOpacity={0} /></radialGradient>
      </defs>
      <ellipse cx={x} cy={y} rx={rx} ry={ry} fill={`url(#${id})`} opacity={opacity} style={{ mixBlendMode: "screen" }} />
    </>
  );
};

const CLOUD_FILL = mixC(C.mute, C.cream, 0.35), CLOUD_SHADE = mixC(C.mute, C.ground, 0.3);

/** A cloud-shaped server far across the sea, the dotted line that marks abroad, and the tick for the one file. */
const Abroad: React.FC<BeatProps> = ({ fr }) => {
  const pop = sp(fr, CLOUD_IN).v;
  const gulp = bounce(fr, FILE_OK, 2.2, 3, 7) + ABSORBED.reduce((s, a) => s + bounce(fr, a, 0.9, 3, 8), 0);
  const [sx, sy] = sq(gulp);
  const tick = sp(fr, FILE_OK).v * (1 - ramp(fr, FILE_OUT, FILE_OUT + 12, depart));
  const line = ramp(fr, BORDER, BORDER + 14, arrive);
  return (
    <>
      <Draw>
        {line > 0 && (
          <line x1={BORDER_X} y1={30} x2={BORDER_X} y2={lerp(30, 450, line)} stroke={C.mute} strokeWidth={7} strokeLinecap="round" strokeDasharray="1 26" opacity={0.75} />
        )}
        {pop > 0.001 && (
          <g transform={`translate(${CLOUD.x} ${CLOUD.y + (1 - pop) * 50 + 5 * Math.sin(fr / FPS * 1.05)}) scale(${lerp(0.5, 1, pop) * sx} ${lerp(0.5, 1, pop) * sy})`} opacity={u01(pop * 1.6)}>
            {[CLOUD_SHADE, CLOUD_FILL].map((fill, j) => (
              <g key={j} fill={fill} transform={j ? "translate(-7 -8)" : undefined}>
                <rect x={-190} y={-10} width={380} height={100} rx={50} />
                <circle cx={-80} cy={-18} r={66} />
                <circle cx={28} cy={-48} r={88} />
                <circle cx={116} cy={0} r={58} />
              </g>
            ))}
            {[0, 1].map((r) => (
              <g key={r} transform={`translate(-7 ${8 + r * 34})`}>
                <rect x={-120} y={0} width={226} height={22} rx={11} fill={C.ground} opacity={0.55} />
                <circle cx={-104} cy={11} r={5} fill={CLOUD_FILL} />
                <rect x={-20} y={8} width={104} height={6} rx={3} fill={CLOUD_SHADE} />
              </g>
            ))}
          </g>
        )}
        {tick > 0.001 && (
          <g transform={`translate(${CLOUD.x - 168} ${CLOUD.y + 84}) scale(${tick})`}>
            <circle r={42} fill={C.gold} />
            <path d="M -19 1 L -6 15 L 20 -13" fill="none" stroke={C.ground} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" />
          </g>
        )}
      </Draw>
      <Tag text="Claude" color={C.mute} size={38} x={CLOUD.x - 122} y={CLOUD.y - 190} fr={fr} start={CLOUD_IN + 5} />
      <Tag text="ChatGPT" color={C.mute} size={38} x={CLOUD.x + 100} y={CLOUD.y - 190} fr={fr} start={CHATGPT} />
      <Label text="luar negeri" x={CLOUD.x - 10} y={CLOUD.y - 270} size={40} fr={fr} start={ABROAD} />
    </>
  );
};

// ---------- Home: the rack and the creatures around it ----------

const HOVER = 280;
const FALL = 5;
const RACK_LIGHTS = 10;

// Lowered in from above, lifted a little more, held, then dropped: it touches the ground on PLANT.
const rackAt = (fr: number) => {
  const wind = ramp(fr, RACK_WIND, PLANT - FALL - HIT);
  const fall = ramp(fr, PLANT - FALL, PLANT, Easing.in(Easing.quad));
  const tau = (fr - PLANT) / FPS;
  return {
    lift: (HOVER + 900 * (1 - ramp(fr, RACK_IN, RACK_WIND, arrive)) + 30 * wind) * (1 - fall),
    squash: fr >= PLANT ? 0.17 * Math.exp(-6 * tau) * Math.cos(2 * Math.PI * 2.6 * tau) : -0.04 * wind - 0.08 * fall,
  };
};

// The light that gathers in the rack, then swells up and becomes the glow behind the lockup.
const LOCK = { x: P.shore.x, logo: GROUND - 556, title: GROUND - 426, url: GROUND - 322 };
const glowAt = (fr: number) => {
  const on = ramp(fr, PLANT, PLANT + 12), charge = ramp(fr, SWELL - HIT - 12, SWELL - HIT), up = sp(fr, SWELL).v;
  const breath = 1 + 0.02 * Math.sin((2 * Math.PI * fr) / FPS / 7);
  return {
    charge,
    y: lerp(GROUND - RACK.h * 0.55, LOCK.title, up),
    rx: lerp(230 * (1 - 0.32 * charge), 760, up) * breath,
    ry: lerp(230 * (1 - 0.32 * charge), 330, up) * breath,
    opacity: on * lerp(0.2 + 0.3 * charge, 0.17, u01(up)),
  };
};

const lightAt = (k: number, fr: number) => {
  const s = fr / FPS, on = sp(fr, PLANT + 3 + 2 * k, SOFT).v;
  const idle = 0.5 + 0.5 * Math.sin((2 * Math.PI * s) / (2.6 + 0.37 * k) + k * 1.7);
  const blink = CARDS.reduce((m, c) => (c.i % RACK_LIGHTS === k ? Math.max(m, decay(fr, c.home, 6)) : m), 0);
  return { level: Math.max(u01(0.12 + on * (0.33 + 0.4 * idle) + glowAt(fr).charge * 0.5), blink), blink };
};

/** The server rack: a dark cabinet with five units and ten gold lights that blink in a slow stagger. */
const Rack: React.FC<BeatProps> = ({ fr }) => {
  if (fr < RACK_IN) return null;
  const { lift, squash } = rackAt(fr), [sx, sy] = sq(squash), g = glowAt(fr);
  const near = 1 - u01(lift / HOVER), hw = RACK.w / 2;
  return (
    <Draw>
      <ellipse cx={RACK.x} cy={GROUND + 4} rx={(hw + 26) * sx * (0.5 + 0.5 * near)} ry={11} fill={C.deep} opacity={0.6 * near} />
      <Light x={RACK.x} y={GROUND - RACK.h * 0.55} rx={250} opacity={0.14 * ramp(fr, PLANT, PLANT + 12)} />
      <g transform={`translate(${RACK.x} ${GROUND - lift}) scale(${sx} ${sy})`}>
        {[-1, 1].map((sd) => <rect key={sd} x={sd * (hw - 34) - 14} y={-10} width={28} height={12} rx={4} fill={C.line} />)}
        <rect x={-hw} y={-RACK.h} width={RACK.w} height={RACK.h - 6} rx={18} fill={C.card} stroke={mixC(C.line, C.mute, 0.6)} strokeWidth={4} />
        <rect x={-hw + 9} y={-RACK.h + 22} width={5} height={RACK.h - 50} rx={2.5} fill={C.mute} opacity={0.28} />
        {Array.from({ length: RACK_LIGHTS / 2 }, (_, r) => {
          const y = -RACK.h + 18 + r * 44;
          return (
            <g key={r}>
              <rect x={-hw + 22} y={y} width={RACK.w - 40} height={34} rx={9} fill={C.deep} stroke={C.line} strokeWidth={2} />
              <rect x={6} y={y + 14} width={54} height={6} rx={3} fill={C.line} />
              {[0, 1].map((col) => {
                const l = lightAt(r * 2 + col, fr), cx = -hw + 44 + col * 24;
                return (
                  <g key={col}>
                    <circle cx={cx} cy={y + 17} r={7} fill={mixC(C.line, C.goldLight, l.level)} />
                    <Light x={cx} y={y + 17} rx={30} color={C.goldLight} opacity={0.75 * l.blink + 0.25 * l.level} />
                  </g>
                );
              })}
            </g>
          );
        })}
      </g>
      <Light x={RACK.x} y={g.y} rx={g.rx} ry={g.ry} opacity={g.opacity} />
    </Draw>
  );
};

// Where the land creatures gather around the rack.
const GATHER = {
  ants: [{ x: P.shore.x - 580, seed: 3 }, { x: P.shore.x - 420, seed: 4 }],
  eagle: { x: P.shore.x - 220, y: GROUND, scale: 0.6 },
  owl: { x: P.shore.x + 210, y: GROUND, scale: 0.5 },
};
const GATHER_ANT = 0.26;

const EAGLE_LAND = HOME_TAG + 14, EAGLE_GO = EAGLE_LAND - 40;
// It folds its wings a body's length short of the rack and drops the last step, so the spread sprite never crosses it.
const eagleAt = (fr: number) => {
  const u = ramp(fr, EAGLE_GO, EAGLE_LAND, Easing.bezier(0.5, 0, 0.6, 1));
  const folded = ramp(u, 0.9, 0.94, linear), air = ramp(fr, EAGLE_GO, EAGLE_GO + 3, linear) * (1 - folded);
  return {
    x: lerp(HOME.eagle.x, GATHER.eagle.x, u), y: lerp(HOME.eagle.y, GROUND, u) - 240 * Math.sin(Math.PI * u),
    scale: lerp(HOME.eagle.scale, GATHER.eagle.scale, u), fly: air, flap: air * (1 - 0.7 * ramp(u, 0.6, 0.9, linear)),
    tilt: 7 * air * (1 - u), squash: bounce(fr, EAGLE_LAND, 2.4, 3, 7) - 0.07 * folded * Math.sin(Math.PI * ramp(u, 0.9, 1, linear)),
  };
};

// The owl comes down from its branch in three hops; the last one is a low scoot behind the rack.
const OWL_STOPS: V2[] = [[HOME.owl.x, HOME.owl.y], [P.shore.x - 490, GROUND], [P.shore.x - 250, GROUND], [GATHER.owl.x, GROUND]];
const OWL_LAND = [HOME_TAG - 26, HOME_TAG - 12, HOME_TAG + 2];
const OWL_AIR = [11, 11, 12];
const OWL_HOP = [{ h: 120, stretch: -0.1 }, { h: 90, stretch: -0.1 }, { h: 16, stretch: 0.05 }];
const owlAt = (fr: number) => {
  const scale = lerp(HOME.owl.scale, GATHER.owl.scale, ramp(fr, OWL_LAND[0] - OWL_AIR[0], OWL_LAND[0]));
  let k = 0;
  while (k < 3 && fr >= OWL_LAND[k]) k++;
  const go = k < 3 ? OWL_LAND[k] - OWL_AIR[k] : Infinity;
  if (fr <= go) {
    const [x, y] = OWL_STOPS[k];
    return { x, y, scale, tilt: 0, squash: (k > 0 ? bounce(fr, OWL_LAND[k - 1], 2.6, 3, 8) : 0) + (k < 3 ? 0.09 * ramp(fr, go - 3, go) : 0) };
  }
  const u = (fr - go) / OWL_AIR[k], a = OWL_STOPS[k], b = OWL_STOPS[k + 1], hop = OWL_HOP[k];
  return {
    x: lerp(a[0], b[0], u), y: lerp(a[1], b[1], u) - hop.h * 4 * u * (1 - u), scale, tilt: 8 * Math.cos(Math.PI * u),
    squash: hop.stretch * Math.sin(Math.PI * u),
  };
};

const antAt = (j: number, fr: number) => {
  const home = HOME.ants[j + 2], end = HOME_TAG + 19 + 5 * j, go = end - 84;
  const u = ramp(fr, go, end);
  return {
    x: lerp(home.x, GATHER.ants[j].x, u), y: GROUND, scale: lerp(home.scale, GATHER_ANT, u), seed: home.seed,
    walk: ramp(fr, go, go + 6, linear) * (1 - ramp(fr, end - 8, end, linear)),
  };
};

/** The home shore, shared by both beats: the rack with its light, and the creatures that settle around it. */
const Shore: React.FC<BeatProps> = ({ fr }) => {
  const tagOut = ramp(fr, SWELL, SWELL + 6, depart);
  return (
    <>
      {HOME.ants.slice(0, 2).map((a) => <Ant key={a.seed} {...a} t={fr} />)}
      {[0, 1].map((j) => <Ant key={j} {...antAt(j, fr)} t={fr} />)}
      <Owl {...owlAt(fr)} t={fr} />
      <Rack fr={fr} />
      <Burst fr={fr} E={PLANT} seed="plant" n={8} x={RACK.x} y={GROUND - 8} arc={[190, 350]} colors={[C.cream, C.mute]} speed={[420, 760]} size={[10, 18]} />
      <Eagle {...eagleAt(fr)} t={fr} />
      <Flash fr={fr} E={PLANT} x={RACK.x} y={GROUND - 60} r={300} color={C.gold} amp={0.35} />
      <Flash fr={fr} E={SWELL} x={RACK.x} y={GROUND - RACK.h} r={320} color={C.goldLight} amp={0.5} />
      {tagOut < 1 && (
        <div style={{ position: "absolute", left: 0, top: 0, opacity: 1 - tagOut, transform: `translateY(${-36 * tagOut}px)` }}>
          <Tag text="Server Anda · Indonesia" size={36} x={RACK.x} y={GROUND - RACK.h - 62} fr={fr} start={HOME_TAG} />
        </div>
      )}
    </>
  );
};

/** Camera nudge in screen px for beats 14–15, added to the camera by AiPas. */
export const nudgeE = (fr: number): [number, number] => [0, bounce(fr, PLANT, 60, 3, 7)];

// The small boxes beat 13 leaves between the eagle and the owl: on screen only while the camera arrives.
const SMALL_BOX = { x: (P.perch.x + P.branch.x) / 2, y: GROUND, size: 110 };

export const Beat14: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Residents t={fr} hide={["ants", "eagle", "owl"]} />
    {fr < B[14].start + 40 && [0, 170].map((dx) => <GpuCube key={dx} {...SMALL_BOX} x={SMALL_BOX.x + dx} />)}
    <Abroad fr={fr} />
    <Shore fr={fr} />
    <PaperFile fr={fr} />
    <CardStream fr={fr} />
  </>
);

// ---------- The lockup ----------

const LOGO = { w: 302, h: 60 };
const TITLE: { text: string; start: number; color?: string }[] = [
  { text: "AI", start: SWELL },
  { text: "yang", start: at(15, "yang") },
  { text: "Pas", start: at(15, "Pas"), color: C.gold },
];

const Lockup: React.FC<BeatProps> = ({ fr }) => {
  const logo = sp(fr, LOGO_IN).v, url = sp(fr, LOGO_IN + 5, SOFT).v;
  return (
    <>
      <Img src={staticFile("illustrated/aipas/hamra-logo.svg")} style={{
        position: "absolute", left: LOCK.x - LOGO.w / 2, top: LOCK.logo - LOGO.h / 2 + (1 - logo) * 24, width: LOGO.w, height: LOGO.h,
        opacity: u01(logo * 1.5), transform: `scale(${lerp(0.7, 1, logo)})`,
      }} />
      <div style={{
        position: "absolute", left: LOCK.x - 700, top: LOCK.title - 70, width: 1400, height: 140, display: "flex", justifyContent: "center", alignItems: "center",
        gap: 29, fontFamily: FONT, fontWeight: 700, fontSize: 104, lineHeight: 1, color: C.ink, whiteSpace: "nowrap",
      }}>
        {TITLE.map((w) => {
          const v = sp(fr, w.start, POP).v;
          return <span key={w.text} style={{ display: "inline-block", color: w.color, opacity: u01(v * 1.6), transform: `translateY(${(1 - v) * 44}px) scale(${lerp(0.6, 1, v)})` }}>{w.text}</span>;
        })}
      </div>
      <div style={{ position: "absolute", left: LOCK.x, top: LOCK.url + (1 - url) * 16, transform: "translate(-50%, -50%)", opacity: url }}>
        <span style={{ fontFamily: MONO, fontWeight: 500, fontSize: 36, letterSpacing: "0.04em", color: C.cream, whiteSpace: "nowrap" }}>hamra.ai/intro</span>
      </div>
    </>
  );
};

export const Beat15: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Residents t={fr} hide={["ants", "eagle", "owl"]} />
    <Shore fr={fr} />
    <Lockup fr={fr} />
  </>
);
