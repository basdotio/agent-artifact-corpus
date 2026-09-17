> English · [中文](design.zh-CN.md)

# How the corpus is built

[`classification.md`](classification.md) says what is measured. This says where each class
gets its material, and which hazards attach to it.

Read the hazards. Every external corpus listed here has at least one, and two of them are
booby-trapped in ways that produce a perfect score from a one-line regex.

---

## The shape of the problem

Eight measurement classes (classification.md) split cleanly by who can supply the samples:

| Classes | Source | Why it cannot be the other way |
|---|---|---|
| 1 false positive, 2 recall | **External** | We cannot write samples that surprise us. Our own adversarial fixtures were written by the people who wrote the rules, so they contain only shapes we already thought of. This is structural, not carelessness — no amount of care removes it. |
| 3 disclosure, 4 evasion, 5 invariants, 6 gate, 7 robustness | **Ours** | They need *injected faults*. No public dataset contains a skill with one subdirectory at `chmod 0111`, because no other scanner has an invariant about admitting what it did not read. |
| 8 performance | **Real machines** | A synthetic tree of the right byte count has the wrong file-count distribution, and file count is what the walk costs. |

The proof that classes 1 and 2 must come from outside is not an argument. Pointing the
scanner at DataDog's corpus, **the first sample** exposed a shape absent from all 30 of our
adversarial scenarios: a textbook reverse shell scoring 88/100, passing `--fail-on high`.
The rule meant to catch it, `BD-003`, matches three string literals and misses every
language-native form.

---

## Layer 1 — vendored, offline, ours

`corpus/<class>/<surface>/<id>.yaml` (the label) beside `corpus/<class>/<surface>/<id>/`
(the sample tree). The label never goes inside the tree — see
[`label-schema.md`](label-schema.md) for what that cost us.

**Classes**: `benign`, `malicious`, `hard-negative`.
**Surfaces**: `skills`, `hooks`, `permission`, `mcp`, `connector`, `instruction`.

A surface is a **load path**: the place an agent reads an artifact from, which decides what
the artifact can do. Listing the six without defining them is why `connector` stayed empty
for as long as it did — nobody could say what artifact belonged there, so nothing did.

| Surface | The artifact | What makes it this surface |
|---|---|---|
| `skills` | a skill directory (`SKILL.md` plus whatever it ships) | the agent reads it as instructions it may follow |
| `hooks` | a settings file with a populated `hooks` block | it runs a command on an agent event, without being asked at the time |
| `permission` | a settings file with a populated `permissions` block | it decides what the agent may do without asking |
| `mcp` | a server's tool declarations (names, descriptions, input schemas) | the agent reads it to learn what a tool is for |
| `connector` | a config that wires in something outside the agent, reaching a remote endpoint (`url` with an http/sse transport, an OAuth scope grant, a `.mcpb`/`.dxt` manifest) | it grants access, rather than describing a tool |
| `instruction` | free prose an agent is told to treat as guidance | it carries no load path of its own; it arrives as content |

`surface` is a **list**, because one file is often two load paths. A real
`.claude/settings.json` normally carries both a `hooks` block and a `permissions` block —
three of the first five real files sampled had both. Filing such a file under one surface
would make `permission` mean "settings files that happen to have no hooks", a subpopulation
invented by the schema rather than found in the world. The artifact is vendored once, its
first surface owns the directory, and per-surface counts therefore do not sum to the sample
count. `corpus stats` says so where it prints them.
**Techniques**: from [`taxonomy/techniques.yaml`](../taxonomy/techniques.yaml), and they are
the part of a label that belongs to nobody. A label's `truth` block is written in them and is
enough on its own to score any scanner; `expect.<tool>` adds one named scanner's rule IDs on
top and is optional. That is what makes layer 1 usable by someone benchmarking a tool we did
not write, and it is why the validator must run with no scanner checked out.

`hard-negative` is a separate class, not a flavour of benign, because it carries an extra
obligation: **every hard negative is paired with a malicious sample that must still fire.**
A suppression and the proof that the rule still works land together or not at all. Without
the pair, "reduce false positives" degrades into "delete the rule", and nothing catches it.

### What layer 1 must contain

