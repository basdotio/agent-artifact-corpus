// Design tokens. Everything that looks like a "design" lives here: swap THEMES to restyle a video.
import React, { createContext, useContext } from "react";
import { AbsoluteFill, interpolate, random, useCurrentFrame, useVideoConfig } from "remotion";

const dark = {
  bg: "#07080d", ink: "#eef1fa", muted: "#7d86a3", green: "#3ddc84", red: "#ff4d5e", amber: "#ffb84d", brand: "#3ddc84",
  line: "rgba(255,255,255,0.10)", glass: "rgba(255,255,255,0.045)", panel: "#0c0e15", chip: "rgba(255,255,255,.08)",
  shadow: "0 30px 80px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.06)", capBg: "rgba(8,9,14,.88)", capText: "#b6bdd3",
  sheen: "255,255,255", fx: true,
};
const light: typeof dark = {
  bg: "#e6dfd2", ink: "#1a1a1a", muted: "#6b6b6b", green: "#2e7d32", red: "#c62828", amber: "#b26a00", brand: "#c0573e",
  line: "rgba(0,0,0,0.10)", glass: "#ffffff", panel: "#ffffff", chip: "#ece7dc",
  shadow: "0 20px 60px rgba(0,0,0,.15)", capBg: "#faf8f4", capText: "#333",
  sheen: "0,0,0", fx: false,
};
export const THEMES = { dark, light };
export type Theme = typeof dark;

const Ctx = createContext<Theme>(dark);
export const ThemeProvider = Ctx.Provider;
export const useTheme = () => useContext(Ctx);
export const useGlass = (): React.CSSProperties => {
  const C = useTheme();
  return { background: C.glass, border: `1px solid ${C.line}`, borderRadius: 20, boxShadow: C.shadow };
};

export const SANS = "-apple-system, 'Helvetica Neue', Helvetica, sans-serif";
export const MONO = "ui-monospace, Menlo, monospace";
export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const BLOBS = [
  { c: "#2b2f9e", x: 0.18, y: 0.2, s: 1000 }, { c: "#6a2c9e", x: 0.82, y: 0.3, s: 900 },
  { c: "#0f6a6a", x: 0.5, y: 0.95, s: 1000 }, { c: "#7a1f2e", x: 0.05, y: 0.9, s: 700 },
];

export const Bg = () => {
  const f = useCurrentFrame();
  const C = useTheme();
  if (!C.fx) return <AbsoluteFill style={{ background: `radial-gradient(ellipse at 30% 30%, #efebe3, ${C.bg})` }} />;
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      {BLOBS.map((b, i) => (
        <div key={i} style={{
          position: "absolute", width: b.s, height: b.s, borderRadius: "50%", background: b.c, opacity: 0.32, filter: "blur(140px)",
          left: b.x * 1920 - b.s / 2 + Math.sin(f / 150 + i * 1.7) * 90, top: b.y * 1080 - b.s / 2 + Math.cos(f / 170 + i) * 70,
        }} />
      ))}
      {Array.from({ length: 70 }).map((_, i) => {
        const x = random(`px${i}`) * 1920, y0 = random(`py${i}`) * 1080, sp = 0.15 + random(`ps${i}`) * 0.35, sz = 1.5 + random(`pz${i}`) * 2;
        const y = (((y0 - f * sp) % 1080) + 1080) % 1080;
        const tw = 0.2 + 0.4 * (0.5 + 0.5 * Math.sin(f / 20 + i));
        return <div key={i} style={{ position: "absolute", left: x, top: y, width: sz, height: sz, borderRadius: "50%", background: "#fff", opacity: tw }} />;
      })}
    </AbsoluteFill>
  );
};

// Fades a scene in and out so cuts do not pop.
export const Fade = ({ children }: { children: React.ReactNode }) => {
  const f = useCurrentFrame();
  const { durationInFrames: d } = useVideoConfig();
  const o = interpolate(f, [0, 8, d - 8, d], [0, 1, 1, 0], clamp);
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

export const Caption = ({ steps }: { steps: { from: number; text: string }[] }) => {
  const f = useCurrentFrame();
  const C = useTheme();
  const cur = [...steps].reverse().find((s) => f >= s.from) ?? steps[0];
  const o = interpolate(f, [cur.from, cur.from + 8], [0, 1], clamp);
  return (
    <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 110, background: C.capBg, borderTop: `1px solid ${C.line}`, display: "flex", alignItems: "center", paddingLeft: 70, fontFamily: SANS }}>
      <span style={{ color: C.ink, fontWeight: 700, fontSize: 32 }}>qa-campaign</span>
      <span style={{ width: 2, height: 40, background: C.brand, margin: "0 28px" }} />
      <span style={{ fontSize: 30, color: C.capText, opacity: o }}>{cur.text}</span>
    </div>
  );
};

export const Chip = ({ text, color, fg, strike = false }: { text: string; color?: string; fg?: string; strike?: boolean }) => {
  const C = useTheme();
  return <span style={{ display: "inline-block", fontFamily: MONO, fontSize: 24, background: color ?? C.chip, color: fg ?? C.ink, border: `1px solid ${C.line}`, borderRadius: 999, padding: "6px 18px", marginRight: 10, textDecoration: strike ? "line-through" : "none" }}>{text}</span>;
};
