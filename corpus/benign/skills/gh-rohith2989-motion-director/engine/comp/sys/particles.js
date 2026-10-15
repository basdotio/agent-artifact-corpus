// Atmosphere: seeded particles — dust in a light beam, soft bokeh, sparks rising — that drift and wrap,
// pure in t. Use sparingly (depth and air, never confetti) and keep them behind the subject.
import { h, css } from "../core/anim.js";
import { mulberry32 } from "../core/rand.js";
import { W, H } from "../core/runtime.js";

/**
 * particles(parent, { n, seed, size:[min,max], speed:[vx,vy] px/s, color, blur, opacity:[min,max], twinkle })
 * Each particle wraps around the frame, so the field never runs out.
 */
export function particles(parent, { n = 60, seed = 11, size = [2, 7], speed = [6, -14], color = "#ffffff", blur = 0.6, opacity = [0.15, 0.6], twinkle = 0.35, depth = 0.6 } = {}) {
  const el = h("div", { class: "fill", style: { overflow: "hidden", pointerEvents: "none" } });
  const r = mulberry32(seed);
  const ps = Array.from({ length: n }, () => {
    const z = r(); // 0 far … 1 near: nearer = bigger, faster, softer
    const s = size[0] + (size[1] - size[0]) * z;
    const d = h("div", {
      style: {
        position: "absolute", left: "0", top: "0", width: `${s}px`, height: `${s}px`, borderRadius: "50%",
        background: `radial-gradient(circle, ${color} 0%, ${color} 35%, transparent 72%)`, filter: blur ? `blur(${(blur * s * z).toFixed(2)}px)` : "",
      },
    });
    el.appendChild(d);
    return { d, s, x: r() * W, y: r() * H, vx: speed[0] * (1 - depth + depth * z) * (0.6 + r() * 0.8), vy: speed[1] * (1 - depth + depth * z) * (0.6 + r() * 0.8), a: opacity[0] + (opacity[1] - opacity[0]) * r(), f: 0.2 + r() * 0.6, ph: r() * 6.28 };
  });
  parent.appendChild(el);
  const wrap = (v, m) => ((v % m) + m) % m;
  return {
    el,
    update(t) {
      for (const p of ps) {
        const x = wrap(p.x + p.vx * t + 30, W + 60) - 30;
        const y = wrap(p.y + p.vy * t + 30, H + 60) - 30;
        const a = p.a * (1 - twinkle + twinkle * (0.5 + 0.5 * Math.sin(6.283 * p.f * t + p.ph)));
        css(p.d, { transform: `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`, opacity: a.toFixed(3) });
      }
    },
  };
}
