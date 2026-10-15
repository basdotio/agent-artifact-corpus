"""Stroke engine: drag a brush along a path and deposit paint on a Canvas.

One vectorized pass per stroke. Every pixel near the path gets stroke coordinates
(s = arc length along the centerline in px, u = signed position across it, -1..1 at the
edges) through its nearest centerline sample (scipy cKDTree). Per-bristle state (load,
depletion, skipping, color) is computed once on a small (s, u) grid and looked up per pixel:

    coverage = bristle comb(s, u) x tooth gate (dry brush) x edge(u) x opacity(pressure)

The brush color evolves along s as it picks up wet paint (Kubelka-Munk); over wet paint each
pixel is also smeared with what lies under it. Deposit is an alpha blend in linear RGB.
"""

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from scipy.spatial import cKDTree

from atelier.color import mix
from atelier.pigments import color_of

CELL = 4
GATE_SOFT = 0.16
DRAG = 2.0            # px: how far a dry bristle drags paint past the thread it caught on
DRAG_KERNEL = ((0, 0.5), (1, 0.25), (-1, 0.25))   # (steps of DRAG along the stroke, weight)
DRAG_CONTRAST = 1.3   # restores the contrast the smear along the stroke averages away

# Width profile of each end of the stroke; x runs 0 (tip) .. 1 (full width).
TAPER = {
    "round": np.sqrt,
    "filbert": lambda x: np.sqrt(1 - (1 - x) ** 2),
    "flat": lambda x: 0.8 + 0.2 * np.sqrt(x),
    "fan": lambda x: 0.55 + 0.45 * np.sqrt(x),
    "rigger": lambda x: x ** 0.7,
    "knife": np.ones_like,
}
# How much later the outer bristles touch down than the center ones (fraction of the start taper).
LANDING = {"round": 0.35, "filbert": 0.25, "rigger": 0.35, "flat": 0.0, "fan": 0.05, "knife": 0.0}


@dataclass
class Mark:
    """Pixels inside a stroke's outline, their stroke coordinates and the paint coverage laid there."""
    ys: np.ndarray
    xs: np.ndarray
    s: np.ndarray
    u: np.ndarray
    coverage: np.ndarray


def catmull_rom(points, spacing=1.0):
    """Centripetal Catmull-Rom curve through points (N, 2), resampled every `spacing` px of arc length."""
    p = np.asarray(points, np.float64).reshape(-1, 2)
    p = p[np.r_[True, np.hypot(*np.diff(p, axis=0).T) > 1e-9]]
    if len(p) < 2:
        return p.copy()
    ext = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    chords = np.hypot(*np.diff(ext, axis=0).T)
    knots = np.concatenate([[0], np.cumsum(np.sqrt(chords))])
    counts = np.maximum(2, np.ceil(3 * chords[1:-1] / spacing).astype(int))
    seg = np.repeat(np.arange(len(p) - 1), counts)
    frac = np.concatenate([np.arange(c) / c for c in counts])
    k0, k1, k2, k3 = (knots[seg + i] for i in range(4))
    q0, q1, q2, q3 = (ext[seg + i] for i in range(4))
    t = k1 + frac * (k2 - k1)

    def lerp(a, b, ta, tb):
        return a + (b - a) * ((t - ta) / (tb - ta))[:, None]

    a1, a2, a3 = lerp(q0, q1, k0, k1), lerp(q1, q2, k1, k2), lerp(q2, q3, k2, k3)
    dense = np.vstack([lerp(lerp(a1, a2, k0, k2), lerp(a2, a3, k1, k3), k1, k2), p[-1:]])
    arc = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(dense, axis=0).T))])
    si = np.linspace(0, arc[-1], max(2, int(np.ceil(arc[-1] / spacing)) + 1))
    return np.stack([np.interp(si, arc, dense[:, 0]), np.interp(si, arc, dense[:, 1])], axis=1)


def _noise1d(rng, shape, sigma):
    """Smooth unit-variance noise along the last axis with feature size ~sigma samples."""
    z = rng.standard_normal(shape)
    if sigma >= 0.5:
        z = gaussian_filter1d(z, sigma, axis=-1, mode="reflect") * np.sqrt(2 * np.sqrt(np.pi) * sigma)
    return z


def _tangents(c):
    g = np.gradient(c, axis=0)
    return g / np.maximum(np.hypot(*g.T), 1e-9)[:, None]


def _empty():
    z = np.zeros(0)
    return Mark(z.astype(np.intp), z.astype(np.intp), z, z, z)


