import { AbsoluteFill, Easing, Img, interpolate, random, spring, staticFile, useCurrentFrame } from "remotion";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { loadFont } from "@remotion/google-fonts/Fredoka";
import { squashAlong } from "../../motion";
import { trailingShift } from "../shared";
import { BODIES, BodyFrame, DURATION_S, FPS, frameAt, R0, T } from "./sim";

const { fontFamily } = loadFont("normal", { weights: ["600"], subsets: ["latin"] });

export const cellDuration = DURATION_S * FPS;
export const cellFps = FPS;

const BG = "#19294a";
const CX = 960;
const CY = 540;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const arrive = Easing.bezier(0.2, 0, 0, 1);
const CHR = { main: "#f9ab14", shade: "#f87d12", hi: "#fad36c" };
const STAR = "#fff3c4";

// Inertial bounce (Dan Ebberts): decaying sine after an impulse.
const bounce = (t: number, v: number, freq = 3, decay = 5) => {
  if (t < 0) return 0;
  const w = freq * 2 * Math.PI;
  return (v * Math.sin(t * w)) / Math.exp(decay * t) / w;
};
const decayFrom = (t: number, start: number, rate: number) => (t < start ? 0 : Math.exp(-(t - start) * rate));

// Original pixel size of each traced part (art/parts/assets.json) and display scale.
const SIZE: Record<string, [number, number, number]> = {
  a00: [332, 332, 0.5],
  a03: [320, 216, 0.42],
  a04: [216, 312, 0.42],
  a05: [320, 232, 0.42],
  a06: [348, 224, 0.4],
  a09: [184, 180, 0.4],
  a10: [184, 180, 0.4],
};
const BASE_ROT: Record<string, number> = { mitoA: -12, mitoV2: 8, mitoB: 14, mitoC: -10 };

// Smooth closed (or open) path through points with Catmull-Rom tangents.
const smooth = (p: [number, number][], closed: boolean) => {
  const n = p.length;
  const at = (i: number) => (closed ? p[(i + n) % n] : p[Math.max(0, Math.min(n - 1, i))]);
  let d = `M ${at(0)[0]} ${at(0)[1]}`;
  for (let i = 0; i < (closed ? n : n - 1); i++) {
    const [p0, p1, p2, p3] = [at(i - 1), at(i), at(i + 1), at(i + 2)];
    d += ` C ${p1[0] + (p2[0] - p0[0]) / 6} ${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6} ${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]} ${p2[1]}`;
  }
  return closed ? d + " Z" : d;
};

const Membrane: React.FC<{ pts: number[]; id: string; glow: number }> = ({ pts, id, glow }) => {
  const p: [number, number][] = [];
  for (let i = 0; i < pts.length; i += 2) p.push([CX + pts[i], CY + pts[i + 1]]);
  const cx = p.reduce((a, q) => a + q[0], 0) / p.length;
  const cy = p.reduce((a, q) => a + q[1], 0) / p.length;
  const size = Math.sqrt(p.reduce((a, q) => a + (q[0] - cx) ** 2 + (q[1] - cy) ** 2, 0) / p.length);
  const outline = smooth(p, true);
  const k = size / R0;
  // Highlight follows the deforming outline: the upper-left arc of each lobe, measured from and
  // pulled toward that lobe's own centre, so a peanut gets two arcs and none crosses the neck.
  const xs = p.map((q) => q[0]), ys = p.map((q) => q[1]);
  const excess = (Math.max(...xs) - Math.min(...xs) - (Math.max(...ys) - Math.min(...ys))) / 2;
  const lobe = excess > 60 ? excess : 0; // wobble on a round cell keeps one arc
  const runs = [-1, 1].map((s) => {
    const lx = cx + s * lobe;
    return p
      .filter((q) => lobe === 0 ? s < 0 : Math.sign(q[0] - cx) === s)
      .map((q) => ({ q, a: (Math.atan2(q[1] - cy, q[0] - lx) * 180) / Math.PI }))
      .filter(({ a }) => a > -165 && a < -100)
      .sort((m, n) => m.a - n.a)
      .map(({ q }): [number, number] => [lx + (q[0] - lx) * 0.74, cy + (q[1] - cy) * 0.74]);
  });
  return (
    <g>
      <path d={outline} fill="none" stroke="#73fbd7" strokeWidth={30 * k} opacity={glow} filter="url(#glow)" />
      <clipPath id={id}><path d={outline} /></clipPath>
      <g clipPath={`url(#${id})`}>
        <path d={outline} fill="#5fccb5" />
        <path d={outline} fill="#84e0c9" transform={`translate(${-14 * k} ${-16 * k}) translate(${cx} ${cy}) scale(0.96) translate(${-cx} ${-cy})`} />
        <path d={outline} fill="none" stroke="#199793" strokeWidth={50 * k} />
        <path d={outline} fill="none" stroke="#22c5b4" strokeWidth={33 * k} />
        <path d={outline} fill="none" stroke="#73fbd7" strokeWidth={12 * k} />
      </g>
      {runs.filter((r) => r.length > 2).map((r, i) => (
        <path key={i} d={smooth(r, false)} stroke="#a9f9e2" strokeWidth={19 * Math.min(1, k)} strokeLinecap="round" fill="none" />
      ))}
    </g>
  );
};

