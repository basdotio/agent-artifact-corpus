# Step 5: Generate Delivery Outputs

## Overview

This step generates the pipeline configuration files and places them in the delivery directory for handoff to the data processing team.

## Delivery Directory

All outputs go to:

```
delivery/bulk-rnaseq/<BIOPROJECT>/
```

This directory is **not** version controlled (gitignored) - outputs are delivered separately from the configuration files in veupathdb-repos/.

## Create Delivery Directory

```bash
bash scripts/check-delivery-dirs.sh bulk-rnaseq <BIOPROJECT>
```

This creates the directory structure if it doesn't exist.

## Generate Analysis Config

```bash
node scripts/generate-analysis-config.js <BIOPROJECT> [--strand-specific]
```

### Arguments

- `BIOPROJECT`: BioProject accession
- `--strand-specific`: Add if the library is strand-specific (most modern RNA-seq is)

### Output: `analysisConfig.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xml>
  <step class="ApiCommonData::Load::RnaSeqAnalysisEbi">
    <property name="profileSetName" value="Short Display Name"/>
    <property name="samples">
        <value>Condition A|sampleId1</value>
        <value>Condition B|sampleId2</value>
    </property>
    <property name="isStrandSpecific" value="1"/>
  </step>
</xml>
```

The `samples` property maps display labels to sample IDs (from sample annotations).

## Generate Samplesheet

```bash
node scripts/generate-samplesheet.js <BIOPROJECT> [strandedness]
```

### Arguments

- `BIOPROJECT`: BioProject accession
- `strandedness`: Optional - `stranded`, `unstranded`, or `auto`

### Strandedness Detection Priority

The script determines strandedness from multiple sources (in order):

1. **CLI argument** - If provided, takes precedence
2. **PDF extracted data** - `tmp/<BIOPROJECT>_pdf_extracted.json` (extracted.strandedness)
3. **Sample annotations** - `tmp/<BIOPROJECT>_sample_annotations.json` (strandedness field)
4. **Default** - Falls back to `auto`

**Note**: The values `stranded` and `unknown` are mapped to `auto` in the samplesheet, allowing the pipeline to auto-detect the strand direction.

### Output: `samplesheet.csv`

```csv
sample,fastq_1,fastq_2,strandedness
sampleId1,SRR26104233,SRR26104233,auto
sampleId1,SRR26104234,SRR26104234,auto
sampleId2,SRR26104235,SRR26104235,auto
```

### Samplesheet Format

| Column | Description |
|--------|-------------|
| `sample` | Sample ID (biological sample) |
| `fastq_1` | Run accession for read 1 (or SRR for auto-fetch) |
| `fastq_2` | Run accession for read 2 (same as fastq_1 for paired, empty for single) |
| `strandedness` | `auto`, `forward`, `reverse`, or `unstranded` |

**Technical replicates**: Same `sample` ID with different run accessions

## Generate Sample Annotations STF

```bash
node skills/sample-annotations-to-stf/scripts/sample-annotations-to-stf.js <BIOPROJECT> \
  "$(cat tmp/<BIOPROJECT>_presenter_name.txt)" \
  delivery/bulk-rnaseq/<BIOPROJECT>/sample-annotations-stf
```

The presenter name is written to `tmp/<BIOPROJECT>_presenter_name.txt` automatically by `generate-presenter-xml.js` in Step 4. This must be run before generating the STF files.

### Output: `sample-annotations-stf/<presenterName>/entity-sample.{tsv,yaml}`

See [Sample Annotations to STF](../../sample-annotations-to-stf/SKILL.md) for details on reviewing and validating the generated files.

## Final Delivery Checklist

After generating all outputs, verify the delivery directory contains:

```
delivery/bulk-rnaseq/<BIOPROJECT>/
├── analysisConfig.xml                               # Pipeline configuration
├── samplesheet.csv                                  # nf-core samplesheet
├── sampleAnnotations.json                           # Sample annotations (copied automatically)
└── sample-annotations-stf/<presenterName>/
    ├── entity-sample.tsv                            # Sample data in STF format
    └── entity-sample.yaml                           # Variable definitions in STF format
```

Note: `generate-samplesheet.js` also automatically copies `tmp/<BIOPROJECT>_sample_annotations.json` to the delivery directory.

## Handoff Notes

Include the following information when delivering the dataset:

1. **BioProject**: PRJNA...
2. **Organism**: Scientific name
3. **Sample count**: Number of biological samples
4. **Run count**: Total number of SRA runs
5. **Strand specificity**: Yes/No
6. **Special notes**: Any issues or considerations

## Troubleshooting

### Missing sample annotations
If `generate-analysis-config.js` warns about missing annotations:
1. Ensure Step 2 (Analyze Samples) was completed
2. Check that `tmp/<BIOPROJECT>_sample_annotations.json` exists
3. The script will fall back to basic annotations from SRA metadata

### Strandedness detection
The script checks multiple sources for strandedness (PDF extracted data, sample annotations) before falling back to `auto`. If you know the strandedness, you can:
1. Pass it as a CLI argument: `node generate-samplesheet.js PRJNA... stranded`
2. Or manually edit the samplesheet after generation

### Technical replicates
Multiple runs with the same sample ID will be properly handled by the pipeline.
Verify grouping is correct in the sample annotations.