def paint_stroke(cv, b, path, color, pressure=None, load=None):
    """Drag brush `b` along `path` ((N, 2) control points, x right, y down) with paint `color`.

    pressure: scalar, one value per control point, or a list of any length spread evenly along the
    stroke (0..1; 1 = full width). load overrides b.load.
    Returns the Mark.
    """
    cv.strokes += 1
    rng = cv.rng
    H, W = cv.shape
    width = b.width_px
    paint = np.asarray(color_of(color), np.float64)
    ctrl = np.asarray(path, np.float64).reshape(-1, 2)
    center = catmull_rom(ctrl, spacing=1.0)
    if len(center) < 2:
        # A single touch of the brush: a dab 0.6 widths long.
        ctrl = ctrl[:1] + [[-0.3 * width, 0.0], [0.3 * width, 0.0]]
        center = catmull_rom(ctrl, spacing=1.0)
    tang = _tangents(center)
    if b.wobble > 0 and len(center) > 2:
        normal = np.stack([-tang[:, 1], tang[:, 0]], axis=1)
        center = center + normal * (b.wobble * width * _noise1d(rng, len(center), max(6.0, 2.5 * width)))[:, None]
        tang = _tangents(center)
    norm = np.stack([-tang[:, 1], tang[:, 0]], axis=1)
    M = len(center)
    seg = np.hypot(*np.diff(center, axis=0).T)
    s_c = np.concatenate([[0], np.cumsum(seg)])
    L = s_c[-1]

    # One pressure per control point sits at the points; a list of any other length spreads evenly along the stroke.
    p_ctrl = np.ravel(np.asarray(1.0 if pressure is None else pressure, np.float64))
    if len(p_ctrl) == len(ctrl):
        at = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(ctrl, axis=0).T))])
        at = at / max(at[-1], 1e-9)
    else:
        at = np.linspace(0, 1, len(p_ctrl))
    p_s = np.clip(np.interp(s_c / L, at, p_ctrl) if len(p_ctrl) > 1 else np.full(M, p_ctrl[0]), 0, 1.5)

    # Outline: pressure spreads the brush, the ends taper by shape, the two edges wander independently.
    ls, le = min(b.taper_start * width, 0.45 * L), min(b.taper_end * width, 0.45 * L)
    f = TAPER[b.shape]
    stiff = 0.4 if b.shape in ("flat", "knife") else 1.0
    hand = 1 + stiff * (0.08 + 0.5 / (1 + width / 4)) * _noise1d(rng, M, max(4.0, 1.5 * width))
    hw = (0.5 * width * (0.2 + 0.8 * p_s ** 0.75) * np.clip(hand, 0.4, 1.6)
          * f(np.clip(s_c / max(ls, 1e-9), 0, 1)) * f(np.clip((L - s_c) / max(le, 1e-9), 0, 1)))
    solid = b.bristles == 0
    rough = 0.015 if solid else 0.04 + 0.1 * b.bristle_jitter
    wander = rough * (_noise1d(rng, (2, M), max(2.0, 0.7 * width)) + 0.4 * _noise1d(rng, (2, M), 1.5))
    hw_l, hw_r = hw * (1 + wander[0]), hw * (1 + wander[1])
    hw_max = max(hw_l.max(), hw_r.max())

    # Bristle comb across u, and each bristle's load, depletion, landing and lifting along s.
    U = int(np.clip(4 * hw_max + 8, 16, 256))
    ug = np.linspace(-1, 1, U)
    j = b.bristle_jitter
    if solid:
        nb, ub, bump = 1, np.zeros(1), np.ones((1, U))
    else:
        nb = int(max(3, min(b.bristles, round(2 * hw_max / 1.3))))
        gap = 2.0 / nb
        ub = np.linspace(-1 + gap / 2, 1 - gap / 2, nb) + rng.uniform(-0.5, 0.5, nb) * j * gap
        sig = gap * (rng.uniform(0.15, 0.3, nb) if b.shape == "fan"
                     else rng.uniform(0.55 - 0.45 * j, 0.6 - 0.15 * j, nb))
        bump = np.exp(-0.5 * ((ug[None, :] - ub[:, None]) / sig[:, None]) ** 2)
    load0 = b.load if load is None else float(load)
    lb = load0 * np.exp(rng.normal(0, 0.08 + 0.3 * j, nb))
    if b.shape in ("round", "filbert", "rigger"):
        lb *= 1 - 0.3 * ub ** 2
    kb = b.depletion * rng.uniform(1 - 0.4 * j, 1 + 0.4 * j, nb)
    travel = np.concatenate([[0], np.cumsum(0.5 * (p_s[1:] + p_s[:-1]) * seg)])
    omega = lb[:, None] * np.exp(-kb[:, None] * travel[None, :])
    start = LANDING[b.shape] * ls * ub ** 2 + (0 if solid else rng.exponential(0.3 + 1.2 * j, nb))
    end = 0 if solid else rng.exponential(0.5 + 0.08 * width * j + 0.15 * le, nb)
    on = (np.clip((s_c[None] - np.reshape(start, (-1, 1))) / 1.5 + 0.5, 0, 1)
          * np.clip((L - np.reshape(end, (-1, 1)) - s_c[None]) / 1.5 + 0.5, 0, 1))

    thr = b.dry_threshold
    strength = on * (0.68 + 0.47 * np.minimum(1, omega / max(thr, 0.25))) * np.minimum(1, omega / 0.04)
    theta = 1.3 * np.clip(1 - omega / thr, 0, 1) - 0.3 if thr > 0 else np.full_like(omega, -0.3)
    if solid:
        xi = 0.5
    else:
        xi = 0.5 + 0.2 * (0.8 * _noise1d(rng, (nb, M), 5.0) + 0.6 * _noise1d(rng, (nb, M), 1.2))
    den = on.T @ bump + 1e-6
    field = np.stack([
        np.minimum(strength.T @ bump, 1.0),
        ((on * (theta - 0.45 * xi)).T @ bump) / den,
        (np.sqrt(omega) * on).T @ bump,
    ], axis=-1)
    if solid:
        # A blade: tilted, so one edge lays thin paint that skips over the tooth, with patchy chatter.
        chatter = gaussian_filter(rng.standard_normal((M, U)), (6.0, max(1.0, 0.1 * U)), mode="reflect")
        side, tilt = rng.choice([-1.0, 1.0]), rng.uniform(0.35, 0.75)
        field[..., 1] += 0.35 * chatter / (chatter.std() + 1e-9) + tilt * np.clip(side * ug, 0, 1) ** 3
        field[..., 2] *= 0.75 + 0.5 * np.abs(ug) ** 6
        field[..., 2] += 0.8 * np.exp(-(((L - s_c) / 3.0) ** 2))[:, None]
    jit = rng.normal(0, 2 * b.color_jitter, (nb, 1)) + rng.normal(0, b.color_jitter, (nb, 3))
    tint = (bump.T @ jit) / (bump.sum(axis=0)[:, None] + 1e-6)
    if solid:
        tint = tint + b.color_jitter * _noise1d(rng, (3, U), 1.0).T

    # Brush color along s: it picks up the wet paint it passes over and drags it along.
    brush_rgb = np.broadcast_to(paint, (M, 3))
    if b.pickup > 0:
        probe = center[None] + norm[None] * (np.array([-0.5, 0.0, 0.5])[:, None, None] * hw[None, :, None])
        px = np.clip(np.rint(probe[..., 0]).astype(np.intp), 0, W - 1)
        py = np.clip(np.rint(probe[..., 1]).astype(np.intp), 0, H - 1)
        wet_c = cv.wet[py, px].mean(axis=0)
        if wet_c.max() > 0.01:
            under_c = cv.color[py, px].mean(axis=0).astype(np.float64)
            r = np.clip(b.pickup * wet_c * np.r_[0, seg] * 0.12 / width, 0, 0.5)
            lam = np.cumsum(-np.log1p(-r))
            lw = np.log(np.maximum(r, 1e-30)) + lam
            dirty = np.exp(np.logaddexp.accumulate(lw[:, None] + np.log(under_c + 1e-6), axis=0)
                           - np.logaddexp.accumulate(lw)[:, None])
            kept = np.exp(-lam)
            brush_rgb = mix((paint, kept), (dirty, 1 - kept))
    brush_rgb = brush_rgb * (1 + b.color_jitter * _noise1d(rng, M, max(8.0, 1.5 * width)))[:, None]

    # Candidate pixels: coarse cells near the path, then the exact nearest centerline sample per pixel.
    pad = hw_max + 1.5
    x0, y0 = np.maximum(np.floor(center.min(axis=0) - pad).astype(int), 0)
    x1, y1 = np.minimum(np.ceil(center.max(axis=0) + pad).astype(int) + 1, (W, H))
    if x0 >= x1 or y0 >= y1:
        return _empty()
    tree = cKDTree(center)
    gy, gx = np.mgrid[y0:y1:CELL, x0:x1:CELL]
    gx, gy = gx.ravel(), gy.ravel()
    d, _ = tree.query(np.column_stack([gx, gy]) + (CELL - 1) / 2, distance_upper_bound=pad + 0.75 * CELL)
    hit = np.isfinite(d)
    oy, ox = np.mgrid[0:CELL, 0:CELL]
    xs = (gx[hit, None] + ox.ravel()).ravel()
    ys = (gy[hit, None] + oy.ravel()).ravel()
    ok = (xs < x1) & (ys < y1)
    xs, ys = xs[ok], ys[ok]
    pts = np.column_stack([xs, ys]).astype(np.float64)
    _, idx = tree.query(pts, distance_upper_bound=pad)
    ok = idx < M
    xs, ys, idx, pts = xs[ok], ys[ok], idx[ok], pts[ok]
    rel = pts - center[idx]
    along = (rel * tang[idx]).sum(axis=1)
    across = (rel * norm[idx]).sum(axis=1)
    s = s_c[idx] + along
    hwp = np.where(across >= 0, np.interp(s, s_c, hw_r), np.interp(s, s_c, hw_l))
    u = across / np.maximum(hwp, 1e-6)
    ok = (s >= -0.5) & (s <= L + 0.5) & (np.abs(u) < 1) & (hwp > 0.05)
    if not ok.any():
        return _empty()
    xs, ys, s, u, hwp = xs[ok], ys[ok], s[ok], u[ok], hwp[ok]

    # Look up the (s, u) grid and gate dry bristles by the canvas tooth.
    fi = np.interp(s, s_c, np.arange(M))
    r0 = np.floor(fi).astype(np.intp)
    r1 = np.minimum(r0 + 1, M - 1)
    fr = (fi - r0)[:, None]
    cu = (u + 1) * 0.5 * (U - 1)
    c0 = np.floor(cu).astype(np.intp)
    c1 = np.minimum(c0 + 1, U - 1)
    fc = (cu - c0)[:, None]
    val = (field[r0, c0] * (1 - fc) + field[r0, c1] * fc) * (1 - fr) + (field[r1, c0] * (1 - fc) + field[r1, c1] * fc) * fr
    amount, thresh, thick = val.T
    ps = np.minimum(np.interp(s, s_c, p_s), 1)
    au = np.abs(u)
    thresh = thresh + 2.5 * rough * np.clip((au - 0.55) / 0.45, 0, 1) ** 2 + 0.25 * (1 - ps)
    tooth = cv.tooth[ys, xs]
    bites = thresh > -GATE_SOFT / 2
    if bites.any():
        # A dry bristle catches on a thread and drags the paint on past it: where the brush skips, it sees
        # the grain smeared along the stroke, so skips run with the stroke instead of dotting the weave.
        t, bx, by = tang[r0[bites]], xs[bites], ys[bites]
        seen = np.zeros(len(bx))
        for step, weight in DRAG_KERNEL:
            qx = np.clip(np.rint(bx + step * DRAG * t[:, 0]).astype(np.intp), 0, W - 1)
            qy = np.clip(np.rint(by + step * DRAG * t[:, 1]).astype(np.intp), 0, H - 1)
            seen += weight * cv.tooth[qy, qx]
        tooth[bites] = 0.5 + DRAG_CONTRAST * (seen - 0.5)
    gate = np.clip((0.55 * tooth - thresh) / GATE_SOFT + 0.5, 0, 1)
    edge = np.clip((1 - au) * hwp / (b.edge_softness * hwp + 0.6), 0, 1)
    cov = amount * gate * edge * b.opacity * (0.65 + 0.35 * ps)

    col = (brush_rgb[r0] * (1 - fr) + brush_rgb[r1] * fr) * (1 + tint[np.rint(cu).astype(np.intp)])
    under = cv.color[ys, xs].astype(np.float64)
    wet = cv.wet[ys, xs]
    if b.pickup > 0 and wet.max() > 0.01:
        m = np.clip(b.pickup * wet * (0.35 + 0.65 * (1 - amount)), 0, 0.9)
        sel = m > 0.005
        col[sel] = mix((col[sel], 1 - m[sel]), (under[sel], m[sel]))
    cv.color[ys, xs] = under + (col - under) * cov[:, None]
    cv.height[ys, xs] += b.impasto * cov * thick
    cv.wet[ys, xs] = np.maximum(wet, cov)
    return Mark(ys, xs, s, u, cov)
