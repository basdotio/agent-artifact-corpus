> English · [中文](classification.zh-CN.md)

# What is measured

Eight classes. Each row states what the number answers, what it needs, and — the column that
matters most — **what claim it licenses**. That last column exists because the failure this
repository was created after was not a bad measurement. It was a real observation used to
support a sentence it could not support.

| # | Class | Answers | Metric | Licenses the claim |
|---|---|---|---|---|
| 1 | **False positive** | Will operators turn it off? | precision, per source | "On corpus X, N% of benign artifacts are blocked" |
| 2 | **Recall** | Does it catch real attacks? | recall, per dimension | "Of N labelled malicious samples from M sources, it flags K" |
| 3 | **Disclosure** | Does it admit what it did not look at? | disclosed / injected | "Every injected coverage gap produced a note" |
| 4 | **Evasion resistance** | Does re-encoding the payload defeat it? | survived / variants | "Payload P survives K of N transformations" |
| 5 | **Invariants** | Does it violate its own guarantees? | pass/fail, no rate | "No sample caused execution, egress, or a leaked secret" |
| 6 | **Gate** | Does a verdict actually stop a load? | pass/fail + latency | "Verdict V produces decision D under permission mode M" |
| 7 | **Robustness** | Can the scanned target kill the scanner? | terminates, peak RSS | "Bounded memory and a verdict within T on adversarial input" |
| 8 | **Performance** | Does it finish inside the gate deadline? | p50/p95 wall time | "p95 scan of a real environment is T seconds" |

Classes 1 and 2 are rates and carry all the sampling hazards. Classes 3 through 7 are
properties: a single counterexample refutes them, so they need no denominator and cannot be
diluted by a convenient one. **Prefer a property over a rate whenever the question admits
one.**

## Which of these travel to another scanner

The classes split a second way, and it has to be stated or someone benchmarking a different
tool will find half the corpus inapplicable and assume it is broken rather than by design.

