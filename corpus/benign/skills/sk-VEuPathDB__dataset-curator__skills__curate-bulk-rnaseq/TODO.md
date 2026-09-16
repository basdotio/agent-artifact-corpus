# TODO: curate-bulk-rnaseq

## Completed

### ~~Initial Implementation~~ (Done)

- ~~Description and methodology generation~~ - Now supports AI-improved descriptions using PDF data (Step 4)
- ~~Strandedness detection~~ - Now detects from PDF extracted data, sample annotations, or CLI argument (Step 5)
- ~~PDF Support for Journal Articles~~ - Implemented in Step 1 with extraction to `_pdf_extracted.json`

---

## Ideas for Future Consideration

### Sample Annotation Ontology/Controlled Vocabulary
- maintain a git-controlled ontology OWL XML file describing sample annotation fields and values appropriately for all organisms in VEuPathDB (some field names and/or values may not be applicable to both single-celled parasites and also insect vectors; developmental stage naming differs even within VectorBase)
- skill workflows search the ontology for similar terms and judge if an existing term can be re-used, or if a new term should be added to the ontology
- values can be handled similarly (when in tractable numbers)
- the outcome is that sample annotation fields and values should be curated consistently across datasets and projects. Inconsistencies would be flagged at PR merge time if two curators worked on similar RNA-Seq studies at the same time.
- slight concern that git's diffing of XML is not ideal