const Sprite: React.FC<{ part: string; x: number; y: number; vx: number; vy: number; scale: number; rot?: number; opacity?: number }> = ({
  part, x, y, vx, vy, scale, rot = 0, opacity = 1,
}) => {
  const [w0, h0, k] = SIZE[part];
  const w = w0 * k;
  const h = h0 * k;
  // Squash and stretch along the direction of travel (area kept), plus a lean into the motion.
  const lean = Math.max(-14, Math.min(14, vx / 30));
  return (
    <Img
      src={staticFile(`illustrated/cell/${part}.svg`)}
      style={{
        position: "absolute", left: CX + x - w / 2, top: CY + y - h / 2, width: w, height: h, opacity,
        transform: `${squashAlong(vx, vy, 1 / 1600, 0.22, scale)} rotate(${rot + lean}deg)`,
      }}
    />
  );
};

// One sister chromatid: two arms bent through the centromere; arm tips come from the sim.
const Chromatid: React.FC<{ b: BodyFrame; shift: number; opacity: number }> = ({ b, shift, opacity }) => {
  const tp = b.tips!;
  const X = (v: number) => CX + v + shift;
  const Y = (v: number) => CY + v;
  const qx = 2 * b.x - (tp[0] + tp[4]) / 2, qy = 2 * b.y - (tp[1] + tp[5]) / 2;
  const d = `M ${X(tp[0])} ${Y(tp[1])} Q ${X(qx)} ${Y(qy)} ${X(tp[4])} ${Y(tp[5])}`;
  const s = b.scale;
  return (
    <g opacity={opacity}>
      <path d={d} transform="translate(1.5 2.5)" stroke={CHR.shade} strokeWidth={17 * s} strokeLinecap="round" fill="none" />
      <path d={d} stroke={CHR.main} strokeWidth={14 * s} strokeLinecap="round" fill="none" />
      <path d={d} transform="translate(-2.5 -2.5)" stroke={CHR.hi} strokeWidth={4 * s} strokeLinecap="round" fill="none"
        pathLength={100} strokeDasharray="0 12 24 28 24 12" />
      <circle cx={X(b.x)} cy={Y(b.y)} r={5 * s} fill={CHR.shade} />
    </g>
  );
};

const Centrosome: React.FC<{ x: number; y: number; scale: number; t: number; seed: number; opacity: number }> = ({ x, y, scale, t, seed, opacity }) => (
  <g transform={`translate(${CX + x} ${CY + y}) scale(${scale})`} opacity={opacity}>
    {Array.from({ length: 9 }, (_, k) => {
      const a = ((k * 40 + t * 8 + seed * 20) * Math.PI) / 180;
      const len = 26 + 6 * Math.sin(t * 1.1 + k * 1.7 + seed);
      return <line key={k} x1={Math.cos(a) * 13} y1={Math.sin(a) * 13} x2={Math.cos(a) * (13 + len)} y2={Math.sin(a) * (13 + len)}
        stroke={STAR} strokeWidth={2} strokeLinecap="round" opacity={0.35} />;
    })}
    <circle r={26} fill="url(#starGlow)" />
    <circle r={8} fill={STAR} />
  </g>
);

