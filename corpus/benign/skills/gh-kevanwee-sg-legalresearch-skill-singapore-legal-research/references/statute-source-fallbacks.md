# Statutory sources when SSO is unavailable

Source directory checked on **20 October 2026**. Recheck availability, coverage and
publication status for each run. No browser integration or replacement database
guarantees access to every Singapore instrument or its operative historical version.

## Choose an independent source

After [browser discovery](sources-authority.md#browser-discovery), if SSO is
unavailable, or automated collection is outside its permitted time window, continue
statutory research through the sources below. Choose by the
instrument, relevant date and available access; do not exhaust irrelevant databases
or wait for SSO before trying an independent publisher. Try relevant independent
sources before asking the user to obtain an SSO copy, unless the missing version
specifically requires that copy. An alternative source may
be read with an available web reader, authorised connector or ordinary download
tool when no browser works, subject to that source's terms and tool instructions.
Discovery of an alternative publisher is different from retrying a blocked SSO
endpoint through a proxy, another client or a mirror that forwards the same request.
An instruction to stop the entire turn still takes precedence.

| Source | What to retrieve | What it does not establish by itself |
|---|---|---|
| [Government eGazette](https://www.egazette.gov.sg/) | The actual Acts Supplement, subsidiary legislation, commencement notification, correction or other relevant Gazette instrument. Follow its search results to the published document; do not guess asset filenames. | An original Act or amendment is not the principal Act consolidated through the relevant date. Check publication status for the particular publication date. |
| [AGC revised editions](https://www.agc.gov.sg/our-roles/drafter-of-laws/revised-editions-of-legislation/) and the responsible ministry/regulator, e.g. [MOM](https://www.mom.gov.sg/legislation) or [ACRA](https://www.acra.gov.sg/regulations/legislation/) | An independently hosted complete legislative document, revised text or official commencement/amendment instrument, if actually available. | A directory linking back to SSO does not provide an independent copy. Agency explainers, FAQs, proposed legislation and consultation drafts are not enacted text. A PDF may be stale. |
| [LawNet](https://www.lawnet.com/) with existing authorised access | The legislation document and version metadata, rather than an AI answer or commentary. Its [legislation interface](https://release-notes.lawnet.com/2025/12/11/q4-2025-lawnet-release/) is documented by the publisher. | Subscription access, complete historical coverage and independence from SSO cannot be assumed. Confirm the text actually loads; a redirect to SSO is not a fallback. |
| [WIPO Lex: Singapore](https://www.wipo.int/wipolex/en/legislation/results?countryOrgs=SG) | Selected Singapore legislation, especially IP and related instruments; open the record and full text/PDF and retain its version information. | This is an international repository's republication, not Singapore's official consolidation service. Subject coverage and amendment cutoffs vary; a record labelled latest in WIPO need not be current Singapore law. |
| [ILO NATLEX](https://natlex.ilo.org/) | Selected labour, employment and social-security texts. Open the record's actual attached text, not just its abstract or external SSO link. | Repository metadata, subject summaries and adopted dates do not establish a current consolidation. Attachments can be historical: its [Employment Act record](https://www.ilo.org/dyn/natlex/natlex_browse.details?p_isn=3210&p_lang=en) links a PDF expressly labelled version in force from 1 April 2019. |
| Private saved copies, a user-supplied official publication or an authorised library/database | The original document and its provenance, edition and date, alongside any separately retrieved updates. | Being saved or supplied does not establish authenticity, completeness or currency. Recheck for this run and draft. |

WIPO and ILO copies can provide the enacted wording for a specified version. Record
their hosting/provenance qualifications rather than calling them Singapore official
publications. Other mirrors, archives and search results may locate missing material,
but do not promote their freshness claims or snippets into verified current law.
Prefer a full, traceable republication over a paraphrase; disclose any unresolved
authenticity, version or completeness issue.

## Verify the operative version

1. Match title, year, identifier, instrument type and exact section. Keep the
   principal Act, amending Act, subsidiary instrument and Bill separate. Capture the
   full cited unit, parent context, definitions, exceptions and schedules.
2. Record the document's stated consolidation/edition date and provenance separately
   from retrieval time. An older edition can govern historical events, but its date
   alone does not prove that it was unchanged until those events.
3. For the relevant date, check later amendments, provision-specific commencement,
   repeals, savings, transition and renumbering using independent official material
   or an authorised versioned legislation service. Log coverage and remaining gaps;
   an unsuccessful web search does not prove the absence of amendments.
4. If using an original or revised text plus amendments, preserve each instrument
   under its own source ID. Explain the provision-by-provision chain, effective
   dates and any amendments not yet commenced. A working reconstruction is analysis,
   not a publisher-issued consolidation: label it, retain the underlying texts, and
   cite the instruments that establish the wording. Do not snapshot generated
   consolidated prose as though downloaded from an official publisher.
5. If the text is found but its operative version cannot be established, say
   **text retrieved; applicable version unverified**. In a cite-check use
   `version_result: "unverifiable"`, retain the original citation and record the
   outstanding check. Leave the legal claim unresolved where that gap determines
   the answer; do not manufacture a verification receipt or mark it supported merely
   to complete a run. A clearly bounded historical comparison can still be reported
   when its own version and applicability have actually been verified.

The [eGazette notice](https://www.egazette.gov.sg/) distinguishes Gazette publications
on or after 9 March 2025 from earlier material. Check the governing publication rules
and date before making an authenticity claim; do not treat every downloaded PDF or
printout as having the same evidential status.

## Use the existing evidence helpers

The statutory workflow is source-independent. `extract-sso` is only for saved SSO
HTML; do not feed a Gazette PDF, WIPO page or LawNet export into that converter or
alter markup to make it look like SSO. Preserve the original, obtain a reviewed UTF-8
text extraction using available tools, and record the transformation with `snapshot`
and `--text`. Review PDF layout/OCR where necessary. Use `index-provisions`, `provision`
and `quote` with the same reviewed hierarchy, full-unit boundaries and fresh
identity/version receipt described in [statutory evidence](statutory-evidence.md).
The helpers do not require an SSO URL or its HTML container for those operations.

Record the actual host, original publisher, URL, retrieval time, edition/cutoff,
access route and SSO access gap in `publication_authority`, `review_note` and
`version_review`. Put amendment/commencement evidence and its source IDs in the
review notes. Do not write an SSO status line or report a live SSO test for a copy
obtained elsewhere. Separately disclose text retrieval, identity, quote fidelity,
operative-version verification and legal proposition support.
