# Catalogue of public corpora

Every public dataset of agent artifacts we have found, with what it is good for and what it
will do to your numbers if you use it wrong.

**Read this before picking.** Two of these corpora produce a near-perfect score from a
one-line regex, four may never be redistributed, and several overlap so heavily that adding
their counts together gives a number that is wrong in the flattering direction. Those facts
are per-corpus and recorded below; there is no way to infer them from the data.

Machine-readable form of the pinned half: [`../manifest/corpora.yaml`](../manifest/corpora.yaml).
Fetch with `make fetch E="<id> <id>"`. Sampling discipline: [`design.md`](design.md).
Licence rules: [`licensing.md`](licensing.md).

---

## Pick by the question you are answering

Do not pick by size. Pick by question, then check the hazards.

| Your question | Use | Never use |
|---|---|---|
| **What is the false positive rate?** | `skillmd-138k` as the headline; `awesome-link-targets` when you need full trees with scripts | Anything labelled benign because a scanner stayed quiet. For a scanner that derives its rules from OWASP Agentic Top 10, `clawhub-security-signals` is circular |
| **What is the recall?** | `datadog-ai-skills` (in-the-wild, deduplicated) plus `skillsgoat` (blind probe) | A pooled figure across overlapping corpora. Report per dimension, not aggregate |
| **Does it catch evasion, or just topics?** | `trailofbits-overt` (4 samples, 4 different mechanisms), `nvidia-skillspector-fixtures` (paired twins) | Size-based corpora. This question is answered by structure, not by n |
| **Does it over-alert on security content?** | `fevzi-injection-corpus`, `guarddog-benign`, `mcp-guardbench`, `skillsgoat`'s 10 decoys | — |
| **Hooks, permissions, MCP config?** | `skillcraft-audit` (hooks, permission bypass), `cisco-mcp-scanner-evals` (MCP) — malicious side only | Cisco's 4 benign samples as an MCP false-positive denominator |
| **Tool-description poisoning?** | `automatelab-mcp-tools` (9,922 real tool descriptions) as the benign side | — |
| **Defensive prose misjudged as attack?** | `skilltrustbench`'s `injected_d8` subset — the only public labelling of this anywhere | Over-refusal benchmarks (OR-Bench, XSTest, FalseReject). They measure *model* over-refusal, not *scanner* over-alerting, and they are prompt strings, not artifacts |

---

## Four rules that override any selection

**1. These counts do not add up.** The corpora contain each other:

```
MaliciousSkillBench ⊃ SkillTrustBench + MalSkillBench + ATR + SkillFortifyBench + …
SkillTrustBench     ⊃ overtly-malicious-skills (4)
DataDog ai-skills   ⊃ overtly-malicious-skills (tjade273-* is simple-formatter)
snyk-labs           ∩ pyxeroai = both from NET_NiNjA
```

Each manifest entry declares `overlaps:`. Summing across an overlap inflates your
denominator and flatters the result.

**2. Four corpora may never be redistributed.** `trailofbits-overt` and `malskillbench` have
**no licence at all** — zero grant, which is stricter than NonCommercial, not looser.
`skilltrustbench` is CC-BY-NC-SA, whose ShareAlike clause is contagious. `anthropics/skills`
is proprietary: the per-skill `LICENSE.txt` forbids reproduction and distribution.

All four may still be **measured against locally**, and aggregate figures published. Running
a tool over material you lawfully obtained is not distribution. That distinction is the
whole reason this repository references by URL and hash instead of vendoring.

**3. Two corpora are booby-trapped.** Both yield excellent scores for a reason that has
nothing to do with detection:

- **`malskillbench`**: `_meta.json` is present in 3,878 of 4,000 benign samples and 0 of
  3,944 malicious ones. **The classes separate at 97% purity without reading a single
  skill.** Delete that file before any measurement.
- **`skillfortifybench`**: malicious samples use RFC-2606 reserved domains and benign ones
  never do. One regex scores perfectly and generalises to nothing.

Neither is obviously wrong when you read individual samples, which is why this belongs in a
build gate rather than a review checklist. A human reading samples one at a time cannot see
a distribution. Its successor ships the mechanism worth copying: `metrics/leakage.py` fails
the build when any structural feature with support ≥8 predicts the label at ≥95% purity.

**4. "No scanner complained" is not evidence of benignity.** Ranked strongest to weakest:
cryptographic attestation (only `NVIDIA/skills`) → enterprise permissive publication under
its own namespace → official marketplace inclusion → marketplace "not suspicious" flag plus
download count → **a clean scanner result, which is circular and usable at no weight**.
Smithery `verified`, Glama `qualityScore` (a paid placement) and reputation scores are all
popularity or vendor curation, none of them a security review.

---

## Pinned and fetchable (13)

Each is pinned to a commit in the manifest and fetched with
`make fetch E="<id>"`.

### Recall — malicious samples

