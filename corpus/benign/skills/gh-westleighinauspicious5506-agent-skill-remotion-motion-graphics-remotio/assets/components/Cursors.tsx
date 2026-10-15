import { C } from "../theme";

type Pt = { x: number; y: number };

// macOS-style pointer arrow (used in the light scenes of the reference).
export const ArrowCursor: React.FC<{
  pos: Pt;
  color?: string;
  pressed?: boolean;
  opacity?: number;
  size?: number;
}> = ({ pos, color = C.blue, pressed, opacity = 1, size = 46 }) => (
  <svg
    viewBox="0 0 24 24"
    width={size}
    height={size}
    style={{
      position: "absolute",
      left: pos.x,
      top: pos.y,
      opacity,
      transform: `scale(${pressed ? 0.86 : 1})`,
      transformOrigin: "22% 12%",
      filter: "drop-shadow(0 6px 10px rgba(0,0,0,0.25))",
    }}
  >
    <path
      d="M5.5 3.2 L5.5 20.5 L9.8 16.6 L12.6 22.6 L15.6 21.2 L12.9 15.3 L18.6 15.3 Z"
      fill={color}
      stroke="#FFFFFF"
      strokeWidth={1.6}
      strokeLinejoin="round"
    />
  </svg>
);

// Black dot cursor (used in the UI scene of the reference).
export const DotCursor: React.FC<{
  pos: Pt;
  pressed?: boolean;
  opacity?: number;
}> = ({ pos, pressed, opacity = 1 }) => (
  <div
    style={{
      position: "absolute",
      left: pos.x - 12,
      top: pos.y - 12,
      width: 24,
      height: 24,
      borderRadius: "50%",
      background: C.ink,
      opacity,
      transform: `scale(${pressed ? 0.75 : 1})`,
      boxShadow: "0 6px 16px rgba(0,0,0,0.35)",
    }}
  />
);
