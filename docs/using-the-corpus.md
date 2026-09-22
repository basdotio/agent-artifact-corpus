> English · [中文](using-the-corpus.zh-CN.md)

# Measuring your scanner against this corpus

For anyone — person or agent — pointing a static scanner of AI agent environments at this
corpus. You need nothing from us: no account, no registration, no entry anywhere in this
repository. Clone it, run three commands, read a scorecard.

This document is the protocol and, just as importantly, **what each number is allowed to
mean**. A benchmark that hands you a percentage without saying what it does not cover is how
a scanner ends up with a good score and a bad product.

---

## The loop, in three commands

```bash
git clone https://github.com/basdotio/agent-artifact-corpus && cd agent-artifact-corpus
cd harness

go run ./cmd/corpus samples > samples.jsonl     # 1. the work list
<your runner> < samples.jsonl > verdicts.jsonl  # 2. YOUR part
go run ./cmd/corpus score verdicts.jsonl        # 3. the scorecard
```

Step 2 is the only part you write. Steps 1 and 3 are ours and know nothing about your tool.

### 1. `corpus samples` — the work list

One JSON object per line, one per sample:

```json
{"sample":"mal-hook-sessionstart-rce","path":"corpus/malicious/hooks/sessionstart-rce","class":"malicious","surface":["hooks"],"severity":"critical"}
```

| Field | Meaning |
|---|---|
| `sample` | the id you must echo back in your verdict |
| `path` | the sample tree, repo-relative — **point your scanner here** |
| `class` | `malicious` / `benign` / `hard-negative` — the answer, given to you openly |
| `surface` | which load path(s) the artifact sits on; a list, because one file can be both |
| `severity` | present on malicious samples |

**The answers are not hidden, and that is deliberate.** This is not a puzzle to be solved
under exam conditions; it is an instrument. Nothing stops you training on it — and if you do,
your score stops meaning anything, which is your problem to avoid, not ours to police.

### 2. Your runner — the only part that knows your tool

For each line: point your scanner at `path`, decide one word, emit one line.

```json
{"sample":"mal-hook-sessionstart-rce","verdict":"malicious","severity":"high","dimensions":["execution"]}
```

| Field | Required | Notes |
|---|---|---|
| `sample` | yes | must match an id from the work list |
| `verdict` | yes | exactly `malicious` or `benign` — nothing else parses |
| `severity` | no | your severity, on the ordinary ladder |
| `dimensions` | no | which KIND, in this corpus's vocabulary — unlocks the attribution score |

Malformed input is refused with a line number rather than skipped. A scorer that silently
drops records reports a rate over an unknown denominator, which is worse than not running.
Duplicate ids are refused for the same reason: two verdicts for one sample is an ambiguous
answer, and picking one would be inventing it.

**Collapsing your states to one word is your decision to make and to state.** Most scanners
have more than two outcomes — a score, a severity ladder, a needs-review band. Pick the
threshold that corresponds to what your product actually does (blocks a load, fails a build)
and say which one you picked when you publish. Score the corpus twice at two thresholds if
that is the honest answer.

#### The one hard part: your scanner's input model

A sample is a single artifact — a skill directory, a `settings.json`, a `.mcp.json`. Many
scanners instead expect a whole config ROOT (`~/.claude`-shaped) and discover artifacts inside
it. If you hand such a scanner a bare sample directory it may find nothing and report clean,
and you will have measured your runner rather than your scanner.

Use `surface` to place each sample where your scanner looks for that kind of thing. A real
example, measured against one scanner: a skill sample placed at `<root>/skills/<name>/` was
detected as a skill, while the same sample as a bare root was read as a loose instruction file
and scored clean. **A sudden column of zeros on one surface is nearly always this, not a real
miss.** Check placement before you believe it.

### 3. `corpus score` — the scorecard

