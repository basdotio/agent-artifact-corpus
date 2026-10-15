/*
 * motion-video-skill engine.
 *
 * A deterministic renderer: render(t) draws the exact frame at time t, so the
 * browser preview and the captured MP4 always match. The video is a list of
 * scenes described in story.json; the timeline, word sync, sound cues and the
 * music plan are all derived from it.
 *
 * Inputs (written by make.mjs into build/): window.STORY, window.VOICES,
 * window.MEDIA. Outputs for the pipeline: window.seek(t), window.cues,
 * window.meta, window.warnings, window.ready.
 */
(() => {
  "use strict";

  /* ---------------------------------------------------------------- setup */
  const S = window.STORY;
  const VO = window.VOICES || {};
  const MEDIA = window.MEDIA || {};
  // Notes: things the engine fixed by itself. Problems: things that block the render until fixed.
  const warnings = [], problems = [];
  const warn = (m) => { if (!warnings.includes(m)) warnings.push(m); };
  const problem = (m) => { if (!problems.includes(m)) problems.push(m); };

  const W = S.format?.width ?? 1080;
  const H = S.format?.height ?? 1920;
  const U = Math.min(W, H) / 1080; // one design unit
  const PORTRAIT = H > W;
  const style = S.style ?? {};
  const hex6 = (h) => (typeof h === "string" && /^#[0-9a-f]{3}$/i.test(h) ? "#" + [...h.slice(1)].map((c) => c + c).join("") : h);
  const PAPER = hex6(style.paper ?? "#f4f3ef");
  const INK = hex6(style.ink ?? "#1c1c1b");
  const PALETTE = {
    blue: "#5B8DEF", violet: "#7A5CD0", green: "#43B17A", amber: "#D9A441",
    rose: "#E4718A", teal: "#3FB3B0", copper: "#C4713D", slate: "#7C8798",
    ...(style.palette ?? {}),
  };
  const col = (c, fallback = style.accent ?? "violet") => hex6(PALETTE[c] ?? (typeof c === "string" && c.startsWith("#") ? c : PALETTE[fallback] ?? fallback));
  const ACCENT = col(style.accent ?? "violet");
  const FONT = `"${style.font ?? "Geist"}", system-ui, sans-serif`;
  const STYLE_BPM = { playful: 100, lofi: 80, upbeat: 118, cinematic: 90, chiptune: 128, tropical: 102, corporate: 110, ambient: 72 };
  const BEAT = 60 / (S.music?.bpm ?? STYLE_BPM[S.music?.style] ?? 100);
  const labels = { now: "now", number: "No.", prompt: "PROMPT", assistant: "AI assistant", quiz: "Quiz", myth: "Myth", fact: "Fact", ...(S.labels ?? {}) };

  /* ---------------------------------------------------------------- maths */
  const TAU = Math.PI * 2;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const prog = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, p) => a + (b - a) * p;
  const outCubic = (p) => 1 - Math.pow(1 - p, 3);
  const inCubic = (p) => p * p * p;
  const inQuad = (p) => p * p;
  const inOutCubic = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  const outBack = (p, s = 1.70158) => 1 + (s + 1) * Math.pow(p - 1, 3) + s * Math.pow(p - 1, 2);
  const inBack = (p, s = 1.70158) => (s + 1) * p * p * p - s * p * p;
  const outElastic = (p) => (p <= 0 ? 0 : p >= 1 ? 1 : Math.pow(2, -10 * p) * Math.sin((p * 10 - 0.75) * (TAU / 3)) + 1);
  /** Squash-and-stretch after an impact: returns the x stretch, y is its mirror. */
  const wobble = (u, amp = 0.24, freq = 30, decay = 8) => (u < 0 ? 0 : amp * Math.exp(-u * decay) * Math.cos(u * freq));
  const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  const rgb = (h) => [1, 3, 5].map((o) => parseInt(h.slice(o, o + 2), 16));
  const mix = (a, b, p) => { const A = rgb(a), B = rgb(b); return "#" + A.map((v, i) => Math.round(lerp(v, B[i], clamp(p))).toString(16).padStart(2, "0")).join(""); };
  const tint = (c) => mix(col(c), PAPER, 0.72);
  const snapUp = (x) => Math.ceil(x / BEAT - 1e-6) * BEAT;
  const f1 = (v) => v.toFixed(1);

  /* ---------------------------------------------------------------- readability */
  // Every piece of text must reach this contrast with what it sits on (WCAG AA).
  const MIN_CONTRAST = 4.5;
  // Smallest text anything draws, and the smallest a title line may shrink to, in pixels at 1080 wide.
  const MIN_TEXT = 40, MIN_TITLE = 72;
  const relLum = (h) => {
    const [r, g, b] = rgb(h).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const contrast = (a, b) => { const la = relLum(a), lb = relLum(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
  /** A text colour that reads on `bg`: itself, or darkened (lightened on a dark background) until it does. */
  function readable(fg, bg, what) {
    fg = hex6(fg); bg = hex6(bg);
    if (contrast(fg, bg) >= MIN_CONTRAST) return fg;
    const toward = relLum(bg) > 0.18 ? "#000000" : "#ffffff";
    let c = fg;
    for (let i = 1; i <= 20 && contrast(c, bg) < MIN_CONTRAST; i++) c = mix(fg, toward, i * 0.05);
    if (what) warn(`${what}: ${fg} on ${bg} is only ${contrast(fg, bg).toFixed(1)}:1, drawn as ${c} so it reads. Choose a darker colour.`);
    return c;
  }
  /** Colours for a filled shape with text on it: white or ink text, or a darker fill when neither reads. */
  function onFill(fill, what) {
    fill = hex6(fill);
    if (contrast("#ffffff", fill) >= MIN_CONTRAST) return { fill, text: "#ffffff" };
    if (contrast(INK, fill) >= MIN_CONTRAST) return { fill, text: INK };
    let f = fill;
    for (let i = 1; i <= 20 && contrast("#ffffff", f) < MIN_CONTRAST; i++) f = mix(fill, "#000000", i * 0.05);
    if (what) warn(`${what}: no text colour reads on ${fill}; filled with ${f} instead.`);
    return { fill: f, text: "#ffffff" };
  }
  if (contrast(INK, PAPER) < 7) problem(`style: ink ${INK} on paper ${PAPER} is only ${contrast(INK, PAPER).toFixed(1)}:1; body text needs 7:1. Use a darker ink or a lighter paper.`);
  /** How to show coloured words: in the colour when it reads on the background, else as a highlighter band with readable text on it. */
  function colouredText(c, bg) {
    c = hex6(c);
    if (contrast(c, bg) >= MIN_CONTRAST) return { text: c, marker: null };
    const o = onFill(c);
    return { text: o.text, marker: o.fill };
  }
  function marker(x0, width, base, size, fill, p, rot = -1.5) {
    if (p <= 0.001) return "";
    const pad = size * 0.16, h = size * 1.08, w = (width + pad * 2) * clamp(p);
    return `<rect x="${f1(x0 - pad)}" y="${f1(base - size * 0.84)}" width="${f1(w)}" height="${f1(h)}" rx="${f1(size * 0.2)}" fill="${fill}" transform="rotate(${rot} ${f1(x0)} ${f1(base)})"/>`;
  }
  /** The background of the scene on screen; set by render(). */
  let BG = PAPER;
  /** Warns when text lands where TikTok, Reels and Shorts draw their own buttons and captions. */
  function safe(sc, top, bottom, what) {
    if (!PORTRAIT) return;
    if (top < H * 0.065 || bottom > H * 0.86) problem(`scene ${sc.key}: ${what} reaches into the top 6.5% or bottom 14% of the frame, where the platform's buttons and caption sit.`);
  }

  /* ---------------------------------------------------------------- text */
  const mctx = document.createElement("canvas").getContext("2d");
  const measure = (str, weight, size) => { mctx.font = `${weight} ${size}px ${FONT}`; return mctx.measureText(str).width; };
  function layout(str, weight, size, track = 0) {
    const letters = [];
    for (let i = 0; i < str.length; i++) {
      const w = measure(str[i], weight, size);
      letters.push({ ch: str[i], x: measure(str.slice(0, i), weight, size) + track * size * i + w / 2 });
    }
    return { letters, width: measure(str, weight, size) + track * size * (str.length - 1), size, weight };
  }
  /** Largest size up to `max` at which the text fits `room` pixels on one line. */
  function fit(str, weight, max, room, track = -0.02, minSize = MIN_TEXT * U, what = null) {
    const size = Math.min(max, (max * room) / (measure(str, weight, max) + track * max * Math.max(0, str.length - 1)));
    if (what && size < minSize) problem(`${what}: "${str}" only fits at ${Math.round(size / U)}px; split it into two lines or shorten it.`);
    return layout(str, weight, size, track);
  }
  /** Words on up to `maxLines` lines at the largest size (≤ max, ≥ min) that fits `room`. */
  function wrap(str, weight, max, min, room, maxLines, what) {
    const words = String(str).split(/\s+/).filter(Boolean);
    const linesAt = (size) => {
      const lines = []; let cur = "";
      for (const w of words) { const t2 = cur ? cur + " " + w : w; if (!cur || measure(t2, weight, size) <= room) cur = t2; else { lines.push(cur); cur = w; } }
      if (cur) lines.push(cur);
      return lines;
    };
    for (let size = max; size >= min - 0.01; size = Math.max(min, size * 0.94)) {
      const lines = linesAt(size);
      if (lines.length <= maxLines && lines.every((l) => measure(l, weight, size) <= room)) return { size, lines };
      if (size === min) break;
    }
    const lines = linesAt(min);
    if (what) problem(`${what}: "${String(str).slice(0, 48)}…" needs ${lines.length} lines at the smallest readable size (max ${maxLines}); shorten it.`);
    return { size: min, lines };
  }
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  function letter(ch, x, y, size, weight, fill, { dy = 0, rot = 0, sx = 1, sy = 1, op = 1, stroke = null } = {}) {
    if (op <= 0.001 || ch === " ") return "";
    const st = stroke ? ` stroke="${stroke}" stroke-width="${f1(size * 0.12)}" stroke-linejoin="round" paint-order="stroke"` : "";
    return `<g transform="translate(${f1(x)} ${f1(y + dy)}) rotate(${rot.toFixed(2)}) scale(${sx.toFixed(3)} ${sy.toFixed(3)})" opacity="${op.toFixed(3)}"><text text-anchor="middle" font-family='${FONT}' font-weight="${weight}" font-size="${size.toFixed(1)}" fill="${fill}"${st}>${esc(ch)}</text></g>`;
  }
  /** One line whose letters pop in one by one from `t0`; `out` (0..1) throws them away. */
  function popLine(t, L, cx, base, fill, t0, { step = 0.03, dur = 0.34, from = 90, out = 0, spin = 30, seed = 0, stroke = null } = {}) {
    const x0 = cx - L.width / 2;
    let s = "";
    L.letters.forEach((l, j) => {
      const p = prog(t, t0 + j * step, t0 + j * step + dur);
      const b = outBack(p, 2.6);
      s += letter(l.ch, x0 + l.x, base, L.size, L.weight, fill, {
        dy: (1 - b) * from * U + out * 900 * U, sx: b, sy: b, stroke,
        rot: (1 - p) * (hash(j + seed) - 0.5) * spin + out * (hash(j + seed + 9) - 0.5) * 120,
        op: clamp(p * 3) * (1 - out),
      });
    });
    return s;
  }
  function pill(text, x, y, { size = 40, weight = 800, fill = INK, color = null, rot = 0, scale = 1, stroke = null, padX = 1.4, what = null } = {}) {
    if (scale <= 0.001) return "";
    if (!color) { const o = onFill(fill, what); fill = o.fill; color = o.text; }
    const w = measure(text, weight, size) + size * padX, h = size * 1.6;
    const st = stroke ? ` stroke="${stroke}" stroke-width="${f1(size * 0.18)}"` : "";
    return `<g transform="translate(${f1(x)} ${f1(y)}) rotate(${rot.toFixed(2)}) scale(${scale.toFixed(3)})">`
      + `<rect x="${f1(-w / 2)}" y="${f1(-h / 2 + size * 0.2)}" width="${f1(w)}" height="${f1(h)}" rx="${f1(h / 2)}" fill="${INK}" opacity=".14"/>`
      + `<rect x="${f1(-w / 2)}" y="${f1(-h / 2)}" width="${f1(w)}" height="${f1(h)}" rx="${f1(h / 2)}" fill="${fill}"${st}/>`
      + `<text text-anchor="middle" y="${f1(size * 0.35)}" font-family='${FONT}' font-weight="${weight}" font-size="${f1(size)}" fill="${color}">${esc(text)}</text></g>`;
  }

  /* ---------------------------------------------------------------- confetti */
  function burst(t, t0, cx, cy, seed, palette, count = 14, reach = 260, r0 = 0) {
    const u = t - t0;
    if (u < 0 || u > 0.9) return "";
    let s = "";
    for (let i = 0; i < count; i++) {
      const a = (i / count) * TAU + hash(seed + i) * 0.6;
      const d = r0 + reach * U * (0.6 + hash(seed + i + 50) * 0.6) * outCubic(clamp(u / 0.7));
      const px = cx + Math.cos(a) * d, py = cy + Math.sin(a) * d + 300 * U * u * u;
      const r = (9 + hash(seed + i + 90) * 13) * U * (1 - prog(u, 0.45, 0.9));
      const c = palette[i % palette.length];
      if (r <= 0.3) continue;
      if (i % 3 === 0) s += `<rect x="${f1(px - r * 1.4)}" y="${f1(py - r * 0.5)}" width="${f1(r * 2.8)}" height="${f1(r)}" rx="${f1(r / 2)}" fill="${c}" transform="rotate(${f1(a * 57 + u * 400)} ${f1(px)} ${f1(py)})"/>`;
      else if (i % 5 === 1) s += `<path d="M${f1(px)} ${f1(py - r * 1.3)} L${f1(px + r * 0.4)} ${f1(py - r * 0.4)} L${f1(px + r * 1.3)} ${f1(py)} L${f1(px + r * 0.4)} ${f1(py + r * 0.4)} L${f1(px)} ${f1(py + r * 1.3)} L${f1(px - r * 0.4)} ${f1(py + r * 0.4)} L${f1(px - r * 1.3)} ${f1(py)} L${f1(px - r * 0.4)} ${f1(py - r * 0.4)}Z" fill="${c}"/>`;
      else s += `<circle cx="${f1(px)}" cy="${f1(py)}" r="${f1(r)}" fill="${c}"/>`;
    }
    return s;
  }
  const CONFETTI = Object.values(PALETTE);

  /* ---------------------------------------------------------------- media */
  const mediaInfo = (id, variant) => MEDIA[id]?.[variant] ?? MEDIA[id]?.full ?? MEDIA[id]?.avatar ?? null;
  function frameUrl(id, variant, t) {
    const m = mediaInfo(id, variant);
    if (!m) { problem(`media "${id}" is not declared in story.media`); return null; }
    const n = m.count > 1 ? ((Math.floor(t * m.fps) % m.count) + m.count) % m.count : 0;
    return `${m.dir}/${String(n + 1).padStart(4, "0")}.${m.ext ?? "jpg"}`;
  }

  /* ---------------------------------------------------------------- timeline */
  const DEFAULT_LEN = { pileup: 3, title: 2.4, fan: 3, card: 2.4, chat: 4.2, cards: 4.2, stats: 3.6, checklist: 4.2, compare: 4.2, prompt: 4.2, quote: 4.2, timeline: 4.8, chart: 4.2, quiz: 5.4, ranking: 4.8, flip: 4.2, definition: 4.2, profile: 4.2, list: 3.6, grid: 4.2, logo: 3.6 };
  const DEFAULT_VOICE_AT = { card: 0.45, logo: 0.75 };
  const scenes = S.scenes.map((raw, index) => ({ ...raw, index, key: raw.id ?? `s${index + 1}` }));
  let cursor = 0;
  for (const sc of scenes) {
    if (!DEFAULT_LEN[sc.type]) problem(`scene ${sc.key}: unknown type "${sc.type}"`);
    sc.v = sc.voice ? VO[sc.key] : null;
    if (sc.voice && !sc.v) warn(`scene ${sc.key}: voice not generated yet (run the voices step)`);
    sc.voiceAt = sc.voice?.at ?? DEFAULT_VOICE_AT[sc.type] ?? 0.35;
    sc.speech = sc.v ? sc.v.speechEnd - sc.v.speechStart : 0;
    const needed = sc.v ? sc.voiceAt + sc.speech + (sc.pad ?? 0.55) + (sc.type === "logo" ? 1.0 : 0) : 0;
    sc.len = snapUp(Math.max(sc.duration ?? DEFAULT_LEN[sc.type] ?? 2.4, needed));
    sc.start = cursor;
    sc.end = cursor + sc.len;
    cursor = sc.end;
  }
  const DURATION = cursor;
  scenes.forEach((sc, i) => { sc.prev = scenes[i - 1] ?? null; sc.next = scenes[i + 1] ?? null; });

  const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\p{L}\p{N}']/gu, "");
  /**
   * Absolute time of a moment inside a scene. `at` may be seconds from the
   * scene start, or a spoken word: "word", "word#2" (second match),
   * "word:end" (when it finishes). Words match by prefix, ignoring case and accents.
   */
  function when(sc, at, fallback = 0) {
    if (at == null) return sc.start + fallback;
    if (typeof at === "number") return sc.start + at;
    let [w, edge] = String(at).split(":");
    let n = 1;
    if (w.includes("#")) { n = Number(w.split("#")[1]) || 1; w = w.split("#")[0]; }
    if (!sc.v) return sc.start + fallback;
    const hits = sc.v.words.filter((x) => norm(x.w).startsWith(norm(w)));
    const hit = hits[n - 1];
    if (!hit) { problem(`scene ${sc.key}: word "${at}" not found in the voice line`); return sc.start + fallback; }
    return sc.start + sc.voiceAt + (edge === "end" ? hit.end : hit.start) - sc.v.speechStart;
  }
  /** The first scene shows at frame 0 what would appear in its first 0.8 s: frame 0 is the thumbnail. */
  const early = (sc, t0) => (sc.index === 0 && t0 - sc.start < 0.8 ? sc.start - 1.0 : t0);
  const speaking = (sc, t) => sc.v && t >= sc.start + sc.voiceAt && t <= sc.start + sc.voiceAt + sc.speech;

  /* ---------------------------------------------------------------- layout helpers */
  const CX = W / 2;
  /** Where a card scene's media card sits: smaller and higher when a prompt panel goes under it. */
  function cardBox(sc) {
    const withPrompt = sc?.type === "card" && Boolean(sc.prompt);
    const h = PORTRAIT ? H * (withPrompt ? 0.35 : 0.56) : H * 0.62;
    const y = PORTRAIT ? H * (withPrompt ? 0.36 : 0.43) : H * 0.47;
    const x = !PORTRAIT && withPrompt ? W * 0.28 : CX;
    return { x, y, w: h * 0.613, h };
  }
  const TEXT_ROOM = W * 0.89;

  /** Cards in a row share progress dots; returns [index, count] within the run. */
  function cardRun(sc) {
    let a = sc.index, b = sc.index;
    while (scenes[a - 1]?.type === "card") a--;
    while (scenes[b + 1]?.type === "card") b++;
    return [sc.index - a, b - a + 1, a];
  }

  /** Grid seats for a grid scene, so other scenes can fly into or out of them. */
  function gridSeats(sc) {
    const n = sc.members.length;
    const cols = sc.columns ?? (PORTRAIT ? (n <= 4 ? 2 : n <= 9 ? 3 : n <= 16 ? 4 : 5) : Math.min(n, n <= 6 ? n : n <= 12 ? 6 : 8));
    const rows = Math.ceil(n / cols);
    const areaTop = PORTRAIT ? H * 0.3 : H * 0.34, areaH = PORTRAIT ? H * 0.46 : H * 0.5;
    const d = Math.min((W * 0.9) / cols - 24 * U, areaH / rows - 28 * U, 300 * U);
    const gap = d + 24 * U;
    return sc.members.map((m, k) => {
      const row = Math.floor(k / cols), c = k % cols, inRow = Math.min(cols, n - row * cols);
      return { x: CX + (c - (inRow - 1) / 2) * gap, y: areaTop + (areaH - rows * (d + 28 * U)) / 2 + d / 2 + row * (d + 28 * U), d, row, col: c };
    });
  }

  /* ---------------------------------------------------------------- frame state */
  let back = "", front = "", media = [];

  /* ---------------------------------------------------------------- background */
  const sceneBg = (sc) => (!sc || sc.background == null || sc.background === "paper" ? PAPER : sc.tint === false ? col(sc.background) : tint(sc.background));
  function drawBackground(t) {
    const sc = sceneAt(t);
    const prevBg = sceneBg(sc.prev), bg = sceneBg(sc);
    const r = prevBg === bg ? 9999 : inOutCubic(prog(t, sc.start, sc.start + 0.5)) * Math.hypot(W, H);
    BG = bg;
    back = `<rect width="${W}" height="${H}" fill="${prevBg}"/><circle cx="${f1(CX)}" cy="${f1(H * 0.45)}" r="${f1(r)}" fill="${bg}"/>`;
    if (S.style?.decor !== false && sc.type !== "pileup") {
      [[0.14, 0.17, 120, 0], [0.88, 0.27, 170, 1], [0.11, 0.78, 190, 2], [0.89, 0.9, 110, 3], [0.81, 0.61, 70, 4]].forEach(([x, y, r2, k]) => {
        back += `<circle cx="${f1(x * W + Math.sin(t * 1.1 + k) * 30 * U)}" cy="${f1(y * H + Math.cos(t * 1.3 + k * 2) * 26 * U)}" r="${f1(r2 * U)}" fill="#fff" opacity=".28"/>`;
      });
    }
  }
  const sceneAt = (t) => scenes.find((s) => t >= s.start && t < s.end) ?? scenes[scenes.length - 1];

  /* ================================================================ scenes */
  const SCENES = {};

  /* ---- pileup: things pile up and shake, words slam in, then everything clears. */
  SCENES.pileup = {
    render(sc, t) {
      const items = sc.items ?? [];
      const clearAt = sc.end - 0.55;
      const amp = t >= clearAt ? 0 : (2 + 12 * prog(t, sc.start + 0.8, clearAt)) * U;
      const nw = Math.min(W * 0.8, 860 * U), nh = 132 * U;
      items.forEach((n, k) => {
        // The first card is already there at the very first frame (the thumbnail).
        const d = k === 0 ? sc.start - 0.3 : sc.start + 0.12 + (sc.len - 0.9) * Math.pow(k / Math.max(1, items.length - 1), 0.72);
        const fall = prog(t, d, d + 0.26);
        if (fall <= 0) return;
        const slotY = H * 0.88 - k * 62 * U * (PORTRAIT ? 1 : 0.55), slotX = CX + (hash(k + 2) - 0.5) * 150 * U;
        let y = lerp(-150 * U, slotY, inQuad(fall)), x = slotX, rot = (hash(k + 5) - 0.5) * 14 * fall + (1 - fall) * (k % 2 ? 20 : -20);
        const w = wobble(t - d - 0.26, 0.06, 30, 9);
        x += Math.sin(t * 43 + k * 1.7) * amp; y += Math.cos(t * 37 + k) * amp * 0.6; rot += Math.sin(t * 29 + k) * amp * 0.12 / U;
        const away = inQuad(prog(t, clearAt + hash(k) * 0.12, clearAt + 0.5 + hash(k) * 0.12));
        y -= away * H * 1.1; rot += away * (hash(k + 8) - 0.5) * 70; x += away * (hash(k + 3) - 0.5) * 600 * U;
        front += notification(n, x, y, rot, (1 + w) * lerp(1, 0.7, away), 1 - away * 0.7, nw, nh);
      });
      (sc.slams ?? []).forEach((sl, k) => {
        const t0 = when(sc, sl.at, 0.4 + k * 0.5);
        const p = prog(t, t0, t0 + 0.22);
        if (p <= 0) return;
        const spots = [[0.3, 0.17, -7], [0.71, 0.245, 6], [0.4, 0.318, -4], [0.68, 0.39, 5]];
        const [x, y, r] = spots[k % spots.length];
        const away = inBack(prog(t, clearAt + 0.05 * k, clearAt + 0.45 + 0.05 * k));
        const s = lerp(2.2, 1, outBack(p, 2)) * (1 + wobble(t - t0 - 0.22, 0.08)) * (1 - away * 0.3);
        front += `<g opacity="${clamp(p * 4).toFixed(3)}" transform="translate(0 ${f1(-away * H * 0.5)})">${pill(sl.text, x * W + Math.sin(t * 50 + k * 3) * amp * 0.5, y * H, { size: 88 * U, fill: sl.color ? col(sl.color) : INK, rot: r + away * 30, scale: s, what: `scene ${sc.key}: slam "${sl.text}"` })}</g>`;
      });
      if (sc.headline) {
        const t0 = when(sc, sc.headline.at, sc.len * 0.6);
        const L = fit(sc.headline.text, 800, 150 * U, TEXT_ROOM, -0.02, MIN_TITLE * U, `scene ${sc.key}: headline`);
        const out = inBack(prog(t, clearAt, clearAt + 0.25));
        front += popLine(t, L, CX + Math.sin(t * 60) * amp * 0.6, H * 0.43, readable(col(sc.headline.color ?? style.accent), BG, `scene ${sc.key}: headline colour`), t0, { step: 0.03, dur: 0.24, from: -60, out, seed: 5, stroke: "#fff" });
      }
    },
    cues(sc, add) {
      const items = sc.items ?? [];
      items.forEach((_, k) => k > 0 && add(sc.start + 0.12 + (sc.len - 0.9) * Math.pow(k / Math.max(1, items.length - 1), 0.72) + 0.24, "ding", { pitch: 1 + (k % 5) * 0.12, gain: 0.35 + (0.5 * k) / Math.max(1, items.length) }));
      (sc.slams ?? []).forEach((sl, k) => add(when(sc, sl.at, 0.4 + k * 0.5), "slam", { gain: 0.8 }));
      if (sc.headline) add(when(sc, sc.headline.at, sc.len * 0.6), "boing", { pitch: 0.7, gain: 0.7 });
      add(sc.end - 0.55, "whoosh", { dur: 0.8, gain: 0.5 });
    },
  };
  function notification(n, x, y, rot, sc, op, nw, nh) {
    const hw = nw / 2, hh = nh / 2, k = nh / 132;
    const c = onFill(col(n.color ?? "slate"));
    return `<g transform="translate(${f1(x)} ${f1(y)}) rotate(${rot.toFixed(2)}) scale(${sc.toFixed(3)})" opacity="${op.toFixed(3)}">`
      + `<rect x="${f1(-hw)}" y="${f1(-hh + 10 * k)}" width="${f1(nw)}" height="${f1(nh)}" rx="${f1(36 * k)}" fill="${INK}" opacity=".13"/>`
      + `<rect x="${f1(-hw)}" y="${f1(-hh)}" width="${f1(nw)}" height="${f1(nh)}" rx="${f1(36 * k)}" fill="#fff"/>`
      + `<rect x="${f1(-hw + 26 * k)}" y="${f1(-38 * k)}" width="${f1(76 * k)}" height="${f1(76 * k)}" rx="${f1(20 * k)}" fill="${c.fill}"/>`
      + `<text x="${f1(-hw + 64 * k)}" y="${f1(14 * k)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(40 * k)}" fill="${c.text}">${esc(n.icon ?? (n.title ?? "?")[0])}</text>`
      + `<text x="${f1(-hw + 128 * k)}" y="${f1(-8 * k)}" font-family='${FONT}' font-weight="800" font-size="${f1(36 * k)}" fill="${INK}">${esc(n.title ?? "")}</text>`
      + `<text x="${f1(-hw + 128 * k)}" y="${f1(36 * k)}" font-family='${FONT}' font-weight="500" font-size="${f1(32 * k)}" fill="#5d5c58">${esc(n.body ?? "")}</text>`
      + `<text x="${f1(hw - 30 * k)}" y="${f1(-14 * k)}" text-anchor="end" font-family='${FONT}' font-weight="500" font-size="${f1(26 * k)}" fill="#6b6a66">${esc(n.time ?? labels.now)}</text></g>`;
  }

  /* ---- title lines: shared by the title and fan scenes. */
  function titleLines(sc, t, area) {
    const lines = sc.lines ?? [];
    const out = inBack(prog(t, sc.end - 0.26, sc.end));
    // A line may not shrink below 72 px; a line that asks for a smaller size may shrink 15% from it (never under 48 px).
    const layouts = lines.map((ln) => fit(ln.text, ln.weight ?? 800, (ln.size ?? (ln.big ? 240 : ln.breathe ? 170 : 130)) * U, TEXT_ROOM, -0.03, (ln.size ? Math.max(48, Math.min(MIN_TITLE, ln.size * 0.85)) : MIN_TITLE) * U, `scene ${sc.key}: title line`));
    const gap = 30 * U;
    const total = layouts.reduce((a, L, k) => (lines[k].breathe ? a : a + L.size * 0.95 + gap), -gap);
    let y = area.center - total / 2;
    lines.forEach((ln, k) => {
      const L = layouts[k];
      if (!ln.breathe) y += L.size * 0.8;
      const t0 = early(sc, when(sc, ln.at, 0.15 + k * 0.4));
      const until = ln.until != null ? when(sc, ln.until, sc.len) - 0.1 : null;
      const lineOut = until != null ? inCubic(prog(t, until, until + 0.4)) : out;
      const ct = ln.color ? colouredText(col(ln.color), BG) : { text: readable(INK, BG), marker: null };
      const fill = ct.text;
      if (ln.breathe) {
        const p = outBack(prog(t, t0, t0 + 0.5), 1.5);
        const s = p * (1 + 0.08 * prog(t, t0, until ?? sc.end));
        if (p > 0 && lineOut < 1) front += `<g transform="translate(${f1(CX)} ${f1((ln.y ?? 0.45) * H - lineOut * 500 * U)}) scale(${s.toFixed(3)})" opacity="${(1 - lineOut).toFixed(3)}"><text text-anchor="middle" font-family='${FONT}' font-weight="${L.weight}" font-size="${L.size.toFixed(1)}" fill="${fill}">${esc(ln.text)}</text></g>`;
      } else {
        const base = ln.y != null ? ln.y * H : y;
        if (ct.marker && lineOut < 1) front += `<g opacity="${clamp(1 - lineOut).toFixed(3)}" transform="translate(0 ${f1(lineOut * 900 * U)})">${marker(CX - L.width / 2, L.width, base, L.size, ct.marker, outCubic(prog(t, t0, t0 + 0.3 + L.letters.length * 0.02)))}</g>`;
        front += popLine(t, L, CX, base, fill, t0, { step: ln.big ? 0.045 : 0.03, dur: ln.big ? 0.3 : 0.34, from: ln.big ? 180 : -110, out: lineOut, seed: 41 + k * 7, spin: ln.big ? 40 : 30 });
        if (ln.confetti) front += burst(t, t0 + 0.15, CX, y - L.size * 0.35, 610 + k, CONFETTI, 18, 380, 150 * U);
      }
      if (!ln.breathe) y += L.size * 0.15 + gap;
    });
    if (sc.badge) {
      const t0 = when(sc, sc.badge.at, 0.8);
      const p = outBack(prog(t, t0, t0 + 0.3), 2.4);
      if (p > 0 && out < 1) front += pill(sc.badge.text, CX, y + 20 * U - out * 400 * U, { size: 50 * U, rot: -3, scale: p * (1 - out), fill: sc.badge.color ? col(sc.badge.color) : INK, what: `scene ${sc.key}: badge` });
    }
  }
  function titleCues(sc, add) {
    (sc.lines ?? []).forEach((ln, k) => {
      const t0 = when(sc, ln.at, 0.15 + k * 0.4);
      if (ln.breathe) add(t0, "breath");
      else if (ln.big) { add(t0 + 0.1, "boing", { pitch: 1.1, gain: 0.6 }); if (ln.confetti) add(t0 + 0.15, "sparkle", { gain: 0.8 }); }
      else add(t0 + 0.05, "pop", { pitch: 1 + k * 0.1, gain: 0.5 });
    });
    if (sc.badge) add(when(sc, sc.badge.at, 0.8), "blip", { pitch: 1.3, gain: 0.6 });
  }

  /* ---- title: big kinetic lines, centred. */
  SCENES.title = {
    render(sc, t) { titleLines(sc, t, { center: H * 0.45 }); },
    cues: titleCues,
  };

  /* ---- fan: media cards fan in like a hand of cards, with title lines above. Always inside the frame. */
  function fanGeom(sc) {
    const n = sc.cards.length;
    const fw = Math.min(PORTRAIT ? H * 0.15 : H * 0.22, (W * 0.9) / (0.62 * n + 0.5));
    const fh = fw * 1.63;
    const R = PORTRAIT ? H * 0.9 : H * 1.3;
    const midY = PORTRAIT ? H * 0.64 : H * 0.66;
    const maxDx = W / 2 - fw * 0.65 - 24 * U;
    const aMax = Math.asin(Math.min(0.95, Math.max(0, maxDx) / R));
    const step = n > 1 ? Math.min((10 * Math.PI) / 180, (2 * aMax) / (n - 1)) : 0;
    return { fw, fh, R, py: midY + R, step, n };
  }
  const fanPose = (sc, i, t) => {
    const g = fanGeom(sc);
    const a = (i - (g.n - 1) / 2) * g.step;
    const t0 = when(sc, sc.cardsAt, 0.6) + i * 0.09;
    const p = outBack(prog(t, t0, t0 + 0.42), 1.6);
    return { x: CX + Math.sin(a) * g.R, y: lerp(H + g.fh, g.py - Math.cos(a) * g.R, p) + Math.sin((t - t0) * 3 + i) * 8 * U, rot: ((a * 180) / Math.PI) * p, p, t0 };
  };
  SCENES.fan = {
    render(sc, t) {
      titleLines(sc, t, { center: PORTRAIT ? H * 0.26 : H * 0.2 });
      const { fw, fh } = fanGeom(sc);
      const next = sc.next?.type === "card" && sc.next.media === sc.cards[0] ? sc.next : null;
      const B = cardBox(next);
      const collapse = prog(t, sc.end - 0.5, sc.end);
      sc.cards.forEach((id, i) => {
        const f = fanPose(sc, i, t);
        if (f.p <= 0) return;
        if (i === 0 && next) {
          const e = inOutCubic(collapse);
          media.push({ id, variant: "full", t: t - sc.start, x: lerp(f.x, B.x, e), y: lerp(f.y, B.y, e) - Math.sin(collapse * Math.PI) * 140 * U, w: lerp(fw, B.w, e), h: lerp(fh, B.h, e), rot: lerp(f.rot, -2.5, e), radius: lerp(26, 46, e) * U, border: lerp(8, 14, e) * U, z: 1 });
        } else {
          const drop = inBack(prog(t, sc.end - 0.5 + i * 0.03, sc.end - 0.1 + i * 0.03), 1.4);
          media.push({ id, variant: "full", t: t - sc.start + i, x: f.x, y: f.y + drop * H * 0.75, w: fw, h: fh, rot: f.rot + drop * (i < sc.cards.length / 2 ? -30 : 30), radius: 26 * U, border: 8 * U });
        }
      });
    },
    cues(sc, add) {
      titleCues(sc, add);
      sc.cards.forEach((_, i) => add(when(sc, sc.cardsAt, 0.6) + i * 0.09 + 0.1, "pop", { pitch: 0.9 + i * 0.1, gain: 0.7 }));
      add(sc.end - 0.5, "whoosh", { dur: 0.55, gain: 0.8 });
    },
  };

  /* ---- card: one media card, name sticker, caption, speech bubble, optional prompt panel. */
  const SIDES = [-1, 1];
  /** Multi-line text, left-aligned from x or centred on x. */
  function textBlock(lines, x, yFirst, size, weight, fill, { anchor = "middle", lh = 1.28, op = 1 } = {}) {
    return lines.map((l, k) => `<text x="${f1(x)}" y="${f1(yFirst + k * size * lh)}" text-anchor="${anchor}" font-family='${FONT}' font-weight="${weight}" font-size="${f1(size)}" fill="${fill}" opacity="${op.toFixed(3)}">${esc(l)}</text>`).join("");
  }
  SCENES.card = {
    render(sc, t) {
      const [ri, rn] = cardRun(sc);
      const u = t - sc.start;
      const side = SIDES[ri % 2];
      const c = col(sc.color);
      const B = cardBox(sc);
      const handedOver = sc.prev?.type === "fan" && sc.prev.cards[0] === sc.media && sc.prev.next === sc;
      // The previous card flies off while this one comes in.
      if (sc.prev?.type === "card" && u < 0.4) {
        const PB = cardBox(sc.prev);
        const p = inBack(prog(u, 0, 0.36), 1.4), ps = SIDES[(ri - 1) % 2] ?? 1;
        media.push({ id: sc.prev.media, variant: "full", t: t - sc.prev.start, x: PB.x - ps * p * W * 1.1, y: PB.y - p * 200 * U, w: PB.w, h: PB.h, rot: ps * -2.5 - ps * p * 35, border: 14 * U });
      }
      // A tiny squash on every spoken word.
      let talk = 0;
      if (sc.v) for (const w of sc.v.words) talk += wobble(u - sc.voiceAt - w.start + sc.v.speechStart, 0.016, 32, 11);
      let x = B.x, y = B.y, rot = -2.5 * side, sx = 1, sy = 1;
      if (handedOver) {
        const w = wobble(u, 0.07, 26, 7) + talk; sx = 1 + w; sy = 1 - w; rot = -2.5;
      } else {
        const enter = prog(u, 0, 0.34), e = outBack(enter, 1.5);
        x = lerp(B.x + side * W * 0.93, B.x, e);
        y = lerp(B.y + 260 * U, B.y, outCubic(enter)) - Math.sin(enter * Math.PI) * 120 * U;
        rot = lerp(side * 28, side * -2.5, e);
        const w = wobble(u - 0.34, 0.07, 26, 7) + talk, zoom = 1 + 0.03 * prog(u, 0.34, sc.len);
        sx = (1 + w) * zoom; sy = (1 - w) * zoom;
      }
      media.push({ id: sc.media, variant: "full", t: u, x, y, w: B.w, h: B.h, rot, sx, sy, border: 14 * U });
      if (!handedOver) front += burst(u, 0.34, B.x, B.y, sc.index * 31, [c, INK, "#fff"], 16, 260, B.h / 2);

      const out = (d = 0) => inBack(prog(u, sc.len - 0.14 + d, sc.len + 0.06 + d));
      const ts = handedOver ? 0.05 : 0.24;
      const bottom = B.y + B.h / 2;
      if (sc.number !== false) {
        const tag = outBack(prog(u, ts, ts + 0.2), 2.4) * (1 - out(0));
        const num = typeof sc.number === "string" ? sc.number : `${labels.number} ${String(ri + 1).padStart(2, "0")}`;
        front += pill(num, B.x - B.w / 2 + 40 * U, B.y - B.h / 2 + 30 * U, { size: 40 * U, rot: -8, scale: tag });
      }
      if (sc.name) {
        const st = outBack(prog(u, ts - 0.06, ts + 0.18), 2.2) * (1 - out(0.02));
        const size = Math.max(MIN_TEXT * U, Math.min(88 * U, (88 * U * B.w * 1.3) / measure(sc.name, 800, 88 * U)));
        front += pill(sc.name, B.x, bottom - 40 * U, { size, fill: c, stroke: "#fff", rot: -3 + (1 - clamp(st)) * 20, scale: st, padX: 1.0, what: `scene ${sc.key}: name sticker` });
      }
      let below = bottom + 58 * U;
      if (sc.caption) {
        const room = PORTRAIT ? TEXT_ROOM : W * 0.44;
        const cap = wrap(sc.caption, 700, (sc.prompt ? 46 : 54) * U, MIN_TEXT * U, room, 2, `scene ${sc.key}: caption`);
        const p = prog(u, ts + 0.1, ts + 0.4) * (1 - out(0.04));
        const fill = readable(INK, BG, `scene ${sc.key}: caption`);
        front += `<g transform="translate(0 ${f1((1 - outCubic(clamp(p))) * 30 * U)})">${textBlock(cap.lines, B.x, below + cap.size, cap.size, 700, fill, { op: clamp(p * 2) })}</g>`;
        below += cap.lines.length * cap.size * 1.28 + 20 * U;
        if (!sc.prompt) safe(sc, below - cap.size * 2, below, "the caption");
      }
      if (sc.prompt) drawPrompt(sc, t, u, B, c, below, out(0.04));
      if (sc.bubble) drawBubble(sc, t, u, B, c, out(-0.04));
      // Progress dots across a run of cards, above the platform's caption zone.
      if (rn > 1 && sc.progress !== false) {
        const run = scenes.slice(sc.index - ri, sc.index - ri + rn);
        const px = CX - ((rn - 1) * 40 * U) / 2;
        let s = "";
        run.forEach((r, k) => {
          const on = k === ri ? outBack(prog(u, 0, 0.3)) : k === ri - 1 ? 1 - prog(u, 0, 0.2) : 0;
          const wdt = (14 + on * 30) * U;
          s += `<rect x="${f1(px + k * 40 * U - wdt / 2)}" y="${f1(PORTRAIT ? H * 0.845 : H * 0.93)}" width="${f1(wdt)}" height="${f1(14 * U)}" rx="${f1(7 * U)}" fill="${k <= ri ? col(r.color) : INK}" opacity="${k <= ri ? 1 : 0.25}"/>`;
        });
        front += s;
      }
    },
    cues(sc, add) {
      const handedOver = sc.prev?.type === "fan" && sc.prev.cards[0] === sc.media;
      if (handedOver) add(sc.start, "thud");
      else {
        add(sc.start - 0.06, "whoosh", { dur: 0.38 });
        add(sc.start + 0.3, "thud");
        // High twinkles mask the first sibilants of a line starting right after: only without a voice.
        if (!sc.v) add(sc.start + 0.34, "sparkle", { gain: 0.3 });
      }
      if (sc.bubble) add(sc.start + (sc.v ? sc.voiceAt : 0.5) - 0.05, "bubble", { gain: 0.5 });
      if (sc.prompt) add(sc.start + promptStart(sc), "typing", { dur: promptTypeTime(sc), gain: 0.5 });
    },
  };
  function drawBubble(sc, t, u, B, c, out) {
    const vu = sc.v ? sc.voiceAt : 0.5;
    const b = outElastic(prog(u, vu - 0.05, vu + 0.55)) * (1 - out);
    if (b <= 0.001) return;
    const meter = sc.v ? 84 * U : 0;
    const wr = wrap(sc.bubble, 700, 46 * U, MIN_TEXT * U, W * 0.74 - meter, 2, `scene ${sc.key}: bubble`);
    const tw = Math.max(...wr.lines.map((l) => measure(l, 700, wr.size)));
    const bw = tw + meter + 72 * U, bh = wr.lines.length * wr.size * 1.28 + 44 * U;
    const by = B.y - B.h / 2 - bh / 2 - 34 * U;
    safe(sc, by - bh / 2, by + bh / 2, "the speech bubble");
    const talking = speaking(sc, t);
    let s = `<g transform="translate(${f1(B.x + 20 * U)} ${f1(by + Math.sin(u * 7) * 5 * U)}) scale(${b.toFixed(3)}) rotate(${((1 - clamp(b)) * -10 + 2).toFixed(2)})">`;
    s += `<rect x="${f1(-bw / 2)}" y="${f1(-bh / 2 + 8 * U)}" width="${f1(bw)}" height="${f1(bh)}" rx="${f1(Math.min(bh / 2, 48 * U))}" fill="${INK}" opacity=".14"/>`;
    s += `<rect x="${f1(-bw / 2)}" y="${f1(-bh / 2)}" width="${f1(bw)}" height="${f1(bh)}" rx="${f1(Math.min(bh / 2, 48 * U))}" fill="#fff"/>`;
    s += `<path d="M${f1(-120 * U)} ${f1(bh / 2 - 4 * U)} L${f1(-150 * U)} ${f1(bh / 2 + 34 * U)} L${f1(-80 * U)} ${f1(bh / 2 - 4 * U)} Z" fill="#fff"/>`;
    if (sc.v) {
      const mc = readable(c, "#ffffff");
      for (let k = 0; k < 4; k++) {
        const lv = talking ? 0.35 + 0.65 * Math.abs(Math.sin(t * (13 + k * 3.1) + k * 1.9)) : 0.3;
        s += `<rect x="${f1(-bw / 2 + 36 * U + k * 16 * U)}" y="${f1((-40 * U * lv) / 2)}" width="${f1(9 * U)}" height="${f1(40 * U * lv)}" rx="${f1(4.5 * U)}" fill="${mc}"/>`;
      }
    }
    const tx = -bw / 2 + 36 * U + meter;
    const y0 = -bh / 2 + 22 * U + wr.size * 0.9;
    s += textBlock(wr.lines, tx, y0, wr.size, 700, INK, { anchor: "start" });
    front += s + "</g>";
  }
  /** When the prompt starts typing, in seconds from the scene start, and how long it types. */
  const promptStart = (sc) => (sc.v ? sc.voiceAt : 0.5);
  const promptTypeTime = (sc) => Math.min(1.2, Math.max(0.4, String(sc.prompt).length / 70));
  function drawPrompt(sc, t, u, B, c, below, out) {
    if (PORTRAIT) return drawPromptPanel(sc, t, u, c, { x: CX, pw: Math.min(W * 0.88, 960 * U), top: below + 10 * U, bottomLimit: H * 0.83, size: 46 * U }, out);
    return drawPromptPanel(sc, t, u, c, { x: W * 0.7, pw: W * 0.5, top: H * 0.16, bottomLimit: H * 0.84, size: 46 * U }, out);
  }
  /** The prompt panel: a label chip and the text, typed out within 1.2 s. Returns its bottom edge. */
  function drawPromptPanel(sc, t, u, c, { x, pw, top, bottomLimit, size }, out) {
    const pad = 36 * U, labelH = 56 * U;
    const maxLines = Math.max(2, Math.floor((bottomLimit - top - pad * 2 - labelH) / (size * 1.3)));
    const wr = wrap(sc.prompt, 600, size, MIN_TEXT * U, pw - pad * 2, maxLines, `scene ${sc.key}: prompt`);
    const ph = pad * 2 + labelH + wr.lines.length * wr.size * 1.3;
    safe(sc, top, top + ph, "the prompt panel");
    const appear = outBack(prog(u, promptStart(sc) - 0.25, promptStart(sc) + 0.05), 1.6) * (1 - out);
    if (appear <= 0.001) return top + ph;
    // Typed fast, so the whole prompt is readable for most of the scene.
    const shown = Math.floor(clamp((u - promptStart(sc)) / promptTypeTime(sc)) * String(sc.prompt).length);
    let left = shown;
    const lines = wr.lines.map((l, k) => { const take = Math.max(0, Math.min(l.length, left)); left -= l.length + (k < wr.lines.length - 1 ? 1 : 0); return l.slice(0, take); });
    const typing = shown < String(sc.prompt).length;
    const label = onFill(c, `scene ${sc.key}: prompt label`);
    let s2 = `<g transform="translate(${f1(x)} ${f1(top)}) scale(${appear.toFixed(3)})">`;
    s2 += uiCard(0, ph / 2, pw, ph, { radius: 34 * U });
    const lw = measure(labels.prompt, 800, 30 * U) + 36 * U;
    s2 += `<rect x="${f1(-pw / 2 + pad)}" y="${f1(pad - 6 * U)}" width="${f1(lw)}" height="${f1(46 * U)}" rx="${f1(23 * U)}" fill="${label.fill}"/>`;
    s2 += `<text x="${f1(-pw / 2 + pad + lw / 2)}" y="${f1(pad + 27 * U)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(30 * U)}" fill="${label.text}">${esc(labels.prompt)}</text>`;
    const y0 = pad + labelH + wr.size * 0.95;
    s2 += textBlock(lines, -pw / 2 + pad, y0, wr.size, 600, INK, { anchor: "start", lh: 1.3 });
    if (typing && Math.floor(t * 3) % 2 === 0) {
      const li = lines.reduce((acc, l, k) => (l.length || k === 0 ? k : acc), 0);
      const cx2 = -pw / 2 + pad + measure(lines[li], 600, wr.size) + 6 * U;
      s2 += `<rect x="${f1(cx2)}" y="${f1(y0 + li * wr.size * 1.3 - wr.size * 0.8)}" width="${f1(5 * U)}" height="${f1(wr.size)}" fill="${readable(c, "#ffffff")}"/>`;
    }
    front += s2 + "</g>";
    return top + ph;
  }

  /* ---- chat: a chat window where messages appear, with an optional stamp slammed on top. */
  SCENES.chat = {
    render(sc, t) {
      titleLines(sc, t, { center: PORTRAIT ? H * 0.15 : H * 0.13 });
      const out = inBack(prog(t, sc.end - 0.24, sc.end));
      const pw = Math.min(W * 0.88, (PORTRAIT ? 960 : 1300) * U);
      const areaTop = PORTRAIT ? H * 0.27 : H * 0.26, areaBottom = PORTRAIT ? H * 0.82 : H * 0.9;
      const appear = outBack(prog(t, early(sc, sc.start + 0.05), early(sc, sc.start + 0.05) + 0.35), 1.4);
      if (appear <= 0.001) return;
      // The window is as tall as its messages, centred in the space under the title.
      const heights = (sc.messages ?? []).map((m) => { const w2 = wrap(m.text, 600, 46 * U, MIN_TEXT * U, pw * 0.7, 5); return w2.lines.length * w2.size * 1.3 + 40 * U; });
      const ph = Math.min(areaBottom - areaTop, Math.max(H * 0.22, 150 * U + heights.reduce((a2, h2) => a2 + h2 + 26 * U, 0) + (sc.stamp ? 190 * U : 20 * U)));
      const top = (areaTop + areaBottom) / 2 - ph / 2, bottom = top + ph;
      safe(sc, top, bottom, "the chat window");
      let s = `<g transform="translate(${f1(CX)} ${f1(top + ph / 2 + out * H * 0.7)}) scale(${appear.toFixed(3)}) translate(0 ${f1(-ph / 2)})">`;
      s += `<rect x="${f1(-pw / 2)}" y="${f1(10 * U)}" width="${f1(pw)}" height="${f1(ph)}" rx="${f1(40 * U)}" fill="${INK}" opacity=".14"/>`;
      s += `<rect x="${f1(-pw / 2)}" y="0" width="${f1(pw)}" height="${f1(ph)}" rx="${f1(40 * U)}" fill="#fff"/>`;
      const acc = col(sc.color ?? style.accent);
      s += `<circle cx="${f1(-pw / 2 + 60 * U)}" cy="${f1(56 * U)}" r="${f1(20 * U)}" fill="${acc}"/>`;
      s += `<text x="${f1(-pw / 2 + 96 * U)}" y="${f1(70 * U)}" font-family='${FONT}' font-weight="800" font-size="${f1(40 * U)}" fill="${INK}">${esc(sc.name ?? labels.assistant)}</text>`;
      s += `<rect x="${f1(-pw / 2)}" y="${f1(110 * U)}" width="${f1(pw)}" height="${f1(2 * U)}" fill="${INK}" opacity=".12"/>`;
      let cy = 150 * U;
      (sc.messages ?? []).forEach((m, i) => {
        const t0 = when(sc, m.at, 0.5 + i * 0.9);
        const p = outBack(prog(t, t0, t0 + 0.3), 1.8);
        const user = m.from === "user";
        const wr = wrap(m.text, 600, 46 * U, MIN_TEXT * U, pw * 0.7, 5, `scene ${sc.key}: message ${i + 1}`);
        const tw = Math.max(...wr.lines.map((l) => measure(l, 600, wr.size)));
        const bw = tw + 60 * U, bh = wr.lines.length * wr.size * 1.3 + 40 * U;
        if (p > 0) {
          const colors = user ? onFill(acc, `scene ${sc.key}: user message`) : { fill: "#eeede8", text: INK };
          const bx = user ? pw / 2 - 36 * U - bw : -pw / 2 + 36 * U;
          // Answers type out quickly; questions appear whole.
          let lines = wr.lines;
          if (!user) {
            let left = Math.floor(clamp((t - t0) / Math.min(1.2, Math.max(0.35, m.text.length / 80))) * m.text.length);
            lines = wr.lines.map((l, k) => { const take = Math.max(0, Math.min(l.length, left)); left -= l.length + 1; return l.slice(0, take); });
          }
          s += `<g transform="translate(${f1(bx + bw / 2)} ${f1(cy + bh / 2)}) scale(${clamp(p, 0, 1.2).toFixed(3)}) translate(${f1(-bw / 2)} ${f1(-bh / 2)})">`;
          s += `<rect width="${f1(bw)}" height="${f1(bh)}" rx="${f1(Math.min(bh / 2, 34 * U))}" fill="${colors.fill}"/>`;
          s += textBlock(lines, 30 * U, 20 * U + wr.size * 0.95, wr.size, 600, colors.text, { anchor: "start", lh: 1.3 });
          s += "</g>";
        }
        cy += bh + 26 * U;
      });
      if (cy > ph + 1) problem(`scene ${sc.key}: the messages do not fit in the chat window; use fewer or shorter messages.`);
      if (sc.stamp) {
        const t0 = when(sc, sc.stamp.at, sc.len * 0.6);
        const p = prog(t, t0, t0 + 0.2);
        if (p > 0) {
          const sc2 = lerp(2.4, 1, outBack(p, 2)) * (1 + wobble(t - t0 - 0.2, 0.1));
          const scol = readable(col(sc.stamp.color ?? "rose"), "#ffffff", `scene ${sc.key}: stamp`);
          const size = 130 * U, sw = measure(sc.stamp.text, 900, size) + 80 * U;
          // Under the last answer, overlapping only its bottom edge, so the answer stays readable.
          s += `<g transform="translate(${f1(pw * 0.12)} ${f1(cy + size * 0.28)}) rotate(-8) scale(${sc2.toFixed(3)})" opacity="${clamp(p * 3).toFixed(3)}">`;
          s += `<rect x="${f1(-sw / 2)}" y="${f1(-size * 0.72)}" width="${f1(sw)}" height="${f1(size * 1.2)}" rx="${f1(26 * U)}" fill="#fff" fill-opacity=".92" stroke="${scol}" stroke-width="${f1(14 * U)}"/>`;
          s += `<text text-anchor="middle" y="${f1(size * 0.3)}" font-family='${FONT}' font-weight="900" font-size="${f1(size)}" fill="${scol}">${esc(sc.stamp.text)}</text></g>`;
        }
      }
      front += s + "</g>";
    },
    cues(sc, add) {
      titleCues(sc, add);
      add(sc.start + 0.05, "pop", { pitch: 0.8, gain: 0.5 });
      (sc.messages ?? []).forEach((m, i) => {
        const t0 = when(sc, m.at, 0.5 + i * 0.9);
        if (m.from === "user") add(t0, "bubble", { gain: 0.6 });
        else add(t0, "typing", { dur: Math.min(1.2, Math.max(0.35, m.text.length / 80)), gain: 0.45 });
      });
      if (sc.stamp) { const t0 = when(sc, sc.stamp.at, sc.len * 0.6); add(t0, "slam", { gain: 0.9 }); add(t0 + 0.02, "boing", { pitch: 0.6, gain: 0.5 }); }
      add(sc.end - 0.35, "whoosh", { dur: 0.45, gain: 0.5 });
    },
  };

  /* ---------------------------------------------------------------- UI kit: icons and cards */
  // Line icons on a 24-unit grid, stroked; drawn, so no image is needed.
  const ICONS = {
    check: "M5 12.5l4.5 4.5L19 7.5",
    x: "M6.5 6.5l11 11M17.5 6.5l-11 11",
    clock: "M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 1 0 0-17M12 7.5v5l3.5 2",
    bolt: "M13 2.5L5 13.5h6l-1 8l8-11h-6z",
    star: "M12 3l2.7 5.6l6.1.8l-4.4 4.3l1 6.1L12 17l-5.4 2.8l1-6.1L3.2 9.4l6.1-.8z",
    bell: "M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15zM10 20a2 2 0 0 0 4 0",
    chart: "M4 20.5h16M7 17v-5M12 17V7M17 17v-8",
    calendar: "M4.5 6.5h15v13h-15zM4.5 10.5h15M8.5 4v4M15.5 4v4",
    chat: "M4.5 5.5h15v10h-8l-4.5 3.5v-3.5h-2.5z",
    lock: "M6.5 11h11v9h-11zM8.5 11V8a3.5 3.5 0 0 1 7 0v3",
    heart: "M12 19.5s-7.5-4.6-7.5-10a4 4 0 0 1 7.5-2a4 4 0 0 1 7.5 2c0 5.4-7.5 10-7.5 10z",
    target: "M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 1 0 0-17M12 7.5a4.5 4.5 0 1 0 0 9a4.5 4.5 0 1 0 0-9M12 11.2a.8.8 0 1 0 0 1.6a.8.8 0 1 0 0-1.6",
    mail: "M3.5 6.5h17v11h-17zM3.5 7l8.5 6.5L20.5 7",
    list: "M9 7h11M9 12h11M9 17h11M4.5 7h.5M4.5 12h.5M4.5 17h.5",
    users: "M9 11a3.5 3.5 0 1 0 0-7a3.5 3.5 0 0 0 0 7M2.5 20c0-3.5 3-5.5 6.5-5.5s6.5 2 6.5 5.5M16 4.5a3.5 3.5 0 0 1 0 6.5M18.5 14.8c1.8.7 3 2.5 3 5.2",
    search: "M10.5 4a6.5 6.5 0 1 0 0 13a6.5 6.5 0 1 0 0-13M15.5 15.5l5 5",
    up: "M12 19.5v-15M6 10.5l6-6l6 6",
    rocket: "M12 3c3 2 4.5 5.5 4.5 9.5l-2.5 3h-4l-2.5-3C7.5 8.5 9 5 12 3zM9.5 15.5l-3 3.5M14.5 15.5l3 3.5M12 9a1.5 1.5 0 1 0 0 3a1.5 1.5 0 1 0 0-3",
    down: "M12 4.5v15M6 13.5l6 6l6-6",
    globe: "M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 1 0 0-17M3.5 12h17M12 3.5c2.5 2.5 3.5 5.5 3.5 8.5s-1 6-3.5 8.5M12 3.5c-2.5 2.5-3.5 5.5-3.5 8.5s1 6 3.5 8.5",
    book: "M4 5.5c2.5-1 5.5-1 8 1v13c-2.5-2-5.5-2-8-1zM20 5.5c-2.5-1-5.5-1-8 1v13c2.5-2 5.5-2 8-1z",
    school: "M2.5 9.5L12 5l9.5 4.5L12 14zM6.5 11.5v4.5c3 2.5 8 2.5 11 0v-4.5M21.5 9.5v5",
    idea: "M9 17.5h6M10 20.5h4M12 3.5a6 6 0 0 0-3.5 10.9c.4.3.5.7.5 1.1v2h5v-2c0-.4.1-.8.5-1.1A6 6 0 0 0 12 3.5z",
    question: "M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 1 0 0-17M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6M12 16.8v.2",
    info: "M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 1 0 0-17M12 11v5.5M12 7.8v.2",
    warning: "M12 4l9 16H3zM12 10v4.5M12 17.3v.2",
    eye: "M2.5 12s3.5-6.5 9.5-6.5s9.5 6.5 9.5 6.5s-3.5 6.5-9.5 6.5S2.5 12 2.5 12zM12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6",
    leaf: "M5 19c0-8 5-13.5 14.5-14.5C19 14 13.5 19 5 19zM5 19l8-8",
    sun: "M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4",
    moon: "M19.5 14.5A8 8 0 1 1 9.5 4.5a6.5 6.5 0 0 0 10 10z",
    cloud: "M7 18.5a4 4 0 0 1-.5-8a5.5 5.5 0 0 1 10.5-1.5a4.5 4.5 0 0 1 .5 9.5z",
    drop: "M12 3.5c3 4 5.5 7 5.5 10a5.5 5.5 0 0 1-11 0c0-3 2.5-6 5.5-10z",
    fire: "M12 20.5a6 6 0 0 1-6-6c0-4 3-6 3.5-10c2.5 1.5 3.5 4 3.5 6c1-.5 1.5-1.5 1.5-2.5c2 1.5 3.5 4 3.5 6.5a6 6 0 0 1-6 6z",
    money: "M3.5 6.5h17v11h-17zM12 9.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 1 0 0-5M6.5 9.5v5M17.5 9.5v5",
    cart: "M3 4h2.5l2.5 11h10l2-8H6.5M9 18a1.3 1.3 0 1 0 0 2.6a1.3 1.3 0 1 0 0-2.6M17 18a1.3 1.3 0 1 0 0 2.6a1.3 1.3 0 1 0 0-2.6",
    gift: "M4 9.5h16v4H4zM5.5 13.5v7h13v-7M12 9.5v11M12 9.5c-1-3-5-4-5-1.5c0 1.5 3 1.5 5 1.5c2 0 5 0 5-1.5c0-2.5-4-1.5-5 1.5",
    trophy: "M7.5 4h9v5a4.5 4.5 0 0 1-9 0zM7.5 6H4.5c0 3 1.5 4.5 3.5 4.5M16.5 6h3c0 3-1.5 4.5-3.5 4.5M12 13.5v3.5M8.5 20.5h7M9.5 20.5l.5-3.5h4l.5 3.5",
    flag: "M5.5 21V4M5.5 4.5h12l-2.5 4l2.5 4h-12",
    pin: "M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11zM12 7.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 1 0 0-5",
    home: "M4 11l8-6.5l8 6.5M6 9.5v10h12v-10M10 19.5v-5h4v5",
    car: "M4 16.5v-4l2-5h12l2 5v4zM4 12.5h16M7 16.5v2M17 16.5v2",
    plane: "M12 3.5c1 0 1.5 1 1.5 2v4.5l7 4v2l-7-2v4l2 1.5v1.5l-3.5-1l-3.5 1v-1.5l2-1.5v-4l-7 2v-2l7-4V5.5c0-1 .5-2 1.5-2z",
    food: "M7 3.5v17M5 3.5v5a2 2 0 0 0 4 0v-5M16.5 20.5v-17c-2 1-3 3.5-3 6.5v3h3",
    cup: "M4.5 8.5h12v5a5 5 0 0 1-5 5h-2a5 5 0 0 1-5-5zM16.5 10h1.5a2.5 2.5 0 0 1 0 5h-2M8 3.5v2M11 3.5v2M14 3.5v2",
    music: "M9 17.5V5.5l10-2v12M9 17.5a2.5 2.5 0 1 1-5 0a2.5 2.5 0 1 1 5 0M19 15.5a2.5 2.5 0 1 1-5 0a2.5 2.5 0 1 1 5 0",
    camera: "M3.5 8h4l1.5-2.5h6L16.5 8h4v11h-17zM12 10.5a3.5 3.5 0 1 0 0 7a3.5 3.5 0 1 0 0-7",
    play: "M8 5.5v13l10.5-6.5z",
    phone: "M7.5 3.5h9v17h-9zM11 17.5h2",
    code: "M8.5 7.5L4 12l4.5 4.5M15.5 7.5L20 12l-4.5 4.5M13.5 5l-3 14",
    settings: "M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1",
    pencil: "M4.5 19.5l1-4.5L16 4.5l3.5 3.5L9 18.5zM13.5 7l3.5 3.5",
    file: "M6 3.5h8l4 4v13H6zM14 3.5v4h4M9 12.5h6M9 16h6",
    link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
    shield: "M12 3.5l7.5 3v5c0 4.5-3 8-7.5 9.5c-4.5-1.5-7.5-5-7.5-9.5v-5z",
    fitness: "M6.5 8v8M17.5 8v8M4 10v4M20 10v4M6.5 12h11",
    hourglass: "M6.5 3.5h11M6.5 20.5h11M7.5 3.5c0 5 9 5 9 8.5s-9 3.5-9 8.5M16.5 3.5c0 5-9 5-9 8.5s9 3.5 9 8.5",
  };
  /** An icon tile: rounded square in `color`, icon (or a short glyph) in its readable colour. */
  function iconTile(icon, x, y, size, color, what) {
    const o = onFill(col(color), what);
    let s = `<rect x="${f1(x - size / 2)}" y="${f1(y - size / 2)}" width="${f1(size)}" height="${f1(size)}" rx="${f1(size * 0.28)}" fill="${o.fill}"/>`;
    if (ICONS[icon]) {
      const k = (size * 0.56) / 24;
      s += `<path d="${ICONS[icon]}" transform="translate(${f1(x - 12 * k)} ${f1(y - 12 * k)}) scale(${k.toFixed(4)})" fill="none" stroke="${o.text}" stroke-width="${(2.2).toFixed(1)}" stroke-linecap="round" stroke-linejoin="round"/>`;
    } else if (icon != null) {
      s += `<text x="${f1(x)}" y="${f1(y + size * 0.16)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(size * 0.44)}" fill="${o.text}">${esc(String(icon).slice(0, 3))}</text>`;
    }
    return s;
  }
  /** A white UI card with a soft shadow; `lift` (0..1) raises it and deepens the shadow. */
  function uiCard(x, y, w, h, { lift = 0, radius = 36 * U, fill = "#fff", stroke = null } = {}) {
    const dy = -lift * 10 * U;
    return `<rect x="${f1(x - w / 2)}" y="${f1(y - h / 2 + (12 + lift * 14) * U)}" width="${f1(w)}" height="${f1(h)}" rx="${f1(radius)}" fill="${INK}" opacity="${(0.1 + lift * 0.06).toFixed(3)}"/>`
      + `<rect x="${f1(x - w / 2)}" y="${f1(y - h / 2 + dy)}" width="${f1(w)}" height="${f1(h)}" rx="${f1(radius)}" fill="${fill}"${stroke ? ` stroke="${stroke}" stroke-width="${f1(5 * U)}"` : ""}/>`;
  }
  const MUTED = readable(mix(INK, "#ffffff", 0.3), "#ffffff");
  /** Enter animation shared by the UI cards: up from below, a slight tilt that settles. */
  function enter(t, t0, k = 0) {
    const p = prog(t, t0, t0 + 0.36);
    return { p, e: outBack(p, 1.6), dy: (1 - outCubic(p)) * 110 * U, rot: (1 - outCubic(p)) * (k % 2 ? 5 : -5), op: clamp(p * 3) };
  }
  /** The item whose moment came last: the one the voice is talking about. */
  function activeIndex(times, t) { let a = -1; times.forEach((t0, k) => { if (t >= t0) a = k; }); return a; }

  /* ---- cards: feature cards, one by one; the one being talked about lifts. */
  SCENES.cards = {
    render(sc, t) {
      const items = sc.items ?? [], n = items.length;
      const hasTitle = (sc.lines ?? []).length > 0;
      titleLines(sc, t, { center: PORTRAIT ? H * 0.16 : H * 0.15 });
      const out = inBack(prog(t, sc.end - 0.24, sc.end));
      const times = items.map((it, k) => when(sc, it.at, 0.35 + k * 0.55));
      const act = activeIndex(times, t);
      const cols = PORTRAIT ? 1 : Math.min(n, sc.columns ?? (n <= 4 ? n : 3));
      const rows = Math.ceil(n / cols);
      const top = hasTitle ? (PORTRAIT ? H * 0.27 : H * 0.3) : H * 0.14, bottom = PORTRAIT ? H * 0.83 : H * 0.9;
      const gapX = 36 * U, gapY = 30 * U;
      const cw = PORTRAIT ? Math.min(W * 0.86, 940 * U) : (W * 0.88 - (cols - 1) * gapX) / cols;
      // Cards are as tall as their tallest content needs, and all the same height.
      const need = items.map((it) => {
        if (PORTRAIT || cols === 1) {
          const room = cw - 34 * U - Math.min(112 * U, 250 * U * 0.46) - 30 * U - 34 * U;
          const ti = wrap(it.title, 800, 54 * U, MIN_TEXT * U, room, 1), tb = it.text ? wrap(it.text, 500, 40 * U, MIN_TEXT * U, room, 2) : null;
          return Math.max(170 * U, 70 * U + ti.size + (tb ? 14 * U + tb.lines.length * tb.size * 1.2 : 0));
        }
        const room = cw - 80 * U, is = 110 * U;
        const ti = wrap(it.title, 800, 56 * U, MIN_TEXT * U, room, 2), tb = it.text ? wrap(it.text, 500, 40 * U, MIN_TEXT * U, room, 3) : null;
        return 40 * U + is + 34 * U + ti.lines.length * ti.size * 1.15 + (tb ? 6 * U + tb.lines.length * tb.size * 1.2 + 10 * U : 0) + 40 * U;
      });
      const avail = (bottom - top - (rows - 1) * gapY) / rows;
      const ch = Math.max(...need, 0) > avail ? avail : Math.max(Math.min(PORTRAIT ? 250 * U : 420 * U, avail), ...need);
      if (Math.max(...need, 0) > avail + 1) problem(`scene ${sc.key}: the cards' text does not fit; shorten titles and texts or use fewer cards.`);
      const blockH = rows * ch + (rows - 1) * gapY, y0 = (top + bottom) / 2 - blockH / 2;
      items.forEach((it, k) => {
        const en = enter(t, early(sc, times[k]), k);
        if (en.p <= 0) return;
        const r = Math.floor(k / cols), c = k % cols, inRow = Math.min(cols, n - r * cols);
        const x = CX + (c - (inRow - 1) / 2) * (cw + gapX), y = y0 + r * (ch + gapY) + ch / 2;
        safe(sc, y - ch / 2, y + ch / 2, `card "${it.title}"`);
        const lift = k === act ? outCubic(prog(t, times[k], times[k] + 0.3)) : 0;
        const color = it.color ?? sc.color ?? style.accent;
        let g = `<g opacity="${(en.op * (1 - out)).toFixed(3)}" transform="translate(0 ${f1(en.dy + out * H * 0.5)}) rotate(${en.rot.toFixed(2)} ${f1(x)} ${f1(y)})">`;
        g += uiCard(x, y, cw, ch, { lift, stroke: lift > 0.5 ? readable(col(color), "#ffffff") : null });
        const lift_dy = -lift * 10 * U;
        if (PORTRAIT || cols === 1) {
          const is = Math.min(ch * 0.46, 112 * U);
          g += iconTile(it.icon ?? String(k + 1), x - cw / 2 + 34 * U + is / 2, y + lift_dy, is, color, `scene ${sc.key}: card ${k + 1} icon`);
          const tx = x - cw / 2 + 34 * U + is + 30 * U, room = cw - (tx - (x - cw / 2)) - 34 * U;
          const ti = wrap(it.title, 800, 54 * U, MIN_TEXT * U, room, 1, `scene ${sc.key}: card ${k + 1} title`);
          const tb = it.text ? wrap(it.text, 500, 40 * U, MIN_TEXT * U, room, 2, `scene ${sc.key}: card ${k + 1} text`) : null;
          const hTot = ti.size + (tb ? 14 * U + tb.lines.length * tb.size * 1.2 : 0);
          const ty = y + lift_dy - hTot / 2 + ti.size * 0.8;
          g += textBlock(ti.lines, tx, ty, ti.size, 800, INK, { anchor: "start" });
          if (tb) g += textBlock(tb.lines, tx, ty + ti.size * 0.35 + 14 * U + tb.size, tb.size, 500, MUTED, { anchor: "start", lh: 1.2 });
        } else {
          const is = 110 * U;
          g += iconTile(it.icon ?? String(k + 1), x - cw / 2 + 40 * U + is / 2, y - ch / 2 + 40 * U + is / 2 + lift_dy, is, color, `scene ${sc.key}: card ${k + 1} icon`);
          const room = cw - 80 * U;
          const ti = wrap(it.title, 800, 56 * U, MIN_TEXT * U, room, 2, `scene ${sc.key}: card ${k + 1} title`);
          let ty = y - ch / 2 + 40 * U + is + 34 * U + ti.size * 0.8 + lift_dy;
          g += textBlock(ti.lines, x - cw / 2 + 40 * U, ty, ti.size, 800, INK, { anchor: "start", lh: 1.15 });
          if (it.text) {
            ty += ti.lines.length * ti.size * 1.15 + 6 * U;
            const tb = wrap(it.text, 500, 40 * U, MIN_TEXT * U, room, 3, `scene ${sc.key}: card ${k + 1} text`);
            g += textBlock(tb.lines, x - cw / 2 + 40 * U, ty + tb.size * 0.4, tb.size, 500, MUTED, { anchor: "start", lh: 1.2 });
          }
        }
        front += g + "</g>";
        if (lift > 0 && lift < 1) front += burst(t, times[k] + 0.05, x + cw / 2 - 30 * U, y - ch / 2, 700 + k * 17, [col(color), INK], 7, 90, 10 * U);
      });
    },
    cues(sc, add) {
      titleCues(sc, add);
      (sc.items ?? []).forEach((it, k) => { const t0 = when(sc, it.at, 0.35 + k * 0.55); add(t0 - 0.05, "swoosh", { gain: 0.5 }); add(t0 + 0.2, "pop", { pitch: 0.9 + k * 0.12, gain: 0.6 }); });
      add(sc.end - 0.35, "whoosh", { dur: 0.45, gain: 0.45 });
    },
  };

  /* ---- stats: metric cards; numbers count up, bars fill, a change chip pops. */
  const formatNumber = (v, it) => {
    const d = it.decimals ?? (Number.isInteger(it.value) ? 0 : 1);
    const locale = S.language === "fr" ? "fr-FR" : S.language ?? "en-US";
    return `${it.prefix ?? ""}${v.toLocaleString(locale, { minimumFractionDigits: d, maximumFractionDigits: d })}${it.suffix ?? ""}`;
  };
  SCENES.stats = {
    render(sc, t) {
      const items = sc.items ?? [], n = items.length;
      titleLines(sc, t, { center: PORTRAIT ? H * 0.16 : H * 0.15 });
      const out = inBack(prog(t, sc.end - 0.24, sc.end));
      const cols = sc.columns ?? (PORTRAIT ? (n === 1 ? 1 : 2) : Math.min(n, 4));
      const rows = Math.ceil(n / cols);
      const top = (sc.lines ?? []).length ? (PORTRAIT ? H * 0.28 : H * 0.3) : H * 0.15, bottom = PORTRAIT ? H * 0.8 : H * 0.88;
      const gap = 34 * U;
      const cw = (Math.min(W * 0.88, PORTRAIT ? 980 * U : W) - (cols - 1) * gap) / cols;
      const ch = Math.min(PORTRAIT ? 420 * U : 460 * U, (bottom - top - (rows - 1) * gap) / rows);
      const y0 = (top + bottom) / 2 - (rows * ch + (rows - 1) * gap) / 2;
      items.forEach((it, k) => {
        const t0 = early(sc, when(sc, it.at, 0.35 + k * 0.45));
        const en = enter(t, t0, k);
        if (en.p <= 0) return;
        const r = Math.floor(k / cols), c = k % cols, inRow = Math.min(cols, n - r * cols);
        const x = CX + (c - (inRow - 1) / 2) * (cw + gap), y = y0 + r * (ch + gap) + ch / 2;
        safe(sc, y - ch / 2, y + ch / 2, `stat "${it.label}"`);
        const color = col(it.color ?? sc.color ?? style.accent);
        const count = outCubic(prog(t, t0 + 0.1, t0 + 1.0));
        const valueText = formatNumber((it.from ?? 0) + (it.value - (it.from ?? 0)) * count, it);
        let g = `<g opacity="${(en.op * (1 - out)).toFixed(3)}" transform="translate(0 ${f1(en.dy + out * H * 0.5)}) rotate(${en.rot.toFixed(2)} ${f1(x)} ${f1(y)})">`;
        g += uiCard(x, y, cw, ch);
        const pad = 40 * U, left = x - cw / 2 + pad;
        if (it.icon) g += iconTile(it.icon, left + 40 * U, y - ch / 2 + pad + 40 * U, 80 * U, color, `scene ${sc.key}: stat ${k + 1} icon`);
        const finalText = formatNumber(it.value, it);
        const vs = Math.min(150 * U, ((cw - pad * 2) * 150 * U) / measure(finalText, 800, 150 * U));
        const vy = y - ch / 2 + pad + (it.icon ? 110 * U : 0) + vs * 0.85;
        g += `<text x="${f1(left)}" y="${f1(vy)}" font-family='${FONT}' font-weight="800" font-size="${f1(vs)}" fill="${readable(color, "#ffffff", `scene ${sc.key}: stat ${k + 1} number`)}">${esc(valueText)}</text>`;
        const lb = wrap(it.label, 600, 42 * U, MIN_TEXT * U, cw - pad * 2, 2, `scene ${sc.key}: stat ${k + 1} label`);
        g += textBlock(lb.lines, left, vy + 26 * U + lb.size, lb.size, 600, MUTED, { anchor: "start", lh: 1.2 });
        if (it.bar != null) {
          const frac = clamp(it.bar === true ? it.value / 100 : it.bar) * count;
          const by = y + ch / 2 - pad - 18 * U, bw = cw - pad * 2;
          g += `<rect x="${f1(left)}" y="${f1(by)}" width="${f1(bw)}" height="${f1(18 * U)}" rx="${f1(9 * U)}" fill="${INK}" opacity=".1"/>`;
          g += `<rect x="${f1(left)}" y="${f1(by)}" width="${f1(Math.max(18 * U, bw * frac))}" height="${f1(18 * U)}" rx="${f1(9 * U)}" fill="${color}"/>`;
        }
        if (it.delta) {
          const dp = outBack(prog(t, t0 + 0.9, t0 + 1.2), 2.2);
          if (dp > 0) g += pill(it.delta, x + cw / 2 - pad - measure(it.delta, 800, 36 * U) / 2 - 26 * U, y - ch / 2 + pad + 26 * U, { size: 36 * U, fill: col(it.deltaColor ?? "green"), scale: dp, what: `scene ${sc.key}: stat ${k + 1} delta` });
        }
        front += g + "</g>";
      });
    },
    cues(sc, add) {
      titleCues(sc, add);
      (sc.items ?? []).forEach((it, k) => {
        const t0 = when(sc, it.at, 0.35 + k * 0.45);
        add(t0 - 0.05, "swoosh", { gain: 0.45 });
        [0.25, 0.45, 0.65, 0.85].forEach((d, j) => add(t0 + d, "tick", { pitch: 1 + j * 0.15 + k * 0.05, gain: 0.35 }));
        add(t0 + 1.0, it.delta ? "coin" : "blip", { pitch: 1 + k * 0.08, gain: 0.45 });
      });
    },
  };

  /* ---- checklist: a to-do card; items get ticked off as they are said. */
  SCENES.checklist = {
    render(sc, t) {
      const items = sc.items ?? [], n = items.length;
      titleLines(sc, t, { center: PORTRAIT ? H * 0.15 : H * 0.14 });
      const out = inBack(prog(t, sc.end - 0.24, sc.end));
      const color = col(sc.color ?? style.accent);
      const cw = Math.min(W * 0.88, (PORTRAIT ? 960 : 1200) * U);
      const rowH = PORTRAIT ? 150 * U : 110 * U, head = 150 * U, foot = 100 * U;
      const ch = head + n * rowH + foot;
      const top = Math.max((sc.lines ?? []).length ? H * 0.26 : H * 0.12, (PORTRAIT ? H * 0.55 : H * 0.56) - ch / 2);
      safe(sc, top, top + ch, "the checklist");
      const en = enter(t, early(sc, sc.start));
      if (en.p <= 0) return;
      const x = CX, y = top + ch / 2;
      const times = items.map((it, k) => when(sc, it.at, 0.8 + k * 0.6));
      const done = times.filter((t0) => t >= t0 + 0.15).length;
      let g = `<g opacity="${(en.op * (1 - out)).toFixed(3)}" transform="translate(0 ${f1(en.dy + out * H * 0.5)})">`;
      g += uiCard(x, y, cw, ch);
      const left = x - cw / 2 + 44 * U;
      const title = sc.title ?? "";
      const hs = wrap(title, 800, 64 * U, MIN_TEXT * U, cw - 300 * U, 1, `scene ${sc.key}: checklist title`);
      g += textBlock(hs.lines, left, top + 96 * U, hs.size, 800, INK, { anchor: "start" });
      g += pill(`${done}/${n}`, x + cw / 2 - 44 * U - 64 * U, top + 76 * U, { size: 42 * U, fill: done === n ? col("green") : INK });
      g += `<rect x="${f1(left)}" y="${f1(top + head - 14 * U)}" width="${f1(cw - 88 * U)}" height="${f1(2 * U)}" fill="${INK}" opacity=".1"/>`;
      items.forEach((it, k) => {
        const ry = top + head + k * rowH + rowH / 2;
        const appear = prog(t, early(sc, sc.start + 0.2 + k * 0.08), early(sc, sc.start + 0.2 + k * 0.08) + 0.3);
        const tick = prog(t, times[k], times[k] + 0.3);
        const bs = 66 * U, bx = left + bs / 2;
        const ob = onFill(color, `scene ${sc.key}: checkbox`);
        g += `<g opacity="${clamp(appear * 2).toFixed(3)}" transform="translate(${f1((1 - outCubic(appear)) * 40 * U)} 0)">`;
        const pop = tick > 0 ? 1 + wobble(t - times[k], 0.25, 30, 9) : 1;
        g += `<g transform="translate(${f1(bx)} ${f1(ry)}) scale(${pop.toFixed(3)})">`;
        g += `<rect x="${f1(-bs / 2)}" y="${f1(-bs / 2)}" width="${f1(bs)}" height="${f1(bs)}" rx="${f1(16 * U)}" fill="${tick > 0 ? ob.fill : "#fff"}" stroke="${tick > 0 ? ob.fill : mix(INK, "#fff", 0.55)}" stroke-width="${f1(5 * U)}"/>`;
        if (tick > 0) {
          const k2 = (bs * 0.62) / 24;
          g += `<path d="${ICONS.check}" transform="translate(${f1(-12 * k2)} ${f1(-12 * k2)}) scale(${k2.toFixed(4)})" fill="none" stroke="${ob.text}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="24" stroke-dashoffset="${f1(24 * (1 - outCubic(tick)))}"/>`;
        }
        g += `</g>`;
        const tx = left + bs + 30 * U;
        const tw = wrap(it.text, 600, 56 * U, MIN_TEXT * U, cw - (tx - (x - cw / 2)) - 44 * U, 1, `scene ${sc.key}: item ${k + 1}`);
        g += textBlock(tw.lines, tx, ry + tw.size * 0.35, tw.size, 600, tick > 0.5 ? MUTED : INK, { anchor: "start" });
        if (tick > 0) g += `<rect x="${f1(tx)}" y="${f1(ry - 2 * U)}" width="${f1(measure(tw.lines[0], 600, tw.size) * outCubic(prog(t, times[k] + 0.1, times[k] + 0.4)))}" height="${f1(4 * U)}" rx="${f1(2 * U)}" fill="${MUTED}"/>`;
        g += `</g>`;
      });
      const by = top + ch - foot / 2, bw = cw - 88 * U;
      const frac = n ? done / n : 0;
      g += `<rect x="${f1(left)}" y="${f1(by - 9 * U)}" width="${f1(bw)}" height="${f1(18 * U)}" rx="${f1(9 * U)}" fill="${INK}" opacity=".1"/>`;
      g += `<rect x="${f1(left)}" y="${f1(by - 9 * U)}" width="${f1(Math.max(18 * U, bw * frac))}" height="${f1(18 * U)}" rx="${f1(9 * U)}" fill="${color}"/>`;
      front += g + "</g>";
      if (done === n && n) front += burst(t, times[n - 1] + 0.2, x + cw / 2 - 104 * U, top + 66 * U, 820, CONFETTI, 16, 260, 30 * U);
    },
    cues(sc, add) {
      titleCues(sc, add);
      add(sc.start + 0.1, "swoosh", { gain: 0.45 });
      const items = sc.items ?? [];
      items.forEach((it, k) => { const t0 = when(sc, it.at, 0.8 + k * 0.6); add(t0, "click", { gain: 0.6 }); add(t0 + 0.05, "blip", { pitch: 1 + k * 0.12, gain: 0.45 }); });
      if (items.length) add(when(sc, items[items.length - 1].at, 0.8 + (items.length - 1) * 0.6) + 0.25, "chime", { gain: 0.6 });
    },
  };

  /* ---- compare: a "before" card, then an "after" card that wins. */
  SCENES.compare = {
    render(sc, t) {
      titleLines(sc, t, { center: PORTRAIT ? H * 0.14 : H * 0.14 });
      const out = inBack(prog(t, sc.end - 0.24, sc.end));
      const sides = [sc.before ?? {}, sc.after ?? {}];
      const good = col(sc.color ?? style.accent), bad = col(sc.badColor ?? "slate");
      const cw = PORTRAIT ? Math.min(W * 0.88, 960 * U) : W * 0.42;
      const rowH = (PORTRAIT ? 104 : 90) * U, head = 130 * U;
      const hs = sides.map((sd) => head + (sd.items ?? []).length * rowH + 40 * U);
      const top = (sc.lines ?? []).length ? (PORTRAIT ? H * 0.23 : H * 0.28) : H * 0.12;
      const bottom = PORTRAIT ? H * 0.84 : H * 0.9;
      sides.forEach((sd, k) => {
        const t0 = early(sc, when(sc, sd.at, 0.3 + k * 1.2));
        const en = enter(t, t0, k);
        if (en.p <= 0) return;
        const ch = hs[k];
        let x, y;
        if (PORTRAIT) { const tot = hs[0] + hs[1] + 40 * U; const y0 = (top + bottom) / 2 - tot / 2; x = CX; y = k === 0 ? y0 + hs[0] / 2 : y0 + hs[0] + 40 * U + hs[1] / 2; }
        else { x = CX + (k === 0 ? -1 : 1) * (cw / 2 + 24 * U); y = (top + bottom) / 2; }
        safe(sc, y - ch / 2, y + ch / 2, k === 0 ? "the before card" : "the after card");
        const winner = k === 1;
        const settle = winner ? 0 : outCubic(prog(t, when(sc, sides[1].at, 1.5), when(sc, sides[1].at, 1.5) + 0.4));
        const c = winner ? good : bad;
        let g = `<g opacity="${(en.op * (1 - out)).toFixed(3)}" transform="translate(0 ${f1(en.dy + out * H * 0.5)}) rotate(${(en.rot - settle * 2).toFixed(2)} ${f1(x)} ${f1(y)}) translate(${f1(x)} ${f1(y)}) scale(${(1 - settle * 0.04).toFixed(3)}) translate(${f1(-x)} ${f1(-y)})">`;
        g += uiCard(x, y, cw, ch, { stroke: winner ? readable(good, "#ffffff") : null, fill: winner ? "#fff" : mix("#ffffff", PAPER, 0.5) });
        const left = x - cw / 2 + 40 * U, tp = y - ch / 2;
        const label = sd.title ?? (winner ? "After" : "Before");
        g += pill(label, left + measure(label, 800, 44 * U) / 2 + 32 * U, tp + 70 * U, { size: 44 * U, fill: c, what: `scene ${sc.key}: ${winner ? "after" : "before"} title` });
        (sd.items ?? []).forEach((txt, j) => {
          const it0 = t0 + 0.25 + j * 0.12;
          const ip = prog(t, it0, it0 + 0.25);
          if (ip <= 0) return;
          const ry = tp + head + j * rowH + rowH / 2;
          g += `<g opacity="${clamp(ip * 2).toFixed(3)}">` + iconTile(winner ? "check" : "x", left + 30 * U, ry, 60 * U, c);
          const tw = wrap(txt, 600, 52 * U, MIN_TEXT * U, cw - 160 * U, 1, `scene ${sc.key}: ${winner ? "after" : "before"} item ${j + 1}`);
          g += textBlock(tw.lines, left + 84 * U, ry + tw.size * 0.35, tw.size, 600, winner ? INK : MUTED, { anchor: "start" }) + `</g>`;
        });
        front += g + "</g>";
        if (winner) front += burst(t, t0 + 0.3, x + cw / 2 - 40 * U, y - ch / 2, 910, CONFETTI, 16, 220, 20 * U);
      });
    },
    cues(sc, add) {
      titleCues(sc, add);
      add(when(sc, sc.before?.at, 0.3) - 0.05, "swoosh", { gain: 0.45 });
      add(when(sc, sc.before?.at, 0.3) + 0.4, "error", { gain: 0.35 });
      add(when(sc, sc.after?.at, 1.5) - 0.05, "whoosh", { dur: 0.35, gain: 0.5 });
      add(when(sc, sc.after?.at, 1.5) + 0.3, "chime", { gain: 0.55 });
    },
  };

  /* ---- prompt: a tip card: number, title, and the prompt to copy, typed out. */
  SCENES.prompt = {
    render(sc, t) {
      const u = t - sc.start;
      const out = inBack(prog(t, sc.end - 0.24, sc.end));
      const c = col(sc.color ?? style.accent);
      const pw = Math.min(W * 0.88, (PORTRAIT ? 960 : 1400) * U);
      const en = enter(t, early(sc, sc.start));
      if (en.p <= 0) return;
      // Measure the block (number, title, panel, caption), then centre it in the frame.
      const psize = (PORTRAIT ? 56 : 50) * U;
      const tiM = sc.title ? wrap(sc.title, 800, 110 * U, 64 * U, pw, 2) : null;
      const pwr = wrap(sc.prompt, 600, psize, MIN_TEXT * U, pw - 72 * U, 8);
      const capM = sc.caption ? wrap(sc.caption, 600, 50 * U, MIN_TEXT * U, pw, 2) : null;
      const blockH = (sc.number !== false ? 80 * U : 0) + (tiM ? tiM.lines.length * tiM.size * 1.05 + 40 * U : 0)
        + 72 * U + 56 * U + pwr.lines.length * pwr.size * 1.3 + (capM ? 50 * U + capM.lines.length * capM.size * 1.25 : 0);
      let y = Math.max(PORTRAIT ? H * 0.1 : H * 0.08, H * 0.5 - blockH / 2);
      let g = `<g opacity="${(en.op * (1 - out)).toFixed(3)}" transform="translate(0 ${f1(en.dy + out * H * 0.5)})">`;
      if (sc.number !== false) {
        const num = typeof sc.number === "string" ? sc.number : `${labels.number} ${String(scenes.filter((x) => x.type === "prompt").indexOf(sc) + 1).padStart(2, "0")}`;
        g += pill(num, CX - pw / 2 + measure(num, 800, 40 * U) / 2 + 30 * U, y, { size: 40 * U, fill: INK, rot: -4 });
        y += 80 * U;
      }
      if (sc.title) {
        const ti = wrap(sc.title, 800, 110 * U, 64 * U, pw, 2, `scene ${sc.key}: title`);
        g += textBlock(ti.lines, CX - pw / 2, y + ti.size * 0.85, ti.size, 800, INK, { anchor: "start", lh: 1.05 });
        y += ti.lines.length * ti.size * 1.05 + 40 * U;
      }
      front += g + "</g>";
      const bottomLimit = PORTRAIT ? (sc.caption ? H * 0.76 : H * 0.84) : H * 0.84;
      const gy = drawPromptPanel(sc, t, u, c, { x: CX, pw, top: y, bottomLimit, size: psize }, out);
      if (sc.caption) {
        const cp = prog(u, promptStart(sc) + promptTypeTime(sc), promptStart(sc) + promptTypeTime(sc) + 0.35) * (1 - out);
        const cap = wrap(sc.caption, 600, 50 * U, MIN_TEXT * U, pw, 2, `scene ${sc.key}: caption`);
        safe(sc, gy + 40 * U, gy + 60 * U + cap.lines.length * cap.size * 1.25, "the caption");
        front += `<g transform="translate(0 ${f1((1 - outCubic(cp)) * 30 * U)})">${textBlock(cap.lines, CX - pw / 2, gy + 50 * U + cap.size, cap.size, 600, readable(mix(INK, BG, 0.2), BG), { anchor: "start", op: clamp(cp * 2), lh: 1.25 })}</g>`;
      }
    },
    cues(sc, add) {
      add(sc.start + 0.05, "swoosh", { gain: 0.45 });
      add(sc.start + promptStart(sc), "typing", { dur: promptTypeTime(sc), gain: 0.5 });
      add(sc.start + promptStart(sc) + promptTypeTime(sc), "pop", { pitch: 1.2, gain: 0.45 });
    },
  };

  /* ---------------------------------------------------------------- more UI cards, for any topic */
  /** The room under a scene's heading lines. */
  function bodyArea(sc) {
    const head = (sc.lines ?? []).length > 0;
    return { top: head ? (PORTRAIT ? H * 0.27 : H * 0.3) : PORTRAIT ? H * 0.12 : H * 0.1, bottom: PORTRAIT ? H * 0.83 : H * 0.9 };
  }
  const HEAD = () => ({ center: PORTRAIT ? H * 0.16 : H * 0.15 });
  const sceneOut = (sc, t) => inBack(prog(t, sc.end - 0.24, sc.end));
  const wideCard = () => Math.min(W * 0.88, (PORTRAIT ? 960 : 1500) * U);
  /** Opens a group carrying a card's enter and exit motion. */
  const cardGroup = (en, out, x, y, rot = true) => `<g opacity="${(en.op * (1 - out)).toFixed(3)}" transform="translate(0 ${f1(en.dy + out * H * 0.5)})${rot ? ` rotate(${en.rot.toFixed(2)} ${f1(x)} ${f1(y)})` : ""}">`;
  /** Top of a block of height h centred in the room; a problem when it does not fit. */
  function place(sc, h, what, area = bodyArea(sc)) {
    if (h > area.bottom - area.top + 1) problem(`scene ${sc.key}: ${what} is too tall for the frame; shorten its text or use fewer items.`);
    const y0 = Math.max(area.top, (area.top + area.bottom) / 2 - h / 2);
    safe(sc, y0, y0 + h, what);
    return y0;
  }
  /** When each word is said: from the voice when it reads these words, else at a steady pace from t0 over dur. */
  function wordTimes(sc, words, t0, dur) {
    const n = words.length, at = new Array(n).fill(null);
    if (sc.v) {
      const vw = sc.v.words;
      let j = 0;
      words.forEach((w, i) => {
        const nw = norm(w);
        if (!nw) return;
        // The first word may come after an introduction ("As the proverb says: …"); later words follow closely.
          for (let k = j; k < Math.min(vw.length, at.some((v) => v != null) ? j + 4 : vw.length); k++) {
          if (norm(vw[k].w) === nw) { at[i] = sc.start + sc.voiceAt + vw[k].start - sc.v.speechStart; j = k + 1; break; }
        }
      });
    }
    const known = at.map((v, i) => (v == null ? null : i)).filter((i) => i != null);
    return at.map((v, i) => {
      let r = v;
      if (r == null) {
        const a = [...known].reverse().find((k) => k < i), b = known.find((k) => k > i);
        if (a != null && b != null) r = lerp(at[a], at[b], (i - a) / (b - a));
        else if (a != null) r = at[a] + (i - a) * 0.22;
        else if (b != null) r = at[b] - (b - i) * 0.22;
        else r = t0 + (dur * i) / Math.max(1, n);
      }
      return Math.max(t0, r);
    });
  }
  /** Lines revealed word by word at `times`; words starting like one in `hl` get a highlighter band. */
  function wordsBlock(lines, x, yFirst, size, weight, fill, t, times, { lh = 1.22, hl = [], band = null } = {}) {
    let s = "", k = 0;
    const space = measure(" ", weight, size);
    lines.forEach((line, li) => {
      const y = yFirst + li * size * lh;
      let cx = x;
      for (const w of line.split(" ")) {
        const ww = measure(w, weight, size), tw = times[k] ?? 0;
        const p = prog(t, tw, tw + 0.22);
        if (p > 0) {
          if (band && hl.some((h) => norm(h) && norm(w).startsWith(norm(h)))) s += marker(cx, ww, y, size, band, outCubic(prog(t, tw + 0.08, tw + 0.4)), 0);
          s += `<text x="${f1(cx)}" y="${f1(y + (1 - outCubic(p)) * 18 * U)}" font-family='${FONT}' font-weight="${weight}" font-size="${f1(size)}" fill="${fill}" opacity="${clamp(p * 1.5).toFixed(3)}">${esc(w)}</text>`;
        }
        cx += ww + space;
        k++;
      }
    });
    return s;
  }
  const splitWords = (s) => String(s ?? "").split(/\s+/).filter(Boolean);
  const initialsOf = (name) => splitWords(name).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const fmtOf = (sc) => (v, it) => formatNumber(v, { prefix: sc.prefix, suffix: sc.suffix, decimals: sc.decimals, ...it });
  /** Colours for data: the item's own, the accent (dimmed when another item is highlighted), or the palette in turn. */
  function dataColors(sc, items, cycle) {
    const c = col(sc.color ?? style.accent);
    const hl = items.some((it) => it.highlight);
    const pal = [c, ...Object.keys(PALETTE).map((k) => col(k)).filter((v) => v !== c)];
    return items.map((it, k) => (it.color ? col(it.color) : cycle ? pal[k % pal.length] : hl && !it.highlight ? mix(c, "#ffffff", 0.55) : c));
  }

  /* ---- quote: a quote card; words appear as they are said, key words get a highlighter. */
  function quoteTiming(sc) {
    const words = splitWords(sc.text);
    const t0 = early(sc, when(sc, sc.at, 0.2));
    const r0 = Math.max(t0 + 0.2, sc.textAt != null ? when(sc, sc.textAt) : sc.v ? sc.start + sc.voiceAt : t0 + 0.35);
    const dur = sc.v ? Math.max(0.6, sc.start + sc.voiceAt + sc.speech - r0) : Math.min(2.4, words.length * 0.12);
    const times = wordTimes(sc, words, r0, dur);
    return { t0, words, times, done: Math.max(t0 + 0.4, ...times) };
  }
  SCENES.quote = {
    render(sc, t) {
      titleLines(sc, t, HEAD());
      const out = sceneOut(sc, t), c = col(sc.color ?? style.accent);
      const cw = wideCard(), pad = 56 * U, left = CX - cw / 2 + pad;
      const qs = wrap(sc.text ?? "", 700, (PORTRAIT ? 74 : 68) * U, MIN_TEXT * U, cw - pad * 2, PORTRAIT ? 8 : 5, `scene ${sc.key}: quote`);
      const markSize = 200 * U, markH = 96 * U, lh = 1.24, d = 100 * U;
      const authorH = sc.author ? 30 * U + d + 30 * U : 0;
      const ch = pad + markH + (qs.lines.length - 1) * qs.size * lh + qs.size * 1.1 + authorH + pad * 0.7;
      const y0 = place(sc, ch, "the quote card"), y = y0 + ch / 2;
      const { t0, times, done } = quoteTiming(sc);
      const en = enter(t, t0);
      if (en.p <= 0) return;
      let g = cardGroup(en, out, CX, y) + uiCard(CX, y, cw, ch);
      g += `<text x="${f1(left - 8 * U)}" y="${f1(y0 + pad + markSize * 0.72)}" font-family='${FONT}' font-weight="900" font-size="${f1(markSize)}" fill="${readable(c, "#ffffff", `scene ${sc.key}: quote mark`)}">“</text>`;
      const ty = y0 + pad + markH + qs.size * 0.85;
      g += wordsBlock(qs.lines, left, ty, qs.size, 700, INK, t, times, { lh, hl: sc.highlight ?? [], band: mix(c, "#ffffff", 0.6) });
      if (sc.author) {
        const at = when(sc, sc.authorAt, done - sc.start + 0.2);
        const ap = prog(t, at, at + 0.35);
        const yA = ty + (qs.lines.length - 1) * qs.size * lh + qs.size * 0.25 + 30 * U, cy = yA + 30 * U + d / 2;
        const room = cw - pad * 2 - d - 30 * U, nx = left + d + 30 * U;
        const nm = wrap(sc.author, 800, 50 * U, MIN_TEXT * U, room, 1, `scene ${sc.key}: author`);
        const rl = sc.role ? wrap(sc.role, 500, 40 * U, MIN_TEXT * U, room, 1, `scene ${sc.key}: author role`) : null;
        if (ap > 0) {
          const o = onFill(c, `scene ${sc.key}: author initials`);
          g += `<g opacity="${clamp(ap * 2).toFixed(3)}" transform="translate(${f1((1 - outCubic(ap)) * 40 * U)} 0)">`;
          g += `<rect x="${f1(left)}" y="${f1(yA)}" width="${f1(cw - pad * 2)}" height="${f1(2 * U)}" fill="${INK}" opacity=".1"/>`;
          g += `<circle cx="${f1(left + d / 2)}" cy="${f1(cy)}" r="${f1(d / 2)}" fill="${o.fill}"/>`;
          g += `<text x="${f1(left + d / 2)}" y="${f1(cy + d * 0.14)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(d * 0.4)}" fill="${o.text}">${esc(sc.initials ?? initialsOf(sc.author))}</text>`;
          const ny = rl ? cy - 6 * U : cy + nm.size * 0.35;
          g += textBlock(nm.lines, nx, ny, nm.size, 800, INK, { anchor: "start" });
          if (rl) g += textBlock(rl.lines, nx, ny + rl.size * 1.25, rl.size, 500, MUTED, { anchor: "start" });
          g += "</g>";
        }
      }
      front += g + "</g>";
    },
    cues(sc, add) {
      titleCues(sc, add);
      const { t0, words, times, done } = quoteTiming(sc);
      add(t0 - 0.05, "swoosh", { gain: 0.45 });
      const hl = sc.highlight ?? [];
      words.forEach((w, k) => { if (hl.some((h) => norm(h) && norm(w).startsWith(norm(h)))) add(times[k] + 0.1, "blip", { pitch: 1.2, gain: 0.35 }); });
      if (sc.author) add(when(sc, sc.authorAt, done - sc.start + 0.2), "pop", { pitch: 1.1, gain: 0.45 });
    },
  };

  /* ---- timeline: dates or steps on a line that draws itself; each stop lights up on its word. */
  const stopTimes = (sc) => (sc.items ?? []).map((it, k) => early(sc, when(sc, it.at, 0.45 + k * 0.7)));
  SCENES.timeline = {
    render(sc, t) {
      titleLines(sc, t, HEAD());
      const out = sceneOut(sc, t);
      const items = sc.items ?? [], n = items.length;
      if (!n) return;
      const cw = wideCard(), pad = 48 * U, cl = CX - cw / 2;
      const times = stopTimes(sc);
      const colors = items.map((it) => col(it.color ?? sc.color ?? style.accent));
      const vertical = PORTRAIT || sc.vertical;
      const rows = [], nodes = [];
      let ch;
      if (vertical) {
        const railX = cl + pad + 26 * U, tx = railX + 62 * U, room = cl + cw - pad - tx, gap = 44 * U;
        items.forEach((it, k) => {
          const lb = wrap(it.label ?? "", 800, 42 * U, MIN_TEXT * U, room, 1, `scene ${sc.key}: stop ${k + 1} label`);
          const ti = it.title ? wrap(it.title, 800, 54 * U, MIN_TEXT * U, room, 2, `scene ${sc.key}: stop ${k + 1} title`) : null;
          const tb = it.text ? wrap(it.text, 500, 40 * U, MIN_TEXT * U, room, 2, `scene ${sc.key}: stop ${k + 1} text`) : null;
          rows.push({ lb, ti, tb, x: tx, anchor: "start", h: lb.size + (ti ? 16 * U + ti.lines.length * ti.size * 1.15 : 0) + (tb ? 12 * U + tb.lines.length * tb.size * 1.2 : 0) });
        });
        ch = pad * 2 + rows.reduce((a, r) => a + r.h, 0) + gap * (n - 1);
        const y0 = place(sc, ch, "the timeline");
        let yy = y0 + pad;
        rows.forEach((r) => { r.top = yy; nodes.push({ x: railX, y: yy + r.lb.size * 0.42 }); yy += r.h + gap; });
      } else {
        const colW = (cw - pad * 2) / n, room = colW - 28 * U;
        items.forEach((it, k) => {
          const lb = wrap(it.label ?? "", 800, 46 * U, MIN_TEXT * U, room, 1, `scene ${sc.key}: stop ${k + 1} label`);
          const ti = it.title ? wrap(it.title, 800, 50 * U, MIN_TEXT * U, room, 3, `scene ${sc.key}: stop ${k + 1} title`) : null;
          const tb = it.text ? wrap(it.text, 500, 40 * U, MIN_TEXT * U, room, 3, `scene ${sc.key}: stop ${k + 1} text`) : null;
          rows.push({ lb, ti, tb, x: cl + pad + colW * (k + 0.5), anchor: "middle", h: lb.size + (ti ? 16 * U + ti.lines.length * ti.size * 1.15 : 0) + (tb ? 12 * U + tb.lines.length * tb.size * 1.2 : 0) });
        });
        ch = pad + 60 * U + 50 * U + Math.max(...rows.map((r) => r.h)) + pad;
        const y0 = place(sc, ch, "the timeline");
        rows.forEach((r) => { r.top = y0 + pad + 110 * U; nodes.push({ x: r.x, y: y0 + pad + 30 * U }); });
      }
      const y = (vertical ? rows[0].top - pad : nodes[0].y - pad - 30 * U) + ch / 2;
      const en = enter(t, early(sc, sc.start));
      if (en.p <= 0) return;
      let g = cardGroup(en, out, CX, y) + uiCard(CX, y, cw, ch);
      // The rail, and the part already travelled.
      const a = nodes[0], b = nodes[n - 1];
      let tip = 0;
      for (let k = 1; k < n; k++) tip += outCubic(prog(t, times[k] - 0.35, times[k]));
      const along = (f) => { const k = Math.min(n - 2, Math.floor(f)), r = f - k; return n < 2 ? a : { x: lerp(nodes[k].x, nodes[k + 1].x, r), y: lerp(nodes[k].y, nodes[k + 1].y, r) }; };
      const tp = along(tip);
      g += `<line x1="${f1(a.x)}" y1="${f1(a.y)}" x2="${f1(b.x)}" y2="${f1(b.y)}" stroke="${INK}" stroke-opacity=".12" stroke-width="${f1(8 * U)}" stroke-linecap="round"/>`;
      if (t >= times[0]) g += `<line x1="${f1(a.x)}" y1="${f1(a.y)}" x2="${f1(tp.x)}" y2="${f1(tp.y)}" stroke="${colors[Math.min(n - 1, Math.floor(tip))]}" stroke-width="${f1(8 * U)}" stroke-linecap="round"/>`;
      items.forEach((it, k) => {
        const nd = nodes[k], r = rows[k], reached = prog(t, times[k], times[k] + 0.3);
        const o = onFill(colors[k], `scene ${sc.key}: stop ${k + 1} node`);
        const pop = reached > 0 ? 1 + wobble(t - times[k], 0.3, 28, 8) : 1;
        g += `<circle cx="${f1(nd.x)}" cy="${f1(nd.y)}" r="${f1(24 * U * pop)}" fill="${reached > 0 ? o.fill : "#fff"}" stroke="${reached > 0 ? o.fill : mix(INK, "#ffffff", 0.6)}" stroke-width="${f1(6 * U)}"/>`;
        if (reached > 0 && reached < 1) g += `<circle cx="${f1(nd.x)}" cy="${f1(nd.y)}" r="${f1(24 * U + reached * 40 * U)}" fill="none" stroke="${o.fill}" stroke-width="${f1(4 * U)}" opacity="${(1 - reached).toFixed(3)}"/>`;
        if (reached <= 0) return;
        const shift = (1 - outCubic(reached)) * 30 * U;
        g += `<g opacity="${clamp(reached * 2).toFixed(3)}" transform="translate(${f1(vertical ? shift : 0)} ${f1(vertical ? 0 : shift)})">`;
        let yy = r.top + r.lb.size * 0.8;
        g += textBlock(r.lb.lines, r.x, yy, r.lb.size, 800, readable(colors[k], "#ffffff", `scene ${sc.key}: stop ${k + 1} label`), { anchor: r.anchor });
        yy += r.lb.size * 0.2;
        if (r.ti) { yy += 16 * U + r.ti.size * 0.85; g += textBlock(r.ti.lines, r.x, yy, r.ti.size, 800, INK, { anchor: r.anchor, lh: 1.15 }); yy += (r.ti.lines.length - 1) * r.ti.size * 1.15 + r.ti.size * 0.3; }
        if (r.tb) { yy += 12 * U + r.tb.size * 0.85; g += textBlock(r.tb.lines, r.x, yy, r.tb.size, 500, MUTED, { anchor: r.anchor, lh: 1.2 }); }
        g += "</g>";
      });
      front += g + "</g>";
    },
    cues(sc, add) {
      titleCues(sc, add);
      add(early(sc, sc.start) + 0.02, "swoosh", { gain: 0.45 });
      stopTimes(sc).forEach((t0, k) => { add(t0, "pop", { pitch: 0.9 + k * 0.12, gain: 0.55 }); add(t0 + 0.04, "tick", { pitch: 1.2, gain: 0.3 }); });
    },
  };

  /* ---- chart: a bar, line or donut chart that builds itself. */
  const chartStart = (sc) => early(sc, when(sc, sc.at, 0.35));
  const chartTimes = (sc) => (sc.items ?? []).map((it, k) => (it.at != null ? when(sc, it.at) : chartStart(sc) + k * (sc.kind === "donut" ? 0.2 : 0.15)));
  function drawBars(sc, t, plot, items, colors, times, fmt) {
    const n = items.length, slot = plot.w / n, bw = Math.min(slot * 0.62, 170 * U);
    const labs = items.map((it, k) => wrap(it.label ?? "", 600, 42 * U, MIN_TEXT * U, slot * 0.94, 2, `scene ${sc.key}: bar ${k + 1} label`));
    const labH = Math.max(...labs.map((l) => l.lines.length * l.size * 1.15)) + 24 * U;
    const base = plot.y + plot.h - labH, valH = 70 * U, maxH = base - plot.y - valH;
    const vmax = sc.max ?? (Math.max(...items.map((it) => it.value), 0) || 1);
    let s = `<rect x="${f1(plot.x)}" y="${f1(base)}" width="${f1(plot.w)}" height="${f1(3 * U)}" fill="${INK}" opacity=".18"/>`;
    items.forEach((it, k) => {
      const x = plot.x + slot * (k + 0.5);
      const gp = outCubic(prog(t, times[k], times[k] + 0.7));
      const h = Math.max(0, it.value / vmax) * maxH * gp, r = Math.min(18 * U, bw / 4, h / 2);
      if (h > 0.5) s += `<path d="M${f1(x - bw / 2)} ${f1(base)}V${f1(base - h + r)}Q${f1(x - bw / 2)} ${f1(base - h)} ${f1(x - bw / 2 + r)} ${f1(base - h)}H${f1(x + bw / 2 - r)}Q${f1(x + bw / 2)} ${f1(base - h)} ${f1(x + bw / 2)} ${f1(base - h + r)}V${f1(base)}Z" fill="${colors[k]}"/>`;
      const fin = fmt(it.value, it), L = fit(fin, 800, 48 * U, slot * 0.96, 0, MIN_TEXT * U, `scene ${sc.key}: bar ${k + 1} value`);
      if (gp > 0) s += `<text x="${f1(x)}" y="${f1(base - h - 18 * U)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(L.size)}" fill="${it.highlight ? readable(colors[k], "#ffffff", `scene ${sc.key}: bar ${k + 1} value`) : INK}" opacity="${clamp(gp * 3).toFixed(3)}">${esc(fmt(it.value * gp, it))}</text>`;
      s += textBlock(labs[k].lines, x, base + 24 * U + labs[k].size * 0.8, labs[k].size, 600, INK, { lh: 1.15, op: clamp(prog(t, times[k] - 0.2, times[k] + 0.1)) });
    });
    return s;
  }
  function drawLine(sc, t, plot, items, color, fmt) {
    const n = items.length, slot = plot.w / n;
    const labs = items.map((it, k) => wrap(it.label ?? "", 600, 42 * U, MIN_TEXT * U, slot * 0.98, 2, `scene ${sc.key}: point ${k + 1} label`));
    const labH = Math.max(...labs.map((l) => l.lines.length * l.size * 1.15)) + 24 * U;
    const base = plot.y + plot.h - labH, top = plot.y + 90 * U;
    const vals = items.map((it) => it.value);
    const vmin = sc.min ?? Math.min(0, ...vals), vmax = sc.max ?? Math.max(...vals);
    const pts = items.map((it, k) => ({ x: plot.x + slot * (k + 0.5), y: base - ((it.value - vmin) / (vmax - vmin || 1)) * (base - top) }));
    const seg = pts.slice(1).map((p, k) => Math.hypot(p.x - pts[k].x, p.y - pts[k].y));
    const total = seg.reduce((a, b) => a + b, 0) || 1;
    const t0 = chartStart(sc), dur = Math.max(0.9, 0.3 * n);
    const lp = prog(t, t0, t0 + dur);
    let s = "";
    [0, 0.5, 1].forEach((f) => { s += `<rect x="${f1(plot.x)}" y="${f1(lerp(base, top, f))}" width="${f1(plot.w)}" height="${f1(2 * U)}" fill="${INK}" opacity="${f === 0 ? ".18" : ".07"}"/>`; });
    const d = pts.map((p, k) => `${k ? "L" : "M"}${f1(p.x)} ${f1(p.y)}`).join("");
    s += `<path d="${d}L${f1(pts[n - 1].x)} ${f1(base)}L${f1(pts[0].x)} ${f1(base)}Z" fill="${color}" opacity="${(0.14 * prog(t, t0 + dur * 0.6, t0 + dur + 0.3)).toFixed(3)}"/>`;
    if (lp > 0) s += `<path d="${d}" fill="none" stroke="${color}" stroke-width="${f1(10 * U)}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="${f1(total)}" stroke-dashoffset="${f1(total * (1 - lp))}"/>`;
    const hl = items.some((it) => it.highlight);
    let acc = 0;
    pts.forEach((p, k) => {
      const reach = t0 + dur * (acc / total);
      acc += seg[k] ?? 0;
      const pp = outBack(prog(t, reach, reach + 0.25), 2.4);
      if (pp > 0) s += `<circle cx="${f1(p.x)}" cy="${f1(p.y)}" r="${f1(14 * U * pp)}" fill="#fff" stroke="${color}" stroke-width="${f1(7 * U)}"/>`;
      s += textBlock(labs[k].lines, p.x, base + 24 * U + labs[k].size * 0.8, labs[k].size, 600, INK, { lh: 1.15 });
      const show = hl ? items[k].highlight : k === n - 1;
      if (show && pp > 0) s += pill(fmt(items[k].value, items[k]), p.x, p.y - 62 * U, { size: 40 * U, fill: color, scale: clamp(pp, 0, 1.2), what: `scene ${sc.key}: point ${k + 1} value` });
    });
    return s;
  }
  function drawDonut(sc, t, plot, items, colors, times, fmt) {
    const n = items.length, rowH = 72 * U;
    let R, cx, cy, lx, ly, lw;
    if (PORTRAIT) {
      R = Math.min(plot.w * 0.36, (plot.h - n * rowH - 40 * U) / 2);
      cx = CX; cy = plot.y + R + 6 * U; lx = plot.x; ly = cy + R + 50 * U; lw = plot.w;
    } else {
      R = Math.min(plot.h * 0.46, plot.w * 0.22);
      cx = plot.x + R + 20 * U; cy = plot.y + plot.h / 2; lx = cx + R + 90 * U; lw = plot.x + plot.w - lx; ly = cy - (n * rowH) / 2;
    }
    if (R < 150 * U) problem(`scene ${sc.key}: the donut is too small; use fewer items or a shorter title.`);
    const thick = R * 0.34, rr = R - thick / 2, C = TAU * rr;
    const total = items.reduce((a, it) => a + Math.max(0, it.value), 0) || 1;
    const t0 = chartStart(sc), sp = inOutCubic(prog(t, t0, t0 + 1.1));
    let s = `<circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(rr)}" fill="none" stroke="${INK}" stroke-opacity=".07" stroke-width="${f1(thick)}"/>`;
    let f0 = 0;
    items.forEach((it, k) => {
      const f = Math.max(0, it.value) / total;
      const len = C * clamp(sp - f0, 0, f) - (sp - f0 > f - 0.001 ? 5 * U : 0);
      if (len > 0) s += `<circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(rr)}" fill="none" stroke="${colors[k]}" stroke-width="${f1(thick)}" stroke-dasharray="${f1(len)} ${f1(C)}" stroke-dashoffset="${f1(-C * f0)}" transform="rotate(-90 ${f1(cx)} ${f1(cy)})"/>`;
      f0 += f;
    });
    const fi = Math.max(0, items.findIndex((it) => it.highlight));
    const focus = items[fi];
    if (focus) {
      const cp = prog(t, t0 + 0.2, t0 + 1.1);
      const L = fit(fmt(focus.value, focus), 800, R * 0.46, rr * 1.25, 0, MIN_TEXT * U, `scene ${sc.key}: donut value`);
      const lb = wrap(focus.label ?? "", 600, 40 * U, MIN_TEXT * U, rr * 1.2, 2, `scene ${sc.key}: donut label`);
      const hTot = L.size * 0.75 + 16 * U + lb.lines.length * lb.size * 1.15;
      const vy = cy - hTot / 2 + L.size * 0.75;
      s += `<text x="${f1(cx)}" y="${f1(vy)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(L.size)}" fill="${readable(colors[fi], "#ffffff", `scene ${sc.key}: donut value`)}" opacity="${clamp(cp * 3).toFixed(3)}">${esc(fmt(focus.value * outCubic(cp), focus))}</text>`;
      s += textBlock(lb.lines, cx, vy + 16 * U + lb.size, lb.size, 600, MUTED, { lh: 1.15, op: clamp(cp * 3) });
    }
    items.forEach((it, k) => {
      const p = prog(t, times[k] + 0.3, times[k] + 0.6);
      if (p <= 0) return;
      const ry = ly + k * rowH + rowH / 2;
      const val = fmt(it.value, it), vw = measure(val, 800, 44 * U);
      const lb = wrap(it.label ?? "", 600, 44 * U, MIN_TEXT * U, lw - 60 * U - vw - 30 * U, 1, `scene ${sc.key}: legend ${k + 1}`);
      s += `<g opacity="${clamp(p * 2).toFixed(3)}" transform="translate(${f1((1 - outCubic(p)) * 30 * U)} 0)">`;
      s += `<circle cx="${f1(lx + 16 * U)}" cy="${f1(ry)}" r="${f1(16 * U)}" fill="${colors[k]}"/>`;
      s += textBlock(lb.lines, lx + 56 * U, ry + lb.size * 0.35, lb.size, 600, INK, { anchor: "start" });
      s += `<text x="${f1(lx + lw)}" y="${f1(ry + 44 * U * 0.35)}" text-anchor="end" font-family='${FONT}' font-weight="800" font-size="${f1(44 * U)}" fill="${INK}">${esc(val)}</text></g>`;
    });
    return s;
  }
  SCENES.chart = {
    render(sc, t) {
      titleLines(sc, t, HEAD());
      const out = sceneOut(sc, t);
      const items = sc.items ?? [], kind = sc.kind ?? "bar";
      if (!items.length) return;
      if (!["bar", "line", "donut"].includes(kind)) problem(`scene ${sc.key}: chart kind "${kind}" is not bar, line or donut.`);
      const area = bodyArea(sc);
      const cw = wideCard(), pad = 48 * U, left = CX - cw / 2 + pad, iw = cw - pad * 2;
      const head = sc.title ? wrap(sc.title, 800, 56 * U, MIN_TEXT * U, iw, 2, `scene ${sc.key}: chart title`) : null;
      const headH = head ? head.lines.length * head.size * 1.15 + 36 * U : 0;
      const cap = sc.caption ? wrap(sc.caption, 500, 40 * U, MIN_TEXT * U, iw, 2, `scene ${sc.key}: chart caption`) : null;
      const capH = cap ? cap.lines.length * cap.size * 1.2 + 28 * U : 0;
      const ch = Math.min(area.bottom - area.top, (PORTRAIT ? (kind === "donut" ? 1180 : 1080) : 780) * U);
      const y0 = place(sc, ch, "the chart", area), y = y0 + ch / 2;
      const en = enter(t, early(sc, sc.start));
      if (en.p <= 0) return;
      const fmt = fmtOf(sc), times = chartTimes(sc);
      let g = cardGroup(en, out, CX, y) + uiCard(CX, y, cw, ch);
      if (head) g += textBlock(head.lines, left, y0 + pad + head.size * 0.8, head.size, 800, INK, { anchor: "start", lh: 1.15 });
      const plot = { x: left, y: y0 + pad + headH, w: iw, h: ch - pad * 2 - headH - capH };
      if (kind === "line") g += drawLine(sc, t, plot, items, col(sc.color ?? style.accent), fmt);
      else if (kind === "donut") g += drawDonut(sc, t, plot, items, dataColors(sc, items, true), times, fmt);
      else g += drawBars(sc, t, plot, items, dataColors(sc, items, false), times, fmt);
      if (cap) g += textBlock(cap.lines, left, y0 + ch - pad - (cap.lines.length - 1) * cap.size * 1.2 - cap.size * 0.25, cap.size, 500, MUTED, { anchor: "start", lh: 1.2 });
      front += g + "</g>";
    },
    cues(sc, add) {
      titleCues(sc, add);
      add(early(sc, sc.start) + 0.02, "swoosh", { gain: 0.45 });
      const t0 = chartStart(sc), items = sc.items ?? [], times = chartTimes(sc);
      if (sc.kind === "line") {
        const dur = Math.max(0.9, 0.3 * items.length);
        add(t0, "rise", { dur, gain: 0.3 });
        add(t0 + dur, "chime", { gain: 0.5 });
      } else if (sc.kind === "donut") {
        add(t0, "whoosh", { dur: 1.1, gain: 0.45 });
        times.forEach((tt, k) => add(tt + 0.3, "pop", { pitch: 1 + k * 0.1, gain: 0.4 }));
      } else {
        times.forEach((tt, k) => add(tt + 0.55, items[k].highlight ? "coin" : "pop", { pitch: 0.9 + k * 0.1, gain: 0.45 }));
      }
    },
  };

  /* ---- quiz: a question, options one by one, a countdown, then the answer lights up. */
  function quizTiming(sc) {
    const opts = (sc.options ?? []).map((o) => (typeof o === "string" ? { text: o } : o));
    const q = early(sc, when(sc, sc.at, 0.15));
    const times = opts.map((o, k) => early(sc, when(sc, o.at, 0.7 + k * 0.4)));
    const reveal = when(sc, sc.revealAt, sc.len * 0.62);
    return { opts, q, times, reveal, countFrom: Math.max(...times, q) + 0.4 };
  }
  SCENES.quiz = {
    render(sc, t) {
      const out = sceneOut(sc, t);
      const { opts, q, times, reveal, countFrom } = quizTiming(sc);
      const n = opts.length, answer = sc.answer ?? 0;
      const c = col(sc.color ?? style.accent), good = col(sc.goodColor ?? "green");
      const cw = wideCard(), pad = 48 * U, iw = cw - pad * 2, cl = CX - cw / 2;
      const cols = !PORTRAIT && n > 2 ? 2 : 1, gap = 24 * U;
      const ow = (cw - (cols - 1) * gap) / cols;
      const qs = wrap(sc.question ?? "", 800, 72 * U, MIN_TEXT * U, iw, 4, `scene ${sc.key}: question`);
      const qH = pad + 90 * U + qs.lines.length * qs.size * 1.15 + pad * 0.7;
      const ows = opts.map((o, k) => wrap(o.text ?? "", 700, 54 * U, MIN_TEXT * U, ow - 170 * U, 2, `scene ${sc.key}: option ${k + 1}`));
      const oh = Math.max(128 * U, ...ows.map((w) => w.lines.length * w.size * 1.2 + 56 * U));
      const rows = Math.ceil(n / cols);
      const ex = sc.explain ? wrap(sc.explain, 600, 46 * U, MIN_TEXT * U, iw - 90 * U, 3, `scene ${sc.key}: explanation`) : null;
      const exH = ex ? ex.lines.length * ex.size * 1.25 + 56 * U : 0;
      const total = qH + 36 * U + rows * oh + (rows - 1) * gap + (ex ? 30 * U + exH : 0);
      const y0 = place(sc, total, "the quiz");
      // Question card.
      const en = enter(t, q);
      if (en.p <= 0) return;
      const qy = y0 + qH / 2;
      let g = cardGroup(en, out, CX, qy) + uiCard(CX, qy, cw, qH);
      g += iconTile("question", cl + pad + 36 * U, y0 + pad + 36 * U, 72 * U, c, `scene ${sc.key}: quiz icon`);
      g += `<text x="${f1(cl + pad + 96 * U)}" y="${f1(y0 + pad + 36 * U + 15 * U)}" font-family='${FONT}' font-weight="800" font-size="${f1(42 * U)}" fill="${readable(c, "#ffffff", `scene ${sc.key}: quiz label`)}">${esc(sc.label ?? labels.quiz)}</text>`;
      g += textBlock(qs.lines, cl + pad, y0 + pad + 90 * U + qs.size * 0.85, qs.size, 800, INK, { anchor: "start", lh: 1.15 });
      // Countdown ring, when there is time for one.
      if (reveal - countFrom > 1.0 && sc.timer !== false) {
        const cp = prog(t, countFrom, reveal), rr = 40 * U, tx = cl + cw - pad - rr, tyy = y0 + pad + 36 * U;
        const left = Math.ceil((reveal - Math.max(t, countFrom)) - 1e-6);
        const vis = clamp(prog(t, countFrom - 0.3, countFrom) * 3) * (1 - prog(t, reveal, reveal + 0.2));
        if (vis > 0) {
          g += `<g opacity="${vis.toFixed(3)}"><circle cx="${f1(tx)}" cy="${f1(tyy)}" r="${f1(rr)}" fill="none" stroke="${INK}" stroke-opacity=".1" stroke-width="${f1(9 * U)}"/>`;
          g += `<circle cx="${f1(tx)}" cy="${f1(tyy)}" r="${f1(rr)}" fill="none" stroke="${readable(c, "#ffffff")}" stroke-width="${f1(9 * U)}" stroke-dasharray="${f1(TAU * rr * (1 - cp))} ${f1(TAU * rr)}" transform="rotate(-90 ${f1(tx)} ${f1(tyy)})"/>`;
          g += `<text x="${f1(tx)}" y="${f1(tyy + 15 * U)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(42 * U)}" fill="${INK}">${Math.max(1, left)}</text></g>`;
        }
      }
      front += g + "</g>";
      // Options.
      const rp = prog(t, reveal, reveal + 0.3);
      const oy0 = y0 + qH + 36 * U;
      opts.forEach((o, k) => {
        const oen = enter(t, times[k], k);
        if (oen.p <= 0) return;
        const r = Math.floor(k / cols), cc = k % cols, inRow = Math.min(cols, n - r * cols);
        const x = CX + (cc - (inRow - 1) / 2) * (ow + gap), y = oy0 + r * (oh + gap) + oh / 2;
        const right = k === answer, won = rp > 0 && right, lost = rp > 0 && !right;
        const og = onFill(good, `scene ${sc.key}: right answer`);
        const pop = won ? 1 + wobble(t - reveal - 0.1, 0.12, 26, 7) : lost ? 1 - 0.03 * rp : 1;
        let s = cardGroup(oen, out, x, y) + `<g transform="translate(${f1(x)} ${f1(y)}) scale(${pop.toFixed(3)}) translate(${f1(-x)} ${f1(-y)})">`;
        s += uiCard(x, y, ow, oh, { fill: won ? og.fill : lost ? mix("#ffffff", PAPER, 0.6) : "#fff", lift: won ? rp : 0 });
        const ts = 84 * U, tx = x - ow / 2 + 28 * U + ts / 2;
        s += won ? iconTile("check", tx, y, ts, "#ffffff") : lost ? iconTile("x", tx, y, ts, mix(INK, "#ffffff", 0.75)) : iconTile(String.fromCharCode(65 + k), tx, y, ts, c, `scene ${sc.key}: option letter`);
        const w = ows[k];
        s += textBlock(w.lines, tx + ts / 2 + 30 * U, y - ((w.lines.length - 1) * w.size * 1.2) / 2 + w.size * 0.35, w.size, 700, won ? og.text : lost ? MUTED : INK, { anchor: "start", lh: 1.2 });
        front += s + "</g></g>";
        if (won) front += burst(t, reveal + 0.1, x + ow / 2 - 60 * U, y - oh / 2, 1200 + k, CONFETTI, 16, 240, 20 * U);
      });
      if (ex) {
        const ep = prog(t, reveal + 0.5, reveal + 0.85);
        if (ep > 0) {
          const ey = oy0 + rows * oh + (rows - 1) * gap + 30 * U + exH / 2;
          const eg = { p: ep, e: outBack(ep, 1.6), dy: (1 - outCubic(ep)) * 60 * U, rot: 0, op: clamp(ep * 3) };
          let s = cardGroup(eg, out, CX, ey) + uiCard(CX, ey, cw, exH, { fill: mix(good, "#ffffff", 0.85) });
          s += iconTile("info", cl + pad + 26 * U, ey, 52 * U, good);
          s += textBlock(ex.lines, cl + pad + 80 * U, ey - ((ex.lines.length - 1) * ex.size * 1.25) / 2 + ex.size * 0.35, ex.size, 600, readable(INK, mix(good, "#ffffff", 0.85)), { anchor: "start", lh: 1.25 });
          front += s + "</g>";
        }
      }
    },
    cues(sc, add) {
      const { opts, q, times, reveal, countFrom } = quizTiming(sc);
      add(q, "swoosh", { gain: 0.45 });
      add(q + 0.25, "blip", { pitch: 0.9, gain: 0.4 });
      opts.forEach((_, k) => add(times[k] + 0.05, "pop", { pitch: 0.9 + k * 0.12, gain: 0.5 }));
      if (reveal - countFrom > 1.0 && sc.timer !== false) for (let tt = countFrom; tt < reveal - 0.2; tt += 0.5) add(tt, "tick", { pitch: 1.4, gain: 0.35 });
      add(reveal, "chime", { gain: 0.6 });
      add(reveal + 0.05, "sparkle", { gain: 0.5 });
      if (sc.explain) add(reveal + 0.5, "pop", { pitch: 1.2, gain: 0.4 });
    },
  };

  /* ---- ranking: a top list revealed from the bottom up; number one gets the spotlight. */
  function rankTimes(sc) {
    const items = sc.items ?? [], n = items.length, up = (sc.order ?? "up") === "up";
    return items.map((it, k) => early(sc, it.at != null ? when(sc, it.at) : sc.start + 0.35 + (up ? n - 1 - k : k) * 0.6));
  }
  SCENES.ranking = {
    render(sc, t) {
      titleLines(sc, t, HEAD());
      const out = sceneOut(sc, t);
      const items = sc.items ?? [], n = items.length;
      if (!n) return;
      const area = bodyArea(sc), gap = 22 * U, cw = wideCard(), pad = 34 * U;
      const rowH = Math.min(PORTRAIT ? 170 * U : 130 * U, (area.bottom - area.top - gap * (n - 1)) / n);
      if (rowH < 110 * U) problem(`scene ${sc.key}: too many ranking rows for the frame; keep it to ${PORTRAIT ? 6 : 5}.`);
      const y0 = place(sc, n * rowH + (n - 1) * gap, "the ranking", area);
      const times = rankTimes(sc), fmt = fmtOf(sc);
      const vmax = Math.max(...items.map((it) => it.value ?? 0), 0) || 1;
      const MEDALS = ["#D9A441", "#A9B1BB", "#C4713D"];
      items.forEach((it, k) => {
        const p = prog(t, times[k], times[k] + 0.4);
        if (p <= 0) return;
        const y = y0 + k * (rowH + gap) + rowH / 2, dx = (1 - outBack(p, 1.4)) * W * 0.7 * (k % 2 ? -1 : 1);
        const star = k === 0 ? outCubic(prog(t, times[0] + 0.35, times[0] + 0.7)) : 0;
        const color = col(it.color ?? sc.color ?? style.accent);
        let s = `<g opacity="${(clamp(p * 3) * (1 - out)).toFixed(3)}" transform="translate(${f1(dx)} ${f1(out * H * 0.5)})">`;
        s += uiCard(CX, y, cw, rowH, { lift: star, stroke: star > 0.5 ? readable(color, "#ffffff") : null });
        const bs = rowH * 0.6, bx = CX - cw / 2 + pad + bs / 2, lift = -star * 10 * U;
        s += iconTile(String(k + 1), bx, y + lift, bs, sc.medals === false || k > 2 ? INK : MEDALS[k], `scene ${sc.key}: rank ${k + 1}`);
        let lx = bx + bs / 2 + 28 * U;
        if (it.icon) { s += iconTile(it.icon, lx + bs * 0.4, y + lift, bs * 0.8, color, `scene ${sc.key}: rank ${k + 1} icon`); lx += bs * 0.8 + 24 * U; }
        const rx = CX + cw / 2 - pad;
        const val = it.value != null ? fmt(it.value, it) : null, vw = val ? measure(val, 800, 50 * U) + 24 * U : 0;
        const lb = wrap(it.label ?? "", 800, 54 * U, MIN_TEXT * U, rx - lx - vw, 1, `scene ${sc.key}: rank ${k + 1} label`);
        if (val != null) {
          const gp = outCubic(prog(t, times[k] + 0.2, times[k] + 0.9));
          s += textBlock(lb.lines, lx, y + lift - 4 * U, lb.size, 800, INK, { anchor: "start" });
          const bw = (rx - lx) * (it.value / vmax) * gp;
          s += `<rect x="${f1(lx)}" y="${f1(y + lift + 22 * U)}" width="${f1(rx - lx)}" height="${f1(14 * U)}" rx="${f1(7 * U)}" fill="${INK}" opacity=".08"/>`;
          s += `<rect x="${f1(lx)}" y="${f1(y + lift + 22 * U)}" width="${f1(Math.max(14 * U, bw))}" height="${f1(14 * U)}" rx="${f1(7 * U)}" fill="${color}"/>`;
          s += `<text x="${f1(rx)}" y="${f1(y + lift - 4 * U)}" text-anchor="end" font-family='${FONT}' font-weight="800" font-size="${f1(50 * U)}" fill="${readable(color, "#ffffff", `scene ${sc.key}: rank ${k + 1} value`)}">${esc(fmt(it.value * gp, it))}</text>`;
        } else s += textBlock(lb.lines, lx, y + lift + lb.size * 0.35, lb.size, 800, INK, { anchor: "start" });
        front += s + "</g>";
        if (k === 0 && star > 0 && star < 1) front += burst(t, times[0] + 0.4, bx, y - rowH / 2, 1300, CONFETTI, 18, 280, 20 * U);
      });
    },
    cues(sc, add) {
      titleCues(sc, add);
      const times = rankTimes(sc), up = (sc.order ?? "up") === "up";
      times.forEach((tt, k) => { add(tt - 0.04, "swoosh", { gain: 0.45 }); add(tt + 0.3, "pop", { pitch: 0.8 + (times.length - k) * 0.1, gain: 0.5 }); });
      if (times.length) {
        if (up && times.length > 1) add(times[0] - 0.6, "drumroll", { dur: 0.55, gain: 0.6 });
        add(times[0] + 0.4, "chime", { gain: 0.55 });
        add(times[0] + 0.42, "sparkle", { gain: 0.5 });
      }
    },
  };

  /* ---- flip: a card shows one side (a myth, a question), then flips to the other (the fact, the answer). */
  const flipTimes = (sc) => ({ t0: early(sc, when(sc, sc.front?.at, 0.2)), tf: when(sc, sc.back?.at, sc.len * 0.45) - 0.25 });
  SCENES.flip = {
    render(sc, t) {
      titleLines(sc, t, HEAD());
      const out = sceneOut(sc, t);
      const sides = [sc.front ?? {}, sc.back ?? {}];
      const cw = wideCard(), pad = 56 * U, cl = CX - cw / 2;
      const lay = sides.map((sd, k) => wrap(sd.text ?? "", 800, (PORTRAIT ? 84 : 76) * U, MIN_TEXT * U, cw - pad * 2, 6, `scene ${sc.key}: ${k ? "back" : "front"} text`));
      const bodyH = Math.max(...lay.map((l) => l.lines.length * l.size * 1.18));
      const ch = Math.max(PORTRAIT ? 720 * U : 520 * U, pad * 2 + 90 * U + 60 * U + bodyH + 40 * U);
      const y0 = place(sc, ch, "the flip card"), y = y0 + ch / 2;
      const { t0, tf } = flipTimes(sc);
      const en = enter(t, t0);
      if (en.p <= 0) return;
      const fp = prog(t, tf, tf + 0.5), ang = inOutCubic(fp) * Math.PI;
      const k = ang > Math.PI / 2 ? 1 : 0, sd = sides[k], L = lay[k];
      const sx = Math.max(0.001, Math.abs(Math.cos(ang))), lift = Math.sin(fp * Math.PI) * 0.08;
      // The default colours are darkened quietly; a colour the story picks gets a note when it needs darkening.
      const c = sd.color ? col(sd.color) : readable(col(k ? "green" : "rose"), "#ffffff");
      let g = cardGroup(en, out, CX, y) + `<g transform="translate(${f1(CX)} ${f1(y)}) scale(${(sx * (1 + lift)).toFixed(3)} ${(1 + lift).toFixed(3)}) translate(${f1(-CX)} ${f1(-y)})">`;
      g += uiCard(CX, y, cw, ch, { stroke: k ? readable(c, "#ffffff") : null });
      g += iconTile(sd.icon ?? (k ? "check" : "x"), cl + pad + 45 * U, y0 + pad + 45 * U, 90 * U, c, `scene ${sc.key}: ${k ? "back" : "front"} icon`);
      g += `<text x="${f1(cl + pad + 120 * U)}" y="${f1(y0 + pad + 45 * U + 18 * U)}" font-family='${FONT}' font-weight="800" font-size="${f1(52 * U)}" fill="${readable(c, "#ffffff", `scene ${sc.key}: ${k ? "back" : "front"} label`)}">${esc(sd.label ?? (k ? labels.fact : labels.myth))}</text>`;
      const top = y0 + pad + 90 * U + 60 * U, room = y0 + ch - pad - top;
      const ty = top + (room - L.lines.length * L.size * 1.18) / 2 + L.size * 0.85;
      g += textBlock(L.lines, cl + pad, ty, L.size, 800, INK, { anchor: "start", lh: 1.18 });
      front += g + "</g></g>";
      if (k) front += burst(t, tf + 0.45, cl + cw - 80 * U, y0 + 20 * U, 1400, CONFETTI, 16, 240, 20 * U);
    },
    cues(sc, add) {
      titleCues(sc, add);
      const { t0, tf } = flipTimes(sc);
      add(t0, "swoosh", { gain: 0.45 });
      add(tf, "whip", { gain: 0.5 });
      add(tf + 0.45, "chime", { gain: 0.55 });
    },
  };

  /* ---- definition: a dictionary card: the word, how to say it, what it means, an example. */
  function definitionTiming(sc) {
    const t0 = early(sc, when(sc, sc.at, 0.15));
    const words = splitWords(sc.text);
    const r0 = Math.max(t0 + 0.5, sc.textAt != null ? when(sc, sc.textAt) : sc.v ? sc.start + sc.voiceAt : t0 + 0.8);
    const times = wordTimes(sc, words, r0, Math.min(2.2, words.length * 0.12));
    const done = Math.max(r0, ...times);
    return { t0, times, done, ex: sc.example ? when(sc, sc.exampleAt, done - sc.start + 0.4) : null };
  }
  SCENES.definition = {
    render(sc, t) {
      titleLines(sc, t, HEAD());
      const out = sceneOut(sc, t), c = col(sc.color ?? style.accent);
      const cw = wideCard(), pad = 56 * U, left = CX - cw / 2 + pad, iw = cw - pad * 2;
      const wd = wrap(sc.word ?? "", 800, (PORTRAIT ? 140 : 124) * U, MIN_TITLE * U, iw, 2, `scene ${sc.key}: word`);
      const meta = sc.phonetic || sc.kind;
      const df = wrap(sc.text ?? "", 600, 58 * U, MIN_TEXT * U, iw, 6, `scene ${sc.key}: definition`);
      const ex = sc.example ? wrap(sc.example, 500, 46 * U, MIN_TEXT * U, iw - 34 * U, 3, `scene ${sc.key}: example`) : null;
      const wordH = wd.lines.length * wd.size * 1.02;
      const ch = pad + wordH + (meta ? 76 * U : 10 * U) + 50 * U + df.lines.length * df.size * 1.25 + (ex ? 40 * U + ex.lines.length * ex.size * 1.25 : 0) + pad * 0.8;
      const y0 = place(sc, ch, "the definition card"), y = y0 + ch / 2;
      const { t0, times, ex: exAt } = definitionTiming(sc);
      const en = enter(t, t0);
      if (en.p <= 0) return;
      let g = cardGroup(en, out, CX, y) + uiCard(CX, y, cw, ch);
      let yy = y0 + pad;
      wd.lines.forEach((line, k) => {
        const L = layout(line, 800, wd.size, -0.02), base = yy + wd.size * 0.8 + k * wd.size * 1.02;
        const bp = outCubic(prog(t, t0 + 0.35 + k * 0.1, t0 + 0.8 + k * 0.1));
        g += `<rect x="${f1(left - 6 * U)}" y="${f1(base - wd.size * 0.3)}" width="${f1((L.width + 12 * U) * bp)}" height="${f1(wd.size * 0.36)}" rx="${f1(8 * U)}" fill="${mix(c, "#ffffff", 0.55)}"/>`;
        g += popLine(t, L, left + L.width / 2, base, INK, t0 + 0.1 + k * 0.1, { step: 0.03, from: 60, spin: 12, seed: 71 + k });
      });
      yy += wordH;
      if (meta) {
        const mp = clamp(prog(t, t0 + 0.4, t0 + 0.7) * 2);
        let mx = left;
        const my = yy + 48 * U;
        if (sc.phonetic) {
          g += `<text x="${f1(mx)}" y="${f1(my)}" font-family='${FONT}' font-weight="500" font-size="${f1(44 * U)}" fill="${MUTED}" opacity="${mp.toFixed(3)}">${esc(sc.phonetic)}</text>`;
          mx += measure(sc.phonetic, 500, 44 * U) + 30 * U;
        }
        if (sc.kind) g += `<g opacity="${mp.toFixed(3)}">${pill(sc.kind, mx + (measure(sc.kind, 800, 40 * U) + 56 * U) / 2, my - 14 * U, { size: 40 * U, fill: c, what: `scene ${sc.key}: word kind` })}</g>`;
        yy += 76 * U;
      } else yy += 10 * U;
      g += `<rect x="${f1(left)}" y="${f1(yy + 20 * U)}" width="${f1(iw)}" height="${f1(2 * U)}" fill="${INK}" opacity=".1"/>`;
      yy += 50 * U;
      g += wordsBlock(df.lines, left, yy + df.size * 0.85, df.size, 600, INK, t, times, { lh: 1.25 });
      yy += df.lines.length * df.size * 1.25;
      if (ex) {
        const ep = prog(t, exAt, exAt + 0.35);
        if (ep > 0) {
          const eh = ex.lines.length * ex.size * 1.25;
          g += `<g opacity="${clamp(ep * 2).toFixed(3)}" transform="translate(${f1((1 - outCubic(ep)) * 30 * U)} 0)">`;
          g += `<rect x="${f1(left)}" y="${f1(yy + 40 * U)}" width="${f1(8 * U)}" height="${f1(eh)}" rx="${f1(4 * U)}" fill="${c}"/>`;
          g += textBlock(ex.lines, left + 34 * U, yy + 40 * U + ex.size * 0.9, ex.size, 500, MUTED, { anchor: "start", lh: 1.25 }) + "</g>";
        }
      }
      front += g + "</g>";
    },
    cues(sc, add) {
      titleCues(sc, add);
      const { t0, ex } = definitionTiming(sc);
      add(t0, "swoosh", { gain: 0.45 });
      add(t0 + 0.15, "pop", { pitch: 1, gain: 0.5 });
      if (ex != null) add(ex, "tap", { gain: 0.45 });
    },
  };

  /* ---- profile: a person, place or thing: avatar, name, role and a few facts, one by one. */
  const factTimes = (sc) => (sc.facts ?? []).map((f, k) => early(sc, when(sc, f.at, 0.9 + k * 0.6)));
  SCENES.profile = {
    render(sc, t) {
      titleLines(sc, t, HEAD());
      const out = sceneOut(sc, t), c = col(sc.color ?? style.accent);
      const n = (sc.facts ?? []).length;
      // Landscape puts the facts beside the person; portrait stacks them underneath.
      const side = !PORTRAIT && n > 0;
      const cw = side ? wideCard() : Math.min(W * 0.88, (PORTRAIT ? 960 : 1200) * U), pad = 50 * U, cl = CX - cw / 2;
      const idW = side ? cw * 0.38 - pad * 2 : cw - pad * 2, idX = side ? cl + cw * 0.19 : CX;
      const fx = side ? cl + cw * 0.38 : cl + pad, fw = side ? cw * 0.62 - pad : cw - pad * 2;
      const d = (PORTRAIT ? 230 : 170) * U;
      const nm = wrap(sc.name ?? "", 800, 84 * U, MIN_TEXT * U, idW, 2, `scene ${sc.key}: name`);
      const rl = sc.role ? wrap(sc.role, 500, 46 * U, MIN_TEXT * U, idW, 2, `scene ${sc.key}: role`) : null;
      const facts = (sc.facts ?? []).map((f, k) => wrap(f.text ?? "", 600, 50 * U, MIN_TEXT * U, fw - 140 * U, 2, `scene ${sc.key}: fact ${k + 1}`));
      const fh = facts.map((f) => Math.max(96 * U, f.lines.length * f.size * 1.2 + 34 * U));
      const idH = d + 40 * U + nm.lines.length * nm.size * 1.1 + (rl ? 12 * U + rl.lines.length * rl.size * 1.25 : 0);
      const fH = n ? fh.reduce((a, b) => a + b, 0) + 14 * U * (n - 1) : 0;
      const ch = side ? pad * 2 + Math.max(idH, fH) : pad * 2 + idH + (n ? 40 * U + fH : 0);
      const y0 = place(sc, ch, "the profile card"), y = y0 + ch / 2;
      const idTop = side ? y - idH / 2 : y0 + pad, fTop = side ? y - fH / 2 : y0 + pad + idH + 40 * U;
      const t0 = early(sc, when(sc, sc.at, 0.15));
      const en = enter(t, t0);
      if (en.p <= 0) return;
      // The card goes behind the media layer, so a photo can sit on it.
      back += cardGroup(en, out, CX, y, false) + uiCard(CX, y, cw, ch) + "</g>";
      const ay = idTop + d / 2, ap = outBack(prog(t, t0 + 0.1, t0 + 0.45), 2);
      if (sc.media && ap > 0 && out < 1) media.push({ id: sc.media, variant: "avatar", t: t - sc.start, x: idX, y: ay + en.dy + out * H * 0.5, w: d * ap, h: d * ap, circle: true, ring: c, ringW: 10 * U });
      let g = cardGroup(en, out, CX, y, false);
      if (!sc.media && ap > 0) {
        const o = onFill(c, `scene ${sc.key}: initials`);
        g += `<g transform="translate(${f1(idX)} ${f1(ay)}) scale(${ap.toFixed(3)})"><circle r="${f1(d / 2)}" fill="${o.fill}"/>`;
        g += sc.icon && ICONS[sc.icon] ? `<path d="${ICONS[sc.icon]}" transform="translate(${f1(-d * 0.28)} ${f1(-d * 0.28)}) scale(${((d * 0.56) / 24).toFixed(4)})" fill="none" stroke="${o.text}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`
          : `<text y="${f1(d * 0.14)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(d * 0.38)}" fill="${o.text}">${esc(sc.initials ?? initialsOf(sc.name))}</text>`;
        g += "</g>";
      }
      let yy = idTop + d + 40 * U;
      nm.lines.forEach((line, k) => { g += popLine(t, layout(line, 800, nm.size, -0.02), idX, yy + nm.size * 0.8 + k * nm.size * 1.1, INK, t0 + 0.3 + k * 0.1, { step: 0.025, from: 50, spin: 10, seed: 81 + k }); });
      yy += nm.lines.length * nm.size * 1.1;
      if (rl) g += textBlock(rl.lines, idX, yy + 12 * U + rl.size * 0.85, rl.size, 500, MUTED, { lh: 1.25, op: clamp(prog(t, t0 + 0.5, t0 + 0.8) * 2) });
      yy = fTop;
      const times = factTimes(sc), tint2 = mix(c, "#ffffff", 0.88);
      facts.forEach((f, k) => {
        const p = prog(t, times[k], times[k] + 0.35), h = fh[k], cy = yy + h / 2;
        if (p > 0) {
          g += `<g opacity="${clamp(p * 2).toFixed(3)}" transform="translate(${f1((1 - outCubic(p)) * 40 * U)} 0)">`;
          g += `<rect x="${f1(fx)}" y="${f1(yy)}" width="${f1(fw)}" height="${f1(h)}" rx="${f1(26 * U)}" fill="${tint2}"/>`;
          g += iconTile(sc.facts[k].icon ?? "check", fx + 56 * U, cy, 60 * U, c, `scene ${sc.key}: fact ${k + 1} icon`);
          g += textBlock(f.lines, fx + 110 * U, cy - ((f.lines.length - 1) * f.size * 1.2) / 2 + f.size * 0.35, f.size, 600, readable(INK, tint2), { anchor: "start", lh: 1.2 }) + "</g>";
        }
        yy += h + 14 * U;
      });
      front += g + "</g>";
    },
    cues(sc, add) {
      titleCues(sc, add);
      const t0 = early(sc, when(sc, sc.at, 0.15));
      add(t0, "swoosh", { gain: 0.45 });
      add(t0 + 0.2, "pop", { pitch: 0.9, gain: 0.55 });
      factTimes(sc).forEach((tt, k) => add(tt, "tap", { pitch: 1 + k * 0.1, gain: 0.5 }));
    },
  };

  /* ---- list: a title and items that pop in one by one (explainers, steps, tips). */
  SCENES.list = {
    render(sc, t) {
      const out = inBack(prog(t, sc.end - 0.3, sc.end));
      if (sc.title) front += popLine(t, fit(sc.title, 800, 120 * U, TEXT_ROOM, -0.03, MIN_TITLE * U, `scene ${sc.key}: title`), CX, H * 0.2, readable(sc.titleColor ? col(sc.titleColor) : INK, BG, `scene ${sc.key}: title`), when(sc, sc.titleAt, 0.1), { step: 0.025, from: -110, out, seed: 3 });
      const items = sc.items ?? [];
      const gap = Math.min(PORTRAIT ? H * 0.1 : H * 0.16, (PORTRAIT ? H * 0.52 : H * 0.62) / Math.max(1, items.length));
      const blockH = gap * Math.max(0, items.length - 1) + Math.min(gap * 0.8, 170 * U);
      const top = (PORTRAIT ? H * 0.54 : H * 0.6) - blockH / 2;
      const iw = Math.min(W * 0.88, (PORTRAIT ? 960 : 1400) * U), ih = Math.min(gap * 0.8, 170 * U);
      items.forEach((it, k) => {
        const t0 = when(sc, it.at, 0.5 + k * 0.6);
        const p = outBack(prog(t, t0, t0 + 0.4), 1.8);
        if (p <= 0) return;
        const side = k % 2 ? 1 : -1;
        const x = lerp(CX + side * W, CX, clamp(p, 0, 1.2)), y = top + gap * k + ih / 2 - out * H * 0.6 * (1 + k * 0.1);
        const c = col(it.color ?? sc.color ?? style.accent);
        const icon = onFill(c, `scene ${sc.key}: item ${k + 1} icon`);
        const wr = wrap(it.text, 700, 58 * U, MIN_TEXT * U, iw - ih - 70 * U, 2, `scene ${sc.key}: item ${k + 1}`);
        const rot = (1 - clamp(p)) * side * 12 + (k % 2 ? 1.2 : -1.2);
        if (k === items.length - 1) safe(sc, top, top + gap * k + ih, "the list");
        front += `<g transform="translate(${f1(x)} ${f1(y)}) rotate(${rot.toFixed(2)})">`
          + `<rect x="${f1(-iw / 2)}" y="${f1(-ih / 2 + 10 * U)}" width="${f1(iw)}" height="${f1(ih)}" rx="${f1(ih / 2)}" fill="${INK}" opacity=".12"/>`
          + `<rect x="${f1(-iw / 2)}" y="${f1(-ih / 2)}" width="${f1(iw)}" height="${f1(ih)}" rx="${f1(ih / 2)}" fill="#fff"/>`
          + `<circle cx="${f1(-iw / 2 + ih / 2)}" cy="0" r="${f1(ih * 0.36)}" fill="${icon.fill}"/>`
          + `<text x="${f1(-iw / 2 + ih / 2)}" y="${f1(ih * 0.13)}" text-anchor="middle" font-family='${FONT}' font-weight="800" font-size="${f1(ih * 0.38)}" fill="${icon.text}">${esc(it.icon ?? String(k + 1))}</text>`
          + textBlock(wr.lines, -iw / 2 + ih + 24 * U, wr.size * 0.35 - ((wr.lines.length - 1) * wr.size * 1.15) / 2, wr.size, 700, INK, { anchor: "start", lh: 1.15 }) + `</g>`;
        front += burst(t, t0 + 0.3, x - iw / 2 + ih / 2, y, 300 + k * 13, [c, INK], 8, 120, ih * 0.4);
      });
    },
    cues(sc, add) {
      if (sc.title) add(when(sc, sc.titleAt, 0.1) + 0.05, "pop", { pitch: 1, gain: 0.5 });
      (sc.items ?? []).forEach((it, k) => { const t0 = when(sc, it.at, 0.5 + k * 0.6); add(t0, "whoosh", { dur: 0.3, gain: 0.5 }); add(t0 + 0.28, "pop", { pitch: 0.9 + k * 0.15, gain: 0.7 }); });
      add(sc.end - 0.3, "whoosh", { dur: 0.45, gain: 0.5 });
    },
  };

  /* ---- grid: everyone pops into seats, does the wave; a following logo gathers them. */
  const gridStart = (sc, n) => sc.start + 0.15 + n * Math.min(0.07, 1.6 / Math.max(1, sc.members.length));
  const gridOrder = (sc) => sc.members.map((_, k) => k).sort((a, b) => hash(a + 3) - hash(b + 3));
  SCENES.grid = {
    render(sc, t) {
      const out = inBack(prog(t, sc.end - 0.2, sc.end + 0.1));
      titleLines(sc, t, { center: PORTRAIT ? H * 0.2 : H * 0.17 });
      if (sc.footer) {
        const wr = wrap(sc.footer.text, 700, 60 * U, MIN_TEXT * U, TEXT_ROOM, 2, `scene ${sc.key}: footer`);
        const fy = PORTRAIT ? H * 0.79 : H * 0.88;
        safe(sc, fy - wr.size, fy + wr.lines.length * wr.size * 1.25, "the footer");
        const p = prog(t, when(sc, sc.footer.at, 2.2), when(sc, sc.footer.at, 2.2) + 0.3) * (1 - out);
        front += `<g transform="translate(0 ${f1((1 - outCubic(clamp(p))) * 40 * U)})">${textBlock(wr.lines, CX, fy, wr.size, 700, readable(sc.footer.color ? col(sc.footer.color) : INK, BG, `scene ${sc.key}: footer`), { op: clamp(p * 2), lh: 1.25 })}</g>`;
      }
      drawGridMembers(sc, t);
    },
    cues(sc, add) {
      titleCues(sc, add);
      const scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31, 33, 36, 38, 40, 43, 45];
      gridOrder(sc).forEach((k, n) => add(gridStart(sc, n) + 0.05, "marimba", { semis: scale[Math.min(n, scale.length - 1)] }));
      if (sc.footer) add(when(sc, sc.footer.at, 2.2), "pop", { pitch: 1.2, gain: 0.5 });
    },
  };
  function drawGridMembers(sc, t, gather = null) {
    const seats = gridSeats(sc);
    const order = gridOrder(sc);
    const allIn = gridStart(sc, sc.members.length) + 0.3;
    const fromCard = sc.prev?.type === "card" ? sc.members.findIndex((m) => m.media === sc.prev.media) : -1;
    sc.members.forEach((m, k) => {
      const seat = seats[k];
      let pop, start;
      if (k === fromCard) {
        // The previous card shrinks into its own seat.
        const go = prog(t, sc.start, sc.start + 0.5), e = inOutCubic(go);
        if (go < 1) {
          const PB = cardBox(sc.prev);
          media.push({ id: m.media, variant: go > 0.55 ? "avatar" : "full", t: t - sc.start, x: lerp(PB.x, seat.x, e), y: lerp(PB.y, seat.y, e) - Math.sin(go * Math.PI) * 180 * U, w: lerp(PB.w, seat.d, e), h: lerp(PB.h, seat.d, e), radius: lerp(46 * U, seat.d / 2, e), rot: lerp(-2.5, 0, e), border: go < 0.7 ? 14 * U : 0, ring: go >= 0.7 ? col(m.color) : null, ringW: 10 * U });
          return;
        }
        start = sc.start + 0.5; pop = 1;
      } else {
        start = gridStart(sc, order.indexOf(k));
        pop = outBack(prog(t, start, start + 0.3), 2.4);
      }
      if (pop <= 0) return;
      const waveT = t - allIn;
      const hop = waveT > 0 && !gather ? Math.max(0, Math.sin(waveT * 5.2 - seat.col * 0.6 - seat.row * 0.9)) * 30 * U : 0;
      const w = wobble(t - start - 0.3, 0.14);
      let x = seat.x, y = seat.y - hop, d = seat.d * clamp(pop, 0, 1.3), ring = col(m.color), ink = 0, rot = 0;
      if (gather) {
        const f0 = gather.start + (k % 6) * 0.03 + Math.floor(k / 6) * 0.02;
        const fly = prog(t, f0, f0 + 0.45), e = inOutCubic(fly);
        x = lerp(seat.x, gather.x, e); y = lerp(seat.y, gather.y, e) - Math.sin(fly * Math.PI) * (160 + hash(k) * 120) * U;
        d = lerp(seat.d, gather.d, e); ring = mix(col(m.color), gather.color, prog(fly, 0.2, 0.8)); ink = prog(fly, 0.45, 0.9) * gather.inkAmount;
        rot = Math.sin(fly * Math.PI) * 30 * (k % 2 ? 1 : -1);
        if (fly >= 1) return;
      }
      media.push({ id: m.media, variant: "avatar", t: t - sc.start + k * 0.37, x, y, w: d, h: d, circle: true, ring, ringW: 10 * U, sx: 1 + w, sy: 1 - w, rot, ink, inkColor: gather?.color });
    });
  }

  /* ---- logo: a mark (monogram or image) with name, tagline and URL. */
  SCENES.logo = {
    render(sc, t) {
      const u = t - sc.start;
      const settle = sc.start + (sc.prev?.type === "grid" ? 0.6 : 0.15);
      const markY = PORTRAIT ? H * 0.385 : H * 0.34, size = (sc.markSize ?? 300) * U;
      const mc = col(sc.color ?? style.accent);
      if (sc.prev?.type === "grid" && u < 0.7) {
        drawGridMembers(sc.prev, t, { start: sc.start, x: CX, y: markY, d: size * 0.3, color: mc, inkAmount: 0.6 });
      }
      if (t >= settle) {
        front += burst(t, settle, CX, markY, 900, CONFETTI, 26, 460, size * 0.4);
        const w = wobble(t - settle, 0.2, 26, 7), p = outBack(prog(t, settle, settle + 0.3), 2);
        if (sc.image) media.push({ id: sc.image, variant: "full", t: 0, x: CX, y: markY - size / 2 * (1 - w) + size / 2, w: size * p, h: size * p, sx: 1 + w, sy: 1 - w, contain: true, plain: true });
        else {
          const mono = sc.monogram ?? (sc.name ?? "?")[0];
          const mk = onFill(mc, `scene ${sc.key}: monogram`);
          front += `<g transform="translate(${f1(CX)} ${f1(markY + size / 2)}) scale(${((1 + w) * p).toFixed(3)} ${((1 - w) * p).toFixed(3)}) translate(0 ${f1(-size / 2)})"><rect x="${f1(-size / 2)}" y="${f1(-size / 2 + 14 * U)}" width="${f1(size)}" height="${f1(size)}" rx="${f1(size * 0.3)}" fill="${INK}" opacity=".15"/><rect x="${f1(-size / 2)}" y="${f1(-size / 2)}" width="${f1(size)}" height="${f1(size)}" rx="${f1(size * 0.3)}" fill="${mk.fill}"/><text text-anchor="middle" y="${f1(size * 0.2)}" font-family='${FONT}' font-weight="800" font-size="${f1(size * 0.56)}" fill="${mk.text}">${esc(mono)}</text></g>`;
        }
      }
      const nameY = markY + size / 2 + (PORTRAIT ? 200 : 150) * U;
      if (sc.name) front += popLine(t, fit(sc.name, 800, 190 * U, TEXT_ROOM, -0.035, MIN_TITLE * U, `scene ${sc.key}: name`), CX, nameY, readable(INK, BG), Math.max(settle - 0.02, when(sc, sc.nameAt, 0)), { step: 0.045, dur: 0.34, from: 130, spin: 20, seed: 31 });
      let y = nameY + 110 * U;
      (sc.tagline ?? []).forEach((part, k) => {
        // Parts share one line, each popping on its own word.
        const whole = sc.tagline.map((p2) => p2.text).join(" ");
        const L = fit(whole, 700, 64 * U, TEXT_ROOM, -0.01, MIN_TEXT * U, `scene ${sc.key}: tagline`);
        const offset = sc.tagline.slice(0, k).reduce((a, p2) => a + p2.text.length + 1, 0);
        const sub = { ...L, letters: L.letters.slice(offset, offset + part.text.length) };
        const ct = part.color ? colouredText(col(part.color), BG) : { text: readable(INK, BG), marker: null };
        if (ct.marker && sub.letters.length) {
          const x0 = CX - L.width / 2 + sub.letters[0].x - measure(part.text[0], 700, L.size) / 2;
          const t0 = when(sc, part.at, 0.4 + k * 0.5) - 0.05;
          front += marker(x0, measure(part.text, 700, L.size), y, L.size, ct.marker, outCubic(prog(t, t0, t0 + 0.35)));
        }
        front += popLine(t, { ...sub, width: L.width }, CX, y, ct.text, when(sc, part.at, 0.4 + k * 0.5) - 0.05, { step: 0.016, dur: 0.28, from: 50, spin: 8, seed: 37 + k });
      });
      if (sc.url) {
        const p = outCubic(prog(t, when(sc, sc.urlAt, sc.len - 1.2), when(sc, sc.urlAt, sc.len - 1.2) + 0.3));
        safe(sc, y + 40 * U, y + 90 * U, "the URL");
        front += `<text x="${f1(CX)}" y="${f1(y + 80 * U)}" text-anchor="middle" font-family='${FONT}' font-weight="600" font-size="${f1(44 * U)}" fill="${readable(mix(INK, BG, 0.3), BG)}" opacity="${p.toFixed(3)}">${esc(sc.url)}</text>`;
      }
    },
    cues(sc, add) {
      const gathered = sc.prev?.type === "grid";
      if (gathered) {
        add(sc.start - 0.6, "drumroll", { dur: 0.58, gain: 0.8 });
        add(sc.start, "slide", { from: 300, to: 1300, dur: 0.55 });
        add(sc.start + 0.05, "whoosh", { dur: 0.5 });
      }
      const settle = sc.start + (gathered ? 0.6 : 0.15);
      add(settle, "tada");
      add(settle + 0.02, "sparkle", { gain: 0.9 });
      if (sc.name) [...sc.name].forEach((_, j) => add(Math.max(settle, when(sc, sc.nameAt, 0)) + j * 0.045 + 0.1, "tick", { pitch: 1.1 + j * 0.05, gain: 0.4 }));
    },
  };

  /* ================================================================ render */
  const backEl = document.getElementById("back"), frontEl = document.getElementById("front");
  const canvas = document.getElementById("media");
  canvas.width = W; canvas.height = H;
  for (const el of [backEl, frontEl]) el.setAttribute("viewBox", `0 0 ${W} ${H}`);
  document.getElementById("frame").style.aspectRatio = `${W} / ${H}`;
  const ctx = canvas.getContext("2d");

  const images = new Map();
  function getImage(url) {
    let e = images.get(url);
    if (!e) {
      const img = new Image();
      img.src = url;
      e = { img, ready: img.decode().then(() => true, () => false) };
      images.set(url, e);
      if (images.size > 400) images.delete(images.keys().next().value);
    }
    return e;
  }
  function drawOp(op, img) {
    const { x, y, w, h, rot = 0, sx = 1, sy = 1 } = op;
    if (w < 1 || h < 1) return;
    ctx.save();
    ctx.translate(x, y + h / 2);
    ctx.rotate((rot * Math.PI) / 180);
    ctx.scale(sx, sy);
    ctx.translate(0, -h / 2);
    const radius = op.circle ? w / 2 : op.radius ?? 46 * U;
    if (op.plain && img) {
      const k = Math.min(w / img.naturalWidth, h / img.naturalHeight);
      ctx.drawImage(img, (-img.naturalWidth * k) / 2, (-img.naturalHeight * k) / 2, img.naturalWidth * k, img.naturalHeight * k);
      ctx.restore();
      return;
    }
    if (op.border) {
      ctx.save();
      ctx.shadowColor = "rgba(28,28,27,0.28)"; ctx.shadowBlur = 50 * U; ctx.shadowOffsetY = 24 * U;
      ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.roundRect(-w / 2 - op.border, -h / 2 - op.border, w + op.border * 2, h + op.border * 2, radius + op.border); ctx.fill();
      ctx.restore();
    }
    if (op.ring) {
      ctx.save();
      ctx.shadowColor = "rgba(28,28,27,0.22)"; ctx.shadowBlur = 24 * U; ctx.shadowOffsetY = 10 * U;
      ctx.fillStyle = op.ring;
      ctx.beginPath();
      if (op.circle) ctx.arc(0, 0, w / 2 + op.ringW, 0, TAU); else ctx.roundRect(-w / 2 - op.ringW, -h / 2 - op.ringW, w + op.ringW * 2, h + op.ringW * 2, radius + op.ringW);
      ctx.fill();
      ctx.restore();
    }
    ctx.beginPath();
    if (op.circle) ctx.arc(0, 0, w / 2, 0, TAU); else ctx.roundRect(-w / 2, -h / 2, w, h, radius);
    ctx.clip();
    if (img) {
      const k = Math.max(w / img.naturalWidth, h / img.naturalHeight);
      const dw = img.naturalWidth * k, dh = img.naturalHeight * k;
      ctx.drawImage(img, -dw / 2, -h / 2 - (dh - h) * 0.42, dw, dh);
    } else { ctx.fillStyle = "#d9d7d0"; ctx.fillRect(-w / 2, -h / 2, w, h); }
    if (op.ink > 0) { ctx.globalAlpha = op.ink; ctx.fillStyle = op.inkColor ?? INK; ctx.fillRect(-w / 2, -h / 2, w, h); }
    ctx.restore();
  }

  const lastGood = new Map();
  async function render(t, wait) {
    t = clamp(t, 0, DURATION - 1e-6);
    back = ""; front = ""; media = [];
    drawBackground(t);
    // The scene on screen, plus its neighbours for overlapping hand-offs.
    const cur = sceneAt(t);
    SCENES[cur.type]?.render(cur, t);
    media.sort((a, b) => (a.z ?? 0) - (b.z ?? 0));
    const ops = media.map((op) => { const url = frameUrl(op.id, op.variant, op.t); return { op, url, e: url ? getImage(url) : null }; });
    if (wait) await Promise.all(ops.map((o) => o.e?.ready));
    backEl.innerHTML = back;
    frontEl.innerHTML = front;
    ctx.clearRect(0, 0, W, H);
    for (const { op, e } of ops) {
      const img = e && e.img.complete && e.img.naturalWidth ? e.img : lastGood.get(op.id + op.variant);
      if (img) lastGood.set(op.id + op.variant, img);
      drawOp(op, img);
    }
  }

  /* ================================================================ cues + music plan */
  function buildCues() {
    const c = [];
    const add = (t, kind, extra = {}) => { if (t >= 0 && t < DURATION) c.push({ t: +t.toFixed(3), kind, ...extra }); };
    for (const sc of scenes) {
      if (sc.v) add(sc.start + sc.voiceAt - sc.v.speechStart, "voice", { key: sc.key, end: +(sc.start + sc.voiceAt + sc.speech).toFixed(3) });
      if (S.autoSfx !== false && sc.autoSfx !== false) SCENES[sc.type]?.cues(sc, add);
      // Sounds placed by hand: a library effect ("kind") or your own file ("file").
      for (const snd of sc.sounds ?? []) {
        const { at, ...rest } = snd;
        add(when(sc, at, 0), snd.file ? "file" : snd.kind ?? "pop", { ...rest, custom: true });
      }
    }
    return c.sort((a, b) => a.t - b.t);
  }
  const DEFAULT_MOOD = { pileup: "tension", title: "calm", fan: "calm", card: "groove", chat: "calm", cards: "groove", stats: "groove", checklist: "groove", compare: "groove", prompt: "groove", quote: "calm", timeline: "groove", chart: "groove", quiz: "tension", ranking: "run", flip: "groove", definition: "calm", profile: "groove", list: "groove", grid: "run", logo: "outro" };
  function buildMeta() {
    return {
      duration: DURATION, beat: BEAT, bpm: 60 / BEAT, width: W, height: H,
      music: { enabled: S.music?.enabled !== false, style: S.music?.style ?? "playful", file: S.music?.file ?? null, key: S.music?.key ?? "C", volume: S.music?.volume ?? 0.55, sfx: S.music?.sfx !== false, progression: S.music?.progression ?? ["C", "Am", "F", "G"] },
      scenes: scenes.map((sc) => ({ key: sc.key, type: sc.type, start: sc.start, len: sc.len, mood: sc.mood ?? DEFAULT_MOOD[sc.type] ?? "groove" })),
    };
  }

  /* ================================================================ playback */
  const capture = new URLSearchParams(location.search).has("capture");
  if (capture) document.body.classList.add("capture");
  const playBtn = document.getElementById("play"), scrub = document.getElementById("scrub"), clock = document.getElementById("clock"), sound = document.getElementById("sound");
  let playing = false, clockStart = 0, current = 0;
  function show(t) { current = t; render(t, false); scrub.value = t; clock.textContent = `${t.toFixed(2)}s`; }
  function tick(now) {
    if (playing) {
      const t = (now - clockStart) / 1000;
      if (t >= DURATION) { playing = false; playBtn.textContent = "Replay"; show(DURATION); sound.pause(); } else show(t);
    }
    requestAnimationFrame(tick);
  }
  playBtn?.addEventListener("click", () => {
    playing = !playing;
    playBtn.textContent = playing ? "Pause" : "Play";
    if (playing) { if (current >= DURATION) current = 0; clockStart = performance.now() - current * 1000; sound.currentTime = current; sound.play().catch(() => {}); } else sound.pause();
  });
  scrub?.addEventListener("input", () => { playing = false; playBtn.textContent = "Play"; sound.pause(); show(parseFloat(scrub.value)); });

  window.seek = (t) => render(t, true);
  const weights = style.fontWeights ?? [500, 600, 700, 800];
  Promise.all(weights.map((w) => document.fonts.load(`${w} 100px ${FONT}`))).catch(() => {}).then(() => document.fonts.ready).then(async () => {
    // A dry pass over every scene, so notes and problems cover the whole video, not just frame 0.
    for (const sc of scenes) {
      for (const f of [0.15, 0.4, 0.7, 0.95]) {
        const tt = sc.start + sc.len * f;
        back = ""; front = ""; media = [];
        drawBackground(tt);
        SCENES[sc.type]?.render(sc, tt);
        for (const op of media) frameUrl(op.id, op.variant, op.t);
      }
    }
    window.cues = buildCues();
    window.meta = buildMeta();
    window.timeline = scenes.map((s) => ({ key: s.key, type: s.type, start: +s.start.toFixed(2), len: +s.len.toFixed(2), voice: s.v ? +s.speech.toFixed(2) : null }));
    window.warnings = warnings;
    window.problems = problems;
    scrub.max = DURATION;
    await render(0, true);
    window.ready = true;
    if (!capture) requestAnimationFrame(tick);
  });
})();
