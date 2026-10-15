/*
  ui_check.js: read-only checks for controls and overlays on a rendered page.

  Run it on every changed page, and again with each overlay open (dialog,
  drawer, menu, select list, popover, toast):
    - Playwright:
        await page.addScriptTag({ path: "<skill>/scripts/ui_check.js" });
        const result = await page.evaluate(() => uiCheck());
    - Browser console: paste the file, then run uiCheck().

  It reports:
    - controls in one row with different heights, corner radii or text sizes;
    - a page that still scrolls behind an open modal;
    - clicks outside a modal that reach the page;
    - see-through overlays and sticky bars;
    - overlays covered by other layers or cut off by the screen edge;
    - dialogs taller than the screen, scrolling as a whole, or hiding their
      actions below the visible area;
    - media that fills most of a dialog;
    - oversized close buttons;
    - focus left outside an open modal.

  Every issue is a measurement, not a verdict: fix it, or write down why the
  design needs it. The script changes nothing on the page.
*/
(function () {
  "use strict";

  var CONTROL = [
    "button", "a.btn", "a[class*='button']", "[role='button']", "select", "textarea", "[role='combobox']",
    "input:not([type='hidden']):not([type='checkbox']):not([type='radio']):not([type='range']):not([type='file'])"
  ].join(",");
  var CLOSE = "[data-dialog-close]:not([value]), [aria-label*='close' i], [aria-label*='kapat' i], [aria-label*='dismiss' i], [aria-label*='schlie' i], [aria-label*='fermer' i], [aria-label*='cerrar' i]";

  function describe(el) {
    if (!el || el.nodeType !== 1) return String(el);
    var name = el.tagName.toLowerCase();
    if (el.id) name += "#" + el.id;
    var cls = (el.getAttribute("class") || "").trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (cls.length) name += "." + cls.join(".");
    var text = (el.getAttribute("aria-label") || el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 32);
    return text ? name + ' "' + text + '"' : name;
  }

  function isVisible(el) {
    if (!el || !el.getBoundingClientRect) return false;
    var r = el.getBoundingClientRect();
    var cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && parseFloat(cs.opacity) > 0.01;
  }

  function alphaOf(color) {
    if (!color || color === "transparent") return 0;
    var m = color.match(/rgba?\(([^)]+)\)/);
    if (m) {
      var parts = m[1].split(/[\s,\/]+/).filter(Boolean);
      return parts.length > 3 ? parseFloat(parts[3]) * (parts[3].indexOf("%") > -1 ? 0.01 : 1) : 1;
    }
    var slash = color.match(/\/\s*([\d.]+%?)\s*\)/);
    if (slash) return parseFloat(slash[1]) * (slash[1].indexOf("%") > -1 ? 0.01 : 1);
    return 1;
  }

  function isOpaque(el) {
    var cs = getComputedStyle(el);
    var blur = cs.backdropFilter || cs.webkitBackdropFilter || "none";
    return alphaOf(cs.backgroundColor) >= 0.95 || (blur !== "none" && alphaOf(cs.backgroundColor) >= 0.7);
  }

  function inside(el, container) {
    return !!el && (el === container || container.contains(el));
  }

  function controlText(el) {
    var total = (el.textContent || "").replace(/\s+/g, "").length;
    Array.prototype.forEach.call(el.querySelectorAll(CONTROL), function (c) {
      total -= (c.textContent || "").replace(/\s+/g, "").length;
    });
    Array.prototype.forEach.call(el.querySelectorAll(".visually-hidden, .sr-only, [class*='visually-hidden']"), function (h) {
      total -= (h.textContent || "").replace(/\s+/g, "").length;
    });
    return total;
  }

  // A box in a row: a control, or a small wrapper around one to four controls
  // (a label around a field, a search field with its icon, a segmented group).
  function isControlBox(el) {
    if (!isVisible(el)) return false;
    if (el.matches(CONTROL)) return true;
    if (el.matches("article, section, li, p, form, fieldset, ul, ol, table, nav, header, footer, main, aside")) return false;
    var count = el.querySelectorAll(CONTROL).length;
    return count >= 1 && count <= 4 && controlText(el) <= 24 && el.getBoundingClientRect().height <= 80;
  }

  function checkRows(issues) {
    var rows = new Set();
    Array.prototype.forEach.call(document.querySelectorAll(CONTROL), function (control) {
      if (!isVisible(control)) return;
      for (var n = control.parentElement, depth = 0; n && depth < 4; n = n.parentElement, depth++) rows.add(n);
    });
    rows.forEach(function (row) {
      var display = getComputedStyle(row).display;
      if (display.indexOf("flex") === -1 && display.indexOf("grid") === -1) return;
      var boxes = Array.prototype.filter.call(row.children, isControlBox);
      if (boxes.length < 2) return;
      var mids = boxes.map(function (b) { var r = b.getBoundingClientRect(); return r.top + r.height / 2; });
      var line = boxes.filter(function (b, i) { return Math.abs(mids[i] - mids[0]) < 12; });
      if (line.length < 2) return;
      var heights = line.map(function (b) { return Math.round(b.getBoundingClientRect().height); });
      if (Math.max.apply(null, heights) - Math.min.apply(null, heights) > 2) {
        issues.push({ check: "controls-height", where: describe(row), detail: "Controls in one row have different heights: " + heights.join(", ") + " px. Use one control height." });
      }
      var radii = line.map(function (b) {
        var target = b.matches(CONTROL) || getComputedStyle(b).borderTopWidth !== "0px" ? b : b.querySelector(CONTROL);
        var cs = getComputedStyle(target);
        var framed = cs.borderTopWidth !== "0px" || alphaOf(cs.backgroundColor) > 0.05;
        return framed ? cs.borderTopLeftRadius : null;
      }).filter(Boolean);
      var distinct = radii.filter(function (v, i) { return radii.indexOf(v) === i; });
      if (distinct.length > 1) {
        issues.push({ check: "controls-radius", where: describe(row), detail: "Controls in one row have different corner radii: " + radii.join(", ") + "." });
      }
      var sizes = line.map(function (b) {
        var target = b.matches(CONTROL) ? b : b.querySelector("input, select, textarea") || b.querySelector(CONTROL);
        var hasText = target && (target.matches("input, select, textarea") || (target.textContent || "").trim().length > 1);
        return hasText ? getComputedStyle(target).fontSize : null;
      }).filter(Boolean);
      var distinctSizes = sizes.filter(function (v, i) { return sizes.indexOf(v) === i; });
      if (distinctSizes.length > 1) {
        issues.push({ check: "controls-text", where: describe(row), detail: "Controls in one row use different text sizes: " + sizes.join(", ") + "." });
      }
    });
  }

  function openModals() {
    var list = [];
    Array.prototype.forEach.call(document.querySelectorAll("dialog[open]"), function (d) {
      var modal = false;
      try { modal = d.matches(":modal"); } catch (e) { modal = false; }
      if (modal) list.push(d);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[aria-modal='true']"), function (d) {
      if (isVisible(d) && list.indexOf(d) === -1) list.push(d);
    });
    return list;
  }

  function checkModal(modal, issues) {
    var where = describe(modal);
    var root = document.scrollingElement || document.documentElement;
    var htmlCs = getComputedStyle(document.documentElement);
    var bodyCs = getComputedStyle(document.body);
    var pageScrolls = root.scrollHeight > window.innerHeight + 1;
    var locked = /hidden|clip/.test(htmlCs.overflowY) || /hidden|clip/.test(bodyCs.overflowY) || bodyCs.position === "fixed";
    if (pageScrolls && !locked) {
      issues.push({ check: "modal-scroll-lock", where: where, detail: "The page behind the open dialog can still scroll. Lock it (overflow: hidden on the root while the dialog is open)." });
    }
    var r = modal.getBoundingClientRect();
    var points = [[4, 4], [window.innerWidth - 4, 4], [4, window.innerHeight - 4], [window.innerWidth - 4, window.innerHeight - 4],
      [r.left - 12, r.top + r.height / 2], [r.right + 12, r.top + r.height / 2], [r.left + r.width / 2, r.top - 12], [r.left + r.width / 2, r.bottom + 12]];
    var leaks = [];
    points.forEach(function (pt) {
      if (pt[0] < 0 || pt[1] < 0 || pt[0] > window.innerWidth || pt[1] > window.innerHeight) return;
      var hit = document.elementFromPoint(pt[0], pt[1]);
      if (!hit || inside(hit, modal)) return;
      var hr = hit.getBoundingClientRect();
      var coversScreen = hr.width >= window.innerWidth * 0.9 && hr.height >= window.innerHeight * 0.9 && getComputedStyle(hit).position === "fixed";
      if (!coversScreen) leaks.push(describe(hit));
    });
    if (leaks.length) {
      issues.push({ check: "modal-click-through", where: where, detail: leaks.length + " of the points tested outside the dialog reach the page (for example " + leaks[0] + "). Cover the page with a backdrop and make it inert." });
    }
    if (!isOpaque(modal) && !Array.prototype.some.call(modal.children, isOpaque)) {
      issues.push({ check: "overlay-opaque", where: where, detail: "The dialog surface is see-through; text behind it can show." });
    }
    if (r.top < -1 || r.bottom > window.innerHeight + 1) {
      issues.push({ check: "modal-fit", where: where, detail: "The dialog is taller than the screen (" + Math.round(r.height) + " of " + window.innerHeight + " px). Cap its height and let only the body scroll." });
    }
    var modalCs = getComputedStyle(modal);
    if (/auto|scroll/.test(modalCs.overflowY) && modal.scrollHeight > modal.clientHeight + 1) {
      issues.push({ check: "modal-scroll", where: where, detail: "The whole dialog scrolls, header and actions included. Keep them fixed and let only the body scroll." });
    }
    Array.prototype.forEach.call(modal.querySelectorAll("*"), function (el) {
      var cs = getComputedStyle(el);
      if (/auto|scroll/.test(cs.overflowY) && el.scrollHeight > el.clientHeight + 1 && el.clientHeight > 0) {
        issues.push({ check: "modal-body-scroll", where: describe(el), detail: "Dialog content scrolls: " + (el.scrollHeight - el.clientHeight) + " px are hidden. Check that the content really needs it (a smaller image or a wider dialog often removes the scroll)." });
      }
    });
    Array.prototype.forEach.call(modal.querySelectorAll("img, video, picture, canvas, svg"), function (m) {
      var mr = m.getBoundingClientRect();
      if (mr.height > window.innerHeight * 0.45) {
        issues.push({ check: "modal-media", where: describe(m), detail: "Media fills " + Math.round(mr.height / window.innerHeight * 100) + "% of the screen height inside the dialog. Cap it (about 35-40%) so the text and actions stay visible." });
      }
    });
    function isIconClose(b) {
      var text = (b.textContent || "").trim();
      return (b.matches(CLOSE) || /^[×✕✖xX]$/.test(text)) && (text === "" || /^[×✕✖xX]$/.test(text));
    }
    var actions = Array.prototype.filter.call(modal.querySelectorAll("button, a[href], [role='button']"), function (b) {
      return isVisible(b) && !isIconClose(b);
    });
    var last = actions[actions.length - 1];
    if (last) {
      var lr = last.getBoundingClientRect();
      var visibleBottom = Math.min(window.innerHeight, r.bottom);
      var scroller = Array.prototype.find.call(modal.querySelectorAll("*"), function (el) {
        return el.contains(last) && /auto|scroll/.test(getComputedStyle(el).overflowY) && el.scrollHeight > el.clientHeight + 1;
      });
      if (lr.bottom > visibleBottom + 1 || scroller) {
        issues.push({ check: "modal-actions", where: describe(last), detail: "The dialog's main action is not visible without scrolling. Put actions in a fixed footer." });
      }
    }
    Array.prototype.forEach.call(modal.querySelectorAll("button, [role='button']"), function (b) {
      if (!isVisible(b) || !isIconClose(b)) return;
      var br = b.getBoundingClientRect();
      if (br.width > 44 || br.height > 44) {
        issues.push({ check: "close-size", where: describe(b), detail: "The close button is " + Math.round(br.width) + "x" + Math.round(br.height) + " px. Use a quiet icon button of about 36-40 px with a 20 px icon." });
      }
    });
    var active = document.activeElement;
    if (!inside(active, modal)) {
      issues.push({ check: "modal-focus", where: where, detail: "Focus is outside the open dialog (" + describe(active) + ")." });
    } else if (isIconClose(active) && active.matches(":focus-visible")) {
      issues.push({ check: "modal-initial-focus", where: describe(active), detail: "The dialog opened with a focus ring on the close button. Focus the title or the first field instead." });
    }
  }

  function checkLayer(el, issues, kind) {
    var r = el.getBoundingClientRect();
    if (!isOpaque(el) && !Array.prototype.some.call(el.children, isOpaque)) {
      issues.push({ check: "overlay-opaque", where: describe(el), detail: "This " + kind + " is see-through; the text under it shows and mixes with its own." });
    }
    var cx = Math.min(Math.max(r.left + r.width / 2, 0), window.innerWidth - 1);
    var cy = Math.min(Math.max(r.top + Math.min(r.height / 2, 20), 0), window.innerHeight - 1);
    var hit = document.elementFromPoint(cx, cy);
    if (hit && !inside(hit, el)) {
      issues.push({ check: "overlay-covered", where: describe(el), detail: "This " + kind + " is covered by " + describe(hit) + ". Check the layer order." });
    }
    if (r.left < -1 || r.top < -1 || r.right > window.innerWidth + 1 || r.bottom > window.innerHeight + 1) {
      issues.push({ check: "overlay-offscreen", where: describe(el), detail: "This " + kind + " is cut off by the edge of the screen." });
    }
  }

  function checkOverlays(issues) {
    var modals = openModals();
    modals.forEach(function (m) { checkModal(m, issues); });
    var candidates = [];
    try { candidates = candidates.concat(Array.prototype.slice.call(document.querySelectorAll(":popover-open"))); } catch (e) { /* no popover support */ }
    candidates = candidates.concat(Array.prototype.slice.call(document.querySelectorAll("[role='menu'], [role='listbox'], [role='tooltip'], dialog[open]")));
    candidates.forEach(function (el) {
      if (modals.indexOf(el) > -1 || !isVisible(el)) return;
      var inModal = modals.some(function (m) { return m.contains(el); });
      if (modals.length && !inModal && !el.matches(":popover-open")) return;
      checkLayer(el, issues, "overlay");
    });
    Array.prototype.forEach.call(document.querySelectorAll("[role='status'], [role='alert'], .toast"), function (t) {
      if (!isVisible(t) || !t.textContent.trim()) return;
      var fixed = false;
      for (var n = t; n && n !== document.body; n = n.parentElement) {
        if (getComputedStyle(n).position === "fixed") { fixed = true; break; }
      }
      if (fixed) checkLayer(t, issues, "notification");
    });
    Array.prototype.forEach.call(document.querySelectorAll("header, nav, [class*='sticky'], [class*='bar']"), function (bar) {
      var cs = getComputedStyle(bar);
      if ((cs.position === "sticky" || cs.position === "fixed") && isVisible(bar) && !isOpaque(bar)) {
        issues.push({ check: "sticky-opaque", where: describe(bar), detail: "This sticky bar is see-through; content scrolling under it will mix with it." });
      }
    });
    return modals.length;
  }

  window.uiCheck = function uiCheck() {
    var issues = [];
    checkRows(issues);
    var modals = checkOverlays(issues);
    var unique = [];
    var keys = {};
    issues.forEach(function (i) {
      var key = i.check + "|" + i.where + "|" + i.detail;
      if (!keys[key]) { keys[key] = true; unique.push(i); }
    });
    if (typeof console !== "undefined" && console.table) console.table(unique);
    return { issues: unique, openModals: modals, url: location.href, viewport: window.innerWidth + "x" + window.innerHeight };
  };
})();
