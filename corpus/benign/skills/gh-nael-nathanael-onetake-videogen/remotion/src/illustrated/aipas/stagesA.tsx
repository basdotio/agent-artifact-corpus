// Beats 1–3: the hook on the home shore, the whale and the letter, the four kinds.
// Each beat is drawn in world coordinates (kit: P, HOME, SHOT) and receives the composition frame.
import React from "react";
import { Easing, random } from "remotion";
import {
  Ant, at, B, BeatProps, blob, BlobFrame, bounce, Burst, C, decay, depart, Draw, Eagle, exit, Flash, FPS, GROUND, HIT, HOME, KIND, lerp,
  NeedBlob, Owl, P, ramp, Residents, SEA, settle, SOFT, sp, SpeechBubble, stretchBy, Tag, vel2, Whale,
} from "./kit";

// Beat 1.
const LAND = at(1, "AI");
const ASK = at(1, "ChatGPT");
// Beat 2.
const HUSH = at(2, "seperti");
const BREACH = at(2, "paus");
const POST = at(2, "mengantar");
const LETTER = at(2, "surat");
const FLICK = at(2, "Bisa");
const LEAVE = at(2, "cuma");
/** Frames the wave takes from the whale to the blob on the shore, and the letter from the nose to the mailbox. */
const WAVE = BREACH + 12;
const FLIGHT = 18;
const DROP = FLICK + FLIGHT;
// Beat 3.
const FOUR = at(3, "empat");
const SHELF = at(3, "pilihannya");
const DATA = at(3, "data");
const LEAP = at(3, "dan");
const NEEDS = at(3, "kebutuhan");
const OUT = B[3].until - 1;

/** Camera nudge in screen px for beats 1–3, added to the camera by AiPas. */
export const nudgeA = (fr: number): [number, number] => [
  0,
  bounce(fr, LAND, 120, 3, 9) - bounce(fr, BREACH, 160, 3, 9) + bounce(fr, DROP, 80, 3, 9) + bounce(fr, DATA, 80, 3, 9) + bounce(fr, NEEDS, 120, 3, 9),
];

const lin = (v: number) => v;
const sq = (s: number): [number, number] => (s >= 0 ? [1 + s, 1 / (1 + s)] : [1 / (1 - s), 1 - s]);
/** 0 → 1 → 0 on a spring: a pop that returns to rest. */
const pulse = (fr: number, on: number, len: number) => sp(fr, on).v * (1 - sp(fr, on + len, SOFT).v);

// ---------- The need on the shore ----------

const NEED_R = 110;
const NEED_X = P.shore.x - 150;

// It drops in, crouches and stretches as it asks, hops on the whale's wave, and leaps off the top in beat 3.
const need = blob({
  from: 0, to: NEEDS, floor: GROUND, hits: [ASK, LEAP],
  kicks: [{ at: ASK - HIT - 4, oval: 320 }, { at: ASK, oval: -560 }, { at: LEAP - HIT - 4, oval: 320 }],
  path: (fr) => {
    // The jelly trails its path by a frame, so the path arrives one early and the body touches down on the word.
    const fall = 1 - ramp(fr, 0, LAND - 1, Easing.in(Easing.quad));
    const hop = ramp(fr, WAVE, WAVE + 9, lin), up = ramp(fr, LEAP, LEAP + 10, depart);
    return { x: NEED_X - 260 * up, y: GROUND - NEED_R - 900 * fall - 240 * hop * (1 - hop) - 3200 * up, r: NEED_R };
  },
});

const box = (s: BlobFrame) => {
  const p = s.rings[0].pts;
  let x0 = Infinity, x1 = -Infinity, top = Infinity;
  for (let i = 0; i < p.length; i += 2) { x0 = Math.min(x0, p[i]); x1 = Math.max(x1, p[i]); top = Math.min(top, p[i + 1]); }
  return { x: (x0 + x1) / 2, w: x1 - x0, top };
};

/** The shore blob with its contact shadow, which tightens as it falls and widens with every squash. */
const ShoreNeed: React.FC<BeatProps> = ({ fr }) => {
  if (fr >= NEEDS) return null;
  const b = box(need(fr));
  const near = ramp(fr, 0, LAND, Easing.in(Easing.quad)) * (1 - ramp(fr, LEAP, LEAP + 5));
  return (
    <>
      <Draw><ellipse cx={b.x} cy={GROUND + 6} rx={b.w * (0.2 + 0.3 * near)} ry={11} fill={C.deep} opacity={0.6 * near} /></Draw>
      <NeedBlob sim={need} fr={fr} label="Mau pakai AI" />
    </>
  );
};

