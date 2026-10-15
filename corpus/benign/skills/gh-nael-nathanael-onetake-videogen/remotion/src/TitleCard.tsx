import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { exit, POP, rig, squash } from "./motion";
import { fontFamily, Format, INK, PAPER } from "./theme";

export type TitleCardProps = {
  title: string;
  subtitle?: string;
  accent?: string;
  seconds: number;
  position?: "lower-third" | "center";
  /** Sets the frame size (Root.tsx); the layout follows the frame. */
  format?: Format;
};

/** Transparent overlay (lower third or centered title) composited onto footage with ffmpeg. */
export const TitleCard: React.FC<TitleCardProps> = ({ title, subtitle, accent = "#FF5A5F", position = "lower-third" }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  // On a vertical frame the lower third sits above the captions and the app's own controls.
  const vertical = height > width;
  const side = vertical ? 56 : 70;
  const card = rig(frame, fps, POP);
  const [cx, cy] = squash(card.vel);
  // The shadow lands after the card: follow-through instead of a welded-on drop shadow.
  const shadow = rig(frame - 4, fps, POP).v;
  const sub = rig(frame - 8, fps, POP);
  const [sy, sx] = squash(sub.vel);
  const out = exit(durationInFrames - frame, 18);
  const center = position === "center";

  return (
    <AbsoluteFill
      style={{
        justifyContent: center ? "center" : "flex-end",
        alignItems: center ? "center" : "flex-start",
        padding: center ? `0 ${side}px` : `0 ${side}px ${vertical ? Math.round(height * 0.34) : 150}px`,
        fontFamily,
        opacity: out,
        transform: `translateY(${(1 - out) * -14}px)`,
      }}
    >
      <div style={{ transform: `translateX(${(1 - card.v) * -60}px) scale(${(0.9 + 0.1 * card.v) * cx}, ${(0.9 + 0.1 * card.v) * cy})` }}>
        <div
          style={{
            display: "inline-block",
            background: accent,
            color: PAPER,
            fontWeight: 800,
            fontSize: (center ? 88 : 54) * (vertical && center ? 0.8 : 1),
            padding: "10px 26px",
            borderRadius: 16,
            boxShadow: `${8 * shadow}px ${8 * shadow}px 0 ${INK}`,
          }}
        >
          {title}
        </div>
        {subtitle && (
          <div
            style={{
              marginTop: 14,
              display: "block",
              width: "fit-content",
              background: PAPER,
              color: INK,
              fontWeight: 700,
              fontSize: center ? 40 : 30,
              padding: "8px 20px",
              borderRadius: 12,
              opacity: Math.min(1, sub.v * 1.5),
              transform: `translateY(${(1 - sub.v) * 20}px) scale(${sx}, ${sy})`,
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
