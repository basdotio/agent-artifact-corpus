import { useVideoConfig } from "remotion";

// Everything positional derives from the composition size, so the same scenes
// render the 9:16 (1080x1920) and 16:9 (1920x1080) versions.
// The wide version is designed at 1600x900 and scaled up 1.2x in <Main> so
// type and UI read at a comfortable size on a landscape frame.
export const designScale = (width: number, height: number) => (width > height ? 1.2 : 1);

export const useLayout = () => {
  const { width, height } = useVideoConfig();
  const s = designScale(width, height);
  const W = width / s;
  const H = height / s;
  return { W, H, cx: W / 2, cy: H / 2, wide: W > H, diag: Math.hypot(W, H), scale: s };
};

export const PILL = { w: 92, h: 60 } as const;
// vertical centre of the "Want ⚡ ..." row (≈42-44% down the frame)
export const hookRowY = (cy: number, H: number) => cy - H * 0.083;
// the map marker the blue pill shrinks into
export const markerPos = (cx: number, H: number) => ({ x: cx, y: H * 0.615, size: 46 });