**`datadog-ai-skills`** — the primary recall corpus.
`https://github.com/DataDog/malicious-software-packages-dataset` @ `d156188d1e45`,
subset `samples/ai-skills`, **Apache-2.0**, vendorable.
204 malicious, 0 benign. The only in-the-wild, manually triaged, cleanly licensed skill set
that exists.
*Hazards*: 81 of 204 (40%) carry one vendor's name and about 40 are near-duplicates;
roughly 26 (13%) are other scanners' synthetic tests rather than in-the-wild samples;
archives are zip-encrypted with the password `infected`. Overlaps `trailofbits-overt`.
*Required prep*: **deduplicate by author and by canonical tree hash before counting**, or
recall measures whether one template was caught.

**`skillsgoat`** — capability probe.
`https://github.com/optimuslabs-io/skillsgoat` @ `c03d70d80c32`, **MIT**, vendorable.
101 malicious, 10 benign. Blind by design: answers are held outside the sample tree, and an
error counts as a miss. Layout is `pasture/<category>/<id>/{expected.yaml, skill/}` across
31 categories, with a `taxonomy.yaml` mapping categories to OWASP Agentic Top 10 and to
SkillSpector's P-codes. Each sample carries `verdict`, `severity`, `inert: true` and a
**canary string**.
*Hazards*: the 10 benign entries are deliberate false-positive decoys — firing on them is
the failure, not the fix.
*Note*: its label file sits **beside** the skill directory, not inside it. This is the
correct layout and this repository arrived at it independently after the inside-the-tree
version corrupted its own measurements.

**`skillcraft-audit`** — hooks and permissions.
`https://github.com/Clay-HHK/skillcraft-audit` @ `0b9c36f28e05`, **MIT**, vendorable.
150 malicious, 0 benign. **The only public corpus covering hook weaponisation and permission
bypass at all.**
*Hazards*: single author, so shapes are stylistically correlated; and being the only source,
there is no second opinion to check it against.

**`cisco-mcp-scanner-evals`** — the MCP surface.
`https://github.com/cisco-ai-defense/mcp-scanner` @ `be87b90d88bc`, subset `evals`,
**Apache-2.0**, vendorable. 154 malicious, 4 benign.
*Hazards*: 4 benign samples is far too few to serve as an MCP false-positive denominator;
the directory name is the label, so a path-aware harness can cheat.

**`trailofbits-overt`** — the evasion touchstone.
`https://github.com/trailofbits/overtly-malicious-skills` @ `4ffbf9461ef0`,
**no licence**, **never vendor**. 4 malicious.
Four samples, four different mechanisms for defeating line-by-line rules. Small enough to
run in seconds and sharp enough that passing it is a real statement.
*Hazards*: zero grant; also contained in `datadog-ai-skills` and `skilltrustbench`, so never
count it alongside either.

**`skilltrustbench`** — best structure, worst licence.
`https://huggingface.co/datasets/cuhk-zhuque/SkillTrustBench` @ `f90517b7058f`,
**CC-BY-NC-SA-4.0**, **never vendor**. 3,877 malicious, 1,643 benign.
*Hazards*: NonCommercial plus ShareAlike contagion, so local measurement and aggregate
figures only; contains the four Trail of Bits samples.
*Unique value*: the **`injected_d8` subset** — 119 samples, 118 labelled `normal`, described
by its authors as security tools and test fixtures that should not be labelled malicious by
default. **This is the only public labelling of defensive-prose false positives that exists
anywhere.**

**`malskillbench`** — scale, with a trap.
`https://github.com/lxyeternal/MalSkillBench` @ `06e083125d5e`, **no licence**,
**never vendor**. 3,944 malicious, 4,000 benign.
*Hazards*: **severe label leakage**, see rule 3 above.
*Required prep*: **delete `_meta.json` from every sample before measuring anything.**
(The companion rumour that the malicious directories are empty is false — all 3,944 contain
a `SKILL.md`.)

### False-positive denominator — benign samples

**`skillmd-138k`** — the primary denominator.
`https://huggingface.co/datasets/FayeZC/SkillMD-138K` @ `0d73048abf2f`, **CC-BY-4.0**,
vendorable. 138,133 skills across **20,556 repos** — the widest real-world distribution
available.
*Hazards*: `SKILL.md` body only, no scripts, so every script-surface rule is untested by it;
and the repo count is the real n, so sampling by file over-weights large repos.
*Required prep*: report per repo, cap samples per repo, and publish **both** the
sample-weighted and the source-unweighted rate. Where they disagree, the disagreement is the
result.

**`clawhub-security-signals`** — scale, with a caveat that must travel with it.
`https://huggingface.co/datasets/OpenClaw/clawhub-security-signals` @ `69dcbd323c15`,
**MIT**, vendorable. 41,743 clean.
*Hazards*: **partly circular** — its labels derive from an OWASP Agentic Top 10 rating, and
that is the taxonomy most agent-artifact scanners derive their rules from. Labels are
silver-standard (model-judged), not human review.
*Required prep*: never use as the headline false-positive figure; report it beside a
non-circular source.

### Hard negatives — benign that looks like an attack

