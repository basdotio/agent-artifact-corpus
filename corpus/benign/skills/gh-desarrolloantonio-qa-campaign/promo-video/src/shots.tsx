// Five shot recipes from video-shotcraft, restyled dark and fed with qa-campaign content:
// brand-ink-open, blur-slide, assemble-then-type-flyin, card-flip-reveal, before-after-slider-scrub.
import React from "react";
import { Easing, interpolate, random, useCurrentFrame } from "remotion";
import { Chip, MONO, SANS, clamp, useGlass, useTheme } from "./theme";

// ---- brand-ink-open: crosshair draws, wordmark letterpress, mono kicker types, then lifts away
export const InkOpen = () => {
  const f = useCurrentFrame();
  const C = useTheme();
  const vDraw = interpolate(f, [0, 9], [100, 0], { ...clamp, easing: Easing.bezier(0.3, 0, 0.2, 1) });
  const hDraw = interpolate(f, [8, 18], [100, 0], clamp);
  const cross = interpolate(f, [24, 34], [1, 0], clamp);
  const WORD = "qa-campaign", KICK = "A SKILL FOR CLAUDE CODE";
  const kChars = Math.floor(Math.max(0, f - 24) / 0.7);
  const kDone = 24 + KICK.length * 0.7;
  const cursor = f >= 24 && (f < kDone || Math.floor((f - kDone) / 2) % 2 === 0) && f < 60;
  const out = interpolate(f, [62, 74], [0, 1], { ...clamp, easing: Easing.bezier(0.4, 0, 0.5, 1) });
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", opacity: 1 - out, transform: `translateY(${-out * 40}px) scale(${1 - out * 0.12})` }}>
      <svg width={64} height={64} viewBox="0 0 64 64" style={{ marginBottom: 30, opacity: cross }}>
        <line x1={32} y1={2} x2={32} y2={62} stroke={C.brand} strokeWidth={5} strokeLinecap="round" pathLength={100} strokeDasharray={100} strokeDashoffset={vDraw} />
        <line x1={2} y1={32} x2={62} y2={32} stroke={C.brand} strokeWidth={5} strokeLinecap="round" pathLength={100} strokeDasharray={100} strokeDashoffset={hDraw} />
      </svg>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 150, color: C.ink, letterSpacing: "-0.03em", display: "inline-flex", whiteSpace: "pre" }}>
        {WORD.split("").map((ch, i) => {
          const d = 8 + i * 3;
          const t = interpolate(f, [d, d + 12], [0, 1], { ...clamp, easing: Easing.bezier(0.2, 0.7, 0.25, 1) });
          const g = interpolate(f, [d + 8, d + 12, d + 16], [0, 1, 0], clamp);
          return (
            <span key={i} style={{ position: "relative", display: "inline-block", opacity: t, transform: `scale(${1.6 - 0.6 * t})`, transformOrigin: "center bottom", filter: `blur(${(1 - t) * 6}px)` }}>
              {ch}
              <span style={{ position: "absolute", left: "50%", bottom: -6, transform: "translateX(-50%)", width: `${g * 100}%`, height: 3, background: C.brand, opacity: g, borderRadius: 2 }} />
            </span>
          );
        })}
      </div>
      <div style={{ fontFamily: MONO, fontSize: 28, letterSpacing: "0.16em", color: C.muted, marginTop: 34, height: 32, display: "flex", alignItems: "center" }}>
        <span style={{ whiteSpace: "pre" }}>{KICK.slice(0, kChars)}</span>
        <span style={{ display: "inline-block", width: 14, height: 26, marginLeft: 6, background: C.brand, opacity: cursor ? 0.85 : 0 }} />
      </div>
    </div>
  );
};

// ---- blur-slide: words rise in one after another (y + blur + opacity on one ease)
export type W = { t: string; c?: string };
export const BlurLine = ({ words, start, gap, dy = 30, style }: { words: W[]; start: number; gap: number; dy?: number; style?: React.CSSProperties }) => {
  const f = useCurrentFrame();
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0 0.3em", ...style }}>
      {words.map((w, i) => {
        const p = interpolate(f, [start + i * gap, start + i * gap + 14], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
        return <span key={i} style={{ color: w.c, opacity: p, transform: `translateY(${(1 - p) * dy}px)`, filter: `blur(${(1 - p) * 10}px)` }}>{w.t}</span>;
      })}
    </div>
  );
};

// ---- assemble-then-type-flyin: empty shells fly in first, then each character arrives from 3D space
export const ShellIn = ({ at, from, rot, style, children }: { at: number; from: [number, number]; rot: number; style: React.CSSProperties; children?: React.ReactNode }) => {
  const f = useCurrentFrame();
  const a = interpolate(f, [at, at + 26], [0, 1], { ...clamp, easing: Easing.out(Easing.back(1.5)) });
  const o = interpolate(f, [at, at + 6], [0, 1], clamp);
  return <div style={{ position: "absolute", opacity: o, transform: `translate(${(1 - a) * from[0]}px,${(1 - a) * from[1]}px) rotate(${(1 - a) * rot}deg)`, ...style }}>{children}</div>;
};

