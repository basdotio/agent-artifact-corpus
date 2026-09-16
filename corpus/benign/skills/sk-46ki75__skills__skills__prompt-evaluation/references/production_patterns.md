# Production Eval Patterns

What distinguishes "I ran 20 cases once" from "we have evals
running on every PR and shadow-scoring production": discipline,
not tooling. This reference covers the patterns that mature teams
use, drawn from Hamel Husain, Eugene Yan, Shreya Shankar, Anthropic
Engineering, LangSmith, Braintrust, and W&B Weave.

## The maturity ladder

A team has graduated from one-off evals to a production discipline
when **all** of the following hold:

1. **Two suites** — a small frozen ~100% pass-rate **regression
   set** owned by a named SME, and a larger evolving **capability
   set** with deliberately low pass rate. (Anthropic)
2. **Datasets are versioned, lineage-tracked, and grown via the
   missing-failure rule** — every production incident becomes a
   row. (Husain)
3. **Per-criterion judges** with measured TPR/TNR vs SME labels;
   target ≥ 0.9 / Cohen's κ ≥ 0.6 before deploy.
4. **Eval-on-PR with threshold gating**, prompt caching on the
   rubric, Batch API for nightly capability sweeps.
5. **Online (shadow) scoring** with sampled human review (~10–20
   traces/week) and a formal review cycle (2–4 weeks).
6. **Judge-health discipline** — periodic recalibration; position
   / verbosity / self-enhancement bias controls; Cohen's κ over
   raw agreement.
7. **Custom labeling UI** for SMEs and a failure-sharing ritual.
8. **Error analysis owns 60–80% of eval effort**, tooling owns the
   rest. (Husain)

Most teams reach 1–4 (offline eval-on-PR). Reaching 5–8 (online
discipline, judge health) is what separates serious teams from
junior ones.

Eugene Yan's line: *"Buying or building yet another evaluation
tool won't save the product"* — without the process underneath.

## Capability vs. regression suites (revisited)

Anthropic Engineering's explicit framing:

- **Capability evals** "should start at a low pass rate, targeting
  tasks the agent struggles with."
- **Regression evals** "should have a nearly 100% pass rate. They
  protect against backsliding, as a decline in score signals that
  something is broken."

Operational rule: when a capability-suite row starts passing
consistently across iterations, **migrate it into the regression
suite**. This is how production tests grow.

## Eval-on-PR (CI gating)

Hamel's Level-1 evals "should run fast and cheaply as you develop
your application so that you can run them every time your code
changes."

The threshold-gating pattern:

```yaml
# GitHub Actions
- name: Run eval
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    PROMPTFOO_CACHE_PATH: ~/.cache/promptfoo
  run: |
    npx promptfoo@latest eval \
      -c regression.yaml \
      -o results.json \
      -o results.junit.xml \
      --tag git.sha="${{ github.sha }}" \
      --fail-on-error

- name: Quality gate
  run: |
    FAILURES=$(jq '.results.stats.failures' results.json)
    [ "$FAILURES" -gt 0 ] && exit 1 || true
```

Three layers of gating, increasing in strictness:

1. **`--fail-on-error`** — block the PR if any row errored out
   (infra failure).
2. **Hard threshold** — block if `failures > 0` on the regression
   suite (the suite is supposed to be ~100% pass).
3. **Trend threshold** — block if the capability-suite pass rate
   dropped by > X% vs the previous run.

Tie thresholds to dollar impact when possible — OpenAI's cookbook
calls out "vibe-based evals" as the anti-pattern and recommends
linking false-positive / false-negative rates to business cost.

### Diff-only evaluation

Don't re-grade rows whose output didn't change from the previous
run. Both LangSmith and Braintrust expose this as a primitive
("compare two experiments"); in a custom pipeline:

```python
def needs_regrade(row, prev_results):
    return row.output != prev_results.get(row.id, {}).get("output")
```

Combined with prompt caching, a typical CI eval run completes in
single-digit seconds even for 200+ rows.

## Offline vs. online evaluation

LangSmith's canonical split:

| Offline | Online |
| --- | --- |
| Pre-deployment | Production traffic |
| Has reference outputs | No references (live requests) |
| Benchmarking, regression | Anomaly detection, shadow scoring |
| Threshold gates | Drift alerts |
| Eval-on-PR | Continuous (sampled) |

Online evaluation = **shadow scoring**. Run the judge on a sampled
fraction of production traces; the score is for observability, not
gating. Pattern:

- Sample at 1–10% of production traffic (stratified by intent /
  user segment).
