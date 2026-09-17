> English · [中文](audit.zh-CN.md)

# Independent audit, 2026-09-17

An audit of this corpus by eight agents running in clean contexts, each told to falsify a
claim rather than confirm it, and each required to attach a reproducible command to every
finding. This document records what they checked, what they found, what was corrected, and
what is still open.

Every figure below was computed at the time of writing. That is not a formality: the largest
single finding of this audit was 47 numeric claims in this repository's own prose that were
wrong, and the cause in every case was a number recalled rather than counted.

---

## Why an audit, and why not by us alone

`make validate` checks that the corpus is internally consistent. It cannot check whether a
label is TRUE — whether the sample really does what the label says. Nothing had ever checked
that. Of 3,494 samples, 19 carry coordinates a person wrote; the other 3,475 were placed by a
rule or a script and had never been read.

The corpus's own third red line says "no scanner complained" is not evidence of benignity.
The same logic points back at itself: **"validate passes" is not evidence that the labels are
correct.**

### What independence means here, and what it does not

The audit agents share a model family with the person who built the corpus. Swapping the
auditor does not swap the blind spots. So independence here does not rest on who audited; it
rests on **falsifiability**:

- every finding carries a command you can run yourself and a number you can check
- an observation with no command is recorded as unresolved, not as a finding
- each agent must report what it checked and found SOUND, not only what it found wrong — a
  list of problems alone is indistinguishable from an incomplete audit

That discipline earned its keep. **Three agent findings were wrong** and were caught by running
the commands they lacked: one reported the technique vocabulary held 24 entries when it holds
3 — an eight-fold error, stated confidently with line numbers; one judged a dimension against a
definition that had been corrected hours earlier; and one asserted the audit reading list was
committed when `.gitignore:5` excludes all of `cache/`, a claim a second agent got right and
stated as a caveat. All three are recorded here rather than quietly dropped, because an audit
that hides its own errors is asking for the trust it is supposed to be testing.

---

## Coverage

| Layer | What was checked | Coverage |
|---|---|---|
| Claims | every number and behavioural promise in 14 bilingual documents, the manifest and the taxonomy | ~355 claims, exhaustive |
| Instrumentation | every invariant `make validate` says it enforces, by constructing a violation for each | 111 invariants, 150 mutation runs |
| Duplication & integrity | exact and near duplicates, cross-class contamination, byte integrity against pinned upstreams | all 3,494 trees; 6,084,816 pairs exactly |
| Derivation fidelity | independent re-implementation of every `derive:` rule, diffed against the committed labels | 3,079 of 3,079 |
| Content leakage | token, structural and artifact features per population, base-rate aware | all samples; only 93 testable |
| Label correctness — coordinates | every sample carrying a `truth` block, read | 253 of 253, census |
| Label correctness — benign | stratified sample, 60 per population, seeded, every one read | 250 of 3,241 |

The last row is an ESTIMATE and the row above it is a CENSUS. They are never combined into
one accuracy figure; they are different kinds of statement. At n=60 per population a 95%
interval is about ±12 points — enough to find a systematic problem, nowhere near enough to
separate 2% from 8%.

---

## The three findings that mattered

### 1. The attribution axis was inverted, not merely imprecise

This corpus measures two things: did a scanner detect a problem, and did it say what KIND.
The second rests entirely on `dimension`, and a census of all 253 coordinate-bearing samples
found **86 disputed dimensions**.

Twenty cisco samples asserted `exfiltration` with **zero egress anywhere in the file** — every
tool returns a count, not content. A scanner correctly reporting host enumeration was being
scored WRONG. **A benchmark that marks the right answer wrong is worse than no benchmark.**

The root cause was one architectural mistake made three times — a per-sample truth assigned by
a per-category rule:

| Entry | Rule | Disputes it produced |
|---|---|---:|
| cisco | `unauthorized-network-access → dim:exfiltration` | 20 |
| skillcraft | `medium/hard → [tier:evasive, evasion:judge-targeting]` | 21 |
| skillsgoat | filename prefix `000/100/200/300` → tier | 13 |