export const FlyChars = ({ text, start, step = 1.2, seed, style }: { text: string; start: number; step?: number; seed: string; style?: React.CSSProperties }) => {
  const f = useCurrentFrame();
  return (
    <div style={{ whiteSpace: "pre", ...style }}>
      {Array.from(text).map((ch, i) => {
        const r = (k: number) => random(`${seed}-${i}-${k}`);
        const ft = start + i * step;
        const a = interpolate(f, [ft, ft + 14], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
        const b = 1 - a;
        const tf = a >= 1 ? "none" : `perspective(900px) translate3d(${b * (r(1) - 0.5) * 50}px,${b * (r(2) - 0.5) * 36}px,${b * (-40 - r(3) * 60)}px) rotateX(${b * (r(4) - 0.5) * 70}deg) rotateY(${b * (r(5) - 0.5) * 60}deg) rotateZ(${b * (r(6) - 0.5) * 24}deg)`;
        return <span key={i} style={{ display: "inline-block", whiteSpace: "pre", opacity: a > 0 ? Math.min(1, a * 1.8) : 0, transform: tf }}>{ch}</span>;
      })}
    </div>
  );
};

// ---- card-flip-reveal: a card turns 180deg on Y (overshoots to 192, settles), sheen sweeps at the edge
const angleAt = (f: number, s: number) =>
  f < s + 18
    ? interpolate(f, [s, s + 18], [0, 192], { ...clamp, easing: Easing.bezier(0.55, 0, 0.3, 1) })
    : interpolate(f, [s + 18, s + 26], [192, 180], { ...clamp, easing: Easing.out(Easing.poly(5)) });

const Sheen = ({ angle }: { angle: number }) => {
  const C = useTheme();
  const pos = interpolate(angle, [35, 145], [-25, 115], clamp);
  const op = Math.max(0, 1 - Math.abs(angle - 90) / 55);
  if (op <= 0.004) return null;
  return <div style={{ position: "absolute", inset: 0, borderRadius: 20, pointerEvents: "none", opacity: op, background: `linear-gradient(105deg, rgba(${C.sheen},0) ${pos - 14}%, rgba(${C.sheen},0.28) ${pos}%, rgba(${C.sheen},0) ${pos + 14}%)` }} />;
};

export const FlipCard = ({ at, w, h, front, back, style }: { at: number; w: number; h: number; front: React.ReactNode; back: React.ReactNode; style?: React.CSSProperties }) => {
  const f = useCurrentFrame();
  const C = useTheme();
  const glass = useGlass();
  const angle = angleAt(f, at);
  const face: React.CSSProperties = { position: "absolute", inset: 0, backfaceVisibility: "hidden", ...glass, background: C.panel, boxSizing: "border-box", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14 };
  return (
    <div style={{ position: "absolute", width: w, height: h, perspective: 1200, ...style }}>
      <div style={{ width: "100%", height: "100%", position: "relative", transformStyle: "preserve-3d", transform: `rotateY(${angle}deg)` }}>
        <div style={face}>{front}<Sheen angle={angle} /></div>
        <div style={{ ...face, transform: "rotateY(180deg)" }}>{back}<Sheen angle={angle} /></div>
      </div>
    </div>
  );
};

// ---- three findings (wording from README "What it has found"), each card flies in after the last.
const FINDINGS = [
  { at: 12, n: "1", head: "The release app crashed on launch", sub: "Every screen, every time. The debug build was fine." },
  { at: 48, n: "2", head: "Saving one field silently reverted the others", sub: "The screen said “saved”, and the server agreed." },
  { at: 84, n: "3", head: "Editing an item deleted the tags someone had added from the web", sub: "Found on code a previous campaign had already approved." },
];
export const Findings = () => {
  const C = useTheme();
  const glass = useGlass();
  return (
    <div style={{ position: "relative", width: 1520, height: 360 }}>
      {FINDINGS.map((x, i) => (
        <ShellIn key={x.n} at={x.at} from={[0, 90]} rot={i === 1 ? 0 : i === 0 ? -2 : 2}
          style={{ left: i * 520, top: 0, width: 480, height: 360, ...glass, boxSizing: "border-box", padding: "34px 36px", fontFamily: SANS }}>
          <div style={{ fontFamily: MONO, fontSize: 24, color: C.brand, border: `1.5px solid ${C.brand}`, borderRadius: 999, width: 48, height: 48, display: "flex", alignItems: "center", justifyContent: "center" }}>{x.n}</div>
          <div style={{ fontSize: 36, fontWeight: 700, color: C.ink, lineHeight: 1.2, marginTop: 24 }}>{x.head}</div>
          <div style={{ fontSize: 26, color: C.muted, lineHeight: 1.3, marginTop: 18 }}>{x.sub}</div>
        </ShellIn>
      ))}
    </div>
  );
};

// ---- phone + tablet mock: taps through controls, screenshots in light then dark, then goes offline.
const ctl = (i: number, h: number) => (i < 3 ? { top: 0.16 * h + i * 0.19 * h, height: 0.15 * h } : { top: 0.8 * h, height: 0.1 * h });

const Screen = ({ w, h, dark, hi, rip, done, offline, black, flash }: { w: number; h: number; dark: boolean; hi: number; rip: number; done: number; offline: boolean; black: boolean; flash: number }) => {
  const C = useTheme();
  const bg = dark ? "#12141d" : "#ffffff", fg = dark ? "#eef1fa" : "#1a1a1a", sub = dark ? "#242838" : "#e8eaf0";
  return (
    <div style={{ position: "relative", width: w, height: h, background: black ? "#000" : bg, overflow: "hidden" }}>
      {!black && <>
        <div style={{ position: "absolute", left: 0.06 * w, top: 0.04 * h, width: 0.4 * w, height: 0.035 * h, borderRadius: 4, background: fg, opacity: 0.85 }} />
        {[0, 1, 2, 3].map((i) => {
          const p = ctl(i, h);
          return (
            <div key={i} style={{ position: "absolute", left: 0.06 * w, right: 0.06 * w, top: p.top, height: p.height, borderRadius: 8, background: i === 3 ? C.brand : sub, border: hi === i ? `2px solid ${C.brand}` : "2px solid transparent", boxSizing: "border-box", display: "flex", alignItems: "center", padding: "0 8px", gap: 8 }}>
              {i < 3 && <><div style={{ width: 0.07 * w + 4, height: 0.07 * w + 4, borderRadius: "50%", background: fg, opacity: 0.25 }} /><div style={{ width: 0.4 * w, height: 0.03 * h, borderRadius: 3, background: fg, opacity: 0.5 }} /></>}
              {done > i && <span style={{ marginLeft: "auto", color: C.green, fontSize: Math.max(12, 0.045 * h), fontWeight: 800 }}>✓</span>}
              {hi === i && <div style={{ position: "absolute", left: "50%", top: "50%", width: 10 + rip * 50, height: 10 + rip * 50, marginLeft: -(5 + rip * 25), marginTop: -(5 + rip * 25), borderRadius: "50%", border: `2px solid ${C.brand}`, opacity: 1 - rip }} />}
            </div>
          );
        })}
        {offline && <div style={{ position: "absolute", left: 0, right: 0, top: 0.095 * h, height: 0.05 * h, background: C.red, color: "#fff", fontFamily: SANS, fontSize: Math.max(10, 0.035 * h), display: "flex", alignItems: "center", justifyContent: "center" }}>No connection</div>}
        <div style={{ position: "absolute", inset: 0, background: "#fff", opacity: flash }} />
      </>}
    </div>
  );
};

export const Devices = () => {
  const f = useCurrentFrame();
  const C = useTheme();
  const inA = interpolate(f, [10, 28], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const tab = interpolate(f, [56, 76], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const out = interpolate(f, [166, 180], [1, 0], clamp);
  const tapping = f >= 16 && f < 56;
  const hi = tapping ? Math.min(3, Math.floor((f - 16) / 10)) : -1;
  const done = f < 16 ? 0 : tapping ? hi : 4;
  const rip = tapping ? ((f - 16) % 10) / 10 : 0;
  const dark = f >= 74;
  const flash = Math.max(f >= 60 && f < 68 ? 0.85 * (1 - (f - 60) / 8) : 0, f >= 78 && f < 86 ? 0.85 * (1 - (f - 78) / 8) : 0);
  const offline = f >= 100 && f < 150;
  const black = f >= 116 && f < 124;
  const frameStyle = (r: number): React.CSSProperties => ({ border: `6px solid ${C.ink}`, borderRadius: r, overflow: "hidden", boxShadow: C.shadow, background: C.panel });
  const lab: React.CSSProperties = { fontFamily: MONO, fontSize: 18, color: C.muted, textAlign: "center", marginTop: 12 };
  return (
    <div style={{ position: "absolute", left: 1180, top: 250, width: 490, height: 460, opacity: out, transform: "scale(1.2)", transformOrigin: "top left" }}>
      <div style={{ position: "absolute", left: 0, top: 22, opacity: inA, transform: `translateY(${(1 - inA) * 30}px)` }}>
        <div style={frameStyle(26)}><Screen w={158} h={366} dark={dark} hi={hi} rip={rip} done={done} offline={offline} black={black} flash={flash} /></div>
        <div style={lab}>phone · 411×914</div>
      </div>
      <div style={{ position: "absolute", left: 190, top: 200, opacity: tab, transform: `translateY(${(1 - tab) * 30}px)` }}>
        <div style={frameStyle(16)}><Screen w={288} h={176} dark={dark} hi={-1} rip={0} done={f >= 56 ? 4 : 0} offline={offline} black={false} flash={flash} /></div>
        <div style={lab}>tablet · 1280×800</div>
      </div>
      <div style={{ position: "absolute", left: 190, top: 0, width: 300, textAlign: "center", fontFamily: MONO, fontSize: 20, color: dark ? C.brand : C.muted, opacity: tab }}>{offline ? "network off" : dark ? "dark mode" : "light mode"}</div>
    </div>
  );
};
