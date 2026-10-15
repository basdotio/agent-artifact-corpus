import React, { useMemo } from "react";
import { interpolateColors, useCurrentFrame, useVideoConfig } from "remotion";
import { POP, rig, SOFT } from "./motion";
import { fontFamily, INK, PAPER, Word } from "./theme";

const FONT_SIZE = 44;
const PAD_Y = 10;

/**
 * Where captions sit in a frame. Landscape: one line near the bottom edge. Vertical: shorter lines
 * that may wrap to two, raised clear of the controls a phone app draws over the bottom of the video.
 * `reserve` is the height from the bottom edge that scene content keeps free.
 */
export const captionLayout = (width: number, height: number) => {
  const vertical = height > width;
  const bottom = vertical ? Math.round(height * 0.19) : 56;
  const bandHeight = (vertical ? 2 : 1) * FONT_SIZE * 1.25 + 2 * PAD_Y;
  return { maxWords: vertical ? 4 : 6, maxWidth: Math.min(1100, width - 112), bottom, bandHeight, reserve: bottom + bandHeight + 19 };
};

/** Group words into short caption lines, breaking on punctuation, pauses and length. */
export const toLines = (words: Word[], maxWords = 6) => {
  const lines: Word[][] = [];
  let cur: Word[] = [];
  words.forEach((w, i) => {
    cur.push(w);
    const next = words[i + 1];
    const punct = /[.,!?;:]$/.test(w.text);
    const pause = next ? next.start - w.end > 0.35 : true;
    if (cur.length >= maxWords || punct || pause) {
      lines.push(cur);
      cur = [];
    }
  });
  if (cur.length) lines.push(cur);
  return lines;
};

export const Captions: React.FC<{ words: Word[]; accent: string; ink?: string; paper?: string }> = ({
  words,
  accent,
  ink = INK,
  paper = PAPER,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  const { maxWords, maxWidth, bottom, bandHeight } = captionLayout(width, height);
  const lines = useMemo(() => toLines(words, maxWords), [words, maxWords]);
  const line = lines.find((l) => t >= l[0].start - 0.05 && t <= l[l.length - 1].end + 0.25);
  // The band captions fill, marked even between lines so the check gate can tell what runs into it.
  const band = <div data-caption-band style={{ position: "absolute", bottom, width: "100%", height: bandHeight }} />;
  if (!line) return band;

  const lineIn = rig(frame - Math.round(line[0].start * fps), fps, SOFT).v;

  return (
    <>
    {band}
    <div
      data-captions
      style={{
        position: "absolute",
        bottom,
        width: "100%",
        display: "flex",
        justifyContent: "center",
        transform: `translateY(${(1 - lineIn) * 30}px)`,
        opacity: lineIn,
      }}
    >
      <div
        style={{
          fontFamily,
          fontWeight: 800,
          fontSize: FONT_SIZE,
          background: ink,
          color: paper,
          padding: `${PAD_Y}px 22px`,
          borderRadius: 18,
          maxWidth,
          textAlign: "center",
          lineHeight: 1.25,
        }}
      >
        {line.map((w, i) => {
          // Highlight eases in on the word's start and back out after it, instead of snapping.
          const on = rig(frame - Math.round(w.start * fps), fps, POP).v;
          const off = rig(frame - Math.round((w.end + 0.05) * fps), fps, SOFT).v;
          const lit = Math.max(0, Math.min(1, on - off));
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                // The gap must outlast the pop: a 300 px word at 1.04 grows 6 px a side.
                marginRight: 16,
                color: interpolateColors(Math.min(1, lit), [0, 1], [paper, accent]),
                transform: `scale(${1 + 0.04 * (on - off)})`,
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </div>
    </>
  );
};
