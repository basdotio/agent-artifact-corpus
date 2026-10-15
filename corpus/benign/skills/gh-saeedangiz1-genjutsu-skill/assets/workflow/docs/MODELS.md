# Models and runtime

All neural inference in the default path is hosted. No weight downloads are included.

| Stage | Provider/model | Configuration |
|---|---|---|
| Vocal separation | Replicate `cjwbw/demucs` | `htdemucs`, WAV; version `25a173108cff36ef9f80f854c162d01df9e6528be175794b81158fa03836d953` |
| Depth, default | [lucataco/depth-anything-video](https://replicate.com/lucataco/depth-anything-video) | latest version/schema resolved at run time; exact returned colors |
| Depth alternative | [chenxwh/depth-any-video](https://replicate.com/chenxwh/depth-any-video) | explicitly selected alternative model |
| Depth alternative | [Video-Depth-Anything Space](https://huggingface.co/spaces/depth-anything/Video-Depth-Anything) | public GPU quota/availability; optional HF_TOKEN |
| Segmentation | [lucataco/sam3-video](https://replicate.com/lucataco/sam3-video) | pinned version `408f82fc20c300aac5d61d2e34ddb34cd0181e810e9f609d250aed14d5f81269`; `video`, `prompt`, `mask_only=true`, `return_zip=true` |
| Generation | Enhancor Seedance 2.5 | Edit or multi_reference; draft then approved 1080p |
| Pitch | Rubber Band CLI | +3 semitones, time ratio 1 |
| Video/audio IO | PyAV / FFmpeg libraries | normalization, compositing, AAC input vocals, original audio packet remux |

The pinned SAM and Demucs versions and the depth model schema were verified through authenticated Replicate API reads on 2026-10-06. If a model becomes unavailable, inspect its current schema before changing the adapter. [Replicate HTTP API](https://replicate.com/docs/reference/http).

The [SAM3-Video Hugging Face Space](https://huggingface.co/spaces/linoyts/SAM3-Video) was an earlier exploration; it is not the active raw-mask implementation. Never describe a green visualization overlay as a raw mask. Public Spaces may change their Gradio API. An RGB segmentation retry is a deliberate repair, not a different depth color treatment.

`requirements.txt` records versions from the development environment. Setup installs them into a clean venv; the package's local tests are also runnable using a compatible existing environment. Hosted availability, price and access are account-dependent; no free-inference claim is made. Local self-hosting of model weights is not configured here.
