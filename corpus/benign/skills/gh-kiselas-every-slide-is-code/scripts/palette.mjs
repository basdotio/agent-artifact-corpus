#!/usr/bin/env node
// deck-kit palette generator: one accent in, a six-role palette out, in OKLCH, with the kit's own
// contrast rules (04-slide-design.md) guaranteed and measured. No dependencies: the colour maths
// (sRGB <-> OKLab, WCAG 2 ratio, APCA Lc) is implemented below and exported for other tools
// (scripts/analyze-reference.mjs uses it).
//
//   node scripts/palette.mjs --accent "#dd4428" [--bg light|dark|"#f4f2ee"] [--second auto|"#2b7a4b"]
//                            [--name my-deck] [--html swatches.html] [--json]
//
// Guarantees (the run exits 1 if one cannot be met, e.g. a custom mid-tone background):
//   ink          >= 7:1 on the background (aims for 12:1)
//   muted        >= 4.5:1 (aims for 5:1, so anti-aliasing and a projector do not push it under)
//   accent-text  >= 4.5:1 (equal to the accent when the accent already passes; a darker/lighter variant
//                of the same hue otherwise); the plain accent is safe for large text (>= 40 px) only
//                when the table says >= 3:1
//   second-text  same as accent-text for the second accent
//   on-accent    the text colour (ink or the lightest tint) that reads best on an accent-coloured fill

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/* ───────── colour maths ───────── */

export const clamp01 = x => Math.min(1, Math.max(0, x));
export const hexToRgb = h => {
  let s = String(h).trim().replace(/^#/, '');
  if (s.length === 3) s = [...s].map(c => c + c).join('');
  if (!/^[0-9a-f]{6}$/i.test(s)) throw new Error(`not a hex colour: "${h}"`);
  return [0, 2, 4].map(i => parseInt(s.slice(i, i + 2), 16));
};
export const rgbToHex = c => '#' + c.map(v => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, '0')).join('');
const toLin = c => { c /= 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; };
const fromLin = c => 255 * (c <= .0031308 ? 12.92 * c : 1.055 * Math.max(0, c) ** (1 / 2.4) - .055);

// Björn Ottosson's OKLab (2020): linear sRGB -> LMS -> cube root -> Lab.
export function rgbToOklab([r, g, b]) {
  const R = toLin(r), G = toLin(g), B = toLin(b);
  const l = Math.cbrt(.4122214708 * R + .5363325363 * G + .0514459929 * B);
  const m = Math.cbrt(.2119034982 * R + .6806995451 * G + .1073969566 * B);
  const s = Math.cbrt(.0883024619 * R + .2817188376 * G + .6299787005 * B);
  return [.2104542553 * l + .793617785 * m - .0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + .4505937099 * s,
    .0259040371 * l + .7827717662 * m - .808675766 * s];
}
// unclamped linear sRGB of an OKLab colour (values outside 0..1 mean out of gamut)
export function oklabToLinear([L, a, b]) {
  const l = (L + .3963377774 * a + .2158037573 * b) ** 3, m = (L - .1055613458 * a - .0638541728 * b) ** 3, s = (L - .0894841775 * a - 1.291485548 * b) ** 3;
  return [4.0767416621 * l - 3.3077115913 * m + .2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s, -.0041960863 * l - .7034186147 * m + 1.707614701 * s];
}
export const oklabToRgb = lab => oklabToLinear(lab).map(v => fromLin(clamp01(v)));
export const oklabToOklch = ([L, a, b]) => { const C = Math.hypot(a, b); return [L, C, C < 1e-4 ? 0 : (Math.atan2(b, a) * 180 / Math.PI + 360) % 360]; };
export const oklchToOklab = ([L, C, h]) => [L, C * Math.cos(h * Math.PI / 180), C * Math.sin(h * Math.PI / 180)];
export const hexToOklch = h => oklabToOklch(rgbToOklab(hexToRgb(h)));
export const deltaE = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);   // Euclidean distance in OKLab (0.02 is about a just-noticeable step)

