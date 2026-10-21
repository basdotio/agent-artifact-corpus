// Lanyard badge — framework-free version (plain ES module, no build step, no React).
//
//   import { initBadge } from "./badge/badge.js";
//   initBadge({ name: "Ada Lovelace", role: "Engineer", photo: "/badge/ada.webp", ... });
//
// Needs: an element `[data-badge-slot]` in the page (the badge mounts inside it) and
// badge.css loaded. See config shape below. The badge hangs from a lanyard, sways, flips to a
// details back on click and on a timer, and (on wide screens) drops into a floating dock as
// the page scrolls (dock.js). Everything is themed through CSS variables in badge.css.

import { createDock } from "./dock.js";

const TICK_MS = 100;

const DEFAULTS = {
  name: "YOUR NAME",
  role: "Your role or title",
  chip: "Short tagline", // keep under ~22 characters so it stays on one line
  photo: "",
  photoAlt: "Portrait",
  backHeading: "About",
  // 3 tiles fit best. `icon` is "search" | "shield" | "spark" | "code" | "cloud" | "user",
  // or a raw "<svg ...>" string.
  items: [],
  links: [], // [{ label, href }], up to 2 side by side
  cta: null, // { label, href }
  autoFlipMs: 5000, // 0 disables the automatic flip
  hint: "Click to flip ↻", // small line at the bottom of the front; "" hides it
  caption: "click the badge to flip it", // line under the badge in the page; "" hides it
  dock: {}, // false disables the scroll dock; or options for dock.js (see its DEFAULTS)
  slot: "[data-badge-slot]",
};

