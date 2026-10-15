/*
 * draw.js: SVG strokes that draw themselves, function curves, points riding
 * a path, and ordered-dither reveals. Load after film.js.
 */
(function () {
  const PF = window.PF;

  /**
   * Make an SVG path/line/polyline drawable. Returns set(p) with p in 0..1.
   * Uses pathLength=1, so it works for any length and survives scaling.
   * The element is hidden at p = 0 (round caps would leave a dot).
   */
  PF.drawable = function (el) {
    el.setAttribute("pathLength", "1");
    el.style.strokeDasharray = "1 1";
    return (p) => {
      p = PF.clamp01(p);
      PF.css(el, { strokeDashoffset: (1 - p).toFixed(5), visibility: p > 0 ? "inherit" : "hidden" });
    };
  };

  /**
   * Sample y = f(x) over [x0, x1] into an SVG path "d" through a mapping to
   * screen px. Breaks the path where f is not finite (asymptotes).
   *   const d = PF.fnPath(x => x**3 - 3*x + 1, -2.2, 2.2, axes.px, axes.py, 400);
   */
  PF.fnPath = function (f, x0, x1, px, py, samples = 300, clampY) {
    let d = "", pen = false;
    for (let i = 0; i <= samples; i++) {
      const x = x0 + ((x1 - x0) * i) / samples;
      const y = f(x);
      if (!Number.isFinite(y) || (clampY && (y < clampY[0] || y > clampY[1]))) { pen = false; continue; }
      d += (pen ? "L" : "M") + px(x).toFixed(2) + " " + py(y).toFixed(2);
      pen = true;
    }
    return d;
  };

  /** Linear maps for a graph: data window -> pixel box {x, y, w, h}. */
  PF.axes = function ({ xMin, xMax, yMin, yMax }, box) {
    return {
      px: (x) => box.x + ((x - xMin) / (xMax - xMin)) * box.w,
      py: (y) => box.y + box.h - ((y - yMin) / (yMax - yMin)) * box.h,
    };
  };

  /** A point p (0..1) along an SVG geometry element, in its user units. */
  PF.along = (el, p) => {
    const len = el.getTotalLength();
    return el.getPointAtLength(PF.clamp01(p) * len);
  };

  /* ---------- math on a 2D canvas (textures for 3D cards) ---------- */

  /**
   * Set a small formula on a canvas in KaTeX's own fonts (load the KaTeX CSS
   * so its @font-face rules exist; PF.film loads them before setup). Letters
   * are math italic, digits and symbols upright, `\name` is an upright word
   * (\ln, \sin, \lim), `^{...}` is a superscript, a prime (′) is raised. Returns the width drawn.
   *   PF.mathText(ctx, "(x + 2)^{2} = x^{2} + 4x + 4", 40, 300, 90, "#FFFFFF");
   * align: "left" | "center" | "right" (x is then the centre or the right edge).
   */
  PF.mathText = function (ctx, src, x, y, size, color, { align = "left", measure = false } = {}) {
    const runs = [];
    let i = 0;
    const push = (text, kind, sup) => runs.push({ text, kind, sup });
    while (i < src.length) {
      const ch = src[i];
      if (ch === "^" && src[i + 1] === "{") {
        const end = src.indexOf("}", i);
        for (const c of src.slice(i + 2, end)) push(c, /[a-z]/i.test(c) ? "math" : "main", true);
        i = end + 1;
      } else if (ch === "\\") {
        let j = i + 1;
        while (j < src.length && /[a-z]/i.test(src[j])) j++;
        push(src.slice(i + 1, j), "main", false);
        i = j;
      } else {
        // a prime sits high and small, as KaTeX sets it
        push(ch, /[a-z]/i.test(ch) ? "math" : "main", ch === "′" || ch === "'");
        i++;
      }
    }
    const font = (r) => `${r.kind === "math" ? "italic " : ""}${Math.round(r.sup ? size * 0.66 : size)}px ${r.kind === "math" ? "KaTeX_Math" : "KaTeX_Main"}`;
    let w = 0;
    for (const r of runs) { ctx.font = font(r); r.w = ctx.measureText(r.text === " " ? "\u2002" : r.text).width * (r.text === " " ? 0.55 : 1); w += r.w; }
    if (measure) return w;
    let cx = align === "center" ? x - w / 2 : align === "right" ? x - w : x;
    ctx.fillStyle = color;
    ctx.textBaseline = "alphabetic";
    for (const r of runs) {
      if (r.text !== " ") { ctx.font = font(r); ctx.fillText(r.text, cx, r.sup ? y - size * 0.42 : y); }
      cx += r.w;
    }
    return w;
  };

  /* ---------- ordered dither ---------- */
  PF.BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]].map((r) => r.map((v) => (v + 0.5) / 16));

  /**
   * Cells light in Bayer order under a front sweeping the area ("up", "down",
   * "left", "right", "out", "in"). Returns an SVG path of lit cells, for a
   * clipPath or an SVG mask.
   */
  PF.bayerPath = function ({ width, height, cell, progress, sweep = "up", band = 0.45, x = 0, y = 0 }) {
    if (progress <= 0) return "";
    const cols = Math.ceil(width / cell), rows = Math.ceil(height / cell);
    if (progress >= 1) return `M${x} ${y}h${cols * cell}v${rows * cell}h${-cols * cell}z`;
    const front = progress * (1 + band);
    let d = "";
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const u = (c + 0.5) / cols, v = (r + 0.5) / rows;
      const radial = Math.min(1, Math.hypot(u - 0.5, v - 0.5) * Math.SQRT2);
      const pos = { up: 1 - v, down: v, left: 1 - u, right: u, out: radial, in: 1 - radial }[sweep];
      if (PF.BAYER[r & 3][c & 3] < PF.clamp01((front - pos) / band)) d += `M${x + c * cell} ${y + r * cell}h${cell}v${cell}h${-cell}z`;
    }
    return d;
  };
})();