const inGamut = lin => lin.every(v => v >= -.0005 && v <= 1.0005);
// OKLCH -> hex; an out-of-gamut colour keeps its lightness and hue and loses chroma (binary search), not its hue.
export function oklchToHex([L, C, h]) {
  L = clamp01(L);
  if (!inGamut(oklabToLinear(oklchToOklab([L, C, h])))) {
    let lo = 0, hi = C;
    for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2; (inGamut(oklabToLinear(oklchToOklab([L, mid, h]))) ? (lo = mid) : (hi = mid)); }
    C = lo;
  }
  return rgbToHex(oklabToRgb(oklchToOklab([L, C, h])));
}

export const luminance = c => .2126 * toLin(c[0]) + .7152 * toLin(c[1]) + .0722 * toLin(c[2]);
export function wcag(a, b) {   // WCAG 2 contrast ratio, hex or [r,g,b]
  const A = luminance(typeof a === 'string' ? hexToRgb(a) : a), B = luminance(typeof b === 'string' ? hexToRgb(b) : b);
  return (Math.max(A, B) + .05) / (Math.min(A, B) + .05);
}
// APCA (SAPC 0.0.98G-4g, the constants of Myndex/apca-w3 0.1.9; the same as export/deck.mjs check). Positive: dark text on light.
export function apca(txt, bg) {
  const rgb = c => (typeof c === 'string' ? hexToRgb(c) : c);
  const Y = c => .2126729 * (c[0] / 255) ** 2.4 + .7151522 * (c[1] / 255) ** 2.4 + .072175 * (c[2] / 255) ** 2.4;
  const clampY = y => (y > .022 ? y : y + (.022 - y) ** 1.414);
  const yt = clampY(Y(rgb(txt))), yb = clampY(Y(rgb(bg)));
  if (Math.abs(yb - yt) < .0005) return 0;
  let s;
  if (yb > yt) { s = (yb ** .56 - yt ** .57) * 1.14; s = s < .1 ? 0 : s - .027; }
  else { s = (yb ** .65 - yt ** .62) * 1.14; s = s > -.1 ? 0 : s + .027; }
  return s * 100;
}

/* ───────── palette ───────── */

const fmtOklch = ([L, C, h]) => `L${L.toFixed(3)} C${C.toFixed(3)} h${Math.round(h)}`;

// Find the colour closest to `fromL` (moving towards `toL`) at fixed chroma and hue whose contrast with `bg` is at least `target`.
function solveL(bg, C, h, fromL, toL, target) {
  const at = L => oklchToHex([L, C, h]);
  if (wcag(at(fromL), bg) >= target) return at(fromL);
  if (wcag(at(toL), bg) < target) return null;
  let lo = fromL, hi = toL;   // lo fails, hi passes
  for (let i = 0; i < 30; i++) { const mid = (lo + hi) / 2; (wcag(at(mid), bg) >= target ? (hi = mid) : (lo = mid)); }
  return at(hi);
}

