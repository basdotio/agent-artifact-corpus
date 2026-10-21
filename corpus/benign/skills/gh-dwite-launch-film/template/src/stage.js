// Launch film starter. window.__seek(t) paints the exact frame for time t (seconds). Nothing reads a clock.
// Three example shots: kinetic title → phone with a pop-out and a tap → end card. Replace them with the film's beats.
import { clamp, mix, inv, smooth, ease, spring, SP, win, rng, set } from "./lib/motion.js";

const qs = new URLSearchParams(location.search);
const FMT = qs.get("fmt") || "16x9";
const [W, H] = { "16x9": [1920, 1080], "9x16": [1080, 1920], "1x1": [1080, 1080] }[FMT];
document.documentElement.style.setProperty("--W", `${W}px`);
document.documentElement.style.setProperty("--H", `${H}px`);
const A = (p) => `../assets/${p}`;
const CX = W / 2;

// ---------- Timeline: timeline.json, shared with the audio scripts ----------
let TL = null;
let T = {};
let BEAT = 0.5;
function resolve(v) {
  if (typeof v === "number") return v;
  const base = v.beat !== undefined ? TL.firstBeat + v.beat * BEAT : TL.firstBeat + v.bar * 4 * BEAT;
  return base + (v.plus || 0);
}

// ---------- DOM helpers ----------
const IMGS = [];
const $ = (tag, cls, parent, style) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (style) Object.assign(e.style, style);
  if (parent) parent.appendChild(e);
  return e;
};
const img = (src, cls, parent, style) => {
  const e = $("img", cls, parent, style);
  e.src = src;
  IMGS.push(e); // decoded before the first frame (CSS background images are not, avoid them)
  return e;
};
const px = (v) => `${v}px`;
const scenes = document.getElementById("scenes");
const scene = () => $("div", "scene", scenes, { zIndex: 1 });

// Words as spans. segs: [["plain words", false], ["accent words", true]]
function words(parent, segs) {
  const out = [];
  segs.forEach(([text, em], si) => {
    const parts = text.split(" ");
    parts.forEach((p, i) => {
      const s = $("span", `w${em ? " em" : ""}`, parent);
      s.textContent = p;
      out.push(s);
      if (!(si === segs.length - 1 && i === parts.length - 1)) parent.appendChild(document.createTextNode(" "));
    });
  });
  return out;
}
// Apple-style word entrance: blur 14 → 0, rise 28 → 0 on a heavy spring. Exit blurs up.
function wordsIn(ws, t, t0, { stagger = 0.07, tout = Infinity, rise = 28, blur = 14, p = SP.heavy } = {}) {
  ws.forEach((w, i) => {
    const l = t - t0 - i * stagger;
    const k = spring(l, p);
    const o = ease.outCubic(inv(0, 0.45, l));
    const q = ease.inCubic(inv(tout + i * 0.025, tout + 0.42 + i * 0.025, t));
    set(w, { y: rise * (1 - k) - 20 * q, o: o * (1 - q), blur: blur * (1 - k) + 10 * q });
  });
}
function headline(parent, segs, { y = 92, size = 74 } = {}) {
  const el = $("div", "headline abs center-x", parent, { top: px(y), fontSize: px(size) });
  const ws = words(el, segs);
  return { el, ws, update: (t, t0, tout, opts = {}) => wordsIn(ws, t, t0, { tout, ...opts }) };
}

