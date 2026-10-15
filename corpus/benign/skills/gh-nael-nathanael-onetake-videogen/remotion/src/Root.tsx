import React from "react";
import { Composition } from "remotion";
import { Explainer, ExplainerProps } from "./Explainer";
import { TitleCard, TitleCardProps } from "./TitleCard";
import { Cell, cellDuration, cellFps } from "./illustrated/cell/Cell";
import { AiFlat, aiFlatDuration, aiFlatFps } from "./illustrated/aiflat/AiFlat";
import { AiPas, aiPasDuration, aiPasFps } from "./illustrated/aipas/AiPas";
import { withLayoutReport } from "./layoutReport";
import { Format } from "./theme";

// Register a composition's component through this, so scripts/check.py can read its on-screen text.
const checked = {
  Explainer: withLayoutReport(Explainer),
  TitleCard: withLayoutReport(TitleCard),
  Cell: withLayoutReport(Cell),
  AiFlat: withLayoutReport(AiFlat),
  AiPas: withLayoutReport(AiPas),
};

// Production format: 720p60, landscape unless the props ask for vertical.
const W = 1280;
const H = 720;
const FPS = 60;
const size = (format?: Format) => (format === "vertical" ? { width: H, height: W } : { width: W, height: H });

const explainerDefaults: ExplainerProps = {
  duration: 6,
  bpm: 110,
  beatOffset: 0,
  words: [
    { text: "Halo,", start: 0.3, end: 0.7 },
    { text: "ini", start: 0.8, end: 1.0 },
    { text: "contoh", start: 1.0, end: 1.4 },
    { text: "video.", start: 1.4, end: 1.9 },
  ],
  scenes: [
    { start: 0, end: 2.5, layout: "title", kicker: "Demo", title: "Edit Video Lebih Cepat", emoji: "⚡" },
    {
      start: 2.5,
      end: 6,
      layout: "points",
      title: "Tiga langkah",
      points: [
        { text: "Unggah video", at: 3.0 },
        { text: "Hapus teks", at: 3.8 },
        { text: "Ekspor", at: 4.6 },
      ],
    },
  ],
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="Explainer"
      component={checked.Explainer}
      width={W}
      height={H}
      fps={FPS}
      durationInFrames={FPS * explainerDefaults.duration}
      defaultProps={explainerDefaults}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.ceil(props.duration * FPS)), ...size(props.format) })}
    />
    <Composition
      id="TitleCard"
      component={checked.TitleCard}
      width={W}
      height={H}
      fps={FPS}
      durationInFrames={FPS * 4}
      defaultProps={{ title: "Judul Video", subtitle: "Subjudul singkat", seconds: 4 } satisfies TitleCardProps}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.ceil(props.seconds * FPS)), ...size(props.format) })}
    />
    {/* Illustrated compositions are authored in 1920×1080 coordinates; remotion.py renders them with --scale to 720p. */}
    <Composition id="Cell" component={checked.Cell}width={1920} height={1080} fps={cellFps} durationInFrames={cellDuration} />
    <Composition id="AiFlat" component={checked.AiFlat}width={1920} height={1080} fps={aiFlatFps} durationInFrames={aiFlatDuration} />
    <Composition id="AiPas" component={checked.AiPas}width={1920} height={1080} fps={aiPasFps} durationInFrames={aiPasDuration} />
  </>
);