export function derivePalette({ accent, bg = 'light', second = 'auto' }) {
  const warnings = [];
  const acc = oklchToHex(hexToOklch(accent));   // normalised hex
  const [aL, aC, aH] = hexToOklch(acc);
  const hue = aC < .02 ? 80 : aH;                // a grey accent: tint the neutrals warm
  const isHex = /^#?[0-9a-f]{3}([0-9a-f]{3})?$/i.test(bg);
  let dark, bgHex;
  if (isHex) { bgHex = rgbToHex(hexToRgb(bg)); dark = hexToOklch(bgHex)[0] < .6; }
  else if (bg === 'light' || bg === 'dark') { dark = bg === 'dark'; bgHex = oklchToHex(dark ? [.17, .014, hue] : [.955, .007, hue]); }
  else throw new Error(`--bg: light, dark or a hex colour (got "${bg}")`);
  const [bL, , bH] = hexToOklch(bgHex), bgHue = hexToOklch(bgHex)[1] < .004 ? hue : bH;
  const end = dark ? 1 : 0, start = dark ? Math.min(.985, bL + .25) : Math.max(.02, bL - .25);
  const roles = [];
  const add = (role, css, hex, need, note = '') => roles.push({ role, css, hex, oklch: hexToOklch(hex), ratio: wcag(hex, bgHex), lc: apca(hex, bgHex), need, note });
  roles.push({ role: 'background', css: '--bg', hex: bgHex, oklch: hexToOklch(bgHex), ratio: 1, lc: 0, need: 0, note: dark ? 'dark: needs higher contrast and fewer thin lines' : 'light survives projectors and PDFs better' });

  // ink: 12:1 if the background allows it, never under 7:1
  let ink = solveL(bgHex, .02, bgHue, start, end, 12) || solveL(bgHex, .02, bgHue, start, end, 7);
  if (!ink) { ink = oklchToHex([end, 0, 0]); warnings.push(`background ${bgHex} is too mid-toned for 7:1 ink: pure ${dark ? 'white' : 'black'} gives ${wcag(ink, bgHex).toFixed(2)}:1`); }
  add('ink', '--ink', ink, 7);
  // muted: the colour closest to the background that still gives 5:1 (7:1 on dark, where WCAG 2 flatters thin light text: APCA Lc ~45),
  // so the 4.5:1 rule holds with margin
  let muted = solveL(bgHex, .022, bgHue, dark ? bL + .06 : bL - .06, end, dark ? 7 : 5);
  if (!muted) { muted = ink; warnings.push('no muted colour reaches 4.5:1 on this background; using the ink colour'); }
  add('muted', '--muted', muted, 4.5);
  // rule: a hairline, decorative, about 1.7:1 (2:1 on dark; survives a projector without competing with text)
  const rule = solveL(bgHex, .018, bgHue, dark ? bL + .02 : bL - .02, end, dark ? 2 : 1.7) || muted;
  add('rule', '--rule', rule, 0, 'decorative; not text');

  // accents
  const textVariant = hex => {
    const [L, C, h] = hexToOklch(hex);
    if (wcag(hex, bgHex) >= 4.5) return { hex, changed: false };
    const t = solveL(bgHex, C, h, L, end, 4.6);
    return t ? { hex: t, changed: true } : { hex: ink, changed: true, failed: true };
  };
  add('accent', '--accent', acc, 3, wcag(acc, bgHex) >= 4.5 ? 'passes as text at any size' : wcag(acc, bgHex) >= 3 ? 'text only at 40 px and above; use accent-text below' : 'under 3:1: a fill, a rule or a swatch only; text uses accent-text');
  const at = textVariant(acc);
  add('accent-text', '--accent-text', at.hex, 4.5, at.failed ? 'FAILED: this background cannot carry a 4.5:1 tint of the accent' : at.changed ? 'same hue, darkened for small text' : 'the accent itself already passes');
  let sec;
  if (second === 'auto' || second == null) { const C2 = Math.min(aC, .16), h2 = (aH + 125) % 360; sec = solveL(bgHex, C2, h2, aL, end, 3.1) || oklchToHex([aL, C2, h2]); }   // same weight as the accent, pushed to 3:1 if it falls short
  else sec = oklchToHex(hexToOklch(second));
  add('second', '--second', sec, 3, second === 'auto' || second == null ? 'accent hue +125°, same chroma, lightness nudged to keep 3:1; use it only for a second meaning' : 'given');
  const st = textVariant(sec);
  add('second-text', '--second-text', st.hex, 4.5, st.failed ? 'FAILED' : st.changed ? 'same hue, adjusted for small text' : 'the second accent itself already passes');

  // text on an accent-coloured fill (badge numbers, buttons): the better of the ink and the lightest tint
  const paper = oklchToHex([.985, .006, bgHue]);
  const pickOn = fill => {   // the kit's own ink or paper if one reads (4.5:1), pure black or white only as a last resort
    const best = list => list.map(x => [x, wcag(x, fill)]).sort((p, q) => q[1] - p[1])[0];
    const kit = best([ink, paper]);
    return kit[1] >= 4.5 ? kit : best([ink, paper, '#ffffff', '#000000']);
  };
  const [onA, onARatio] = pickOn(acc);
  roles.push({ role: 'on-accent', css: '--on-accent', hex: onA, oklch: hexToOklch(onA), ratio: onARatio, ratioOn: acc, lc: apca(onA, acc), need: 4.5,
    note: onARatio >= 4.5 ? 'text on an accent-coloured fill' : `under 4.5:1 on the accent: put text on accent-text (${wcag(onA, at.hex).toFixed(2)}:1) or use it at 24 px bold or larger only` });
  const [onS, onSRatio] = pickOn(sec);
  roles.push({ role: 'on-second', css: '--on-second', hex: onS, oklch: hexToOklch(onS), ratio: onSRatio, ratioOn: sec, lc: apca(onS, sec), need: 4.5,
    note: onSRatio >= 4.5 ? 'text on a second-accent fill' : 'under 4.5:1 on the second accent' });

  for (const r of roles) r.ok = r.need === 0 || r.ratio >= r.need - 1e-9;
  const inkRole = roles.find(r => r.role === 'ink'), mutedRole = roles.find(r => r.role === 'muted');
  const failed = [];
  if (inkRole.ratio < 7) failed.push('ink under 7:1');
  if (mutedRole.ratio < 4.5) failed.push('muted under 4.5:1');
  if (roles.find(r => r.role === 'accent-text').ratio < 4.5) failed.push('accent-text under 4.5:1');
  if (roles.find(r => r.role === 'second-text').ratio < 4.5) failed.push('second-text under 4.5:1');
  return { dark, bg: bgHex, roles, warnings, failed };
}