```
detection — recall per dimension. collected and constructed never merge:
  dimension        evidence          n   result
  execution        collected        61   18%  [10, 29]  (11/61)
  execution        constructed       6   caught 1 of 6 (coverage of chosen shapes, not a rate)
  reconnaissance   collected        28   4%  [1, 18]  (1/28)
  resource-abuse   collected        16   caught 0 of 16 (n too small for a rate; ±19 pts)

  per source — a rate over one source is a rate ABOUT that source, not the world:
  cisco-mcp-scanner-evals         127   11%  [7, 18]  (14/127)
  skillcraft-audit                 42   71%  [56, 83]  (30/42)

flag rate on the benign pool — an estimate, reported per source:
  benign here means `somebody runs this`, on an `assumed` basis — these are flags,
  not confirmed false positives. Read one before you count it as an error.
  skillmd-138k                   1996   7%  [6, 8]  (133/1996)

hard negatives — the precision probe, a census, never pooled with the estimate above:
  flagged 5 of 19 (26%) — each one a confirmed false positive: these were read

attribution — of caught malicious with a read-basis dimension, was the KIND named:
  31 of 68 correct (46%, [34, 57])
```

---

## Reading it honestly

The scorecard is built to make the dishonest reading hard. Six rules are enforced in the
output itself rather than left to your judgement.

**Collected and constructed never merge.** A `collected` row rests on samples that came from
outside us — harvested configs, upstream datasets, real captures — so a rate over them is a
claim about the world. A `constructed` row rests on reconstructions of a disclosed attack and
on synthetic fixtures; those measure **coverage of the shapes we chose to include**, never a
rate that predicts the wild, and they print as `caught K of N` no matter how large N gets.
Adding the two numbers produces something that means nothing.

**A per-source rate is a rate about that source.** `cisco 11%` and `skillcraft 71%` on the
same scanner is a sixty-point spread, and pooling them into one figure would hide exactly the
thing worth knowing. Publish per source, with `n`, with the source count. This corpus was
built after a published 11.0% turned out to be 12.9% on the full population.

**A wide interval is printed as a count, not a rate.** Below the width where a percentage
would mislead, the line reads `caught 0 of 16 (n too small for a rate; ±19 pts)`. That is not
a formatting choice: a recall from a handful of samples carries an interval so wide it is not
a figure, and printing `0%` would invite a conclusion the data cannot support.

**A flag on a benign sample is not yet a false positive.** The benign half means *somebody
committed this to be loaded*; its class rests on `assumed`, nobody read it, and no security
review of it exists. So the benign table reports what your scanner DID — a flag rate — and how
much of it is error is a question these labels cannot answer. Read one before counting it.

The bridge is a `reviewed` block, and it is the only one: a benign label that someone has read
carries `reviewed: {date, verdict, note}` with the verdict one of `benign`, `would-fire` or
`not-benign`. It deliberately does NOT change `basis.class`, which stays `assumed` forever —
reading one file cannot prove harmlessness, and there is no quote for the absence of an attack.
What it does is let the scorecard say how many of your flags landed on samples a person read,
and those ARE confirmed false positives. The count starts small and grows one reading at a
time; when it is zero the scorer says so in words, because a silent zero would read as "no
confirmed false positives" when it means "nobody has looked".

**A census and an estimate are never one number.** The 19 hard negatives ARE read
individually — every one is a deliberate near-miss, so a flag on any of them is a confirmed false
positive you can go look at. The thousands of benign samples are a sample of a population.
They answer different questions and are printed apart.

**Attribution is scored only where the dimension rests on a reading.** Saying WHICH kind of
attack something is can only be graded against a dimension a person established by quoting the
artifact, not against one a batch rule assigned. So the attribution denominator is smaller
than your catch count, and that is the honest denominator, not a shortfall.

**An uncovered sample is not a pass.** If your runner emits nothing for a sample, the header
says so and the recall below is over the scored subset only. Silence is never scored as a
correct benign.

---

## The injected-fault fixtures

Some of what a scanner must survive cannot be checked into git — a directory permission bit, a
named pipe, a symlink cycle. Those are built on demand:

```bash
go run ./cmd/corpus fixtures                        # list them, with what each asserts
go run ./cmd/corpus fixtures --materialize /tmp/fx  # build the hostile trees
<point your scanner at /tmp/fx/*>
go run ./cmd/corpus fixtures --restore /tmp/fx      # REQUIRED before deleting
```

