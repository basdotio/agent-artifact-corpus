/*
 * words.js: punchlines (big words landing one by one on the beat) and
 * captions (one line in a fixed band). Load after film.js.
 *
 * Every word is in the DOM from the start and keeps its slot (opacity and
 * transform only), so a centred line never re-centres while it builds.
 *
 *   const say = PF.punchlines(stage, [
 *     { lines: [[{ text: "Meet", at: b(3) }, { text: "Acme.", at: b(3, 2), accent: true }]],
 *       out: b(4) - 0.1, y: 860, size: 132 },
 *   ], THEME);
 *   ...in draw(t): say(t);
 *
 * THEME = { font, color, accent, weight, lineHeight, gap,
 *           enter: { length, rise, blur, ease }, exit: { length, blur } }
 * Take enter/exit from the product's motion tokens. If the product never
 * blurs, set blur: 0.
 */
(function () {
  const PF = window.PF;

  const defaults = {
    weight: 600,
    lineHeight: 1.08,
    gap: "0.26em",
    enter: { length: 0.3, rise: 36, blur: 16, ease: PF.bezier(0.22, 1, 0.36, 1) },
    exit: { length: 0.18, blur: 12, fall: 16 },
  };
  const merge = (theme) => Object.assign({}, defaults, theme, {
    enter: Object.assign({}, defaults.enter, theme && theme.enter),
    exit: Object.assign({}, defaults.exit, theme && theme.exit),
  });

  function wordEl(word) {
    const s = document.createElement("span");
    s.className = "pf-word" + (word.className ? " " + word.className : "");
    s.style.cssText = "display:inline-block";
    if (word.html) s.innerHTML = word.html; else s.textContent = word.text;
    if (word.dir) s.dir = word.dir;
    return s;
  }

  /** Big words, card by card. Returns draw(t). */
  PF.punchlines = function (parent, cards, theme) {
    const th = merge(theme);
    const built = cards.map((card) => {
      const box = document.createElement("div");
      box.className = "pf-card";
      if (card.dir) box.dir = card.dir;
      if (card.lang) box.lang = card.lang;
      box.style.cssText =
        `position:absolute;left:${card.left ?? 0}px;right:${card.right ?? 0}px;top:${card.y}px;` +
        `transform:translateY(-50%);display:grid;justify-items:${card.align || "center"};` +
        `font-family:${th.font};font-size:${card.size}px;font-weight:${card.weight || th.weight};` +
        `line-height:${th.lineHeight};color:${th.color};visibility:hidden`;
      const words = [];
      for (const line of card.lines) {
        const row = document.createElement("div");
        row.style.cssText = `display:flex;align-items:baseline;gap:${th.gap};white-space:nowrap`;
        for (const w of line) {
          const el = wordEl(w);
          if (w.accent) el.style.color = w.accentColor || th.accent;
          row.appendChild(el);
          words.push({ el, at: w.at });
        }
        box.appendChild(row);
      }
      parent.appendChild(box);
      return { card, box, words, first: Math.min(...words.map((w) => w.at)) };
    });

    return function (t) {
      for (const { card, box, words, first } of built) {
        const live = t >= first - 0.05 && t < card.out + th.exit.length + 0.05;
        PF.show(box, live);
        if (!live) continue;
        const leave = PF.clamp01((t - card.out) / th.exit.length);
        PF.css(box, {
          opacity: 1 - leave,
          filter: leave > 0 && th.exit.blur ? `blur(${(leave * th.exit.blur).toFixed(2)}px)` : "none",
        });
        for (const w of words) {
          const u = th.enter.ease(PF.clamp01((t - w.at) / th.enter.length));
          PF.css(w.el, {
            opacity: u,
            filter: u < 1 && th.enter.blur ? `blur(${((1 - u) * th.enter.blur).toFixed(2)}px)` : "none",
            transform: `translateY(${((1 - u) * th.enter.rise - leave * th.exit.fall).toFixed(2)}px)`,
          });
        }
      }
    };
  };

  /**
   * Captions: one short line at a time in a fixed band ({y, size}) that never
   * overlaps the UI. lines: [{text | html, at, out, y?, size?, weight?}]
   * (per-line y/size/weight override the band, e.g. a tagline). A line should hold at
   * least 4 beats. Returns draw(t).
   */
  PF.captions = function (parent, lines, band, theme) {
    const th = merge(theme);
    const els = lines.map((line) => {
      const el = document.createElement("div");
      el.className = "pf-caption";
      if (line.dir) el.dir = line.dir;
      el.style.cssText =
        `position:absolute;left:${band.left ?? 80}px;right:${band.right ?? 80}px;top:${line.y ?? band.y}px;transform:translateY(-50%);` +
        `text-align:${band.align || "center"};font-family:${th.font};font-size:${line.size ?? band.size}px;font-weight:${line.weight || band.weight || th.weight};` +
        `line-height:${band.lineHeight || 1.2};color:${th.color};visibility:hidden`;
      if (line.html) el.innerHTML = line.html; else el.textContent = line.text;
      parent.appendChild(el);
      return { el, line };
    });
    return function (t) {
      for (const { el, line } of els) {
        const s = PF.swap(t, line.at, line.out, { enter: th.enter.length, leave: th.exit.length, blur: th.enter.blur });
        const rise = (1 - PF.clamp01((t - line.at) / th.enter.length)) * Math.min(12, th.enter.rise);
        PF.swapStyle(el, s, { transform: `translateY(calc(-50% + ${rise.toFixed(2)}px))` });
      }
    };
  };
})();