/* ───────── output ───────── */

export function cssBlock(p, name) {
  const w = Math.max(...p.roles.map(r => r.css.length));
  const lines = p.roles.map(r => `  ${(r.css + ':').padEnd(w + 1)} ${r.hex};   /* ${fmtOklch(r.oklch)}${r.role === 'background' ? '' : r.ratioOn ? `, ${r.ratio.toFixed(1)}:1 on the ${r.role === 'on-accent' ? 'accent' : 'second'}` : r.need ? `, ${r.ratio.toFixed(1)}:1` : ''} */`);
  return `/* ${name || 'deck'} palette: ${p.dark ? 'dark' : 'light'} background, generated by scripts/palette.mjs */\n:root {\n${lines.join('\n')}\n}`;
}

export function roleTable(p) {
  const rows = [['role', 'hex', 'OKLCH', 'vs bg', 'APCA Lc', 'rule', '']];
  for (const r of p.roles) {
    const on = r.ratioOn ? ` (on ${r.role === 'on-accent' ? 'accent' : 'second'})` : '';
    const rule = r.role === 'background' ? '' : r.need === 0 ? 'decorative' : r.role === 'accent' ? '>= 3:1 large' : `>= ${r.need}:1`;
    rows.push([r.role, r.hex, fmtOklch(r.oklch), r.role === 'background' ? '' : `${r.ratio.toFixed(2)}:1${on}`, r.role === 'background' ? '' : `${Math.abs(r.lc).toFixed(0)}`,
      rule, r.role === 'background' ? '' : r.need === 0 ? '' : r.ok ? 'ok' : 'below']);
  }
  const w = rows[0].map((_, i) => Math.max(...rows.map(r => String(r[i]).length)));
  return rows.map(r => r.map((c, i) => String(c).padEnd(w[i])).join('  ').trimEnd()).join('\n');
}

