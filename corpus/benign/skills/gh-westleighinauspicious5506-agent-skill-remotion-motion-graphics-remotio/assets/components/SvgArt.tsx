// Renders SVG artwork (a logo, mascot, icon) straight from path data produced
// by scripts/svg_to_paths.mjs, so any subset of paths can be animated on its
// own: letters popping in one by one, a character bobbing, a part rotating.
// Copy to src/components/SvgArt.tsx.
import { useCurrentFrame, useVideoConfig } from "remotion";
import { springAt } from "../anim";

export type SvgPath = { d: string; fill: string; box: [number, number, number, number] };
export type SvgData = { box: [number, number, number, number]; paths: SvgPath[] };

export const unionBox = (paths: SvgPath[]): [number, number, number, number] => [
  Math.min(...paths.map((p) => p.box[0])),
  Math.min(...paths.map((p) => p.box[1])),
  Math.max(...paths.map((p) => p.box[2])),
  Math.max(...paths.map((p) => p.box[3])),
];

// A part = a named group of path indices with its own animation.
export type Part = {
  indices: number[];
  // Return CSS for the group at this frame. transform-box is fill-box, so
  // scale()/rotate() pivot on the group's own centre (or `origin`).
  style?: (frame: number, fps: number) => React.CSSProperties;
  origin?: string; // e.g. "50% 100%" to pivot on the feet
  // Stagger helper: pop each path in the part individually.
  popEach?: { start: number; stagger: number; damping?: number; stiffness?: number };
};

export const SvgArt: React.FC<{
  data: SvgData;
  width: number;
  parts?: Record<string, Part>;
  crop?: number[]; // path indices to fit the viewBox to (default: all)
  pad?: number;
  fadeLeft?: boolean; // soften artwork cropped at the canvas edge
  style?: React.CSSProperties;
}> = ({ data, width, parts = {}, crop, pad = 80, fadeLeft, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const box = crop ? unionBox(crop.map((i) => data.paths[i])) : data.box;
  const vb = [box[0] - pad, box[1] - pad, box[2] - box[0] + pad * 2, box[3] - box[1] + pad * 2];
  const height = (width * vb[3]) / vb[2];
  const assigned = new Set(Object.values(parts).flatMap((p) => p.indices));
  const mask = fadeLeft
    ? "linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0) 4.5%, rgba(0,0,0,1) 17%, rgba(0,0,0,1) 100%)"
    : undefined;

  return (
    <svg
      viewBox={vb.join(" ")}
      width={width}
      height={height}
      style={{ overflow: "visible", WebkitMaskImage: mask, maskImage: mask, WebkitMaskSize: "100% 100%", maskSize: "100% 100%", ...style }}
    >
      {/* static paths */}
      {data.paths.map((p, i) => (assigned.has(i) ? null : <path key={i} d={p.d} fill={p.fill} />))}
      {/* animated parts */}
      {Object.entries(parts).map(([name, part]) => {
        if (part.popEach) {
          const { start, stagger, damping = 10, stiffness = 170 } = part.popEach;
          return part.indices.map((i, k) => {
            const p = springAt(frame, fps, start + k * stagger, { damping, stiffness });
            return (
              <g key={`${name}-${i}`} style={{ transformBox: "fill-box", transformOrigin: "center", transform: `scale(${p})`, opacity: Math.max(0, Math.min(1, p * 1.5)) }}>
                <path d={data.paths[i].d} fill={data.paths[i].fill} />
              </g>
            );
          });
        }
        return (
          <g key={name} style={{ transformBox: "fill-box", transformOrigin: part.origin ?? "center", ...(part.style ? part.style(frame, fps) : {}) }}>
            {part.indices.map((i) => (
              <path key={i} d={data.paths[i].d} fill={data.paths[i].fill} />
            ))}
          </g>
        );
      })}
    </svg>
  );
};

// Ready-made character motion: spring in from below, then bob + sway.
export const characterStyle =
  (opts: { entrance?: number | null; bobAmp?: number; period?: number; tilt?: number }) =>
  (frame: number, fps: number): React.CSSProperties => {
    const { entrance = 0, bobAmp = 50, period = 40, tilt = 2.5 } = opts;
    const ent = entrance === null ? 1 : springAt(frame, fps, entrance, { damping: 12, stiffness: 110, mass: 0.9 });
    const bob = Math.sin((frame / period) * Math.PI * 2) * bobAmp;
    const rot = Math.sin((frame / period) * Math.PI * 2 + 1.2) * tilt;
    return {
      transform: `translateY(${bob}px) rotate(${rot}deg) translateY(${(1 - ent) * 60}%) scale(${0.7 + 0.3 * ent})`,
      opacity: Math.max(0, Math.min(1, ent * 2)),
    };
  };
