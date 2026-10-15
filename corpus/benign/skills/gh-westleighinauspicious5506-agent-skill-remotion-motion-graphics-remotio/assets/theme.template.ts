// Brand + timing system. Copy to src/theme.ts and fill the colours from the
// brand (logo SVG fills, site CSS variables). Keep ONE accent + ink + a light
// base; motion pieces read best with few colours used consistently.
export const PORTRAIT = { width: 1080, height: 1920, fps: 30 } as const;
export const LANDSCAPE = { width: 1920, height: 1080, fps: 30 } as const;

export const C = {
  ink: "#0A0A0A",
  white: "#FFFFFF",
  accent: "#FBF713", // >>> primary brand colour (glows, pills, highlight word)
  accent2: "#0A8CF0", // >>> secondary brand colour (blue text, buttons)
  accentText: "#1C7DE8", // slightly darker accent2 for text on light
  lightBase: "#FCFBF6", // near-white light background
  gray: "#B8B8B8",
  dark: "#070707",
  surface: "#141414",
  surface2: "#1E1E1E",
  border: "rgba(255,255,255,0.10)",
  textDim: "rgba(255,255,255,0.62)",
  inkDim: "rgba(10,10,10,0.5)",
} as const;

// Scene durations in frames, in playback order. Name every beat; the sum is
// the composition length, so re-timing one scene never breaks the others.
export const SCENES = {
  hook: 135,
  reveal: 75,
  statement: 45,
  final: 84,
} as const;

export const TOTAL = Object.values(SCENES).reduce((a, b) => a + b, 0);

export const hexToRgba = (hex: string, alpha: number) => {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
