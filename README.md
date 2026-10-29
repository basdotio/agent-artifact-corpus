> English · [中文](README.zh-CN.md)

# agent-artifact-corpus

A labelled test corpus and benchmark for **static security scanners of AI agent
environments** — the skills, hooks, permission configs, MCP servers, connectors and
instruction files an agent loads.

It is **tool-neutral by construction, and `make validate` enforces it.** Claiming neutrality
in a README is not the same as having it, and this repository has lost it twice without
noticing — both times with a green build, because coupling of this kind is invisible unless
something looks for it. Three checks now run on every validate, and each was written after
the property it guards had already silently broken:

| Checked | Why |
|---|---|
| No registered scanner's id appears in any `truth` block or in `taxonomy/techniques.yaml` | The moment a sample's truth explains what some scanner misses, that scanner's model *is* the ground truth, and the next tool is scored on a description of its competitor |
| No scanner's id appears in the harness's own code (string literals and identifiers; comments exempt) | Code that names one tool makes that tool's presence part of how everybody else's samples are validated. This caught a CI step that pinned the literal `"aguard"` |
| No workflow sets a scanner's `rules_source.env` | The shared gate would verify one project's rule ids and no other project's |

Plus one rule in the validator: a tool's `rules_source.path` may not leave the repository.
It used to, and the consequence was that `make validate` reported 73 verified rule ids on the
author's machine and "not checked" on everyone else's — the corpus's own result depending on
one person's directory layout.

What is deliberately *not* checked is described in
[`neutrality.go`](harness/cmd/corpus/neutrality.go): a pass that strips every `expect` block
and revalidates was built and then deleted, because nothing in the validator requires an
expect block, so it could only ever pass. `truth`'s self-sufficiency is already enforced per
class — a malicious sample must name a severity and either a technique or a dimension, a hard
negative must name
`resembles` and `differs_by` — and those checks fail loudly.

Every sample states what it *is*, in a vocabulary no
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

**This repository does not RUN scanners; it does grade their answers.** The line moved, and
where it moved to matters. `corpus score` reads a scanner's verdicts and turns them into
recall, false positives and coverage — that is arithmetic over `truth`, and keeping it here is
what stops every scanner inventing its own scoring and calling the results comparable. What
stays out is the part that has to know a particular tool: how to invoke it, how to read its
output, how to place a sample into the layout it expects. That **runner belongs with each
scanner**, or as a thin adapter that normalises output — SARIF 2.1.0 is the obvious boundary
and several scanners in this space already emit it.

The split is what lets `make validate` and `corpus score` run with no build of any scanner
present: the corpus never executes anything it is measuring. See
[`using-the-corpus.md`](docs/using-the-corpus.md) for the whole protocol from the other side.
Short introductions suitable for a post are in [`articles.md`](docs/articles.md).

### Tools wired up today

