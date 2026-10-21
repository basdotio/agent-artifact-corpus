# GO-CAM review checks

The GO-CAM review skill checks a GO-CAM model, either in Noctua, in Noctua-dev, or as a file loaded in the workspace. The script (`qc.md`) covers the mechanical part, marked **[flag]** with the tag it uses; 
everything else is read. The rules the model is judged against are in the `gocam-best-practice` skill
(`references/Relation_selection.md`, `Evidence_and_evidence_codes.md`, and the
activity-type files); read the ones that match the model's activities.

## Severity

| Severity | Meaning |
|---|---|
| critical | The model makes a false statement, or cannot stand in production as is: wrong gene, a claim not in the paper, a missing enabler, a fact with no evidence, a single-activity model, an obsolete term, or a term present in the do-not-annotate or obsoletion-candidate subsets. |
| major | A fact is unsupported or mis-coded: incorrect organism for the evidence code (experimental captured instead of ISS),  a direct relation without a known mechanism, a reference that does not show the fact. Hygiene and style: malformed reference, malformed identifier in 'with/from' or inputs/outputs.|
| moderate | Correct in substance but weakly supported or imprecise: a self-referential IC, a too-general term, an unverifiable reference, ISS without an experimental source, a bare DOI where a PMID exists, missing location or process. |
| minor | Duplicate evidence line, leftover comment. |
| note | Not a defect: a remark, a question for the curator, or something that is fine and worth saying. |

Script severities are inputs, not verdicts: an `error` is usually a critical
or major candidate, a `warning` a major or moderate candidate; read each in
context before it becomes a finding.

## Checking procedure 
There are 8 groups of checks ran in this skill, labeled A-I. 

### A. Hygiene

- The title correctly and succinctly describes what the model is about (main biological process, additional
  relevant biological context (such as cells, tissues, specific genes), and organism. Not a
  placeholder, not a PMID. Length is not raised. **[flag]** `hygiene`
- The Model State is the curator's call; say if it looks inconsistent (production with
  open reviewer comments).
- Confirm that the taxon set is correct. **[flag]** `hygiene`
- Model comments addressed to a reviewer or describing a past edit should be
  resolved before upgrading the model to production; comments documenting a decision are fine. Read
  each. **[flag]** `hygiene: model comment to read`
- Orphans and leftovers: individuals in no fact, evidence attached to nothing,
  the same edge reified twice. **[flag]** `structure` (these are the
  noctua-models production QC checks; an error there blocks promotion)
- Every activity unit is complete: a molecular function with an enabler (the
  root MF with an enabler means "function unknown", which is allowed), a
  process by `part of`, a location by `occurs in` where known, and evidence on
  every fact. **[flag]** `activity`, `evidence`. Enumerate activities both
  ways: by `enabled by` and by MF typing; an MF node with no enabler is only
  visible the second way, and is critical.
- Single-activity model: GO expects a multi-activity flow. **[flag]** `structure`

### B. Evidence codes and the with/from field

The rules are in `gocam-best-practice` `references/Evidence_and_evidence_codes.md`
(evidence codes, the with/from field, references). Check every fact against them;
what the review adds:

- Code against the experiment: read the cited figure, not the abstract or the
  paper's conclusion.
- IEP on a fact whose term is not a biological process. **[flag]** `with: IEP`
- `with` present or absent as the code requires. **[flag]** `with`
- Circular `with`: an IC citing the term it supports, or an ISS citing the gene
  being annotated. An IC from the activity's own MF (e.g. MF → occurs in nucleus)
  is legitimate if that MF has its own evidence; check that it does.
  **[flag]** `with: circular`
- Copy-paste `with`: one value repeated on facts where it cannot be right. Use
  the with/from inventory in `qc.md`.
- Recipe mismatch between GO_REF and code. **[flag]** `with: recipe`
- Reference form and duplicate evidence lines. **[flag]** `evidence`.
- A bare DOI when a PMID exists is moderate (`gocam-review` rated it a blocker, `gocam-qc`
  hygiene).
