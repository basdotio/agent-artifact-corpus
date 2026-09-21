> English · [中文](articles.zh-CN.md)

# Articles

Two short pieces for a blog or a release announcement. The first is for people who ship a
scanner; the second is for the security audience who does not. Every figure in them was read
from `make stats`, `make validate` or a recorded run — none is an estimate.

---

## Measure your scanner in three commands

*For anyone shipping a static scanner for AI agent environments.*

You need nothing from us. No account, no registration, no entry anywhere in our repository.
Clone the corpus, run three commands, and read a scorecard for your own tool.

`corpus samples` emits a work list, one JSON line per sample, with the path to point your
scanner at. Your runner turns each into `{"sample": id, "verdict": "malicious"|"benign"}`.
`corpus score` grades it. Only the middle piece is yours to write, and it is the only part that
needs to know anything about your tool.

What comes back is not one percentage. Recall is reported per dimension and per source, each
with an interval and its `n`, because a scanner that catches 71% of one source's samples and
11% of another's does not have an average worth printing. False positives are reported per
benign population. Nineteen hard negatives — benign artifacts wearing an attack's shape — are
counted separately, because each one you flag is a false positive you can go read.

A group too small for a tight interval prints as a count, not a rate. Reconstructed samples
print as coverage and never merge with collected ones.

MIT, 3,539 samples: **github.com/basdotio/agent-artifact-corpus**. Tell us where it is wrong.

---

## A benchmark that is hard to fool yourself with

*For security practitioners and researchers.*

AI agents auto-load skills, MCP servers, hooks and permission files, each handed real tools and
real credentials. Scanners for that surface are shipping now. What they are mostly measured
against is each vendor's own fixtures — which contain, by construction, only the attack shapes
their authors already thought of.

This corpus is built the other way round. The benign half is harvested: 3,220 real
configurations from 2,016 public repositories, collected rather than written, because a benign
sample authored by someone who knows the rules unconsciously avoids the shapes that fire. Each
of the 300 malicious samples carries a quote located in its own bytes, so a disputed label can
be checked rather than argued.

Here is what that buys. A run against one real scanner showed `env | curl` completed no
exfiltration chain at all — the whole environment could leave unflagged. After the fix,
exfiltration recall moved from 19 of 44 to 24 of 44, while the false-positive count on all four
benign populations stayed identical. Finding a miss is easy; proving the fix cost nothing is
what needs per-source denominators.

It also refuses to claim things. Several surfaces report coverage rather than a rate, because
no public dataset yet holds real-world samples for them. A benchmark that hides its limits is
worse than a small one.

MIT: **github.com/basdotio/agent-artifact-corpus**. Adversarial readings welcome.
