<!--
AUTHOR: Erik Schultes (ORCID: 0000-0001-8888-635X)
SESSION: Making MAC FAIR/npfdo Chat B2
DATE: 2026-09-28
URL: https://claude.ai/chat/06e46b23-6173-46d6-a59e-5b7fb629498f
CREATED_AT: P04/R04 (revised P12/R12, P22/R22)
DESCRIPTION: Pinned inputs for the npfdo-mint skill: Trusty URIs, template links, term IRIs and FAIA predicates, each with its source file.
-->

# Pinned inputs, np-FDO core v0.1

Every value below is copied from a source file in the `npfdo-core` repository or the FAIA
distribution, not typed from memory. Re-verify against the source before relying on it. When a
record is superseded, the superseding record's Trusty URI replaces the old one for that object,
but the specification record `#1` (the `dct:conformsTo` value) is stable at v0.1.

## 1. The eight minted objects (Trusty URIs)

Source: `npfdo-core/MINTING_LOG.md`. Object numbers follow specification section 9, which lists
nine objects; object `#9` is not yet minted, so only `#1` to `#8` appear below.

| No. | Object | Trusty URI |
|---|---|---|
| 1 | Specification record (the `dct:conformsTo` value) | `https://w3id.org/np/RAYTT7oW0dbPdx3PqIA1m9XBLRGYVqmAhzLY7vLTMG1GI` |
| 2 | Assertion template | `https://w3id.org/np/RA5OrG1-PCAa3Z4kTLKTxq8lhgNAsopAtQM5h0-xj3MSA` |
| 3 | Publication-information template | `https://w3id.org/np/RAQV2LjRzG8BQ8wXb6Kbyytc8vVAUeS4pFdoOkG2WA_yI` |
| 4 | Example record | `https://w3id.org/np/RAE8Y_jz4pP3qZrKg1_zdkD-KvuVraVyfgpTrmaCgnIFQ` |
| 5 | Term record: FDORecord | `https://w3id.org/np/RAHgOMpNZQIyaymvafdq-qYruOFyMyYqTY2uVantrBDFE` |
| 6 | Term record: SlideDeck | `https://w3id.org/np/RAIST6Eo_gng7uaCjnOPbRbDUX67FnGVxW01_bYHjLOqM` |
| 7 | Term record: Skill | `https://w3id.org/np/RAxQWlDwrGKz4fKCVGX23WHCMlZjDHEGXu7JcMOBv85t0` |
| 8 | Conference record | `https://w3id.org/np/RAwBRuyJaw0ogGwUTxl8woy3nHPcFvDGCXBUXSQJfhZVc` |

## 2. Template links for pubinfo

Source: the `sub:pubinfo` block of the published records, e.g. `npfdo-core/records/08-conference-record.trig`.
Copy these three predicates verbatim into every record's pubinfo. Templates `#2` and `#3` have
embedded identity, so they are cited by their `.../template` IRI, not the bare nanopub URI.

| Predicate | Value(s) |
|---|---|
| `nt:wasCreatedFromTemplate` | `https://w3id.org/np/RA5OrG1-PCAa3Z4kTLKTxq8lhgNAsopAtQM5h0-xj3MSA/template` |
| `nt:wasCreatedFromProvenanceTemplate` | `https://w3id.org/np/RA7lSq6MuK_TIC6JMSHvLtee3lpLoZDOqLJCLXevnrPoU` |
| `nt:wasCreatedFromPubinfoTemplate` | `https://w3id.org/np/RAQV2LjRzG8BQ8wXb6Kbyytc8vVAUeS4pFdoOkG2WA_yI/template`, `https://w3id.org/np/RA-N4_kFxcruvBTlo1yJv29E4SLOXsx5KO_th69PprMrA`, `https://w3id.org/np/RALmzqHlrRfeTD8ESZdKFyDNYY6eFuyQ8GAe_4N5eVytc`, `https://w3id.org/np/RACJ58Gvyn91LqCKIO9zu1eijDQIeEff28iyDrJgjSJF8` |

Identities of the generic templates cited above. Each Note was verified P12/R12 by fetching the
template nanopub with `curl -fsSL -H "Accept: application/trig" https://w3id.org/np/<code>`: `#2` and
`#3` carry `npx:embeds sub:template` (embedded identity); the other four have their template node on
the `sub:assertion` graph and no `npx:embeds` (legacy), with `nt:TransientTemplate` on "Creator" and
`nt:UnlistedTemplate` on "optional creation date". Source: those template nanopubs.