**Portable — classes 1, 2, 4, 8.** False positive, recall, evasion resistance and
performance are questions about any scanner. They are answered from a label's `truth` block,
which is written in technique names no product owns, so running them needs nothing from us
beyond the sample trees. See [`label-schema.md`](label-schema.md#the-two-halves).

**Specific to one tool — classes 3, 5, 6, 7.** Disclosure asks whether the tool admits what
it did not read; invariants, gate and robustness are assertions about one implementation's
guarantees, its permission modes and its process. A scanner that makes no such promise cannot
fail these, and scoring it against them would be measuring the absence of a feature rather
than a defect. These are expressed inside `expect.<tool>` for exactly that reason.

## Two parts: did it find anything, and did it say what

Classes 1 and 2 each split in two, and collapsing the halves is how two very different
scanners end up with the same number.

**Part 1 — detection.** Did it report a finding at or above the sample's `truth.severity`?
Benign and hard-negative samples assert the reverse. Scored from `truth` alone, so it needs
nothing from us but the sample trees.

**Part 2 — attribution.** Having found something, did it say what *kind*? The tool reports in
its own categories, so each entry in [`taxonomy/tools.yaml`](../taxonomy/tools.yaml) carries a
`dimension_map` from those categories to ours. Evaluated only on samples that passed part 1.

The outcome of a run is one of these per sample, never a boolean:

| Outcome | Meaning |
|---|---|
| `hit` | flagged at or above `truth.severity` |
| `weak-hit` | flagged, but below it — caught and still allowed to load |
| `wrong-reason` | flagged, but the rule `expect.<tool>` named did not fire |
| `miss` | not flagged |
| `false-positive` | a benign or hard-negative sample flagged above its bound |
| `clean` | a benign or hard-negative sample within its bound |
| `error` | the scanner crashed or timed out; counts as a miss |
| `not-measured` | no result for this tool |

And on the samples that passed part 1: `classified` (the right dimension), `misclassified`
(a different one), or **`smelled`** — every finding mapped to no dimension of ours. A scanner
whose only output on a wrapped reverse shell is "obfuscation" detected that something was
hidden, not that there was a backdoor. Both pass part 1. Only one is usable.

Two scanners at the same recall can be entirely different tools:

| | detected | of those, classified | of those, smelled |
|---|---|---|---|
| A | 80% | 90% | 4% |
| B | 80% | 30% | 65% |

B is a smell detector. No single score separates it from A.

## The grid a failure is read off

A result has to be locatable, or "it is weak at exfiltration" is the end of the conversation
rather than the start. Every sample carries three coordinates, and each one, when a cell
fails, points at a different fix.

| Axis | Says | A failure here means |
|---|---|---|
| `dimension` | what the sample achieves | a capability is missing |
| `tier` | how deeply it is buried | the matching is too literal |
| `evasion` | which mechanism buries it | exactly which transformation to handle |

`tier` runs `plain` → `indirect` → `evasive` → `structural`, with `maps_to` recording the
equivalent level in skillsgoat and cisco so their published figures stay comparable.
**`plain` is a calibration floor**: a miss there is a property failure, not a low score. It
says the scanner is broken rather than weak, and the two must never land in the same number.
The same reading runs in reverse for hard negatives — firing on a `plain` hard negative means
broken.

`obfuscation` is deliberately **not** a dimension, though both skillsgoat's categories and
AgentGuard's scoring dimensions make it one. It describes how an attack hides, not what it
achieves, and on one axis with the rest a sample is either a backdoor or obfuscated and never
both. The question worth asking — *does this scanner handle an obfuscated backdoor* — becomes
inexpressible. Here that sample is `backdoor` / `evasive` / `base64-wrapper`.

The reporting grid is `dimension × tier`, 32 cells. Surface is a separate table rather than a
third axis of the same one: 8 × 4 × 6 is 192 cells for a corpus this size, and a hole-naming
discipline that emits 190 lines of noise is one people learn to ignore.

The recall axis in class 2 is the `dimension` of a technique in
[`taxonomy/techniques.yaml`](../taxonomy/techniques.yaml), never a scanner's own rule
categories. Taking the axis from the tool under test is how a per-dimension recall figure
becomes circular: it reports that the tool covers the categories it chose to have categories
for.

---

## 1. False positive

The only class where the corpus **must** come from outside. A benign sample written by
someone who knows the rules is imagined benign.

Reported per source, never only as a pooled average. Pooling is what produced the 12.9%
that started this repository: two authors were 87% of the denominator, and the per-source
spread (0.0%–30.8%) was wider than the pooled figure.

- **Primary**: `SkillMD-138K` (138,133 skills / 20,556 repos, CC-BY-4.0) — the widest
  real-world distribution available.
- **Secondary**: `clawhub-security-signals` clean split (41,743, MIT). **Caveat that must
  travel with it**: its labels come from an OWASP Agentic Top 10 rating, which is the same
  taxonomy most scanners in this space derive their rules from. Using it to select benign
  samples is partly circular against almost any of them. Use
  it for scale, never as the headline.
- **Full trees**: awesome-list link targets (1,231 trees / 382 repos, cap 5 per repo) — the
  only benign source with real scripts alongside the manifest, and human-collected, so
  non-circular.
- **Never**: any "clean" label that means popularity, vendor curation, or "no scanner
  complained". Those are circular for us by construction.

Reporting rule: **n beside every ratio, source count beside every n, and both the
sample-weighted and source-unweighted figures.** If they disagree, the disagreement is the
result.

## 2. Recall

Per dimension, not pooled. A tool that catches 90% of injection and 0% of reverse shells has
no meaningful aggregate recall, and W-027 is exactly that case: `BD-003` matches three
string literals and misses every language-native reverse shell.

- **Primary**: `DataDog/malicious-software-packages-dataset` `samples/ai-skills/` (204
  in-the-wild, manually triaged, Apache-2.0). **Deduplicate by author before counting** —
  40% carry one vendor's name and about 40 are near-duplicates, so an undeduplicated recall
  figure measures whether one template was caught.
- **Capability probes**: `skillsgoat` (101 malicious — 66 single plus 35 chains — MIT) —
  blind, answers held outside the tree, an error counts as a miss. Its 10 deliberate
  false-positive decoys are not part of that figure and are not recall material: firing on
  them is the failure, not the fix.
- **Hook and permission weaponisation**: `skillcraft-audit` (150, MIT) — the only public
  corpus covering these at all.
- **MCP**: `cisco-ai-defense/mcp-scanner` evals (154, Apache-2.0).
- **Touchstone, never vendored**: `trailofbits/overtly-malicious-skills` (4, no license) —
  each of the four defeats line-by-line rules by a different mechanism.

**Excluded from the denominator, and named in the report**: samples malicious in ways this
tool states it does not detect (pure runtime behaviour, anything requiring a live MCP
connection). Silently leaving them in understates recall and hides the design boundary;
silently dropping them overstates it. Naming them does neither.

## 3. Disclosure

Nothing is omitted silently. **Almost no scanner in this space measures this at all**, which
is why the corpus has to carry it rather than expect it. The one scanner measured here so far
fails it worst of the eight classes: a `chmod 0111` once turned a 26/100
artifact with four findings into 100/100 with zero notes (W-001).

Method: take a known artifact, inject one coverage gap, assert the score is unchanged *and*
a dimension-0 note names it. Gap kinds: unreadable directory, unreadable file, oversized
file, non-regular file, symlink outside the boundary, unresolvable symlink, credential
import, generated directory, binary with unknown extension.

This is a property class. The metric is `disclosed / injected`, and anything below 100% is a
defect, not a score.

## 4. Evasion resistance

Distinct from recall: recall asks whether a payload is caught, this asks whether *the same
payload* survives transformation. One payload, N encodings, count how many still fire.

Transformation families: line continuation, quote splitting inside a command word,
zero-width characters, blank-line padding, extension/magic mismatch, bundled `.pyc`,
base64 and other wrappers, Unicode confusables in hostnames, and bidi overrides in filenames.

Reported as a matrix, payload × transformation, because the aggregate hides which mechanism
is weak. A cell that flips from fire to silent is a regression regardless of what the totals
do.

## 5. Invariants

Binary. Each is asserted over every sample in the corpus, not sampled.

| Invariant | Assertion |
|---|---|
| Never execute | No process spawned; sample payloads write canary files that must not appear |
| Never phone home | No outbound connection during a non-`--llm` run |
| Redaction chokepoint | No secret-shaped string from any sample appears in any output |
| Symlink boundary | Fail-closed; unresolvable resolves to refusal, not to a read |
| Two scores | `OverallEffective <= Overall` holds for every sample |
| Determinism | Same bytes, same output, across repeated and concurrent runs |
| Terminal sanitisation | No control or bidi character reaches a human-facing renderer |

The canary mechanism is the load-bearing part: an assertion that "nothing ran" is only as
good as the evidence that something would have been noticed if it had.

## 6. Gate

The gate is where a verdict becomes an outcome, and where the most embarrassing failures
live: a 51/100 skill with a full credential-exfiltration chain once returned `ask` under a
permission mode that auto-accepts, so it loaded silently.

Cases: verdict maps to the right decision per permission mode; approvals keyed by canonical
hash, so one changed byte re-prompts; an approval granted for reviewed bytes does not carry
to substituted bytes; every fail-open path emits `GATE-000` rather than silence; and the
scan completes inside the deadline (see class 8 — on a real machine it did not, W-021).

## 7. Robustness

The scanned target is attacker-controlled, so it must not be able to kill its auditor.
Hangs matter more than crashes here: a crash is reported, a hang is silence that looks like
success.

Inputs: FIFOs in place of every file the scanner opens, multi-gigabyte config files, deeply
nested and wide trees, symlink cycles, zip bombs in the inbox path, and files that grow
while being read.

**Every test in this class carries a deadline.** A regression here manifests as a test that
hangs, and a hung test reports nothing at all.

## 8. Performance

Measured against a threshold that exists in the product: the gate's 30-second scan deadline.
The real-machine figure is 57–60 seconds for 1.4 GB across 14,336 files, which means the
gate times out on every session start and reports that it could not audit anything.

Reported as p50/p95 by environment size, with the deadline drawn on the same axis. A latency
number without the threshold beside it is decoration.

---

## Why this classification

Grouped by **what kind of statement the result supports**, not by what part of the code is
exercised. Two consequences that matter in practice.

Classes 1 and 2 need corpora we did not write, and their sampling discipline is the whole
job. Classes 3 through 7 need corpora we *must* write, because they require injected faults
that no public dataset contains, and they are immune to sampling bias because a single
counterexample settles them.

And the classes pull in opposite directions. Reducing class 1 means firing less; raising
classes 2 and 4 means firing more. Anyone working on one can silently undo the other, which
is why every entry in `corpus/hard-negative/` is paired with a malicious sample: the
suppression and the proof that the rule still works land together or not at all.
