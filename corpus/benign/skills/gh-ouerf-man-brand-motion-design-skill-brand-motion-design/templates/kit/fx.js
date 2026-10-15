/*
 * fx.js: the showreel toolkit (the default register). Wipes and floods,
 * slams, camera shake, grain, a viewfinder overlay with a running
 * timecode, typewriter text, a particle swarm and outlined word walls.
 * Everything is a pure function of t. Load after film.js and motion.js.
 *
 * Build them from the brand's own elements (its colours, its mark, its type). A wipe in
 * the brand's colour through the brand's mark reads as the brand; a generic
 * lens flare reads as a template.
 */
(function () {
  const PF = window.PF;

  /* ---------- wipes and floods (clip-path, so they cost nothing) ---------- */

  /**
   * Iris: a circle growing from (x, y) that reveals `el`. p 0..1 on your ease.
   * The circle reaches the farthest corner at p = 1.
   */
  PF.iris = function (el, p, x, y, W, H) {
    const r = Math.hypot(Math.max(x, W - x), Math.max(y, H - y)) * PF.clamp01(p);
    PF.css(el, { clipPath: p >= 1 ? "none" : `circle(${r.toFixed(2)}px at ${x}px ${y}px)` });
  };

  /** Flood: a full-bleed layer wiping in from an edge ("up", "down", "left", "right"). */
  PF.flood = function (el, p, from = "up") {
    const q = ((1 - PF.clamp01(p)) * 100).toFixed(3) + "%";
    const inset = { up: `${q} 0 0 0`, down: `0 0 ${q} 0`, left: `0 0 0 ${q}`, right: `0 ${q} 0 0` }[from];
    PF.css(el, { clipPath: p >= 1 ? "none" : `inset(${inset})` });
  };

  /** Blinds: n bands closing in a stagger (a wipe with rhythm). Needs n child bands. */
  PF.blinds = function (bands, t, start, { each = 0.18, stagger = 0.035, ease, from = "left" } = {}) {
    bands.forEach((band, i) => {
      const u = (ease || PF.bezier(0.7, 0, 0.2, 1))(PF.progress(t, start + i * stagger, each));
      PF.css(band, { transform: from === "left" || from === "right" ? `scaleX(${u.toFixed(4)})` : `scaleY(${u.toFixed(4)})`, transformOrigin: { left: "0 50%", right: "100% 50%", up: "50% 100%", down: "50% 0" }[from] });
    });
  };

  /* ---------- slams and pops ---------- */

  /**
   * A slam: big and blurred to sharp, overshooting a hair, in `length` seconds.
   * Returns { scale, opacity, blur, u }. Pair with a thud on the same frame.
   */
  PF.slam = function (t, at, { from = 1.35, length = 0.22, blur = 18 } = {}) {
    const u = PF.progress(t, at, length);
    const e = PF.bezier(0.2, 0.9, 0.3, 1.15)(u);
    return { scale: PF.lerp(from, 1, e), opacity: PF.clamp01(u * 3), blur: (1 - PF.clamp01(e)) * blur, u };
  };
  PF.slamStyle = (el, s, extra) =>
    PF.css(el, Object.assign({ transform: `scale(${s.scale.toFixed(4)})`, opacity: s.opacity.toFixed(3), filter: s.blur > 0.05 ? `blur(${s.blur.toFixed(2)}px)` : "none" }, extra || {}));

  /**
   * A shockwave ring from a landing: radius and opacity at t. Draw it as an
   * SVG circle or a bordered div. One per landing, never looping.
   */
  PF.ring = (t, at, { length = 0.6, from = 0, to = 220 } = {}) => {
    const u = PF.progress(t, at, length);
    const e = PF.bezier(0.1, 0.8, 0.2, 1)(u);
    return { r: PF.lerp(from, to, e), opacity: u <= 0 || u >= 1 ? 0 : (1 - e) * 0.9, width: PF.lerp(6, 1, e) };
  };

  /* ---------- camera shake (deterministic) ---------- */

  /**
   * Shake kicked at each time in `hits`, decaying over `decay` seconds.
   * Returns { x, y, r } in px and degrees. Sum of fixed sines: no randomness.
   */
  PF.shake = function (t, hits, { amp = 14, decay = 0.35, freq = 23, rot = 0.6 } = {}) {
    let x = 0, y = 0, r = 0;
    for (const h of hits) {
      const d = t - h;
      if (d < 0 || d > decay) continue;
      const k = Math.pow(1 - d / decay, 2);
      x += amp * k * Math.sin(d * freq * 6.283 + 1.3);
      y += amp * 0.8 * k * Math.sin(d * freq * 1.37 * 6.283 + 0.4);
      r += rot * k * Math.sin(d * freq * 0.71 * 6.283 + 2.1);
    }
    return { x, y, r };
  };

  /* ---------- grain and vignette ---------- */

  /**
   * Film grain on a canvas the size of the frame (render it at 1/2 or 1/3 and
   * scale up with CSS). A new seed every 1/fps seconds, so it flickers like
   * film but is the same pixels for the same t. The strength is the canvas's
   * CSS opacity (0.04 to 0.1), not pixel alpha: `hyperframes check` treats any
   * canvas at 60% opacity or more as opaque and reports every word under it
   * as hidden. Pixels are drawn opaque; the element carries the strength.
   */
  PF.grain = function (canvas, t, { fps = 24, alpha = 0.06, mono = true } = {}) {
    PF.css(canvas, { opacity: alpha });
    alpha = 1;
    const ctx = canvas.getContext("2d");
    const w = canvas.width, h = canvas.height;
    if (!canvas._pfImg) canvas._pfImg = ctx.createImageData(w, h);
    const img = canvas._pfImg, d = img.data;
    const rand = PF.random(Math.floor(t * fps) * 7919 + 17);
    const a = Math.round(alpha * 255);
    for (let i = 0; i < d.length; i += 4) {
      const v = rand() * 255;
      d[i] = v; d[i + 1] = mono ? v : rand() * 255; d[i + 2] = mono ? v : rand() * 255; d[i + 3] = a;
    }
    ctx.putImageData(img, 0, 0);
  };

  /** A vignette as a CSS background (put it on a full-bleed overlay). */
  PF.vignette = (strength = 0.45, color = "0,0,0") =>
    `radial-gradient(ellipse 75% 65% at 50% 50%, rgba(${color},0) 55%, rgba(${color},${strength}) 100%)`;

  /* ---------- viewfinder overlay ---------- */

  /**
   * Corner brackets and four labels around the frame, like a camera
   * viewfinder: { tl, tr, bl, br } strings or functions of t. The timecode
   * helper gives HH:MM:SS:FF. Colour follows the scene (set with .color(c)).
   */
  PF.hud = function (parent, { inset = 48, size = 24, bracket = 34, font, color = "#fff", top = 0, bottom = 0 } = {}) {
    const box = document.createElement("div");
    box.className = "pf-hud";
    box.style.cssText = `position:absolute;left:${inset}px;right:${inset}px;top:${inset + top}px;bottom:${inset + bottom}px;pointer-events:none;color:${color};font:500 ${size}px/1 ${font || "monospace"};letter-spacing:0.14em;text-transform:uppercase`;
    const corners = ["tl", "tr", "bl", "br"].map((k) => {
      const c = document.createElement("div");
      const v = k[0] === "t" ? "top:0" : "bottom:0", hz = k[1] === "l" ? "left:0" : "right:0";
      const bw = `${k[0] === "t" ? "border-top" : "border-bottom"}:2px solid currentColor;${k[1] === "l" ? "border-left" : "border-right"}:2px solid currentColor`;
      c.style.cssText = `position:absolute;${v};${hz};width:${bracket}px;height:${bracket}px;${bw}`;
      box.appendChild(c);
      const label = document.createElement("div");
      label.style.cssText = `position:absolute;${k[0] === "t" ? "top:" + (bracket * 0.35) + "px" : "bottom:" + (bracket * 0.35) + "px"};${k[1] === "l" ? "left:" : "right:"}${bracket + 14}px;white-space:nowrap`;
      box.appendChild(label);
      return { k, label };
    });
    parent.appendChild(box);
    const api = {
      el: box,
      set(labels, t) {
        for (const { k, label } of corners) {
          const v = labels[k];
          label.textContent = typeof v === "function" ? v(t) : v || "";
        }
      },
      color(c) { PF.css(box, { color: c }); },
    };
    return api;
  };
  PF.timecode = (t, fps = 30) => {
    const f = Math.floor(t * fps);
    const ff = f % fps, s = Math.floor(f / fps) % 60, m = Math.floor(f / fps / 60);
    const p = (n) => String(n).padStart(2, "0");
    return `00:${p(m)}:${p(s)}:${p(ff)}`;
  };

  /* ---------- text ---------- */

  /** Typewriter: how much of `text` shows at t, with a block caret that blinks on the beat. */
  PF.typewriter = function (el, text, t, start, { cps = 22, caret = true, beat = 0.5, caretColor } = {}) {
    const n = Math.max(0, Math.min(text.length, Math.floor((t - start) * cps)));
    const on = caret && t >= start - beat && Math.floor((t - start) / (beat / 2)) % 2 === 0;
    const c = caret ? `<span style="display:inline-block;width:0.55em;height:1em;vertical-align:-0.12em;margin-left:0.08em;background:${caretColor || "currentColor"};opacity:${on || n < text.length ? 1 : 0}"></span>` : "";
    const html = text.slice(0, n).replace(/&/g, "&amp;").replace(/</g, "&lt;") + c;
    if (el._pfType !== html) { el.innerHTML = html; el._pfType = html; }
  };

  /**
   * A wall of the same word in outline, rows drifting in opposite directions
   * (behind a slammed word). Returns draw(t). Keep it low contrast.
   */
  PF.wordWall = function (parent, word, { rows = 7, size = 150, gap = 0.1, color = "rgba(255,255,255,.14)", font, weight = 800, speed = 60, y0 = 0 } = {}) {
    const wall = document.createElement("div");
    wall.style.cssText = `position:absolute;left:0;right:0;top:${y0}px;overflow:hidden;pointer-events:none`;
    const lines = [];
    for (let i = 0; i < rows; i++) {
      const row = document.createElement("div");
      row.style.cssText = `white-space:nowrap;font:${weight} ${size}px/${1 + gap} ${font || "sans-serif"};color:transparent;-webkit-text-stroke:2px ${color};text-transform:uppercase`;
      row.textContent = (word + " ").repeat(12);
      wall.appendChild(row);
      lines.push(row);
    }
    parent.appendChild(wall);
    return (t) => lines.forEach((row, i) => PF.css(row, { transform: `translateX(${((i % 2 ? 1 : -1) * speed * t - size * 2 - (i % 2 ? size * 3 : 0)).toFixed(2)}px)` }));
  };

  /* ---------- particles ---------- */

  /**
   * A swarm of n points that start scattered (seeded) and settle onto target
   * points on springs, staggered. `targets(i)` gives the resting {x, y} of
   * particle i (for example samples along a curve). Draws on a canvas.
   * Returns draw(t, { start, spread, color, size, drift }).
   */
  PF.swarm = function (canvas, n, targets, { seed = 7, W, H } = {}) {
    const rand = PF.random(seed);
    const ps = [];
    for (let i = 0; i < n; i++) {
      const a = rand() * Math.PI * 2, d = 0.35 + rand() * 0.75;
      ps.push({ sx: W / 2 + Math.cos(a) * d * W, sy: H / 2 + Math.sin(a) * d * H, delay: rand(), size: 0.6 + rand() * 0.8, tone: rand(), ...targets(i, n) });
    }
    const ctx = canvas.getContext("2d");
    return function (t, { start, spread = 0.6, colors = ["#fff"], size = 4, config = { stiffness: 90, damping: 16 }, alpha = 1, trail = 0 } = {}) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (alpha <= 0) return;
      ctx.globalAlpha = alpha;
      for (let i = 0; i < ps.length; i++) {
        const p = ps[i];
        const u = PF.step(t - start - p.delay * spread, config);
        const x = PF.lerp(p.sx, p.x, u), y = PF.lerp(p.sy, p.y, u);
        ctx.fillStyle = colors[Math.floor(p.tone * colors.length) % colors.length];
        if (trail > 0 && u < 0.98) {
          // a short streak toward where it came from, reads as speed
          const u2 = PF.step(t - start - p.delay * spread - trail, config);
          const x2 = PF.lerp(p.sx, p.x, u2), y2 = PF.lerp(p.sy, p.y, u2);
          ctx.strokeStyle = ctx.fillStyle;
          ctx.lineWidth = size * p.size;
          ctx.beginPath(); ctx.moveTo(x2, y2); ctx.lineTo(x, y); ctx.stroke();
        }
        ctx.beginPath(); ctx.arc(x, y, (size * p.size) / 2, 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalAlpha = 1;
    };
  };
})();