/** The bubble rides the blob's top two frames behind it, and shrinks back into its tail on `HUSH`. */
const Ask: React.FC<BeatProps> = ({ fr }) => {
  const b = box(need(fr - 2));
  const out = exit(HUSH + 10 - fr, 10);
  if (out <= 0.001) return null;
  return (
    <div style={{ position: "absolute", left: b.x + NEED_R * 0.6, top: b.top + 20, width: 0, height: 0, transform: `scale(${out})` }}>
      <SpeechBubble x={0} y={0} text="ChatGPT?" fr={fr} start={ASK} />
    </div>
  );
};

export const Beat01: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Residents t={fr} hide={["whale"]} />
    <Burst fr={fr} E={LAND} seed="land" n={8} x={NEED_X} y={GROUND - 6} arc={[195, 345]} colors={[C.mute, C.line]} speed={[800, 1400]} size={[9, 17]} />
    <ShoreNeed fr={fr} />
    <Ask fr={fr} />
  </>
);

// ---------- Beat 2: the whale and the letter ----------

const SHORE_END = 4130;
const DEEP = 600;
/** Where the letter rests on the whale's head, from the whale's anchor, at home scale and facing the shore. */
const NOSE = { x: -433, y: -99 };
const LETTER_W = 120;
const LETTER_H = 82;
const MAIL_X = P.shore.x + 210;
const MAIL = { hw: 82, mouth: 240, floor: 80 };
const BULGE_X = HOME.whale.x - 160;

/** The whale's whole performance as a function of frame: it lurks, breaches on BREACH, nods and flicks on FLICK. */
const whaleAt = (fr: number) => {
  const up = settle((fr - BREACH) / FPS);
  const y = (q: number) => HOME.whale.y + (1 - settle((q - BREACH) / FPS)) * DEEP;
  const nod = -8 * ramp(fr, FLICK - HIT - 8, FLICK - HIT) * (1 - settle((fr - FLICK) / FPS));
  return {
    x: HOME.whale.x + 90 * (1 - up), y: y(fr),
    tilt: 6 * (1 - up) + bounce(fr, BREACH, 280, 1.6, 4.5) + nod + bounce(fr, FLICK, 345, 2.5, 6),
    // Stretched by the rise, then a belly squash as it falls back from the overshoot.
    squash: stretchBy(vel2((q) => [0, y(q)], fr)[1], 1 / 30000, 0.08) + bounce(fr, BREACH + 9, 1.8, 3, 6),
    opacity: ramp(fr, BREACH - HIT - 16, BREACH - HIT - 6), idle: ramp(fr, BREACH, BREACH + 20),
  };
};

/** The letter's resting spot on the whale's head. Mirrors the kit whale's idle bob and roll, so it never slides. */
const noseAt = (fr: number) => {
  const w = whaleAt(fr), s = fr / FPS;
  const tilt = w.tilt + w.idle * 1.1 * Math.sin((2 * Math.PI * s) / 7.7);
  const a = (tilt * Math.PI) / 180, [sx, sy] = sq(w.squash);
  const nx = NOSE.x * sx, ny = NOSE.y * sy;
  return {
    x: w.x + nx * Math.cos(a) - ny * Math.sin(a),
    y: w.y + w.idle * 7 * Math.sin((2 * Math.PI * s) / 5.3) * HOME.whale.scale + nx * Math.sin(a) + ny * Math.cos(a),
    tilt,
  };
};

/** The letter: on the nose until FLICK (tossed at the top of the breach, a hop on LETTER), then an arc into the mailbox. */
const letterAt = (fr: number) => {
  const riding = (q: number) => {
    const n = noseAt(q), a = (n.tilt * Math.PI) / 180;
    const toss = ramp(q, BREACH + 7, BREACH + 19, lin), hop = ramp(q, LETTER, LETTER + 9, lin);
    const lift = LETTER_H / 2 + 240 * toss * (1 - toss) + 150 * hop * (1 - hop);
    return { x: n.x + lift * Math.sin(a), y: n.y - lift * Math.cos(a), rot: n.tilt + 60 * bounce(q, BREACH + 19, 1, 3, 6) };
  };
  if (fr < FLICK) return { ...riding(fr), k: 1 + 0.25 * pulse(fr, LETTER, 5), opacity: fr < BREACH ? 0 : 1 };
  const from = riding(FLICK), u = Math.min(1, (fr - FLICK) / FLIGHT);
  return {
    x: lerp(from.x, MAIL_X, u), y: lerp(from.y, GROUND - MAIL.mouth + 80, u) - 330 * 4 * u * (1 - u),
    rot: lerp(from.rot, -450, u), k: lerp(1, 0.75, u), opacity: fr > DROP ? 0 : 1,
  };
};

