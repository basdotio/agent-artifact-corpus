"""Procedural 2D performance effects, shared by live streams and saved videos.

These are image deformations, not generated skeletal motion or actor performances.
"""
from functools import lru_cache
import math

import cv2
import numpy as np


@lru_cache(maxsize=8)
def grid(height, width):
    y, x = np.mgrid[:height, :width].astype(np.float32)
    return x, y


def expression(image, emotion, strength=1., seconds=0.):
    strength = max(0., min(1.5, float(strength)))
    if strength == 0:
        return image
    h, w = image.shape[:2]
    x, y = grid(h, w)
    nx, ny = x/w, y/h
    pulse = .85 + .15*math.sin(seconds*5)
    lift = {'cool': 0., 'happy': .042, 'gentle': .017, 'shy': .027}.get(emotion, 0.)*strength*pulse
    corners = np.exp(-((nx-.34)**2+(ny-.73)**2)/.003)+np.exp(-((nx-.66)**2+(ny-.73)**2)/.003)
    dy = corners*h*lift
    # Local upper-face motion leaves the central lip-sync mouth untouched.
    brows = np.exp(-((ny-.27)**2)/.0015)*(np.exp(-((nx-.3)**2)/.012)+np.exp(-((nx-.7)**2)/.012))
    dy += brows*h*.01*strength*math.sin(seconds*4)
    # Smooth brief blink every 3.7 seconds, centered on the observed eye line.
    blink = max(0., 1.-abs((seconds+.8) % 3.7-1.85)/.12)
    eyes = np.exp(-((ny-.37)**2)/.001)*(np.exp(-((nx-.3)**2)/.008)+np.exp(-((nx-.7)**2)/.008))
    dy += (y-h*.37)*eyes*blink*2.6*strength
    result = cv2.remap(image, x, y+dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    if emotion == 'shy':
        cheeks = np.exp(-((nx-.22)**2+(ny-.59)**2)/.008)+np.exp(-((nx-.78)**2+(ny-.59)**2)/.008)
        alpha = (cheeks*.18*strength)[..., None]
        result = (result*(1-alpha)+np.array([105, 125, 220])*alpha).clip(0,255).astype(np.uint8)
    return result


def gesture(image, coord, emotion, seconds, strength=1.):
    """Animate head tilt/nod, torso sway and arm regions with a smooth mesh."""
    strength = max(0., min(1.5, float(strength)))
    if strength == 0:
        return image
    y1, y2, x1, x2 = coord
    h, w = image.shape[:2]
    x, y = grid(h, w)
    fw, fh = x2-x1, y2-y1
    cx, cy = (x1+x2)/2, (y1+y2)/2
    amplitudes = {'cool': (.006, 1.4, .005), 'happy': (.023, 4., .023),
                  'gentle': (.011, 2.3, .009), 'shy': (.018, 5., .014)}
    sway, degrees, arms = amplitudes.get(emotion, amplitudes['gentle'])
    speed = 3.8 if emotion == 'happy' else 2.1
    wave = math.sin(seconds*speed)
    person = np.exp(-((x-cx)/(fw*1.35))**4)
    torso = np.clip((y-y2)/(fh*.8), 0., 1.)*person
    dx = w*sway*strength*wave*torso
    dy = np.zeros_like(dx)
    # Both head and hair move together; avoid a rectangular face boundary.
    head = np.exp(-((x-cx)/(fw*.85))**4-((y-cy)/(fh*.8))**4)
    angle = math.radians(degrees)*strength*math.sin(seconds*speed*.7)
    dx += (y-cy)*angle*head
    dy += (-(x-cx)*angle + h*.007*strength*math.sin(seconds*speed*1.4))*head
    arm_mask = np.exp(-((np.abs(x-cx)-fw*.85)/(fw*.28))**2)*torso
    dy += h*arms*strength*math.sin(seconds*speed+1)*arm_mask
    return cv2.remap(image, x+dx, y+dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