// Depth: far out-of-focus cells and two dot layers behind, a few big bokeh dots in front.
const Dots: React.FC<{ t: number; layer: string; count: number; size: [number, number]; opacity: [number, number]; speed: number; blur: number }> = ({
  t, layer, count, size, opacity, speed, blur,
}) => (
  <>
    {Array.from({ length: count }, (_, i) => {
      const r = (k: string) => random(`${layer}${k}${i}`);
      const s = size[0] + r("s") * (size[1] - size[0]);
      const x = r("x") * 2100 - 90 + 20 * Math.sin(t * 0.2 + i);
      const y = ((r("y") * 1300 - t * speed * (0.6 + r("v") * 0.8)) % 1300 + 1300) % 1300 - 110;
      return (
        <div key={i} style={{
          position: "absolute", left: x, top: y, width: s, height: s, borderRadius: s, background: "#7fb6ff",
          opacity: opacity[0] + r("o") * (opacity[1] - opacity[0]), filter: blur ? `blur(${blur}px)` : undefined,
        }} />
      );
    })}
  </>
);
const FAR_CELLS: [number, number, number][] = [[230, 190, 140], [1690, 240, 185], [1610, 900, 120], [300, 890, 165]];
const FarCells: React.FC<{ t: number }> = ({ t }) => (
  <>
    {FAR_CELLS.map(([x, y, r], i) => (
      <div key={i} style={{
        position: "absolute", left: x - r + 18 * Math.sin(t * 0.15 + i * 2), top: y - r + 14 * Math.sin(t * 0.11 + i), width: 2 * r, height: 2 * r,
        borderRadius: "50%", background: "rgba(95,204,181,0.035)", border: "10px solid rgba(115,251,215,0.045)", filter: "blur(16px)",
      }} />
    ))}
  </>
);

// Bits that fly out from a point, decelerate, then drift and fade slowly (they stay a while).
const Burst: React.FC<{ t: number; start: number; seed: string; n: number; x: number; y: number; speed: [number, number]; size: [number, number]; colors: string[]; life: number; vertical?: boolean }> = ({
  t, start, seed, n, x, y, speed, size, colors, life, vertical,
}) => {
  const tau = t - start;
  if (tau < 0 || tau > life) return null;
  return (
    <>
      {Array.from({ length: n }, (_, i) => {
        const r = (k: string) => random(`${seed}${k}${i}`);
        const a = vertical ? (i % 2 ? -1 : 1) * (Math.PI / 2) + (r("a") - 0.5) * 1.6 : (i / n) * Math.PI * 2 + r("a") * 0.5;
        const v = speed[0] + r("v") * (speed[1] - speed[0]);
        const travel = (v * (1 - Math.exp(-4 * tau))) / 4;
        const px = x + Math.cos(a) * travel + 10 * Math.sin(tau * 0.8 + i);
        const py = y + Math.sin(a) * travel - 14 * tau;
        const s = (size[0] + r("s") * (size[1] - size[0])) * interpolate(tau, [0, 0.12, life], [0.3, 1, 0.5], clamp);
        const o = interpolate(tau, [0, 0.05, 0.5, life], [0, 1, 0.8, 0], clamp);
        return <div key={i} style={{
          position: "absolute", left: CX + px - s / 2, top: CY + py - s / 2, width: s, height: s, borderRadius: s,
          background: colors[i % colors.length], opacity: o, boxShadow: `0 0 ${s}px ${colors[i % colors.length]}`,
        }} />;
      })}
    </>
  );
};

const Title: React.FC<{ frame: number }> = ({ frame }) => {
  const words = ["One", "cell", "becomes", "two."];
  return (
    <div style={{ position: "absolute", top: 890, width: "100%", textAlign: "center", fontFamily, fontSize: 64, color: "#eaf6ff" }}>
      {words.map((w, i) => {
        const t = spring({ frame: frame - T.title * FPS - 8 * i, fps: FPS, config: { damping: 12, stiffness: 180, mass: 0.6 } });
        return (
          <span key={i} style={{
            display: "inline-block", margin: "0 12px", opacity: Math.min(1, t * 1.5),
            transform: `translateY(${(1 - t) * 30}px) scale(${0.6 + 0.4 * t})`,
          }}>{w}</span>
        );
      })}
    </div>
  );
};

