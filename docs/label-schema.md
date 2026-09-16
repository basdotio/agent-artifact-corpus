# The label file

One per sample, named `<id>.yaml`, sitting **beside** the sample tree — never inside it.

```
corpus/malicious/skills/revshell-python-dup2.yaml    <- the label
corpus/malicious/skills/revshell-python-dup2/        <- the tree `aguard check` is pointed at
```

**This is load-bearing, not tidiness.** The labels started as `_label.yaml` inside each tree,
and that silently corrupted every measurement: the scanner reads the whole target directory,
so each sample was injecting its own annotation as evidence.

The reverse-shell sample scored 83 with `BD-003` apparently caught — on the words "textbook
reverse shell" in its own `note:` field, while the actual payload went undetected. With the
label moved out it scores 88 and `BD-003` is silent, which is the true result and the one
W-027 records. The `environ-copy` hard negative scored 63 on a high `EXFIL-001` whose two
evidence lines were the label's own `source:` URL and `note:` prose; clean, it scores 88.

The contamination ran both ways: malicious samples looked better caught than they were, and
benign samples looked like false positives they were not. The validator now rejects any
`_label.yaml` found inside a tree.

`make validate` enforces everything below.

```yaml
id: mal-skill-revshell-python        # unique, stable, never reused
class: malicious                     # malicious | benign | hard-negative
surface: skills                      # skills | hooks | permission | mcp | connector | instruction
kind: skill                          # maps to model.ArtifactKind
entry: .                             # what `aguard check` is pointed at

origin:
  type: reconstruction               # real-world | promoted | reconstruction | synthetic
  source: "https://…"                # article or repo url+commit
  license: MIT                       # of the sample itself; must match NOTICE if vendored
  note: "minimal sample rebuilt from the described shape, not the original payload"
  added: 2026-09-16
  labeled_before_run: true           # REQUIRED true — see below

expect:
  rules: [BD-003]                    # must fire
  min_severity: high                 # gate view: sample must reach at least this
  quiet: [PERM-006]                  # must NOT fire
  notes: [COV-000]                   # dimension-0 notes that must be present

known_gap:                           # optional; present = we currently fail this
  item: W-027
  since: 2026-09-16
  observed: "88/100, only EXEC-004 medium; --fail-on high passes it"
```

Benign and hard-negative invert the severity bound:

```yaml
class: hard-negative
expect:
  max_severity: low                  # low/advisory tolerated; above it is a false positive
  quiet: [EXFIL-001, EXEC-001]
pairs_with: mal-skill-exfil-credchain # REQUIRED for hard-negative
```

## Rules the validator enforces

**`labeled_before_run` must be `true`.** Label first, run second. Running first and
labelling after treats the tool's current behaviour as the correct answer, which measures
100% every time and detects nothing forever.

**`hard-negative` requires `pairs_with`**, naming a malicious sample that must still fire.
Without it, "reduce false positives" degrades into "delete the rule" and nothing notices.
The paired sample must exist and must list at least one rule in `expect.rules` that appears
in this sample's `quiet:`.

**`expect.rules` and `expect.quiet` must not intersect.**

**`expect.notes`** carries measurement class 3 by itself. A sample that injects a coverage
gap — an unreadable directory, a FIFO, a symlink out of bounds — asserts here that the tool
announced it. Without this field the corpus cannot express disclosure at all, and disclosure
is the class where this tool has historically failed worst.

**Benign bounds are bounds, not silence.** `max_severity` means "not above this", and
setting it too tight is the common mistake. The `environ-copy` hard negative was first
labelled `max_severity: low` and failed validation, because the sample's whole purpose is to
run `make` in a subprocess and `EXEC-004` at medium is the tool being right. The assertion
that matters there is `quiet: [EXFIL-004]`. Set the bound to what a correct tool would emit,
and let `quiet` carry the real claim.

**Rule IDs must exist.** Checked against the tool's generated `docs/rules.md`, so a renamed
or retired rule turns the corpus red instead of silently never matching. The check reads
**73** IDs; note that two of them, `REP-GOOD` and `REP-BAD`, do not end in digits, so a
`XXX-000`-shaped pattern silently finds only 71 and then rejects labels citing those two.

**`origin.license` must be compatible with layer 1**, and must appear in `NOTICE` when the
sample is vendored from a third party. No-license, NC, SA and copyleft material cannot live
here — it belongs in `manifest/`.

**`out_of_scope`** (string, optional): non-empty means the sample is malicious in a way this
tool states it does not detect — pure runtime behaviour, anything needing a live MCP
connection. It leaves the recall denominator **and is named in the report**. Silently
leaving it in understates recall; silently dropping it overstates it; naming it does
neither.

## `known_gap` and why it is not just a failing test

A sample whose expectation the tool does not currently meet is the most valuable kind, and
the easiest to lose. Without a field for it, adding the reverse-shell sample turns CI red on
commit, and the cheapest way to green is to delete the sample — removing the only evidence
of the defect.

So `known_gap` makes the failure **expected and attributed**: the run reports it as a known
gap against a work item rather than a regression, the number appears in the published report
as an open gap, and **the gap closing also fails the build** — you do not get to fix it
without deleting the field and updating the report in the same change.

A sample carrying `known_gap` counts in the recall denominator. It is a miss, not an
exclusion.
