/* ==========================================================================
   teach · lesson-kit.js  —  shared authoring source, INLINED into each lesson.
   Progressive enhancement ONLY: every component is fully usable / legible with
   this script disabled (see lesson-kit.css @media print and the JS-off column
   in references/HTML-LESSON.md). No dependencies, no network, no storage.
   Grading emits a `teach:graded` CustomEvent {id, correct, type} on document so
   an optional future module (progress/SRS) can listen without this file knowing.
   ========================================================================== */
(function () {
  "use strict";
  // Mark that JS is live, so CSS can gate JS-only behaviour (e.g. the flashcard
  // crossfade) and fall back to a readable stacked layout when scripting is off.
  document.documentElement.classList.add("js");

  var ready = function (fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  };

  // Normalise free-text answers: Unicode NFC, trim, collapse spaces, fold case,
  // strip typographic quotes. (Umlauts/accents preserved — only quotes normalised.)
  function normalise(s) {
    return (s || "")
      .normalize("NFC")
      .trim()
      .replace(/\s+/g, " ")
      .replace(/[‘’‛]/g, "'")
      .replace(/[“”]/g, '"')
      .toLocaleLowerCase();
  }

  function emit(el, id, correct, type, extra) {
    var detail = { id: id || null, correct: !!correct, type: type };
    if (extra) {
      Object.keys(extra).forEach(function (key) { detail[key] = extra[key]; });
    }
    document.dispatchEvent(new CustomEvent("teach:graded", { detail: detail }));
  }

  function button(text, className, label) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = className;
    btn.textContent = text;
    if (label) btn.setAttribute("aria-label", label);
    return btn;
  }

  function reveal(el) {
    if (el) el.hidden = false;
  }

  function toArray(list) {
    return Array.prototype.slice.call(list);
  }

  ready(function () {
    // ---- MCQ ------------------------------------------------------------
    document.querySelectorAll(".quiz").forEach(function (quiz) {
      var why = quiz.querySelector(".quiz__why");
      var id = quiz.getAttribute("data-id");
      quiz.querySelectorAll(".quiz__option").forEach(function (opt) {
        opt.setAttribute("type", "button");
        opt.addEventListener("click", function () {
          if (quiz.dataset.answered) return;
          quiz.dataset.answered = "1";
          var correct = opt.getAttribute("data-correct") === "true";
          opt.classList.add(correct ? "is-correct" : "is-wrong");
          quiz.querySelectorAll(".quiz__option").forEach(function (o) {
            o.disabled = true;
            if (o.getAttribute("data-correct") === "true") o.classList.add("is-correct");
          });
          if (why) why.hidden = false;
          emit(quiz, id, correct, "mcq");
        });
      });
    });

    // ---- Cloze (fill-in-the-blank) -------------------------------------
    document.querySelectorAll(".cloze input").forEach(function (input) {
      var answers = (input.getAttribute("data-answer") || "").split("|").map(normalise);
      var check = function () {
        var val = normalise(input.value);
        if (!val) {
          input.classList.remove("is-correct", "is-wrong");
          input.__teachLastClozeGrade = "";
          return;
        }
        var ok = answers.indexOf(val) !== -1;
        input.classList.toggle("is-correct", ok);
        input.classList.toggle("is-wrong", !ok);
        var gradeKey = val + ":" + ok;
        if (input.__teachLastClozeGrade === gradeKey) return;
        input.__teachLastClozeGrade = gradeKey;
        emit(input, input.getAttribute("data-id"), ok, "cloze");
      };
      input.addEventListener("change", check);
      input.addEventListener("blur", check);
    });

    // ---- Flashcard flip (opacity crossfade) ----------------------------
    document.querySelectorAll(".flip").forEach(function (card) {
      if (!card.querySelector(".flip__hint")) {
        var hint = document.createElement("span");
        hint.className = "flip__hint"; hint.textContent = "click to flip";
        card.appendChild(hint);
      }
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      var flip = function () { card.classList.toggle("is-flipped"); };
      card.addEventListener("click", flip);
      card.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); flip(); }
      });
    });

    // ---- Faded worked example (reveal steps) ---------------------------
    document.querySelectorAll(".worked__step").forEach(function (step) {
      var ans = step.querySelector(".worked__answer");
      var btn = step.querySelector(".worked__reveal");
      if (ans && btn) {
        ans.hidden = true;
        btn.setAttribute("type", "button");
        btn.addEventListener("click", function () {
          ans.hidden = false; btn.hidden = true;
          emit(step, step.getAttribute("data-id"), true, "worked");
        });
      }
    });

    // ---- Ordering / sequence ------------------------------------------
    document.querySelectorAll(".sequence").forEach(function (seq) {
      var id = seq.getAttribute("data-id");
      var list = seq.querySelector(".sequence__list");
      if (!list) return;
      var check = seq.querySelector(".sequence__check");
      if (!check) {
        check = button("Check order", "sequence__check", null);
        seq.appendChild(check);
      } else {
        check.type = "button";
      }
      var feedback = seq.querySelector(".sequence__feedback");
      if (!feedback) {
        feedback = document.createElement("p");
        feedback.className = "sequence__feedback";
        feedback.setAttribute("aria-live", "polite");
        feedback.hidden = true;
        seq.appendChild(feedback);
      }
      var answer = seq.querySelector(".sequence__answer");
      var why = seq.querySelector(".sequence__why");

      function items() {
        return toArray(list.querySelectorAll(".sequence__item"));
      }
      function itemLabel(item) {
        var explicit = item.getAttribute("data-label") || item.getAttribute("aria-label");
        if (explicit) return explicit.trim();
        var clone = item.cloneNode(true);
        clone.querySelectorAll(".sequence__controls").forEach(function (node) { node.remove(); });
        return clone.textContent.replace(/\s+/g, " ").trim() || "item";
      }
      function reset() {
        seq.classList.remove("is-correct", "is-wrong");
        feedback.hidden = true;
      }
      function move(item, dir) {
        reset();
        if (dir < 0 && item.previousElementSibling) {
          list.insertBefore(item, item.previousElementSibling);
        }
        if (dir > 0 && item.nextElementSibling) {
          list.insertBefore(item.nextElementSibling, item);
        }
        var position = items().indexOf(item) + 1;
        feedback.textContent = "Moved " + itemLabel(item) + " to position " + position + " of " + items().length + ".";
        feedback.hidden = false;
      }

      items().forEach(function (item) {
        if (item.querySelector(".sequence__controls")) return;
        var label = itemLabel(item);
        var controls = document.createElement("span");
        controls.className = "sequence__controls";
        var up = button("↑", "sequence__move", "Move '" + label + "' up");
        var down = button("↓", "sequence__move", "Move '" + label + "' down");
        up.addEventListener("click", function () { move(item, -1); });
        down.addEventListener("click", function () { move(item, 1); });
        controls.appendChild(up);
        controls.appendChild(down);
        item.appendChild(controls);
      });

      check.addEventListener("click", function () {
        var invalid = false;
        var order = items().map(function (item) {
          if (!item.hasAttribute("data-order")) {
            invalid = true;
            return NaN;
          }
          var n = Number(item.getAttribute("data-order"));
          if (!Number.isFinite(n)) invalid = true;
          return n;
        });
        if (invalid) {
          if (window.console && console.warn) {
            console.warn("teach sequence skipped: every .sequence__item needs a finite data-order value", seq);
          }
          seq.classList.remove("is-correct");
          seq.classList.add("is-wrong");
          feedback.textContent = "This sequence is missing order data, so it cannot be checked.";
          feedback.hidden = false;
          return;
        }
        var correct = order.every(function (n, i) {
          return Number.isFinite(n) && (i === 0 || order[i - 1] <= n);
        });
        seq.classList.toggle("is-correct", correct);
        seq.classList.toggle("is-wrong", !correct);
        feedback.textContent = correct ? "Correct order." : "Not yet. Move the earliest step upward and try again.";
        feedback.hidden = false;
        if (correct) reveal(why);
        reveal(answer);
        emit(seq, id, correct, "sequence");
      });
    });

    // ---- Matching pairs ------------------------------------------------
    document.querySelectorAll(".match").forEach(function (match) {
      var id = match.getAttribute("data-id");
      var selected = null;
      var left = toArray(match.querySelectorAll(".match__left .match__button"));
      var right = toArray(match.querySelectorAll(".match__right .match__button"));
      var answer = match.querySelector(".match__answer");
      var matched = {};

      function clearWrong() {
        match.querySelectorAll(".is-wrong").forEach(function (el) {
          el.classList.remove("is-wrong");
        });
      }
      function clearSelected() {
        if (selected) {
          selected.classList.remove("is-selected");
          selected.setAttribute("aria-pressed", "false");
        }
        selected = null;
      }
      function allMatched() {
        return left.every(function (btn) { return matched[btn.getAttribute("data-key")]; });
      }

      left.concat(right).forEach(function (btn) { btn.type = "button"; });
      left.forEach(function (btn) {
        btn.addEventListener("click", function () {
          if (btn.disabled) return;
          clearWrong();
          clearSelected();
          selected = btn;
          btn.classList.add("is-selected");
          btn.setAttribute("aria-pressed", "true");
        });
      });
      right.forEach(function (btn) {
        btn.addEventListener("click", function () {
          if (btn.disabled || !selected) return;
          var key = selected.getAttribute("data-key");
          var correct = key && key === btn.getAttribute("data-key");
          clearWrong();
          if (correct) {
            matched[key] = true;
            selected.classList.add("is-correct");
            btn.classList.add("is-correct");
            selected.disabled = true;
            btn.disabled = true;
            selected.setAttribute("aria-pressed", "false");
            clearSelected();
            if (allMatched()) reveal(answer);
          } else {
            selected.classList.add("is-wrong");
            btn.classList.add("is-wrong");
          }
          emit(match, id, correct, "matching", { pair: key || null });
        });
      });
    });

    // ---- Predict the output -------------------------------------------
    document.querySelectorAll(".predict").forEach(function (predict) {
      var id = predict.getAttribute("data-id");
      var input = predict.querySelector(".predict__input");
      var check = predict.querySelector(".predict__check");
      var answer = predict.querySelector(".predict__answer");
      var why = predict.querySelector(".predict__why");
      var feedback = predict.querySelector(".predict__feedback");
      if (!input) return;
      var answers = (input.getAttribute("data-answer") || "").split("|").map(normalise);
      if (!check) {
        check = button("Check prediction", "predict__check", null);
        input.insertAdjacentElement("afterend", check);
      } else {
        check.type = "button";
      }
      if (!feedback) {
        feedback = document.createElement("p");
        feedback.className = "predict__feedback";
        feedback.setAttribute("aria-live", "polite");
        feedback.hidden = true;
        check.insertAdjacentElement("afterend", feedback);
      }
      check.addEventListener("click", function () {
        var val = normalise(input.value);
        if (!val) {
          input.classList.remove("is-correct", "is-wrong");
          feedback.hidden = true;
          return;
        }
        var correct = answers.indexOf(val) !== -1;
        input.classList.toggle("is-correct", correct);
        input.classList.toggle("is-wrong", !correct);
        feedback.textContent = correct ? "Prediction matches." : "Not this time. Compare it with the revealed answer.";
        feedback.hidden = false;
        reveal(answer);
        reveal(why);
        emit(predict, id, correct, "predict");
      });
    });

    // ---- Self rating ---------------------------------------------------
    document.querySelectorAll(".self-rate").forEach(function (rate) {
      var id = rate.getAttribute("data-id");
      var feedback = rate.querySelector(".self-rate__feedback");
      rate.querySelectorAll(".self-rate__button").forEach(function (btn) {
        btn.type = "button";
        btn.addEventListener("click", function () {
          var rating = normalise(btn.getAttribute("data-rating") || btn.textContent);
          rate.querySelectorAll(".self-rate__button").forEach(function (other) {
            other.classList.remove("is-selected");
            other.setAttribute("aria-pressed", "false");
          });
          btn.classList.add("is-selected");
          btn.setAttribute("aria-pressed", "true");
          if (feedback) {
            feedback.textContent = "Marked " + rating + ".";
            feedback.hidden = false;
          }
          emit(rate, id, rating !== "again", "self-rate", { rating: rating });
        });
      });
    });

    // ---- Optional recall tally (updates any .recall-score element) ------
    var scoreEl = document.querySelector(".recall-score");
    if (scoreEl) {
      var gradable = document.querySelectorAll('.quiz[data-id], .cloze input[data-id]').length;
      var seen = {}, correct = 0;
      var render = function () {
        scoreEl.textContent = correct + (gradable ? " / " + gradable : "") + " recalled";
      };
      render();
      document.addEventListener("teach:graded", function (e) {
        // Only MCQ + cloze count toward the tally (they form the denominator above).
        // Worked-step reveals emit events for future modules but aren't tally items.
        if (e.detail.type !== "mcq" && e.detail.type !== "cloze") return;
        if (!e.detail.id) return;
        var key = e.detail.type + ":" + (e.detail.id || "");
        if (e.detail.correct && !seen[key]) { seen[key] = true; correct++; render(); }
      });
    }

    // ---- Print: force-open closed reveals so their answers print, then restore.
    // Belt-and-suspenders with the CSS ::details-content rule (covers browsers
    // that don't support it yet, whenever JS is on).
    var openedForPrint = [];
    window.addEventListener("beforeprint", function () {
      document.querySelectorAll("details.reveal:not([open])").forEach(function (d) {
        openedForPrint.push(d); d.open = true;
      });
    });
    window.addEventListener("afterprint", function () {
      openedForPrint.forEach(function (d) { d.open = false; });
      openedForPrint = [];
    });
  });
})();
