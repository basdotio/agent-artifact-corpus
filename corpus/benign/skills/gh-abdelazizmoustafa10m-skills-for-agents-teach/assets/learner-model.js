/* ==========================================================================
   teach optional asset: learner-model.js
   Listens to `teach:graded` and keeps a tiny local model by author feature key.
   Privacy: this stores only feature keys, item ids, correctness, and timestamps
   in this browser's localStorage. It never stores answers and never uses network.
   Authors should keep ids/features non-sensitive.
   ========================================================================== */
(function () {
  "use strict";

  var VERSION = 1;
  var MAX_EVENTS = 500;
  var ALPHA = 0.35;          // EMA weight for the latest attempt.
  var DECAY_DAYS = 30;       // Calendar decay half-ish life for hit-rate strength.
  var MS_DAY = 86400000;
  var KEY = "teach:learner-model:v1";
  var BAK = KEY + ":backup";

  function storage() {
    try {
      var s = window.localStorage;
      var k = "__teach_lm_probe__";
      s.setItem(k, "1"); s.removeItem(k);
      return s;
    } catch (_) {
      return null;
    }
  }

  var store = storage();

  function readRaw(key) {
    if (!store) return null;
    try { return store.getItem(key); } catch (_) { return null; }
  }

  function parse(raw) {
    if (!raw) return { v: VERSION, events: [] };
    try {
      var data = JSON.parse(raw);
      if (data && data.v === VERSION && Array.isArray(data.events)) return data;
    } catch (_) {}
    return { v: VERSION, events: [] };
  }

  function load() {
    var data = parse(readRaw(KEY));
    if (!data.events.length) data = parse(readRaw(BAK));
    data.events = data.events.slice(-MAX_EVENTS);
    return data;
  }

  function save(data) {
    if (!store) return false;
    data.v = VERSION;
    data.events = data.events.slice(-MAX_EVENTS);
    data.updatedAt = new Date().toISOString();
    try {
      var old = store.getItem(KEY);
      if (old) store.setItem(BAK, old);
      store.setItem(KEY, JSON.stringify(data));
      return true;
    } catch (_) {
      try {
        data.events = data.events.slice(-Math.floor(MAX_EVENTS / 2));
        store.setItem(KEY, JSON.stringify(data));
        return true;
      } catch (__) {
        return false;
      }
    }
  }

  function lessonId() {
    var meta = document.querySelector('meta[name="teach:lesson"]');
    return (meta && meta.content) || document.title || location.pathname;
  }

  function splitKeys(value) {
    if (!value) return [];
    if (Array.isArray(value)) return value.map(String);
    return String(value).split(/[,\s|]+/);
  }

  function addKeys(out, value) {
    splitKeys(value).forEach(function (key) {
      key = key.trim();
      if (key && out.indexOf(key) === -1) out.push(key);
    });
  }

  function dataKeysFrom(el, out) {
    if (!el || !el.getAttribute) return;
    [
      "data-teach-features",
      "data-feature-keys",
      "data-features",
      "data-feature",
      "data-skill",
      "data-topic"
    ].forEach(function (name) { addKeys(out, el.getAttribute(name)); });
  }

  function lookupFeatureKeys(id, out) {
    if (!id || !document.querySelectorAll) return;
    Array.prototype.forEach.call(document.querySelectorAll("[data-id]"), function (el) {
      if (el.getAttribute("data-id") !== String(id)) return;
      dataKeysFrom(el, out);
      dataKeysFrom(el.closest && el.closest("[data-teach-features],[data-feature-keys],[data-features],[data-feature],[data-skill],[data-topic]"), out);
    });
  }

  function featureKeys(detail) {
    var out = [];
    addKeys(out, detail.featureKeys || detail.features || detail.keys || detail.feature);
    lookupFeatureKeys(detail.id, out);
    if (!out.length && detail.id) out.push((detail.type || "item") + ":" + detail.id);
    return out;
  }

  function cleanEvent(detail) {
    detail = detail || {};
    var keys = featureKeys(detail);
    if (!keys.length) return null;
    return {
      t: Date.now(),
      lesson: lessonId(),
      id: detail.id == null ? null : String(detail.id),
      type: detail.type == null ? null : String(detail.type),
      correct: !!detail.correct,
      keys: keys
    };
  }

  function record(detail) {
    if (!store) return false;
    var ev = cleanEvent(detail);
    if (!ev) return false;
    var data = load();
    data.events.push(ev);
    return save(data);
  }

  function decay(hitRate, from, to) {
    var days = Math.max(0, (to - from) / MS_DAY);
    return hitRate * Math.exp(-days / DECAY_DAYS);
  }

  function round(n) {
    return Math.round(n * 1000) / 1000;
  }

  function buildStats(events, now) {
    var stats = {};
    events.slice().sort(function (a, b) { return a.t - b.t; }).forEach(function (ev) {
      (ev.keys || []).forEach(function (key) {
        var s = stats[key] || (stats[key] = {
          key: key, n: 0, correct: 0, emaHitRate: 0, lastSeen: null
        });
        if (s.lastSeen != null) s.emaHitRate = decay(s.emaHitRate, s.lastSeen, ev.t);
        var hit = ev.correct ? 1 : 0;
        s.n += 1;
        s.correct += hit;
        s.emaHitRate = s.n === 1 ? hit : ALPHA * hit + (1 - ALPHA) * s.emaHitRate;
        s.lastSeen = ev.t;
      });
    });

    Object.keys(stats).forEach(function (key) {
      var s = stats[key];
      if (s.lastSeen != null) s.emaHitRate = decay(s.emaHitRate, s.lastSeen, now);
      s.confidence = 1 - Math.exp(-s.n / 8);
      s.hitRate = s.n ? s.correct / s.n : 0;
      s.strength = s.emaHitRate * s.confidence;
      s.weakness = 1 - s.strength;
      s.lastSeen = s.lastSeen ? new Date(s.lastSeen).toISOString() : null;
      ["emaHitRate", "hitRate", "confidence", "strength", "weakness"].forEach(function (field) {
        s[field] = round(s[field]);
      });
    });
    return stats;
  }

  function getWeakest(limit) {
    if (!store) return [];
    var stats = buildStats(load().events, Date.now());
    return Object.keys(stats).map(function (key) { return stats[key]; })
      .sort(function (a, b) {
        return b.weakness - a.weakness || a.confidence - b.confidence || a.key.localeCompare(b.key);
      })
      .slice(0, limit || 5);
  }

  var api = {
    version: VERSION,
    enabled: !!store,
    record: record,
    getWeakest: getWeakest,
    snapshot: function () { return store ? buildStats(load().events, Date.now()) : {}; }
  };

  window.TeachLearnerModel = api;
  if (!store) return;

  document.addEventListener("teach:graded", function (e) {
    record(e.detail);
  });
})();
