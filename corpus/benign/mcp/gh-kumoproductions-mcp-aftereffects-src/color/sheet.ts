// Frame inspection for the render tool: tiling several captures into one
// labelled contact sheet, and measuring a capture (edge bands, content
// bounds, coverage) so a motion check does not need a human — or an image
// model — to spot a black bar or an element that slid off frame.
//
// Pure Node, zero dependencies: pixels come from png16.decodePng, and the
// only text ever drawn is a frame index and a time, which a 5×7 bitmap
// font covers.

import type { DecodedPng } from "./png16.js";

export type Rgb = [number, number, number];

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

export interface EdgeBand {
  /** Rows (top/bottom) or columns (left/right) of one uniform color at that edge. */
  width: number;
  /** transparent = alpha 0 all along the band; color = one opaque color; none = no uniform band. */
  kind: "transparent" | "color" | "none";
  color: Rgb | null;
}

export interface FrameAnalysis {
  width: number;
  height: number;
  /** Mean of the capture's RGB (before any color conversion). */
  meanRgb: Rgb;
  /** True when every pixel is one color (an empty or fully covered frame). */
  uniform: boolean;
  /** What "nothing" looks like in this frame: alpha 0 when there is alpha, else the corner color. */
  background: { kind: "transparent" | "color"; color: Rgb | null };
  /** Bounding box of every pixel that is not background, or null when the frame is all background. */
  contentBounds: { left: number; top: number; width: number; height: number } | null;
  /** Fraction (0..1) of pixels that are not background. */
  coverage: number;
  edges: { top: EdgeBand; bottom: EdgeBand; left: EdgeBand; right: EdgeBand };
}

/** Per-channel tolerance for "same color": two 8-bit steps. */
const TOL = 2 / 255;

function px(img: DecodedPng, x: number, y: number): Rgb {
  const i = (y * img.width + x) * 3;
  return [img.rgb[i], img.rgb[i + 1], img.rgb[i + 2]];
}

function same(a: Rgb, b: Rgb): boolean {
  return (
    Math.abs(a[0] - b[0]) <= TOL && Math.abs(a[1] - b[1]) <= TOL && Math.abs(a[2] - b[2]) <= TOL
  );
}

function isBackground(img: DecodedPng, x: number, y: number, bg: Rgb | null): boolean {
  if (img.alpha) return img.alpha[y * img.width + x] <= TOL;
  return bg !== null && same(px(img, x, y), bg);
}

/** The color most of the four corners share (ties go to the top-left). */
function cornerColor(img: DecodedPng): Rgb {
  const corners: Rgb[] = [
    px(img, 0, 0),
    px(img, img.width - 1, 0),
    px(img, 0, img.height - 1),
    px(img, img.width - 1, img.height - 1),
  ];
  let best = corners[0];
  let bestCount = 0;
  for (const c of corners) {
    const count = corners.filter((o) => same(o, c)).length;
    if (count > bestCount) {
      best = c;
      bestCount = count;
    }
  }
  return best;
}

/** True when every pixel along one row (or column) is background-like or one color. */
function lineUniform(
  img: DecodedPng,
  fixed: number,
  horizontal: boolean,
): { uniform: boolean; transparent: boolean; color: Rgb } {
  const n = horizontal ? img.width : img.height;
  const first = horizontal ? px(img, 0, fixed) : px(img, fixed, 0);
  let transparent = img.alpha !== undefined;
  for (let i = 0; i < n; i++) {
    const x = horizontal ? i : fixed;
    const y = horizontal ? fixed : i;
    if (transparent && (img.alpha as Float64Array)[y * img.width + x] > TOL) transparent = false;
    if (!same(px(img, x, y), first)) return { uniform: false, transparent: false, color: first };
  }
  return { uniform: true, transparent, color: first };
}