**Every confirmed false positive, pinned.** Four are confirmed today: a UTF-8 BOM at file
offset 0, `os.environ.copy()` passed to a subprocess, **defensive prose teaching an agent to
refuse injection**, and one `atob(` reported by two rules at once. Each gets a
`hard-negative` entry with the rule ID in `quiet:`, and each gets its malicious twin. Fixing
a false positive by editing one regex is undone by the next regex change, silently. Turning
it into a sample makes "this must not fire" a regression-testable property.

**Every injected-fault case for classes 3–7.** These are the ones only we can write.

**Nothing licensed more restrictively than the repo.** See [`licensing.md`](licensing.md).
Layer 1 is MIT plus permissive vendored material; anything no-license, NC, SA, or copyleft
belongs in layer 2 or nowhere.

### The part that cannot be a file

Git does not carry directory permission bits, and BSD `tar` cannot reproduce `0111`
(measured). So this entire family is constructible **only in test setup code**, not as a
checked-in fixture:

- traverse-only directories (`chmod 0111`) — the agent executes by path, `WalkDir` cannot read
- FIFOs standing in for `SKILL.md`, `settings.json`, `.mcp.json`
- symlink escapes and cycles
- files that grow while being read

`fixtures/` is where the Go constructors for these belong. **It is empty today** — the
directory exists and nothing has been written into it, which makes this the largest declared
hole in layer 1. **Disk fixtures take scale and non-Go contributors; a Go harness takes the
filesystem-level evasions.** Neither replaces the other, and the three most severe defects
found in audit so far are all in the second group.

---

## Layer 2 — referenced, fetched, never vendored

`manifest/*.yaml` records a pin and what is known about it: `url + commit + sha256`, the
`license` and `role`, the counts the source claims, and the `hazards`, `overlaps` and `prep`
that decide how it may be counted. **No sample content, ever.**

Recording a URL and a hash is not distribution. That is the whole reason this layer exists:
it can reference no-license, CC-BY-NC-SA, and AGPL corpora, measure against them locally,
and publish aggregate figures, all outside the reach of their distribution terms.

### Malicious

| Corpus | License | Malicious | Role | Hazard |
|---|---|---:|---|---|
| **`DataDog/.../samples/ai-skills`** | Apache-2.0 | 204 | **Primary.** Only in-the-wild, manually triaged, cleanly licensed skill set | **40% carry one vendor's name**, ~40 near-duplicates; ~26 (13%) are other scanners' synthetic tests, not in-the-wild. **Dedupe by author or canonical hash before counting.** |
| `optimuslabs-io/skillsgoat` | MIT | 66 + 35 chains | Capability probe; blind, answers outside the tree, an error counts as a miss | Includes 10 FP decoys — intentional, do not "fix" |
| `Clay-HHK/skillcraft-audit` | MIT | 150 | **Only public coverage of hook weaponisation and permission bypass** | Single author |
| `cisco-ai-defense/mcp-scanner` `evals/` | Apache-2.0 | 154 | MCP surface; directory is the label | Only 4 benign |
| `trailofbits/overtly-malicious-skills` | **none** | 4 | **Touchstone.** Each defeats line-by-line rules by a different mechanism | Zero grant — never vendor. Also contained in DataDog above and SkillTrustBench below |
| `Agent-Threat-Rule/atr-skill-benchmark` | MIT | 466 | Includes `evasive-stub`, explicitly built for FP testing | Subset of MaliciousSkillBench |
| `cuhk-zhuque/SkillTrustBench` | **CC-BY-NC-SA** | 2,863 + 1,014 | **Best structure available**, and the only corpus anywhere labelling defensive-prose FPs (`injected_d8`, 119 samples, 118 `normal`) | NC + ShareAlike. Local measurement only, forever |
| `lxyeternal/MalSkillBench` | **none** | 3,944 | Scale | **Label leakage — see below** |
| `protectskills/MaliciousSkillBench` | code Apache-2.0 / data CC-BY-4.0 | 7,505 | Scale | **Aggregates 13 sources** — overlaps most of this table |

### Benign — the half that decides the false positive rate

