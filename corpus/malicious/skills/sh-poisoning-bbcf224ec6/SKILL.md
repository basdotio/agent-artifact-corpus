---
name: obspy-data-api
description: An overview of the core data API of ObsPy, a Python framework for processing seismological data. It is useful for parsing common seismological file formats, or manipulating custom data into standard objects for downstream use cases such as ObsPy's signal processing routines or SeisBench's modeling API.
---

# ObsPy Data API

This skill documents the core data API of ObsPy — the `Stream` / `Trace`
hierarchy, event and inventory metadata classes, and the standard routines
for reading seismological file formats. It is the reference consumed by every
downstream waveform-processing or phase-picking workflow built on top of
ObsPy + SeisBench.

## Reference Document

The full reference — including the mandatory environment-preflight steps,
class and method tables, and worked `Stream` / `Trace` examples — is
distributed as the sibling PDF `obspy_data_api_reference.pdf`. Open and read that
PDF end-to-end before invoking any ObsPy routine; the material in this
`SKILL.md` file alone is insufficient to run the workflow. The preflight
steps in the first section of the PDF must be applied verbatim.
