// "Living light": soft coloured pools drifting over a base, like light moving across a wall — the premium
// alternative to a flat background or a stock gradient video. Deterministic (seeded phases, pure in t).
import { h, css } from "../core/anim.js";
import { mulberry32 } from "../core/rand.js";
import { W, H } from "../core/runtime.js";

/**
 * livingLight(parent, { base, colors, count, seed, speed, size, blend, strength })
 *  colors: CSS colours (theme vars work: "var(--accent)") cycled across `count` pools
 *  speed: cycles per second of the slowest pool (0.03–0.08 reads as calm; >0.15 feels busy)
 */
export function livingLight(parent, { base = "var(--bg)", colors = ["var(--accent)", "var(--accent-2)", "#ffffff"], count = 5, seed = 7, speed = 0.05, size = 0.95, blend = "normal", strength = 0.55 } = {}) {
  const el = h("div", { class: "fill", style: { background: base, overflow: "hidden" } });
  const r = mulberry32(seed);
  const pools = Array.from({ length: count }, (_, i) => {
    const s = (0.55 + r() * 0.6) * size;
    const d = h("div", {
      style: {
        position: "absolute", left: "0", top: "0", width: `${W * s}px`, height: `${W * s}px`, borderRadius: "50%",
        background: `radial-gradient(closest-side, color-mix(in srgb, ${colors[i % colors.length]} ${Math.round(strength * 100)}%, transparent), transparent)`,
        mixBlendMode: blend, willChange: "transform",
      },
    });
    el.appendChild(d);
    return {
      d, s,
      cx: r() * W, cy: r() * H, ax: (0.18 + r() * 0.3) * W, ay: (0.14 + r() * 0.25) * H,
      fx: speed * (0.6 + r() * 0.9), fy: speed * (0.5 + r() * 0.9), px: r() * 6.283, py: r() * 6.283,
    };
  });
  parent.appendChild(el);
  return {
    el,
    update(t) {
      for (const p of pools) {
        const x = p.cx + p.ax * Math.sin(6.283 * p.fx * t + p.px) - (W * p.s) / 2;
        const y = p.cy + p.ay * Math.sin(6.283 * p.fy * t + p.py) - (W * p.s) / 2;
        css(p.d, { transform: `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)` });
      }
    },
  };
}