These rules are faithfully mechanical: an independent re-derivation reproduced all 3,079
labels exactly. **The error was treating "mechanical" as "correct".**

48 dimensions were corrected — 29 cisco, 10 skillcraft, 9 skillsgoat — each read before it was
written. Two category rules were deleted rather than overridden: a rule wrong for all twenty of
its members should go, not be papered over sample by sample.

A ninth dimension, `reconnaissance`, was added, and 26 samples now carry it: 24 on the MCP
surface, two on the skills surface. They enumerate the environment, scan internal ports or query a metadata
endpoint and hand the result back to the caller: nothing leaves the host, so `exfiltration`
excludes them, and many touch no file, so `filesystem` does not fit. The alternative was
excluding two dozen real malicious MCP servers and losing the ability to ask "does this scanner
catch internal port scanning". Twenty of them lost the `exfiltration` label they had carried.

**Detection was unaffected.** Across all 253 samples read, disputes about `class`: **zero**.
Not one benign sample turned out to be malicious, not one hard negative turned out to be an
attack. Severity: 6 of 253.

### 2. The guards could not see what they were built to catch

- **`leakage.Imbalanced()` was dead code**, never called outside its own test, while its doc
  comment explained precisely why it had to exist. Its comment promised single-class
  populations were "reported elsewhere"; elsewhere did not exist.
- **`leakage active over 3489 samples`** reported the corpus's size as if it were the gate's
  reach. The gate can only reach a verdict inside a multi-class population below the purity
  ceiling — 87 samples, 2.5%. It now says so and names every population it cannot judge.
- **The gate only saw what a sample HAD.** A classifier uses absence as readily: "no SKILL.md"
  was a 100%-pure predictor it could not express.
- **`implies_tier` structurally could not catch the contamination it was written for.** Eleven
  calibration-tier samples were base64-wrapped, trigger-gated or fetch-and-obey. The rule fires
  only when an evasion value is PRESENT, and the same constant that set the tier wrong also
  left evasion empty. **The guard's input was supplied by the thing it guards.**
- **The pin check answered confidently about caches it never looked at.** `git -C cache/<id>
  rev-parse HEAD` returns a plausible sha for two upstreams that are parquet drops with no
  `.git` — git walks up and answers for THIS repository. No error, a real sha, the wrong
  repository.

### 3. One population ships its own answer key, and no gate can see it — OPEN

Every one of the 75 vendored skillsgoat trees contains an HTML comment of the form
`<!-- GOAT-CANARY-<label> -->`, which is the upstream's label surviving inside the artifact:

```bash
grep -rl 'GOAT-CANARY-benign' corpus/benign/skills/sg-* | xargs -n1 dirname | sort -u | wc -l
```

Ten of ten benign trees, zero of sixty-five malicious. **One substring separates that
population perfectly** — 100% precision, 100% recall, against a 13.3% benign base rate. And it
does not stop at the class: the malicious canaries carry a numeric prefix that recovers `tier`
in **64 of 65** samples, the single exception being the one sample a `tier_override` corrects.
A scanner scoring two of this corpus's four axes on skillsgoat can do it without reading a line
of the skill.

**No gate covers this, by construction.** `leakage.go:48` states it plainly: *"Contents are
deliberately not available here — the whole question is what is learnable without them."* The
gate is structural — filenames, extensions, tree depth. The canary is content, so it sits in
the one blind spot the design accepts on purpose.

What makes this worth stating bluntly: the leakage package's own header cites MalSkillBench
shipping `_meta.json` in 3,878 of 4,000 benign samples as the archetype it exists to prevent.
**This corpus documented that failure mode and then shipped an instance of it.**

