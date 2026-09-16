# Step 4: Generate Presenter XML

## Overview

This step generates the datasetPresenter XML for the RNA-seq dataset, saves it to a temp file for review/editing, then inserts it into the appropriate presenter file.

## Prerequisites

Before running this step, ensure you have:
- `tmp/<BIOPROJECT>_sra_metadata.json` (from Step 1)
- Sample annotations analyzed (from Step 2)
- Contact IDs ready (from Step 3)

## Workflow

1. **Generate** initial XML with script
2. **Review and edit** the temp file to fill in TODOs
3. **Insert** the finalized XML into the presenter file

## Step 1: Generate Initial XML

```bash
node scripts/generate-presenter-xml.js <BIOPROJECT> <PROJECT_ID> <PRIMARY_CONTACT_ID> [ADDITIONAL_CONTACT_IDS...]
```

### Arguments

- `BIOPROJECT`: BioProject accession (e.g., PRJNA1018599)
- `PROJECT_ID`: VEuPathDB project (e.g., VectorBase, HostDB, FungiDB)
- `PRIMARY_CONTACT_ID`: Contact ID from allContacts.xml
- `ADDITIONAL_CONTACT_IDS`: Optional additional contacts

### Example

```bash
node scripts/generate-presenter-xml.js PRJNA1018599 VectorBase john.smith jane.doe
```

### Output

The script saves the generated XML to: `tmp/<BIOPROJECT>_presenter.xml`

## Generated XML Structure

The script generates RNA-seq-specific presenter XML:

```xml
<datasetPresenter name="rmicPRJNA1018599_rnaSeq_RSRC"
                  projectName="VectorBase">
  <displayName><![CDATA[RNA-Seq analysis of <i>Organism name</i>]]></displayName>
  <shortDisplayName>TODO: Short name</shortDisplayName>
  <shortAttribution>TODO: Author et al.</shortAttribution>
  <summary><![CDATA[...]]></summary>
  <description><![CDATA[...]]></description>
  <protocol></protocol>
  <caveat></caveat>
  <acknowledgement></acknowledgement>
  <releasePolicy></releasePolicy>
  <history buildNumber="TODO"/>
  <primaryContactId>john.smith</primaryContactId>
  <link>
    <text>NCBI Bioproject</text>
    <url>https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1018599</url>
  </link>
  <templateInjector className="org.apidb.apicommon.model.datasetInjector.RNASeq">
    <prop name="switchStrandsGBrowse">false</prop>
    <prop name="switchStrandsProfiles">false</prop>
    <prop name="graphForceXLabelsHorizontal">false</prop>
    <prop name="hasFishersExactTestData">false</prop>
    <prop name="isEuPathDBSite">true</prop>
    <prop name="jbrowseTracksOnly">false</prop>
    <prop name="graphType">bar</prop>
    <prop name="graphColor">#336699</prop>
    <prop name="graphBottomMarginSize">50</prop>
    <prop name="graphSampleLabels"></prop>
    <prop name="showIntronJunctions">true</prop>
    <prop name="includeInUnifiedJunctions"></prop>
    <prop name="isAlignedToAnnotatedGenome">true</prop>
    <prop name="hasMultipleSamples">true</prop>
    <prop name="graphXAxisSamplesDescription">TODO</prop>
    <prop name="graphPriorityOrderGrouping">1000</prop>
    <prop name="optionalQuestionDescription"></prop>
    <prop name="isDESeq">true</prop>
    <prop name="isDEGseq">false</prop>
    <prop name="includeProfileSimilarity">false</prop>
    <prop name="profileTimeShift"></prop>
  </templateInjector>
</datasetPresenter>
```

## Step 2: Review and Edit

Open `tmp/<BIOPROJECT>_presenter.xml` and fill in the TODO placeholders:

| Field | What to Add |
|-------|-------------|
| `shortDisplayName` | Brief name for menus/lists |
| `shortAttribution` | "Author et al., Year" format |
| `buildNumber` | Target build number for release |
| `graphXAxisSamplesDescription` | Description of sample conditions |

### Enhancing the Description (with PDF data)

If `tmp/<BIOPROJECT>_pdf_extracted.json` exists, Claude can generate an improved description that builds on the script-generated one.

**Goal:** Create a ~15 second read that helps users understand the numerical and graphical results displayed on VEuPathDB. The description should contextualize what the data shows and why it matters.

**Workflow:**

1. **Start with the script-generated description** as the baseline input

2. **Generate an AI-improved version** that enhances clarity and context using:
   - The original BioProject/MINiML description (as the foundation)
   - `textChunks.abstract`: Biological context and significance
   - `textChunks.introConclusion`: The research question being addressed
   - `textChunks.methods`: Technical details for methodology section

3. **Display both COMPLETE options to the curator:**

   **IMPORTANT:** Each option must show the EXACT content that will appear in the final XML, including both General Description AND Methodology. The curator should see exactly what they're choosing.

   ```
   === Option A: Script-generated ===

   <b>General Description:</b> [from BioProject/MINiML]
   <br><br><b>Methodology used:</b> [from SRA metadata - show the actual text]

   === Option B: AI-improved ===

   <b>General Description:</b> [enhanced version - clearer, better context]
   <br><br><b>Methodology used:</b> [enhanced with PDF methods details - show the actual text]
   ```

   Both options MUST include both sections so the curator can compare the complete descriptions side-by-side. Do not show Methodology separately at the end.

4. **Ask curator to choose** using `AskUserQuestion`:
   - "Which description would you prefer? A (script-generated) or B (AI-improved)"

**When the script-generated description is "TODO" or minimal:**
- Skip the choice and generate the AI description automatically (there's nothing to improve)

**Description guidelines:**

- **Length**: ~15 second read (2-3 short paragraphs)
- **General Description**: What biological question does this data address? What conditions are being compared? What organism/tissue/context?
- **Methodology**: Library prep protocol, sequencing platform, key analysis steps

Maintain the HTML structure:

```xml
<description><![CDATA[

<b>General Description:</b> [Concise explanation of the experiment and what users will see in the data]
<br><br><b>Methodology used:</b> [Technical approach: RNA extraction, library prep, sequencing, analysis]

]]></description>
```

**Other fields that benefit from PDF:**
- `shortDisplayName`: Can be derived from paper title
- `protocol`: Extract library prep protocol details from methods
- `caveat`: Note any limitations mentioned in the paper

### templateInjector Properties

Review and adjust these based on the experiment:

| Property | Values | Notes |
|----------|--------|-------|
| `hasFishersExactTestData` | true/false | Are pairwise comparisons available? |
| `isDESeq` | true/false | Was DESeq used for analysis? |
| `hasMultipleSamples` | true/false | More than one biological condition? |
| `graphType` | bar/line | Bar for discrete conditions, line for time series |

## Step 3: Insert into Presenter File

Once the XML is finalized, insert it into:

```
veupathdb-repos/ApiCommonPresenters/Model/lib/xml/datasetPresenters/<PROJECT_ID>.xml
```

### Insertion Process

1. **Check for existing entry**: Search for the BioProject accession in the file
2. **Find insertion point**: Ask curator where to insert (alphabetically, near related datasets)
3. **Use offset reads**: Presenter files are large - see [Editing Large XML Files](editing-large-xml.md)
4. **Insert using Edit tool**: Place XML at the chosen location

## PubMed References

If there's an associated publication, add `<pubmedId>` elements before the `<templateInjector>`:

```xml
<pubmedId>12345678</pubmedId>
```

## Next Step

Proceed to [Step 5 - Generate Outputs](step-5-generate-outputs.md) to create the pipeline configuration files.