**`automatelab-mcp-tools`** — real tool descriptions.
`https://huggingface.co/datasets/automatelab/mcp-servers-tool-catalog` @ `a413afb7b02a`,
**CC-BY-4.0**, vendorable. **9,922 tools across 359 servers.**
Real descriptions legitimately contain `IMPORTANT:`, `<placeholder>`, tokens and URLs — all
the shapes a tool-poisoning rule looks for.
*Hazards*: none known for the data itself. The hazard is on your side: this is typically a
two-order-of-magnitude expansion over whatever your tool-description rules were validated
against, and may surface many false positives at once.

**`nvidia-skillspector-fixtures`** — paired twins.
`https://github.com/NVIDIA/SkillSpector` @ `2e9ae8d1cfa6`, **Apache-2.0**, vendorable.
About 6 pairs, each a malicious fixture beside a near-identical clean version.
**The only structure that tests whether a hit lands on the difference rather than on the
topic.**
*Hazards*: tiny. Its value is the structure, not the count.

**`guarddog-benign`** — false positives with their history attached.
`https://github.com/DataDog/guarddog` @ `1f4a66c064fb`, **Apache-2.0**, vendorable.
25 benign fixtures, each carrying a comment naming the real false positive it was added to
fix.
*Hazards*: targets Python package rules, not agent skills — the shapes transfer, the surface
does not.

**`fevzi-injection-corpus`** — documentation about injection.
`https://github.com/fevziegeyurtsevenler/prompt-injection-corpus` @ `05fd3571d53a`,
**CC-BY-4.0**, vendorable. 5 markdown files, densely containing literal
`ignore previous instructions`.
*Hazards*: it is documentation *about* injection, so **every injection-rule hit on it is a
false positive by construction**. That is precisely what makes it useful.

---

## Found but not yet pinned (10)

Real and usable; they simply have no manifest entry yet, so there is no pinned commit and no
`make fetch` support. Verify counts and licence before relying on them.

| Corpus | Licence | Size | Why you might want it |
|---|---|---:|---|
| `Agent-Threat-Rule/atr-skill-benchmark` | MIT | 466 | Includes `evasive-stub`, built explicitly for false-positive testing. Subset of MaliciousSkillBench |
| `NVIDIA/skills` | Apache-2.0 | 356 | **The only corpus with cryptographic signatures** (Sigstore, private PKI) |
| `anthropics/claude-plugins-official` | Apache-2.0 | 31 skills / 39 plugins | First-party curation. Check whether your tool already allowlists any of them — then it is not independent |
| `ossf/package-analysis` detections | Apache-2.0 | ~191 | Go, table-driven, same language and style. URL fixtures inline-annotate their authors' own misjudgements, including hex escapes and IDN confusables |
| `protectskills/MaliciousSkillBench` | code Apache-2.0 / data CC-BY-4.0 | 7,505 / 2,235 | Scale — but it **aggregates 13 sources** and overlaps most of this catalogue |
| `shenyimings/skillet` `benchmark/wild/` | MIT | 483 safe | **Repo-disjoint by construction**, and records `label_source` so you can see how each label was produced |
| `mcp-guardbench` `cases/benign/` | MIT | 20 | Deliberate traps: Cyrillic prose, `ignore`-flag documentation, AWS *example* keys |
| Vendor repos (google, adobe, stripe, microsoft, forcedotcom) | Apache-2.0 / MIT | 14–337 each | Enterprises publishing permissively under their own namespace — credible benign, style-homogeneous per vendor |
| `anthropics/.../security-guidance` | Apache-2.0 | 1 | Attack-pattern regexes plus warning prose, **registered as a hook**, so it lands on a real load path |
| awesome-list link targets | 457 of 573 permissive | 1,231 trees / 382 repos | **Full trees with real scripts, human-collected, non-circular** — the best benign source that is not a bare manifest |

The last row is deliberately **not** in the manifest. It is a list of repositories rather
than one repository, so it does not fit the one-url-one-commit shape and needs its own
resolver: read the lists, filter by licence, cap at 5 trees per repo, pin each target.
Recording it with a placeholder URL would have validated, and a validated placeholder is
exactly the failure the manifest exists to prevent.

---

## Hard red line

**`anthropics/skills` is proprietary.** Each skill's `LICENSE.txt` reads All rights reserved
and explicitly forbids reproducing, copying and distributing. It cannot be vendored into any
layer. Measure against it locally if you have it installed; redistribute nothing.

---

## What is missing from the public world

**Benign hooks, benign permission grants, and benign MCP server configurations.** The
malicious side of these surfaces exists (`skillcraft-audit`, `cisco-mcp-scanner-evals`); the
benign side does not, anywhere, because almost nobody scans those surfaces and so nobody has
collected what normal ones look like.

This is the one gap that must be filled by collecting rather than downloading, and it is
also the easiest place in the whole corpus to manufacture a flattering false-positive rate.
The rule this repository applies: **harvest benign hook and permission samples from real
machines only** — your own, colleagues', public dotfiles repositories. Never hand-written. A
hand-written benign hook and a hand-written benign skill are the same mistake, and the
reasoning is in [`design.md`](design.md).
