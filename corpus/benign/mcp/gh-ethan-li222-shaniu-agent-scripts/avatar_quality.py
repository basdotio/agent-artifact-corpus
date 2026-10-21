"""Conservative lower-face compositing for original TV still avatars."""
from functools import lru_cache

import cv2
import numpy as np


@lru_cache(maxsize=16)
def mouth_mask(height, width):
    y, x = np.mgrid[:height, :width].astype(np.float32)
    # Keep eyes, nose bridge and outer contour exactly as photographed.
    distance = ((x/width-.5)/.43)**4 + ((y/height-.76)/.235)**4
    alpha = np.clip((1-distance)/.45, 0, 1)
    alpha[y/height < .525] = 0
    return alpha[..., None]


def blend_mouth(original, predicted):
    """Blend a generated mouth while retaining original identity and skin edges.

    Inputs are BGR uint8 face crops. Returns a new image; caches stay immutable.
    """
    h, w = original.shape[:2]
    predicted = cv2.resize(predicted, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    source = original.astype(np.float32)
    alpha = mouth_mask(h, w)
    # Match skin brightness around the feathered edge, not the changing lips.
    ring = (alpha[..., 0] > .05) & (alpha[..., 0] < .45)
    if np.any(ring):
        offset = np.clip(np.median(source[ring]-predicted[ring], axis=0), -15, 15)
        predicted = np.clip(predicted+offset, 0, 255)
    return np.rint(source*(1-alpha)+predicted*alpha).clip(0, 255).astype(np.uint8)
