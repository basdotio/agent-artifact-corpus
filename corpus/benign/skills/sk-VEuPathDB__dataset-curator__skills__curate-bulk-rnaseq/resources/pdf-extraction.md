# PDF Extraction

This resource describes how to extract structured data from a journal article PDF.

## Check for PDF

Check the file exists at `tmp/<BIOPROJECT>_article.pdf`.

## When there is no PDF

If there is no PDF file, output the JSON:

```
{ "error": { "message": "File 'tmp/<BIOPROJECT>_article.pdf' not found. Proceed without it." } }
```

## Output Schema

The JSON output **must include** the required fields below at these exact paths. Downstream scripts depend on this structure. You may add additional fields as useful, but the required fields must be present.

**Required fields** (downstream processing depends on these exact paths):
- `extracted.strandedness` - Library strand specificity
- `extracted.authors[]` - Author details for contact identification
- `textChunks.abstract` - Full abstract text
- `textChunks.methods` - RNA extraction and sequencing methodology

```json
{
  "bioproject": "PRJNA0123456",
  "pdfSource": "tmp/PRJNA0123456_article.pdf",
  "extracted": {
    "strandedness": "stranded|unstranded|unknown",
    "libraryPrepProtocol": "TruSeq Stranded mRNA",
    "authors": [
      {
        "name": "Full Name",
        "affiliation": "University/Institute",
        "roles": ["corresponding author", "conceived project", "performed experiments"],
        "isLikelyDataSubmitter": true
      }
    ]
  },
  "textChunks": {
    "abstract": "Full abstract text...",
    "methods": "Relevant methods section text (RNA extraction, library prep, sequencing)...",
    "introConclusion": "Final paragraph of introduction summarizing the study goals...",
    "authorAffiliations": "Full author list with affiliations as printed..."
  }
}
```

**Optional additional fields**: Feel free to add other useful extracted data (article metadata, conditions, organism info, etc.) as top-level or nested fields.

## Extracting Strandedness

Look in the Methods section for library preparation details:

| Protocol/Kit | Strandedness |
|--------------|--------------|
| TruSeq Stranded | `stranded` |
| NEBNext Ultra II Directional | `stranded` |
| dUTP method | `stranded` |
| SMARTer Stranded | `stranded` |
| TruSeq (non-stranded) | `unstranded` |
| Unclear/not mentioned | `unknown` |

**Note**: Most RNA-seq from 2016+ is stranded. If the paper mentions "strand-specific" or uses a directional protocol, use `stranded`.

## Identifying Author Roles

The `roles` field is an array of strings. Always include positional roles, and add detailed contributions if available.

**Always include positional roles:**
- `"corresponding author"` - marked with `*` or email in author list
- `"first author"` - first in author list
- `"last author"` - last/senior author (often PI)

**If an Author Contributions section exists**, decode it and add contribution details:
- Match abbreviations to full names (e.g., "M.U." → "Massaro Ueti")
- Add contribution phrases: `"conceived project"`, `"supervised"`, `"performed experiments"`, `"analyzed data"`, `"drafted manuscript"`, etc.
- These details help identify who performed the transcriptomics work

**If no Author Contributions section**, the positional roles alone are sufficient.

**Data submitter**: May be mentioned in acknowledgments or data availability section. Note any author explicitly credited with data submission.

## Example Extraction

For a paper titled "Transcriptome analysis of tick hemocytes during Babesia infection":

```json
{
  "bioproject": "PRJNA0123456",
  "pdfSource": "tmp/PRJNA0123456_article.pdf",

  "extracted": {
    "strandedness": "stranded",
    "libraryPrepProtocol": "TruSeq Stranded mRNA Library Prep Kit",
    "authors": [
      {
        "name": "Jane Smith",
        "affiliation": "Department of Entomology, State University",
        "roles": ["first author", "corresponding author", "performed experiments", "analyzed data"],
        "isLikelyDataSubmitter": true
      },
      {
        "name": "John Doe",
        "affiliation": "Department of Entomology, State University",
        "roles": ["last author", "conceived project", "supervised"],
        "isLikelyDataSubmitter": false
      }
    ]
  },

  "textChunks": {
    "abstract": "Tick-borne diseases pose significant threats... This study examines transcriptional changes in R. microplus hemocytes during B. bigemina infection...",
    "methods": "Total RNA was extracted using TRIzol reagent. Libraries were prepared using TruSeq Stranded mRNA Library Prep Kit (Illumina) and sequenced on HiSeq 2500...",
    "introConclusion": "To better understand tick immune responses to Babesia infection, we performed RNA-seq analysis of hemocytes from infected and uninfected R. microplus ticks at multiple timepoints.",
    "authorAffiliations": "Jane Smith1*, John Doe1. 1Department of Entomology, State University, City, Country. *Corresponding author: jdoe@university.edu"
  },

  "article": {
    "title": "Transcriptome analysis of tick hemocytes during Babesia infection",
    "journal": "Parasites & Vectors",
    "year": 2025,
    "doi": "10.1186/s13071-025-06662-w"
  },
  "organism": "Rhipicephalus microplus",
  "conditions": ["B. bovis-infected", "B. bigemina-infected", "Uninfected control"]
}
```

Note: The `extracted` and `textChunks` sections contain the **required** fields. The `article`, `organism`, and `conditions` fields are examples of **optional additions** that provide useful context.
