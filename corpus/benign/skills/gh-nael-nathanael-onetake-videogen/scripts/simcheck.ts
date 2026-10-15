// Headless check of the Cell sim: runtime, NaNs, pinch-off frame, membrane jiggle and settling.
//   bun scripts/simcheck.ts        (needs remotion/node_modules: npm install in remotion/)
import { FPS, getFrames, T } from "../remotion/src/illustrated/cell/sim";

const t0 = performance.now();
const frames = getFrames();
console.log(`simulated ${frames.length} frames in ${(performance.now() - t0).toFixed(0)} ms`);

const bad = frames.findIndex((f) => f.rings.some((r) => r.pts.some((v) => !Number.isFinite(v))) || f.bodies.some((b) => !Number.isFinite(b.x) || !Number.isFinite(b.y)));
const pinch = frames.findIndex((f) => f.rings.length === 2);
console.log("first NaN frame:", bad);
console.log(`pinch-off at frame ${pinch} (${(pinch / FPS).toFixed(2)} s), designed ${Math.round(T.pinch * FPS)}`);

// Radius spread of each ring (min..max distance from its centroid): jiggle amplitude over time.
for (let s = 0; s < frames.length / FPS; s += 0.5) {
  const f = frames[Math.round(s * FPS)];
  const out = f.rings.map((r) => {
    const n = r.pts.length / 2;
    let cx = 0, cy = 0;
    for (let i = 0; i < n; i++) { cx += r.pts[2 * i]; cy += r.pts[2 * i + 1]; }
    cx /= n; cy /= n;
    const d = Array.from({ length: n }, (_, i) => Math.hypot(r.pts[2 * i] - cx, r.pts[2 * i + 1] - cy));
    return `c=${cx.toFixed(0)} r=${Math.min(...d).toFixed(0)}..${Math.max(...d).toFixed(0)}`;
  });
  console.log(s.toFixed(1).padStart(4), out.join(" | "));
}

if (bad !== -1 || pinch !== Math.round(T.pinch * FPS)) {
  console.error("FAIL");
  process.exit(1);
}
console.log("OK");
