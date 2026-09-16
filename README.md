# agent-guard-corpus

Test corpus and benchmark for [`aguard`](https://github.com/basdotio/agent-guard), a static
security scanner for installed Claude Code agent environments.

It answers three questions, and the answers come from different places:

| Question | Answered by | Where |
|---|---|---|
| What is the false positive rate? | **The world** | `manifest/` — layer 2, fetched |
| What is the recall? | **Mostly the world, we fill two gaps** | layer 2 + `corpus/malicious/` |
| Did this change make things worse? | **Only us** | `corpus/` — layer 1, vendored, offline |

In one line: **the denominator comes from the world, the numerator from us, and the gate
from nobody else.**

Start with [`docs/classification.md`](docs/classification.md) for what is measured, then
[`docs/design.md`](docs/design.md) for how it is built.

---

## Three red lines

**① Do not hand-write benign samples to measure false positives.**

A benign sample written by someone who knows the rules is *imagined* benign. Real skill
authors do not know our rules exist, so they casually paste a `curl` config example into a
`SKILL.md` — which is where our confirmed false positives actually come from. Writing them
yourself, you unconsciously avoid the shapes you know will fire, so the measured rate is
biased low by an unknowable margin.

The one exception is `corpus/benign/hooks/` and `corpus/benign/permission/`: nobody collects
normal hook and permission configs, because nobody else scans them. That cell has to be
built, **and it is exactly where a good-looking number is easiest to manufacture**, so the
sampling rule is fixed: **harvest from real machines only** (our own, colleagues', public
dotfiles repos). **Never hand-written.** A hand-written benign hook and a hand-written
benign skill are the same mistake.

**② No denominator may carry an exclusion.**

Any `grep -v`, any "this category does not count", must appear in the conclusion line
**with both figures — including the exclusion and without it.**

This was learned the expensive way. A false positive rate of 11.0% was published from a
denominator of 290 samples selected by two `find` commands. The full population is 952, and
the rate is 12.9%. The 44% removed by that `grep -v` was the worst-scoring group on the
machine, dropped to sidestep a performance defect. **Using one defect as grounds to drop
half the denominator means one problem concealed another.**

**③ "No scanner complained" is not evidence of benignity.**

It is circular for us. The sharpest case is ClawHub, which rates by OWASP Agentic Top 10 —
the same taxonomy our rules derive from. Selecting benign samples with it means selecting
our test set with a scanner that shares our blind spots. See
[benign credibility](docs/design.md#benign-credibility-ranking).

---

## Two layers

Third-party samples carry license constraints (see [`docs/licensing.md`](docs/licensing.md)),
and "download then test" breaks offline CI. The compromise is two layers:

- **Layer 1 — `corpus/`.** Written by us, plus permissively licensed material. Vendored,
  runs offline. **The regression gate looks only here.**
- **Layer 2 — `manifest/`.** Only `url + commit + sha256 + labels`. `make fetch` pulls into
  a gitignored `cache/`. **Published rates come from here.**

**Every published number states which layer it came from.**

Recording a URL and a hash is not distribution, which is why layer 2 may reference corpora
that layer 1 must never contain: no-license, CC-BY-NC-SA, AGPL.

---

## Usage

```bash
make validate    # check every label, manifest entry and the leakage gate (offline)
make fetch       # pull layer 2 per manifest, verify sha256
make stats       # corpus composition
```

Running the benchmark itself lives in the tool repository (`make bench`). This repository
owns the corpus, not the scorer.

## Adding a sample

1. Create the sample tree `corpus/<class>/<surface>/<id>/`
2. Write the label **beside it**, as `corpus/<class>/<surface>/<id>.yaml` — schema in
   [`docs/label-schema.md`](docs/label-schema.md). **Never inside the tree**: the scanner
   reads the whole target, so a label in there injects its own text as evidence and
   corrupts the sample's own result in both directions.
3. **Label before running.** `origin.labeled_before_run` must be `true`. Running first and
   labelling after treats the tool's current behaviour as the correct answer, which measures
   100% every time.
4. `make validate`

## License

Content written by us is MIT (`LICENSE`). Vendored third-party samples in layer 1 keep their
original license, itemised in `NOTICE`. Layer 2 is never vendored.
