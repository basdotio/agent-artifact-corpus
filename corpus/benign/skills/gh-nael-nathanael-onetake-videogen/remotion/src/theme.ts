import { loadFont } from "@remotion/google-fonts/PlusJakartaSans";

export const { fontFamily } = loadFont("normal", {
  weights: ["500", "700", "800"],
  subsets: ["latin"],
});

// Default "pop" palette: one background tone per scene, cycled.
export const DEFAULT_PALETTE = ["#FF5A5F", "#3D5AFE", "#00B894", "#FFB300", "#8E44AD"];

export const INK = "#14141F";
export const PAPER = "#FFFDF7";

export type Word = { text: string; start: number; end: number };

/** Landscape is 1280×720; vertical is 720×1280, for TikTok, Reels and Shorts. */
export type Format = "landscape" | "vertical";

export type Point = { text: string; at: number };

export type Scene = {
  start: number;
  end: number;
  layout?: "title" | "points" | "big" | "quote";
  kicker?: string;
  title: string;
  points?: Point[];
  emoji?: string;
};

/** Seconds since the most recent beat, given a tempo and the time of the first beat. */
export const beatPhase = (t: number, bpm: number, offset: number) => {
  if (!bpm) return 1;
  const period = 60 / bpm;
  const x = (t - offset) / period;
  if (x < 0) return 1;
  return (x - Math.floor(x)) * period;
};
