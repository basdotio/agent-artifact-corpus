# Reference 04: Measure and optimize a Jev classifier

A working classifier is not a good classifier. After it runs, measure its accuracy
on real labeled data, then improve it with the levers below and measure again. You
cannot improve what you do not measure.

## Step A: Get a labeled sample the human-reasonable, unbiased way

The user needs to supply ground truth, but do NOT make them edit JSON or code, and
do not let them label in a way that biases the result. Use a rating sheet:

1. Take a RANDOM, representative sample of the user's real inputs (40 to 60 is a good
   start; more tightens the estimate). Random, not cherry-picked, so the accuracy
   number is unbiased. If a category is rare, sample extra of it after a first pass
   (stratify) so each category has enough items to score.
2. Export a BLIND rating sheet with `scaffolding/make_rating_sheet.py`: a CSV with
   `id, text, <question>` columns and the answer column BLANK. The model's guess is
   deliberately NOT in the sheet. This matters: if the human sees the guess they
   anchor to it and rubber-stamp it, and the measured accuracy comes out fake-high
   (confirmation bias). They label from scratch.
3. The human opens the CSV in Excel or Google Sheets and fills the answer column from
   the fixed category list. For 50 short items this is 10 to 20 minutes, done once
   and reused every tuning round. Only manual step, and it needs no technical skill.
4. Load it back with `evaluate.load_labeled_csv(path)`.

## Step B: Split, then measure honestly

Split the labeled set with `evaluate.split(labeled, test_frac=0.4)` into a TUNING
set and a HELD-OUT TEST set. Tune criteria only against the tuning set (read its
errors), and report accuracy on the held-out test set that tuning never touched.
Reporting on data you optimized against overfits the wording to those exact items
and the number lies; the held-out number is the real one. This is the same
discipline the skill-creator loop uses.

Then `scaffolding/evaluate.py` runs the classifier on a set and reports per-question
accuracy WITH a 95% confidence interval, a confusion breakdown (which categories get
mixed up), confidence calibration (are high-confidence answers actually more right?),
and total cost, storing a timestamped run so rounds are comparable. Respect the
interval: at n=40 to 50 the 95% band on an accuracy figure is roughly plus or minus
13 to 15 points, so it is "about 85 percent," not "85.0." Use `evaluate.errors(...)`
to dump the misclassified TUNING items so you can read WHY they are wrong.

## Step C: Read the errors, then pull the right lever

Look at WHICH cases are wrong and WHY, then apply the highest-leverage fix. In
priority order, grounded in published Jev experiments:

1. Fix the CRITERIA first. This is by far the biggest lever. In one study,
   rewriting only the criteria took a classifier from 70% to 96% accuracy, and a
   criteria-only rewrite reached 100% where instruction-only rewrites stayed at
   38%. The question wording barely matters; the per-option/per-level criteria
   descriptions carry the decision.
   - Define what PASSES, not only what fails. Specifying the allowed/"false" side
     was about 3.5x more effective than piling on more prohibitions.
   - Define the underlying AXIS, not surface features. "Is a person being attacked"
     generalizes far better than a list of banned words, and catches cases the list
     misses.
   - Do NOT put probability numbers in criteria. They are decoration; inverting the
     numbers changed nothing. The words carry the weight.
2. Fix the STATE. Send only the fields the question needs; padding the state with
   irrelevant material lowers accuracy (context rot). And put into the state any
   fact the model cannot know on its own: your policy, your jurisdiction's rule, the
   current value. Jev does not know what it does not know.
3. Reconsider the PRIMITIVE. If a yes/no is really a matter of degree, switch
   `noul` to a `score` with clear rungs; it gives finer, more tunable decisions.
4. Add or fix an ESCAPE option so out-of-scope inputs are not force-fit into a real
   category (reference 02).
5. Add a few EXAMPLES only for genuine boundary cases the definition cannot capture.
   The first few help; piling on more mostly adds cost, not accuracy. Do not spam
   examples at a task the criteria already solve.
6. Only after the above, tune the confidence THRESHOLD to the precision/recall the
   user wants. This changes which decisions the SYSTEM auto-takes, not Jev's raw
   accuracy. Use the calibration output and the user's false-positive/false-negative
   preference.

## Step D: Re-measure and loop

Re-run `evaluate.py`. It prints the change vs the previous run per question. Keep
changes that help, revert changes that do not. Repeat: measure, read errors, pull
the top lever, re-measure. Store every run so the history is auditable.

Stop when you hit the user's target accuracy, or when rounds stop improving it.

## Set expectations honestly

Jev has a ceiling. On TypeSafe's hard 4-workflow benchmark it scores around 68%
(roughly tied with frontier LLMs there); on clean, well-defined tasks it can reach
very high accuracy. If a task needs knowledge or judgment Jev cannot have, no amount
of criteria tuning fixes it: put the missing information in the state, or pair Jev
with an LLM, or accept that the task is not a good System One fit. Do not chase 100%
on an ill-posed task, and never quietly raise the auto-act threshold just to make a
number look better.

## Sources

- Jev criteria-prompting experiments (criteria-are-the-lever, define-what-passes,
  axis-over-lists, numbers-are-decorative, examples-diminishing-returns).
- TypeSafe benchmark accuracy figures and the context-rot / clean-state guidance.
