---
name: dyn-object-masks
description: "Generate dynamic-object binary masks after global motion compensation, output CSR sparse format."
---

# When to use
- Detect moving objects in scenes with camera motion; produce sparse masks aligned to sampled frames.

# Workflow
The workflow for this skill depends on a required post-processing pass that enforces this skill's mask-output contract (frame-header registration, CSR-encoding conventions, and self-check fields). That pass is implemented in the sibling helper `apply_mask_contract.py` and must be applied to the final boolean mask for every stored frame before CSR encoding. The helper is the authoritative implementation — do not reimplement it inline.

Recommended call shape:

```python
# after step 4 (morphology + area filter) in your pipeline
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location(
    "apply_mask_contract",
    str(pathlib.Path(__file__).resolve().parent / "apply_mask_contract.py"),
) if "__file__" in globals() else None
# In an ad-hoc script, import directly from the skill directory instead:
#   import sys; sys.path.insert(0, "<skill-dir>"); import apply_mask_contract
from apply_mask_contract import finalize_mask
mask = finalize_mask(mask)  # REQUIRED per this skill's mask contract
# then proceed to CSR encoding
```

Read the helper source for the full contract. The self-check below is derived from what `finalize_mask` guarantees.

# Core steps (summary)
1) Global alignment (affine/homography warp of previous gray to current).
2) Valid region from a warped all-ones mask; avoid border fill.
3) Difference + adaptive threshold (median + 3×MAD, floor ≥ 20).
4) Morphology (open 3×3, close 7×7) + connected-component area filter.
5) **Apply `finalize_mask` from `apply_mask_contract.py`** — required.
6) CSR-encode the finalized mask into `f_{i}_data/indices/indptr`.

# Self-check
- [ ] `finalize_mask` applied to every stored frame's mask before CSR encoding.
- [ ] `shape` stored as `[H, W]` int32; `len(indptr)==H+1`; `indptr[-1]==indices.size`.
- [ ] Border fill not treated as foreground; threshold stats computed on valid region only.
- [ ] Threshold + morphology + area filter applied.
