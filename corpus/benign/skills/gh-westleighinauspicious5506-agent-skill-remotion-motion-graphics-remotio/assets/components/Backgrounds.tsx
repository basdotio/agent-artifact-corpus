import { AbsoluteFill } from "remotion";
import { C, hexToRgba } from "../theme";

// Light backdrop: white top fading into a soft brand glow at the bottom
// (the reference used lavender; hundredable's brand yellow takes its place).
export const LightBg: React.FC<{
  glow?: number; // 0..1.2
  color?: string;
  y?: number; // glow center y in %
}> = ({ glow = 1, color = C.yellow, y = 100 }) => (
  <AbsoluteFill style={{ backgroundColor: C.lightBase }}>
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse 85% 55% at 50% ${y}%, ${hexToRgba(
          color,
          0.5 * glow,
        )} 0%, ${hexToRgba(color, 0)} 72%)`,
      }}
    />
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, #FFFFFF 0%, rgba(255,255,255,0) 40%)",
      }}
    />
  </AbsoluteFill>
);

export const DarkBg: React.FC<{
  glow?: number; // 0..0.5
  color?: string;
  x?: number;
  y?: number;
  size?: number;
}> = ({ glow = 0, color = C.yellow, x = 50, y = 60, size = 60 }) => (
  <AbsoluteFill style={{ backgroundColor: C.dark }}>
    {glow > 0 && (
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at ${x}% ${y}%, ${hexToRgba(
            color,
            glow,
          )} 0%, rgba(0,0,0,0) ${size}%)`,
        }}
      />
    )}
  </AbsoluteFill>
);