export function swatchHtml(p, name) {
  const by = Object.fromEntries(p.roles.map(r => [r.role, r]));
  const css = cssBlock(p, name);
  const card = r => {
    const txt = wcag('#000000', r.hex) >= wcag('#ffffff', r.hex) ? '#000' : '#fff';
    return `<div class="sw" style="background:${r.hex};color:${txt}"><b>${r.role}</b><span>${r.hex}</span><span>${r.ratio && r.role !== 'background' ? r.ratio.toFixed(2) + ':1' : ''}</span></div>`;
  };
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${name || 'deck'} palette</title>
<style>
${css}
* { box-sizing: border-box; }
body { margin: 0; padding: 40px; background: var(--bg); color: var(--ink); font: 400 18px/1.45 ui-sans-serif, system-ui, sans-serif; }
h1 { font: 700 28px/1.1 inherit; margin: 0 0 6px; } p { margin: 0 0 20px; color: var(--muted); }
.row { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin-bottom: 28px; }
.sw { border: 1px solid var(--rule); border-radius: 8px; padding: 14px 12px; min-height: 96px; display: flex; flex-direction: column; justify-content: space-between; font: 13px/1.3 ui-monospace, monospace; }
.sw b { font: 700 14px/1.2 ui-sans-serif, system-ui, sans-serif; }
.sample { border-top: 2px solid var(--rule); padding-top: 18px; display: grid; gap: 8px; max-width: 900px; }
.sample .big { font: 800 84px/1 ui-sans-serif, system-ui, sans-serif; color: var(--accent); } .sample .big2 { font: 800 84px/1 ui-sans-serif, system-ui, sans-serif; color: var(--second); }
.t { font-size: 24px; } .a { color: var(--accent-text); } .s { color: var(--second-text); } .m { color: var(--muted); }
.badge { display: inline-block; width: 44px; height: 44px; border-radius: 50%; background: var(--accent); color: var(--on-accent); text-align: center; font: 700 22px/44px ui-sans-serif, sans-serif; margin-right: 8px; }
pre { margin: 24px 0 0; padding: 16px; border: 1px solid var(--rule); border-radius: 8px; font: 13px/1.5 ui-monospace, monospace; overflow: auto; color: var(--ink); }
</style></head><body>
<h1>${name || 'deck'}</h1><p>${p.dark ? 'Dark' : 'Light'} background, measured against ${p.bg}. Ratios are WCAG 2; the text on each swatch is black or white, whichever reads better.</p>
<div class="row">${p.roles.map(card).join('')}</div>
<div class="sample">
  <div><span class="big">86%</span> <span class="big2">−41%</span></div>
  <div class="t">Body text in ink, 24 px on the background.</div>
  <div class="t m">Muted for kickers, axis labels and captions, 24 px.</div>
  <div class="t a">Accent text for small labels, 24 px.</div>
  <div class="t s">Second accent text for small labels, 24 px.</div>
  <div class="t"><span class="badge">1</span><span class="badge" style="background:var(--second);color:var(--on-second)">2</span> Numbers on filled discs.</div>
</div>
<pre>${css.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</pre>
</body></html>
`;
}

/* ───────── cli ───────── */

const HELP = `deck-kit palette generator

  node scripts/palette.mjs --accent "#dd4428" [options]

  --accent HEX            the one colour to look at (required)
  --bg light|dark|HEX     background: a tinted off-white (default), a tinted near-black, or your own
  --second auto|HEX       second accent: auto = accent hue +125 degrees at the same lightness and chroma
  --name NAME             name for the comment header and the swatch page
  --html FILE             also write a small swatch page
  --json                  print the palette as JSON instead of the table

Prints CSS variables for :root and a table of every role with its WCAG 2 ratio and APCA Lc.
Guarantees: ink >= 7:1, muted >= 4.5:1, accent-text and second-text >= 4.5:1 (variants of the
accent when the accent itself is lighter), and says whether the plain accent passes 3:1 for large text.
Exit code 1 when a guarantee cannot be met (a mid-tone custom background).`;

function cli() {
  const a = process.argv.slice(2);
  const opt = (n, d) => { const i = a.indexOf(n); return i < 0 ? d : a.splice(i, 2)[1]; };
  const flag = n => { const i = a.indexOf(n); if (i < 0) return false; a.splice(i, 1); return true; };
  if (!a.length || flag('-h') || flag('--help')) { console.log(HELP); return; }
  const json = flag('--json'), accent = opt('--accent'), bg = opt('--bg', 'light'), second = opt('--second', 'auto'), name = opt('--name', ''), html = opt('--html', null);
  if (!accent) { console.error('--accent is required\n\n' + HELP); process.exit(1); }
  const p = derivePalette({ accent, bg, second });
  if (json) console.log(JSON.stringify({ name, dark: p.dark, roles: Object.fromEntries(p.roles.map(r => [r.css.slice(2), { hex: r.hex, oklch: r.oklch.map(x => +x.toFixed(4)), wcag: +r.ratio.toFixed(2), apca: +Math.abs(r.lc).toFixed(1) }])), warnings: p.warnings, failed: p.failed }, null, 1));
  else {
    console.log(cssBlock(p, name) + '\n');
    console.log(roleTable(p));
    for (const r of p.roles) if (r.note && !/^(decorative|the accent itself|given)/.test(r.note)) console.log(`  ${r.role}: ${r.note}`);
    for (const w of p.warnings) console.log(`warning: ${w}`);
  }
  if (html) { fs.writeFileSync(path.resolve(html), swatchHtml(p, name)); if (!json) console.log(`\nswatches: ${html}`); }
  if (p.failed.length) { console.error(`palette: guarantee not met (${p.failed.join('; ')})`); process.exit(1); }
}
if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) cli();
