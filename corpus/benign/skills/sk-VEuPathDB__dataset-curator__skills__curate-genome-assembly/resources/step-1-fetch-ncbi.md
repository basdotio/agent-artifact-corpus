# Step 1: Fetch Assembly Metadata from NCBI

## Overview

This step fetches detailed assembly and organism metadata from NCBI's Datasets API using the GenBank accession number.

## Command

```bash
curl -X GET "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/<GENBANK_ACCESSION>/dataset_report" -o tmp/<GENBANK_ACCESSION>_dataset_report.json
```

Replace `<GENBANK_ACCESSION>` with your actual accession (e.g., `GCA_000988875.2`).

## Example

```bash
curl -X GET "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/GCA_000988875.2/dataset_report" -o tmp/GCA_000988875.2_dataset_report.json
```

## What This Fetches

The NCBI dataset report contains:
- **Organism information**: Taxonomic name, tax ID, strain designation
- **Assembly information**: Version, release date, source database (GenBank/RefSeq)
- **BioProject accession**: Used in subsequent steps to fetch additional metadata
- **BioSample information**: Collection details, submitter organization
- **Annotation statistics**: Gene counts including non-coding genes (tRNAs)
- **Assembly methodology**: Sequencing technology, assembly method, coverage

## Expected Output

The JSON file is saved to `tmp/<GENBANK_ACCESSION>_dataset_report.json` and contains a structure like:

```json
{
  "reports": [
    {
      "organism": {
        "organism_name": "Genus species",
        "tax_id": 12345,
        "infraspecific_names": {
          "strain": "ABC123"
        }
      },
      "assembly_info": {
        "release_date": "2024-01-15"
      },
      "source_database": "SOURCE_DATABASE_GENBANK",
      "annotation_info": {
        "stats": {
          "gene_counts": {
            "non_coding": 123
          }
        }
      }
    }
  ]
}
```

## Troubleshooting

- **404 Not Found**: Verify the GenBank accession is correct and includes version suffix
- **Network errors**: Check internet connectivity
- **Invalid JSON**: The accession may not exist or API may be unavailable
