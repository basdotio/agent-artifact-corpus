# Statutory provision evidence and fresh-draft verification

Apply this to Acts, the Constitution and subsidiary legislation. The two directions
are the same as for judgments: research retrieves the precise operative provision
before citing it; cite-checking starts with the provision actually cited in the draft
and tests that provision against the proposition or quotation.

This workflow accepts reviewed text from sources other than SSO. When SSO is
unavailable, follow [statutory-source fallbacks](statute-source-fallbacks.md) for
independent official publications, authorised databases and version-labelled copies.
Obtaining text does not establish that it governs the relevant date; unresolved
version findings must remain visible.

## Identify the instrument before checking its section

For every fresh document, identify each statutory citation from its full title,
year, historical chapter/edition where relevant, and any abbreviation defined in
that draft. Resolve short forms within this document; do not reuse another matter's
abbreviation mappings. Verify that the source is the intended Act, Constitution,
regulation, rule or order. A similarly named statute, a predecessor Act, a different
year's re-enactment, an amending Act and the principal Act are distinct instruments.
An Act and regulations under it are not interchangeable just because a provision
number matches. Check the actual citation provision and official identifier.

Then establish the date governing the proposition from the events and issues in
the draft. **Do not automatically select today's law.** Retrieve the corresponding
SSO/Gazette version, check the particular provision's commencement and operative
status, amendments, savings and transitional provisions, and any renumbering or
re-enactment. Follow [statutes and revised editions](statutes-revised-editions.md).
The revised-edition year is not a current-through date or proof of commencement.

Create a fresh run for a fresh or materially revised document. Existing downloads
can be consulted, but their prior identity/version findings are not automatically
verified for this draft. Record the checks actually repeated and unresolved access
gaps. Do not stamp a cached document as current because its title looks right.

## Capture the exact unit and its context

Retain the complete cited section/subsection/paragraph with its source offsets,
version and official numbering, including for a paraphrase. For `s 9A(2)(b)`, also
retain the full enclosing `s 9A(2)` and `s 9A` as context so the lead-in, qualifications
and sibling exceptions can be read. Retrieve relevant definitions, schedules and
cross-referenced provisions separately. Parent context does not authorise quoting
an uncited sibling as if it came from the cited leaf provision.
The same rule applies to a parent's lead-in words: a quotation from the opening of
`s 9A(2)` needs that parent as a cited evidence unit, rather than only `s 9A(2)(b)`.

For an SSO provision view saved as HTML, convert it with the bundled command first:

```sh
python skills/singapore-legal-research/scripts/research.py extract-sso provision.html --out provision.txt
```

It writes the text of the page's provision container only, with split labels rejoined
(`(a)`, `146.—(1)`) and navigation, version list and footer removed. Its JSON report
gives the Act title, the page's version status line, the sections found, and the Act's
amendment list ("Amended by Act … of …", Act-wide rather than provision-specific). Use
the status line as the snapshot `--version`, review the amendment list in
`version_review`, and pass the reported transformation to `snapshot`. It works on raw
and browser-rendered pages, never fetches, and never overwrites a file.
The content container is parsed by its `id`, independently of attribute order or
quoting. Extraction ends at its matching closing tag, even with no page footer;
following sibling text is excluded. Duplicate, unbalanced or unclosed containers
are refused. If a raw fragment is incomplete or relies on omitted closing tags,
save a complete browser-rendered page rather than relaxing the boundary check.

The helper uses a **reviewed provision map**, not a universal statutory-layout parser.
Obtain the hierarchy and complete boundaries from the actual source or a documented
structural extraction, then map locators to zero-based Python string offsets in the
saved UTF-8 text. Never substitute PDF viewer coordinates or a search-result snippet.
The span begins with the unit's real label, e.g. `9A.` or `(b)`. Preserve the complete
unit through its actual end. The checker rejects a mapped end that leaves continuation
text before the next unit boundary. Valid boundaries are: a following mapped unit; an
unmapped line-start section/rule/paragraph number or Order/Schedule/Part heading, or
the next unit's heading line immediately before that number; an unmapped child label
only when it is the unit's own or an ancestor's next sibling (`(b)`→`(c)` or inserted
`(ba)`, `(2)`→`(3)` or `(2A)`, `(iv)`→`(v)`); the parent's declared trailing text; or
end of source. Line-only amendment notes such as `[23/2018]` are skipped. This catches
mid-word, mid-sentence and wrapped-line cutoffs, and a unit cut before its own unmapped
sub-units, without requiring a full stop; valid semicolons, colons and quoted endings
are preserved. It also rejects an older saved index cropped in the same way. A parent
cannot end before its mapped child. Text alone cannot distinguish a roman `(i)` sub-limb
from the letter that follows `(h)`, so check that case against the source. Unsupported
layouts need a source-structured extraction rather than a guessed boundary.

When a parent has trailing words after its last child, such as closing words, a proviso,
an Explanation or Illustrations, set `tail_start` on the parent to the offset where that
line begins. Its last child then ends there, and every mapped child must end before it.
Do not stretch a child over the parent's closing words: a quotation from them must cite
the parent itself. `tail_start` cannot point at a child label or mid-line.

Review notes, amendments, tables and trailing material against the original. A source
file already truncated at its own end, a lost label, or a misleading number inside
quoted text cannot be certified complete from flattened text alone. Keep the original
file and document the extraction; these checks do not establish source authenticity.

The map has a non-empty `provisions` array. Each entry contains:

```json
{
  "locator": "s 9A(2)(b)",
  "start": 100,
  "end": 180,
  "status": "in-force",
  "status_note": "Record the actual provision-level commencement and operative-status check."
}
```