It is left OPEN rather than patched, because every available fix costs something real and the
choice is not the auditor's to make: stripping the comment breaks "the artifact is vendored
unchanged" and every `origin.sha256` on the entry; excluding the population loses 75 samples
including the only structural-tier examples; declaring it keeps the samples and obliges every
figure computed on skillsgoat to carry the caveat. What is not acceptable is the current state,
where a perfect score on this population can be reported as detection.

### 4. Prose drifted from data, and the same fix had already been applied once by hand

47 of ~355 numeric claims were wrong. They were not 47 mistakes but four, each duplicated
across five documents and their Chinese mirrors: cisco's sample count in ten places,
skillcraft's in seven, automatelab's unit in five, skillet's repository count in five. In two
cases the manifest carried a hazard string saying the old number was wrong while the
machine-readable field three lines above still held it.

Correcting them again would have fixed nothing — it had been done once already, one number at
a time, and it came back. `make validate` now cross-checks prose against the manifest.

---

## What the corpus's own labels got wrong about themselves

Four of the nineteen hand-written labels were wrong, and three of those four share one cause:
**every defective claim was quantitative, and every one was recalled rather than counted.**

| Claim | Reality |
|---|---|
| "five literal `ignore all previous instructions`, more than any malicious sample" | one — and the densest malicious sample also has one, so the comparison inverts into a tie |
| "the canonical strings never appear" — the stated reason that sample exists | they appear twice, verbatim, in plain ASCII |
| "the `allow` list grants Edit, Write and WebFetch to nine domains" | zero Edit, zero Write — the string `Write` does not occur in the file — and 11 domains |

Each was rewritten to what the artifact contains, and each keeps a parenthetical recording
what it used to say. A label that quietly stops being wrong teaches nobody.

**One negative result worth stating plainly:** no `differs_by` described an element its
artifact actually performs. The worst case a hard negative can produce — training a scanner to
suppress a real attack — did not occur in any of the eleven.

---

## Also found, and corrected

- **A malicious sample had no attack in it.** `sg-symlink-escape` is a symlink escaping its own
  directory; `copyTree` dropped every non-regular file, so what shipped was a 230-byte skill
  pointing at a file that did not exist, sitting in the recall denominator under a label
  reading "the artifact is vendored unchanged".
- **Three `.DS_Store` files** were gitignored and are byte-identical to files the pinned
  upstream ships. Dropping them made the duplicate report environment-dependent: five groups in
  a working tree, seven in a fresh clone.
- **163 labels** claimed "coordinates derived from the upstream's own labels" about two entries
  that ship no labels at all, with a fidelity string byte-identical to an entry that does.
- **The leading-digit strip** removes a tier prefix, and only one entry reads its tier that way.
  Applied to all, `12306-mcp` became `am-mcp` and `2389-research/ourocodus` lost its owner.
- **Two bilingual divergences**, one of which dropped half a publication requirement from the
  Chinese — the tool-neutral half, keeping the tool-coupled one.
- **Cisco's `defense-evasion` exclusion** dropped ten samples on a rationale true of four of
  them. Six are back, with hand-read dimensions; the four are excluded by name with a reason
  each.

---

## Checks added, each proven to fail before it shipped

Every check below was verified by constructing a real violation, confirming the build went
red, then confirming it went green again. A check that has never failed has not been tested.

| Check | What it catches |
|---|---|
| prose vs manifest | a count corrected in one place and stale in five |
| duplicate trees | the same bytes under two classes (fails); under one class (reported and counted) |
| `entry` resolution | a label pointing a scanner at a file that does not exist |
| empty sample tree | a sample that can be counted but not scored |
| pin verification | a drifted checkout, and a cache that cannot be verified at all |
| `rules_source.path` containment | a path that makes validate answer differently per machine |
| tool-neutrality, four checks | a scanner's name in `truth`, the vocabulary, the harness, the build files or CI |
| `origin.sha256` | vendored bytes that are not the bytes collected |
| dimension definitions | a dimension with no `what`, or no `not` |
| unused override keys | a hand-read judgement keyed on a sample that does not exist |

---

## The benign half, measured