Six exist today. One is a **disclosure** test: a `0111` subdirectory a walk cannot enumerate —
a scanner that says nothing has scored an unread skill as read. The rest are **robustness**: a
FIFO standing in for `SKILL.md` (does an open-and-read hang forever), a symlink cycle (does a
walk loop), a symlink escaping to `/etc/passwd` (is host content read as skill content), a
4096-deep chain, an 8 GiB sparse `.mcp.json` (is the whole file loaded to parse it).

These are pass/fail per fixture, not a rate — a single counterexample settles them. They are
scored by your runner, not by `corpus score`, because the pass condition depends on what your
tool promises. `--restore` is not optional: the `0111` directory defeats the enumeration
`rm -rf` needs.

---

## What this corpus cannot tell you

Stated plainly, because a benchmark that hides its limits is worse than a small one.

| Limit | Why |
|---|---|
| **Config surfaces report coverage, not a rate.** hooks, permission and connector hold a handful of reconstructed shapes each | A recall RATE needs independent real-world samples. A survey of eight public datasets found none for these surfaces: every source that has them is synthetic, and every real-world source carries the injection/exfiltration shapes already covered. The ceiling is the world, not the effort |
| **Some dimensions are counts, not rates** | filesystem, reconnaissance and resource-abuse hold 16–28 samples each. Enough to find a systematic hole, nowhere near enough to separate 60% from 80% |
| **Benign is not "reviewed and safe"** | It means *somebody committed this to be loaded*. No security review of those files exists and none is claimed |
| **A high score is not a safety certification** | This measures what the corpus contains. A public corpus covers its authors' chosen topics, not the threat surface |

The corpus states its own holes the same way: `corpus stats` prints every technique with no
sample and every empty dimension × tier cell. A declared hole is something you can act on; a
hidden one is a lie.

---

## If this corpus contains your own test fixtures

It may. 127 of the malicious MCP samples derive from cisco-ai-defense's scanner evals, and 6
samples (5 of them malicious) come from NVIDIA's SkillSpector fixtures. If you are one of those projects, a figure over
the whole corpus is partly your scanner graded on its own tests, and it will flatter you.

Produce both numbers:

```bash
go run ./cmd/corpus samples --exclude-source <your-source-id> > samples.jsonl
```

`corpus samples` lists the source ids in its error message if you mistype one — and it REFUSES a
name no sample carries rather than filtering nothing, because a typo would otherwise hand you a
figure that looks de-contaminated and is not. The default excludes nothing: a denominator that
shrinks unless you ask is a denominator that shrinks without anyone noticing.

Both runs, then both numbers in the conclusion. `corpus score` helps by naming what is missing:
when samples have no verdict it prints them grouped by source, and marks the ones where an entire
source is absent.

**Excluding is not always the better number.** Dropping cisco's 127 leaves three malicious MCP
samples, which is too few for a rate — so on that surface there is no clean denominator for
anyone, and the honest report says that rather than picking whichever version reads better.

---

## If you want rule-level precision

Everything above works with no entry anywhere in this repository. If you want more than a
verdict — which of YOUR rules must fire on a sample and which must stay quiet — add your tool
to [`taxonomy/tools.yaml`](../taxonomy/tools.yaml) and labels can carry `expect.<yourtool>`
blocks, checked against your own severity ladder. Two scanners with different scales annotate
the same sample without either adopting the other's.

This is optional precision layered on top. The `truth` block alone scores any scanner, which is
the point of splitting the two — see [`label-schema.md`](label-schema.md#the-two-halves).

---

## Publishing numbers from this corpus

Three rules the corpus keeps on itself, and asks of anything citing it:

1. **Report per source, with `n` and the source count.** Never only a pooled average.
2. **Any exclusion appears in the conclusion with both figures** — with it and without it. A
   denominator that quietly dropped its worst-scoring group is how 11.0% hid 12.9%.
3. **Say which verdict threshold you used**, since collapsing a scanner's states to one word
   is a choice, not a fact.

And one prohibition worth repeating: *"the corpus does not contain it, so our rule is fine"* is
not an argument. This corpus covers what its sources covered.