const svg = (d) =>
  `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;

const ICONS = {
  search: svg('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
  shield: svg('<path d="M12 3 4.5 6v5.5c0 4.6 3.1 8.2 7.5 9.5 4.4-1.3 7.5-4.9 7.5-9.5V6z"/><path d="m9 12 2 2 4-4"/>'),
  spark: svg('<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18"/>'),
  code: svg('<path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/>'),
  cloud: svg('<path d="M7 18a4 4 0 0 1-.6-7.96A6 6 0 0 1 18 9.5a4.25 4.25 0 0 1-.5 8.5z"/>'),
  user: svg('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
};

// Links may be relative, #anchors, http(s), mailto or tel. Any other scheme (javascript:, data:) becomes "#".
// Browsers ignore tabs, newlines and control characters inside a scheme, so strip them before testing.
const safeHref = (v) => {
  const s = String(v ?? "").trim();
  const bare = s.replace(/[\u0000-\u0020]/g, "");
  return /^[a-z][a-z\d+.-]*:/i.test(bare) && !/^(https?|mailto|tel):/i.test(bare) ? "#" : s;
};

// Light that runs around the holder edge (styled in badge.css, --badge-shine).
const BEAMS = `<span class="badge-beams" aria-hidden="true">${["top", "right", "bottom", "left"]
  .map((s) => `<i class="badge-beam is-${s}"></i>`)
  .join("")}${["tl", "tr", "br", "bl"].map((s) => `<i class="badge-spot is-${s}"></i>`).join("")}</span>`;

// Config strings are inserted as HTML, so escape them (icons are the one trusted exception).
const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function buildMarkup(c) {
  const tiles = c.items
    .map((it) => {
      const icon = typeof it.icon === "string" && it.icon.trimStart().startsWith("<svg") ? it.icon : ICONS[it.icon] || ICONS.spark;
      return `
        <li class="badge-tile">
          <span class="badge-tile-icon">${icon}</span>
          <span class="badge-tile-text">
            <span class="badge-tile-title">${esc(it.title)}</span>
            <span class="badge-tile-detail">${esc(it.detail)}</span>
          </span>
        </li>`;
    })
    .join("");
  const links = c.links
    .slice(0, 2)
    .map((l) => `<a class="badge-link" href="${esc(safeHref(l.href))}" target="_blank" rel="noopener noreferrer">${esc(l.label)}</a>`)
    .join("");
  const foot = [
    links ? `<div class="badge-links">${links}</div>` : "",
    c.cta ? `<a class="badge-cta" href="${esc(safeHref(c.cta.href))}">${esc(c.cta.label)}</a>` : "",
  ].join("");

  return `
    <div class="badge-swing" data-badge-swing>
      <div class="badge-sway">
        <div class="badge-strap" aria-hidden="true"></div>
        <div class="badge-clasp" aria-hidden="true"></div>

        <div class="badge-flip" data-badge-flip>
          <div class="badge-face badge-face-front" data-badge-face="front">
            <span class="badge-slot-pill" aria-hidden="true"></span>
            <div class="badge-card">
              <div class="badge-front">
                ${c.photo ? `<span class="badge-photo"><img src="${esc(c.photo)}" alt="${esc(c.photoAlt)}" width="188" height="188" decoding="async" /></span>` : ""}
                <p class="badge-name">${esc(c.name)}</p>
                <p class="badge-role">${esc(c.role)}</p>
                ${c.chip ? `<span class="badge-chip"><span class="badge-chip-dot" aria-hidden="true"></span>${esc(c.chip)}</span>` : ""}
                ${c.hint ? `<p class="badge-hint" aria-hidden="true">${esc(c.hint)}</p>` : ""}
              </div>
            </div>
            <span class="badge-glare" aria-hidden="true"></span>
            ${BEAMS}
            <button type="button" class="badge-hit" data-badge-front-hit aria-label="Flip the badge to see more details"></button>
          </div>

          <div class="badge-face badge-face-back" data-badge-face="back">
            <span class="badge-slot-pill" aria-hidden="true"></span>
            <div class="badge-card">
              <div class="badge-back">
                <div class="badge-back-head">
                  <p class="badge-back-label">${esc(c.backHeading)}</p>
                  <button type="button" class="badge-flip-back" data-badge-back-hit aria-label="Flip the badge back to the front">↻</button>
                </div>
                <ul class="badge-tiles">${tiles}</ul>
                <div class="badge-back-foot">${foot}</div>
              </div>
            </div>
            <span class="badge-glare" aria-hidden="true"></span>
            ${BEAMS}
          </div>
        </div>
        <div class="badge-ring" aria-hidden="true"></div>
      </div>
    </div>`;
}

export function initBadge(userConfig = {}) {
  const c = { ...DEFAULTS, ...userConfig };
  c.items = c.items || [];
  c.links = c.links || [];

  const slot = document.querySelector(c.slot);
  if (!slot) return null;
  // Already mounted here (React StrictMode runs effects twice, hot reload re-runs scripts): keep the first.
  if (slot.querySelector("[data-badge]")) return null;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const root = document.createElement("div");
  root.className = "badge-root";
  root.setAttribute("data-badge", "");
  root.setAttribute("role", "group");
  root.setAttribute("aria-label", `${c.name}'s badge`);
  root.innerHTML = buildMarkup(c);
  slot.prepend(root);

  if (c.caption) {
    const caption = document.createElement("p");
    caption.className = "badge-caption";
    caption.setAttribute("aria-hidden", "true");
    caption.textContent = c.caption;
    slot.append(caption);
  }

  const swing = root.querySelector("[data-badge-swing]");
  const flip = root.querySelector("[data-badge-flip]");
  const front = root.querySelector('[data-badge-face="front"]');
  const back = root.querySelector('[data-badge-face="back"]');

  // ---- Flip state -------------------------------------------------------------------------
  // `angle` only ever increases, so the badge always turns the same way. Even multiples of
  // 180 mean the front faces the viewer, odd multiples the back.
  let angle = 0;
  let manual = false; // visitor flipped it by hand: hold that side until they flip again
  let hovered = false;
  let focused = false;
  let elapsed = 0;
  let dock = null;

  const showingBack = () => Math.abs(Math.round(angle / 180)) % 2 !== 0;

  const syncFaces = () => {
    const isBack = showingBack();
    front.inert = isBack;
    back.inert = !isBack;
    front.setAttribute("aria-hidden", String(isBack));
    back.setAttribute("aria-hidden", String(!isBack));
  };

  const turn = (deg) => {
    angle += deg;
    flip.style.transform = `rotateY(${angle}deg)`;
    syncFaces();
  };

  const syncExpanded = () => {
    if (dock) dock.setExpanded(hovered || focused || manual);
  };

  front.querySelector("[data-badge-front-hit]").addEventListener("click", () => {
    manual = true;
    elapsed = 0;
    turn(180);
    syncExpanded();
  });

  const flipBackToFront = () => {
    manual = false;
    elapsed = 0;
    turn(180);
    syncExpanded();
  };
  back.querySelector("[data-badge-back-hit]").addEventListener("click", flipBackToFront);
  // Clicking anywhere else on the back flips it too, but never when the target is a link.
  back.addEventListener("click", (e) => {
    if (e.target.closest("a, button")) return;
    flipBackToFront();
  });

  // Hover and keyboard focus pause the timer so the card never turns mid-read.
  root.addEventListener("pointerenter", (e) => {
    if (e.pointerType !== "mouse") return;
    hovered = true;
    syncExpanded();
  });
  root.addEventListener("pointerleave", (e) => {
    if (e.pointerType !== "mouse") return;
    hovered = false;
    syncExpanded();
  });
  root.addEventListener("focusin", () => {
    focused = true;
    syncExpanded();
  });
  root.addEventListener("focusout", (e) => {
    if (root.contains(e.relatedTarget)) return;
    focused = false;
    syncExpanded();
  });

  if (c.autoFlipMs > 0) {
    setInterval(() => {
      if (document.hidden || reduceMotion.matches || hovered || focused || manual) return;
      elapsed += TICK_MS;
      if (elapsed >= c.autoFlipMs) {
        elapsed = 0;
        turn(180);
      }
    }, TICK_MS);
  }

  syncFaces();

  // ---- Entrance + dock --------------------------------------------------------------------
  dock =
    c.dock === false
      ? { isFloating: () => false, setExpanded() {} }
      : createDock({
          slot,
          root,
          swing,
          reduceMotion,
          options: c.dock || {},
          // The drop is punctuated by a full turn on the strap.
          onDock: () => turn(360),
        });

  // Entrance animation (drop + full spin) plays the first time the slot is on screen.
  const enter = () => {
    root.classList.add("is-in");
    if (!reduceMotion.matches && !dock.isFloating()) {
      angle = -360;
      flip.style.transition = "none";
      flip.style.transform = `rotateY(${angle}deg)`;
      void flip.offsetWidth;
      flip.style.transition = "";
      turn(360);
    }
  };

  if (dock.isFloating()) {
    enter();
  } else if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          enter();
        }
      },
      { threshold: 0.25 }
    );
    io.observe(slot);
  } else {
    enter();
  }

  return { root, flip: () => turn(180) };
}
