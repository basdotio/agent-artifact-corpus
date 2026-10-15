// The default motion of the search-results video. The renderer loads store/video/motion.js instead when the project
// has one: copy this file there and change it.
//
// What is on the stage: for every scene i = 0 … N - 1, and once more for i = N (a copy of the first scene, which the
// loop ends on), a background `.v-bg[data-i]`, a text `.v-text[data-i]` and a card `.v-card[data-i]`.
// What is given: N (scenes), D (seconds per scene), TR (seconds of the transition at the end of each scene),
// RTL (true for a language written from right to left).
// What this file must do: define window.renderAt(t) for t from 0 to N * D seconds, setting styles from the time alone
// (no timers, no CSS animations: frames are captured one by one, in any order), and bring the stage back to the
// picture at 0 at least one frame before N * D: the last captured frame is the one at N * D - 1 / fps, and it has to
// equal the first or the loop shows a seam.
const clamp = (x) => Math.min(1, Math.max(0, x));
const ease = (x) => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const easeIn = (x) => clamp(x) ** 3, easeOut = (x) => 1 - Math.pow(1 - clamp(x), 3);
const part = (p, a, b) => (p - a) / (b - a);
const all = (selector) => [...document.querySelectorAll(selector)];
// Everything on the stage is a function of the time alone, so a frame can be rendered in any order.
window.renderAt = (t) => {
  t = Math.min(Math.max(t, 0), N * D);
  const i = Math.min(Math.floor(t / D), N - 1), local = t - i * D;
  const p = local < D - TR ? -1 : (local - (D - TR)) / TR;   // 0..1 through the transition from scene i to i + 1
  for (const e of all(".v-bg")) {   // the next colour fades in over the current one
    const k = +e.dataset.i, o = k === i ? 1 : k === i + 1 && p >= 0 ? ease(part(p, .05, .8)) : 0;
    e.style.opacity = o; e.style.zIndex = k === i ? 1 : 2; e.style.visibility = o > 0 ? "visible" : "hidden";
  }
  for (const e of all(".v-text")) {   // fades out and in with a slight scale
    const k = +e.dataset.i; let o = 0, sc = 1;
    if (k === i) { const q = p < 0 ? 0 : easeIn(part(p, 0, .32)); o = 1 - q; sc = 1 - .05 * q; }
    if (k === i + 1 && p >= 0) { const q = easeOut(part(p, .55, .94)); o = q; sc = .95 + .05 * q; }
    e.style.opacity = o; e.style.transform = "scale(" + sc + ")"; e.style.visibility = o > 0 ? "visible" : "hidden";
  }
  for (const e of all(".v-card")) {   // flips from the side: the old card turns away, the new one turns in
    const k = +e.dataset.i; let r = null;
    if (k === i) r = p < 0 ? 0 : p < .5 ? -90 * easeIn(part(p, .12, .5)) : null;
    if (k === i + 1 && p >= .5) r = 90 * (1 - easeOut(part(p, .5, .88)));
    // Once the last flip has landed, the first scene's own card stands in for its copy: the copy rasterises a
    // fraction of a pixel off, and the loop point has to be exact.
    if (i === N - 1 && p >= .88) r = k === 0 ? 0 : null;
    e.style.visibility = r === null ? "hidden" : "visible"; e.style.transform = "rotateY(" + (RTL ? -1 : 1) * (r ?? 0) + "deg)";
  }
};
