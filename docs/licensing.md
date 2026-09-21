> English · [中文](licensing.zh-CN.md)

# Licensing

Two questions, and conflating them is the common error:

1. **May we redistribute it?** — governs layer 1 (`corpus/`), which is vendored.
2. **May we measure against it and publish aggregate numbers?** — governs layer 2
   (`manifest/`), which is not.

**The answer to 2 is yes for everything here.** Running a tool locally over material you
lawfully obtained, and publishing counts and rates, is not distribution and not a derivative
work. That is why layer 2 exists and why it is only URLs and hashes.

### That answer rests on the word "locally", and some scanners are not

Added 2026-09-21, after the reasoning above was misread — by the author of the misreading.

Not every scanner is a local program. A growing number are CLI front ends to a hosted service:
the binary runs on your machine, the detection runs on theirs, and the artifact's text goes over
the wire. Point one of those at material here and the sentence above stops applying, because
"running a tool locally" was doing the work in it. Handing a file to a third party's service is
at minimum a transmission, and for material under no licence it is the question 1 nobody asked.

**Where this does and does not bite, precisely:**

| | What it holds | A cloud-backed scanner |
|---|---|---|
| **Layer 1** — `corpus/`, the 3,539 labelled samples | Permissive licences only, and `make validate` rejects any label whose `origin.license` is outside that set. This repository is public. | **Fine.** Anything you could hand a vendor, they could clone. |
| **Layer 2** — `cache/`, fetched on demand per `manifest/` | The no-licence and NonCommercial corpora, by design: they are referenced precisely because they may not be vendored. Currently ~874 MB once fetched. | **Not fine.** Zero-grant material to a commercial service is redistribution, not measurement. |

So the rule has a shape worth stating plainly: **a cloud-backed scanner may be measured on
layer 1 and must not be pointed at `cache/`.** Its figures then rest on a different denominator
than a local tool's, and the citation rules below already require saying so — an exclusion
appears in the conclusion with both numbers.

**The mistake that produced this section** is recorded because it is the instructive part. A
reader took the `vendorable: false` flags in `manifest/corpora.yaml` to be a list of
non-redistributable samples sitting in the corpus, and concluded that nine sources had to be
withheld from a commercial scanner. They are nothing of the kind: those flags describe whether an
UPSTREAM corpus could be vendored, and the samples in layer 1 that trace back to them are our own
permissively licensed reconstructions. Three of them are MIT files we wrote from a paper's
description. The two questions at the top of this page were conflated exactly as the first
sentence warns, by someone who had read that sentence.

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