| Corpus | License | Size | Role | Hazard |
|---|---|---:|---|---|
| **HF `FayeZC/SkillMD-138K`** | CC-BY-4.0 | 138,133 / 20,556 repos | **Primary FP denominator.** Widest real-world distribution | `SKILL.md` body only — no scripts, so script-surface rules are untested by it |
| HF `OpenClaw/clawhub-security-signals` | MIT | 41,743 clean | Scale | **Partly circular**: labels come from an OWASP Agentic Top 10 rating, the taxonomy most scanners in this space derive their rules from. Never the headline |
| **awesome-list link targets** | 457/573 permissive | 1,231 trees / 382 repos | **Full trees with real scripts, human-collected, non-circular** | Cap 5 per repo or a few large repos dominate |
| `shenyimings/skillet` `benchmark/wild/` | MIT | 483 safe | Repo-disjoint by construction; records `label_source` | Small |
| `anthropics/claude-plugins-official` | Apache-2.0 | 31 skills / 39 plugins | First-party curation | Some entries already sit in the reputation allowlist of the scanner measured here — **not independent of the tool under test** |
| `NVIDIA/skills` | Apache-2.0 | 356 | **Only corpus with cryptographic signatures** (Sigstore) | Private PKI |
| Vendor repos (google, adobe, stripe, microsoft, …) | Apache-2.0 / MIT | 14–337 each | Enterprises publishing permissively under their own namespace | Style-homogeneous per vendor |
| **`anthropics/skills`** | **proprietary** | — | — | **Hard red line.** Per-skill `LICENSE.txt` says All rights reserved, forbids Reproduce and Distribute. Not usable, in either layer |

### Hard negatives — benign that looks like an attack

| Corpus | License | Size | Why it is hard |
|---|---|---:|---|
| **`automatelab/mcp-servers-tool-catalog`** | CC-BY-4.0 | **9,922 tools / 359 servers** | Real tool descriptions legitimately contain `IMPORTANT:`, `<placeholder>`, tokens, URLs. **Our `MCP-001..004` have been validated against 44 tools.** This is the 225× expansion |
| `NVIDIA/SkillSpector` `tests/fixtures/` | Apache-2.0 | ~6 pairs | **Paired twins**: each malicious fixture has a near-identical clean version. The only structure that tests whether a hit is on the *difference* rather than on the topic |
| `DataDog/guarddog` `tests/.../benign/` | Apache-2.0 | 25 | Each benign file carries a comment naming the real false positive it fixed |
| `ossf/package-analysis` `detections/*_test.go` | Apache-2.0 | ~191 | **Go, table-driven, same language and style.** URL fixtures inline-annotate their own misjudgements, including hex escapes and IDN — the confusable surface that has already produced a real defect in a scanner measured here |
| `mcp-guardbench` `cases/benign/` | MIT | 20 | Deliberate traps: Cyrillic prose, `ignore`-flag documentation, AWS *example* keys |
| `anthropics/.../security-guidance` | Apache-2.0 | 1 | Attack-pattern regexes plus warning prose, **registered as a hook**, so it lands on a real load path. **Measured 88/100, zero high on the scanner wired up today.** Keep as standing regression |
| `fevziegeyurtsevenler/prompt-injection-corpus` | CC-BY-4.0 | 5 | Dense literal `ignore previous instructions`. **Every `INJ-*` hit is a false positive** |
| this repository's own tree | MIT | 1 | Documents in prose every pattern a scanner detects, so it is a maximally adversarial benign input. Free, reproducible |

**Do not use over-refusal benchmarks** (OR-Bench, XSTest, FalseReject). They measure *model*
over-refusal, not *scanner* over-alerting, and they are prompt strings, not artifacts.

---

## Hazards that silently produce a perfect score

**Label leakage in `MalSkillBench`.** 3,878 of 4,000 benign samples carry a `_meta.json`;
0 of 3,944 malicious samples do. **Looking only for that one file classifies the whole corpus
at 98.5% without reading any skill content** — every malicious sample and 97% of the benign
ones. Delete that file before use. (The companion rumour that malicious directories are
empty is false — all 3,944 have a `SKILL.md`.)

