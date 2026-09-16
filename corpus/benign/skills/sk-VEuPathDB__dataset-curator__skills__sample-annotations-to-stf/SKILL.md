---
name: sample-annotations-to-stf
description: Convert VEuPathDB sample annotations JSON to STF format (TSV + YAML entity files) for use with study-wrangler
---

# Sample Annotations to STF

Converts `tmp/<BIOPROJECT>_sample_annotations.json` to a pair of STF files for a sample entity:
- `<outputDir>/<datasetName>/entity-sample.tsv` — tab-separated sample data
- `<outputDir>/<datasetName>/entity-sample.yaml` — variable definitions

## Input Format

The annotations JSON must follow the current schema, with `factors` as an object:

```json
{
  "bioproject": "PRJNAXXXXXX",
  "profileSetName": "Short description of the experiment",
  "samples": [
    {
      "sampleId": "SAMN...",
      "label": "human-readable label",
      "runs": ["SRR..."],
      "factors": { "timepoint": "24", "infection": "infected" }
    }
  ],
  "factors": {
    "timepoint": {
      "displayName": "timepoint",
      "definition": "Time elapsed after treatment",
      "unit": "hour"
    },
    "infection": {
      "displayName": "infection status",
      "definition": "Whether samples were exposed to a pathogen or left as untreated controls"
    }
  }
}
```

`strandedness` is not used by this script and may be omitted.

## Step 1: Run the conversion script

```bash
node skills/sample-annotations-to-stf/scripts/sample-annotations-to-stf.js <BIOPROJECT> <datasetName> [outputBase]
```

`outputBase` defaults to `outputs` if omitted.

**Output:** `<outputBase>/<datasetName>/entity-sample.{tsv,yaml}`

## Step 2: Review the YAML variable types

The script infers `data_type` and `data_shape` from actual factor values using these rules:

| Values | data_type | data_shape |
|---|---|---|
| All integers | `integer` | `continuous` |
| All numbers (non-integer) | `number` | `continuous` |
| All ISO-8601 dates (`YYYY-MM-DD`) | `date` | `continuous` |
| Otherwise | `string` | `categorical` |

Check each factor variable in the generated YAML and correct any mis-inferred types by editing the file directly.

## Step 3: Validate (optional)

If a `study-wrangler` Docker container is available, load the detailed validation instructions:

[Validate with study-wrangler](resources/validate-with-study-wrangler.md)

## Scripts

- `scripts/sample-annotations-to-stf.js` — converts annotations JSON to STF TSV + YAML
