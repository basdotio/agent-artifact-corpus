// s03 · Stat (8.0–10.6). The camera's dive into March opens a circle out of the bar itself: night falls,
// "+38%" counts up in the display face, the caption says what it means, and a line draws the six months.
import { scene, cue, bar, W, H } from "../core/runtime.js";
import { h, css, clamp } from "../core/anim.js";
import { expoOut, inOutSoft } from "../core/ease.js";
import { stage, circleWipe, recede, panelTf } from "../sys/stage.js";
import { lineChart } from "../sys/chart.js";
import { countUp } from "../sys/ui.js";
import { particles } from "../sys/particles.js";
import { heroBarScreen } from "./s02_product.js";

export const T3 = { wipe: 8.22, stat: bar(4) + 0.3, cap: 9.0, line: 8.75, out: 10.0 };

scene({
  id: "s03",
  start: 8.0,
  end: 10.65,
  z: 30,
  samples: (lt, t) => (t < T3.wipe + 0.6 || t > T3.out ? 10 : 2),
  build(root, s) {
    s.panel = h("div", { class: "fill", style: { overflow: "hidden", transformOrigin: "50% 50%" } });
    s.bg = stage("night");
    s.sparks = particles(s.bg.el, { n: 40, seed: 21, size: [2, 5], speed: [0, -18], color: "var(--accent-2)", opacity: [0.08, 0.35], blur: 0.4 });
    s.stat = h("div", { class: "abs t-mega tab", style: { left: "0", width: `${W}px`, top: `${H * 0.2}px`, textAlign: "center", color: "#fff" }, text: "+0%" });
    s.cap = h("div", { class: "abs t-cap", style: { left: "0", width: `${W}px`, top: `${H * 0.47}px`, textAlign: "center", color: "rgba(255,255,255,.72)" }, text: "March, explained in four seconds." });
    s.line = lineChart({ values: [118, 124, 131, 127, 136, 188], width: 900, height: 230, stroke: "var(--accent-2)" });
    s.lineWrap = h("div", { class: "abs", style: { left: `${(W - 900) / 2}px`, top: `${H * 0.6}px` } }, s.line.el);
    s.panel.append(s.bg.el, s.stat, s.cap, s.lineWrap);
    root.appendChild(s.panel);
    cue(T3.stat, "relay", { i: 9 });
  },
  update(lt, t, s) {
    s.bg.update(t);
    s.sparks.update(t);
    // the circle opens from wherever the hero bar is on screen (it is converging on the centre as we dive)
    const p = heroBarScreen(Math.min(t, T3.wipe + 0.55));
    circleWipe(s.panel, t, T3.wipe, 0.55, p.x, p.y, inOutSoft);
    const u = expoOut(clamp((t - T3.stat) / 0.7));
    css(s.stat, { opacity: clamp((t - T3.stat) / 0.25).toFixed(3), transform: `translateY(${((1 - u) * 40).toFixed(2)}px) scale(${(0.96 + 0.04 * u).toFixed(4)})` });
    countUp(s.stat, t, T3.stat, 1.1, 0, 38, (v) => `+${Math.round(v)}%`);
    const c = expoOut(clamp((t - T3.cap) / 0.8));
    css(s.cap, { opacity: clamp((t - T3.cap) / 0.4).toFixed(3), transform: `translateY(${((1 - c) * 16).toFixed(2)}px)` });
    s.line.set(expoOut(clamp((t - T3.line) / 1.3)));
    panelTf(s.panel, recede(t, T3.out, 1.0), {});
  },
});
