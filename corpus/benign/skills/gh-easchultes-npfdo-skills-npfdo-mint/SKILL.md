---
name: npfdo-mint
description: Mints np-FDO records, that is, metadata records of FAIR Digital Objects published as nanopublications conforming to the np-FDO core specification v0.1, each typing, labelling and attributing exactly one referent, stating the conditions of use of any materialisation, declaring the specification version, and marked npfdo:FDORecord, with optional FAIA (FAIR AI Attribution) statements. Use when a user wants to describe a conference, specification, vocabulary, slide deck, agent skill or vocabulary term as an FDO record.
---
<!--
AUTHOR: Erik Schultes (ORCID: 0000-0001-8888-635X)
SESSION: Making MAC FAIR/npfdo Chat B2
DATE: 2026-09-28
URL: https://claude.ai/chat/06e46b23-6173-46d6-a59e-5b7fb629498f
CREATED_AT: P04/R04 (revised P12/R12, P22/R22)
DESCRIPTION: The np-FDO minting skill: elicit, write TriG, check, sign, verify, stop; the human publishes.
-->

This skill mints one np-FDO record: a nanopublication that is the metadata record of one FAIR
Digital Object under np-FDO core v0.1. It adds a thin np-FDO layer on top of the general
nanopublication workflow and defers all network mechanics to the upstream `nanopub` skill.

## Dependency

This skill **requires the Knowledge Pixels `nanopub` skill** and defers to it for:

- the four-graph TriG structure: section **"Nanopublication Structure"** and **"3. Create the TriG file"**;
- validating and signing: section **"4. Validate and sign"**;
- publishing: section **"7. Wait for explicit publishing instruction"**;
- retraction: section **"8. Retract a nanopub (if a bad version was published)"**;
- template conformance checking: the passage **"Checking a nanopub against its template"**
  (its `check-nanopub-conformance.py`, installed at
  `~/.claude/skills/nanopub/scripts/check-nanopub-conformance.py`);
- fetching a published record back: section **"Fetching an existing nanopub"**.

If the `nanopub` skill is not available, **stop and say so**; do not reimplement it here.

**Profile check: a deliberate departure.** This skill does **not** follow the upstream section
**"2. Check the user's profile"**, because that check reads `~/.nanopub/`, which hard rule 2
forbids. Instead, the user **declares their ORCID** (step 1), and after signing, `npx:signedBy`
**must equal that declared ORCID** (step 5).

Precedence: on network mechanics (signing, publishing, fetching, URI schemes) the `nanopub`
skill wins. On the np-FDO layer (what a record must contain and mean) the frozen np-FDO core
specification wins.

## Hard rules

This skill runs where no project `CLAUDE.md` exists, so its rules are stated in full here.

1. **Never publish.** This skill ends with a signed, verified file and a printed one-line command
   for the human to run in a separate plain terminal. Signing is allowed; publishing is not.
2. **Never touch the key store.** Never open, print, copy or modify anything under `~/.nanopub/`.
   Only the jar's own `sign` command may read the key.
3. **Never hand-write signature triples** (`npx:signedBy`, `npx:hasSignature`, `npx:hasPublicKey`,
   `npx:hasSignatureTarget`). Signing produces them.
4. **Stop and ask** on any design question the specification or the starter slot list does not
   settle. Do not choose.
5. **Declarations, not inferences.** FAIA values, dates, licences and creators are the user's
   declaration. Never infer or default them.
6. **Test registry is the default.** Publication is proposed against the test registry; the live
   network only on an explicit instruction that names it.

## Pinned inputs

All Trusty URIs, template links, term IRIs and FAIA predicates are in
[`reference/pinned.md`](reference/pinned.md), each with its source file. Copy values from there
(or re-read the source), never from memory. A worked skeleton is in
[`reference/record-skeleton.trig`](reference/record-skeleton.trig).

## Procedure (the np-FDO layer)

### 1. Elicit

Ask the user for, and never infer:

- **The user's ORCID**, as a declaration. Do not read it from `~/.nanopub/` (hard rule 2). It is
  used for `dct:creator` and provenance, and checked against `npx:signedBy` in step 5.
- **Type** (slot C1). v0.1 choices: `bibo:Conference`, `bibo:Specification`, `skos:ConceptScheme`,
  `npfdo:SlideDeck`, `npfdo:Skill`; and `owl:Class` for a vocabulary-term record (bootstrap term
  set section 3). A type outside this list is a design question: stop and ask.
- **Label** (slot C2), with a language tag, e.g. `"..."@en`. When the user declares the example
  marker (`npx:hasNanopubType npx:ExampleNanopub`), propose a label beginning `"Example: "` (the
  upstream convention); the label the user declares decides.
- **Identity** (slot C5). If the object already has an identifier, the record **describes** that
  IRI (`npx:describes <IRI>`, subject is the external IRI). Otherwise it **introduces** a new
  referent (`npx:introduces sub:referent`); for a w3id term use the **full IRI**, not `sub:`.
- **Materialisations** (slot cluster B), 0..n. Each is a node linked to the referent by
  `fdof:materializes`, carrying: `dcat:accessURL`; `dcat:downloadURL` (SHOULD be present when a
  checksum is given); `dct:license` (**required per node**, slot M1); `dcat:mediaType` as an IANA
  media-type IRI (`http://www.iana.org/assignments/media-types/<type>/<subtype>`); `dcat:byteSize`
  (`xsd:nonNegativeInteger`); `dct:issued` (`xsd:date`); and `spdx:checksum` pointing at a named
  `spdx:Checksum` node (`spdx:algorithm`, `spdx:checksumValue`), the value being the **SHA-256
  computed from the bytes served at the download URL**. The media type is the **user's
  declaration**; report the `Content-Type` the server sends for information only, never as the
  value (GitHub raw, for example, serves `text/plain`).
