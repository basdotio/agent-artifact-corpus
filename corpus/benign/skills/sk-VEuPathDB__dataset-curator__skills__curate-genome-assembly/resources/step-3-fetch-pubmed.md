# Step 3: Fetch PubMed Data

## Overview

This step finds and fetches PubMed publications for the genome assembly. These publications provide:
- PubMed IDs for the presenter XML
- Author information for contact identification

## Prerequisites

Steps 1 and 2 should be completed first (the script reads from the assembly and bioproject JSON files).

## Command

```bash
node scripts/fetch-pubmed.js <ASSEMBLY_ACCESSION>
```

## Example

```bash
node scripts/fetch-pubmed.js GCA_000988875.2
```

## What the Script Does

1. **NCBI Datasets publications API**: Finds both formally linked and text-mined publications
2. **BioProject elink** (fallback): Checks for publications linked via BioProject
3. **esummary**: Fetches details for each PubMed record (title, authors, etc.)

## Output

The script saves results to `tmp/<ASSEMBLY_ACCESSION>_pubmed.json`:

```json
{
  "assemblyAccession": "GCA_000988875.2",
  "bioProjectAccession": "PRJNA282568",
  "pubmedCount": 1,
  "papers": [
    {
      "pmid": "29521624",
      "title": "Genome sequence of the oleaginous yeast Rhodotorula toruloides...",
      "authors": [
        {"name": "Coradetti ST", "authtype": "Author"},
        {"name": "Skerker JM", "authtype": "Author"}
      ],
      "lastAuthor": "Skerker JM",
      "discoverySource": ["entrez", "assembly_pubmed", "bioproject_pubmed"]
    }
  ]
}
```

## Key Fields

- **pmid**: PubMed ID to include in presenter XML
- **authors**: List of authors (useful for contact identification)
- **lastAuthor**: Senior/corresponding author (often the primary contact)
- **discoverySource**: How the publication was found (formal links vs text-mined)

## No Publications Found

If no publications are found automatically, the curator can provide a PubMed ID manually if they find a relevant paper through their own search.

### Manual PubMed ID Provided

If the curator provides a PubMed ID manually, fetch the paper details using:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=<PMID>&retmode=json
```

Use the author list for contact curation in the next step.

## Contact Identification

Use the author list to help identify contacts:
1. **lastAuthor** is typically the senior/corresponding author - good candidate for primary contact
2. For genome-specific papers, other authors may be appropriate additional contacts
3. For papers where genome is incidental to a larger study, use judgment about which authors to include

## Next Step

Proceed to [Step 4 - Curate Contacts](step-4-curate-contacts.md) to identify and create contact entries.
