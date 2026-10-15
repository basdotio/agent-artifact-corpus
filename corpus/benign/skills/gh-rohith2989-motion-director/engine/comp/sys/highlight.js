// Pointing at words: an editorial marker underline that sweeps in as a phrase is spoken, and a spotlight
// that steps everything else back. Both are cheap, legible at any zoom, and never look like a hack.
import { h, css, clamp } from "../core/anim.js";

/** Split `text` so `phrase` can be highlighted. Returns { nodes, hl } — append nodes, animate hl. */
export function withHighlight(text, phrase) {
  const i = text.indexOf(phrase);
  if (i < 0) throw new Error(`highlight: "${phrase}" not in "${text}"`);
  const hl = h("span", { class: "hl", text: phrase });
  return { nodes: [document.createTextNode(text.slice(0, i)), hl, document.createTextNode(text.slice(i + phrase.length))], hl };
}

/** Sweep the marker on (u 0..1); the words take `tint` as it passes (null keeps their colour). */
export function setHighlight(hl, u, tint = "var(--ink)") {
  css(hl, { backgroundSize: `${(clamp(u) * 100).toFixed(2)}% 100%`, color: tint && u > 0.02 ? tint : "" });
}

/**
 * Spotlight: every element of `els` except those in `keep` fades toward `dim` by amount k (0..1).
 * Use while a voice talks about one paragraph of a dense screen.
 */
export function spotlight(els, keep, k, dim = 0.22) {
  const ks = new Set(Array.isArray(keep) ? keep : [keep]);
  for (const el of els) css(el, { opacity: ks.has(el) ? "1" : (1 - (1 - dim) * clamp(k)).toFixed(3) });
}

/** A soft glow ring around an element (0..1), e.g. a tile being named. */
export function glowRing(el, k, color = "var(--accent)") {
  css(el, { boxShadow: k > 0.001 ? `0 0 0 ${(3 * k).toFixed(2)}px color-mix(in srgb, ${color} ${Math.round(45 * k)}%, transparent)` : "" });
}