- **Optional**: description, creator(s), and qualified references, the four relations of slot list
  section D (`dct:isPartOf`, `bibo:presentedAt`, `prov:wasDerivedFrom`, `dct:replaces`).
- **Type-specific slots** (slot list section G) only on explicit instruction; report them as
  **unmatched extensions** (they are permitted by the open shape but are not in template `#2`).
- **FAIA**, per graph, if the user declares it (see step 3).

### 2. Write the TriG

Follow the published records (`npfdo-core/records/`) and the skeleton. The base name of the
temporary prefixes is free, but it must be **unique per file**, and `this:` and `sub:` must be
**equal** and **end in a slash** (a missing slash produced `//assertion` graph names in an earlier
build). The pubinfo graph carries, exactly as in the published records:

- `npx:hasNanopubType npfdo:FDORecord`;
- the identity link (`npx:introduces` or `npx:describes`);
- `dct:conformsTo` the specification record `#1` Trusty URI (see `reference/pinned.md`);
- `dct:created` as an `xsd:dateTime` in UTC (get it with `date -u +%Y-%m-%dT%H:%M:%SZ`);
- `dct:creator` (the user's ORCID);
- `dct:license` for the record itself, elicited like any other declaration (see step 1); propose
  CC BY 4.0, which every published v0.1 record uses, but do not hard-code it;
- the three `nt:wasCreatedFrom...` template links, copied verbatim from `reference/pinned.md`.

Provenance carries `sub:assertion prov:wasAttributedTo <ORCID>`.

### 3. FAIA placement (decided P04/R04)

Under np-FDO core **v0.1, FAIA statements are extensions**: the frozen specification keeps FAIA
outside the core, and FAIA enters the core with v0.2. They are therefore optional and, when
present, appear as unmatched extensions in the conformance check (step 4).

FAIA statements may be attached in any of three graphs, by what the AI involvement is about:

- **the referent** (assertion graph): subject is the referent;
- **the description activity** (provenance graph):
  `sub:assertion prov:wasGeneratedBy sub:activity . sub:activity a prov:Activity .` with subject
  `sub:activity`;
- **the record** (pubinfo graph): subject is `this:`.

**Default proposal to the user:** FAIA in all three graphs (flag, activity code, and system where
the user declares them). **The flag alone is the minimum.** Every value is asked, never inferred.

Ask for the **system name** (`faia_ont:systemAttribution`) and the **system version**
(`faia_ont:systemVersion`) as two separate questions. If the user gives one combined string, keep
it whole in `faia_ont:systemAttribution`; never split it.

Predicate ranges (see `reference/pinned.md`): `faia_ont:faiaFlag` and `faia_ont:activityCode` take
the concept IRI as an **`xsd:anyURI` typed literal**; `faia_ont:systemAttribution` and
`faia_ont:systemVersion` take **`xsd:string`** literals. Known consequence: each FAIA predicate has
`rdfs:domain <https://w3id.org/liccium/ont/Declaration>`, so the subject is entailed to be a
`liccium:Declaration`. This is expected, not an error.

### 4. Check

Validate with the jar (section "4. Validate and sign"). On the **unsigned** file the jar reports
`Nanopub has no signature element` and `Unexpected graph uri` for the temporary graph names; these
are normal. The ISSUES gate (an empty `ISSUES:` block) applies to the **signed** file only.

Then run the `nanopub` skill's conformance checker as its passage "Checking a nanopub against its
template" describes:

```
python3 ~/.claude/skills/nanopub/scripts/check-nanopub-conformance.py <file.trig>
```

The checker compares **only the assertion graph** with template `#2`. FAIA statements in
provenance and pubinfo, and the example marker, are **not checked by it**; check them in the TriG.

Expected **unmatched** items, which are permitted extensions, not faults:

- FAIA statements in the assertion graph (not in template `#2`);
- for term records: the SKOS statements and `owl:Class` (outside the type choice list; the
  required type statement then reports as not instantiated);
- type-specific slots given on explicit instruction (step 1).

Exit code 1 is acceptable **if and only if** every unmatched item is an expected extension.
Report anything else as a finding and stop. The checker's display truncates long literals: check
values against the TriG itself, not the display.

### 5. Sign and verify

Sign per the `nanopub` skill (default key). Verify that `npx:signedBy` equals the ORCID the user
declared in step 1.
Report the Trusty URI and the signed file's SHA-256.

### 6. Stop

Print the one-line gate command for the human to run in a separate terminal (test registry
proposed), runnable from any directory:

```
bash ~/.claude/skills/npfdo-mint/scripts/npfdo-gate-publish.sh <signed-file.trig> <RA-code> <sha256> test
```

`<RA-code>` is the **bare artefact code** (`RA...`), not the full URI. `NP_JAR` must be set in the
environment (as the `nanopub` skill requires). Do not run it. Do not
publish.

### 7. Record (after the human reports publication)

Append a row to `MINTING_LOG.md` in the working directory (create it if absent) with: number,
object, file, Trusty URI, signed-file SHA-256, registry (test or live), date.

### 8. Supersession

To supersede, add `npx:supersedes <old Trusty URI>` in pubinfo, **same signing key only** (if the
key differs, use `prov:wasDerivedFrom` in provenance instead). An introduced referent is
re-introduced by its **full IRI**; unchanged content is copied verbatim from the old record.
