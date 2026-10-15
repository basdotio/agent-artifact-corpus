// The site's TextReveal, as a pure function of time: every word rises from its own mask.
// Lines are strings with light markup: *accent*  ~soft~  _outline_  {token}  (tokens are
// element factories passed in, e.g. an inline mascot or a brand mark).
import { h, clamp } from "../core/anim.js";
import { expoOut, inQuart } from "../core/ease.js";

const MARK = { "*": "acc", "~": "soft", _: "outl" };

function parse(line) {
  // → [{text, cls, token}] word runs; markup may span several words
  const out = [];
  let cls = null;
  let buf = "";
  const flush = () => {
    if (buf) out.push({ text: buf, cls });
    buf = "";
  };
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (MARK[c]) {
      flush();
      cls = cls === MARK[c] ? null : MARK[c];
    } else if (c === "{") {
      flush();
      const j = line.indexOf("}", i);
      out.push({ token: line.slice(i + 1, j), cls });
      i = j;
    } else buf += c;
  }
  flush();
  return out;
}

export class Words {
  /**
   * parent: element to fill. lines: string[] (or a single string).
   * opts: { tokens: {name: () => Element}, lineCls, wordCls }
   */
  constructor(parent, lines, opts = {}) {
    this.el = parent;
    this.words = [];
    this.lines = [];
    this.cfgIn = null;
    this.cfgOut = null;
    const L = Array.isArray(lines) ? lines : [lines];
    L.forEach((line, li) => {
      const le = h("span", { class: `rv-line ${opts.lineCls ?? ""}` });
      let first = true;
      for (const run of parse(line)) {
        if (run.token) {
          const tokEl = opts.tokens?.[run.token]?.();
          if (!tokEl) continue;
          const m = h("span", { class: "rv-m rv-tok" }, h("span", { class: "rv-w" }, tokEl));
          le.appendChild(m);
          this.words.push({ m, w: m.firstChild, li, tok: true, el: tokEl });
          first = false;
          continue;
        }
        const parts = run.text.split(/( +)/);
        for (const p of parts) {
          if (!p) continue;
          if (/^ +$/.test(p)) {
            le.appendChild(document.createTextNode(" "));
            continue;
          }
          const w = h("span", { class: `rv-w ${run.cls ?? ""} ${opts.wordCls ?? ""}`, text: p });
          const m = h("span", { class: "rv-m" }, w);
          le.appendChild(m);
          this.words.push({ m, w, li, text: p });
          first = false;
        }
      }
      this.lines.push(le);
      parent.appendChild(le);
    });
  }

  /** Entrance: t0 start; per-word stagger, per-line delay, duration, rise (fraction of line). */
  in(t0, { stagger = 0.055, line = 0.12, dur = 0.9, ease = expoOut, rise = 1.1, fade = true, order = null } = {}) {
    this.cfgIn = { t0, stagger, line, dur, ease, rise, fade, order };
    return this;
  }
  /** Exit: words rise out of their masks (dir -1) or sink (dir 1). */
  out(t0, { stagger = 0.03, line = 0.05, dur = 0.5, ease = inQuart, rise = 1.1, dir = -1, fade = true } = {}) {
    this.cfgOut = { t0, stagger, line, dur, ease, rise, dir, fade };
    return this;
  }
  /** Times each word finishes entering (for sound or follow-on cues). */
  startOf(i) {
    const c = this.cfgIn;
    const w = this.words[i];
    const k = c.order ? c.order[i] : i;
    return c.t0 + k * c.stagger + w.li * c.line;
  }
  update(t) {
    const ci = this.cfgIn, co = this.cfgOut;
    this.words.forEach((w, i) => {
      let y = 0, a = 1;
      if (ci) {
        const k = ci.order ? ci.order[i] : i;
        const s = ci.t0 + k * ci.stagger + w.li * ci.line;
        const u = ci.ease(clamp((t - s) / ci.dur));
        y += (1 - u) * ci.rise * 100;
        if (ci.fade) a *= clamp(((t - s) / ci.dur) * 2.2);
      }
      if (co) {
        const s = co.t0 + i * co.stagger + w.li * co.line;
        const u = co.ease(clamp((t - s) / co.dur));
        y += co.dir * u * co.rise * 100;
        if (co.fade) a *= 1 - clamp((t - s) / co.dur) * 0.4;
      }
      const tf = `translateY(${y.toFixed(3)}%)`;
      if (w._tf !== tf) {
        w.w.style.transform = tf;
        w._tf = tf;
      }
      const op = a.toFixed(3);
      if (w._op !== op) {
        w.w.style.opacity = op;
        w._op = op;
      }
    });
  }
}

/** Letters instead of words (for a wordmark): same contract as Words. */
export class Letters extends Words {
  constructor(parent, text, opts = {}) {
    super(parent, [""], opts);
    const le = this.lines[0];
    for (const ch of text) {
      const w = h("span", { class: `rv-w ${opts.wordCls ?? ""}`, text: ch });
      const m = h("span", { class: "rv-m" }, w);
      le.appendChild(m);
      this.words.push({ m, w, li: 0, text: ch });
    }
  }
}
