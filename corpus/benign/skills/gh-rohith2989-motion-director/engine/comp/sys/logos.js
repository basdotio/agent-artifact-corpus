// Brand marks for integration walls and "works with" moments: 3,400+ logos from simple-icons (CC0 data;
// the marks themselves are their owners' trademarks — show only tools the product really supports).
// Call `await loadLogos(["hubspot", "stripe", "googlesheets"])` in a scene's build() before using them.
import { h } from "../core/anim.js";

const ICONS = new Map(); // slug -> { path, hex, title }
let DATA = null;

const base = new URL("../../node_modules/simple-icons/", import.meta.url);

/** Load the given slugs (see https://simpleicons.org for slugs: "googlesheets", "hubspot", "notion"…). */
export async function loadLogos(slugs) {
  if (!DATA) DATA = await (await fetch(new URL("data/simple-icons.json", base))).json();
  await Promise.all(slugs.filter((s) => !ICONS.has(s)).map(async (slug) => {
    const res = await fetch(new URL(`icons/${slug}.svg`, base));
    const path = res.ok ? ((await res.text()).match(/ d="([^"]+)"/) || [])[1] : null;
    const meta = DATA.find((d) => d.slug === slug) || DATA.find((d) => d.title.toLowerCase().replace(/[^a-z0-9]/g, "") === slug);
    // some brands (e.g. Slack, Microsoft products) asked simple-icons to remove them: draw those marks from the
    // brand's own press kit SVG instead (and only where the product really integrates with them)
    if (!path) throw new Error(`logos: "${slug}" is not in simple-icons — use the brand's official SVG from its press kit`);
    ICONS.set(slug, { path, hex: `#${meta?.hex ?? "333333"}`, title: meta?.title ?? slug });
  }));
}

/** A brand mark as an SVG element (brand colour unless `color` is given). */
export function brandMark(slug, size = 24, color = null) {
  const i = ICONS.get(slug);
  if (!i) throw new Error(`logos: "${slug}" not loaded — await loadLogos([...]) in build()`);
  return h("svg", { viewBox: "0 0 24 24", width: size, height: size, style: { display: "block", flex: "none" } }, h("path", { d: i.path, fill: color ?? i.hex }));
}

/** An app tile: the brand colour as the field, the mark in white (ink if the brand colour is light). */
export function appTile(slug, size = 96, { radius = size * 0.235, label = false } = {}) {
  const i = ICONS.get(slug);
  const x = i.hex.replace("#", "");
  const luma = (0.299 * parseInt(x.slice(0, 2), 16) + 0.587 * parseInt(x.slice(2, 4), 16) + 0.114 * parseInt(x.slice(4, 6), 16)) / 255;
  const el = h("div", { style: { position: "relative", width: `${size}px`, height: `${size}px`, borderRadius: `${radius}px`, background: i.hex, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", boxShadow: "inset 0 0 0 1px rgba(255,255,255,.12), 0 3px 0 rgba(30,20,60,.06), 0 20px 40px -18px rgba(30,20,60,.45)" } },
    brandMark(slug, Math.round(size * 0.5), luma > 0.72 ? "#1b1a22" : "#ffffff"));
  if (label) el.appendChild(h("div", { style: { position: "absolute", left: 0, right: 0, bottom: 0, padding: `${size * 0.12}px 4px ${size * 0.05}px`, textAlign: "center", font: `600 ${Math.max(9, size * 0.115)}px/1.1 var(--sans)`, color: luma > 0.72 ? "#1b1a22" : "#fff", background: "linear-gradient(to top, rgba(0,0,0,.35), transparent)" }, text: i.title }));
  return el;
}

/** A cream tile holding the full-colour mark (floating "works with" tiles). */
export function creamTile(slug, size = 96) {
  return h("div", { style: { width: `${size}px`, height: `${size}px`, borderRadius: `${size * 0.25}px`, background: "#fffdf8", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "inset 0 0 0 1px rgba(60,49,91,.1), 0 3px 0 rgba(60,49,91,.08), 0 22px 44px -18px rgba(60,49,91,.5)" } }, brandMark(slug, Math.round(size * 0.5)));
}