- Run a fast, cheap judge (Haiku 4.5 with cached rubric, binary
  verdict).
- Alert when the score distribution shifts beyond a threshold
  (e.g. 5-day moving average drops by > 10%).
- Pull the flagged traces into a labeling queue for human review.

## Cost engineering for evals

Eval datasets are highly repetitive — same system prompt, same
few-shot block, same rubric. Cost-control levers in priority
order:

1. **Prompt-cache the rubric.** 0.1× cost on cached reads;
   minimum 4,096 tokens (Haiku, Opus) or 1,024 (Sonnet). For a
   200-row eval with a 5k-token rubric this is ~10× cheaper.
   See `code_graded.md`.

2. **Batch API for offline regression sweeps.** ~50% cheaper than
   sync. Matches nightly schedules (5-minute to 24-hour latency).

3. **Cheap judge by default.** Haiku 4.5 with a tight binary
   rubric handles most criteria. Promote to Opus for calibration
   or on the disagreement set.

4. **Judge cascade.** Cheap judge on every row; expensive judge
   on rows where the cheap judge is uncertain or the prompt
   author flagged the row. Databricks: GPT-4 to *discover* the
   rubric, GPT-3.5 (cheap) with one example per score in
   production — 10× cheaper, 3× faster, ~95% of accuracy preserved.

5. **Stratified sampling for online evals.** Don't judge every
   production row. Sample by user intent / retrieval source;
   confidence intervals improve faster than uniform sampling.

6. **Skip the judge on rows that fail code-graded gates first.**
   Format / length / refusal checks are essentially free; run
   them first as a filter.

## Failure modes of the evals themselves

This meta-discipline separates mature teams from junior ones.

### Goodhart / overfitting to the eval set

When you optimize the prompt against a fixed test set long enough,
the prompt starts to **win on the test set in ways that don't
generalize**. Symptoms:

- The regression-suite score keeps climbing but production
  metrics stay flat.
- Prompt edits get oddly specific ("don't use the word 'unable'")
  — clear sign you're fitting noise.

Mitigations: rotate the dataset; keep a held-out "production-
mirror" set you don't touch; do online eval-on-traffic so you
catch divergence.

Eugene Yan on fine-tuned judges (JudgeLM, PandaLM, Auto-J,
Prometheus): they "had higher correlation amongst themselves than
with GPT-4, indicating they may be task-specific classifiers
rather than general evaluators." Goodhart for judges, too.

### Test/train leakage

If your eval rows ever appeared in pretraining (because they came
from public benchmarks or you posted them in a blog), the model
might be *memorizing* the answers. The `openai/evals` repo uses
Git-LFS partly to track exactly which eval data has been
published. For internal evals, Eugene Yan suggests "text from the
middle of copyrighted works rather than famous opening lines that
saturate training data."

### Judge drift

The judge model is upgraded (Sonnet 4.6 → 4.7) and your scores
shift even though the prompt-under-test didn't change. **Pin the
judge model ID** for regression suites; recalibrate when you
upgrade.

### Criteria drift

Shreya Shankar's coined term: "it is impossible to completely
determine evaluation criteria prior to human judging of LLM
outputs." The rubric you wrote up front is wrong. You discover the
real criteria during labeling.

Mitigation: treat the first 20–30 labels as **criteria discovery**;
rewrite the rubric afterward; re-calibrate quarterly. This is why
"look at the data first" beats "write the rubric in advance."

### Saturation

When everything passes, the eval is no longer informative. Either
the prompt is genuinely good or the set has saturated. Promote the
passing rows to regression (lock them in) and add harder
capability rows.

### Mis-calibrated judges

Measured biases (see `model_graded.md` for full numbers):

- Position bias: Claude-v1 75% first-position preference.
- Verbosity bias: Claude-v1 91% prefer the padded answer.
- Self-enhancement: Claude-v1 +25% own-family win rate.

Mitigations: position swap with agreement gate; length-neutral
rubric; heterogeneous judge family; **calibrate against humans
quarterly**.

## Ownership and rituals

### The "Benevolent Dictator" / Principal Domain Expert

Hamel: appoint *"a single domain expert who sets quality standards
and ensures consistency. This approach eliminates annotation
conflicts and prevents decision paralysis."*

For multi-team systems, find the one or two individuals whose
judgment is critical. Their labels are the ground truth for judge
calibration; their rubric edits are authoritative.

### SME involvement and custom viewers

Hamel: *"The single most impactful investment I've seen AI teams
make isn't a fancy evaluation dashboard — it's building a
customized interface that allows experts to efficiently review and
label LLM outputs."*

