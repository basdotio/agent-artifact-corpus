/*
 * cursor.js: a user's cursor that arrives exactly on the cue, and free paths.
 * Load after film.js.
 */
(function () {
  const PF = window.PF;
  const glide = PF.bezier(0.42, 0, 0.12, 1);

  /**
   * Keys: {t, x, y, click?, release?}. The cursor ARRIVES at (x, y) at t
   * (it starts gliding up to 0.46 s before). A click squashes on arrival;
   * `release` holds the button down until then. `toScreen(x, y)` maps world
   * points for keys with world: true (pass the camera projection).
   */
  PF.cursorAt = function (t, keys, toScreen) {
    const pts = keys.map((k) => Object.assign({}, k, k.world && toScreen ? toScreen(k.x, k.y) : { x: k.x, y: k.y }));
    let x = pts[0].x, y = pts[0].y;
    for (let i = 1; i < pts.length; i++) {
      const to = pts[i];
      if (t >= to.t) { x = to.x; y = to.y; continue; }
      const from = pts[i - 1];
      const d = Math.min(0.46, (to.t - from.t) * 0.82);
      const u = PF.clamp01((t - (to.t - d)) / d);
      const e = glide(u);
      const dx = to.x - from.x, dy = to.y - from.y, len = Math.hypot(dx, dy) || 1;
      const bulge = Math.sin(Math.PI * u) * Math.min(70, len * 0.09); // a hand, not a ruler
      x = from.x + dx * e - (dy / len) * bulge;
      y = from.y + dy * e + (dx / len) * bulge;
      break;
    }
    let squash = 1, pressed = false;
    for (const k of keys) {
      if (k.click && t >= k.t && t - k.t < 0.16) squash = Math.min(squash, 1 - 0.2 * Math.sin((Math.PI * (t - k.t)) / 0.16));
      if (k.release !== undefined && t >= k.t && t < k.release) pressed = true;
    }
    if (pressed) squash = Math.min(squash, 0.86);
    return { x, y, squash, pressed };
  };

  /** The OS arrow as an element. Position it with PF.placeCursor each frame. */
  PF.makeCursor = function (parent, size = 44) {
    const el = document.createElement("div");
    el.className = "pf-cursor";
    el.style.cssText = "position:absolute;left:0;top:0;width:0;height:0;z-index:50;pointer-events:none";
    el.innerHTML =
      `<svg width="${size}" height="${size}" viewBox="0 0 24 24" style="position:absolute;left:${-size * 0.2}px;top:${-size * 0.08}px;overflow:visible;transform-origin:20% 8%">` +
      `<path d="M5 2 L5 19 L9.5 15.5 L12.5 22 L15.5 20.5 L12.5 14 L18.5 14 Z" fill="#fff" stroke="#000" stroke-width="1.2" stroke-linejoin="round"/></svg>`;
    parent.appendChild(el);
    return el;
  };
  PF.placeCursor = (el, c, visible = true) => {
    PF.css(el, { transform: `translate(${c.x}px, ${c.y}px)`, visibility: visible ? "inherit" : "hidden" });
    PF.css(el.firstChild, { transform: `scale(${c.squash})` });
  };

  /**
   * A free-form path through timed stops {t, x, y} (cubic Hermite with
   * Catmull-Rom velocities). Stops whose t is in `hold` rest (zero velocity).
   */
  PF.pathAt = function (stops, t, hold = []) {
    if (t <= stops[0].t) return { x: stops[0].x, y: stops[0].y };
    const last = stops[stops.length - 1];
    if (t >= last.t) return { x: last.x, y: last.y };
    const i = stops.findIndex((s, k) => t >= s.t && t < stops[k + 1].t);
    const p0 = stops[i], p1 = stops[i + 1];
    const vel = (k, a) => {
      if (hold.includes(stops[k].t)) return 0;
      const b = stops[Math.max(0, k - 1)], c = stops[Math.min(stops.length - 1, k + 1)];
      return (c[a] - b[a]) / (c.t - b.t);
    };
    const span = p1.t - p0.t, u = (t - p0.t) / span;
    const h00 = 2 * u ** 3 - 3 * u ** 2 + 1, h10 = u ** 3 - 2 * u ** 2 + u, h01 = -2 * u ** 3 + 3 * u ** 2, h11 = u ** 3 - u ** 2;
    const along = (a) => h00 * p0[a] + h10 * span * vel(i, a) + h01 * p1[a] + h11 * span * vel(i + 1, a);
    return { x: along("x"), y: along("y") };
  };
})();