| Tool | Rule-level expectations | Note |
|---|---|---|
| [`aguard`](https://github.com/basdotio/agent-guard) | yes, on 6 of the 5,060 layer-1 samples | the only one so far — see *Known gaps* |

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

The hardest place for this rule was `corpus/benign/{hooks,permission,connector}/`: nobody
collects normal hook, permission and connector configs, because almost nobody scans them.
That cell has to be built, **and it is exactly where a good-looking number is easiest to
manufacture**, so the sampling rule is fixed: **collect, never write**. A hand-written benign
hook and a hand-written benign skill are the same mistake.

Those three cells are now built, by `scripts/harvest-claude-config.py`: real
`.claude/settings.json` and `.mcp.json` files collected from public repositories, assigned to
a surface by their CONTENT rather than their filename, restricted to real load paths (a
`.template` or `.bak` is documentation, not something an agent loads), and restricted to
licences that permit redistribution — that last one being an exclusion, so both figures are
printed on every run.

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
make score V=verdicts.jsonl   # grade a scanner's verdicts into recall, false positives, coverage
```

`corpus samples` emits the corpus as a JSONL work list — `{id, path, class, surface}` per
sample — the input side of the scoring loop: a runner iterates it, points its scanner at each
`path`, and emits `{sample, verdict}` back for `corpus score`. It names no scanner and belongs
here for the same reason the runner does not.

`corpus fixtures` lists or materialises the injected-fault trees git cannot store — a 0111
traverse-only directory, a FIFO SKILL.md, symlink cycles and escapes, a 4096-deep chain, an
8 GiB sparse config — each with the tool-neutral pass condition a runner checks. Run
`corpus fixtures --restore <dir>` before deleting a materialised set, or the 0111 directory
blocks `rm -rf`.

`corpus score` reads a scanner's output as JSONL — one `{"sample","verdict"}` object per line,
with optional `severity` and `dimensions` — and prints recall per dimension and per source,
the flag rate on each benign population, the hard-negative census, and attribution over the
read-basis samples. It keeps the lines the corpus is built on: **wild**, **fixture**,
**synthetic**, **injected** and **constructed** samples never merge into one number — only the first can back a claim about the
world, and a third party's test fixtures are not it — a per-source rate is labelled a rate about
that source, and a group too small for a tight interval is printed as a bare count, not a
figure. It grades against `truth`; it never decides what passes.

`make validate` is offline and needs no scanner installed. CI runs these same targets on a
clean checkout, so anything that passes locally only because your machine has something extra
shows up there rather than in someone else's clone.

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

- **Rule ids in `expect.<tool>` blocks are not verified here, by design.** 6 of 5,060 labels
  carry such a block; the other 5,054 are pure `truth` and need no scanner to check. A
  scanner's rule list belongs to that scanner, so `taxonomy/tools.yaml` reaches it only
  through an environment variable and the validator now **rejects** a `rules_source.path`
  that leaves this repository. That rule exists because aguard's used to be
  `../agent-guard/docs/rules.md` — a sibling directory on one machine. Nothing broke, which
  was the problem: `make validate` reported "73 ids, 56 carry a dimension" there and
  "not checked" everywhere else, so the corpus's own result depended on the author's
  directory layout. The remaining gap is real and belongs elsewhere: **no scanner's
  repository yet clones this corpus to check its own `expect` blocks against its own rules**,
  which is where that check has to live.
- **`sha256` is verified in layer 1 and still empty in layer 2.** The 393 harvested
  configuration files each carry the hash of the bytes as collected, and `make validate`
  recomputes all 393 from the vendored artifact and fails on a mismatch. The 1,197 harvested
  server and skill TREES cannot: the label's `sha256` names one file and is refused on a tree,
  so their integrity claim is `tree_sha256` in `manifest/pins/mcp-servers.json`, recomputed by
  `scripts/harvest-mcp-servers.py --from-pins`, not by `make validate`. Every *manifest* entry still carries an empty
  `sha256` and the fetcher checks the pinned commit only: a reference has no bytes here to
  hash, so for layer 2 integrity still rests on git.
- **The table-shaped upstreams are not reproducible from `make fetch` alone.**
  `automatelab-mcp-tools` and `SkillMD-138K` ship parquet tables, not sample trees, so each
  needs a script under `scripts/` between the fetch and the derive. The scripts are pinned and
  seeded, but `make derive` does not run them, so a clean clone cannot rebuild those two
  entries in one command.
- **The benign side is a sample; the malicious side is a census, with two exceptions.** 4,473
  benign samples are drawn from stated populations under stated designs; 310 of the 568
  malicious samples are everything their upstreams had, the 240 from SkillHarm are a
  seeded draw of 20 per risk from 641, and the 18 from `clawhub-live` are the candidates two
  independent AI readers (or, for the ones they left open, two models) both read as malicious, out of 279 the registry's judge flagged. A recall figure and a false-positive figure from this corpus
  therefore rest on different kinds of denominator, and cannot be combined into one score.
- **No dimension has a wild recall rate yet.** `corpus score` splits recall into wild, fixture
  and constructed, and on the wild row no dimension holds enough samples for a rate — at most
  13. Every redistributable source of real-world malicious skills has now been read: all 204 of
  `datadog-ai-skills` (23 derived once fixtures and copies of one campaign payload are removed)
  and the 124 of `agent-skill-malware` (each a copy of the same few ClawHub lures, or a
  defensive scanner mislabelled for quoting their IOCs). Larger sets with more distinct wild
  samples exist but cannot be redistributed (MalSkillBench is for academic use only,
  SkillTrustBench is NC-SA). `clawhub-live` is the one source that keeps producing: a weekly
  intake of registry-flagged skills, 6 derived from the first 279 candidates. Until it has
  accumulated, the wild row is coverage, and the recall rates this corpus can report are rates
  about the fixture sources named beside them.
- **One tool has rule-level expectations.** `taxonomy/tools.yaml` registers three scanners
  (aguard, ccaudit, skill-scanner), but only aguard carries `expect` blocks, on 6 samples; the
  other two are scored on `truth` alone.
- **`NOTICE` is not cross-checked** against label licenses by `make validate`.
- **One harness package has no tests**: `fetch`.
- **5 of 36 dimension × tier cells have no sample.** `make stats` names them.
- **Three surfaces have no wild malicious sample.** hooks, permission and connector hold 5, 6 and
  5 malicious samples, every one reconstructed from a named disclosure (CVE-2025-59536 and the
  like), because no public corpus contains a weaponised hook or permission grant as an
  artifact. On those surfaces this corpus measures over-alerting against real configs (188, 168
  and 121 benign by `make stats`) and coverage of the disclosed shapes — never a recall rate.
  Some hard negatives there pair with twins on the *skills* surface — stated in their labels —
  so a scanner that never parses a settings file can go quiet for lack of coverage rather than
  by discriminating.
- **The config harvest is not reproducible from its script.** GitHub code search ranks by
  relevance and returns a different hundred each day, so `scripts/harvest-claude-config.py`
  accumulates into `manifest/pins/claude-config.json` and `--from-pins` rebuilds exactly that
  recorded set. A published figure is reproducible from the pins file, never from a re-search.
  The same holds for `scripts/harvest-mcp-servers.py` and `manifest/pins/mcp-servers.json`
  (server source and recent skills), whose `--from-pins` also recomputes each tree's hash.

## License

Content written by us is MIT (`LICENSE`). Vendored third-party samples in layer 1 keep their
original license, itemised in `NOTICE`. Layer 2 is never vendored.
