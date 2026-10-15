// The finish: a fine monochrome grain (it breaks banding in soft gradients before the encoder) and a barely-
// there falloff toward the frame edges. Deterministic per frame. Tune with config.finish {grain, vignette}.
import { h, css } from "./anim.js";
import { mulberry32 } from "./rand.js";

export function createFinish(stage, { grain = 0.032, vignette = 0.07, tint = "28,28,36" } = {}) {
  const TILE = 384;
  const tiles = [];
  const rnd = mulberry32(4242);
  for (let k = 0; k < 12; k++) {
    const c = document.createElement("canvas");
    c.width = c.height = TILE;
    const g = c.getContext("2d");
    const img = g.createImageData(TILE, TILE);
    for (let i = 0; i < TILE * TILE; i++) {
      const n = (rnd() + rnd() + rnd() - 1.5) * 0.9;
      const v = Math.max(0, Math.min(255, 128 + n * 128));
      img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v;
      img.data[i * 4 + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    tiles.push(c.toDataURL());
  }
  const vig = h("div", { class: "fx-top", style: { background: `radial-gradient(118% 100% at 50% 44%, rgba(${tint},0) 58%, rgba(${tint},${vignette}) 100%)` } });
  const grainEl = h("div", { class: "fx-top", style: { mixBlendMode: "overlay", opacity: String(grain), backgroundRepeat: "repeat", backgroundSize: `${TILE}px ${TILE}px`, imageRendering: "pixelated" } });
  stage.append(vig, grainEl);
  const pre = tiles.map((src) => {
    const i = new Image();
    i.src = src;
    return i;
  });
  return {
    ready: Promise.all(pre.map((i) => i.decode())),
    update(t, fps = 60) {
      const f = Math.round(t * fps);
      const r = mulberry32(f * 7 + 3);
      css(grainEl, { backgroundImage: `url(${tiles[f % tiles.length]})`, backgroundPosition: `${Math.floor(r() * TILE)}px ${Math.floor(r() * TILE)}px` });
    },
  };
}
