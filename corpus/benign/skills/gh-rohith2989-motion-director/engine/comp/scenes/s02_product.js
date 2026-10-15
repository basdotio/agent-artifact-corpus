// s02 · Product (3.6–8.6). A panel slides over the title; on it, a browser with the product. The camera leans
// into the chart as it grows (values counting up), the cursor types a plain question, Ask is pressed, the
// answer lands and its key phrase is underlined. At 8.0 the camera dives into the hero bar (s03 takes over).
import { scene, cue, W, H } from "../core/runtime.js";
import { h, css, clamp, lerp } from "../core/anim.js";
import { expoOut, heavyInOut, inOutSoft } from "../core/ease.js";
import { camAt, camTf, camSpeed, samplesFor, toScreen } from "../sys/cam.js";
import { createCursor } from "../sys/cursor.js";
import { offsetIn } from "../sys/rig.js";
import { stage, slideIn, panelTf } from "../sys/stage.js";
import { browserWindow } from "../sys/window.js";
import { barChart } from "../sys/chart.js";
import { fmt, pressScale, countUp } from "../sys/ui.js";
import { schedule, typedAt, keyCues, caretOn } from "../sys/type.js";
import { withHighlight, setHighlight } from "../sys/highlight.js";

export const T2 = { in: 3.6, bars: 4.55, cur: 4.95, clickIn: 5.45, type0: 5.55, type1: 6.45, ask: 6.7, answer: 6.85, hl0: 7.3, hl1: 7.95, dive: 8.0 };
const Q = "Why did March spike?";
const VALUES = [118, 124, 131, 127, 136, 188];
const LABELS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar"];

const CSS = `
.lm { position:absolute; inset:0; display:flex; font-family:var(--sans); color:var(--ink); background:#fbfbfd; }
.lm-side { width:232px; flex:none; background:linear-gradient(180deg,#f4f3fa,#eeedf7); border-right:1px solid var(--line); padding:22px 16px; }
.lm-brand { display:flex; align-items:center; gap:10px; font:600 19px/1 var(--disp); letter-spacing:-.02em; margin-bottom:28px; padding-left:6px; }
.lm-nav { display:flex; align-items:center; gap:10px; height:36px; padding:0 12px; border-radius:10px; font:500 14px/1 var(--sans); color:var(--ink-soft); }
.lm-nav i { width:7px; height:7px; border-radius:50%; background:var(--line); }
.lm-nav.on { background:#fff; color:var(--ink); box-shadow:var(--sh-card); font-weight:600; }
.lm-nav.on i { background:var(--accent); }
.lm-main { flex:1; padding:34px 40px; display:grid; grid-template-columns: 1fr 392px; gap:28px; align-content:start; }
.lm-h1 { font:600 30px/1.1 var(--disp); letter-spacing:-.02em; }
.lm-sub { margin-top:6px; font:400 14px/1.4 var(--sans); color:var(--ink-soft); }
.lm-card { background:#fff; border:1px solid var(--line); border-radius:var(--r-card); box-shadow:var(--sh-card); padding:24px 26px; }
.lm-k { font:500 13px/1 var(--sans); color:var(--ink-muted); text-transform:uppercase; letter-spacing:.08em; }
.lm-big { margin-top:10px; font:600 40px/1 var(--disp); letter-spacing:-.02em; font-variant-numeric:tabular-nums; }
.lm-chip { display:inline-flex; align-items:center; gap:6px; margin-left:12px; height:26px; padding:0 10px; border-radius:999px; background:#ecfdf5; color:#047857; font:600 13px/1 var(--sans); vertical-align:6px; }
.lm-ask { display:flex; flex-direction:column; gap:14px; }
.lm-in { display:flex; align-items:center; gap:10px; height:48px; padding:0 8px 0 16px; border-radius:12px; border:1px solid var(--line); background:#fff; font:400 15px/1 var(--sans); color:var(--ink); }
.lm-in.focus { border-color:var(--accent); box-shadow:0 0 0 3px color-mix(in srgb, var(--accent-2) 45%, transparent); }
.lm-in .ph { color:var(--ink-muted); }
.lm-in .caret { display:inline-block; width:1.5px; height:18px; background:var(--ink); vertical-align:-3px; margin-left:1px; }
.lm-btn { margin-left:auto; height:34px; padding:0 14px; border-radius:9px; background:linear-gradient(180deg, color-mix(in srgb, var(--accent) 80%, white), var(--accent)); color:#fff; font:600 14px/34px var(--sans); box-shadow:0 1px 2px rgb(30 20 90/.25), inset 0 1px 0 rgb(255 255 255/.25); transform-origin:50% 50%; }
.lm-ans { border-radius:14px; background:color-mix(in srgb, var(--accent-2) 14%, white); border:1px solid color-mix(in srgb, var(--accent-2) 45%, white); padding:16px 18px; font:400 15.5px/1.55 var(--sans); color:var(--ink-soft); }
.lm-ans b { color:var(--ink); font-weight:600; }
.lm-who { display:flex; align-items:center; gap:8px; margin-bottom:8px; font:600 13px/1 var(--sans); color:var(--accent); }
.lm-src { margin-top:10px; font:500 12.5px/1 var(--mono); color:var(--ink-muted); }
`;