const Letter: React.FC<BeatProps> = ({ fr }) => {
  const l = letterAt(fr), w = LETTER_W / 2, h = LETTER_H / 2;
  if (l.opacity <= 0.001) return null;
  return (
    <Draw opacity={l.opacity}>
      <g transform={`translate(${l.x} ${l.y}) rotate(${l.rot}) scale(${l.k})`}>
        <rect x={-w} y={-h} width={LETTER_W} height={LETTER_H} rx={10} fill={C.ink} />
        <path d={`M ${-w} ${h} L ${-w} ${h - 26} L 0 ${-4} L ${w} ${h - 26} L ${w} ${h} Z`} fill={C.cream} />
        <path d={`M ${-w + 6} ${-h + 6} L 0 6 L ${w - 6} ${-h + 6}`} fill="none" stroke={C.mute} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={0} cy={8} r={11} fill={C.gold} />
      </g>
    </Draw>
  );
};

/**
 * The mailbox on the shore: an open bin on a post with a flag. `part` splits it so the letter can drop between
 * its back rim and its front. It springs up on POST, squashes and raises the flag on DROP, and sinks on LEAVE.
 */
const Mailbox: React.FC<BeatProps & { part: "back" | "front" }> = ({ fr, part }) => {
  const grow = sp(fr, POST).v * exit(LEAVE + 12 - fr, 12);
  if (grow <= 0.001) return null;
  const [sx, sy] = sq(bounce(fr, DROP, 2.6, 3.5, 8));
  const { hw, mouth, floor } = MAIL;
  const flag = 90 * (1 - sp(fr, DROP + 4).v);
  return (
    <Draw>
      <g transform={`translate(${MAIL_X} ${GROUND}) scale(${(0.6 + 0.4 * grow) * sx} ${grow * sy})`}>
        {part === "back" ? (
          <>
            <ellipse cx={0} cy={3} rx={54} ry={9} fill={C.deep} opacity={0.6} />
            <rect x={-11} y={-floor - 20} width={22} height={floor + 22} rx={8} fill={C.wood} />
            <ellipse cx={0} cy={-mouth} rx={hw} ry={22} fill={C.deep} stroke={C.goldDark} strokeWidth={8} />
          </>
        ) : (
          <>
            <g transform={`translate(${hw - 4} ${-mouth + 96}) rotate(${flag})`}>
              <rect x={-6} y={-78} width={12} height={84} rx={6} fill={C.woodLight} />
              <rect x={0} y={-78} width={40} height={28} rx={6} fill={C.coral} />
            </g>
            <path d={`M ${-hw} ${-mouth} A ${hw} 22 0 0 0 ${hw} ${-mouth} L ${hw} ${-floor - 24} Q ${hw} ${-floor} ${hw - 24} ${-floor} L ${-hw + 24} ${-floor} Q ${-hw} ${-floor} ${-hw} ${-floor - 24} Z`} fill={C.gold} />
            <path d={`M ${hw - 30} ${-mouth + 17} L ${hw} ${-mouth} L ${hw} ${-floor - 24} Q ${hw} ${-floor} ${hw - 24} ${-floor} L ${hw - 30} ${-floor} Z`} fill={C.goldDark} opacity={0.7} />
            <path d={`M ${-hw + 4} ${-mouth + 2} A ${hw - 4} 21 0 0 0 ${hw - 4} ${-mouth + 2}`} fill="none" stroke={C.goldLight} strokeWidth={6} strokeLinecap="round" />
            <rect x={-40} y={-178} width={70} height={48} rx={7} fill={C.ink} />
            <path d="M -34 -172 L -5 -152 L 24 -172" fill="none" stroke={C.mute} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" />
          </>
        )}
      </g>
    </Draw>
  );
};