- IEA or IBA not copied from an existing annotation; NAS or TAS where a primary
  paper exists: note it.
- Attribution: if the model cites P for a fact P attributes to Q, the fix is to
  re-source to Q. Finding Q, or any better reference, follows the Step 5 limits:
  papers already in the model first, then one search, three facts per review.

### C. ISS and orthology

The ISS recipe is in `Evidence_and_evidence_codes.md`. For every ortholog in a
`with` on ISS/ISO/ISA evidence:

1. Look up the source gene's annotation (`amigo` skill): experimental, to the
   same or a more specific term. An ISS whose source is itself ISS, ISO, IBA or
   IEA has no source: major.
2. For a causal edge, the source data show the same relation between the
   orthologs.
3. The `with` id is the true ortholog (PANTHER or the Alliance when in doubt,
   especially in families with paralogs).
4. When the transfer carries the model, check the source annotation's own
   reference; it can be wrong too, and that is worth telling the curator.

### D. Species of the data and of the entities

- An experimental evidence code on an assertion needs an
  experiment on the species encoding the gene product enabler. Data on a mouse protein in a
  human model is ISS from the mouse gene, not IDA. A human protein in a
  heterologous system (HEK293, CHO, yeast, Xenopus oocytes) supports IDA on
  the human protein; say which it was. Only down-code the facts that rest
  solely on the ortholog: a mouse phenotype paper can still carry a correct
  IDA from a human-protein assay in the same paper.
- Read the methods for the species of cells, animals and constructs; abstracts
  often omit it. Abstract only: species unverified.
- Entities whose namespace implies another species than the model's taxon:
  host-pathogen models are the exception. **[flag]** `species`
- Model-organism gene products use the MOD accession (MGI, RGD, ZFIN, FB,
  SGD, WB, PomBase, ...), not UniProtKB; human is the exception. MGI ids are
  written `MGI:MGI:n`. Applies to `with` too.

### E. References reused out of context (every PMID, every round)

The most common real problem, invisible to the script. Use "References, and
the facts each supports" in `qc.md`; for each PMID, fact by fact:

- Does this paper show this fact: this gene product (not a paralog or the
  family), this activity, this relation, this location or cell type?
- Is the code right for what the paper shows for this fact? A paper with IDA
  for the binding does not give IDA for the downstream process.
- Was the reference copied from another model or the parent onto edges it
  does not cover? A comment "evidence copied from ..." is the usual trace.
- A review under an experimental code: TAS or NAS at most; better, the
  primary paper.
- When the cited paper does not show the fact, suggest a better reference:
  one already cited elsewhere in the model first, then one search (Step 5
  limits). The suggestion is a candidate for the author to read, not a fact.

Raise this even when a similar item was declined earlier: new edges reuse
references. Without the full text, "not verified (abstract only)".

### F. Causal relations and molecule handling

`Relation_selection.md` is the rule; the short version:

- directly positively/negatively regulates: an immediately downstream
  activity, no intervening activity, mechanism known. Without a known
  mechanism: causally upstream of, positive/negative effect. indirectly
  regulates: through a larger reusable process deliberately not drawn,
  mechanism still known. provides input for: the upstream output is the
  downstream input (only when the molecule itself is not modelled; when it is,
  `has output` and `has input` carry it). removes input for: both act on the
  same target site with opposite effect. constitutively upstream of: required,
  not regulating.
- Sign matches the data, direction is upstream to downstream, and the edge's
  reference shows the link between these two activities, not merely between
  the two proteins somewhere. A ligand to its receptor is a causal relation,
  not `has input`.
- Look at the whole chain: missing obvious steps, a regulated activity with no
  path to the process, a causal edge into a process when an activity in that
  process is known.
- Inputs are the direct targets. Do not call a `has input` redundant because a
  causal edge exists; call it missing when a substrate, regulated gene,
  receptor ligand or activated effector is absent. When `has input` is a gene
  product there is no `has output`; the relation is `directly regulates`,
  except when there are intervening activities.
