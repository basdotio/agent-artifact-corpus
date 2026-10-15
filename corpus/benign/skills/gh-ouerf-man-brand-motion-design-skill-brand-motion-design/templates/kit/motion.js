/*
 * motion.js: closed-form springs, magic moves, blur swaps, a camera.
 * Everything here is a pure function of t (seconds). Load after film.js.
 */
(function () {
  const PF = window.PF;

  /* ---------- springs ---------- */
  /** Closed-form step response of a damped spring let go at t = 0, from 0 toward 1. */
  PF.step = function (t, { stiffness, damping, mass = 1, clamp = false }) {
    if (t <= 0) return 0;
    const w = Math.sqrt(stiffness / mass);
    const z = damping / (2 * Math.sqrt(stiffness * mass));
    let v;
    if (z < 1) {
      const wd = w * Math.sqrt(1 - z * z);
      v = 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
    } else if (z === 1) {
      v = 1 - Math.exp(-w * t) * (1 + w * t);
    } else {
      const wd = w * Math.sqrt(z * z - 1);
      v = 1 - Math.exp(-z * w * t) * (Math.cosh(wd * t) + ((z * w) / wd) * Math.sinh(wd * t));
    }
    return clamp ? Math.min(v, 1) : v;
  };

  /**
   * A value that retargets at each key [time, value]: the first value plus one
   * spring per change. Keys must be sorted by time. Still pure in t.
   */
  PF.track = function (t, keys, config) {
    let v = keys[0][1];
    for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * PF.step(t - keys[i][0], config);
    return v;
  };

  /** A critically damped spring with the given response (rad/s). */
  PF.critical = (response) => ({ stiffness: response * response, damping: 2 * response });

  PF.springs = {
    glide: { stiffness: 150, damping: 20 }, // magic moves
    camera: { stiffness: 120, damping: 30, mass: 1.2 }, // held, not thrown
    snap: { stiffness: 320, damping: 28 }, // small UI settles
  };

  /* ---------- magic moves ---------- */
  /** Rect from -> to on a spring started at `start`. Rects are {x, y, w, h} in composition px. */
  PF.move = function (t, start, from, to, config) {
    const u = PF.step(t - start, config || PF.springs.glide);
    return { x: PF.lerp(from.x, to.x, u), y: PF.lerp(from.y, to.y, u), w: PF.lerp(from.w, to.w, u), h: PF.lerp(from.h, to.h, u), u };
  };

  /**
   * Style for a traveler that renders in the DESTINATION's style and size and
   * scales from the source: put it at the destination box with
   * transform-origin 0 0 and apply this.
   */
  PF.travel = (rect, dest) => ({
    transform: `translate(${rect.x - dest.x}px, ${rect.y - dest.y}px) scale(${rect.w / dest.w}, ${rect.h / dest.h})`,
    transformOrigin: "0 0",
  });

  /**
   * Content that arrives after a move lands and leaves just before the next:
   * a short blur swap. Returns {opacity, filter, visible}.
   */
  PF.swap = function (t, from, to = Infinity, { delay = 0, enter = 0.18, leave = 0.12, blur = 10 } = {}) {
    const a = PF.clamp01((t - from - delay) / enter);
    const b = to === Infinity ? 0 : PF.clamp01((t - (to - leave)) / leave);
    const v = a * (1 - b);
    return { opacity: v, filter: v < 1 && blur ? `blur(${((1 - v) * blur).toFixed(2)}px)` : "none", visible: v > 0.001 };
  };

  /** Apply a swap() result to an element in one call. */
  PF.swapStyle = (el, s, extra) =>
    PF.css(el, Object.assign({ opacity: s.opacity, filter: s.filter, visibility: s.visible ? "inherit" : "hidden" }, extra || {}));

  /**
   * Rise-and-fade entry, the usual UI "enter": offset px, over `length` s, on an ease.
   * Returns {opacity, y}. Use the product's own enter duration and curve.
   */
  PF.enter = function (t, start, { length = 0.24, offset = 8, ease } = {}) {
    const u = (ease || PF.bezier(0, 0, 0.2, 1))(PF.progress(t, start, length));
    return { opacity: u, y: (1 - u) * offset, u };
  };

  /* ---------- camera ---------- */
  /**
   * Camera keys [t, x, y, zoom] in world units (the world point at the frame
   * centre). Zoom springs in log space so a push reads the same at any scale.
   */
  PF.camera = function (t, keys, config) {
    config = config || PF.springs.camera;
    return {
      x: PF.track(t, keys.map((k) => [k[0], k[1]]), config),
      y: PF.track(t, keys.map((k) => [k[0], k[2]]), config),
      zoom: Math.exp(PF.track(t, keys.map((k) => [k[0], Math.log(k[3])]), config)),
    };
  };
  /** CSS transform for a world layer (transform-origin 0 0). Never add will-change to it. */
  PF.worldTransform = (view, frame) =>
    `translate(${frame.width / 2}px, ${frame.height / 2}px) scale(${view.zoom}) translate(${-view.x}px, ${-view.y}px)`;
  /** Screen position of a world point. */
  PF.project = (view, frame, x, y) => ({ x: frame.width / 2 + (x - view.x) * view.zoom, y: frame.height / 2 + (y - view.y) * view.zoom });
})();