/** A swell on the waterline, centred on cx: half-width hw, height h. */
const Swell: React.FC<{ cx: number; hw: number; h: number }> = ({ cx, hw, h }) => {
  if (h < 0.5) return null;
  const top = Array.from({ length: 25 }, (_, i) => `${(cx - hw + (2 * hw * i) / 24).toFixed(1)} ${(SEA + 2 - h * Math.sin((Math.PI * i) / 24) ** 2).toFixed(1)}`).join(" L ");
  return (
    <Draw>
      <path d={`M ${cx - hw} ${SEA + 40} L ${top} L ${cx + hw} ${SEA + 40} Z`} fill={C.sea} />
      <path d={`M ${top}`} fill="none" stroke={C.sky} strokeWidth={5} strokeLinecap="round" opacity={0.4} />
    </Draw>
  );
};

/** Water drops thrown up from the waterline on frame E: they rise, fall under gravity and vanish back into the sea. */
const Spray: React.FC<{ fr: number; E: number; seed: string; n: number; x: number; width: number; up: [number, number]; side?: number }> = ({
  fr, E, seed, n, x, width, up, side = 520,
}) => {
  const tau = (fr - E) / FPS, g = 2600;
  if (tau < 0 || tau > 1.6) return null;
  return (
    <Draw>
      {Array.from({ length: n }, (_, i) => {
        const r = (k: string) => random(`${seed}${k}${i}`);
        const spot = (i + r("x")) / n - 0.5, vx = spot * side + (r("d") - 0.5) * 120, vy = -(up[0] + r("v") * (up[1] - up[0]));
        const y = SEA + vy * tau + (g * tau * tau) / 2;
        if (y > SEA + 8) return null;
        const [along, across] = sq(-Math.min(0.5, Math.hypot(vx, vy + g * tau) / 2600));
        const size = 7 + r("s") * 9;
        return (
          <ellipse key={i} cx={x + spot * width + vx * tau} cy={y} rx={size * along} ry={size * across} fill={i % 3 ? C.sky : C.ink} opacity={0.85}
            transform={`rotate(${(Math.atan2(vy + g * tau, vx) * 180) / Math.PI + 90} ${x + spot * width + vx * tau} ${y})`} />
        );
      })}
    </Draw>
  );
};

export const Beat02: React.FC<BeatProps> = ({ fr }) => {
  const w = whaleAt(fr);
  // The water bulges, sags a little for the wind-up, holds, and bursts as the whale comes through.
  const bulge = (76 * ramp(fr, BREACH - HIT - 16, BREACH - HIT - 6) - 14 * ramp(fr, BREACH - HIT - 6, BREACH - HIT)) * (1 - ramp(fr, BREACH, BREACH + 5));
  const run = ramp(fr, BREACH + 2, BREACH + 11, lin);
  const posted = fr >= FLICK;
  return (
    <>
      <Residents t={fr} hide={["whale"]} />
      <ShoreNeed fr={fr} />
      <Ask fr={fr} />
      <Swell cx={BULGE_X} hw={560} h={bulge} />
      <Whale {...HOME.whale} x={w.x} y={w.y} tilt={w.tilt} squash={w.squash} opacity={w.opacity} idle={w.idle} t={fr} />
      <Swell cx={lerp(HOME.whale.x - 620, SHORE_END + 150, run)} hw={150} h={40 * (1 - 0.5 * run) * ramp(fr, BREACH + 1, BREACH + 3) * (1 - ramp(fr, BREACH + 10, BREACH + 12))} />
      <Flash fr={fr} E={BREACH} x={BULGE_X} y={SEA - 120} r={520} color={C.sky} amp={0.3} />
      <Spray fr={fr} E={BREACH} seed="breach" n={12} x={BULGE_X} width={900} up={[700, 1350]} />
      <Spray fr={fr} E={BREACH + 10} seed="shore" n={5} x={SHORE_END + 40} width={90} up={[320, 560]} side={160} />
      <Mailbox fr={fr} part="back" />
      {posted && <Letter fr={fr} />}
      <Mailbox fr={fr} part="front" />
      {!posted && <Letter fr={fr} />}
      <Flash fr={fr} E={LETTER} x={letterAt(LETTER).x} y={letterAt(LETTER).y} r={130} color={C.gold} amp={0.5} />
      <Flash fr={fr} E={DROP} x={MAIL_X} y={GROUND - MAIL.mouth} r={200} color={C.gold} amp={0.55} />
      <Burst fr={fr} E={DROP} seed="post" n={7} x={MAIL_X} y={GROUND - MAIL.mouth - 10} arc={[215, 325]} colors={[C.gold, C.ink]} speed={[420, 760]} size={[14, 26]} life={1.3} />
    </>
  );
};

