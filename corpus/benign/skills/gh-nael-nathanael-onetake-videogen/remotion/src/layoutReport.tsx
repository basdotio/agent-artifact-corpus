// Reports what text is on screen and where, for the check gate (scripts/check.py).
// With the input prop `layoutReport` set, every frame logs one "[layout] {json}" line once fonts are in.
// The text walk is ported from vincentfranstyo/video-gen-skill (kit/lib/layout-check.ts, MIT;
// see LICENSES/video-gen-skill-MIT.txt).
import React, { useLayoutEffect, useRef } from "react";
import { continueRender, delayRender, getInputProps, useCurrentFrame } from "remotion";

// Platforms crop and overlay the edges; readable text keeps this share of the width clear on each side.
const SAFE_MARGIN = 0.04;
const MIN_VISIBLE_OPACITY = 0.5;
const SNIPPET = 60;

export type LayoutReport = {
  frame: number;
  /** Every distinct visible string outside the captions. */
  texts: string[];
  /** Text that leaves the frame or its side margins. */
  cropped: string[];
  /** Text outside the captions that sits in the band kept free for them. */
  overCaptions: string[];
  /** [family, sample]: text whose font did not load, so a fallback is drawn. */
  fallbackFonts: [string, string][];
};

type Box = { left: number; right: number; top: number; bottom: number };

const measure = (root: HTMLElement, frame: number): LayoutReport => {
  const frameBox = root.getBoundingClientRect();
  const margin = frameBox.width * SAFE_MARGIN;
  const band = root.querySelector("[data-caption-band]")?.getBoundingClientRect();
  const loaded = new Set([...document.fonts].filter((f) => f.status === "loaded").map((f) => f.family.replace(/["']/g, "")));

  // Opacity multiplies down the ancestor chain, so a faded-out scene counts as hidden.
  const shown = (el: Element) => {
    let opacity = 1;
    for (let n: Element | null = el; n && n !== root.parentElement; n = n.parentElement) {
      const style = getComputedStyle(n);
      if (style.visibility !== "visible") return false;
      opacity *= Number(style.opacity);
    }
    return opacity >= MIN_VISIBLE_OPACITY;
  };
  // Text scrolled out of a box with hidden overflow is not on screen; only the part the box shows counts.
  const visiblePart = (rect: DOMRect, el: Element): Box | null => {
    let { left, right, top, bottom } = rect;
    for (let n = el.parentElement; n && n !== root; n = n.parentElement) {
      if (getComputedStyle(n).overflow === "visible") continue;
      const box = n.getBoundingClientRect();
      left = Math.max(left, box.left);
      right = Math.min(right, box.right);
      top = Math.max(top, box.top);
      bottom = Math.min(bottom, box.bottom);
    }
    return right - left > 1 && bottom - top > 1 ? { left, right, top, bottom } : null;
  };

  const texts = new Set<string>();
  const cropped = new Set<string>();
  const overCaptions = new Set<string>();
  const fallbackFonts = new Map<string, string>();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.textContent?.replace(/\s+/g, " ").trim();
    const el = node.parentElement;
    if (!text || !el || el.closest("script, style") || !shown(el)) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    const parts = [...range.getClientRects()].map((rect) => visiblePart(rect, el)).filter((p): p is Box => p !== null);
    if (parts.length === 0) continue;
    const caption = el.closest("[data-captions]") !== null;
    // Captions repeat the narration, which is proofread as text; the list is what else is on screen.
    if (!caption) texts.add(text);
    const sample = text.slice(0, SNIPPET);

    if (/[\p{L}\p{N}]/u.test(text)) {
      const family = getComputedStyle(el).fontFamily.split(",")[0].trim().replace(/^["']|["']$/g, "");
      if (!loaded.has(family) && !fallbackFonts.has(family)) fallbackFonts.set(family, sample);
    }
    // Decoration that is meant to run off the frame carries data-bleed.
    if (el.closest("[data-bleed]")) continue;
    const outside = parts.some(
      (p) => p.left < frameBox.left + margin - 1 || p.right > frameBox.right - margin + 1 || p.top < frameBox.top - 1 || p.bottom > frameBox.bottom + 1,
    );
    if (outside) cropped.add(sample);
    if (band && !caption && parts.some((p) => p.bottom > band.top + 1 && p.top < band.bottom - 1 && p.right > band.left && p.left < band.right)) {
      overCaptions.add(sample);
    }
  }
  return { frame, texts: [...texts], cropped: [...cropped], overCaptions: [...overCaptions], fallbackFonts: [...fallbackFonts] };
};

const Reporter: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    // The frame is held until fonts are in (measured earlier, every box has the fallback font's size)
    // and until Remotion has moved the composition from its off-screen parking node into the canvas.
    const handle = delayRender("layout report");
    const report = () => {
      const root = ref.current;
      if (!root) return continueRender(handle);
      if (root.getBoundingClientRect().width === 0) return void setTimeout(report, 10);
      console.log(`[layout] ${JSON.stringify(measure(root, frame))}`);
      continueRender(handle);
    };
    document.fonts.ready.then(report);
  }, [frame]);
  return (
    <div ref={ref} style={{ position: "absolute", inset: 0 }}>
      {children}
    </div>
  );
};

/** Wraps a composition's component; it only reports when rendered with the input prop `layoutReport`. */
export const withLayoutReport = <P extends object>(Component: React.ComponentType<P>): React.FC<P> => {
  const Reported: React.FC<P> = (props) =>
    getInputProps().layoutReport ? (
      <Reporter>
        <Component {...props} />
      </Reporter>
    ) : (
      <Component {...props} />
    );
  return Reported;
};