Those offsets are illustrative, not usable source evidence. Include every ancestor
unit in the same map, each with its own full span. The helper computes parent paths,
checks the source label, enforces containment, and rejects overlapping unrelated
units. Statuses are `in-force`, `partly-in-force`, `not-in-force`, `repealed` and
`uncertain`. A status note is required for each unit; do not rely solely on the Act's
original commencement date. Non-operative/uncertain units remain visible limitations.
If a cited unit is `repealed` or `not-in-force`, a `supported` claim must include
`date_basis` on that evidence reference explaining historical comparison, relevant
events or saved application. Without that explanation, qualify the claim or record
it as unsupported/unresolved as appropriate; the checker rejects an unqualified
`supported` claim. A non-empty explanation records review, not proof of applicability.

The map rejects a span that contains only its label/delimiter without provision text,
and a mapped target whose source label was lost. A label on its own line followed by
the actual provision text is valid here: the explicit span and parent mapping define
its boundary. Do not apply the judgment indexer's consecutive-numbering rule to
statutes: inserted lettered sections, repeals and historical numbering can leave
legitimate gaps. An omitted unit or lost label absent from both the extract and map
cannot be recovered by this validation; verify the map against the original structure.

Supported locator forms include `s 9A(2)(b)`, `reg 4(1)`, `r 12(3)`, `art 4`,
`O 9 r 1(2)`, and `First Schedule para 2(1)(a)`; single-unit long forms such as
`section 9A(2)` are accepted. Unsupported layouts or locator syntax require manual
review and a disclosed limitation, not invented labels. Split multi-section/range
citations into individual provision findings; do not silently truncate a range.
Definition-specific locators such as `s 2(1) definition of "x"` are not supported.
Cite and capture the whole subsection and identify the definition in the analysis,
or record a manual-verification limitation without inventing a parsed locator.

## Verify identity and version for this run and draft

The map also includes `statute_verification`:

```json
{
  "run_id": "copy the current run_id from run.json",
  "draft_sha256": null,
  "instrument_title": "Synthetic Act 2000",
  "instrument_citation": "SYNTHETIC-ACT-1",
  "instrument_kind": "act",
  "source_version": "copy the actual source version from run.json",
  "law_as_at": "2026-10-20",
  "checked_on": "2026-10-20",
  "identity_note": "Explain the title, year, identifier and instrument-type comparison.",
  "version_note": "Explain why this selected version governs the relevant events.",
  "commencement_note": "Explain provision-level commencement, amendments, savings and transition checks."
}
```

This is a synthetic template. Use the actual title and identifier from the source,
and match `source_version` to its actual recorded version; changing a version label
without a corresponding fresh verification record fails the check. Use
actual dates, and factual check notes. `instrument_kind` is `act`,
`subsidiary-legislation`, `constitution` or `other-written-law`. For a Word draft,
`draft_sha256` must equal the current run's `draft.sha256`; null applies only when no
draft snapshot is attached. `run_id` and `checked_on` must match the current run and
research date. A stale receipt or another draft's hash fails; attaching a draft after
verification requires rechecking and a receipt tied to that snapshot. These bindings
record the review, not proof that a reviewer actually performed it.

```sh
python skills/singapore-legal-research/scripts/research.py index-provisions runs/matter --source L1 --map provision-map.json --confirm-boundaries --review-note "Checked complete provision boundaries and hierarchy against the selected official version"
python skills/singapore-legal-research/scripts/research.py provision runs/matter --source L1 --locator "s 9A(2)(b)"
```

The `provision` command returns an evidence object with the selected full `passages`,
separate ancestor `context`, exact locator, and verified source date. Add it to the
claim and complete `support_note` and `pinpoint_reviewed` after legal review. The
command leaves that review flag false. The reference's `law_as_at` must match its
source receipt; when it differs from the run's default date, add `date_basis` explaining
the relevant event date or the historical comparison. Keep different versions under
different source IDs, each with its own snapshot, map and fresh receipt.

## Cite-check the original statute, version and provision

Preserve the literal draft citation in `citation_check`, as with case citations.
In addition to `source_id`, `citation`, `pinpoint`, `result` and `reason`, record:

- `resolved_instrument`: the actual source title after resolving the draft's name or abbreviation.
- `instrument_result`: `matched`, `wrong-instrument`, `ambiguous` or `unverifiable`, plus `instrument_note`.
- `version_result`: `matched`, `wrong-version` or `unverifiable`, plus `version_note`.
- `applicable_on`: the date governing this proposition, plus `date_basis` explaining it.

A supported finding requires matched instrument and version, the source verified for
that applicable date, and the exact cited provision in the evidence. Retain the
original wrong section or historical version as comparison evidence; capture any
proposed correction separately. Use distinct `wrong-instrument`, `wrong-version`,
`wrong-pinpoint`, `unsupported`, `missing-pinpoint` and `unverifiable` findings. A
defective or unverified citation cannot be marked supported. If the original source
cannot be identified or retrieved, use an unresolved finding with the exact citation
and obstacle; never manufacture a map or receipt merely to pass the checker.

For shorthand such as the second provision in `ss 9A and 9B`, retain the literal
locator fragment as `pinpoint`, provide `resolved_pinpoint` such as `s 9B`, and add
`pinpoint_resolution_note` explaining its antecedent and unit. Each cited provision
still needs its own finding. Do not confuse a change in numbering with a change in law.

The checker verifies the source spans, hierarchy, receipt bindings, dates and declared
review fields. The agent must still assess whether the operative wording supports
the draft's proposition, read definitions/exceptions, and verify the publication and
version metadata against official material. It does not infer statutory meaning or
commencement from the text offsets, nor certify the authenticity of a supplied file.
