# Step 2: Fetch BioProject Metadata

## Overview

This step fetches BioProject metadata from NCBI to get the project description, which is used in the presenter XML's description field.

## Prerequisites

Step 1 must be completed first. The BioProject accession is extracted from the assembly report JSON.

## Command

```bash
node scripts/fetch-bioproject.js <BIOPROJECT_ACCESSION>
```

## Example

```bash
# First, extract BioProject accession from assembly report
# It's at: reports[0].assembly_info.bioproject_accession

node scripts/fetch-bioproject.js PRJNA282568
```

## What the Script Does

1. **esearch**: Searches NCBI BioProject database to convert accession (e.g., PRJNA282568) to numeric ID
2. **esummary**: Fetches detailed BioProject summary using the numeric ID

## Output

The script saves results to `tmp/<BIOPROJECT>_bioproject.json`:

```json
{
  "accession": "PRJNA282568",
  "id": "282568",
  "title": "Rhodosporidium toruloides Genome sequencing",
  "description": "De novo assembly and annotation of the oleaginous yeast...",
  "organism": "Rhodotorula toruloides",
  "submitterOrganization": "University of California, Berkeley",
  "registrationDate": "2015/04/29"
}
```

## Key Fields

- **title**: Short project title (used for reference)
- **description**: Detailed project description (used in presenter XML's "General Description")
- **submitterOrganization**: May help identify contacts

## Troubleshooting

- **No results**: Verify the BioProject accession format (PRJNA, PRJEA, PRJDA, etc.)
- **Empty description**: Some BioProjects have minimal metadata; curator may need to write description manually

## Next Step

Proceed to [Step 3 - Fetch PubMed](step-3-fetch-pubmed.md) to find linked publications.
