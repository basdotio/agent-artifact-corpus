# Saved research and evidence records

The helper is offline and uses Python 3.11+ standard-library modules. It does not
download authorities, interpret law, detect every citation or quotation, or verify
that a retrieved page is authentic. Use an available browser or authorised research
tool to retrieve a source, then preserve that retrieved file. Do not snapshot a
model-written summary as if it were source text.

Run the script from its installed location. Commands below assume a repository checkout.
On systems where `python` is not Python 3, substitute `python3`.

## Create a run

```sh
python skills/singapore-legal-research/scripts/research.py init runs/matter --question "The actual research question" --mode research --research-date 2026-10-20 --law-as-at 2026-10-20
```

Use the actual dates, not the dates in this example. `--law-as-at` is the date whose
law you are analysing; `--research-date` is when you perform the work. Modes are
`research`, `deep-research`, `find-authority`, `cite-check`, `legislation-hansard`,
`case-prep`, `library` and `proofread`. Existing `run.json` files are never overwritten
by `init`. Use a fresh run for a new draft or an update to earlier research.

## Preserve the material actually read

For a plain UTF-8 source file saved from a retrieved authority:

```sh
python skills/singapore-legal-research/scripts/research.py snapshot runs/matter source.txt --id S1 --kind case --title "Exact verified case name" --url "https://publisher.example/source" --citation "Exact verified legal identifier" --version "Actual version examined"
```

The URL and metadata above are placeholders, not authorities. Valid kinds are `case`,
`legislation`, `hansard`, `bill`, `secondary`, and `other`. Source IDs use letters,
digits, underscores and hyphens, beginning with a letter. Duplicate IDs are rejected.

For a PDF, save the original plus a UTF-8 text extraction and record the conversion:

```sh
python skills/singapore-legal-research/scripts/research.py snapshot runs/matter judgment.pdf --id S1 --kind case --title "Exact verified case name" --url "https://publisher.example/source" --citation "Exact verified legal identifier" --version "Unreported judgment PDF" --text judgment.txt --transformation "Extracted with pdftotext; paragraph and quote checked against PDF"
```

The helper does not supply a PDF extractor or OCR engine. Use available tools and
check the PDF visually where layout, characters, or numbering are uncertain. Preserve
OCR uncertainty; do not treat cleaned OCR as verbatim original text. HTML-to-text
conversion likewise needs the original file and a transformation description.

Snapshots record hashes and a UTC snapshot timestamp. **Snapshot time is not retrieval
time.** Fill in `retrieved_on` from the actual source retrieval, together with:

| Source field | Reviewer supplies |
|---|---|
| `publication_authority` | What this copy is: court-issued reasons, published report, official consolidation, supplied copy, etc.; include relevant status qualifications. |
| `identity_verified` | Boolean after matching title, identifier, court/instrument and other metadata to the source. |
| `full_text_reviewed` | Boolean after examining the source for the relevant context, rather than relying on a snippet or headnote. |
| `review_note` | What was compared, the version actually read, how the copy was obtained (user-saved browser copy, agent-operated browser, or scripted request with time and user-agent), and any limits. |
| `version_review` | For legislation relied on: selected date, operative provision, commencement, amendments, savings, revision and any old/new numbering evidence. |
| `treatment` | For cases relied on: status, explanatory note and search-log IDs. |

Treatment statuses: `not-checked`, `public-search-limited`, `citator-checked`,
`adverse-treatment-found`. Each asserted check needs linked `search_log` entries.
Record `id`, `database`, `query`, `searched_on`, `coverage`, and `result_note` for each
search. Queries must pass `screen` before they are sent, and `check` re-screens them against
the run's matter terms. A citator label records the reviewer's declaration, not an API verification.
Include the citator, search date and relevant results in the note.

For case evidence, build a reviewed paragraph index and pull the full paragraphs
using `index-paragraphs` and `passages`; see [paragraph evidence](paragraph-evidence.md).
This is required for case-law paraphrases as well as direct quotations. Each case
reference retains the complete selected paragraph records in `passages`. A saved
cite-check also preserves the original citation in the claim's `citation_check`.

For legislation, use `index-provisions` and `provision`; see [statutory evidence](statutory-evidence.md).
Every reference needs the exact unit's `passages`, its ancestor `context`,
`locator_type: "provision"`, and the selected `law_as_at` date. The source needs a
fresh `statute_verification` receipt identifying the actual instrument and version,
tied to the current `run_id`, research date and draft hash. `init` creates a new
`run_id`; copy it into the receipt only after the required identity/version checks.
Keep the existing `version_review` note as a concise summary of the provision checks.

## Claims and quotations

Edit `run.json` as the research proceeds. Each claim needs an ID, text, location,
assessment, reason and evidence array. The following is **synthetic test material**,
not a Singapore legal proposition:

```json
{
  "id": "C1",
  "text": "A synthetic proposition.",
  "location": "answer/p:1",
  "assessment": "supported",
  "reason": "The synthetic fixture expressly states this sentence.",
  "evidence": [
    {
      "source_id": "S1",
      "pinpoint": "[1]",
      "pinpoint_reviewed": true,
      "support_note": "Synthetic example only.",
      "passages": [
        {
          "paragraph": 1,
          "start": 4,
          "end": 28,
          "text": "A synthetic proposition."
        }
      ]
    }
  ]
}
```

Assessments are `supported`, `qualified`, `unsupported`, `unresolved`, and `editorial`.
`supported` and `qualified` need reviewed source evidence. An unresolved item may
have an empty evidence array and an explanation; it remains a visible limitation,
not a supported proposition. `editorial` is for prose-only findings, not a way to
bypass authority checks for a legal assertion.

