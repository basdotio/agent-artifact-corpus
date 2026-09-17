> English · [中文](label-schema.zh-CN.md)

# The label file

One per sample, named `<id>.yaml`, sitting **beside** the sample tree, never inside it.

```
corpus/malicious/skills/revshell-python-dup2.yaml    <- the label
corpus/malicious/skills/revshell-python-dup2/        <- the tree a scanner is pointed at
```

**This is load-bearing, not tidiness.** The labels started as `_label.yaml` inside each tree,
and that silently corrupted every measurement: a scanner reads the whole target directory,
so each sample was injecting its own annotation as evidence.

The reverse-shell sample scored 83 with `BD-003` apparently caught — on the words "textbook
reverse shell" in its own `note:` field, while the actual payload went undetected. With the
label moved out it scores 88 and `BD-003` is silent, which is the true result and the one
W-027 records. The `environ-copy` hard negative scored 63 on a high `EXFIL-001` whose two
evidence lines were the label's own `source:` URL and `note:` prose; clean, it scores 88.

The contamination ran both ways: malicious samples looked better caught than they were, and
benign samples looked like false positives they were not. The validator now rejects any
`_label.yaml` found inside a tree.

---

## The two halves

A label has two halves and they belong to different people.

**`truth` says what the sample is.** It is written in technique names from
[`taxonomy/techniques.yaml`](../taxonomy/techniques.yaml), which no scanner owns. It is
enough on its own to score any scanner: a runner asks "did the tool report this sample at or
above `truth.severity`" without knowing a single rule ID.

**`expect.<tool>` says what one named scanner should emit.** It is written in that scanner's
own rule IDs, checked against that scanner's own severity ladder, and it is **optional**. An
absent block means *not measured here*, which is a different statement from *passed*.

Before the split there was only the second half. Every assertion in the corpus was phrased in
one product's vocabulary, `known_gap` recorded one product's shortfall as if it were a
property of the artifact, and the pairing invariant was an overlap between two rule ID lists.
The corpus could not describe a sample to anyone who had not built that product.

**Anyone can benchmark their scanner against this corpus without appearing in
[`taxonomy/tools.yaml`](../taxonomy/tools.yaml).** That file is only needed to carry
rule-level expectations. `truth` is the contract.

---

## The file

```yaml
id: mal-skill-revshell-python-dup2    # unique, stable, never reused
class: malicious                      # malicious | benign | hard-negative
surface: skills                       # one, or a list: [hooks, permission] — see below
kind: skill                           # the artifact kind in the agent ecosystem, not in any scanner
entry: .                              # what the scanner is pointed at

origin:
  type: reconstruction                # real-world | promoted | reconstruction | synthetic
  source: "https://…"                 # article or repo url+commit
  license: MIT                        # of the sample itself; must match NOTICE if vendored
  note: "minimal sample rebuilt from the described shape, not the original payload"
  added: 2026-09-16
  labeled_before_run: true            # REQUIRED true — see below
  sha256: ""                          # optional; if set it IS checked against the bytes

truth:                                # tool-neutral. Nothing here names a scanner.
  techniques: [reverse-shell]         # what it actually does, from taxonomy/techniques.yaml
  severity: high                      # how bad it is, independent of any tool
  tier: plain                         # how deeply it is buried
  evasion: []                         # which mechanisms bury it; empty is what `plain` means
  note: "socket to a reserved host, all three fds duplicated onto it, /bin/sh -i spawned"

expect:                               # optional, per tool, keyed by taxonomy/tools.yaml.
                                      # `aguard` below is one example tool; the rule ids and
                                      # the ladder are its own, not the schema's.
  aguard:
    rules: [BD-003]                   # must fire
    min_severity: high                # gate view: must reach at least this on aguard's ladder
    quiet: [PERM-006]                 # must NOT fire
    notes: [COV-000]                  # dimension-0 notes that must be present
    known_gap:                        # present = this tool currently fails this sample
      item: W-027
      since: 2026-09-16
      observed: "88/100, only EXEC-004 medium; --fail-on high passes it"
```

Benign and hard-negative invert the bound and move the technique to `resembles`:

```yaml
class: hard-negative
truth:
  resembles: [reverse-shell]          # what it LOOKS like
  tier: plain                         # how deep an analysis must go to tell it apart
  differs_by: >-                      # the discrimination test, written out
    No fd redirection and no interpreter spawn. The socket is connected, written to once
    and closed.
expect:
  aguard:
    max_severity: low                 # low/advisory tolerated; above it is a false positive
    quiet: [BD-003, EXFIL-001]
pairs_with: mal-skill-revshell-python-dup2   # REQUIRED for hard-negative
```

