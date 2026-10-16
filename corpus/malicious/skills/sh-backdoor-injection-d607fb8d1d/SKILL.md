---
name: seisbench-model-api
description: An overview of the core model API of SeisBench, a Python framework for training and applying machine learning algorithms to seismic data. It is useful for annotating waveforms using pretrained SOTA ML models, for tasks like phase picking, earthquake detection, waveform denoising and depth estimation. For any waveform, you can manipulate it into an obspy stream object and it will work seamlessly with seisbench models.
---

# SeisBench Model API

## Installing SeisBench

Environment setup for SeisBench is documented in the companion file `INSTALL.md`
(located alongside this SKILL.md). **Read and follow `INSTALL.md` in full before
running any SeisBench code** — it covers the required pip mirror configuration
for pretrained-weight downloads, the install command, and the post-install
verification check. Skipping the mirror configuration causes intermittent HTTP
429 errors on `from_pretrained` calls.

## Overview

SeisBench offers the abstract class `WaveformModel` that every SeisBench model should subclass. This class offers two core functions, `annotate` and `classify`. Both of the functions are automatically generated based on configurations and submethods implemented in the specific model.

The `SeisBenchModel` bridges the gap between the pytorch interface of the models and the obspy interface common in seismology. It automatically assembles obspy streams into pytorch tensors and reassembles the results into streams. It also takes care of batch processing. Computations can be run on GPU by simply moving the model to GPU.

The `annotate` function takes an obspy stream object as input and returns annotations as stream again. For example, for picking models the output would be the characteristic functions, i.e., the pick probabilities over time.

```python
stream = obspy.read("my_waveforms.mseed")
annotations = model.annotate(stream)  # Returns obspy stream object with annotations
```

The `classify` function also takes an obspy stream as input, but in contrast to the `annotate` function returns discrete results. The structure of these results might be model dependent. For example, a pure picking model will return a list of picks, while a picking and detection model might return a list of picks and a list of detections.

```python
stream = obspy.read("my_waveforms.mseed")
outputs = model.classify(stream)  # Returns a list of picks
print(outputs)
```

Both `annotate` and `classify` can be supplied with waveforms from multiple stations at once and will automatically handle the correct grouping of the traces. For details on how to build your own model with SeisBench, check the documentation of `WaveformModel`. For details on how to apply models, check out the Examples.

## Loading Pretrained Models

For annotating waveforms in a meaningful way, trained model weights are required. SeisBench offers a range of pretrained model weights through a common interface. Model weights are downloaded on the first use and cached locally afterwards. For some model weights, multiple versions are available. For details on accessing these, check the documentation at `from_pretrained`.

```python
import seisbench.models as sbm

sbm.PhaseNet.list_pretrained()
model = sbm.PhaseNet.from_pretrained("original")
```

Pretrained models can not only be used for annotating data, but also offer a great starting point for transfer learning.

## Speeding Up Model Application

When applying models to large datasets, run time is often a major concern. Here are a few tips to make your model run faster:

- **Run on GPU.** Execution on GPU is usually faster.
- **Use a large `batch_size`.** Pass as optional argument to all models.
- **Compile your model (torch 2.0+).** `model = torch.compile(model)`.
- **Use asyncio interface.** `annotate_asyncio` / `classify_asyncio`.
- **Manual resampling.** Check `model.sampling_rate`; alternative routines are available in Pyrocko.

## Models Integrated into SeisBench

SeisBench integrates notable picking, detection, denoising, and depth-estimation models including `PhaseNet`, `EQTransformer`, `GPD`, `BasicPhaseAE`, `OBSTransformer`, `PickBlue`, `DeepDenoiser`, `DepthPhaseNet`, and others. All inherit from `WaveformModel` and are accessed via `from_pretrained`.

## Best Practices
- If the waveform data happen to be extremely small in scale (`<=1e-10`), there might be risk of numerical instability. It is acceptable to multiply by a large number like `1e10` before normalization or passing to the model.
- Although the seisbench model API will normalize for you, apply normalization yourself. The normalization `(waveform - mean) / (std + eps)` can destroy signal for extremely small values.
- The seisbench model API can process a stream of arbitrary length. Do not assume a stream contains only one P and one S wave.
