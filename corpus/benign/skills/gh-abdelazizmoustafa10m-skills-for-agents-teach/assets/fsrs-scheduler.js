/* teach optional asset: compact FSRS-6 scheduler for `[data-fsrs-card]` or `.fsrs-card` decks. */
(function () {
  "use strict";
  var root = typeof window !== "undefined" ? window : globalThis;
  var MS_DAY = 86400000;
  var VERSION = "FSRS-6";
  var DEFAULT_RETENTION = 0.9;
  var W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
    1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
    1.8729, 0.5425, 0.0912, 0.0658, 0.1542];
  var LABELS = { 1: "Again", 2: "Hard", 3: "Good", 4: "Easy" };
  function clamp(n, lo, hi) { return Math.min(hi, Math.max(lo, n)); }
  function num(v, fallback) {
    v = Number(v);
    return Number.isFinite(v) ? v : fallback;
  }
  function iso(date) { return date.toISOString(); }
  function dateOf(value, fallback) {
    var d = value ? new Date(value) : null;
    return d && !Number.isNaN(d.getTime()) ? d : fallback;
  }
  function initialStability(grade) { return Math.max(0.01, W[grade - 1]); }
  function initialDifficulty(grade) { return clamp(W[4] - Math.exp(W[5] * (grade - 1)) + 1, 1, 10); }
  function nextDifficulty(difficulty, grade) {
    var delta = -W[6] * (grade - 3);
    var damped = difficulty + delta * (10 - difficulty) / 9;
    return clamp(W[7] * initialDifficulty(4) + (1 - W[7]) * damped, 1, 10);
  }
  function retrievability(days, stability) {
    if (!stability) return 0;
    var factor = Math.pow(0.9, -1 / W[20]) - 1;
    return Math.pow(1 + factor * Math.max(0, days) / stability, -W[20]);
  }
  function nextInterval(stability, retention) {
    retention = clamp(num(retention, DEFAULT_RETENTION), 0.7, 0.98);
    var factor = Math.pow(0.9, -1 / W[20]) - 1;
    var days = stability / factor * (Math.pow(retention, -1 / W[20]) - 1);
    return Math.max(1 / 1440, days);
  }
  function sameDayStability(stability, grade) {
    var inc = Math.exp(W[17] * (grade - 3 + W[18])) * Math.pow(stability, -W[19]);
    var next = stability * inc;
    return grade >= 3 ? Math.max(stability, next) : Math.max(0.01, next);
  }
  function recallStability(difficulty, stability, r, grade) {
    var hard = grade === 2 ? W[15] : 1;
    var easy = grade === 4 ? W[16] : 1;
    var inc = Math.exp(W[8]) * (11 - difficulty) * Math.pow(stability, -W[9]) *
      (Math.exp(W[10] * (1 - r)) - 1) * hard * easy + 1;
    return Math.max(stability, stability * inc);
  }
  function forgetStability(difficulty, stability, r) {
    return Math.max(0.01, W[11] * Math.pow(difficulty, -W[12]) *
      (Math.pow(stability + 1, W[13]) - 1) * Math.exp(W[14] * (1 - r)));
  }
  function normaliseEase(ease) {
    ease = num(ease, NaN);
    if (!Number.isFinite(ease)) return null;
    return ease > 100 ? ease / 1000 : ease > 10 ? ease / 100 : ease;
  }
  function migrate(card) {
    card = card || {};
    var out = {};
    Object.keys(card).forEach(function (k) { out[k] = card[k]; });
    out.fsrsVersion = 6;
    out.reps = Math.max(0, num(out.reps || out.repetitions || out.reviewCount, 0));
    out.lapses = Math.max(0, num(out.lapses, 0));
    if (Number.isFinite(Number(out.stability)) && Number.isFinite(Number(out.difficulty))) {
      out.stability = Math.max(0.01, Number(out.stability));
      out.difficulty = clamp(Number(out.difficulty), 1, 10);
      return out;
    }
    var interval = num(out.interval || out.ivl || out.days, NaN);
    var ease = normaliseEase(out.easeFactor || out.efactor || out.ease || out.factor);
    if (Number.isFinite(interval) || ease != null || out.repetitions != null) {
      out.stability = Math.max(0.1, num(interval, 1));
      out.difficulty = ease == null ? 5 : clamp(11 - ease * 3, 1, 10);
      out.migratedFrom = out.migratedFrom || "sm2";
      return out;
    }
    out.stability = null;
    out.difficulty = null;
    return out;
  }
  function review(card, grade, options) {
    options = options || {};
    grade = clamp(Math.round(Number(grade)), 1, 4);
    var now = dateOf(options.now, new Date());
    var out = migrate(card);
    var s = out.stability;
    var d = out.difficulty;
    var elapsed = out.lastReview ? Math.max(0, (now - dateOf(out.lastReview, now)) / MS_DAY) : 0;
    if (!s || !d) {
      s = initialStability(grade);
      d = initialDifficulty(grade);
    } else if (elapsed < 1) {
      s = sameDayStability(s, grade);
      d = nextDifficulty(d, grade);
    } else {
      var r = retrievability(elapsed, s);
      s = grade === 1 ? Math.min(forgetStability(d, s, r), s) : recallStability(d, s, r, grade);
      d = nextDifficulty(d, grade);
    }
    var interval = nextInterval(s, options.retention);
    out.stability = s;
    out.difficulty = d;
    out.reps += 1;
    out.lapses += grade === 1 ? 1 : 0;
    out.lastGrade = grade;
    out.lastReview = iso(now);
    out.interval = interval;
    out.due = iso(new Date(now.getTime() + interval * MS_DAY));
    return out;
  }
  function preview(card, options) {
    var p = {};
    [1, 2, 3, 4].forEach(function (grade) {
      var next = review(card, grade, options);
      p[grade] = { label: LABELS[grade], interval: next.interval, due: next.due, state: next };
    });
    return p;
  }
  function human(days) {
    if (days < 1 / 24) return Math.max(1, Math.round(days * 1440)) + "m";
    if (days < 1) return Math.round(days * 24) + "h";
    if (days < 45) return Math.round(days) + "d";
    if (days < 365) return Math.round(days / 30) + "mo";
    return Math.round(days / 365 * 10) / 10 + "y";
  }
  function storage() {
    try {
      var s = root.localStorage, k = "__teach_fsrs_probe__";
      s.setItem(k, "1"); s.removeItem(k);
      return s;
    } catch (_) { return null; }
  }
  function lessonKey() {
    var meta = document.querySelector('meta[name="teach:lesson"]');
    return "teach:fsrs:v1:" + ((meta && meta.content) || location.pathname);
  }
  function loadStates(key) {
    var s = storage();
    if (!s) return {};
    try { return JSON.parse(s.getItem(key) || "{}") || {}; } catch (_) { return {}; }
  }
  function saveStates(key, states) {
    var s = storage();
    if (!s) return;
    try { s.setItem(key, JSON.stringify(states)); } catch (_) {}
  }
  function stateFromElement(el) {
    var state = {};
    ["stability", "difficulty", "interval", "ease", "easeFactor", "reps", "repetitions", "due", "lastReview"].forEach(function (k) {
      var attr = "data-" + k.replace(/[A-Z]/g, function (m) { return "-" + m.toLowerCase(); });
      if (el.hasAttribute(attr)) state[k] = el.getAttribute(attr);
    });
    var raw = el.getAttribute("data-fsrs-state") || el.getAttribute("data-card-state");
    if (raw) {
      try {
        var parsed = JSON.parse(raw);
        Object.keys(parsed).forEach(function (k) { state[k] = parsed[k]; });
      } catch (_) {}
    }
    return state;
  }
  function renderCard(el, id, states, key) {
    var state = states[id] || stateFromElement(el);
    var bar = el.querySelector(".fsrs-gradebar");
    if (!bar) {
      bar = document.createElement("div");
      bar.className = "fsrs-gradebar";
      bar.style.cssText = "display:flex;flex-wrap:wrap;gap:.5rem;margin:.75rem 0;font-family:var(--font-sans,system-ui,sans-serif)";
      el.appendChild(bar);
    }
    bar.innerHTML = "";
    var choices = preview(state);
    [1, 2, 3, 4].forEach(function (grade) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = choices[grade].label + " " + human(choices[grade].interval);
      btn.title = "Next review: " + new Date(choices[grade].due).toLocaleString();
      btn.style.cssText = "font:inherit;padding:.25rem .55rem;border:1px solid var(--border,currentColor);border-radius:var(--r-sm,6px);background:var(--surface-2,transparent);color:inherit;cursor:pointer";
      btn.addEventListener("click", function () {
        var next = review(state, grade);
        states[id] = next;
        saveStates(key, states);
        el.setAttribute("data-fsrs-due", next.due);
        document.dispatchEvent(new CustomEvent("teach:fsrs-reviewed", { detail: { id: id, grade: grade, state: next } }));
        document.dispatchEvent(new CustomEvent("teach:graded", { detail: { id: id, correct: grade > 1, type: "fsrs", grade: grade } }));
        renderCard(el, id, states, key);
      });
      bar.appendChild(btn);
    });
  }
  function bind(rootEl) {
    if (!root.document) return;
    rootEl = rootEl || document;
    var key = lessonKey();
    var states = loadStates(key);
    Array.prototype.forEach.call(rootEl.querySelectorAll("[data-fsrs-card], .fsrs-card"), function (el) {
      var id = el.getAttribute("data-fsrs-card") || el.getAttribute("data-id") || el.id;
      if (!id || id === "off") return;
      renderCard(el, id, states, key);
    });
  }
  root.TeachFSRS = {
    version: VERSION,
    weights: W.slice(),
    migrate: migrate,
    review: review,
    preview: preview,
    retrievability: retrievability,
    nextInterval: nextInterval,
    bind: bind
  };
  if (root.document) {
    if (document.readyState !== "loading") bind();
    else document.addEventListener("DOMContentLoaded", function () { bind(); });
  }
})();
