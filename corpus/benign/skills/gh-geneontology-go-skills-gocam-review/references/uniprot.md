# UniProt cross-check (optional module, `--with-uniprot`)

A GO-CAM often holds experimentally supported knowledge that is not yet in
UniProt, or that conflicts with the entry. For every gene-product enabler,
compare the model's claims with the UniProt entry in both directions and write
`uniprot-review.md`; the model report keeps one line pointing at it. A genuine
conflict where the model is the one that is wrong is also a finding in the
model report.

1. Resolve the entry. A MOD accession maps to UniProtKB through ID mapping
   (`uniprot-database` skill); human enablers are UniProtKB already.
2. Compare: `CC FUNCTION` against the asserted molecular functions;
   `cc_catalytic_activity` (Rhea id and ChEBI participants) against the
   model's reaction, direction and participants; `SUBCELLULAR LOCATION`
   against `occurs in`.
3. Classify each as missing in UniProt, conflict (report both sides and the
   evidence each rests on; do not pick), or consistent (say so briefly).
4. For missing and conflict items, draft what the author could submit: the
   UniProt-style text (a function sentence, a catalytic activity line with Rhea
   id and ChEBIs, a location term), the PMID and the ECO code for what the
   paper shows, and one line on why. Primary experimental evidence only; ISS,
   IBA or IEA support is not submittable on its own, and the draft says so.
5. Verify the paper in full text before proposing a reaction (a synthetic
   substrate assay does not support a physiological Rhea reaction; a
   right-reaction, wrong-paper mismatch is common). Rhea reactions and ChEBI
   participants come from the Rhea SPARQL endpoint
   (`https://sparql.rhea-db.org/sparql`); prefer the generic reaction over
   acyl-specific forms; ortholog entries sometimes carry reactions the human
   entry lacks.

Limits: the enablers in the model, not their families; at most the five
papers of Step 5.
