"""Direction fields: which way the brush travels at each point of the canvas.

A field is any callable that takes points (..., 2) in px (x right, y down) and returns unit
direction vectors (..., 2). Strokes only care about orientation: v and -v are the same brush
direction, so stroke tracing and `combine` treat them as equal. Angles are in degrees,
0 = to the right, 90 = straight down.

    sky = fields.combine((fields.vortex((1400, 380), twist=0.8), 1.0), (fields.noise(300, cv.rng), 0.35))
    land = fields.contour(land_mask)
    flow = fields.combine((sky, sky_mask), (land, 1 - sky_mask))
"""

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates


def _unit(v):
    n = np.hypot(v[..., 0], v[..., 1])[..., None]
    return np.where(n > 1e-12, v / np.maximum(n, 1e-12), [1.0, 0.0])


def _field(fn):
    """Turn fn(points (N, 2)) -> vectors (N, 2) into a field over (..., 2) returning unit vectors."""
    def field(points):
        p = np.asarray(points, np.float64)
        return _unit(fn(p.reshape(-1, 2))).reshape(p.shape)
    return field


def sample(grid, points):
    """Bilinear sample of an HxW array at points (N, 2) (x, y in px); clamps at the borders."""
    p = np.asarray(points, np.float64).reshape(-1, 2)
    return map_coordinates(np.asarray(grid, np.float32), [p[:, 1], p[:, 0]], order=1, mode="nearest")


def constant(angle):
    """Every stroke runs at `angle` degrees."""
    a = np.radians(angle)
    v = np.array([np.cos(a), np.sin(a)])
    return _field(lambda p: np.broadcast_to(v, p.shape))


def radial(center):
    """Strokes radiate from `center` (x, y), like light rays or a sunburst."""
    c = np.asarray(center, np.float64)
    return _field(lambda p: p - c)


def vortex(center, twist=0.8):
    """Strokes swirl clockwise around `center` (x, y).

    twist: 1 = pure rotation (concentric circles), 0 = straight in toward the center; in between the
    strokes form spiral arms (0.6 runs 36 degrees off the circle). Negative twist spirals outward,
    which draws the mirror-image spiral.
    """
    c = np.asarray(center, np.float64)
    beta = (1 - min(abs(twist), 1.0)) * np.pi / 2
    inward = 1.0 if twist >= 0 else -1.0

    def fn(p):
        r = _unit(p - c)
        tangent = np.stack([-r[:, 1], r[:, 0]], axis=1)
        return np.cos(beta) * tangent - inward * np.sin(beta) * r
    return _field(fn)


def noise(scale, rng, angle=0.0, spread=180.0, waves=24):
    """Smooth random flow whose direction changes over distances of about `scale` px.

    rng: a numpy Generator (pass cv.rng) or an int seed. Directions are angle + spread * n(x, y)
    with n a smooth unit-variance noise: spread=180 turns every way, spread=15 wavers around `angle`.
    """
    rng = np.random.default_rng(rng)
    k = 2.0 ** rng.uniform(-0.5, 0.5, waves) / scale
    th = rng.uniform(0, 2 * np.pi, waves)
    kx, ky, phase = k * np.cos(th), k * np.sin(th), rng.uniform(0, 2 * np.pi, waves)
    amp, a0, spr = np.sqrt(2 / waves), np.radians(angle), np.radians(spread)

    def fn(p):
        n = np.zeros(len(p))
        for i in range(waves):
            n += np.cos(p[:, 0] * kx[i] + p[:, 1] * ky[i] + phase[i])
        a = a0 + spr * amp * n
        return np.stack([np.cos(a), np.sin(a)], axis=1)
    return _field(fn)


def contour(mask, sigma=3.0):
    """Strokes run along the edges of `mask` and echo them inside and outside the shape.

    mask: HxW bool region or float image, or an HxWxC color image (e.g. a design: strokes then run
    along its color edges, perpendicular to the gradient). Near an edge the direction is its tangent
    (gradient of the mask smoothed by `sigma` px); elsewhere it copies the nearest edge.
    """
    m = np.asarray(mask, np.float32)
    m = gaussian_filter(m if m.ndim == 3 else m[..., None], (sigma, sigma, 0), mode="nearest")
    gy, gx = np.gradient(m, axis=(0, 1))
    rho = max(1.0, sigma)
    jxx, jyy, jxy = (gaussian_filter(a.sum(axis=-1), rho, mode="nearest") for a in (gx * gx, gy * gy, gx * gy))
    c2, s2 = jxx - jyy, 2 * jxy  # doubled angle of the gradient; the length is the edge strength
    strength = np.hypot(c2, s2)
    top = strength.max()
    if top <= 0:
        return constant(0)
    edge = strength > 0.02 * top
    if not edge.all():
        iy, ix = distance_transform_edt(~edge, return_indices=True, return_distances=False)
        c2, s2, strength = c2[iy, ix], s2[iy, ix], strength[iy, ix]
    # Soften the seams where the territories of two edges meet, then turn gradient into tangent.
    tc = -gaussian_filter(c2 / strength, 2 * sigma, mode="nearest")
    ts = -gaussian_filter(s2 / strength, 2 * sigma, mode="nearest")

    def fn(p):
        a = 0.5 * np.arctan2(sample(ts, p), sample(tc, p))
        return np.stack([np.cos(a), np.sin(a)], axis=1)
    return _field(fn)


def combine(*pairs):
    """Blend fields: combine((field, weight), ...).

    weight: a number, an HxW array sampled at the points (a region mask; soften it for a gradual
    hand-over) or a callable points (N, 2) -> (N,). Orientations are averaged as doubled angles, so
    opposite vectors reinforce rather than cancel and the blend has no seams; two fields at right
    angles with equal weight have no average, and the blend turns quickly there.
    """
    def fn(p):
        acc = np.zeros_like(p)
        for field, w in pairs:
            d = np.asarray(field(p), np.float64)
            acc += _weight(w, p)[:, None] * np.stack([d[:, 0] ** 2 - d[:, 1] ** 2, 2 * d[:, 0] * d[:, 1]], axis=1)
        a = 0.5 * np.arctan2(acc[:, 1], acc[:, 0])
        return np.stack([np.cos(a), np.sin(a)], axis=1)
    return _field(fn)


def _weight(w, p):
    if callable(w):
        return np.asarray(w(p), np.float64).reshape(-1)
    w = np.asarray(w, np.float64)
    return np.full(len(p), float(w)) if w.ndim == 0 else sample(w, p).astype(np.float64)