- Molecule reuse: the productive handoff is good modelling. A molecule that is
  the `has output` of one activity and the `has input`, or the small-molecule
  activator or inhibitor, of a downstream activity should be the same
  individual; that shared node is what represents the handoff. Only flag reuse
  that forces one individual into contradictory roles or merges two separate
  pools. Each activity has its own `part of` process individual; a process
  node shared by several activities is a defect.
- Chemicals: reactants and products are the ChEBI ids of the enzyme's Rhea
  reaction (UniProt `cc_catalytic_activity`); one compound keeps one ChEBI id
  across a handoff; only primary substrate and product belong (cofactors,
  donors, byproducts such as UDP, ATP, ADP, H2O, H+ do not). An obligate
  coupled reaction (an exchange or antiport) is one activity with its full
  participant set and one Rhea id, not two half-transfers.
- A metabolite `located in` a compartment needs direct evidence for that
  metabolite in that place (a transporter or marker paper is not), and the
  location must be compatible with the `occurs in` of the activities that
  produce or consume it.

### G. Term choice, specificity, locations, enablers

- Every class exists, is not obsolete, and is not in `gocheck_do_not_annotate`
  (errors) or `gocheck_obsoletion_candidate` (warning). **[flag]** `terms`.
  Read the labels the script prints: a label that does not match what the
  curator meant is a wrong ID.
- Taxon constraints for the model's species: not checked by the script; check
  by hand (`taxon-constraint` skill) for terms with a restricted taxon range.
- Specificity: as specific as the data support, no more. "protein binding" or
  a generic binding term where the paper shows the activity; a parent like
  "signal transduction" where the pathway is known; or a child the paper does
  not reach.
- The MF is an activity of the enabler, not a role in a process; regulators as
  regulator activities (enzyme regulator, adaptor) per the guidelines.
- Locations: `occurs in` the GO component where the activity happens (a
  receptor at the plasma membrane, not "cell"). A complex term is not a
  location. Nest the component `part of` a CL cell type or UBERON anatomy when
  the paper's system is known, and check it matches the paper (cell line,
  primary cell, tissue).
- Enablers: the gene product (UniProtKB, isoform when the paper is isoform
  specific), a ComplexPortal complex when subunits are known, the GO complex
  term when they are not, per `How_to_annotate_complexes_in_GO-CAM.md`.
- Process context: each MF `part of` the right process; nested processes make
  sense. Cytokine-signalling models: GO:0019221 in every activity unit;
  sibling cytokine-production terms collapsed to GO:0001819, with GO:0050729
  as the process above them.
- Models bound for the drop box (gocam-py YAML): the YAML keeps one `part of`
  chain per activity, so parallel process branches on one activity need a
  single nested chain; flag them.

### H. Lineage

- Earlier rounds: read `checklist.md` and `checklist-done.md` under
  `~/reviews/*-<id>/`. Done items: verify they are fixed. Declined with a
  reason: do not re-raise (except E). Keep ids stable.
- Parent model ("Derived from" in the header): fetch, `--facts-only` both,
  diff. Fixes made to the parent after the copy are often missing from the
  child; where an edit in the child looks as if it belongs in the parent too,
  say so in the report. The parent is edited, if at all, by its author in
  Noctua; nothing on the hub writes to a Noctua model, and nothing on the hub
  has access to production Noctua.
- Dev versus production: if the model is in both and they differ, say how.

### I. Literature honesty

- For every PMID, the evidence notes record what it supports, at what level
  (biochemical, cellular loss-of-function, genetic, interaction, imaging,
  clinical), the species and protein used, and "full text" or "abstract only".
- Figure-level detail (cell type, species, construct, assay) never comes from
  an abstract. If a finding depends on it and the paper was not read, the
  finding is unverified and the curator is asked for the PDF.
- Claims in model comments ("Fig. 3B shows ...") that were not checked are
  reported as unchecked, not endorsed.
- A wrong earlier finding is withdrawn by id at the top of the next report.