const SHUTTER = 180;
const SAMPLES = 6;
const SHIFT = trailingShift(SHUTTER, SAMPLES);

// Parallax layer transform at depth f (1 = the cell's plane).
const camera = (t: number) => {
  const camScale = interpolate(t, [0, 8, 15.7, 20], [1, 1.18, 1, 0.94], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const camY = interpolate(t, [15.7, 19], [0, -50], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const nudge = bounce(t - T.pinch, 80) + bounce(t - T.burst, 35);
  return (f: number) => ({
    position: "absolute" as const, inset: 0,
    transform: `translateY(${(camY + nudge) * f}px) scale(${1 + (camScale - 1) * f})`,
  });
};

// Only the cell plane is motion-blurred: slow background and foreground layers render once, which keeps
// their faint gradients free of the 8-bit banding that summing 1/SAMPLES-opacity copies causes.
export const Cell: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const layer = camera(t);
  // Payoff light (flash, saturation spike) is not motion: applied once per frame, outside the blur.
  const flash = decayFrom(t, T.pinch, 9) * 0.6 + decayFrom(t, T.burst, 10) * 0.25;
  const hit = decayFrom(t, T.pinch, 5);
  return (
    <AbsoluteFill style={{ background: BG, overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(circle at 50% 50%, rgba(60,200,190,0.18) 0%, rgba(25,41,74,0) 45%)" }} />
      <div style={layer(0.3)}><FarCells t={t} /></div>
      <div style={layer(0.5)}><Dots t={t} layer="far" count={45} size={[1.5, 3]} opacity={[0.12, 0.3]} speed={8} blur={0} /></div>
      <div style={layer(0.8)}><Dots t={t} layer="mid" count={20} size={[3, 6]} opacity={[0.25, 0.45]} speed={18} blur={0} /></div>
      <div style={{ position: "absolute", inset: 0, filter: `saturate(${1 + 0.4 * hit}) brightness(${1 + 0.1 * decayFrom(t, T.pinch, 8)})` }}>
        <CameraMotionBlur shutterAngle={SHUTTER} samples={SAMPLES}>
          <Scene />
        </CameraMotionBlur>
        {flash > 0.01 && (
          <svg width={1920} height={1080} style={{ ...layer(1), overflow: "visible", mixBlendMode: "screen" }}>
            <defs><radialGradient id="flash"><stop offset="0%" stopColor="#ffffff" stopOpacity={1} /><stop offset="100%" stopColor="#ffffff" stopOpacity={0} /></radialGradient></defs>
            <circle cx={CX} cy={CY} r={260} fill="url(#flash)" opacity={flash} />
          </svg>
        )}
      </div>
      <div style={layer(1.3)}><Dots t={t} layer="near" count={7} size={[18, 40]} opacity={[0.05, 0.1]} speed={30} blur={8} /></div>
      <Title frame={frame} />
    </AbsoluteFill>
  );
};

const Scene: React.FC = () => {
  const frame = useCurrentFrame() - SHIFT;
  const t = frame / FPS;
  // Output frame's own time: light changes (flash, saturation) land whole on their frame, not smeared.
  const tLight = Math.ceil(frame - 1e-6) / FPS;
  const state = frameAt(frame);
  const layer = camera(t);
  // All samples share one DOM: clip-path ids must differ per sample or every copy clips to the first.
  const uid = Math.round(frame * 120);

  // Nucleus: dips (anticipation), swells, holds through the hit-pause, then its envelope pops.
  const pulse = interpolate(t, [3.05, 3.3, 3.9], [1, 0.96, 1.1], { ...clamp, easing: Easing.inOut(Easing.quad) });
  const pop = interpolate(t, [T.burst, T.burst + 0.15], [0, 1], { ...clamp, easing: Easing.out(Easing.quad) });
  const fadeChr = interpolate(t, [T.telophase, T.newNuclei + 0.05], [1, 0], clamp);
  const fadeSpindle = interpolate(t, [13.4, 14.2], [1, 0], clamp);

  // Payoff: flash, saturation spike and glow boost at pinch-off.
  const hit = decayFrom(tLight, T.pinch, 5);
  const glow = 0.22 + 0.6 * hit;
  // Contractile ring: the two furrow tips glow brighter as tension builds.
  const tension = interpolate(t, [11, 13.15], [0, 1], { ...clamp, easing: Easing.in(Easing.quad) });

  const centro = (side: number) => BODIES.findIndex((b) => b.id === `centro${side}`);

  return (
    <div style={layer(1)}>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation={16} /></filter>
            <radialGradient id="starGlow"><stop offset="0%" stopColor={STAR} stopOpacity={0.8} /><stop offset="100%" stopColor={STAR} stopOpacity={0} /></radialGradient>
          </defs>
          {state.rings.map((r, i) => <Membrane key={i} pts={r.pts} id={`m${i}-${uid}`} glow={glow} />)}
          {state.rings.length === 1 && tension > 0 && [16, 48].map((i) => (
            <g key={i} transform={`translate(${CX + state.rings[0].pts[2 * i]} ${CY + state.rings[0].pts[2 * i + 1]})`}>
              <circle r={30} fill="url(#starGlow)" opacity={tension} />
              <circle r={6} fill={STAR} opacity={tension} />
            </g>
          ))}
        </svg>
        {BODIES.map((spec, i) => {
          const b = state.bodies[i];
          if (!b.alive || !SIZE[spec.part]) return null;
          return (
            <Sprite key={spec.id} part={spec.part} x={b.x} y={b.y} vx={b.vx} vy={b.vy}
              scale={b.scale * (spec.id === "nucleus" ? pulse : spec.id.startsWith("nucleus") ? 0.8 : 1)}
              rot={BASE_ROT[spec.id] ?? 0} />
          );
        })}
        {t >= T.burst && pop < 1 && <Sprite part="a00" x={0} y={0} vx={0} vy={0} scale={1.1 + 0.35 * pop} opacity={1 - pop} />}
        <Burst t={t} start={T.burst} seed="env" n={10} x={0} y={0} speed={[180, 320]} size={[9, 17]} colors={["#a868d0", "#8840b8", "#d0a8e8"]} life={1.6} />
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
          {BODIES.map((spec, i) => {
            const b = state.bodies[i];
            const c = state.bodies[centro(spec.side)];
            if (!spec.chromatid || !b.alive || !c?.alive) return null;
            const k = Number(spec.id[3]);
            const g = interpolate(t, [T.poles + 0.05 * k, T.plate + 0.12 * k], [0, 1], { ...clamp, easing: arrive });
            if (g <= 0) return null;
            const ex = c.x + (b.x - c.x) * g, ey = c.y + (b.y - c.y) * g;
            const len = Math.hypot(ex - c.x, ey - c.y) || 1;
            const bow = 7 * Math.sin(t * 1.3 + k);
            const mx = (c.x + ex) / 2 - ((ey - c.y) / len) * bow, my = (c.y + ey) / 2 + ((ex - c.x) / len) * bow;
            return <path key={spec.id} d={`M ${CX + c.x} ${CY + c.y} Q ${CX + mx} ${CY + my} ${CX + ex} ${CY + ey}`}
              stroke="#d9fff4" strokeWidth={2.5} strokeLinecap="round" fill="none" opacity={0.5 * fadeSpindle} />;
          })}
          {BODIES.map((spec, i) => {
            const b = state.bodies[i];
            if (!spec.chromatid || !b.alive) return null;
            return <Chromatid key={spec.id} b={b} shift={t < T.anaphase ? spec.side * 3 : 0} opacity={fadeChr} />;
          })}
          {([-1, 1] as const).map((side) => {
            const b = state.bodies[centro(side)];
            return b.alive && <Centrosome key={side} x={b.x} y={b.y} scale={b.scale} t={t} seed={side} opacity={fadeSpindle} />;
          })}
        </svg>
        <Burst t={t} start={T.pinch} seed="pinch" n={10} x={0} y={0} speed={[260, 520]} size={[5, 11]} colors={["#a9f9e2", "#ffffff", STAR]} life={3.2} vertical />
    </div>
  );
};
