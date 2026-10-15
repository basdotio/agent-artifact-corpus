import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { captionLayout, Captions } from "./Captions";
import { breathe, exit, POP, rig, SOFT, squash, stagger } from "./motion";
import { beatPhase, DEFAULT_PALETTE, fontFamily, Format, INK, PAPER, Scene, Word } from "./theme";

export type ExplainerProps = {
  duration: number;
  scenes: Scene[];
  words: Word[];
  bpm?: number;
  beatOffset?: number;
  palette?: string[];
  /** Brand theme. `paper` is the text on a scene and the point cards; `ink` is the frame, kicker
   *  and card text. For a light theme (dark text on pale scenes), pass the dark tone as `paper`. */
  ink?: string;
  paper?: string;
  /** Caption highlight; defaults to a palette colour. */
  accent?: string;
  captions?: boolean;
  /** Sets the frame size (Root.tsx); the layout follows the frame. */
  format?: Format;
};

type Tones = { ink: string; paper: string };

const SceneView: React.FC<{ scene: Scene; color: string; t: number; pulse: number } & Tones> = ({
  scene,
  color,
  t,
  pulse,
  ink: INK,
  paper: PAPER,
}) => {
  const { fps, width, height } = useVideoConfig();
  // A vertical frame is narrower: smaller type, tighter sides, and room at the top for the app's own bar.
  const vertical = height > width;
  const side = vertical ? 56 : 90;
  const local = Math.round((t - scene.start) * fps);
  // The panel settles without a bounce; the parts on it arrive one after another.
  const panel = rig(local, fps, SOFT).v;
  const kicker = rig(local - stagger(1), fps, POP);
  const title = rig(local - stagger(scene.kicker ? 2 : 1), fps, POP);
  const emoji = rig(local - stagger(scene.kicker ? 4 : 3), fps, POP);
  const [ty, tx] = squash(title.vel);
  const out = exit(Math.round((scene.end - t) * fps));
  const layout = scene.layout ?? (scene.points?.length ? "points" : "title");
  const titleSize = (layout === "big" ? 120 : layout === "title" ? 84 : 60) * (vertical ? 0.8 : 1);

  return (
    <AbsoluteFill
      style={{
        background: color,
        opacity: out,
        transform: `scale(${(0.94 + 0.06 * panel) * (0.98 + 0.02 * out)})`,
        padding: `${vertical ? 150 : 70}px ${side}px ${captionLayout(width, height).reserve}px`,
        justifyContent: layout === "points" ? "flex-start" : "center",
        alignItems: layout === "points" ? "flex-start" : "center",
        fontFamily,
        color: PAPER,
      }}
    >
      {/* Accent blob breathes slowly with a faint beat accent: alive, never busy. */}
      <div
        style={{
          position: "absolute",
          right: -120,
          top: -120,
          width: 420,
          height: 420,
          borderRadius: "50%",
          background: PAPER,
          opacity: 0.12,
          transform: `scale(${breathe(t, 7, 0.03) * (1 + 0.015 * pulse)})`,
        }}
      />
      {scene.kicker && (
        <div
          style={{
            fontWeight: 700,
            fontSize: 28,
            letterSpacing: 3,
            textTransform: "uppercase",
            background: INK,
            padding: "6px 16px",
            borderRadius: 10,
            marginBottom: 18,
            opacity: Math.min(1, kicker.v * 1.5),
            transform: `translateY(${(1 - kicker.v) * -30}px)`,
          }}
        >
          {scene.kicker}
        </div>
      )}
      <div
        style={{
          fontWeight: 800,
          fontSize: titleSize,
          lineHeight: 1.08,
          textAlign: layout === "points" ? "left" : "center",
          maxWidth: width - 2 * side,
          opacity: Math.min(1, title.v * 1.5),
          transform: `translateY(${(1 - title.v) * 50}px) scale(${tx}, ${ty})`,
          textShadow: `0 6px 0 ${INK}33`,
        }}
      >
        {scene.emoji && (
          <span
            style={{
              display: "inline-block",
              marginRight: 20,
              transform: `scale(${emoji.v}) rotate(${(1 - emoji.v) * -20}deg)`,
            }}
          >
            {scene.emoji}
          </span>
        )}
        {scene.title}
      </div>
      {layout === "points" && (
        <div style={{ marginTop: 36, display: "flex", flexDirection: "column", gap: 20 }}>
          {(scene.points ?? []).map((p, i) => {
            if (t < p.at) return null;
            const f = Math.round((t - p.at) * fps);
            const row = rig(f, fps, POP);
            const [rx, ry] = squash(row.vel);
            // The number badge trails its row and pops in after it lands.
            const badge = rig(f - 4, fps, POP).v;
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 18,
                  fontWeight: 700,
                  fontSize: vertical ? 36 : 40,
                  background: PAPER,
                  color: INK,
                  padding: "12px 24px",
                  borderRadius: 16,
                  transform: `translateX(${(1 - row.v) * -80}px) scale(${(0.92 + 0.08 * row.v) * rx}, ${(0.92 + 0.08 * row.v) * ry})`,
                  opacity: Math.min(1, row.v * 1.5),
                }}
              >
                <span
                  style={{
                    background: color,
                    color: PAPER,
                    borderRadius: 10,
                    width: 46,
                    height: 46,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 800,
                    transform: `scale(${badge})`,
                  }}
                >
                  {i + 1}
                </span>
                {p.text}
              </div>
            );
          })}
        </div>
      )}
    </AbsoluteFill>
  );
};

export const Explainer: React.FC<ExplainerProps> = ({
  scenes,
  words,
  bpm = 0,
  beatOffset = 0,
  palette = DEFAULT_PALETTE,
  ink = INK,
  paper = PAPER,
  accent,
  captions = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const since = beatPhase(t, bpm, beatOffset);
  const pulse = Math.exp(-since * 9);
  const idx = scenes.findIndex((s) => t >= s.start && t < s.end);
  const scene = idx >= 0 ? scenes[idx] : undefined;
  const color = palette[Math.max(idx, 0) % palette.length];

  return (
    <AbsoluteFill style={{ background: ink }}>
      {scene && <SceneView scene={scene} color={color} t={t} pulse={pulse} ink={ink} paper={paper} />}
      {captions && (
        <Captions
          words={words}
          accent={accent ?? palette[(Math.max(idx, 0) + 3) % palette.length]}
          ink={ink}
          paper={paper}
        />
      )}
    </AbsoluteFill>
  );
};
