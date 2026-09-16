# Step 1: Fetch SRA Metadata

## Overview

This step fetches run-level metadata from ENA and sample attributes from NCBI BioSample for the specified BioProject.

## Command

```bash
node scripts/fetch-sra-metadata.js <BIOPROJECT>
```

Replace `<BIOPROJECT>` with the accession (e.g., `PRJNA1018599`).

## Example

```bash
node scripts/fetch-sra-metadata.js PRJNA1018599
```

## What This Fetches

The script queries two APIs and merges the results:

### ENA Portal API
- Run accessions (SRR...)
- Sample accessions (SAMN...)
- Library layout (PAIRED/SINGLE)
- Library strategy, source, selection
- Instrument platform and model
- Read and base counts
- Scientific name and taxonomy ID

### NCBI BioSample API
- Custom sample attributes (infection status, tissue, timepoint, etc.)
- These are the experimental factors that vary between samples

## Expected Output

The JSON file is saved to `tmp/<BIOPROJECT>_sra_metadata.json`:

```json
{
  "bioproject": "PRJNA1018599",
  "fetchDate": "2025-11-23T...",
  "source": "ENA+BioSample",
  "runCount": 24,
  "runs": [
    {
      "run_accession": "SRR26104233",
      "sample_accession": "SAMN37446236",
      "sample_alias": "GSM7789499",
      "library_layout": "PAIRED",
      "library_strategy": "RNA-Seq",
      "instrument_model": "Illumina HiSeq 2500",
      "read_count": 11294392,
      "scientific_name": "Rhipicephalus microplus",
      "sample_attributes": {
        "infection": "Babesia infected",
        "tissue": "hemolymph",
        "cell_type": "hemocyte"
      }
    }
  ]
}
```

## Manual CSV Fallback

If the API fetch fails, explain to the curator user that they should manually access the SRA Run Selector as follows:

1. Go to: `https://www.ncbi.nlm.nih.gov/Traces/study/?acc=<BIOPROJECT>`
2. Click the **Metadata** button to download `SraRunTable.csv`
3. Save as: `tmp/<BIOPROJECT>_SraRunTable.csv` in your curation workspace directory (which should also be the current directory)
4. Tell Claude "I downloaded the CSV for you here: tmp/<BIOPROJECT>_SraRunTable.csv"

Claude will rerun the script and parse the CSV file.

---

## Optional: Fetch MINiML for GEO-linked Datasets

If the BioProject is linked to a GEO Series (GSE), fetch the MINiML XML for richer descriptions:

```bash
node scripts/fetch-miniml.js <BIOPROJECT>
```

### Output

- **Success**: Prints GSE accession, saves `tmp/<GSE>_family.xml`
- **No GEO link**: Prints `NO_GEO_LINK` (this is OK - many datasets aren't in GEO)

The MINiML file contains:
- Series title and summary
- Sample descriptions and characteristics
- Platform information
- Contributor details

---

## Optional: Extract PDF Data

**STOP: Do NOT read the PDF or pdf-extraction.md yourself.** Both will consume your context.

**You MUST use the Task tool** with these parameters:
- **subagent_type**: `general-purpose`
- **prompt**: `Read the PDF at tmp/<BIOPROJECT>_article.pdf and extract structured data following the instructions and schema in resources/pdf-extraction.md. On success only, save to tmp/<BIOPROJECT>_pdf_extracted.json. Return a brief summary: strandedness, author count, and whether Author Contributions section was found.`

**Output (on success):** `tmp/<BIOPROJECT>_pdf_extracted.json`

## Troubleshooting

- **No runs found**: The BioProject may not have public SRA data yet
- **Missing sample attributes**: Not all submitters provide custom attributes
- **API timeout**: NCBI may be slow; the script uses rate limiting
