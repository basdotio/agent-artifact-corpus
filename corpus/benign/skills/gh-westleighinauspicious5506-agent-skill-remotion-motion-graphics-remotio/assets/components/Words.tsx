import { useCurrentFrame } from "remotion";
import { EASE_IN, EASE_OUT, prog } from "../anim";

// Word-by-word reveal (rise + fade), optional exit. Mirrors the kinetic type
// in the reference video where each word lands a few frames after the last.
export const Words: React.FC<{
  text: string;
  start: number;
  stagger?: number;
  dur?: number;
  out?: { start: number; dur?: number };
  style?: React.CSSProperties;
  wordStyle?: (word: string, i: number) => React.CSSProperties;
  dy?: number;
}> = ({ text, start, stagger = 5, dur = 14, out, style, wordStyle, dy = 22 }) => {
  const frame = useCurrentFrame();
  const words = text.split(" ");
  return (
    <span style={{ display: "inline", ...style }}>
      {words.map((w, i) => {
        const p = prog(frame, start + i * stagger, dur, EASE_OUT);
        const q = out ? prog(frame, out.start + i * 2, out.dur ?? 10, EASE_IN) : 0;
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              whiteSpace: "pre",
              opacity: p * (1 - q),
              transform: `translateY(${(1 - p) * dy - q * 36}px)`,
              filter: p < 1 ? `blur(${(1 - p) * 3}px)` : undefined,
              ...(wordStyle ? wordStyle(w, i) : {}),
            }}
          >
            {w}
            {i < words.length - 1 ? " " : ""}
          </span>
        );
      })}
    </span>
  );
};
