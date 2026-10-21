// Scroll "drop and dock" controller for the lanyard badge.
//
// In the page the badge sits in normal flow inside the slot element. Once the slot scrolls up
// past `dockAt` the badge detaches (position: fixed) and a spring drops it into a dock at the
// top-right, hanging from beneath the fixed header, where it stays while the page scrolls.
// Scrolling back above `undockAt` sends it home again. While docked it shrinks to
// `collapsedScale`; hover, focus or a held click enlarges it to `expandedScale` so the back
// stays readable.
//
// Below `dockMinWidth` there is no dock (a floating card would cover too much content).
// Between `twoColMinWidth` and that, and on short screens, the in-flow badge is scaled down a
// little so the whole card clears the fold.
//
// Options (all optional), passed as `dock: { ... }` in the badge config:

const W = 280; // badge width in px  (keep in sync with .badge-root in badge.css)
const H = 650; // badge height incl. strap
const CLASP_TOP = 128; // y of the clasp inside the badge: this is what hangs below the header

const DEFAULTS = {
  dockMinWidth: 1280, // viewport width from which the floating dock is allowed
  twoColMinWidth: 1024, // viewport width from which the slot is a side column (fit-to-height applies)
  nav: "[data-nav]", // selector of a fixed header the lanyard hangs beneath; null if there is none
  navHeight: 0, // header height to assume when `nav` matches nothing
  collapsedScale: 0.6, // docked size
  expandedScale: 0.85, // docked size on hover / focus / held click
  margin: 24, // gap from the right edge of the viewport
  belowNav: 16, // breathing room between the header and the clasp
  dockAt: 20, // slot top (px from viewport top) below which the badge docks
  undockAt: 60, // hysteresis so it doesn't flicker on the threshold
  minHeroScale: 0.72, // smallest the in-flow badge may shrink to fit a short screen
  fitMargin: 120, // px of viewport (beyond the header) kept free when fitting: covers hero padding + vertical centering
  dropVelocity: 650, // px/s downward kick when it lets go: the "drop"
  swingKick: 120, // deg/s kick so it swings as it lands
};

