/*
 * debug.js: measurements printed INTO the frame (snapshots do not forward
 * console output). Active only when window.PF_DEBUG is true, which
 * scripts/stills.mjs --debug injects. Never ships in a render otherwise.
 *
 *   PF.debug({ grid: b, safe: { top: 250, bottom: 420, left: 60, right: 150 } });
 *
 * Shows: time and bar.beat, every [data-target] box (x, y centre, w, h) in
 * composition px, and the platform safe zone.
 */
(function () {
  const PF = window.PF;
  PF.debug = function ({ grid, safe } = {}) {
    if (!window.PF_DEBUG) return;
    const root = document.querySelector("[data-composition-id]");
    const W = root.offsetWidth, H = root.offsetHeight;
    const layer = document.createElement("div");
    layer.style.cssText = "position:absolute;inset:0;z-index:9999;pointer-events:none;font:600 22px/1.25 monospace";
    if (safe) {
      const s = document.createElement("div");
      s.style.cssText = `position:absolute;left:${safe.left || 0}px;top:${safe.top || 0}px;right:${safe.right || 0}px;bottom:${safe.bottom || 0}px;outline:3px dashed #ff00ff`;
      layer.appendChild(s);
    }
    const log = document.createElement("pre");
    log.style.cssText = "position:absolute;left:12px;top:12px;margin:0;padding:10px 14px;background:#000c;color:#0f0;white-space:pre";
    layer.appendChild(log);
    const boxes = document.createElement("div");
    layer.appendChild(boxes);
    root.appendChild(layer);

    PF.debugDraw = function (t) {
      const lines = [`t=${t.toFixed(3)}s` + (grid ? `  bar ${grid.label(t)}` : "") + `  ${W}x${H}`];
      boxes.innerHTML = "";
      for (const el of PF.$$("[data-target]", root)) {
        const cs = getComputedStyle(el);
        if (cs.visibility === "hidden" || el.closest("[style*='visibility: hidden']")) continue;
        const r = PF.rectOf(el, root);
        if (r.w === 0 && r.h === 0) continue;
        const name = el.getAttribute("data-target");
        lines.push(`${name} cx=${Math.round(r.x + r.w / 2)} cy=${Math.round(r.y + r.h / 2)} w=${Math.round(r.w)} h=${Math.round(r.h)}`);
        const b = document.createElement("div");
        b.style.cssText = `position:absolute;left:${r.x}px;top:${r.y}px;width:${r.w}px;height:${r.h}px;outline:2px solid #0f0`;
        boxes.appendChild(b);
      }
      log.textContent = lines.join("\n");
    };
  };
})();