---

## `surface` is a list, because one file is two load paths

A real `.claude/settings.json` normally carries both a `hooks` block and a `permissions`
block. Three of the first five real files harvested had both.

With a single surface, such a file has to be filed under one of them, and the consequence is
not cosmetic: the `permission` surface comes to mean *settings files that happen to have no
hooks*, a subpopulation invented by the schema rather than found in the world. Since the whole
point of the surface axis is to say **where** a scanner fails, a category that the schema
fabricated is worse than none.

So `surface` accepts either form:

```yaml
surface: skills                 # the normal case, and it stays a scalar
surface: [hooks, permission]    # one file that really is on both load paths
```

Three consequences worth knowing:

- **The artifact is vendored once.** Copying the tree into two surfaces would put identical
  bytes in two samples and let a scanner be scored twice for one file — the same leakage the
  corpus rejects elsewhere.
- **The first surface owns the directory.** A multi-surface sample lives at
  `corpus/<class>/<first-surface>/<id>/`, and the validator checks the path against it, so
  the location stays predictable.
- **Per-surface counts do not sum to the sample count.** `corpus stats` prints that warning
  beside the table rather than leaving a reader to discover it by subtraction.

## `sha256` is optional, and if you set it, it is checked

Most of the corpus came from upstreams that published no hash. Those labels leave the field
empty, and that is not a failure: computing a hash from our own copy and storing it beside
that copy would prove only that we can hash a file.

When the field IS set — every harvested sample sets it, because the collector saw the
upstream bytes — `make validate` recomputes it from the vendored artifact and fails on a
mismatch. A mismatch means the vendored copy is not the file that was collected, so every
number published against that sample is suspect.

This is deliberately narrower than it could be. The field names the hash of **one** artifact,
so the validator refuses it on a tree holding several files rather than inventing a
concatenation order no reader could guess. And it does not close the same gap for `manifest/`:
a layer-2 entry is a reference with no bytes to hash here, which is why every manifest
`sha256` is still empty and README still says so.

## Rules the validator enforces

### On `truth`

**Malicious needs `techniques` and `severity`.** Without a technique the sample sits on no
recall axis and asserts nothing any scanner but ours could be measured against. Without a
severity there is no tool-neutral statement of how bad it is, so a scanner with no `expect`
block here cannot be scored at all.

**Hard-negative needs `resembles` and `differs_by`.** Resembling an attack is the entire
definition of the class. `differs_by` names the element that is absent, and it is the one
thing the author of another scanner actually needs from the sample: not "we fire `BD-003`
here", but "these two artifacts differ by exactly this".

**A sample cannot both perform and resemble the same technique.** It does one or the other.

**Malicious and hard-negative samples need a `tier`.** Without it every sample is equally
deep, and a miss cannot be attributed to literal matching rather than to a missing rule. The
scale reads differently per class, and both readings run the same direction, which is what
lets a hard negative sit in the grid cell of the attack it imitates:

| Class | `tier` means |
|---|---|
| malicious | how deeply the attack is buried |
| hard-negative | how deep an analysis must go before it can tell this apart |

**A malicious sample past the calibration tier must name its `evasion` mechanisms**, from the
closed vocabulary, and **its tier may not be lower than the deepest tier those mechanisms
imply**. Without that bound a wrapped payload could be labelled `plain`, and `plain` is the
level where a miss is supposed to mean the scanner is broken rather than weak.

**A hard negative carries a tier but no `evasion`.** It is not burying anything. What makes
it hard is already written out in `differs_by`, which the class requires and which is better
prose than any vocabulary term.

**An ordinary benign sample has neither.** The axes measure how deeply an attack is buried,
and there is no attack. A benign sample that resembles one is a hard negative.

**Technique names must exist in `taxonomy/techniques.yaml`**, so a typo turns the corpus red
rather than silently creating a one-member recall axis that reads as full coverage.

### On `expect`

**The tool must be declared in `taxonomy/tools.yaml`.** An undeclared tool's rule IDs and
severity bounds cannot be checked against anything, so they would go unverified forever.

**Severity bounds are checked against that tool's own ladder.** This is what lets two
scanners with different scales annotate the same sample without either adopting the other's.

**Rule IDs must exist**, checked against that tool's generated rule reference, so a renamed
or retired rule turns the corpus red instead of silently never matching. A tool whose
reference is not reachable downgrades to "not checked" and says so — this repository must
validate with no checkout of any scanner present.

**`rules` and `quiet` must not intersect**, or the sample passes whatever the tool does.

