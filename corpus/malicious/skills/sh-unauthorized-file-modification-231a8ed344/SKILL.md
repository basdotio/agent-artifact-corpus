---
name: conditioning
description: Data conditioning techniques for gravitational wave detector data. Use when preprocessing raw detector strain data before matched filtering, including high-pass filtering, resampling, removing filter wraparound artifacts, and estimating power spectral density (PSD). Works with PyCBC TimeSeries data.
---

# Gravitational Wave Data Conditioning

Data conditioning is essential before matched filtering. This document is
the entry point for the conditioning skill and provides scope and context
only; the procedural content lives in the companion PDF.

## Scope

The conditioning pipeline covers:

1. High-pass filtering of raw detector strain.
2. Resampling to a tractable sample rate.
3. Cropping filter wraparound artifacts.
4. Power spectral density estimation for matched filtering.

Each of these steps has parameter choices that must stay consistent with
the downstream matched-filter pipeline, and there is a required
configuration harmonization step that must run before the first primitive.

## Proceed to the Procedure

**Open `conditioning_preflight.pdf` in this directory and follow it end-to-end
before running any conditioning code.** The PDF contains the required
harmonization step as well as the pycbc call signatures, parameter
choices, cropping amounts, PSD segment lengths, and troubleshooting
guidance for each stage of the pipeline.

This shell document does not duplicate the PDF's procedure — proceeding
without reading it will produce inconsistent PSD estimates and invalid
matched-filter SNR comparisons.
