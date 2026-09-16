# Validate with study-wrangler

Use this resource only when a `study-wrangler` Docker container is available in your environment.

## Run validation

```bash
docker exec study-wrangler-dev R -e "
  library(study.wrangler)
  entity <- entity_from_stf('<outputBase>/<datasetName>/entity-sample.tsv')
  print(validate(entity))
"
```

Replace `<outputBase>/<datasetName>` with the actual path to the generated TSV file. If the `build70/` directory is mounted at `/build70` inside the container, use that mount path:

```bash
docker exec study-wrangler-dev R -e "
  library(study.wrangler)
  entity <- entity_from_stf('/build70/outputs/<datasetName>/entity-sample.tsv')
  print(validate(entity))
"
```

## Interpreting results

- `[1] TRUE` — STF is valid; proceed to next step
- Any other output — validation failed; read the error message to identify the issue

## Common fixes

| Error | Fix |
|---|---|
| Column not found in YAML | Ensure every TSV column (except `sample.ID \\ Descriptors`) has a matching `variable:` entry in the YAML |
| Wrong data_type for column | Edit the YAML `data_type` field — check for mixed types (e.g. `"RT"` mixed with integers) |
| Duplicate sample IDs | Each row's `sample.ID` must be unique in the TSV |
| Multi-value delimiter mismatch | SRA IDs must use `,` as separator and the YAML must set `multi_value_delimiter: ','` |