// ---------- Beat 3: the four kinds, then data and the need ----------

const KIND_TAG = 84;
const GAP = 8;
// Each kind, small to large: its halo (centre and radii) and where its chip sits.
const KINDS: { k: keyof typeof KIND; x: number; y: number; rx: number; ry: number; chip: [number, number] }[] = [
  { k: "cerdas", x: P.ants.x, y: GROUND - 60, rx: 520, ry: 190, chip: [P.ants.x, GROUND - 330] },
  { k: "spesialis", x: HOME.eagle.x, y: HOME.eagle.y - 160, rx: 290, ry: 290, chip: [HOME.eagle.x, HOME.eagle.y - 480] },
  { k: "ringan", x: HOME.owl.x, y: HOME.owl.y - 180, rx: 300, ry: 300, chip: [HOME.owl.x - 60, HOME.owl.y - 470] },
  { k: "besar", x: HOME.whale.x, y: HOME.whale.y - 30, rx: 640, ry: 460, chip: [HOME.whale.x, HOME.whale.y - 620] },
];
const turn = (i: number) => FOUR + GAP * i;

/** A creature's light-up on frame T: dim until then, a crouch, then a stretch and a scale pop that return to rest. */
const lightUp = (fr: number, T: number) => ({
  opacity: 1 - 0.55 * ramp(fr, B[3].start, B[3].start + 14) * (1 - ramp(fr, T - 1, T + 3)),
  scale: 1 + 0.14 * pulse(fr, T, 8),
  squash: fr < T ? 0.07 * ramp(fr, T - 7, T - 1) : -bounce(fr, T, 2.4, 3, 8),
});

const Halo: React.FC<{ x: number; y: number; rx: number; ry: number; color: string; opacity: number }> = ({ x, y, rx, ry, color, opacity }) => {
  const id = "h" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
  if (opacity < 0.01) return null;
  return (
    <Draw>
      <defs>
        <radialGradient id={id}><stop offset="0%" stopColor={color} stopOpacity={1} /><stop offset="100%" stopColor={color} stopOpacity={0} /></radialGradient>
      </defs>
      <ellipse cx={x} cy={y} rx={rx} ry={ry} fill={`url(#${id})`} opacity={opacity} style={{ mixBlendMode: "screen" }} />
    </Draw>
  );
};

const TOP_R = 240;
const SHELF_Y = P.wide.y + 150;
const TOP_X = P.wide.x + 330;
const DATA_X = P.wide.x - 330;
const DISC = { rx: 170, ry: 48, h: 64, pitch: 76 };

// The need comes back down beside the data, larger, and lands on the shelf.
const needTop = blob({
  from: LEAP, to: B[3].until, floor: SHELF_Y,
  path: (fr) => ({ x: TOP_X, y: SHELF_Y - TOP_R - 1500 * (1 - ramp(fr, LEAP, NEEDS - 1, Easing.in(Easing.quad))), r: TOP_R }),
});

