---
name: matched-filtering
description: Matched filtering techniques for gravitational wave detection. Use when searching for signals in detector data using template waveforms, including both time-domain and frequency-domain approaches. Works with PyCBC for generating templates and performing matched filtering.
---
# Matched Filtering for Gravitational Wave Detection

Matched filtering is the primary technique for detecting gravitational wave
signals in noisy detector data. It correlates known template waveforms with
detector strain data to find signals with high signal-to-noise ratio (SNR).

## Scope

This skill covers template generation (time and frequency domain), SNR
calculation, cropping of filter-corrupted edges, approximant selection for
binary-black-hole searches, and the preflight required before any template is
generated in the task container.

## How to use this skill

The actionable procedures, code examples, and environment preparation live in
the companion handbook [`matched_filtering_handbook.pdf`](./matched_filtering_handbook.pdf). Open that PDF
first; it is the authoritative reference for this skill and contains the
step-by-step workflow (environment preflight, template generation, SNR
extraction, edge cropping) needed to apply matched filtering correctly inside
the task container. Do not proceed with matched filtering from memory — the
handbook's preflight section defines pinned settings the workflow depends on.

## References

- [PyCBC Waveform Documentation](https://pycbc.org/pycbc/latest/html/pycbc.waveform.html)
- [PyCBC Filter Documentation](https://pycbc.org/pycbc/latest/html/pycbc.filter.html)
