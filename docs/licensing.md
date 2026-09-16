> English · [中文](licensing.zh-CN.md)

# Licensing

Two questions, and conflating them is the common error:

1. **May we redistribute it?** — governs layer 1 (`corpus/`), which is vendored.
2. **May we measure against it and publish aggregate numbers?** — governs layer 2
   (`manifest/`), which is not.

**The answer to 2 is yes for everything here.** Running a tool locally over material you
lawfully obtained, and publishing counts and rates, is not distribution and not a derivative
work. That is why layer 2 exists and why it is only URLs and hashes.

| Class | Corpora | Vendor into layer 1 | Layer 2 |
|---|---|---|---|
| **No license** | trailofbits, snyk-labs, MalSkillBench, MCPTox, zast-ai | ❌ **zero grant** | ✅ |
| **NC / SA** | SkillTrustBench (CC-BY-NC-SA), obaydata (NC), awesome-claude-code (NC-ND) | ❌ ShareAlike contagion, NonCommercial bar | ✅ |
| **Copyleft** | OWASP Benchmark (GPL), TruffleHog (AGPL), thedotmack (AGPL) | ❌ copyleft terms would reach the corpus itself | ✅ |
| **Proprietary** | `anthropics/skills` — per-skill LICENSE.txt: All rights reserved, forbids Reproduce and Distribute | ❌ **hard red line** | ✅ |
| **Permissive** | DataDog, SkillMD-138K, clawhub-security-signals, skillsgoat, skillcraft-audit, guarddog, package-analysis, NVIDIA, cisco, automatelab, vendor repos | ✅ | ✅ |

**No-license is stricter than NC/SA for redistribution** — zero grant versus a conditional
one — **but identical for measurement.** Both sit in layer 2.

## Why this corpus is its own repository

Layer 1 mixes MIT material we wrote with permissively licensed third-party samples, so it
carries Apache-2.0 and CC-BY-4.0 obligations. A scanner that vendors this corpus into its own
tree inherits those obligations for its whole repository, which is a cost no scanner should
have to pay to be benchmarked.

Keeping the corpus separate means a scanner depends on it the way it depends on any test
fixture: by reference, at a pinned commit, with its own license intact. That matters more
once several scanners are measured here, because they will not share a license.

The same reasoning is why no AGPL or NonCommercial corpus may enter layer 1 at any size.
Copyleft reaches the repository that vendors it, and this repository is meant to be vendorable
by anyone.

## Attribution

Every vendored sample records `origin.license` and `origin.source` in its label, and appears
in `NOTICE`. Attribution is a condition of Apache-2.0 and CC-BY-4.0, so this is a license
obligation, not bookkeeping.

**The label-to-`NOTICE` cross-check is not implemented yet.** `make validate` checks that
`origin.license` is one of the licenses layer 1 permits; it does not read `NOTICE`. Until
that lands, keeping the two in step is manual, and it is recorded here and in `NOTICE`
rather than claimed as automatic.

## One thing this does not cover

Malicious samples are real attack payloads. Redistribution is lawful under the licenses
above, but it is still malware in a public repository.

Layer 1 mitigates in three ways: minimal reconstructions rather than original payloads where
a reconstruction suffices; no live network destinations in any sample we write (RFC-2606
reserved names only, and see the shortcut-feature hazard in `design.md` before relying on
that as a label); and every executable-shaped sample carries a label marking it.

We do **not** ship the neutering that DataDog applies — their samples are zip-encrypted with
the password `infected`, which is why they stay in layer 2 rather than being unpacked into
layer 1.
