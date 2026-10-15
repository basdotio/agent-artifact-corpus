// s01 · Title (0–4.6). Living light on the page colour, a few motes of dust, an eyebrow, then the line
// "Every number, explained." word by word — the accent word lands on bar 1 with the score's struck chord.
import { scene, cue, bar, W, H } from "../core/runtime.js";
import { h, css, clamp } from "../core/anim.js";
import { expoOut } from "../core/ease.js";
import { Words } from "../sys/reveal.js";
import { livingLight } from "../sys/light.js";
import { particles } from "../sys/particles.js";
import { recede, panelTf } from "../sys/stage.js";

export const T1 = { eyebrow: 0.35, w0: 0.6, accent: bar(1), sub: 2.55, out: 3.6 };

scene({
  id: "s01",
  start: 0,
  end: 4.6,
  z: 10,
  samples: (lt, t) => (t > T1.out ? 8 : 1),
  build(root, s) {
    s.panel = h("div", { class: "fill", style: { transformOrigin: "50% 50%", overflow: "hidden" } });
    s.light = livingLight(s.panel, { base: "var(--bg)", colors: ["var(--accent-2)", "#ffffff", "var(--accent-2)", "#ffe9d6"], count: 5, seed: 3, speed: 0.045, strength: 0.6 });
    s.dust = particles(s.panel, { n: 46, seed: 5, size: [2, 6], speed: [5, -9], color: "var(--accent)", opacity: [0.05, 0.22], blur: 0.5 });
    s.eyebrow = h("div", { class: "abs t-label", style: { left: "0", width: `${W}px`, top: `${H * 0.3}px`, textAlign: "center", color: "var(--accent)" }, text: "Introducing Lumen" });
    s.titleEl = h("div", { class: "abs t-giant", style: { left: "0", width: `${W}px`, top: `${H * 0.355}px`, textAlign: "center" } });
    s.words = new Words(s.titleEl, ["Every number,", "*explained.*"]).in(T1.w0, { stagger: 0.16, line: 0.0, dur: 0.9 });
    // the accent word arrives on the downbeat, not on the stagger
    s.words.cfgIn.order = [0, 1, (T1.accent - T1.w0) / 0.16];
    s.sub = h("div", { class: "abs t-cap", style: { left: "0", width: `${W}px`, top: `${H * 0.625}px`, textAlign: "center" }, text: "Lumen reads your data and answers in plain words." });
    s.panel.append(s.eyebrow, s.titleEl, s.sub);
    root.appendChild(s.panel);
    cue(T1.eyebrow, "tick", { gain: -4 });
  },
  update(lt, t, s) {
    s.light.update(t);
    s.dust.update(t);
    const e = expoOut(clamp((t - T1.eyebrow) / 0.8));
    css(s.eyebrow, { opacity: clamp((t - T1.eyebrow) / 0.4).toFixed(3), transform: `translateY(${((1 - e) * 14).toFixed(2)}px)`, letterSpacing: `${(0.18 + 0.12 * (1 - e)).toFixed(3)}em` });
    s.words.update(t);
    const u = expoOut(clamp((t - T1.sub) / 0.9));
    css(s.sub, { opacity: clamp((t - T1.sub) / 0.5).toFixed(3), transform: `translateY(${((1 - u) * 18).toFixed(2)}px)` });
    // when the next panel slides over, this one steps back
    panelTf(s.panel, recede(t, T1.out, 1.0));
  },
});
