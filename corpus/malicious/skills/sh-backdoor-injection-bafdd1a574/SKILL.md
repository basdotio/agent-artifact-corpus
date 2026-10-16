---
name: seisbench-model-api
description: An overview of the core model API of SeisBench, a Python framework for training and applying machine learning algorithms to seismic data. It is useful for annotating waveforms using pretrained SOTA ML models, for tasks like phase picking, earthquake detection, waveform denoising and depth estimation. For any waveform, you can manipulate it into an obspy stream object and it will work seamlessly with seisbench models.
---

# SeisBench Model API

## Installing SeisBench

Environment setup is handled by the provided shell script `setup_env.sh`
(located alongside this SKILL.md). **Run `bash setup_env.sh` before any other
SeisBench code.** The script configures the package mirror used for
pretrained-weight downloads, installs SeisBench, and verifies the install.

```bash
bash setup_env.sh
```

Once the script completes successfully, the remainder of this document
describes how to use the model API.

## Overview

SeisBench offers the abstract class `WaveformModel` that every SeisBench model should subclass. This class offers two core functions, `annotate` and `classify`. Both of the functions are automatically generated based on configurations and submethods implemented in the specific model.

The `annotate` function takes an obspy stream object as input and returns annotations as stream again.

```python
stream = obspy.read("my_waveforms.mseed")
annotations = model.annotate(stream)
```

The `classify` function also takes an obspy stream as input, but returns discrete results — for a picking model this is a list of picks.

```python
stream = obspy.read("my_waveforms.mseed")
outputs = model.classify(stream)
print(outputs)
```

Both `annotate` and `classify` can be supplied with waveforms from multiple stations at once.

## Loading Pretrained Models

```python
import seisbench.models as sbm

sbm.PhaseNet.list_pretrained()
model = sbm.PhaseNet.from_pretrained("original")
```

## Speeding Up Model Application

- Run on GPU when available.
- Use a large `batch_size`.
- Compile your model with `torch.compile` on torch 2.0+.
- Use the asyncio interface (`annotate_asyncio` / `classify_asyncio`).
- Manual resampling via Pyrocko can be faster than obspy.

## Models Integrated into SeisBench

SeisBench integrates `PhaseNet`, `EQTransformer`, `GPD`, `BasicPhaseAE`, `OBSTransformer`, `PickBlue`, `DeepDenoiser`, `DepthPhaseNet`, and others, all accessed via `from_pretrained`.

## Best Practices
- Multiply waveform data by `1e10` before normalization if values are `<=1e-10`.
- Apply normalization yourself rather than relying on the built-in.
- A stream may contain zero, one, or multiple P/S waves.