/** Centre-top: a shelf draws out, the data stack lands on it disc by disc, then the need. All of it leaves with the beat. */
const Top: React.FC<BeatProps> = ({ fr }) => {
  const out = exit(OUT - fr, 8);
  if (fr < SHELF || out <= 0.001) return null;
  const dip = bounce(fr, DATA, 600, 3, 8) + bounce(fr, NEEDS, 1000, 3, 8);
  const shelf = sp(fr, SHELF, SOFT).v;
  return (
    <div style={{
      position: "absolute", left: 0, top: 0, transformOrigin: `${P.wide.x}px ${SHELF_Y}px`, opacity: out,
      transform: `translateY(${dip - 70 * (1 - out)}px) scale(${0.9 + 0.1 * out})`,
    }}>
      <Draw>
        <rect x={P.wide.x - 660 * shelf} y={SHELF_Y} width={1320 * shelf} height={26} rx={13} fill={C.line} />
        <rect x={P.wide.x - 640 * shelf} y={SHELF_Y + 3} width={1280 * shelf} height={5} rx={2.5} fill={C.mute} opacity={0.5} />
        {[0, 1, 2].map((j) => {
          const land = DATA + 4 * j;
          if (fr < land - 12) return null;
          const fall = 1 - ramp(fr, land - 12, land, Easing.in(Easing.quad));
          const [sx, sy] = sq(bounce(fr, land, 3, 3.5, 9));
          const { rx, ry, h } = DISC;
          return (
            <g key={j} transform={`translate(${DATA_X} ${SHELF_Y - j * DISC.pitch - 1300 * fall}) scale(${sx} ${sy})`}>
              <path d={`M ${-rx} ${-h} L ${-rx} 0 A ${rx} ${ry} 0 0 0 ${rx} 0 L ${rx} ${-h} Z`} fill={C.mute} />
              <path d={`M ${rx * 0.5} ${-h} L ${rx * 0.5} ${ry * 0.86} A ${rx} ${ry} 0 0 0 ${rx} 0 L ${rx} ${-h} Z`} fill={C.ground} opacity={0.22} />
              <ellipse cx={0} cy={-h} rx={rx} ry={ry} fill={C.ink} />
              <circle cx={-rx * 0.62} cy={-h * 0.5 + ry * 0.72} r={13} fill={C.gold} />
            </g>
          );
        })}
      </Draw>
      <Tag text="Data" color={C.ink} x={DATA_X} y={SHELF_Y + 112} size={KIND_TAG} fr={fr} start={DATA + 13} />
      <Flash fr={fr} E={NEEDS} x={TOP_X} y={SHELF_Y - TOP_R} r={620} color={C.cream} amp={0.45} />
      {[[182, 214], [326, 358]].map(([a, b]) => (
        <Burst key={a} fr={fr} E={NEEDS} seed={`needs${a}`} n={4} x={TOP_X} y={SHELF_Y - 16} arc={[a, b]} colors={[C.cream, C.gold]} speed={[1500, 2300]} size={[20, 40]} life={1.2} />
      ))}
      {fr >= LEAP && <NeedBlob sim={needTop} fr={fr} label="Kebutuhan Anda" />}
    </div>
  );
};

export const Beat03: React.FC<BeatProps> = ({ fr }) => {
  const out = exit(OUT - fr, 8);
  const [ants, eagle, owl, whale] = KINDS.map((_, i) => lightUp(fr, turn(i)));
  return (
    <>
      {KINDS.map(({ k, x, y, rx, ry }, i) => (
        <Halo key={k} x={x} y={y} rx={rx} ry={ry} color={KIND[k].color} opacity={out * ramp(fr, turn(i), turn(i) + 3) * (0.2 + 0.4 * decay(fr, turn(i), 4))} />
      ))}
      {HOME.ants.map((a, j) => {
        const g = lightUp(fr, turn(0) + 2 * j);
        return <Ant key={a.seed} {...a} t={fr} scale={a.scale * g.scale} squash={g.squash} opacity={ants.opacity} />;
      })}
      <Eagle {...HOME.eagle} t={fr} scale={HOME.eagle.scale * eagle.scale} squash={eagle.squash} opacity={eagle.opacity} />
      <Owl {...HOME.owl} t={fr} scale={HOME.owl.scale * owl.scale} squash={owl.squash} opacity={owl.opacity} />
      <Whale {...HOME.whale} t={fr} scale={HOME.whale.scale * whale.scale} squash={whale.squash} opacity={whale.opacity} />
      <ShoreNeed fr={fr} />
      <Draw>
        {KINDS.map(({ k, x, y, rx, ry }, i) => {
          const u = ramp(fr, turn(i), turn(i) + 16, Easing.out(Easing.cubic));
          if (u <= 0 || u >= 1) return null;
          return <ellipse key={k} cx={x} cy={y} rx={rx * (0.7 + 0.45 * u)} ry={ry * (0.7 + 0.45 * u)} fill="none" stroke={KIND[k].color} strokeWidth={16} opacity={0.8 * (1 - u)} />;
        })}
      </Draw>
      {KINDS.map(({ k, chip }, i) => (
        <div key={k} style={{ position: "absolute", left: chip[0], top: chip[1], width: 0, height: 0, transform: `scale(${out})` }}>
          <Tag text={KIND[k].name} color={KIND[k].color} x={0} y={0} size={KIND_TAG} fr={fr} start={turn(i) + 4} />
        </div>
      ))}
      <Top fr={fr} />
    </>
  );
};
