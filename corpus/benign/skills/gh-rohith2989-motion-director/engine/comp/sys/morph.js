// One card, many screens: the card's frame morphs between each screen's size while the contents cross-fade,
// clipped to the frame. Reads as one continuous object travelling through a flow (step 1 → 2 → 3).
import { css, clamp, lerp } from "../core/anim.js";
import { bezier, expoOut } from "../core/ease.js";

const MORPH = bezier(0.45, 0, 0.1, 1);

/**
 * createMorph(frameEl, cards) — frameEl draws the card (background, border, shadow, radius); cards are the
 * contents, each absolutely placed where its own screen puts it. Build-time: pass each card's frame rect
 * { el, x, y, w, h } (layout px, contents + border). steps: [[t0, fromIndex, toIndex, dur], …] in order.
 */
export function createMorph(frameEl, cards, steps, { radius = 14, border = 1 } = {}) {
  const at = (t) => {
    let from = steps.length ? steps[0][1] : 0, to = from, u = 0;
    for (const [t0, a, b, d] of steps) {
      if (t >= t0) {
        from = a;
        to = b;
        u = MORPH(clamp((t - t0) / d));
      }
    }
    return { from, to, u };
  };
  return {
    update(t) {
      const { from, to, u } = at(t);
      const A = cards[from], B = cards[to];
      const f = { x: lerp(A.x, B.x, u), y: lerp(A.y, B.y, u), w: lerp(A.w, B.w, u), h: lerp(A.h, B.h, u) };
      css(frameEl, { left: `${f.x.toFixed(2)}px`, top: `${f.y.toFixed(2)}px`, width: `${f.w.toFixed(2)}px`, height: `${f.h.toFixed(2)}px` });
      // the outgoing contents leave quickly; the incoming arrive a beat later, rising a few px
      const last = steps.filter((s) => t >= s[0]).pop();
      cards.forEach((c, i) => {
        let o = 0;
        if (!last) o = i === from ? 1 : 0;
        else if (i === to) o = clamp((t - last[0] - 0.1) / 0.3);
        else if (i === from && from !== to) o = 1 - clamp((t - last[0] - 0.04) / 0.2);
        css(c.el, { opacity: o.toFixed(3), display: o > 0.001 ? "block" : "none" });
        if (o <= 0.001) return;
        if (last && i === to) css(c.el, { transform: `translateY(${((1 - expoOut(clamp((t - last[0] - 0.2) / 0.6))) * 10).toFixed(2)}px)` });
        // clip to the frame's inner rect
        const cx = c.x + border, cy = c.y + border, cw = c.w - 2 * border, ch = c.h - 2 * border;
        const top = Math.max(0, f.y + border - cy), left = Math.max(0, f.x + border - cx);
        const right = Math.max(0, cx + cw - (f.x + f.w - border)), bottom = Math.max(0, cy + ch - (f.y + f.h - border));
        css(c.el, { clipPath: `inset(${top.toFixed(2)}px ${right.toFixed(2)}px ${bottom.toFixed(2)}px ${left.toFixed(2)}px round ${radius - border}px)` });
      });
      return f;
    },
  };
}