export function createDock({ slot, root, swing, reduceMotion, onDock, options = {} }) {
  const o = { ...DEFAULTS, ...options };
  const desktop = window.matchMedia(`(min-width: ${o.dockMinWidth}px)`);
  const twoCol = window.matchMedia(`(min-width: ${o.twoColMinWidth}px)`);
  const nav = o.nav ? document.querySelector(o.nav) : null;

  let floating = false; // root is position: fixed
  let docked = false; // target is the dock (otherwise: back to the hero slot)
  let expanded = false;

  const p = { x: 0, y: 0, s: 1 };
  const v = { x: 0, y: 0, s: 0 };
  const sw = { a: 0, v: 0 };
  let raf = 0;
  let last = 0;
  let lastScrollY = window.scrollY;

  const navHeight = () => (nav ? nav.getBoundingClientRect().height : o.navHeight);

  function dockTarget() {
    const vw = document.documentElement.clientWidth;
    const clearY = navHeight() + o.belowNav;
    // Largest scale at which the whole badge still fits under the nav and above the bottom.
    const fit = (window.innerHeight - 16 - clearY) / (H - CLASP_TOP);
    const s = Math.min(expanded ? o.expandedScale : o.collapsedScale, Math.max(0.35, fit));
    return { x: vw - o.margin - W * s, y: clearY - CLASP_TOP * s, s };
  }

  // The hero badge shrinks a little on short screens so the whole card clears the fold.
  function heroScale() {
    if (!twoCol.matches) return 1;
    const avail = window.innerHeight - navHeight() - o.fitMargin;
    return Math.max(o.minHeroScale, Math.min(1, avail / H));
  }

  function heroTarget() {
    const r = slot.getBoundingClientRect();
    const s = heroScale();
    return { x: r.left + (r.width - W * s) / 2, y: r.top, s };
  }

  function applyHeroLayout() {
    const s = heroScale();
    slot.style.minHeight = s < 1 ? Math.round(H * s) + "px" : "";
    if (!floating) root.style.transform = s < 1 ? `scale(${s})` : "";
  }

  function apply() {
    root.style.transform = `translate3d(${p.x}px, ${p.y}px, 0) scale(${p.s})`;
    swing.style.transform = sw.a ? `rotate(${sw.a}deg)` : "";
  }

  function beginFloating() {
    if (floating) return;
    const t = heroTarget();
    p.x = t.x;
    p.y = t.y;
    p.s = t.s;
    v.x = v.y = v.s = 0;
    floating = true;
    root.classList.add("is-floating");
    apply();
  }

  function endFloating() {
    floating = false;
    docked = false;
    root.classList.remove("is-floating", "is-expanded");
    swing.style.transform = "";
    sw.a = sw.v = 0;
    applyHeroLayout();
  }

  function snap() {
    const t = docked ? dockTarget() : heroTarget();
    Object.assign(p, t);
    v.x = v.y = v.s = 0;
    sw.a = sw.v = 0;
    apply();
    if (!docked) endFloating();
  }

  function integrate(dt) {
    const t = docked ? dockTarget() : heroTarget();
    // Docking is under-damped (it overshoots and bounces: the "drop"); returning home is
    // close to critically damped so it glides back without wobbling into the hero copy.
    const k = docked ? 170 : 230;
    const c = docked ? 13 : 28;
    for (const ax of ["x", "y", "s"]) {
      v[ax] += (k * (t[ax] - p[ax]) - c * v[ax]) * dt;
      p[ax] += v[ax] * dt;
    }
    const sk = 40;
    const sc = docked ? 2.4 : 6;
    sw.v += (-sk * sw.a - sc * sw.v) * dt;
    sw.a += sw.v * dt;
    return t;
  }

  function frame(now) {
    raf = 0;
    let dt = Math.min((now - last) / 1000, 1 / 30);
    last = now;
    let t;
    while (dt > 0) {
      const step = Math.min(dt, 1 / 120);
      t = integrate(step);
      dt -= step;
    }
    apply();

    const settled =
      t &&
      Math.abs(t.x - p.x) < 0.3 &&
      Math.abs(t.y - p.y) < 0.3 &&
      Math.abs(t.s - p.s) < 0.002 &&
      Math.abs(v.x) < 2 &&
      Math.abs(v.y) < 2 &&
      Math.abs(v.s) < 0.02 &&
      Math.abs(sw.a) < 0.05 &&
      Math.abs(sw.v) < 0.5;

    if (settled) {
      snap();
      return;
    }
    raf = requestAnimationFrame(frame);
  }

  function wake() {
    if (reduceMotion.matches) {
      snap();
      return;
    }
    if (raf) return;
    last = performance.now();
    raf = requestAnimationFrame(frame);
  }

  function dockNow() {
    const fromHero = !floating;
    docked = true;
    beginFloating();
    if (reduceMotion.matches) {
      snap();
      return;
    }
    v.y += o.dropVelocity;
    sw.v += o.swingKick;
    if (fromHero && onDock) onDock();
    wake();
  }

  function undockNow() {
    docked = false;
    root.classList.remove("is-expanded");
    wake();
  }

  function evaluate() {
    if (!desktop.matches) {
      if (floating) {
        if (raf) cancelAnimationFrame(raf);
        raf = 0;
        endFloating();
      }
      return;
    }
    const top = slot.getBoundingClientRect().top;
    if (!docked && top < o.dockAt) dockNow();
    else if (docked && top > o.undockAt) undockNow();
  }

  window.addEventListener(
    "scroll",
    () => {
      const dy = window.scrollY - lastScrollY;
      lastScrollY = window.scrollY;
      evaluate();
      // The floating badge swings a little with the scroll, like a real lanyard.
      if (floating && docked && !reduceMotion.matches && dy) {
        sw.v += Math.max(-60, Math.min(60, dy * -0.5));
        wake();
      }
    },
    { passive: true }
  );

  window.addEventListener("resize", () => {
    applyHeroLayout();
    evaluate();
    if (floating) wake();
  });
  desktop.addEventListener("change", evaluate);

  applyHeroLayout();

  // Landing mid-page (reload, anchor link): start already docked, no drop.
  if (desktop.matches && slot.getBoundingClientRect().top < o.dockAt) {
    docked = true;
    beginFloating();
    snap();
  }

  return {
    isFloating: () => floating,
    setExpanded(next) {
      if (expanded === next) return;
      expanded = next;
      root.classList.toggle("is-expanded", next && floating && docked);
      if (floating && docked) wake();
    },
  };
}
