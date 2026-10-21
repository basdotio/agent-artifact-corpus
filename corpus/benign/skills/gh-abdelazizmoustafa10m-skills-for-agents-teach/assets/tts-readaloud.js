/* ==========================================================================
   teach optional asset: tts-readaloud.js
   Web Speech API read-aloud for explicit opt-ins only. Feature-detected,
   no dependency, no network, and never autoplays.
   ========================================================================== */
(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;
  var supported = !!(root.speechSynthesis && root.SpeechSynthesisUtterance);
  var current = null;

  function clamp(n, lo, hi) {
    n = Number(n);
    return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : null;
  }

  function closestLang(node) {
    if (node && node.closest) {
      var langNode = node.closest("[data-lang],[lang]");
      if (langNode) return langNode.getAttribute("data-lang") || langNode.getAttribute("lang");
    }
    if (root.document && document.documentElement) {
      return document.documentElement.getAttribute("data-lang") ||
        document.documentElement.getAttribute("lang");
    }
    return root.navigator && navigator.language;
  }

  function targetFor(control) {
    var sel = control.getAttribute("data-tts-target") ||
      control.getAttribute("data-readaloud-target") ||
      control.getAttribute("data-readaloud");
    if (sel && sel !== "true" && root.document) {
      try { return document.querySelector(sel) || control; } catch (_) { return control; }
    }
    return control;
  }

  function textFor(source) {
    if (source == null) return "";
    if (typeof source === "string") return source.trim();
    return (source.getAttribute && (source.getAttribute("data-tts-text") ||
      source.getAttribute("aria-label"))) || (source.textContent || "").trim();
  }

  function stop() {
    if (!supported) return;
    root.speechSynthesis.cancel();
    current = null;
  }

  function speak(source, options) {
    if (!supported) return false;
    options = options || {};
    var text = textFor(source);
    if (!text) return false;
    var u = new root.SpeechSynthesisUtterance(text);
    u.lang = options.lang || (source && source.getAttribute && source.getAttribute("data-lang")) ||
      closestLang(source) || "en";
    var rate = clamp(options.rate || (source && source.getAttribute && source.getAttribute("data-rate")), 0.5, 1.5);
    var pitch = clamp(options.pitch || (source && source.getAttribute && source.getAttribute("data-pitch")), 0, 2);
    if (rate != null) u.rate = rate;
    if (pitch != null) u.pitch = pitch;
    u.onend = u.onerror = function () { current = null; };
    stop();
    current = u;
    root.speechSynthesis.speak(u);
    return true;
  }

  function styleButton(btn) {
    btn.style.cssText = "font:inherit;font-family:var(--font-sans,system-ui,sans-serif);padding:.2rem .55rem;margin:.25rem 0 .5rem;border:1px solid var(--border,currentColor);border-radius:var(--r-sm,6px);background:var(--surface-2,transparent);color:inherit;cursor:pointer";
  }

  function bind(rootEl) {
    if (!supported || !root.document) return;
    rootEl = rootEl || document;

    Array.prototype.forEach.call(rootEl.querySelectorAll("[data-readaloud],[data-tts-target]"), function (control) {
      if (control.__teachTtsBound) return;
      control.__teachTtsBound = true;
      control.addEventListener("click", function () { speak(targetFor(control)); });
    });

    Array.prototype.forEach.call(rootEl.querySelectorAll("[data-tts]"), function (el) {
      if (el.__teachTtsBound) return;
      el.__teachTtsBound = true;
      if (/^(BUTTON|A)$/i.test(el.tagName) || el.getAttribute("role") === "button") {
        el.addEventListener("click", function (e) {
          if (el.tagName === "A") e.preventDefault();
          speak(targetFor(el));
        });
        return;
      }
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tts-readaloud__button";
      btn.textContent = el.getAttribute("data-tts-label") || "Read aloud";
      btn.setAttribute("aria-label", btn.textContent);
      styleButton(btn);
      btn.addEventListener("click", function () { speak(el); });
      el.parentNode.insertBefore(btn, el);
    });
  }

  root.TeachReadAloud = {
    supported: supported,
    speak: speak,
    stop: stop,
    bind: bind,
    speaking: function () { return !!current; }
  };

  if (supported && root.document) {
    if (document.readyState !== "loading") bind();
    else document.addEventListener("DOMContentLoaded", function () { bind(); });
  }
})();