Every quotation delivered must be separately inventoried. For source text beginning
`[1] A synthetic proposition.`, this example records the exact sentence:

```json
{
  "id": "Q1",
  "claim_id": "C1",
  "source_id": "S1",
  "text": "A synthetic proposition.",
  "start": 4,
  "end": 28,
  "pinpoint": "[1]",
  "pinpoint_reviewed": true
}
```

`start` and `end` are zero-based Python string offsets in the saved UTF-8 text, with
an exclusive end. They are not PDF coordinates or byte offsets. Matching normalises
Unicode composition and whitespace only; case, punctuation and words must match.
For an ellipsis or bracketed alteration, record each unchanged segment separately,
preserve the displayed alteration in the output, and manually review order, omissions
and meaning. The checker does not validate the legal effect of an omission.

Build quote records with the `quote` command rather than searching the text yourself:

```sh
python skills/singapore-legal-research/scripts/research.py quote runs/matter --source S1 --pinpoint "[103]" --text "the quoted words" --id Q1 --claim C1
```

It searches **only the cited paragraphs or provision**, so words that also appear
elsewhere in the source are bound to the passage actually cited. Whitespace in the
given words may differ from the source; the record keeps the source's exact text and
offsets. If the words are not in the cited passage, it fails and reports where they
do occur, which is often the right pinpoint to check. If they occur more than once in
the passage, choose one with `--occurrence`. An ellipsis is refused: quote each segment
separately. Add the printed record to `quotes` and set `pinpoint_reviewed: true` only
after checking it against the source.
For a case sub-paragraph pinpoint such as `[185(b)]`, the returned record includes
`scope` with the requested pinpoint, the full parent paragraphs searched and an
explicit warning: sibling text may match because child boundaries are not indexed.
Check the actual child against the source before setting the review flag. The
warning describes the tool's search scope; it is not automatic child verification.

The quotation's source and pinpoint must also appear in its linked claim's evidence.
For numbered cases, the checker binds the evidence to every full selected paragraph
in the reviewed source index and requires the quotation to lie within those paragraphs.
The reviewer still verifies numbering and boundaries against the original judgment,
and report-page locators require a documented manual check. Matching a quotation
elsewhere in a judgment does not verify its cited paragraph or legal support.

## Word drafts and coverage

```sh
python skills/singapore-legal-research/scripts/research.py extract-docx runs/matter draft.docx
```

This preserves the draft, hashes the extraction, and creates one `inventory` row per
non-empty body, table-cell, footnote and endnote paragraph. Rows initially have
`reviewed: false`, `claim_ids: []`, and an empty `reason`. Mark each reviewed location,
link its individual findings through `claim_ids` (each claim's `location` must equal
the inventory row's ID), or explain why it contains no
research item. Several authorities in one paragraph need separate claim records.
For non-Word material, manually build an inventory with stable locations, exact text
and the same review fields; preserve the original separately and state coverage limits.

The extractor preserves OOXML note IDs, not guaranteed displayed note numbers. It
includes deleted text and inserted text if present, and warns about revisions and
fields. It does not silently choose a final version. Headers, footers and comments
are flagged but not inventoried; complex layouts and text boxes need visual review.
Compare displayed numbering in Word before giving numbered-note findings. Do not
remove a warning unless you have resolved it and record what you checked.

## Check and deliver

Fill the top-level `review` with who performed the final review (including same-agent
review if applicable), what was rechecked and any material limitations. Record
remaining access/coverage limits in `gaps`, an array of non-empty strings. Then run:

```sh
python skills/singapore-legal-research/scripts/research.py check runs/matter
```

| Status | Meaning |
|---|---|
| `fail` (exit 1) | Missing or inconsistent records, changed evidence, unreviewed support, missing/wrong full paragraphs, wrong quote span, original citation replaced without checking, or incomplete draft coverage. Fix before claiming record checks passed. |
| `pass-with-limits` (exit 0) | Records are consistent but qualifications, unverified sources, public-only treatment checks or other gaps remain. Disclose them in the answer. |
| `pass-record-checks` (exit 0) | The recorded evidence passes these mechanical checks. This is not a legal accuracy or completeness certification. |
| CLI error (exit 2) | The command or input could not be processed. No successful check is implied. |

The checker does not discover omitted claims or quotes, scan the final memo, resolve
short-form citations, certify a source's authenticity, determine ratio, or test whether
support notes are legally correct. Reconcile the final output manually against the
ledger. A hash detects changes relative to a record; someone who rewrites both a file
and its hash can defeat that comparison. These are local evidence records, not signatures.

Existing saved runs keep their source snapshots, but case references must be enriched
with a reviewed paragraph index and full `passages` before the strengthened checker
passes them. Cite-check findings also need the original `citation_check` record. Do
not relabel an earlier successful check as having passed these newer requirements.
Earlier statutory runs without a `run_id` need a fresh `init` run and new identity,
version and provision review records. An existing `version_review` sentence alone
does not satisfy the stronger statutory evidence requirements.

## Library export

Add verified CSL metadata under a source's `csl` field, e.g. a synthetic example:
`{"type": "report", "title": "Synthetic test report"}`. Choose the correct type and
add only verified author, date, reporter, volume, page and other fields. Then:

```sh
python skills/singapore-legal-research/scripts/research.py export-library runs/matter runs/matter/library.json
```

Only records with `csl` metadata are selected. Export requires passing record checks,
identity verification and source review; identical citation/version pairs are rejected.
The output file must not already exist. Review near-duplicates and completeness manually.
Import into Zotero only when authorised; the helper does not mutate any account.
