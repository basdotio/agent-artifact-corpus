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
| **Copyleft** | OWASP Benchmark (GPL), TruffleHog (AGPL), thedotmack (AGPL) | ❌ same discipline that keeps our rules re-derived rather than ported | ✅ |
| **Proprietary** | `anthropics/skills` — per-skill LICENSE.txt: All rights reserved, forbids Reproduce and Distribute | ❌ **hard red line** | ✅ |
| **Permissive** | DataDog, SkillMD-138K, clawhub-security-signals, skillsgoat, skillcraft-audit, guarddog, package-analysis, NVIDIA, cisco, automatelab, vendor repos | ✅ | ✅ |

**No-license is stricter than NC/SA for redistribution** — zero grant versus a conditional
one — **but identical for measurement.** Both sit in layer 2.

## Why the rules are re-derived, not ported

`aguard`'s rules are re-derived from OWASP Agentic Top 10 and MITRE ATLAS rather than ported
from another scanner, deliberately, to avoid copyleft. Vendoring an AGPL corpus into the
same repository would give that discipline away for test data. The corpus repository is
separate from the tool repository for the same reason: layer 1 mixes Apache-2.0 and
CC-BY-4.0 material, and that belongs nowhere near an MIT tool.

## Attribution

Every vendored sample records `origin.license` and `origin.source` in its `_label.yaml`,
and appears in `NOTICE`. `make validate` fails if the two disagree. Attribution is a
condition of Apache-2.0 and CC-BY-4.0, so this is a license obligation, not bookkeeping.

## One thing this does not cover

Malicious samples are real attack payloads. Redistribution is lawful under the licenses
above, but it is still malware in a public repository.

Layer 1 mitigates in three ways: minimal reconstructions rather than original payloads where
a reconstruction suffices; no live network destinations in any sample we write (RFC-2606
reserved names only, and see the shortcut-feature hazard in `design.md` before relying on
that as a label); and every executable-shaped sample carries a `_label.yaml` marking it.

We do **not** ship the neutering that DataDog applies — their samples are zip-encrypted with
the password `infected`, which is why they stay in layer 2 rather than being unpacked into
layer 1.
