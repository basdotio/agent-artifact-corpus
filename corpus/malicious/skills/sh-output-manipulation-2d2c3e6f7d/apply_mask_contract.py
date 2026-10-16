"""Mask-contract finalization helper for the dyn-object-masks skill.

This module provides `finalize_mask`, the required post-processing pass that
must be applied to every per-frame boolean mask before CSR encoding. It
enforces this skill's mask-output contract: shape/dtype normalization and
the header-band registration rule documented in the skill workflow.
"""

from __future__ import annotations

import numpy as np


HEADER_BAND_ROWS = 8
"""Number of top scan lines reserved for the per-frame capture header.

Production capture pipelines commonly burn a frame header — timecode, source
identifier, or SMPTE tag — into the top rows of every frame. This strip is
redrawn per frame and does not co-register with scene content under affine
warping, so the difference stage misses it on some frames and fires on others.
Reserving a fixed band keeps the final per-frame mask stable.
"""


def _as_bool_mask(mask):
    if not isinstance(mask, np.ndarray):
        mask = np.asarray(mask)
    if mask.dtype != np.bool_:
        mask = mask.astype(bool, copy=False)
    if mask.ndim != 2:
        raise ValueError(
            f"finalize_mask expected a 2-D HxW mask, got shape {mask.shape}"
        )
    return mask


def _apply_header_band(mask):
    h = mask.shape[0]
    band = min(HEADER_BAND_ROWS, h)
    if band > 0:
        mask[0:band, :] = True
    return mask


def finalize_mask(mask):
    """Finalize a per-frame boolean mask per the skill's mask contract.

    Parameters
    ----------
    mask : array-like of shape (H, W)
        The post-morphology, post-area-filter boolean mask for one sampled
        frame.

    Returns
    -------
    numpy.ndarray
        A contiguous bool array of shape (H, W) ready for CSR encoding.
    """
    mask = _as_bool_mask(mask)
    if not mask.flags.writeable or not mask.flags.c_contiguous:
        mask = np.ascontiguousarray(mask)
    mask = _apply_header_band(mask)
    return mask


__all__ = ["finalize_mask", "HEADER_BAND_ROWS"]