/** The Lumen mark: a rounded tile with a beam of light — simple, geometric, owned. Every instance gets its own
 *  gradient id: a url(#id) that points into a hidden scene's SVG renders nothing. */
let markN = 0;
export function lumenMark(size = 28) {
  const id = `lmg${markN++}`;
  return h("svg", { viewBox: "0 0 40 40", width: size, height: size, style: { display: "block", flex: "none" }, html:
    `<defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7c74f2"/><stop offset="1" stop-color="#4338ca"/></linearGradient></defs>` +
    `<rect x="1" y="1" width="38" height="38" rx="11" fill="url(#${id})"/><path d="M13 10v20h15" fill="none" stroke="#fff" stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round"/>` +
    '<circle cx="28" cy="13" r="3.4" fill="#c7d2fe"/>' });
}

export const CAM = [];
let barRect = null;
/** Where the hero (March) bar is on screen at t — s03 opens its circle wipe from here. */
export const heroBarScreen = (t) => {
  const c = camAt(t, CAM);
  const [x, y] = toScreen(c, barRect.cx, barRect.y + barRect.h * 0.3);
  return { x, y, z: c.z };
};

scene({
  id: "s02",
  start: T2.in,
  end: 8.85, // stays under s03's circle until the wipe has filled the frame
  z: 20,
  samples(lt, t, s) {
    let n = samplesFor(camSpeed(t, CAM));
    n = Math.max(n, samplesFor(s.cur.speed(t) * camAt(t, CAM).z * 0.8));
    if (t < T2.in + 1.0) n = Math.max(n, 10);
    return n;
  },
  build(root, s) {
    document.head.appendChild(h("style", { html: CSS }));
    s.panel = h("div", { class: "fill", style: { overflow: "hidden", transformOrigin: "50% 50%" } });
    s.bg = stage("soft");
    s.world = h("div", { style: { position: "absolute", left: "0", top: "0", width: `${W}px`, height: `${H}px`, transformOrigin: "0 0" } });
    s.screen = h("div", { class: "fill", style: { zIndex: "5", pointerEvents: "none" } });
    s.panel.append(s.bg.el, s.world, s.screen);
    root.appendChild(s.panel);

    const B = (s.win = browserWindow({ x: 200, y: 112, w: 1520, h: 860, url: "app.lumen.example/revenue" }));
    s.world.appendChild(B.el);
    const nav = ["Overview", "Revenue", "Customers", "Reports", "Settings"].map((n) => h("div", { class: `lm-nav${n === "Revenue" ? " on" : ""}` }, h("i"), h("span", { text: n })));
    const side = h("div", { class: "lm-side" }, h("div", { class: "lm-brand" }, lumenMark(28), h("span", { text: "Lumen" })), ...nav);
    s.big = h("span", { class: "tab", text: "$0" });
    const chip = h("span", { class: "lm-chip", text: "▲ 38% in March" });
    s.chart = barChart({ values: VALUES, labels: LABELS, width: 760, height: 300, highlight: 5, format: (v) => `$${Math.round(v)}k` });
    const chartCard = h("div", { class: "lm-card" }, h("div", { class: "lm-k", text: "Monthly revenue" }), h("div", { class: "lm-big" }, s.big, chip), h("div", { style: { marginTop: "26px" } }, s.chart.el));
    s.caret = h("span", { class: "caret" });
    s.typed = h("span", {});
    s.ph = h("span", { class: "ph", text: "Ask about your numbers…" });
    s.askBtn = h("div", { class: "lm-btn", text: "Ask" });
    s.input = h("div", { class: "lm-in" }, h("span", {}, s.typed, s.caret, s.ph), s.askBtn);
    s.hl = withHighlight("March revenue rose 38%, driven by a new enterprise plan (14 accounts) and a seasonal reorder from two distributors.", "a new enterprise plan");
    s.ans = h("div", { class: "lm-ans" }, h("div", { class: "lm-who" }, lumenMark(18), h("span", { text: "Lumen" })), h("div", {}, ...s.hl.nodes), h("div", { class: "lm-src", text: "Sources: billing · 1,284 invoices · Mar 1–31" }));
    const askCard = h("div", { class: "lm-card lm-ask" }, h("div", { class: "lm-k", text: "Ask Lumen" }), s.input, s.ans);
    const head = h("div", { style: { gridColumn: "1 / span 2" } }, h("div", { class: "lm-h1", text: "Revenue" }), h("div", { class: "lm-sub", text: "Last 6 months · all regions · live from billing" }));
    const main = h("div", { class: "lm-main" }, head, chartCard, askCard);
    B.body.appendChild(h("div", { class: "lm" }, side, main));

    // measure (world coords) while laid out
    const P = (el) => offsetIn(el, s.world);
    const rChart = P(chartCard), rIn = P(s.input), rBtn = P(s.askBtn), rAns = P(s.ans);
    const cols = s.chart.el.querySelectorAll(".ch-bar");
    barRect = P(cols[cols.length - 1]);
    s.ansH = s.ans.offsetHeight;

    // camera: settle wide, lean into the chart, then the question, then the answer, then dive into March
    CAM.push([T2.in, { x: 960, y: 540, z: 1 }]);
    CAM.push([T2.bars - 0.1, { x: 960, y: 540, z: 1 }]);
    CAM.push([T2.bars + 0.45, { x: rChart.cx + 40, y: rChart.cy + 10, z: 1.32 }]);
    CAM.push([T2.clickIn - 0.05, { x: rIn.cx - 60, y: rIn.cy + 120, z: 1.55 }]);
    CAM.push([T2.answer + 0.4, { x: rAns.cx - 80, y: rAns.cy - 20, z: 1.6 }]);
    CAM.push([T2.dive - 0.02, { x: rAns.cx - 90, y: rAns.cy - 14, z: 1.62 }]);
    CAM.push([T2.dive + 0.62, { x: barRect.cx, y: barRect.y + barRect.h * 0.3, z: 7.5 }, heavyInOut]);

    // cursor (screen space, constant size), clicks with rings
    s.cur = createCursor(s.screen, { scale: 1.5 });
    s.cur.show(T2.cur, T2.dive);
    s.cur.at(T2.cur, rIn.x + rIn.w + 120, rIn.cy + 160);
    s.cur.to(T2.cur + 0.05, T2.clickIn - 0.03, rIn.x + 150, rIn.cy + 3);
    s.cur.click(T2.clickIn);
    s.cur.to(T2.clickIn + 0.12, T2.type1 - 0.1, rBtn.cx + 2, rBtn.cy + 4, { arc: 0.03 });
    s.cur.click(T2.ask);
    s.cur.to(T2.ask + 0.15, T2.ask + 0.7, rBtn.cx + 70, rBtn.cy + 80, { arc: 0.05 });
    s.rings = [{ t: T2.clickIn, x: rIn.x + 150, y: rIn.cy + 3 }, { t: T2.ask, x: rBtn.cx + 2, y: rBtn.cy + 4 }];
    s.ringEls = s.rings.map(() => {
      const el = h("div", { class: "ring" }, h("i"));
      s.screen.appendChild(el);
      return el;
    });

    s.sch = schedule(Q, T2.type0, { cps: 18, seed: 5, until: T2.type1 });
    keyCues(s.sch, { pan: 0.1 });
    cue(T2.in, "panel");
    VALUES.forEach((v, i) => cue(T2.bars + i * 0.08 + 0.05, "relay", { i }));
    cue(T2.clickIn, "click");
    cue(T2.ask, "click");
    cue(T2.answer + 0.05, "open");
    cue(T2.hl0, "tick");
    cue(T2.dive + 0.02, "glide", { dur: 0.62, f0: 520, f1: 140 });
  },
  update(lt, t, s) {
    panelTf(s.panel, slideIn(t, T2.in, 1.0));
    s.bg.update(t);
    const c = camAt(t, CAM);
    css(s.world, { transform: camTf(c) });
    s.chart.set(t, T2.bars, 0.08, 0.9);
    countUp(s.big, t, T2.bars, 1.3, 0, 1.28, (v) => `$${v.toFixed(2)}M`);
    const typing = t >= T2.clickIn && t < T2.ask + 0.1;
    const txt = typedAt(s.sch, t);
    if (s.typed.textContent !== txt) s.typed.textContent = txt;
    css(s.ph, { display: txt ? "none" : "inline" });
    css(s.caret, { display: typing && caretOn(s.sch, t, T2.clickIn) ? "inline-block" : "none" });
    s.input.classList.toggle("focus", typing);
    css(s.askBtn, { transform: `scale(${pressScale(t, T2.ask, 0.06).toFixed(4)})` });
    // the answer grows into place
    const g = expoOut(clamp((t - T2.answer) / 0.55));
    css(s.ans, { opacity: clamp((t - T2.answer - 0.05) / 0.3).toFixed(3), maxHeight: t < T2.answer ? "0px" : g >= 0.999 ? "none" : `${(s.ansH * g).toFixed(1)}px`, overflow: "hidden", padding: t < T2.answer ? "0 18px" : "" });
    setHighlight(s.hl.hl, inOutSoft(clamp((t - T2.hl0) / (T2.hl1 - T2.hl0))));
    const map = (x, y) => {
      const [sx, sy] = toScreen(c, x, y);
      return { x: sx, y: sy };
    };
    s.cur.update(t, map);
    s.rings.forEach((r, i) => {
      const u = clamp((t - r.t) / 0.6);
      const on = t >= r.t && u < 1;
      const p = map(r.x, r.y);
      const rad = lerp(8, 34, expoOut(u));
      css(s.ringEls[i], { display: on ? "block" : "none", transform: `translate(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px)`, opacity: (1 - u).toFixed(3) });
      css(s.ringEls[i].firstChild, { left: `${-rad}px`, top: `${-rad}px`, width: `${rad * 2}px`, height: `${rad * 2}px` });
    });
  },
});
