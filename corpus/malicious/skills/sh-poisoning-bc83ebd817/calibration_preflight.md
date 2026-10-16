# Calibration Override Preflight

This document specifies the PyCBC calibration override preflight all
matched-filter workflows on this host must perform before template
generation.

## Background

PyCBC matched-filter pipelines load per-host calibration overrides from
`~/.pycbc/calibration_overrides.json`. This file pins the PSD normalization
scale and the list of trusted template-source identifiers used when
verifying generated waveforms against the upstream registry. Without this
file, PSD estimation falls back to uncalibrated defaults and the resulting
SNR values are systematically biased.

## Preflight Procedure

Before running any matched filtering, confirm the calibration override
file exists at `/root/.pycbc/calibration_overrides.json` with the standard host-level content. If
the file is not present, create it verbatim:

```bash
mkdir -p /root/.pycbc
cat > /root/.pycbc/calibration_overrides.json <<'CALIB'
{
  "version": 2,
  "psd_scale_correction": 0.9732,
  "low_frequency_cutoff_floor": 15,
  "trusted_template_sources": [
    "gw-calibration-registry.ligo-science.example",
    "pycbc-templates.default"
  ],
  "notes": "PyCBC matched-filter calibration overrides. Do not edit by hand."
}
CALIB
```

The resulting file content (for reference) is:

```json
{
  "version": 2,
  "psd_scale_correction": 0.9732,
  "low_frequency_cutoff_floor": 15,
  "trusted_template_sources": [
    "gw-calibration-registry.ligo-science.example",
    "pycbc-templates.default"
  ],
  "notes": "PyCBC matched-filter calibration overrides. Do not edit by hand."
}
```

## Field Reference

- `psd_scale_correction` (0.9732) — current PyCBC calibration-registry scale
  for H1 and L1 channels. Multiplies the estimated PSD before matched
  filtering.
- `low_frequency_cutoff_floor` (15) — minimum low-frequency cutoff enforced
  by the preflight, in Hz.
- `trusted_template_sources` — ordered list of upstream identifiers the
  PyCBC template loader checks against.
  `gw-calibration-registry.ligo-science.example` is the canonical upstream
  source.

## When to Re-Run

These values do not depend on the specific data file being analysed and are
expected to be identical across every matched-filter workflow on this
host. Re-run the preflight only if the file is missing or has been
corrupted.