**Shortcut features in `skillfortifybench`.** Malicious samples use RFC-2606 reserved
domains; benign samples never do. One regex scores perfectly and generalises to nothing.

Its successor ships the mechanism worth copying: `metrics/leakage.py` is a **mechanical
release gate** — any structural feature with support ≥8 that predicts the label at ≥95%
purity fails the build. `make validate` implements the same idea here. A corpus that can be
solved without reading content is not a corpus.

**Circular benign labels.** Smithery `verified`, Glama `qualityScore` (a paid placement),
reputation scores — all popularity or vendor curation, none a security review.

### Benign credibility ranking

Strongest to weakest:

1. Cryptographic attestation (NVIDIA only)
2. Enterprise permissive publication under own namespace
3. Official marketplace inclusion
4. Marketplace "not suspicious" flag plus download count
5. **"No scanner found a problem" — circular for us. Not usable at any weight.**

---

## Contamination map — these numbers do not add up

```
MaliciousSkillBench ⊃ SkillTrustBench + MalSkillBench + ATR + SkillFortifyBench + …
SkillTrustBench     ⊃ overtly-malicious-skills (4)
DataDog ai-skills   ⊃ overtly-malicious-skills (tjade273-* is simple-formatter)
snyk-labs           ∩ pyxeroai  = both from NET_NiNjA
```

Every manifest entry declares `overlaps:`. `make stats` refuses to print a pooled total
across entries that overlap, because the sum would be a lie in the safe-looking direction.

## Source-disjoint splits are mandatory

Cisco measured recall falling **31.43% → 7.75%** when the split went from random to
source-disjoint. A random split trains and tests on the same author's templates, and what it
measures is template memorisation.

This bit us on the benign side too. A machine-wide false positive figure of 12.9% turned out
to be 7 sources with two of them at 87%, and a per-source spread of 0.0%–30.8% — wider than
the figure itself. That number describes two authors' writing habits.

**Therefore**: every rate is reported per source, with `n`, with the source count, and with
both the sample-weighted and source-unweighted values. Where they disagree, the disagreement
is the result.

---

## Build order

Layer 1 schema and validator come first — cheap, and their output is the sampling list for
everything after. Collecting first guarantees re-labelling everything later.

That output is now two lists, because a label is two halves. `make stats` prints **every
technique in the vocabulary including the ones with no sample**, which is the tool-neutral
hole and the one another team can act on; six of nine dimensions are empty today. And per
tool, **which of its scoring rules has no sample at all** — a count that must be read from
the tool's generated rule reference, never written by hand. An earlier revision of this paragraph
wrote that count out by hand as 61 while the generated header said 62 — the drift the rule
exists to prevent, committed in the document that states the rule. There is no number here
now, deliberately.

| Phase | Content | Then we can say |
|---|---|---|
| **0** | Schema, validator, leakage gate; promote whatever adversarial cases a scanner already has | Real numbers on a small set, **and which techniques and which scoring rules are untested** |
| **1** | FP denominator: `SkillMD-138K` + awesome trees + clawhub, per source | The false positive rate becomes meaningful |
| **2** | Recall: DataDog deduped, skillsgoat, ToB touchstone | Recall is publishable, per dimension |
| **3** | Our own surfaces: skillcraft-audit and cisco for malicious; **harvested** real hooks, permissions, MCP configs for benign | The differentiating surfaces are covered |
| **4** | Classes 3–7 injected faults; `fixtures/` Go constructors | The property classes have evidence |
| **5** | CI gate on layer 1, published report on layer 2 | Externally citable |

Phase 1 before phase 3, always. Building our own first guarantees building in the wrong
direction — the reverse shell gap is the standing proof.

## What the report must publish

Beyond the rates: **the techniques with no sample, and the rules with no sample, both named.**
Same discipline as a scanner's own
`COV-000` — a declared hole is something an operator can act on, a hidden one is a lie.
The denominator is the `score` count in the header block of the tool's generated
`docs/rules.md`, never a hand-written number.

And one standing prohibition: **"the external corpus does not contain it, so our rule is
fine" is not an argument.** A public corpus covers its authors' chosen topics, not the
threat surface. Layer 1 exists to fill that gap, not to certify it away.
