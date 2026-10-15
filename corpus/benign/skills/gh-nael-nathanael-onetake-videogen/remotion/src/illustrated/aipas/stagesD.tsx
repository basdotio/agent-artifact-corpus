// Beats 10–13: the bank desk, the two linked cards, the need that splits in two, the 97% saving.
// Each beat is drawn in world coordinates (kit: P, HOME, SHOT) and receives the composition frame.
import React from "react";
import {
  arrive, at, B, BeatProps, blob, BlobFrame, bounce, Burst, C, Card, decay, depart, DESK_FLOOR, Draw, Eagle, Flash, FONT, FPS, GPU_CAP,
  GpuCube, GpuPile, GROUND, HIT, HOME, inOut, KIND, Label, lerp, mixC, MONO, NeedBlob, Owl, P, Person, punch, ramp, Residents,
  settle, SOFT, sp, Tag, Whale,
} from "./kit";

const u01 = (v: number) => Math.max(0, Math.min(1, v));
// Area-preserving scale pair, as the kit's actors use: s > 0 flattens, s < 0 stretches.
const sq = (s: number): [number, number] => (s >= 0 ? [1 + s, 1 / (1 + s)] : [1 / (1 - s), 1 - s]);

/** A soft light behind something that has just been given work, or holds the eye. */
const Halo: React.FC<{ x: number; y: number; rx: number; ry?: number; color?: string; opacity: number }> = ({ x, y, rx, ry = rx, color = C.gold, opacity }) => {
  const id = "d" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
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

/**
 * A hop on frame E: crouch over `wind` frames, HIT-frame hold, `air` frames off the ground stretched along the
 * travel, then a landing squash that settles. Returns the y offset and the `squash` prop.
 */
const hop = (fr: number, E: number, height: number, air = 14, crouch = 0.1, wind = 12) => {
  if (fr < E) return { y: 0, squash: crouch * ramp(fr, E - HIT - wind, E - HIT) };
  const q = (fr - E) / air;
  if (q < 1) return { y: -height * 4 * q * (1 - q), squash: -crouch * Math.abs(1 - 2 * q) };
  return { y: 0, squash: bounce(fr, E + air, 2.4, 3.5, 9) };
};

// ---------- Beats 10–11: the bank ----------

const T10 = {
  greet: at(10, "Rina"), reach: at(10, "memasukkan"), plateOut: at(10, "nomor"), type: at(10, "CIF"), open: at(10, "Budi"),
  profil: at(10, "profilnya"), mutasi: at(10, "mutasi"), note: at(10, "AI"), lean: at(10, "omzet"), bars: at(10, "naik"), chip: at(10, "bulan"),
};
const T11 = {
  room: at(11, "Lalu"), reko: at(11, "rekomendasi"), plafon: at(11, "plafon"), spark: at(11, "arus"), dinda: at(11, "Dinda"),
  status: at(11, "nasabah"), draw: at(11, "profil"), snap: at(11, "terhubung"), family: at(11, "keluarga"), via: at(11, "bancassurance"),
  ready: at(11, "siap"), offer: at(11, "tawaran"),
};
/** The cards fold into the need on the way back up to the landscape. */
const MERGE = B[12].start;
const RISEN = at(12, "layar") + 8;

const CIF = "0042 7781";
const DIGIT_GAP = 4;
const BUDI = { x: P.card.x - 50, y: P.card.y, w: 580 };
const DINDA = { x: P.card2.x + 45, y: P.card2.y, w: 470 };
// Heights of the sections of Pak Budi's card, top to bottom; the card grows as each arrives.
const H = { pad: 28, head: 80, profil: 68, mutasi: 132, note: 176, reko: 125 };
const LINK_Y = BUDI.y + H.pad + 40;
const LINK = { a: BUDI.x + BUDI.w / 2, b: DINDA.x - DINDA.w / 2, mid: (BUDI.x + BUDI.w / 2 + DINDA.x - DINDA.w / 2) / 2 };
const FAMILY_Y = LINK_Y - 150;
const REKO_PT = { x: BUDI.x - BUDI.w / 2 + H.pad + 165, y: BUDI.y + H.pad + H.head + H.profil + H.mutasi + H.note + 46 };
const FOLD = { x: LINK.mid, y: BUDI.y + 170 };
const KEYS = { x: P.desk.x - 146, y: DESK_FLOOR - 184 };
const MUTASI = [["Apr", "+ Rp 21,5 jt"], ["Mei", "+ Rp 24,0 jt"], ["Jun", "+ Rp 26,8 jt"]];
const BARS = [26, 36, 48, 60, 76, 92];
const SPARK = "M 2 28 L 20 24 L 38 27 L 56 17 L 74 20 L 92 10 L 112 5";
// The piles and labels beat 9 (stagesC) leaves beside each kind, held while the camera leaves the landscape.
const PILES_9 = [
  { x: P.trail1.x - 170, count: 1, size: 60, seed: "ants", label: "GPU hampir nol" },
  { x: P.perch.x + 330, count: 6, size: 60, seed: "eagle", label: "GPU kecil" },
  { x: P.branch.x - 380, count: 21, size: 60, seed: "owl", label: "GPU menengah" },
  { x: P.shore.x - 140, count: GPU_CAP, size: 46, seed: "whale", label: "GPU besar" },
];

// Bu Rina's whole performance as a function of frame, so her arm and what she holds can trail it.
const rinaAt = (fr: number) => {
  const nod = bounce(fr, T10.greet, 2.6, 2.5, 6);
  const lean = ramp(fr, T10.lean, T10.lean + 26);
  const perk = bounce(fr, T11.reko + 4, 0.7, 3, 7);
  const jump = hop(fr, T11.ready, 84);
  const glad = ramp(fr, T11.ready, T11.ready + 6);
  return {
    x: P.rina.x + 12 * lean, y: P.rina.y + jump.y,
    squash: nod + jump.squash - perk,
    tilt: 30 * nod + 3 * ramp(fr, T10.reach, T10.reach + 14) + 5 * lean - 6 * glad,
    happy: Math.max(0.8 * ramp(fr, T10.greet, T10.greet + 6) * (1 - ramp(fr, T10.greet + 30, T10.greet + 46)), 0.4 * ramp(fr, T10.bars, T10.bars + 20), glad),
    look: ramp(fr, T10.reach, T10.reach + 12),
    idle: fr >= T11.ready - HIT && fr < T11.ready ? 0 : 1,
  };
};

// Her right hand: out to the keyboard, a tap per digit, a raised finger before Enter, then up with the offer.
const handAt = (fr: number) => {
  const r = rinaAt(fr), held = rinaAt(fr - 3);
  const reach = sp(fr, T10.reach, SOFT).v, offer = sp(fr, T11.offer).v;
  const typing = ramp(fr, T10.type - 4, T10.type - 2) * (fr <= T10.type + DIGIT_GAP * 7 ? 1 : 0);
  const tap = typing * 11 * Math.abs(Math.sin((Math.PI * (fr - T10.type)) / DIGIT_GAP));
  const enter = 22 * (fr < T10.open ? ramp(fr, T10.open - HIT - 8, T10.open - HIT) : 1 - ramp(fr, T10.open, T10.open + 2, arrive));
  const key = Math.max(0, Math.min(7, Math.floor((fr - T10.type) / DIGIT_GAP)));
  const kx = lerp(r.x + 40, KEYS.x - 26 + 7 * key, reach), ky = lerp(r.y - 120, KEYS.y - 7 - tap - enter, reach);
  return { x: lerp(kx, P.rina.x + 100, offer), y: lerp(ky, held.y - 250, offer), reach, offer, sx: r.x + 44, sy: r.y - 126 };
};

const KEY_TEXT: React.CSSProperties = { fontFamily: MONO, fontWeight: 500, fontSize: 21, letterSpacing: "0.06em", textTransform: "uppercase", color: C.mute };
const RULE: React.CSSProperties = { borderTop: `1.5px solid ${C.line}`, paddingTop: 14, display: "flex", justifyContent: "space-between", gap: 16 };

/** A card section that makes room for itself: the card grows by `h` as `v` goes 0 → 1. */
const Grow: React.FC<{ v: number; h: number; clip?: boolean; children?: React.ReactNode }> = ({ v, h, clip = true, children }) =>
  v <= 0.001 ? null : (
    <div style={{ height: h * Math.min(1, v), overflow: clip ? "hidden" : "visible" }}>
      <div style={{ height: h, boxSizing: "border-box", paddingTop: 16 }}>{children}</div>
    </div>
  );

/** A filled gold chip for a recommendation. */
const GoldChip: React.FC<{ text: string; size: number; scale: number; ink: number; glow: number }> = ({ text, size, scale, ink, glow }) => (
  <span style={{
    display: "inline-block", fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.15, whiteSpace: "nowrap", color: C.ground,
    background: mixC(C.gold, C.goldLight, 0.6 * glow), borderRadius: 999, padding: `${size * 0.32}px ${size * 0.72}px`,
    transform: `scale(${scale})`, boxShadow: `0 0 ${(14 + 34 * glow).toFixed(1)}px ${mixC(C.card, C.gold, 0.35 + 0.65 * glow)}`,
  }}><span style={{ opacity: ink }}>{text}</span></span>
);

const slide = (v: number, dx = 36): React.CSSProperties => ({ opacity: u01(v * 1.5), transform: `translateX(${(1 - v) * dx}px)` });

const BudiCard: React.FC<{ fr: number; x: number }> = ({ fr, x }) => {
  const note = sp(fr, T10.note).v;
  const seed = ramp(fr, T11.reko - HIT - 18, T11.reko - HIT - 12, arrive), pop = punch(fr, T11.reko);
  const plafon = sp(fr, T11.plafon).v, fill = 0.68 * sp(fr, T11.plafon + 5, { damping: 14, stiffness: 46 }).v;
  const spark = ramp(fr, T11.spark, T11.spark + 18);
  return (
    <Card x={x} y={BUDI.y} w={BUDI.w} fr={fr} start={T10.open} title="Pak Budi" sub={`CIF ${CIF}`} who="budi">
      <Grow v={sp(fr, T10.profil, SOFT).v} h={H.profil}>
        <div style={{ ...RULE, alignItems: "baseline", ...slide(sp(fr, T10.profil).v) }}>
          <span style={KEY_TEXT}>Profil</span>
          <span style={{ fontWeight: 500, fontSize: 31 }}>Pemilik usaha</span>
        </div>
      </Grow>
      <Grow v={sp(fr, T10.mutasi, SOFT).v} h={H.mutasi}>
        <div style={RULE}>
          <span style={{ ...KEY_TEXT, ...slide(sp(fr, T10.mutasi).v, 0) }}>Mutasi</span>
          <div>
            {MUTASI.map(([month, sum], i) => (
              <div key={month} style={{ display: "flex", justifyContent: "flex-end", alignItems: "baseline", gap: 18, height: 34, ...slide(sp(fr, T10.mutasi + 5 * i).v) }}>
                <span style={{ ...KEY_TEXT, fontSize: 20 }}>{month}</span>
                <span style={{ fontWeight: 500, fontSize: 27, color: C.cream, fontVariantNumeric: "tabular-nums", minWidth: 172, textAlign: "right" }}>{sum}</span>
              </div>
            ))}
          </div>
        </div>
      </Grow>
      <Grow v={sp(fr, T10.note, SOFT).v} h={H.note}>
        <div style={{
          boxSizing: "border-box", height: H.note - 18, padding: "14px 18px", borderRadius: 16, background: C.deep, border: `1.5px solid ${mixC(C.line, C.gold, 0.45)}`,
          transformOrigin: "50% 0", transform: `scale(${0.92 + 0.08 * note})`, opacity: u01(note * 1.5),
        }}>
          <div style={{ ...KEY_TEXT, fontSize: 20, color: C.gold, lineHeight: "24px" }}>Catatan AI</div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 10 }}>
            <svg width={184} height={96} style={{ overflow: "visible", flex: "none" }}>
              <rect x={0} y={93} width={184} height={3} rx={1.5} fill={C.line} />
              {BARS.map((h, i) => {
                const v = sp(fr, T10.bars + 5 * i).v;
                return <rect key={i} x={2 + i * 31} y={92 - h * v} width={24} height={Math.max(0, h * v)} rx={5} fill={mixC(C.goldDark, C.goldLight, (i / 5) * u01(v))} />;
              })}
            </svg>
            <Tag text="Omzet naik 6 bulan" size={22} fr={fr} start={T10.chip} />
          </div>
        </div>
      </Grow>
      <Grow v={sp(fr, T11.room, SOFT).v} h={H.reko} clip={false}>
        <div style={{ paddingTop: 2, height: 56 }}>
          <GoldChip text="Kredit Modal Kerja" size={28} scale={seed * (0.3 + 0.7 * pop)} ink={ramp(fr, T11.reko, T11.reko + 4)} glow={decay(fr, T11.reko, 2.4)} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 12, height: 38, ...slide(plafon, 24) }}>
          <span style={{ ...KEY_TEXT, fontSize: 20 }}>Plafon</span>
          <div style={{ position: "relative", width: 210, height: 16, borderRadius: 8, background: C.line }}>
            <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${fill * 100}%`, borderRadius: 8, background: C.gold }} />
            <div style={{ position: "absolute", left: "82%", top: -5, bottom: -5, width: 3, borderRadius: 2, background: C.mute, opacity: 0.7 }} />
          </div>
          <svg width={116} height={34} style={{ overflow: "visible", flex: "none" }}>
            <path d={SPARK} fill="none" stroke={C.cream} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - spark} opacity={spark > 0 ? 1 : 0} />
            <circle cx={112} cy={5} r={6 * sp(fr, T11.spark + 18).v} fill={C.gold} />
          </svg>
        </div>
      </Grow>
    </Card>
  );
};

/** The CIF field on Bu Rina's monitor: digits tick in one by one, then the button is pressed. */
const CifScreen: React.FC<{ fr: number }> = ({ fr }) => {
  const focus = ramp(fr, T10.type - 8, T10.type), press = fr < T10.open ? 0.16 * ramp(fr, T10.open - HIT - 8, T10.open - HIT) : -bounce(fr, T10.open, 1.6, 4, 10);
  const typed = Math.max(0, Math.min(8, Math.floor((fr - T10.type) / DIGIT_GAP) + 1));
  const CW = 21.6, X0 = -86;
  const caret = X0 - 12 + CW * (typed + (typed > 4 ? 1 : 0)) + (typed === 4 ? CW * 0.5 : 0);
  let digit = -1;
  return (
    <Draw>
      <g transform={`translate(${P.desk.x} ${DESK_FLOOR})`}>
        <rect x={-140} y={-380} width={280} height={166} rx={12} fill={C.card} />
        <text x={-122} y={-350} fontFamily={MONO} fontWeight={500} fontSize={20} letterSpacing="0.06em" fill={C.mute}>NOMOR CIF</text>
        <rect x={-124} y={-336} width={248} height={62} rx={14} fill={C.deep} stroke={mixC(C.line, C.gold, 0.7 * focus)} strokeWidth={3} />
        {CIF.split("").map((ch, i) => {
          if (ch === " ") return null;
          digit++;
          const v = sp(fr, T10.type + DIGIT_GAP * digit).v;
          return v <= 0.001 ? null : (
            <text key={i} transform={`translate(${X0 + CW * i} ${-292 + (1 - v) * 8}) scale(${0.6 + 0.4 * v})`} textAnchor="middle" fontFamily={MONO} fontWeight={500} fontSize={36} fill={C.ink} opacity={u01(v * 2)}>{ch}</text>
          );
        })}
        {fr < T10.open && focus > 0 && <rect x={caret} y={-322} width={3} height={34} rx={1.5} fill={C.gold} opacity={focus * (0.55 + 0.45 * Math.sin(fr * 0.5))} />}
        <g transform={`translate(78 -242) scale(${1 - press})`}>
          <rect x={-46} y={-18} width={92} height={36} rx={18} fill={mixC(C.line, C.gold, 0.25 + 0.75 * ramp(fr, T10.type + DIGIT_GAP * 7, T10.type + DIGIT_GAP * 7 + 6))} />
          <text y={7} textAnchor="middle" fontFamily={FONT} fontWeight={700} fontSize={20} fill={C.ground}>Cari</text>
        </g>
      </g>
    </Draw>
  );
};

const NamePlate: React.FC<{ fr: number }> = ({ fr }) => {
  const v = sp(fr, T10.greet + 5).v, out = ramp(fr, T10.plateOut, T10.plateOut + 12, depart);
  if (v <= 0.001 || out >= 1) return null;
  return (
    <div style={{ position: "absolute", left: P.rina.x - 36, top: P.rina.y - 384 - 14 * out, transform: "translate(-50%, -50%)", opacity: 1 - out }}>
      <div style={{ transform: `scale(${v})`, background: C.card, border: `1.5px solid ${C.line}`, borderRadius: 20, padding: "12px 22px", textAlign: "center", whiteSpace: "nowrap" }}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 32, lineHeight: 1.15, color: C.ink }}>Bu Rina</div>
        <div style={{ ...KEY_TEXT, fontSize: 19, marginTop: 4, opacity: u01(sp(fr, T10.greet + 10).v) }}>Relationship Manager</div>
      </div>
    </div>
  );
};

/** Bu Rina at her desk: body, keyboard, typing arm, and the offer sheet she ends up holding. */
const Rina: React.FC<{ fr: number }> = ({ fr }) => {
  const r = rinaAt(fr), h = handAt(fr), paper = handAt(fr - 2);
  const mx = (h.sx + h.x) / 2, my = (h.sy + h.y) / 2 + 26 * (1 - h.offer);
  return (
    <>
      <Draw><rect x={KEYS.x - 50} y={KEYS.y} width={100} height={12} rx={5} fill="#4a4628" /></Draw>
      <Person who="rina" x={r.x} y={r.y} t={fr} squash={r.squash} tilt={r.tilt} happy={r.happy} look={r.look} idle={r.idle} />
      {paper.offer > 0.01 && (
        <Draw>
          <g transform={`translate(${paper.x} ${paper.y - 6}) rotate(${-6 - 0.8 * sp(fr, T11.offer).vel}) scale(${paper.offer})`}>
            <rect x={-56} y={-146} width={112} height={146} rx={12} fill={C.cream} />
            <rect x={-56} y={-146} width={112} height={36} rx={12} fill={C.gold} />
            <rect x={-56} y={-124} width={112} height={14} fill={C.gold} />
            <text x={0} y={-120} textAnchor="middle" fontFamily={FONT} fontWeight={700} fontSize={22} fill={C.ground}>Tawaran</text>
            {[0, 1, 2].map((i) => <rect key={i} x={-40} y={-92 + i * 22} width={i === 2 ? 46 : 80} height={8} rx={4} fill={C.mute} />)}
            <circle cx={30} cy={-28} r={13} fill={C.gold} />
            <path d="M 23 -28 L 28 -22 L 37 -34" fill="none" stroke={C.ground} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
          </g>
        </Draw>
      )}
      {h.reach > 0.01 && (
        <Draw opacity={u01(h.reach * 3)}>
          <path d={`M ${h.sx} ${h.sy} Q ${mx} ${my} ${h.x} ${h.y}`} fill="none" stroke="#c9bd98" strokeWidth={26} strokeLinecap="round" />
          <path d={`M ${h.sx} ${h.sy - 3} Q ${mx} ${my - 3} ${h.x} ${h.y - 3}`} fill="none" stroke={C.cream} strokeWidth={19} strokeLinecap="round" />
          <circle cx={h.x} cy={h.y} r={13} fill={C.skin} />
        </Draw>
      )}
    </>
  );
};

/** Everything in the bank room, as a function of frame alone: beats 10 and 11, and the way out in beat 12. */
const Bank: React.FC<BeatProps> = ({ fr }) => {
  const fold = ramp(fr, MERGE, MERGE + 16, depart);
  // The link snapping taut tugs both cards toward each other; the lighter card moves more.
  const tug = bounce(fr, T11.snap, 230, 4, 9);
  const dinda = sp(fr, T11.dinda);
  const a = LINK.a + 0.6 * tug, b = LINK.b - tug + (1 - dinda.v) * 420;
  const drawn = ramp(fr, T11.draw, T11.draw + 18);
  const sag = fr < T11.snap ? 44 + 16 * ramp(fr, T11.snap - HIT - 8, T11.snap - HIT) : 60 * (1 - settle((fr - T11.snap) / FPS));
  const taut = decay(fr, T11.snap, 5);
  const bud = ramp(fr, T11.family - HIT - 12, T11.family - HIT), grown = fr < T11.family ? 0 : settle((fr - T11.family) / FPS);
  const fy = lerp(LINK_Y, FAMILY_Y, grown);
  const via = sp(fr, T11.via, SOFT).v;
  return (
    <>
      <Halo x={P.desk.x} y={DESK_FLOOR - 297} rx={260} opacity={0.22 * ramp(fr, T10.type - 8, T10.type) + 0.3 * decay(fr, T10.open, 4)} />
      <CifScreen fr={fr} />
      <Burst fr={fr} E={T11.ready + 14} seed="ready" n={6} x={P.rina.x} y={P.rina.y - 4} colors={[C.mute, C.line]} speed={[160, 320]} size={[6, 11]} life={1.1} arc={[190, 350]} />
      <Rina fr={fr} />
      <NamePlate fr={fr} />
      {fold < 1 && (
        <div style={{ position: "absolute", left: 0, top: 0, width: 0, height: 0, transformOrigin: `${FOLD.x}px ${FOLD.y}px`, transform: `scale(${1 - 0.85 * fold})`, opacity: 1 - fold }}>
          <BudiCard fr={fr} x={BUDI.x + 0.6 * tug} />
          <Flash fr={fr} E={T11.reko} x={REKO_PT.x} y={REKO_PT.y} r={300} color={C.gold} amp={0.55} />
          <Burst fr={fr} E={T11.reko} seed="reko" n={8} x={REKO_PT.x} y={REKO_PT.y} colors={[C.gold, C.goldLight, C.cream]} speed={[240, 520]} size={[6, 12]} life={1.4} />
          {fr >= T11.dinda && (
            <Card x={DINDA.x - tug + (1 - dinda.v) * 420} y={DINDA.y} w={DINDA.w} fr={fr} title="Dinda" sub="Anak Pak Budi" who="dinda"
              rows={[{ k: "Status", v: "Nasabah", at: T11.status }]} opacity={ramp(fr, T11.dinda, T11.dinda + 6)} />
          )}
          {drawn > 0 && (
            <Draw>
              <path d={`M ${a} ${LINK_Y} Q ${(a + b) / 2} ${LINK_Y + 2 * sag} ${b} ${LINK_Y}`} fill="none" stroke={C.gold} strokeWidth={14} strokeLinecap="round" opacity={0.35 * taut} style={{ filter: "blur(8px)" }} />
              <path d={`M ${a} ${LINK_Y} Q ${(a + b) / 2} ${LINK_Y + 2 * sag} ${b} ${LINK_Y}`} fill="none" stroke={mixC(C.goldDark, C.gold, u01(fr - T11.snap + 1))} strokeWidth={5} strokeLinecap="round"
                pathLength={1} strokeDasharray={1} strokeDashoffset={1 - drawn} />
              <circle cx={a} cy={LINK_Y} r={9} fill={C.gold} />
              <circle cx={b} cy={LINK_Y} r={9 * sp(fr, T11.draw + 18).v} fill={C.gold} />
              {grown > 0 && <line x1={LINK.mid} y1={LINK_Y} x2={LINK.mid} y2={fy + 20} stroke={C.gold} strokeWidth={4} strokeLinecap="round" />}
              <circle cx={LINK.mid} cy={LINK_Y + sag} r={11 * bud} fill={C.goldLight} />
            </Draw>
          )}
          <Flash fr={fr} E={T11.snap} x={LINK.mid} y={LINK_Y} r={220} color={C.gold} amp={0.5} />
          <Flash fr={fr} E={T11.family} x={LINK.mid} y={FAMILY_Y} r={320} color={C.gold} amp={0.55} />
          <Burst fr={fr} E={T11.family} seed="family" n={8} x={LINK.mid} y={FAMILY_Y} colors={[C.gold, C.goldLight, C.cream]} speed={[220, 460]} size={[6, 12]} life={1.4} arc={[180, 360]} />
          {grown > 0.001 && (
            <div style={{ position: "absolute", left: LINK.mid, top: fy, transform: "translate(-50%, -50%)" }}>
              <GoldChip text="Asuransi pendidikan" size={30} scale={grown} ink={1} glow={decay(fr, T11.family, 2.4)} />
            </div>
          )}
          {via > 0.001 && (
            <div style={{ position: "absolute", left: LINK.mid, top: FAMILY_Y - 58 + (1 - via) * 12, transform: "translate(-50%, -50%)", opacity: via, fontFamily: MONO, fontWeight: 500, fontSize: 24, letterSpacing: "0.04em", color: C.mute, whiteSpace: "nowrap" }}>
              lewat bancassurance
            </div>
          )}
        </div>
      )}
    </>
  );
};

// ---------- Beat 12: the need splits in two ----------

const SPLIT = at(12, "dua");
const PINCH = SPLIT - HIT - 28;
const NEED_R = 300;
const T12 = {
  nameA: at(12, "pola"), goA: at(12, "tugas"), catchA: at(12, "spesialis"), nameB: at(12, "catatan"), goB: at(12, "model"), catchB: at(12, "ringan"),
  yawn: at(12, "beristirahat"),
};
const EAGLE_HOLD = { x: HOME.eagle.x + 10, y: HOME.eagle.y - 170 };
const OWL_HOLD = { x: HOME.owl.x, y: HOME.owl.y - 180 };

type XY = { x: number; y: number };
// A half's flight: it backs off 6% first, holds for the hit-pause, then travels an arc bulging by `bulge`.
const fly = (go: number, land: number, to: XY, bulge: XY) => (fr: number, rest: XY): XY => {
  const u = ramp(fr, go, land), back = 0.06 * ramp(fr, go - HIT - 12, go - HIT) * (1 - u), arc = Math.sin(Math.PI * u);
  return { x: rest.x + (to.x - rest.x) * (u - back) + bulge.x * arc, y: rest.y + (to.y - rest.y) * (u - back) + bulge.y * arc };
};

const need = blob({
  from: MERGE, to: B[13].start,
  path: (fr) => {
    const u = ramp(fr, MERGE + 4, RISEN);
    return { x: lerp(FOLD.x, P.wide.x, u), y: lerp(FOLD.y, P.wide.y, u), r: lerp(16, 110, ramp(fr, MERGE + 2, MERGE + 16, arrive)) + (NEED_R - 110) * ramp(fr, MERGE, RISEN) };
  },
  hits: [T12.goA, T12.goB],
  // Aimed short of each chest: the jelly carries on past where it is sent.
  split: {
    at: SPLIT,
    to: [
      fly(T12.goA, T12.catchA, { x: EAGLE_HOLD.x + 30, y: EAGLE_HOLD.y - 120 }, { x: -120, y: -260 }),
      fly(T12.goB, T12.catchB, { x: OWL_HOLD.x + 50, y: OWL_HOLD.y - 50 }, { x: 300, y: -120 }),
    ],
  },
});

// One half of the split need on its own, shrunk about its centre as it is handed over.
const halfSim = (k: number, s: (fr: number) => number) => (fr: number): BlobFrame => {
  const rings = need(fr).rings, ring = rings[k] ?? rings[0], z = s(fr);
  return { rings: [{ ...ring, r: ring.r * z, pts: ring.pts.map((v, i) => (i % 2 ? ring.y : ring.x) + (v - (i % 2 ? ring.y : ring.x)) * z) }] };
};
const handOver = (go: number, land: number) => (fr: number) => lerp(1, 0.46, ramp(fr, go, land)) * (1 - ramp(fr, land, land + 5, depart));
const HALVES = [
  { name: ["Pola", "transaksi"], nameAt: T12.nameA, go: T12.goA, land: T12.catchA, size: handOver(T12.goA, T12.catchA) },
  { name: ["Catatan"], nameAt: T12.nameB, go: T12.goB, land: T12.catchB, size: handOver(T12.goB, T12.catchB) },
].map((h, k) => ({ ...h, sim: halfSim(k, h.size) }));

/** A label on a blob, sized as NeedBlob sizes its own, with an opacity of its own. */
const BlobText: React.FC<{ ring: { x: number; y: number; r: number }; lines: string[]; opacity: number }> = ({ ring, lines, opacity }) => {
  if (opacity < 0.01 || ring.r < 1) return null;
  const fs = Math.min(0.4 * ring.r, (1.62 * ring.r) / (0.56 * Math.max(...lines.map((l) => l.length))));
  return (
    <Draw opacity={opacity}>
      {lines.map((l, i) => (
        <text key={i} x={ring.x} y={ring.y + fs * 0.35 + (i - (lines.length - 1) / 2) * fs * 1.08} textAnchor="middle" fontFamily={FONT} fontWeight={700} fontSize={fs} fill={C.ground}>{l}</text>
      ))}
    </Draw>
  );
};

const Need: React.FC<BeatProps> = ({ fr }) => {
  if (fr < SPLIT) {
    return (
      <>
        {fr >= MERGE + 2 && <NeedBlob sim={need} fr={fr} />}
        <BlobText ring={need(fr).rings[0]} lines={["Kebutuhan"]} opacity={ramp(fr, MERGE + 12, MERGE + 24) * (1 - ramp(fr, PINCH - 10, PINCH - 2))} />
      </>
    );
  }
  return (
    <>
      {HALVES.map((h, k) => {
        const z = h.size(fr);
        if (z < 0.02) return null;
        const ring = h.sim(fr).rings[0], flying = u01((fr - h.go) / 3) * u01((h.land + 5 - fr) / 5);
        return (
          <React.Fragment key={k}>
            {flying > 0 && (
              <Draw>
                {Array.from({ length: 16 }, (_, j) => {
                  const i = 16 - j, past = h.sim(fr - i * 0.5).rings[0];
                  return <circle key={i} cx={past.x} cy={past.y} r={past.r * (0.9 - 0.045 * i)} fill={C.cream} opacity={0.13 * flying * (1 - i / 17)} />;
                })}
              </Draw>
            )}
            <NeedBlob sim={h.sim} fr={fr} glow={1 + 2.5 * flying} />
            <BlobText ring={ring} lines={h.name} opacity={ramp(fr, h.nameAt, h.nameAt + 10) * u01((h.land + 2 - fr) / 4)} />
          </React.Fragment>
        );
      })}
    </>
  );
};

// A creature catching its half: it braces as the blob comes in, then gives a pleased hop.
const catchAt = (fr: number, E: number) => {
  const h = hop(fr, E, 70, 12, 0.11, 8);
  return { dy: h.y, squash: h.squash, tilt: -6 * ramp(fr, E - HIT - 8, E - HIT) * (1 - ramp(fr, E, E + 10)) + bounce(fr, E + 12, 60, 2.5, 6) };
};
const TAGS_OUT = B[13].start;
const busy = (fr: number, E: number) => ramp(fr, E, E + 10) * (1 - ramp(fr, TAGS_OUT, TAGS_OUT + 15, depart));

const Catchers: React.FC<BeatProps> = ({ fr }) => {
  const e = catchAt(fr, T12.catchA), o = catchAt(fr, T12.catchB);
  const out = ramp(fr, TAGS_OUT, TAGS_OUT + 15, depart);
  return (
    <>
      <Halo x={EAGLE_HOLD.x} y={EAGLE_HOLD.y} rx={330} color={KIND.spesialis.color} opacity={0.3 * busy(fr, T12.catchA)} />
      <Halo x={OWL_HOLD.x} y={OWL_HOLD.y} rx={330} color={KIND.ringan.color} opacity={0.3 * busy(fr, T12.catchB)} />
      <Eagle {...HOME.eagle} y={HOME.eagle.y + e.dy} squash={e.squash} tilt={e.tilt} t={fr} />
      <Owl {...HOME.owl} y={HOME.owl.y + o.dy} squash={o.squash} tilt={-o.tilt} t={fr} />
      <Flash fr={fr} E={T12.catchA} {...EAGLE_HOLD} r={420} color={KIND.spesialis.color} amp={0.75} />
      <Burst fr={fr} E={T12.catchA} seed="catchA" n={9} {...EAGLE_HOLD} colors={[C.cream, C.gold, C.goldLight]} speed={[500, 1100]} size={[18, 34]} life={1.5} />
      <Flash fr={fr} E={T12.catchB} {...OWL_HOLD} r={420} color={KIND.ringan.color} amp={0.75} />
      <Burst fr={fr} E={T12.catchB} seed="catchB" n={9} {...OWL_HOLD} colors={[C.cream, C.sky, C.ink]} speed={[500, 1100]} size={[18, 34]} life={1.5} />
      {out < 1 && (
        <div style={{ position: "absolute", left: 0, top: 0, opacity: 1 - out, transform: `translateY(${-50 * out}px)` }}>
          <Tag text="Pola transaksi + pilih produk" color={KIND.spesialis.color} size={66} x={HOME.eagle.x + 60} y={HOME.eagle.y - 470} fr={fr} start={T12.catchA + 5} />
          <Tag text="Catatan untuk Bu Rina" color={KIND.ringan.color} size={66} x={HOME.owl.x} y={HOME.owl.y - 500} fr={fr} start={T12.catchB + 5} />
        </div>
      )}
    </>
  );
};

// The whale's doze: a slow yawn that lifts and stretches it, then it sinks a little and sleeps. It is back at
// its home pose, awake, by the time beat 14 takes over.
const WAKE = B[13].until;
const dozeAt = (fr: number) => {
  const up = ramp(fr, T12.yawn, T12.yawn + 24) * (1 - ramp(fr, T12.yawn + 28, T12.yawn + 56));
  const asleep = ramp(fr, T12.yawn + 26, T12.yawn + 60) * (1 - ramp(fr, WAKE - 30, WAKE));
  return {
    y: HOME.whale.y - 34 * up + 46 * asleep, squash: -0.1 * up + 0.03 * ramp(fr, T12.yawn - 12, T12.yawn) * (1 - ramp(fr, T12.yawn, T12.yawn + 8)) + asleep * 0.016 * Math.sin((fr / FPS) * 1.5),
    tilt: 7 * up - 2.5 * asleep, asleep,
  };
};
const WHALE_EYE = { x: 192, y: 19.8, w: 51, h: 33, lid: "#fe684f" };

const DozingWhale: React.FC<BeatProps> = ({ fr }) => {
  const d = dozeAt(fr), [sx, sy] = sq(d.squash), k = HOME.whale.scale;
  return (
    <>
      <Whale {...HOME.whale} y={d.y} squash={d.squash} tilt={d.tilt} idle={1 - d.asleep} t={fr} />
      {d.asleep > 0.03 && (
        <div style={{ position: "absolute", left: HOME.whale.x, top: d.y, width: 0, height: 0, transform: `rotate(${d.tilt}deg) scale(${-k * sx}, ${k * sy})` }}>
          <div style={{ position: "absolute", left: WHALE_EYE.x, top: WHALE_EYE.y, width: WHALE_EYE.w, height: WHALE_EYE.h * 0.86 * d.asleep, overflow: "hidden" }}>
            <div style={{ width: WHALE_EYE.w, height: WHALE_EYE.h, borderRadius: "50%", background: WHALE_EYE.lid }} />
          </div>
        </div>
      )}
      <Draw>
        {[0, 1, 2].map((i) => {
          const q = (fr - (T12.yawn + 44) - i * 30) / 90;
          if (q < 0) return null;
          const p = q % 1;
          return (
            <text key={i} x={HOME.whale.x - 330 + 150 * p + 26 * Math.sin(p * 5 + i)} y={d.y - 330 - 330 * p} textAnchor="middle" fontFamily={FONT} fontWeight={700}
              fontSize={70 + 60 * p} fill={C.cream} opacity={0.75 * Math.sin(Math.PI * p) * d.asleep}>z</text>
          );
        })}
      </Draw>
    </>
  );
};

// ---------- Beat 13: 97% ----------

const T13 = {
  build: at(13, "AI"), count: at(13, "menghemat"), drain: at(13, "sembilan"), land: at(13, "persen"), caption: at(13, "biaya"),
  spare: at(13, "cadangan"), sheet: at(13, "Hasilnya"), stamp: at(13, "diaudit"),
};
const TOWER = { x: P.shore.x - 140, levels: 11, size: 130 };
const SMALL_BOX = { x: (P.perch.x + P.branch.x) / 2, y: GROUND, size: 110 };
const SPARE_X = SMALL_BOX.x + 170;
const COUNTER = { x: P.wide.x, y: P.wide.y - 30, size: 400 };
const SHEET = { x: (SMALL_BOX.x + SPARE_X) / 2, y: GROUND - 470, w: 280, h: 350 };
const MARK = { x: 40, y: 66 };

const drained = (fr: number) => ramp(fr, T13.drain, T13.land);
const towerX = (fr: number) => lerp(TOWER.x, SMALL_BOX.x, drained(fr));

/** The GPU tower: built level by level, then drained from the top while its base glides to the small box. */
const Tower: React.FC<BeatProps> = ({ fr }) => {
  const u = drained(fr), size = lerp(TOWER.size, SMALL_BOX.size, u), left = 1 + (TOWER.levels - 1) * (1 - u);
  const landing = bounce(fr, T13.land, 2.2, 3.5, 9);
  let top = GROUND;
  const cubes = Array.from({ length: TOWER.levels }, (_, k) => {
    const built = sp(fr, T13.build + 3 * k), s = Math.min(1.12, built.v) * (k === 0 ? 1 : arrive(u01(left - k)));
    const y = top;
    top -= 0.56 * size * Math.min(1, s);
    if (s <= 0.01) return null;
    // Upper levels trail the base as it glides.
    return <GpuCube key={k} x={towerX(fr - k * 0.12) + (k % 2 ? 1 : -1) * size * 0.03 * (1 - u)} y={y} size={size * s} squash={k === 0 ? landing : 0} glow={0} />;
  });
  return (
    <>
      <Halo x={towerX(fr)} y={(GROUND + top) / 2} rx={size * 1.9} ry={(GROUND - top) * 0.62 + size} opacity={0.3 * sp(fr, T13.build, SOFT).v + 0.3 * decay(fr, T13.land, 5)} />
      {cubes}
    </>
  );
};

const Counter: React.FC<BeatProps> = ({ fr }) => {
  const v = sp(fr, T13.count, SOFT).v;
  if (v <= 0.001) return null;
  const hit = bounce(fr, T13.land, 2.4, 3, 7), lit = decay(fr, T13.land, 3);
  return (
    <>
      <Flash fr={fr} E={T13.land} x={COUNTER.x} y={COUNTER.y} r={900} color={C.gold} amp={0.4} />
      <div style={{
        position: "absolute", left: COUNTER.x - 700, top: COUNTER.y - COUNTER.size / 2 + (1 - v) * 40, width: 1400, textAlign: "center", fontFamily: FONT, fontWeight: 700,
        fontSize: COUNTER.size, lineHeight: 1, fontVariantNumeric: "tabular-nums", color: mixC(C.gold, C.goldLight, lit), opacity: v,
        transform: `scale(${(0.9 + 0.1 * v) * (1 + hit)})`, textShadow: `0 0 ${(40 + 80 * lit).toFixed(0)}px ${mixC(C.ground, C.gold, 0.25 + 0.5 * lit)}`,
      }}>{Math.round(97 * drained(fr))}%</div>
      <Label text="biaya hardware" x={COUNTER.x} y={COUNTER.y + COUNTER.size / 2 + 70} size={84} fr={fr} start={T13.caption} />
    </>
  );
};

const AuditSheet: React.FC<BeatProps> = ({ fr }) => {
  const v = sp(fr, T13.sheet);
  if (v.v <= 0.001) return null;
  const E = T13.stamp, [sx, sy] = sq(bounce(fr, E, 1.8, 3.5, 9) - 0.02 * v.vel);
  const hover = ramp(fr, E - HIT - 16, E - HIT - 10, arrive), wind = ramp(fr, E - HIT - 10, E - HIT);
  const k = fr < E ? 1.4 + 0.14 * wind : 1.54 - 0.54 * settle((fr - E) / FPS);
  return (
    <>
      <Draw>
        <g transform={`translate(${SHEET.x} ${SHEET.y + SHEET.h / 2 + 14 * Math.sin(fr / 38)}) scale(${v.v * sx} ${v.v * sy}) translate(0 ${-SHEET.h / 2})`}>
          <rect x={-SHEET.w / 2} y={-SHEET.h / 2} width={SHEET.w} height={SHEET.h} rx={28} fill={C.card} stroke={C.line} strokeWidth={5} />
          <text x={-SHEET.w / 2 + 34} y={-SHEET.h / 2 + 98} fontFamily={FONT} fontWeight={700} fontSize={78} fill={C.ink}>Audit</text>
          {[0, 1, 2].map((i) => <rect key={i} x={-SHEET.w / 2 + 34} y={-34 + i * 44} width={i === 2 ? 90 : i === 1 ? 150 : 212} height={16} rx={8} fill={C.line} />)}
          {hover > 0 && (
            <g transform={`translate(${MARK.x} ${MARK.y - 46 * (k - 1)}) rotate(-10) scale(${k})`} opacity={hover * (0.45 + 0.55 * ramp(fr, E - 1, E + 1))}>
              <circle r={78} fill={C.card} stroke={C.gold} strokeWidth={13} />
              <path d="M -35 3 L -10 30 L 38 -28" fill="none" stroke={C.goldLight} strokeWidth={18} strokeLinecap="round" strokeLinejoin="round" />
            </g>
          )}
        </g>
      </Draw>
      <Flash fr={fr} E={E} x={SHEET.x + MARK.x} y={SHEET.y + MARK.y} r={380} color={C.gold} amp={0.6} />
      <Burst fr={fr} E={E} seed="audit" n={8} x={SHEET.x + MARK.x} y={SHEET.y + MARK.y} colors={[C.gold, C.goldLight, C.cream]} speed={[420, 900]} size={[16, 30]} life={1.4} />
    </>
  );
};

const Savings: React.FC<BeatProps> = ({ fr }) => {
  const spare = sp(fr, T13.spare);
  // Only the two boxes stay for beat 14: the figures and the sheet leave before it mounts.
  const out = ramp(fr, B[13].until - 10, B[13].until - 1, depart);
  return (
    <>
      {spare.v > 0.001 && <GpuCube x={SPARE_X} y={GROUND} size={SMALL_BOX.size * spare.v} squash={-Math.max(-0.2, Math.min(0.2, spare.vel * 0.03))} />}
      <div style={{ position: "absolute", left: 0, top: 0, opacity: 1 - out }}>
        <Counter fr={fr} />
        <Label text="Pusat data cadangan" x={(SMALL_BOX.x + SPARE_X) / 2} y={GROUND + 100} size={66} fr={fr} start={T13.spare + 5} />
        <AuditSheet fr={fr} />
      </div>
    </>
  );
};

// ---------- Camera nudges ----------

const NUDGES: [number, number, number][] = [
  [T11.snap, 1, 0], [T12.catchA, 0, 1], [T12.catchB, 0, 1], [T13.land, 0, 1], [T13.stamp, 0, 1],
];
/** Camera nudge in screen px for beats 10–13, added to the camera by AiPas: about 3 px on each impact. */
export const nudgeD = (fr: number): [number, number] =>
  NUDGES.reduce<[number, number]>(([x, y], [E, dx, dy]) => {
    const n = bounce(fr, E, 170, 5, 12);
    return [x + dx * n, y + dy * n];
  }, [0, 0]);

// ---------- Beats ----------

export const Beat10: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Residents t={fr} />
    {fr < B[10].start + 44 && PILES_9.map(({ label, ...p }) => (
      <React.Fragment key={p.seed}>
        <GpuPile {...p} y={GROUND} fr={fr} />
        <Label text={label} x={p.x} y={GROUND + 84} size={46} color={C.gold} />
      </React.Fragment>
    ))}
    <Bank fr={fr} />
  </>
);

export const Beat11: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Residents t={fr} />
    <Bank fr={fr} />
  </>
);

export const Beat12: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Residents t={fr} hide={["eagle", "owl", "whale"]} />
    {fr < RISEN + 6 && <Bank fr={fr} />}
    <Catchers fr={fr} />
    <DozingWhale fr={fr} />
    <Need fr={fr} />
  </>
);

export const Beat13: React.FC<BeatProps> = ({ fr }) => (
  <>
    <Tower fr={fr} />
    <Residents t={fr} hide={["eagle", "owl", "whale"]} />
    <Catchers fr={fr} />
    <DozingWhale fr={fr} />
    <Savings fr={fr} />
  </>
);