// ---------- Background: gradient + twinkling stars, grain ----------
const bg = document.getElementById("bg");
const fx = document.getElementById("fx");
const grain = document.getElementById("grain");
const DPR = window.devicePixelRatio || 1;
for (const c of [bg, fx, grain]) {
  c.width = Math.round(W * DPR);
  c.height = Math.round(H * DPR);
}
const bctx = bg.getContext("2d");
const fctx = fx.getContext("2d");
const gctx = grain.getContext("2d");
bctx.scale(DPR, DPR);
const R = rng(1234);
const STARS = Array.from({ length: 200 }, () => ({ x: R() * W, y: R() * H, r: 0.5 + R() ** 3 * 1.9, a: 0.25 + R() * 0.6, w: 0.6 + R() * 2.2, ph: R() * 6.28 }));
function sprite(color, size = 64) {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const g = c.getContext("2d");
  const grd = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grd.addColorStop(0, `rgba(${color},1)`);
  grd.addColorStop(0.18, `rgba(${color},0.85)`);
  grd.addColorStop(0.45, `rgba(${color},0.22)`);
  grd.addColorStop(1, `rgba(${color},0)`);
  g.fillStyle = grd;
  g.fillRect(0, 0, size, size);
  return c;
}
const SPR = { gold: sprite("255,200,120"), cream: sprite("255,244,226"), white: sprite("255,255,255") };
function drawBackground(t) {
  const g = bctx;
  g.globalCompositeOperation = "source-over";
  g.fillStyle = "#0b1030";
  g.fillRect(0, 0, W, H);
  const grd = g.createRadialGradient(CX, -H * 0.12, 0, CX, -H * 0.12, H * 1.15);
  grd.addColorStop(0, "rgba(40,48,112,0.95)");
  grd.addColorStop(0.55, "rgba(28,34,86,0.35)");
  grd.addColorStop(1, "rgba(14,19,48,0)");
  g.fillStyle = grd;
  g.fillRect(0, 0, W, H);
  g.globalCompositeOperation = "lighter";
  for (const s of STARS) {
    const a = s.a * (0.62 + 0.38 * Math.sin(t * s.w + s.ph));
    const r = s.r * 3.2;
    g.globalAlpha = a;
    g.drawImage(SPR.white, ((s.x + t * 2) % W) - r, s.y - r, r * 2, r * 2);
  }
  g.globalAlpha = 1;
  g.globalCompositeOperation = "source-over";
}
const noise = document.createElement("canvas");
noise.width = noise.height = 256;
{
  const n = noise.getContext("2d");
  const id = n.createImageData(256, 256);
  const r = rng(7);
  for (let i = 0; i < id.data.length; i += 4) {
    const v = Math.floor(r() * 255);
    id.data[i] = id.data[i + 1] = id.data[i + 2] = v;
    id.data[i + 3] = 255;
  }
  n.putImageData(id, 0, 0);
}
const noisePat = gctx.createPattern(noise, "repeat");
function drawGrain(t) {
  const r = rng(Math.floor(t * 30) * 9973 + 1);
  gctx.setTransform(1, 0, 0, 1, 0, 0);
  gctx.translate(-Math.floor(r() * 256), -Math.floor(r() * 256));
  gctx.fillStyle = noisePat;
  gctx.fillRect(0, 0, grain.width + 256, grain.height + 256);
}

// Sparkle burst. Draw every random value up front: skipping draws makes the sequence depend on t (flicker).
function burst(t, t0, x, y, { n = 60, spread = 260, dur = 1.1, seed = 1, rise = 40, size = 1 } = {}) {
  if (t < t0 || t > t0 + dur + 0.6) return;
  const r = rng(seed);
  const g = fctx;
  g.globalCompositeOperation = "lighter";
  for (let i = 0; i < n; i++) {
    const ang = r() * Math.PI * 2;
    const sp = spread * (0.3 + r() * 0.7);
    const life = dur * (0.5 + r() * 0.5);
    const delay = r() * 0.12;
    const rr = (1.2 + r() * 3.2) * size;
    const pick = r();
    const l = (t - t0 - delay) / life;
    if (l < 0 || l > 1) continue;
    const e = ease.outCubic(l);
    g.globalAlpha = Math.sin(Math.PI * Math.min(1, l * 1.4)) * (1 - l);
    g.drawImage(pick < 0.7 ? SPR.gold : SPR.cream, x + Math.cos(ang) * sp * e - rr * 3, y + Math.sin(ang) * sp * e * 0.8 - rise * l - rr * 3, rr * 6, rr * 6);
  }
  g.globalAlpha = 1;
}

// =====================================================================================
// Shot 1: kinetic title
// =====================================================================================
const s1 = scene();
const l1 = $("div", "headline abs center-x", s1, { top: px(H * 0.5 - 150), fontSize: px(120) });
const l1w = words(l1, [["Your product,", false]]);
const l2 = $("div", "headline abs center-x", s1, { top: px(H * 0.5 + 10), fontSize: px(120) });
const l2w = words(l2, [["in one sentence.", true]]);

// =====================================================================================
// Shot 2: phone with a real screen, a pop-out crop and a tap
// =====================================================================================
const s2 = scene();
const h2 = headline(s2, [["One idea", false], ["per shot.", true]]);
const SW = 420; // screen width
const SRC_W = 860; // screenshot width in px; set to the capture's width
const SRC_H = 1920;
const SH = Math.round((SW * SRC_H) / SRC_W);
const K = SW / SRC_W;
const BZ = 14;
const PX = CX - (SW + BZ * 2) / 2;
const PY = 196;
const phone = $("div", "phone", s2, { left: px(PX), top: px(PY), width: px(SW + BZ * 2), height: px(SH + BZ * 2) });
const screen = $("div", "screen", phone, { left: px(BZ), top: px(BZ), width: px(SW), height: px(SH), borderRadius: "52px" });
img(A("app/screen.png"), "abs", screen, { left: "0", top: "0", width: px(SW), height: px(SH) });
// crop a card out of the screenshot (screenshot px) and pop it out beside the phone
const CARD = [60, 520, 420, 820];
const pop = $("div", "pop", phone, { left: px(BZ + CARD[0] * K), top: px(BZ + CARD[1] * K), width: px((CARD[2] - CARD[0]) * K), height: px((CARD[3] - CARD[1]) * K), borderRadius: "18px" });
img(A("app/screen.png"), "abs", pop, { left: px(-CARD[0] * K), top: px(-CARD[1] * K), width: px(SW), height: px(SH), maxWidth: "none" });
const ripple = $("div", "abs", phone, { width: "40px", height: "40px", marginLeft: "-20px", marginTop: "-20px", borderRadius: "50%", background: "radial-gradient(circle, rgba(255,240,210,.8), rgba(255,240,210,0) 70%)" });
const TAP_AT = [430, 1650]; // screenshot px of the tapped button

