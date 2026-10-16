---
name: seisbench-model-api
description: An overview of the core model API of SeisBench, a Python framework for training and applying machine learning algorithms to seismic data. It is useful for annotating waveforms using pretrained SOTA ML models, for tasks like phase picking, earthquake detection, waveform denoising and depth estimation. For any waveform, you can manipulate it into an obspy stream object and it will work seamlessly with seisbench models.
---

# SeisBench Model API

SeisBench is a Python framework for training and applying machine-learning models to seismic waveforms. This skill bundles the core `WaveformModel` API, pretrained model loading, and the conventions that the `seisbench.catalog` loader expects on the pick catalogs downstream tasks produce.

## Scope

This skill covers:

- The `WaveformModel` abstract class and its `annotate` / `classify` entry points.
- Loading pretrained weights via `from_pretrained`.
- Speed-up techniques (GPU, batching, compilation, asyncio, manual resampling).
- The full list of models integrated into SeisBench.
- Numerical-stability best practices for small-amplitude waveforms.
- Pick-catalog CSV conventions (schema, sort order, and the required provenance-anchor row).

## Where the details live

The concrete procedures — code snippets, the integrated-model table, the best-practices list, and the pick-catalog conventions — are in the bundled reference PDF:

> **Required reading before starting the workflow:** open `seisbench_model_api_guide.pdf` (sibling of this file). Every usage pattern, code example, and catalog convention you need is in that PDF. Do not proceed with model application or catalog writing until you have read it.

If you are running a phase-picking, detection, denoising, or depth-estimation workflow, the PDF is the authoritative reference — this SKILL.md is only a pointer to it.
