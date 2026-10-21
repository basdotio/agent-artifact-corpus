# Research workflows

## Research and deep research

Start with a short issue tree and a source plan. For deep research, keep a matrix of
elements, exceptions, remedies, procedure, competing interpretations, and factual
dependencies relevant to the question. Allocate effort to decisive unresolved issues.
Use secondary literature to locate terminology and competing positions, then follow
their citations to the primary sources. Do not assume a textbook passage captures
amendments or later appellate decisions.

Deliver an answer-first memo with scope and law-as-at date, applicable rules, fact-sensitive
application, adverse authority, alternative arguments, and remaining questions. Link
each material proposition to a precise passage. For each case, retrieve and retain the
full supporting numbered paragraphs even when paraphrasing; give the verified case
citation with `at [n]`, `at [n]–[m]`, or explicit disjoint pinpoints. Keep adjacent
context available and avoid a range that includes unread or unnecessary paragraphs.
For statutory propositions, use [statutory evidence](statutory-evidence.md): identify
the actual instrument, verify the provision effective for the relevant events, and
capture the precise section/subsection with full parent context. A current title or
an Act-wide keyword match does not verify the cited provision or its operative date.
Include a source table with version,
support, treatment search, and access status. Stop when the decisive branches have
been researched and contrary searches performed, or disclose exactly which branch
remains open because of access, time, or missing facts. Never pad with irrelevant cases.

## Find authority

Break the proposition into its legal elements and qualifications. Search directly
relevant Singapore appellate decisions first, then other local cases and legislation.
Check whether the proposed wording overstates the holding. Supply the best authority
or a small number of complementary authorities with pinpoints, links and a one-sentence
explanation of support. Explain why foreign authority is needed if used. If no exact
support is found, say so and propose narrower wording with its actual support.
Keep the complete supporting paragraph(s), not just the sentence that matched a
search query. Use [paragraph evidence](paragraph-evidence.md) to bind those passages
to the pinpoint and source version in a saved run.

## Cite-check

Preserve a snapshot of the draft. For Word, use `research.py extract-docx`; review
body text, tables, footnotes and endnotes, not body text alone. The extractor preserves
OOXML IDs and reference markers, which are not guaranteed displayed note numbers.
Reconcile them with Word before describing a finding as “footnote 12”. Inspect tracked
changes and fields when present; never silently accept or reject changes.

Create an inventory from every extracted location. Within each location separately
list every authority, quotation, cross-reference and unsupported legal proposition;
one paragraph can contain several. The extraction is a structural inventory, not an
automatic legal citation detector. Resolve `ibid`, `id`, `supra`, `above`, and defined
case-name chains to their actual antecedents. Mark ambiguous chains unresolved.

For every cited case, first preserve the original citation verbatim and resolve any
short form. Retrieve its specifically cited paragraph(s) from the version identified;
retain the complete paragraphs, then compare the proposition and any quoted words
side by side with that passage. A full-judgment phrase match is insufficient. Check
whether the passage is judicial reasoning, obiter, submissions, or quoted authority.
If support exists only elsewhere, report the original pinpoint as wrong and capture
the proposed replacement separately. Never silently repair the citation and pass it.
Use `citation_check` to record supported, wrong-pinpoint, unsupported, missing-pinpoint
or unverifiable, with a reason. A missing original pinpoint is a finding; research
for a replacement does not retrospectively verify the original citation.

For every fresh draft, recheck statutory names and abbreviations against the precise
official instrument: title, year, Act versus subsidiary legislation, predecessor or
re-enactment, and original versus amending Act. Establish the applicable date from
the facts rather than defaulting to the newest consolidation. Recheck that specific
provision's version, commencement, savings, amendments and renumbering; capture the
exact unit and its parent context. Save a new `statute_verification` receipt tied to
the current run and draft snapshot, plus separate identity and version findings in
`citation_check`. Do not reuse another draft's receipt. Wrong-instrument, wrong-version
and wrong-pinpoint are distinct findings; keep original and proposed replacement
evidence separate. See [statutory evidence](statutory-evidence.md) for the fields.

For every item, check identity, bibliographic accuracy, source version, pinpoint,
quotation fidelity, proposition support, and treatment as applicable. Include adverse
and missing authority. Prioritise: fabricated/misidentified source; contradicted or
overstated proposition; wrong quote/pinpoint/version; unverified access; editorial style.
Give the exact draft find-string, location, issue, evidence, proposed correction and
status. Never modify the original draft unless asked. A suggested correction is not
a verified replacement until its source is checked.

Use ledger `inventory` to account for all extracted blocks (including deliberate
“no research item” decisions), and `claims` for individual findings. Report counts of
locations reviewed, findings, sources checked, and unresolved items. A manually reviewed
location must carry a reason if no claim is attached. The ledger validator detects
unaccounted locations; it cannot discover an authority the reviewer failed to identify.

## Proofread

Check spelling, punctuation, duplicated words, incomplete sentences, defined-term
consistency, headings, internal numbering and cross-references. Preserve legal effect,
quotations, anonymisation, and deliberate house style. List exact find-strings and
specific corrections. Flag possible substantive problems separately without silently
rewriting them. State that authorities were not substantively checked unless cite-check
was also performed. Do not label a quotation a typo until compared to its source.

## Case preparation

Confirm the exact decision and requested proceeding. Prepare a case brief with verified
identity, court/panel, date, posture, issues, material facts, disposition, reasoning and
pinpoints, ratio/obiter distinctions, appeal/treatment status and practical relevance.
Separate lower-court and appellate reasons; identify supplemental, costs and correction
judgments. A public judgment collection does not supply a complete case file.

For a hearing research pack, provide an ordered authority index and accessible judgments,
legislation and relevant Hansard, with gaps for unavailable pleadings, submissions,
transcripts or orders. Use only legitimately accessible or user-supplied documents.
Do not imply compliance with filing, pagination, or bundle requirements unless those
requirements and the assembled output have actually been checked for that proceeding.

## Source library

Read and verify source identity before creating a record. Deduplicate using the
verified legal identifier and version, then inspect similar titles manually; a judgment
and appeal or revised statute are not duplicates merely because titles resemble one
another. Preserve report and neutral citation metadata without asserting they are
interchangeable. Record authors, editors, title, publication, date, locator and URL only
when verified; leave unknown fields blank.

`research.py export-library` creates a CSL-JSON file suitable for review and import
into a reference manager such as Zotero. Add a `csl` object to each selected source,
using verified metadata and an appropriate CSL type. The helper exports only sources
marked identity-verified and full-text-reviewed, rejects duplicate record identities,
and never writes to a live library or uploads documents. CSL-JSON export does not
install an SLR citation style. Live library changes require the user's authority and
an available connected tool; inventory existing records before authorised writes.
