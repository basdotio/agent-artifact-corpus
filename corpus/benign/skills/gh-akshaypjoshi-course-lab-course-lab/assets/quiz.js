/* course-lab quiz runtime. Mounts every <section class="lab" data-quiz="base64(json)">.
   Grading happens here, in the page; answers are only base64-obscured, which is enough for self-study. */
(function () {
  "use strict";
  var W = { easy: 1, medium: 2, hard: 3 };
  var KEYS = "ABCDEF";

  function decode(b64) {
    var bin = atob(b64), bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return JSON.parse(new TextDecoder().decode(bytes));
  }
  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function md(s) { // inline only: `code`, **bold**, *em*
    return esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  }
  function el(tag, cls, html) { var n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; }
  function store(key, val) { try { if (val === undefined) return JSON.parse(localStorage.getItem(key) || "null"); localStorage.setItem(key, JSON.stringify(val)); } catch (e) { return null; } }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  function Quiz(root) {
    this.root = root;
    this.q = decode(root.getAttribute("data-quiz"));
    this.picks = {}; this.guess = {}; this.done = false; this.confirming = false;
    this.render();
  }

  Quiz.prototype.render = function () {
    var self = this, Q = this.q, root = this.root;
    root.innerHTML = "";
    var counts = { easy: 0, medium: 0, hard: 0 };
    Q.questions.forEach(function (q) { counts[q.difficulty]++; });
    var mins = Math.ceil(Q.questions.reduce(function (t, q) { return t + ({ easy: 45, medium: 75, hard: 120 })[q.difficulty]; }, 0) / 60);
    var head = el("div", "lab-head");
    head.appendChild(el("h2", "", (Q.num ? '<span class="num">' + esc(Q.num) + "</span>" : "") + esc(Q.heading || "Test yourself")));
    head.appendChild(el("div", "lab-meta",
      Q.questions.length + " questions · ~" + mins + " min " +
      ["easy", "medium", "hard"].map(function (d) { return counts[d] ? '<span class="lab-chip ' + d + '">' + counts[d] + " " + d + "</span>" : ""; }).join("")));
    root.appendChild(head);
    if (Q.intro) root.appendChild(el("p", "lab-intro", md(Q.intro)));
    this.resultBox = el("div"); root.appendChild(this.resultBox);

    this.cards = Q.questions.map(function (q, i) {
      var card = el("div", "lab-q"); card.id = (root.id || "quiz") + "-q" + (i + 1);
      card.appendChild(el("div", "lab-q-top", '<span class="lab-q-n">Q' + (i + 1) + '</span><span class="lab-chip ' + q.difficulty + '">' + q.difficulty + '</span><span class="lab-q-topic">' + esc(q.group && q.group !== q.topic ? q.group + " · " + q.topic : q.topic) + "</span>"));
      card.appendChild(el("p", "lab-q-text", md(q.question)));
      if (q.code) { var pre = el("pre"); pre.textContent = q.code; card.appendChild(pre); }
      var list = el("div", "lab-opts"); list.setAttribute("role", "group"); list.setAttribute("aria-label", "Options for question " + (i + 1));
      var btns = q.options.map(function (o, k) {
        var b = el("button", "lab-opt", '<span class="key">' + KEYS[k] + '</span><span class="txt">' + md(o) + "</span>");
        b.type = "button"; b.setAttribute("aria-pressed", "false");
        b.onclick = function () { if (!self.done) self.pick(i, k); };
        list.appendChild(b); return b;
      });
      card.appendChild(list);
      var foot = el("div", "lab-q-foot");
      var g = el("label", "lab-guess", '<input type="checkbox"> I\'m guessing');
      g.querySelector("input").onchange = function (e) { self.guess[i] = e.target.checked; };
      foot.appendChild(g);
      card.appendChild(foot);
      card._btns = btns; card._foot = foot; card._guess = g;
      root.appendChild(card);
      return card;
    });

    var bar = el("div", "lab-bar");
    this.prog = el("div", "lab-progress", "<i></i>");
    this.count = el("span", "lab-count");
    this.submit = el("button", "lab-btn primary", "Submit answers"); this.submit.type = "button";
    this.submit.onclick = function () { self.trySubmit(); };
    this.note = el("div", "lab-note");
    bar.appendChild(this.prog); bar.appendChild(this.count); bar.appendChild(this.submit); bar.appendChild(this.note);
    root.appendChild(bar); this.bar = bar;
    this.update();
  };

  Quiz.prototype.pick = function (i, k) {
    this.picks[i] = k; this.confirming = false; this.note.textContent = "";
    this.cards[i]._btns.forEach(function (b, j) { b.setAttribute("aria-pressed", j === k ? "true" : "false"); });
    this.update();
  };

  Quiz.prototype.update = function () {
    var n = Object.keys(this.picks).length, t = this.q.questions.length;
    this.prog.firstChild.style.width = (100 * n / t) + "%";
    this.count.textContent = n + " / " + t + " answered";
  };

  Quiz.prototype.trySubmit = function () {
    var blanks = this.q.questions.length - Object.keys(this.picks).length;
    if (blanks && !this.confirming) {
      this.confirming = true;
      this.note.textContent = blanks + " unanswered: they count as wrong. Press Submit again to finish, or answer them first.";
      return;
    }
    this.grade();
  };

  Quiz.prototype.grade = function () {
    var self = this, Q = this.q;
    this.done = true;
    var R = { right: 0, wrong: 0, blank: 0, pts: 0, max: 0, diff: {}, groups: {}, order: [], sure: [], lucky: [], items: [] };
    ["easy", "medium", "hard"].forEach(function (d) { R.diff[d] = { c: 0, t: 0 }; });
    Q.questions.forEach(function (q, i) {
      var p = self.picks[i], ok = p === q.answer, w = W[q.difficulty], g = q.group || q.topic;
      R.max += w; R.diff[q.difficulty].t++;
      if (!R.groups[g]) { R.groups[g] = { c: 0, t: 0, links: [] }; R.order.push(g); }
      R.groups[g].t++;
      if (!ok && q.link && !R.groups[g].links.some(function (l) { return l.href === q.link.href; })) R.groups[g].links.push(q.link);
      if (ok) { R.right++; R.pts += w; R.diff[q.difficulty].c++; R.groups[g].c++; if (self.guess[i]) R.lucky.push(i); }
      else if (p == null) R.blank++;
      else { R.wrong++; if (!self.guess[i]) R.sure.push(i); }
      R.items.push({ n: i + 1, d: q.difficulty, topic: q.topic, pick: p, ok: ok, guess: !!self.guess[i] });
      self.reveal(i, p, ok);
    });
    R.pct = R.max ? R.pts / R.max : 0;
    var hardNeed = Math.ceil(R.diff.hard.t * 2 / 3);
    R.level = R.pct >= 0.85 && R.diff.hard.c >= hardNeed ? 4 : R.pct >= 0.65 ? 3 : R.pct >= 0.4 ? 2 : 1;
    this.R = R;
    var hist = store("course-lab:" + Q.id) || [];
    hist.push({ t: Date.now(), s: R.right, n: Q.questions.length, p: Math.round(R.pct * 100), l: R.level });
    store("course-lab:" + Q.id, hist.slice(-10));
    this.showResult(hist);
    this.bar.style.display = "none";
    this.resultBox.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  Quiz.prototype.reveal = function (i, p, ok) {
    var q = this.q.questions[i], card = this.cards[i];
    card.classList.add(ok ? "is-correct" : p == null ? "is-blank" : "is-wrong");
    card._btns.forEach(function (b, k) {
      b.disabled = true;
      if (k === q.answer) b.classList.add("right");
      if (k === p && !ok) {
        b.classList.add("picked-wrong");
        if (q.rationales && q.rationales[k]) b.querySelector(".txt").insertAdjacentHTML("beforeend", '<span class="rat">' + md(q.rationales[k]) + "</span>");
      }
    });
    card._guess.querySelector("input").disabled = true;
    card._foot.insertBefore(el("span", "lab-verdict " + (ok ? "ok" : p == null ? "blank" : "bad"),
      ok ? (this.guess[i] ? "Correct · guessed" : "Correct") : p == null ? "Not answered" : (this.guess[i] ? "Wrong · guessed" : "Wrong")), card._foot.firstChild);
    var why = el("div", "lab-why", md(q.explanation) + (q.link ? ' <a href="' + esc(q.link.href) + '">Revisit: ' + esc(q.link.label) + " →</a>" : ""));
    card.appendChild(why);
  };

  var LEVELS = {
    4: ["Mastered", "You can use this, not just recognise it, including the hard cases."],
    3: ["Proficient", "Solid on the core; a few applications still slip."],
    2: ["Developing", "The basics are there; the reasoning behind them needs another pass."],
    1: ["Needs review", "Re-read the sections below before moving on: the core idea hasn't landed yet."],
  };

  Quiz.prototype.showResult = function (hist) {
    var self = this, R = this.R, Q = this.q, box = this.resultBox, n = Q.questions.length;
    var L = LEVELS[R.level];
    var html = '<div class="lab-result" role="region" aria-label="Your result">';
    html += '<div class="lab-score"><div class="lab-big">' + R.right + "<small>/" + n + "</small></div><div>" +
      '<span class="lab-badge l' + R.level + '">' + L[0] + '</span><div class="lab-level">' + Math.round(R.pct * 100) + "% weighted score</div>" +
      '<div class="lab-level-sub">' + L[1] + "</div></div></div>";
    html += '<div class="lab-stats"><span><b>' + R.right + "</b> correct</span><span><b>" + R.wrong + "</b> wrong</span><span><b>" + R.blank +
      "</b> blank</span><span><b>" + R.pts + "/" + R.max + "</b> points (easy 1 · medium 2 · hard 3)</span></div>";

    html += '<div class="lab-h">By difficulty</div><div class="lab-diff">';
    ["easy", "medium", "hard"].forEach(function (d) {
      var x = R.diff[d]; if (!x.t) return;
      var col = d === "easy" ? "var(--ok)" : d === "medium" ? "var(--warn)" : "var(--bad)";
      html += "<span>" + cap(d) + '</span><span class="track"><i style="width:' + (100 * x.c / x.t) + "%;background:" + col + '"></i></span><span class="v">' + x.c + "/" + x.t + "</span>";
    });
    html += "</div>";

    html += '<div class="lab-h">' + (Q.scope === "final" ? "By chapter" : "By topic") + '</div><ul class="lab-topics">';
    R.order.forEach(function (g) {
      var x = R.groups[g], r = x.c / x.t, st = r >= 0.8 ? "strong" : r >= 0.5 ? "developing" : "weak";
      html += "<li><span>" + esc(g) + ' <span class="lab-q-topic">' + x.c + "/" + x.t + '</span></span><span class="st ' + st + '">' + st + "</span>" +
        (x.links.length ? '<span class="go">' + x.links.slice(0, 3).map(function (l) { return '<a href="' + esc(l.href) + '">Revisit: ' + esc(l.label) + " →</a>"; }).join("<br>") + "</span>" : "") + "</li>";
    });
    html += "</ul>";

    var tips = [];
    if (R.sure.length) tips.push("<strong>Confident mistakes</strong> (fix these first; they're misconceptions, not gaps): " +
      R.sure.map(function (i) { return '<a href="#' + self.cards[i].id + '">Q' + (i + 1) + "</a>"; }).join(", ") + ".");
    if (R.lucky.length) tips.push("<strong>Right but guessed</strong>: " + R.lucky.map(function (i) { return '<a href="#' + self.cards[i].id + '">Q' + (i + 1) + "</a>"; }).join(", ") + ". Read the explanations; you can't rely on these yet.");
    if (R.diff.easy.t && R.diff.easy.c < R.diff.easy.t && R.diff.hard.c > 0) tips.push("You got hard questions right but missed an easy one. Slow down on the basics.");
    if (R.diff.hard.t && R.diff.hard.c === 0 && R.diff.easy.c + R.diff.medium.c >= (R.diff.easy.t + R.diff.medium.t) * 0.7)
      tips.push("You know the rules but not yet how to apply them under pressure: redo the hard questions after re-reading their linked sections.");
    if (R.blank) tips.push(R.blank + " left blank. An honest guess (marked as guessing) tells you more than a blank.");
    tips.push(R.level === 4 ? "Next: move on to the next chapter." : R.level === 3 ? "Next: review the explanations of what you missed, then retake in a day." :
      "Next: re-read the linked sections, then copy your results below and ask Claude for a targeted retest.");
    html += '<div class="lab-h">What to do next</div><ul class="lab-insights"><li>' + tips.join("</li><li>") + "</li></ul>";

    html += '<div class="lab-actions"><button type="button" class="lab-btn primary" data-act="copy">Copy results for Claude</button>' +
      '<button type="button" class="lab-btn" data-act="retake">Retake</button><span class="lab-copied" aria-live="polite"></span></div>';
    if (hist && hist.length > 1) html += '<div class="lab-history">Attempts: ' + hist.map(function (h) { return h.s + "/" + h.n + " (" + h.p + "%)"; }).join(" → ") + "</div>";
    html += "</div>";
    box.innerHTML = html;
    box.querySelector('[data-act="retake"]').onclick = function () { self.picks = {}; self.guess = {}; self.done = false; self.confirming = false; self.render(); self.root.scrollIntoView({ behavior: "smooth" }); };
    box.querySelector('[data-act="copy"]').onclick = function () { self.copy(box.querySelector(".lab-copied")); };
  };

  Quiz.prototype.report = function () {
    var R = this.R, Q = this.q;
    var lines = ["course-lab results", "Quiz: " + Q.title + " [" + Q.id + "]" + (Q.course ? " · " + Q.course : ""),
      "Score: " + R.right + "/" + Q.questions.length + " · weighted " + R.pts + "/" + R.max + " (" + Math.round(R.pct * 100) + "%) · level: " + LEVELS[R.level][0],
      "Difficulty: " + ["easy", "medium", "hard"].map(function (d) { return d + " " + R.diff[d].c + "/" + R.diff[d].t; }).join(", "), "Answers:"];
    var Qs = Q.questions;
    R.items.forEach(function (it) {
      var q = Qs[it.n - 1];
      lines.push("Q" + it.n + " [" + it.d + " · " + it.topic + "] " + (it.pick == null ? "blank" : "picked " + KEYS[it.pick]) +
        ": " + (it.ok ? "correct" : "wrong, answer " + KEYS[q.answer]) + (it.guess ? " (guessed)" : it.pick != null && !it.ok ? " (was sure)" : ""));
    });
    lines.push("", "Please evaluate me with the course-lab skill: diagnose my misconceptions, tell me exactly what to revise, and build a 10-question retest on my weak topics.");
    return lines.join("\n");
  };

  Quiz.prototype.copy = function (msg) {
    var text = this.report();
    function done() { msg.textContent = "Copied. Paste it into Claude."; }
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { msg.textContent = "Select and copy the text below."; }
      document.body.removeChild(ta);
    }
    try { navigator.clipboard.writeText(text).then(done, fallback); } catch (e) { fallback(); }
    this.root.setAttribute("data-report", text);
  };

  function mountAll() {
    [].forEach.call(document.querySelectorAll("section.lab[data-quiz]"), function (s) {
      if (s._lab) return;
      try { s._lab = new Quiz(s); } catch (e) { s.textContent = "Quiz failed to load: " + e.message; if (window.console) console.error(e); }
    });
  }
  window.CourseLab = { mountAll: mountAll };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountAll); else mountAll();
})();
