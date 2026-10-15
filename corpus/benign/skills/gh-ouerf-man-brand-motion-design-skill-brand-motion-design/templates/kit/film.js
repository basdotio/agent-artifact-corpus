/*
 * film.js: the clock of a product film in HyperFrames.
 *
 * HyperFrames seeks one paused GSAP timeline per composition. This file adds
 * one linear "clock" tween to it whose onUpdate calls your draw(t), so every
 * style on screen is a pure function of the time in seconds. Seek anywhere,
 * in any order, and you get the same pixels.
 *
 *   index.html loads vendor/gsap.min.js, kit/film.js (then the other kit
 *   files you use), cues.js, then an inline script calls:
 *     PF.film({ duration: CUES.duration, setup, draw,
 *       register: (tl) => { window.__timelines["main"] = tl; } });
 *
 * Never write a closing script tag anywhere in a kit file, even in a comment:
 * HyperFrames inlines external scripts, and that tag would end the inlined
 * script early and print the rest of the file into the frame.
 *
 * register(tl) must assign the timeline to window.__timelines["<root
 * data-composition-id>"] literally: `hyperframes lint` looks for that line.
 * setup() runs once after every declared font has loaded (build DOM, render
 * KaTeX, then measure). draw(t) runs
 * on every seek. You may still add ordinary GSAP tweens in build(tl): they
 * are seekable too, but keep one owner per property (clock OR tween).
 */