| Role | Trusty URI | Note |
|---|---|---|
| np-FDO assertion template (`#2`) | `.../RA5OrG1-PCAa3Z4kTLKTxq8lhgNAsopAtQM5h0-xj3MSA/template` | embedded identity |
| np-FDO publication-information template (`#3`) | `.../RAQV2LjRzG8BQ8wXb6Kbyytc8vVAUeS4pFdoOkG2WA_yI/template` | embedded identity |
| Standard provenance: "Attributed to myself/others" | `.../RA7lSq6MuK_TIC6JMSHvLtee3lpLoZDOqLJCLXevnrPoU` | legacy, nanopub URI |
| Standard pubinfo: "Creator" | `.../RA-N4_kFxcruvBTlo1yJv29E4SLOXsx5KO_th69PprMrA` | legacy; `nt:TransientTemplate` |
| Standard pubinfo: "optional creation date" | `.../RALmzqHlrRfeTD8ESZdKFyDNYY6eFuyQ8GAe_4N5eVytc` | legacy; `nt:UnlistedTemplate` |
| Standard pubinfo: "License" | `.../RACJ58Gvyn91LqCKIO9zu1eijDQIeEff28iyDrJgjSJF8` | legacy, nanopub URI |

## 3. The three np-FDO term IRIs

Source: `npfdo-core/records/05-term-FDORecord.trig`, `06-term-SlideDeck.trig`, `07-term-Skill.trig`
(the `npx:introduces` object) and the frozen bootstrap term set. Base `https://w3id.org/npfdo/terms/`.

| Term | Full IRI | Used as |
|---|---|---|
| FDO record | `https://w3id.org/npfdo/terms/FDORecord` | object of `npx:hasNanopubType` on the record |
| Slide deck | `https://w3id.org/npfdo/terms/SlideDeck` | `rdf:type` of the referent |
| Skill | `https://w3id.org/npfdo/terms/Skill` | `rdf:type` of the referent |

## 4. FAIA predicates and values

Source: `tools/faia/faia_ont_0.6.0.ttl` and `tools/faia/faia_vocab_0.7.0.ttl`.
Prefix `faia_ont: <https://w3id.org/faia-framework/faia_ont/>`,
`faia_vocab: <https://w3id.org/faia-framework/faia_vocab/>`.

File SHA-256:

| File | SHA-256 |
|---|---|
| `faia_vocab_0.7.0.ttl` | `d9f350363a1a6fc95c8b5006475b39400d593fb73451722fbf7dda0c07483c9d` |
| `faia_ont_0.6.0.ttl` | `e9ce0b913df39e4d7d2dfd18a2492021a1679847ebb7e333a78f3dad820e1998` |

Predicates (`faia_ont`), each with `rdfs:domain <https://w3id.org/liccium/ont/Declaration>`:

| Predicate | `rdfs:range` | Literal form to write |
|---|---|---|
| `faia_ont:faiaFlag` | `xsd:anyURI` | the concept IRI as `"<IRI>"^^xsd:anyURI` |
| `faia_ont:activityCode` | `xsd:anyURI` | the concept IRI as `"<IRI>"^^xsd:anyURI` |
| `faia_ont:systemAttribution` | `xsd:string` | plain `xsd:string` literal |
| `faia_ont:systemVersion` | `xsd:string` | plain `xsd:string` literal |

FAIA flag values (`skos:narrower` of `faia_ont:FaiaFlag`):

| IRI | prefLabel | altLabel |
|---|---|---|
| `https://w3id.org/faia-framework/faia_vocab/HCC` | HCC | human-created content |
| `https://w3id.org/faia-framework/faia_vocab/AAC` | AAC | ai-assisted content |
| `https://w3id.org/faia-framework/faia_vocab/AIG` | AIG | ai-generated content |

Activity code values (`skos:narrower` of `faia_ont:ActivityCode`); the FAIA core set:

| IRI | prefLabel |
|---|---|
| `https://w3id.org/faia-framework/faia_vocab/Co-Creation` | co-creation |
| `https://w3id.org/faia-framework/faia_vocab/Contribution` | contribution |
| `https://w3id.org/faia-framework/faia_vocab/Enhancement` | enhancement |
| `https://w3id.org/faia-framework/faia_vocab/Refinement` | refinement |
| `https://w3id.org/faia-framework/faia_vocab/Transformation` | transformation |
| `https://w3id.org/faia-framework/faia_vocab/Analysis` | analysis |

The vocabulary also defines eight `STM-*` activity codes (source: STM Association) under the same
`faia_vocab` base, e.g. `STM-LanguageRefinement`, `STM-ManuscriptDrafting`. Use only the value the
user declares; never infer it.

`rdfs:domain` entailment (known consequence): any subject that carries one of the four predicates
is entailed to be a `<https://w3id.org/liccium/ont/Declaration>`. This follows from the FAIA
ontology and is expected; it is not an error in the record.