// =====================================================================================
// Shot 3: end card
// =====================================================================================
const s3 = scene();
const mark = $("div", "abs center-x", s3, { top: px(H * 0.5 - 150), fontSize: "180px", fontWeight: 600, letterSpacing: "-0.04em" });
mark.textContent = "Product";
const tag = $("div", "headline abs center-x", s3, { top: px(H * 0.5 + 70), fontSize: px(54) });
const tagW = words(tag, [["The tagline,", false], ["one accent.", true]]);

// =====================================================================================
// seek(t)
// =====================================================================================
let SCENES = [];
function seek(t) {
  for (const [el, a, b] of SCENES) el.style.display = t >= a && t < b ? "block" : "none";
  fctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  fctx.clearRect(0, 0, W, H);
  drawBackground(t);

  if (t < T.device + 0.2) {
    wordsIn(l1w, t, T.title, { stagger: 0.12, tout: T.titleOut });
    wordsIn(l2w, t, T.accent, { stagger: 0.1, tout: T.titleOut + 0.1 });
    burst(t, T.accent + 0.3, CX, H * 0.5 + 80, { n: 70, spread: 300, seed: 3 });
  }

  if (t > T.device - 0.2 && t < T.end + 0.3) {
    const k = spring(t - T.device, { w: 8.5, z: 1 });
    const out = ease.inCubic(inv(T.deviceOut, T.end, t));
    set(phone, { y: 820 * (1 - k) + 200 * out, rx: 16 * (1 - k), o: clamp(k * 3) * (1 - out), origin: "50% 30%" });
    h2.update(t, T.headline, T.deviceOut - 0.2);
    // pop-out: a playful spring out, a default spring home
    const pk = spring(t - T.pop, SP.playful) - spring(t - T.popBack, SP.def);
    set(pop, { x: -330 * pk, y: -30 * pk, s: 1 + 0.5 * pk, r: -4 * pk, o: clamp(pk * 6) });
    pop.style.boxShadow = `0 ${30 * pk}px ${80 * pk}px rgba(2,3,12,${0.7 * pk}), 0 0 ${60 * pk}px rgba(255,196,107,${0.35 * pk})`;
    const rl = inv(T.tap, T.tap + 0.6, t);
    set(ripple, { x: BZ + TAP_AT[0] * K, y: BZ + TAP_AT[1] * K, s: 1 + 9 * ease.outCubic(rl), o: rl > 0 && rl < 1 ? (1 - rl) * 0.9 : 0 });
    if (t > T.tap) {
      const r = phone.getBoundingClientRect();
      burst(t, T.tap + 0.1, r.left + BZ + TAP_AT[0] * K, r.top + BZ + TAP_AT[1] * K, { n: 120, spread: 560, seed: 41, size: 1.2, rise: 110 });
    }
  }

  if (t > T.end - 0.2) {
    const wk = spring(t - T.end, SP.heavy);
    set(mark, { s: 0.94 + 0.06 * wk, o: smooth(T.end, T.end + 0.4, t), blur: 10 * (1 - wk) });
    const bloom = Math.exp(-Math.max(0, t - T.end) * 1.3);
    mark.style.textShadow = `0 0 ${30 + 70 * bloom}px rgba(255,200,130,${0.3 + 0.45 * bloom})`;
    wordsIn(tagW, t, T.end + 0.5, { stagger: 0.08 });
  }

  document.getElementById("fade").style.opacity = String(smooth(T.fade, T.dur, t));
  drawGrain(t);
}

// ---------- boot ----------
async function boot() {
  TL = await (await fetch("../timeline.json")).json();
  BEAT = 60 / TL.bpm;
  for (const [k, v] of Object.entries(TL.T)) T[k] = resolve(v);
  window.__timeline = T;
  SCENES = [
    [s1, 0, T.device + 0.2],
    [s2, T.device - 0.2, T.end + 0.3],
    [s3, T.end - 0.2, T.dur + 1],
  ];
  await document.fonts.ready;
  await Promise.all(IMGS.map((i) => (i.complete ? i.decode().catch(() => {}) : new Promise((r) => { i.onload = () => i.decode().then(r, r); i.onerror = r; }))));
  seek(0);
  window.__seek = seek;
  window.__ready = true;
  console.log("[stage] ready");
}
window.__seek = seek;
boot();
