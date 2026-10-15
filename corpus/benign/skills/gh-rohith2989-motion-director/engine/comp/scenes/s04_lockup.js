// s04 · Lockup (10.0–12). The dawn panel slides over the night; the mark arrives, the wordmark rises letter by
// letter beside it, the address settles beneath. The score's last chord lands on 10.0, the lockup sound on the mark.
import { scene, cue, bar, W, H } from "../core/runtime.js";
import { h, css, clamp } from "../core/anim.js";
import { expoOut, inOutSoft } from "../core/ease.js";
import { Letters } from "../sys/reveal.js";
import { slideIn, panelTf } from "../sys/stage.js";
import { livingLight } from "../sys/light.js";
import { lumenMark } from "./s02_product.js";

export const T4 = { in: bar(5), mark: bar(5) + 0.42, word: bar(5) + 0.62, url: bar(5) + 1.05 };

scene({
  id: "s04",
  start: T4.in,
  end: 12,
  z: 40,
  samples: (lt, t) => (t < T4.in + 1.0 ? 10 : t < T4.mark + 0.6 ? 6 : 1),
  build(root, s) {
    s.panel = h("div", { class: "fill", style: { overflow: "hidden", transformOrigin: "50% 50%" } });
    s.light = livingLight(s.panel, { base: "var(--bg)", colors: ["var(--accent-2)", "#ffffff", "#ffe2cc"], count: 4, seed: 9, speed: 0.04, strength: 0.7 });
    s.markEl = h("div", { class: "abs" }, lumenMark(132));
    s.word = h("div", { class: "abs", style: { font: "600 150px/1 var(--disp)", letterSpacing: "-0.035em", color: "var(--ink)", whiteSpace: "nowrap" } });
    s.letters = new Letters(s.word, "Lumen");
    s.url = h("div", { class: "abs t-cap", style: { left: "0", width: `${W}px`, top: `${H * 0.62}px`, textAlign: "center" }, text: "lumen.example" });
    s.panel.append(s.markEl, s.word, s.url);
    root.appendChild(s.panel);
    // lay the lockup out once, centred as a unit (mark + gap + wordmark)
    s.ww = s.word.offsetWidth;
    const total = 132 + 34 + s.ww;
    s.x0 = (W - total) / 2;
    css(s.markEl, { left: `${s.x0}px`, top: `${H * 0.42 - 66}px` });
    css(s.word, { left: `${s.x0 + 132 + 34}px`, top: `${H * 0.42 - 78}px` });
    cue(T4.in, "panel");
    cue(T4.mark, "lockup");
  },
  update(lt, t, s) {
    // slide over the night, then a slow push on the held end card keeps it alive
    const sl = slideIn(t, T4.in, 1.0);
    const push = 1 + 0.025 * inOutSoft(clamp((t - T4.mark) / 2.2));
    panelTf(s.panel, { y: sl.y, r: sl.r, s: push });
    s.light.update(t);
    const m = expoOut(clamp((t - T4.mark) / 0.9));
    css(s.markEl, { opacity: clamp((t - T4.mark) / 0.25).toFixed(3), transform: `translateY(${((1 - m) * 26).toFixed(2)}px) scale(${(0.86 + 0.14 * m).toFixed(4)}) rotate(${((1 - m) * -8).toFixed(2)}deg)` });
    s.letters.words.forEach((L, i) => {
      const s0 = T4.word + i * 0.045;
      const u = expoOut(clamp((t - s0) / 0.8));
      css(L.w, { transform: `translateY(${((1 - u) * 110).toFixed(2)}%)`, opacity: clamp(((t - s0) / 0.8) * 2.2).toFixed(3) });
    });
    const a = clamp((t - T4.url) / 0.5);
    css(s.url, { opacity: a.toFixed(3), transform: `translateY(${((1 - expoOut(a)) * 12).toFixed(2)}px)` });
  },
});