The labeling discipline pays a second dividend: *"the process of
grading outputs helps them to define that very criteria"* — the
SME's rubric emerges from the work.

### Rituals

- **Weekly trace review** — 10–20 production traces, prioritizing
  outliers (Husain).
- **2-4 week formal review cycle** — fresh batch of 100+ traces,
  update the dataset (Husain).
- **Failure-sharing meeting** — Eugene Yan's "fifteen-fives" or
  "no-prep sharing sessions."
- **Quarterly judge recalibration** — re-validate against ≥50
  human labels.

### Annotation queue infrastructure

LangSmith's annotation queues institutionalize the labeling ritual:
"configured multiple reviewers per run, enabling reservations to
prevent conflicts." Braintrust experiments and W&B Weave datasets
do the same. For a small team, a CSV in a shared drive works;
graduate when conflicts or volume justify it.

## Binary judgments over Likert scales

The strongest single piece of advice across senior practitioners
(repeated in `model_graded.md` for emphasis):

- **Hamel**: *"If your evaluations consist of a bunch of metrics
  that LLMs score on a 1–5 scale (or any other scale), you're
  doing it wrong... It's not actionable... people don't know what
  to do with a 3 or 4."*
- **Shankar**: *"Binary metrics are easier to align (you only need
  to agree on what constitutes True and False) and easier for
  humans to consistently judge."*
- **Yan / Arize / Databricks**: same consensus.

Pair binary judgment with **free-text critiques** to capture nuance
without forcing rating variance.

## Per-criterion judges (not composite)

Anthropic's published rule: *"grade each dimension with an
isolated LLM-as-judge rather than using one to grade all
dimensions."*

Concretely: instead of one judge that scores "summary quality
(1-10)", split into three judges:

- Faithfulness judge (binary; does the summary stay grounded?)
- Coverage judge (binary; are the key points present?)
- Tone judge (binary; is the register exec-appropriate?)

Each is calibrated independently. The dashboard shows three pass
rates instead of one composite. A regression alert fires on the
specific failing axis. This is the design that scales.

## Sample sizes worth knowing

| Decision | Sample |
| --- | --- |
| Seed dataset | 20–50 real failures |
| Stop sampling for failure categories | 20 traces with no new category |
| Iteration loop | 20–100 cases |
| Pre-deploy regression | 100–500 |
| Judge calibration | 25–50 human labels |
| Ongoing production review | 10–20 traces/week |
| Quarterly recalibration | ≥50 fresh human labels |

## Anti-patterns to flag

- **Vibes-based evals** ("seems better to me") — OpenAI cookbook's
  named anti-pattern.
- **One composite judge** scoring multiple criteria — invites halo
  bias.
- **Likert without anchors** — judges drift to the middle.
- **Same model under test as judge** — self-enhancement bias.
- **Pairwise without position swap** — Claude judges 75% biased
  to first position.
- **Raw correlation on imbalanced data** — Goodhart's κ instead.
- **Frozen rubric never recalibrated** — criteria drift will
  silently move the score.
- **Eval set never grown after launch** — production failures
  bypass the safety net.

## Source citations

- [Anthropic — Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Anthropic — Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Hamel Husain — Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/)
- [Hamel Husain — LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/)
- [Hamel Husain — LLM-as-Judge that Drives Business Results](https://hamel.dev/blog/posts/llm-judge/)
- [Hamel Husain — Field Guide to Rapidly Improving AI Products](https://hamel.dev/blog/posts/field-guide/)
- [Eugene Yan — An LLM-as-Judge Won't Save the Product](https://eugeneyan.com/writing/eval-process/)
- [Eugene Yan — LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/)
- [Eugene Yan — Task-Specific Evals](https://eugeneyan.com/writing/evals/)
- [Shreya Shankar — Data Flywheels for LLM Applications](https://www.sh-reya.com/)
- [Shankar et al. — Who Validates the Validators?](https://arxiv.org/abs/2404.12272) — criteria drift
- [LangSmith — Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [Braintrust — Evals Guide](https://www.braintrust.dev/docs/guides/evals)
- [W&B Weave](https://wandb.ai/site/weave)
- [Databricks — RAG auto-eval best practices](https://www.databricks.com/blog/LLM-auto-eval-best-practices-RAG)
- [Honeycomb — All the Hard Stuff Nobody Talks About When Building LLM Products](https://www.honeycomb.io/blog/hard-stuff-nobody-talks-about-llm)
- [OpenAI Cookbook — Eval-Driven System Design](https://developers.openai.com/cookbook/examples/partners/eval_driven_system_design/receipt_inspection)