(function () {
  const PF = (window.PF = window.PF || {});

  /* ---------- numbers ---------- */
  PF.clamp01 = (v) => Math.min(1, Math.max(0, v));
  PF.lerp = (a, b, u) => a + (b - a) * u;
  /** 0 before start, 1 after start + length, linear between. */
  PF.progress = (t, start, length) =>
    length <= 0 ? (t >= start ? 1 : 0) : PF.clamp01((t - start) / length);
  /** true while start <= t < end (the same half-open window HyperFrames uses for clips). */
  PF.within = (t, start, end) => t >= start && t < end;

  /**
   * cubic-bezier(x1, y1, x2, y2) as a function of 0..1, so the product's own
   * CSS easing tokens drive the film exactly (Newton, then bisection).
   */
  PF.bezier = function (x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = (u) => ((ax * u + bx) * u + cx) * u;
    const sy = (u) => ((ay * u + by) * u + cy) * u;
    const dx = (u) => (3 * ax * u + 2 * bx) * u + cx;
    function solve(x) {
      let u = x;
      for (let i = 0; i < 8; i++) {
        const e = sx(u) - x;
        if (Math.abs(e) < 1e-6) return u;
        const d = dx(u);
        if (Math.abs(d) < 1e-6) break;
        u -= e / d;
      }
      let lo = 0, hi = 1;
      u = x;
      while (lo < hi) {
        const v = sx(u);
        if (Math.abs(v - x) < 1e-6) return u;
        if (x > v) lo = u; else hi = u;
        u = (lo + hi) / 2;
        if (hi - lo < 1e-7) break;
      }
      return u;
    }
    return (x) => (x <= 0 ? 0 : x >= 1 ? 1 : sy(solve(x)));
  };
  /** Parse "cubic-bezier(.4, 0, .2, 1)" straight from a token file. */
  PF.ease = (css) => {
    const m = String(css).match(/cubic-bezier\(([^)]+)\)/);
    if (!m) throw new Error("PF.ease: not a cubic-bezier: " + css);
    const [a, b, c, d] = m[1].split(",").map(Number);
    return PF.bezier(a, b, c, d);
  };
  /** Eased progress: ease(progress(t, start, length)). */
  PF.tween = (t, start, length, ease) => (ease || ((u) => u))(PF.progress(t, start, length));

  /** Hex colour mix. Animate hex tokens only, never color-mix() or CSS vars. */
  PF.mix = function (a, b, u) {
    const p = (h) => {
      h = h.replace("#", "");
      if (h.length === 3) h = h.split("").map((c) => c + c).join("");
      return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
    };
    const [x, y] = [p(a), p(b)];
    return "#" + x.map((v, i) => Math.round(PF.lerp(v, y[i], PF.clamp01(u))).toString(16).padStart(2, "0")).join("");
  };

  /** Seeded PRNG (mulberry32): the only randomness a film may use. */
  PF.random = function (seed) {
    let s = seed >>> 0;
    return function () {
      s = (s + 0x6d2b79f5) >>> 0;
      let r = Math.imul(s ^ (s >>> 15), 1 | s);
      r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  };

  /* ---------- the beat grid ---------- */
  /**
   * A measured grid (scripts/beats.py, or the one scripts/synth.py wrote).
   * b(bar, beat, fraction) -> seconds. Bar 1 beat 1 is the first downbeat;
   * fraction is a share of one beat (0.5 is the "and").
   */
  PF.grid = function ({ bpm, firstBeat = 0, pickupBeats = 0, beatsPerBar = 4 }) {
    const beat = 60 / bpm;
    const b = (bar, beatInBar = 1, fraction = 0) =>
      firstBeat + (pickupBeats + (bar - 1) * beatsPerBar + (beatInBar - 1) + fraction) * beat;
    b.beat = beat;
    b.bar = beat * beatsPerBar;
    b.bpm = bpm;
    /** The inverse, for debug readouts: seconds -> "bar.beat". */
    b.label = (t) => {
      const i = (t - firstBeat) / beat - pickupBeats;
      const bar = Math.floor(i / beatsPerBar) + 1;
      const inBar = i - (bar - 1) * beatsPerBar + 1;
      return bar + "." + inBar.toFixed(2);
    };
    return b;
  };

  /* ---------- DOM helpers (cheap, per frame) ---------- */
  const lastStyle = new WeakMap();
  /** Set only the styles that changed since the last frame. */
  PF.css = function (el, styles) {
    if (!el) return;
    let prev = lastStyle.get(el);
    if (!prev) lastStyle.set(el, (prev = {}));
    for (const key in styles) {
      const value = styles[key] == null ? "" : String(styles[key]);
      if (prev[key] !== value) {
        prev[key] = value;
        if (key.startsWith("--")) el.style.setProperty(key, value);
        else el.style[key] = value;
      }
    }
  };
  /**
   * Show or hide without layout shift (keeps the slot). "Shown" is
   * visibility: inherit, never "visible": a child set to visible stays on
   * screen even when its hidden scene is not, which leaks elements across scenes.
   */
  PF.show = (el, visible) => PF.css(el, { visibility: visible ? "inherit" : "hidden" });
  PF.$ = (sel, root) => (root || document).querySelector(sel);
  PF.$$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  /**
   * A box in composition pixels, whatever the preview scale. Measure in setup(),
   * not per frame, and only for elements with no transform of their own.
   */
  PF.rectOf = function (el, root) {
    root = root || document.querySelector("[data-composition-id]");
    const r = root.getBoundingClientRect();
    const scale = r.width / root.offsetWidth || 1;
    const b = el.getBoundingClientRect();
    return { x: (b.left - r.left) / scale, y: (b.top - r.top) / scale, w: b.width / scale, h: b.height / scale };
  };

  /* ---------- mount ---------- */
  /**
   * Register the film with HyperFrames. Builds after document.fonts.ready and
   * registers the timeline only when the build is complete (a timeline
   * registered early renders blank).
   */
  /**
   * A named one-shot signal, for things that load outside the classic
   * scripts (an ES module such as Three.js). The module calls
   * PF.signal("three").resolve(); PF.film({ waitFor: [PF.signal("three")] })
   * waits for it before setup.
   */
  const signals = {};
  PF.signal = function (name) {
    if (!signals[name]) {
      let resolve;
      const p = new Promise((r) => (resolve = r));
      p.resolve = resolve;
      signals[name] = p;
    }
    return signals[name];
  };

  /**
   * The user's images (logo PNG, product photos, screenshots), decoded before
   * setup so they can be measured and painted into 3D:
   *   PF.film({ waitFor: [PF.loadImages({ hero: "assets/images/hero.png" })] })
   *   setup(): PF.img.hero is a decoded HTMLImageElement (null if it failed).
   */
  PF.img = {};
  PF.loadImages = function (map) {
    return Promise.all(Object.entries(map).map(([key, src]) => new Promise((done) => {
      const im = new Image();
      im.onload = () => Promise.resolve(im.decode ? im.decode() : null).catch(() => null).then(() => { PF.img[key] = im; done(im); });
      im.onerror = () => { console.error("PF.loadImages: cannot load " + src); PF.img[key] = null; done(null); };
      im.src = src;
    })));
  };

  PF.film = function ({ id = "main", duration, setup, draw, build, register, waitFor = [] }) {
    if (!(duration > 0)) throw new Error("PF.film: duration (seconds) is required");
    const start = () => {
      if (setup) setup();
      const tl = gsap.timeline({ paused: true });
      const clock = { t: 0 };
      // Land the clock a hair before the end: a clip is hidden at exactly start + duration.
      const end = Math.max(0, duration - 1e-4);
      tl.to(clock, {
        t: end,
        duration: end,
        ease: "none",
        onUpdate() {
          PF.now = clock.t;
          draw(clock.t);
          if (PF.debugDraw) PF.debugDraw(clock.t);
        },
      }, 0);
      if (build) build(tl);
      PF.now = 0;
      draw(0);
      if (PF.debugDraw) PF.debugDraw(0);
      PF.timeline = tl;
      if (register) register(tl); else window.__timelines[id] = tl;
      if (window.__hfForceTimelineRebind) window.__hfForceTimelineRebind();
    };
    // Load EVERY declared @font-face before setup, not just the ones in use:
    // document.fonts.ready only waits for fonts the page already uses, so text
    // rendered in setup (KaTeX, words) would be measured in a fallback font
    // and every measured box would be off.
    const fonts = document.fonts;
    if (!fonts) return Promise.all(waitFor).then(start);
    Promise.all(Array.from(fonts).map((f) => f.load().catch(() => null)).concat(waitFor))
      .then(() => fonts.ready)
      .then(start);
  };
})();