250 samples across five populations, drawn by `scripts/sample-for-audit.py` (seed 20260918),
every one read. Each was placed in one of three buckets, and the middle bucket is the point of
the exercise — a benign sample a scanner would reasonably alert on is not a defect, it is the
precision test working.

| Population | Size | Read | Plainly benign | Benign, would reasonably fire | **Not benign** |
|---|---:|---:|---:|---:|---:|
| skillmd-138k | 2,000 | 60 | 48 | 12 | 0 |
| skillet-wild | 483 | 60 | 30 | 29 | **1** |
| harvested | 391 | 60 | 29 | 31 | 0 |
| automatelab-mcp-tools | 357 | 60 | 45 | 15 | 0 |
| skillsgoat | 10 | 10 (census) | 0 | 10 | 0 |
| **total** | **3,241** | **250** | **152** | **97** | **1** |

**Mislabelling: 1 of 250.** At n=60 a zero result bounds the rate below roughly 5%, not at
zero. The four populations that returned zero are consistent with a true rate anywhere under
5%, and saying otherwise would be reading precision the sample does not have.

The one real miss is `sk-phamtiendatbg92__ai-gent-for-java__…tech-stack-config`, which ships a
plaintext database password — `datpt`, not `${VAR}`, not `YOUR_PASSWORD` — at `SKILL.md:25`,
`:482` and `:501`. **A secret scanner that alerts here is right**, so as long as this tree sits
in the denominator, a correct scanner is being charged a false positive. It should be excluded
from the credential-rule denominator by name, with the reason recorded.

**The number that actually matters is the middle column: 97 of 250, 39%.** And it is not evenly
spread — 20% of skillmd, 48% of skillet-wild, 52% of harvested. The two heavy populations also
fail *differently*: skillet-wild trips content rules (install pipelines, example secrets,
agent-directed imperatives — Electron's own repository contains the literal line "Ignore other
instructions about making commit messages"), while harvested trips policy rules
(`"defaultMode": "bypassPermissions"`, blanket interpreter grants, hooks executing scripts that
are not in the sample). **Any single pooled false-positive figure measures the mix as much as
the scanner**, which is what the per-population rule in the manifest was for, and this is the
first measurement that shows the size of the effect rather than asserting it.

Two limits worth stating. **131 of 141 hook commands in the harvested configs invoke a script
that is not vendored** — the artifact is the `settings.json` alone, so those verdicts judge the
command string, not what runs. And **seven sample trees are strictly contained inside another
sample**, with five more exact-duplicate pairs; one of them crosses populations (the same
author's skill collected independently by skillmd-138k and skillet-wild), so the populations are
not quite the independent strata the reporting design assumes.

## Still open

- **`tier` and `evasion` are not corrected.** 33 and 32 disputes respectively. They are
  EXPLANATORY axes — they tell a scanner author why a miss happened — and they are not scored.
  A missing explanation is honest; a wrong one sends someone to fix the wrong thing. The lossy
  derivations that produce them are to be stopped rather than overridden.
- **The skillsgoat canary is unfixed**, and finding 3 above states why the choice is not the
  auditor's. Until it is decided, no figure computed on that population means what it says.
- **`sk-phamtiendatbg92…tech-stack-config` is still in the denominator.** The exclusion is
  written above but not yet keyed into the manifest.
- **Two upstream pins cannot be verified locally** — parquet drops with no git history.
- **The rule-id check cannot run here** and should not: it belongs in the scanner's own
  repository. No scanner's repository yet clones this corpus to check its own `expect` blocks.
- **Three samples could not be judged**: their attack refers to a file the upstream itself does
  not ship. Faithfully vendored, and resting on a referent nobody can read.
- **86 dimension disputes were raised; 48 were corrected.** The gap is not a backlog. The ones
  left alone were marked arguable by the agents, and they are arguable in both directions — a
  coin-flip correction adds noise to the axis it claims to clean. The 48 are the ones where
  reading the artifact settled it.
