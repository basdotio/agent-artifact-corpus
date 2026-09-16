> English · [中文](README.zh-CN.md)

# agent-artifact-corpus

A labelled test corpus and benchmark for **static security scanners of AI agent
environments** — the skills, hooks, permission configs, MCP servers, connectors and
instruction files an agent loads.

It is **tool-neutral by construction**. Every sample states what it *is*, in a vocabulary no
scanner owns ([`taxonomy/techniques.yaml`](taxonomy/techniques.yaml)), so any scanner can be
measured against it and several can be compared on the same samples. Naming a scanner's own
rule IDs is optional precision layered on top, never the assertion itself. See
[the two halves](docs/label-schema.md#the-two-halves).

It answers three questions, and the answers come from different places:

| Question | Answered by | Where |
|---|---|---|
| What is the false positive rate? | **The world** | `manifest/` — layer 2, fetched |
| What is the recall? | **Mostly the world, we fill two gaps** | layer 2 + `corpus/malicious/` |
| Did this change make things worse? | **Only this repository** | `corpus/` — layer 1, vendored, offline |

In one line: **the denominator comes from the world, the numerator from us, and the gate
from nobody else.**

Start with [`docs/classification.md`](docs/classification.md) for what is measured, then
[`docs/design.md`](docs/design.md) for how it is built.
For the public corpora themselves — what each is good for, and what it will do to your
numbers if you use it wrong — see [`docs/catalogue.md`](docs/catalogue.md).

---

## Measuring a scanner

**Any scanner, without asking us for anything.** Point it at the sample trees under
`corpus/`, and for each one ask whether it reported a finding at or above the sample's
`truth.severity`. Hard negatives and benign samples assert the reverse. That is the whole
protocol, and it needs no rule IDs, no severity mapping and no entry anywhere in this
repository.

**Rule-level expectations, optionally.** Adding an entry to
[`taxonomy/tools.yaml`](taxonomy/tools.yaml) lets labels carry `expect.<tool>` blocks that
name which of that scanner's rules must fire and which must stay quiet, checked against that
scanner's own severity ladder. Two scanners with different scales annotate the same sample
without either adopting the other's.

**Comparing scanners.** Because the ground truth is shared and the per-tool expectations are
separate, the same corpus yields a per-technique, per-dimension comparison rather than one
number per tool. `make stats` already reports the tool-neutral composition, including every
technique that has no sample yet.

**This repository does not score.** It owns the samples and the rules about them. A runner
belongs with each scanner, or as a thin adapter that normalises output — SARIF 2.1.0 is the
obvious boundary and several scanners in this space already emit it. Keeping the scorer out
is what lets `make validate` run with no build of any scanner present.

### Tools wired up today

| Tool | Rule-level expectations | Note |
|---|---|---|
| [`aguard`](https://github.com/basdotio/agent-guard) | yes, on all 6 layer-1 samples | the only one so far — see *Known gaps* |

No second scanner has been wired up yet. Until one is, the tool-neutral claims above are a
property of the schema rather than a demonstrated result, and that distinction is the reason
for saying so here.

---

## Three red lines

**① Do not hand-write benign samples to measure false positives.**

A benign sample written by someone who knows the rules is *imagined* benign. Real skill
authors do not know any scanner's rules exist, so they casually paste a `curl` config example
into a `SKILL.md` — which is where confirmed false positives actually come from. Writing them
yourself, you unconsciously avoid the shapes you know will fire, so the measured rate is
biased low by an unknowable margin.

The one exception is `corpus/benign/hooks/` and `corpus/benign/permission/`: nobody collects
normal hook and permission configs, because almost nobody scans them. That cell has to be
built, **and it is exactly where a good-looking number is easiest to manufacture**, so the
sampling rule is fixed: **harvest from real machines only** (our own, colleagues', public
dotfiles repos). **Never hand-written.** A hand-written benign hook and a hand-written benign
skill are the same mistake.

**② No denominator may carry an exclusion.**

Any `grep -v`, any "this category does not count", must appear in the conclusion line
**with both figures — including the exclusion and without it.**

This was learned the expensive way. A false positive rate of 11.0% was published from a
denominator of 290 samples selected by two `find` commands. The full population is 952, and
the rate is 12.9%. The 44% removed by that `grep -v` was the worst-scoring group on the
machine, dropped to sidestep a performance defect. **Using one defect as grounds to drop half
the denominator means one problem concealed another.**

**③ "No scanner complained" is not evidence of benignity.**

It is circular. The sharpest case is ClawHub, which rates by OWASP Agentic Top 10 — the
taxonomy most scanners in this space derive their rules from, including the one this corpus
was first built against. Selecting benign samples with it means selecting the test set with a
scanner that shares the blind spots of the scanner under test. See
[benign credibility](docs/design.md#benign-credibility-ranking).

---

## Two layers

Third-party samples carry license constraints (see [`docs/licensing.md`](docs/licensing.md)),
and "download then test" breaks offline CI. The compromise is two layers:

- **Layer 1 — `corpus/`.** Written by us, plus permissively licensed material. Vendored,
  runs offline. **A regression gate should watch only here.**
- **Layer 2 — `manifest/`.** Only `url + commit + sha256` and what is known about the
  corpus. `make fetch` pulls into a gitignored `cache/`. **Published rates come from here.**

**Every published number states which layer it came from.**

Recording a URL and a hash is not distribution, which is why layer 2 may reference corpora
that layer 1 must never contain: no-license, CC-BY-NC-SA, AGPL.

---

## Usage

```bash
make validate    # check every label, the taxonomy, every manifest entry, the doc pairs
make stats       # corpus composition, tool-neutral and per tool
make fetch       # materialise named layer-2 entries at their pinned commit (network)
make test        # harness unit tests
```

`make validate` is offline and needs no scanner installed.

## Adding a sample

1. Create the sample tree `corpus/<class>/<surface>/<id>/`
2. Write the label **beside it**, as `corpus/<class>/<surface>/<id>.yaml` — schema in
   [`docs/label-schema.md`](docs/label-schema.md). **Never inside the tree**: a scanner reads
   the whole target, so a label in there injects its own text as evidence and corrupts the
   sample's own result in both directions.
3. Fill in `truth` first, and stop there if you like. A `truth` block alone is a complete
   label; `expect.<tool>` is precision you add once you have measured a particular scanner.
4. **Label before running.** `origin.labeled_before_run` must be `true`. Running first and
   labelling after treats a tool's current behaviour as the correct answer, which measures
   100% every time.
5. `make validate`

## Known gaps in this repository

Declared rather than omitted, on the same principle this corpus applies to the scanners it
measures.

- **No CI.** Nothing runs `make validate` automatically, so the regression gate described
  above is a design, not a mechanism.
- **`sha256` is never verified.** Every manifest entry carries an empty `sha256`, and the
  fetcher checks the pinned commit only. Integrity rests on git, not on the hash.
- **The HuggingFace entries need more than a fetch.** git access works and the pinned commits
  resolve, but the payload is behind git-lfs, which is not installed here, and `SkillMD-138K`
  is a single 560MB `train.parquet` rather than sample trees. Using it as a denominator needs
  git-lfs, then an extraction step, then the per-repo cap its own hazards call for.
- **`subset` is declared but ignored by the fetcher.** `datadog-ai-skills` names
  `samples/ai-skills` and `cisco-mcp-scanner-evals` names `evals`, yet both would clone whole.
- **One tool wired up.** `taxonomy/tools.yaml` has a single entry.
- **`NOTICE` is not cross-checked** against label licenses by `make validate`.
- **One harness package has no tests**: `fetch`.
- **Six of nine technique dimensions have no sample.** `make stats` names them.

## License

Content written by us is MIT (`LICENSE`). Vendored third-party samples in layer 1 keep their
original license, itemised in `NOTICE`. Layer 2 is never vendored.
