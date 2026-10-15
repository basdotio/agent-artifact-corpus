// Measuring helpers: layout positions (untransformed) of elements inside a root, and a window rig that
// maps an app's logical coordinates into the world a camera looks at.

/** Layout position of el inside root (summed offsets; ignores transforms). */
export function offsetIn(el, root) {
  let x = 0, y = 0;
  let n = el;
  while (n && n !== root) {
    x += n.offsetLeft;
    y += n.offsetTop;
    n = n.offsetParent;
  }
  return { x, y, w: el.offsetWidth, h: el.offsetHeight, cx: x + el.offsetWidth / 2, cy: y + el.offsetHeight / 2 };
}

/**
 * A window placed in the world at (x, y) with scale s; `top` is the chrome height above the app.
 * rig.world(lx, ly) → world coords of an app point; rig.rect(el) → element rect in world coords.
 */
export function windowRig(appRoot, { x, y, s, top = 0 }) {
  const rig = {
    x, y, s, top, dx: 0, dy: 0,
    world(lx, ly) {
      return [rig.x + rig.dx + rig.s * lx, rig.y + rig.dy + rig.s * (ly + rig.top)];
    },
    rect(el) {
      const r = offsetIn(el, appRoot);
      const [wx, wy] = rig.world(r.x, r.y);
      return { x: wx, y: wy, w: r.w * rig.s, h: r.h * rig.s, cx: wx + (r.w * rig.s) / 2, cy: wy + (r.h * rig.s) / 2, l: r };
    },
  };
  return rig;
}