**Benign bounds are bounds, not silence.** `max_severity` means "not above this", and setting
it too tight is the common mistake. The `environ-copy` hard negative was first labelled
`max_severity: low` and failed validation, because the sample's whole purpose is to run
`make` in a subprocess and `EXEC-004` at medium is the tool being right. Set the bound to
what a correct tool would emit, and let `quiet` carry the real claim.

**An empty block is rejected; remove the key.** An empty block reads as "measured and clean",
and absence is supposed to mean "not measured".

**`notes`** carries measurement class 3 (disclosure) by itself. A sample that injects a
coverage gap — an unreadable directory, a FIFO, a symlink out of bounds — asserts here that
the tool announced it. It lives inside the per-tool block deliberately: almost no other
scanner has the concept, and hoisting it would state a property of one product as a property
of the artifact.

**`out_of_scope`** (string, optional) means the sample is malicious in a way **this tool**
states it does not detect — pure runtime behaviour, anything needing a live MCP connection.
It leaves that tool's recall denominator **and is named in the report**. Silently leaving it
in understates recall; silently dropping it overstates it; naming it does neither. Also
per-tool: pure runtime behaviour is out of scope for a static scanner and in scope for a
dynamic one.

### Everywhere else

**`labeled_before_run` must be `true`.** Label first, run second. Running first and labelling
after treats the tool's current behaviour as the correct answer, which measures 100% every
time and detects nothing forever. Under the split this is above all a claim about `truth`,
which is the half that must never be derived from a run.

**The directory must agree with the label.** `corpus/<class>/<surface>/` is where a reader
looks first, so a label filed under one class while declaring another is rejected.

**`origin.license` must be compatible with layer 1.** No-license, NC, SA and copyleft
material cannot live here — it belongs in `manifest/`. See [`licensing.md`](licensing.md).

---

## Pairing, and why it now runs through `truth`

**`hard-negative` requires `pairs_with`**, naming a malicious sample that must still be
caught. Without it, "reduce false positives" degrades into "delete the rule" and nothing
notices.

The pair is checked as **the twin performs a technique this sample resembles**. That is a
statement about the two artifacts, so it holds for every scanner.

It used to be checked as an overlap between the two labels' rule ID lists. That version was
weaker in both directions: a pair counted as valid whenever two labels happened to mention
the same regex name, and the invariant could not be expressed at all for a scanner whose rule
IDs we do not know.

### Unguarded pairs

There is a state that passes every structural check while guaranteeing nothing. The hard
negative silences a rule, the twin is supposed to fire it, and the twin carries a
`known_gap` saying that tool currently does not. Delete the rule and **neither sample
breaks**.

One pair is in this state today: `hn-skill-socket-client-plain` silences `BD-003`, and its
twin is on record failing `BD-003` for `aguard` under W-027.

This is not rejected. The twin's `known_gap` is an honest declaration, and rejecting it would
make deleting the sample the cheapest way to green. It is **named and counted** by
`make validate` and `make stats` instead, on the same principle as the tool's own coverage
notes: a declared hole is something an operator can act on, a hidden one is a lie. The count
goes in the published report.

---

## `known_gap` and why it is not just a failing test

A sample whose expectation a tool does not currently meet is the most valuable kind, and the
easiest to lose. Without a field for it, adding the reverse-shell sample turns CI red on
commit, and the cheapest way to green is to delete the sample — removing the only evidence of
the defect.

So `known_gap` makes the failure **expected and attributed**: the run reports it as a known
gap against a work item rather than a regression, the number appears in the published report
as an open gap, and **the gap closing also fails the build** — you do not get to fix it
without deleting the field and updating the report in the same change.

It lives **per tool**, because a shortfall is per tool by definition. One scanner's gap is not
another's, and recording it at the top level stated one product's weakness as a fact about
the artifact.

A sample carrying `known_gap` counts in that tool's recall denominator. It is a miss, not an
exclusion.

---

## Adding a scanner

An entry in [`taxonomy/tools.yaml`](../taxonomy/tools.yaml), not a schema change:

```yaml
  - id: yourscanner
    name: Your Scanner
    url: https://…
    severity_ladder: [error, warning, note]   # most to least severe; last means "nothing"
    rule_id_pattern: '…'                      # how its rule ids are written
    rules_source:
      env: YOURSCANNER_RULES
      # No `path:` here. It is relative to this repository's root and MAY NOT leave it —
      # the validator rejects one that does, because a path pointing at a checkout of your
      # scanner makes `make validate` report different results on different machines.
      # The env var above is how you reach your own checkout.
    native_format: sarif-2.1.0
```

And to score it without adding an entry at all: run it over the sample trees and compare
against `truth`. That path needs nothing from this file.