function edgeBand(img: DecodedPng, side: "top" | "bottom" | "left" | "right"): EdgeBand {
  const horizontal = side === "top" || side === "bottom";
  const n = horizontal ? img.height : img.width;
  let width = 0;
  let color: Rgb | null = null;
  let transparent = true;
  for (let i = 0; i < n; i++) {
    const fixed = side === "top" || side === "left" ? i : n - 1 - i;
    const line = lineUniform(img, fixed, horizontal);
    if (!line.uniform) break;
    if (color === null) color = line.color;
    else if (!same(color, line.color)) break;
    if (!line.transparent) transparent = false;
    width++;
  }
  if (width === 0) return { width: 0, kind: "none", color: null };
  return { width, kind: transparent && img.alpha ? "transparent" : "color", color };
}

/** Measure a capture. Works on the raw decode so alpha is still there. */
export function analyzeFrame(img: DecodedPng): FrameAnalysis {
  const { width, height } = img;
  const bgColor = img.alpha ? null : cornerColor(img);
  const sum: Rgb = [0, 0, 0];
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  let content = 0;
  const first = px(img, 0, 0);
  let uniform = true;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 3;
      sum[0] += img.rgb[i];
      sum[1] += img.rgb[i + 1];
      sum[2] += img.rgb[i + 2];
      if (uniform && !same(px(img, x, y), first)) uniform = false;
      if (!isBackground(img, x, y, bgColor)) {
        content++;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  const total = width * height;
  return {
    width,
    height,
    meanRgb: [sum[0] / total, sum[1] / total, sum[2] / total],
    uniform,
    background: img.alpha
      ? { kind: "transparent", color: null }
      : { kind: "color", color: bgColor },
    contentBounds:
      content === 0
        ? null
        : { left: minX, top: minY, width: maxX - minX + 1, height: maxY - minY + 1 },
    coverage: content / total,
    edges: {
      top: edgeBand(img, "top"),
      bottom: edgeBand(img, "bottom"),
      left: edgeBand(img, "left"),
      right: edgeBand(img, "right"),
    },
  };
}

// ---------------------------------------------------------------------------
// Contact sheet
// ---------------------------------------------------------------------------

export interface SheetOptions {
  /** Tiles per row (default: ceil(sqrt(n))). */
  columns?: number;
  /** Width of each tile in px; frames are never upscaled (default 480). */
  thumbWidth?: number;
  /** One label per frame, drawn above its tile. */
  labels?: string[];
  gap?: number;
  background?: Rgb;
}

export interface SheetImage {
  width: number;
  height: number;
  rgb: Float64Array;
  columns: number;
  rows: number;
  thumbWidth: number;
  thumbHeight: number;
}

/** Area-averaging downscale to exactly tw×th. */
export function resample(img: DecodedPng, tw: number, th: number): Float64Array {
  const out = new Float64Array(tw * th * 3);
  const counts = new Float64Array(tw * th);
  for (let y = 0; y < img.height; y++) {
    const ty = Math.min(th - 1, Math.floor((y * th) / img.height));
    for (let x = 0; x < img.width; x++) {
      const tx = Math.min(tw - 1, Math.floor((x * tw) / img.width));
      const si = (y * img.width + x) * 3;
      const di = (ty * tw + tx) * 3;
      out[di] += img.rgb[si];
      out[di + 1] += img.rgb[si + 1];
      out[di + 2] += img.rgb[si + 2];
      counts[ty * tw + tx]++;
    }
  }
  for (let i = 0; i < tw * th; i++) {
    const c = counts[i] || 1;
    out[i * 3] /= c;
    out[i * 3 + 1] /= c;
    out[i * 3 + 2] /= c;
  }
  return out;
}

// 5×7 glyphs for the only text the sheet ever carries: "#<index> <time>s".
const GLYPHS: Record<string, string[]> = {
  "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
  "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
  "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
  "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
  "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
  "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
  "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
  "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
  "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
  "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
  ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
  ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
  "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
  "#": [".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."],
  s: [".....", ".....", ".####", "#....", ".###.", "....#", "####."],
  f: ["..##.", ".#...", "###..", ".#...", ".#...", ".#...", ".#..."],
  " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
};
const GLYPH_W = 5;
const GLYPH_H = 7;
const FONT_SCALE = 2;
const LABEL_H = GLYPH_H * FONT_SCALE + 6;

function drawText(
  rgb: Float64Array,
  width: number,
  x0: number,
  y0: number,
  text: string,
  color: Rgb,
): void {
  let cx = x0;
  for (const ch of text) {
    const glyph = GLYPHS[ch] ?? GLYPHS[" "];
    for (let gy = 0; gy < GLYPH_H; gy++) {
      for (let gx = 0; gx < GLYPH_W; gx++) {
        if (glyph[gy][gx] !== "#") continue;
        for (let sy = 0; sy < FONT_SCALE; sy++) {
          for (let sx = 0; sx < FONT_SCALE; sx++) {
            const x = cx + gx * FONT_SCALE + sx;
            const y = y0 + gy * FONT_SCALE + sy;
            const i = (y * width + x) * 3;
            rgb[i] = color[0];
            rgb[i + 1] = color[1];
            rgb[i + 2] = color[2];
          }
        }
      }
    }
    cx += (GLYPH_W + 1) * FONT_SCALE;
  }
}

/** Tile frames into one image with a label strip above each tile. */
export function composeContactSheet(frames: DecodedPng[], opts: SheetOptions = {}): SheetImage {
  if (frames.length === 0) throw new Error("contact sheet needs at least one frame");
  const gap = opts.gap ?? 8;
  const bg = opts.background ?? [0.12, 0.12, 0.12];
  const columns = Math.max(
    1,
    Math.min(frames.length, opts.columns ?? Math.ceil(Math.sqrt(frames.length))),
  );
  const rows = Math.ceil(frames.length / columns);
  const srcW = Math.max(...frames.map((f) => f.width));
  const srcH = Math.max(...frames.map((f) => f.height));
  const thumbWidth = Math.max(16, Math.min(opts.thumbWidth ?? 480, srcW));
  const thumbHeight = Math.max(1, Math.round((srcH * thumbWidth) / srcW));
  const cellW = thumbWidth;
  const cellH = LABEL_H + thumbHeight;
  const width = gap + columns * (cellW + gap);
  const height = gap + rows * (cellH + gap);
  const rgb = new Float64Array(width * height * 3);
  for (let i = 0; i < width * height; i++) {
    rgb[i * 3] = bg[0];
    rgb[i * 3 + 1] = bg[1];
    rgb[i * 3 + 2] = bg[2];
  }
  for (const [n, frame] of frames.entries()) {
    const col = n % columns;
    const row = Math.floor(n / columns);
    const x0 = gap + col * (cellW + gap);
    const y0 = gap + row * (cellH + gap);
    // Keep each frame's own aspect; a smaller frame just leaves background.
    const tw = Math.max(1, Math.min(thumbWidth, Math.round((frame.width * thumbWidth) / srcW)));
    const th = Math.max(1, Math.min(thumbHeight, Math.round((frame.height * tw) / frame.width)));
    const thumb = resample(frame, tw, th);
    for (let y = 0; y < th; y++) {
      for (let x = 0; x < tw; x++) {
        const si = (y * tw + x) * 3;
        const di = ((y0 + LABEL_H + y) * width + (x0 + x)) * 3;
        rgb[di] = thumb[si];
        rgb[di + 1] = thumb[si + 1];
        rgb[di + 2] = thumb[si + 2];
      }
    }
    const label = opts.labels?.[n] ?? `#${n}`;
    drawText(rgb, width, x0 + 2, y0 + 3, label, [0.95, 0.95, 0.95]);
  }
  return { width, height, rgb, columns, rows, thumbWidth, thumbHeight };
}

/** Label text for a frame: "#3 1.500s" — only characters the font has. */
export function frameLabel(index: number, time: number | undefined): string {
  return time === undefined ? `#${index}` : `#${index} ${time.toFixed(3)}s`;
}
