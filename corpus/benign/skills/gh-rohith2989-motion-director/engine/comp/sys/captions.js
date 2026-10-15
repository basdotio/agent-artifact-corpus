// Captions for watching muted (most social video is watched without sound): the spoken phrase on a soft pill,
// each word firming up as it is said. Phrases are cut by hand for reading; their words are matched to the
// voice's word times (comp/data/vo.json). Register once: captionsScene({ phrases }).
import { scene, W, H, DURATION } from "../core/runtime.js";
import { h, css, clamp } from "../core/anim.js";
import { expoOut } from "../core/ease.js";
import { allLines } from "./vo.js";

const norm = (s) => s.toLowerCase().replace(/[—–-]/g, " ").replace(/@/g, " at ").replace(/[^a-z0-9' ]/g, " ").split(/\s+/).filter(Boolean);

/**
 * phrases: one array per voice line, each an array of caption strings that together read exactly that line
 *   (display spelling is free — "@acme" may stand for the spoken "at acme"; tokens are matched in order).
 * skip: phrases not to show (e.g. a line the picture already writes on screen).
 * bottom: px from the frame's bottom to the pill's bottom (respect the platform's safe zone).
 */
export function captionsScene({ phrases, skip = [], bottom = Math.round(H * 0.054), z = 90, size = Math.round(H * 0.0315) } = {}) {
  const SKIP = new Set(skip);
  return scene({
    id: "captions",
    start: 0,
    end: DURATION,
    z,
    build(root) {
      const lines = allLines();
      this.caps = [];
      phrases.forEach((phs, li) => {
        const words = lines[li].words;
        let k = 0;
        phs.forEach((ph) => {
          const el = h("div", { class: "cap", style: { fontSize: `${size}px`, lineHeight: `${Math.round(size * 1.3)}px` } });
          const parts = [];
          ph.split(" ").forEach((tok, i) => {
            const n = norm(tok);
            const span = h("span", { text: tok });
            if (i) el.appendChild(document.createTextNode(" "));
            el.appendChild(span);
            if (n.length) {
              const vw = words[k];
              if (!vw) throw new Error(`captions: ran out of voice words at "${tok}" (line ${li})`);
              parts.push({ span, t0: vw.t0 });
              k += n.length;
            } else parts.push({ span, t0: null });
          });
          for (let i = parts.length - 1; i >= 0; i--) if (parts[i].t0 == null) parts[i].t0 = parts[i + 1]?.t0 ?? parts[i - 1].t0;
          if (SKIP.has(ph)) el.style.visibility = "hidden";
          root.appendChild(el);
          this.caps.push({ el, parts, w: el.offsetWidth, hh: el.offsetHeight, t0: parts[0].t0, t1: words[Math.min(k, words.length) - 1].t1, li });
        });
      });
      this.caps.forEach((c, i) => {
        const nx = this.caps[i + 1];
        c.in = c.t0 - 0.12;
        c.out = nx && nx.li === c.li ? nx.t0 - 0.12 : Math.min(c.t1 + 0.55, nx ? nx.t0 - 0.12 : 1e9);
      });
    },
    update(lt, t) {
      for (const c of this.caps) {
        const vis = t >= c.in - 0.01 && t < c.out + 0.2;
        css(c.el, { display: vis ? "block" : "none" });
        if (!vis) continue;
        const a = clamp((t - c.in) / 0.16) * (1 - clamp((t - c.out) / 0.16));
        const u = expoOut(clamp((t - c.in) / 0.4));
        css(c.el, { opacity: a.toFixed(3), transform: `translate(${(W / 2 - c.w / 2).toFixed(1)}px, ${(H - bottom - c.hh + (1 - u) * 8).toFixed(2)}px)` });
        for (const p of c.parts) css(p.span, { opacity: (0.38 + 0.62 * clamp((t - p.t0 + 0.04) / 0.14)).toFixed(3) });
      }
    },
  });
}
