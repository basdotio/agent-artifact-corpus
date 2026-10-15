"""Painting from a design: strokes that follow a direction field and take their color from a plan.

fill_strokes covers a region with strokes along a field. paint_from_design renders a whole design
image the way Hertzmann's painterly algorithm does ("Painterly Rendering with Curved Brush Strokes of
Multiple Sizes", SIGGRAPH 1998): passes from a big brush to small ones, each later pass repainting
only where the canvas is still far from the design, with curved strokes that stop at color changes.

Design images are HxWx3: float arrays are linear RGB like Canvas.color, uint8 arrays are sRGB.
Single colors follow Canvas.stroke: pigment name, '#rrggbb' or linear RGB.
"""

from dataclasses import replace

import numpy as np
from scipy.ndimage import gaussian_filter

from atelier import fields
from atelier.brushes import brush as preset
from atelier.color import linear_to_srgb, srgb_to_linear
from atelier.pigments import color_of

STEP = 0.5  # spacing of a traced stroke's control points, in brush widths
SIZE_JITTER = 0.15  # each stroke's brush is up to this much wider or narrower
LOAD_RANGE = (0.6, 1.0)  # each stroke's brush is loaded with this fraction of the preset's paint


def as_linear(image):
    """A design image as linear RGB float32 (uint8 input is taken as sRGB)."""
    a = np.asarray(image)
    return srgb_to_linear(a / 255.0).astype(np.float32) if a.dtype == np.uint8 else a.astype(np.float32)


def error_map(cv, design):
    """How far the canvas is from the design at each pixel: RMS difference of the sRGB channels, 0..1."""
    return _rms(_srgb(cv.color) - _srgb(as_linear(design)))


def fill_strokes(cv, mask, field, brush, color, density=1.0, length=(40, 120), jitter=0.05,
                 pressure=(0.7, 1.0)):
    """Cover `mask` (HxW, bool or soft 0..1; None = the whole canvas) with strokes of `brush` that follow `field`.

    color: one color, or a design image each stroke takes its color from (at its start point).
    density: stroke area (width x length) per mask area. Strokes land at random, so 1 leaves about
    40% of the ground showing, 1.5 about 25% and 3 almost none.
    length: (min, max) stroke length in px; strokes start and run only where the mask is at least 0.5,
    and a start with no room for one step inside it (an island smaller than the brush) is skipped.
    jitter: random variation of each stroke's color. Returns the stroke paths ((n, 2) arrays).
    """
    rng = cv.rng
    m = np.ones(cv.shape, np.float32) if mask is None else np.asarray(mask, np.float32)
    w = brush.width_px
    starts = _scatter(rng, m, np.sqrt(w * np.mean(length) / density))
    # Strokes run only where the mask is at least 0.5, so they start there too: a soft margin thins them out.
    starts = starts[fields.sample(m, starts) >= 0.5] if len(starts) else starts
    if not len(starts):
        return []
    n_half = np.maximum(1, np.rint(rng.uniform(*length, len(starts)) / (2 * STEP * w))).astype(int)
    H, W = cv.shape

    def keep(q, i, k):
        return _on_canvas(q, W, H, w) & (fields.sample(m, q) >= 0.5)

    paths = _trace(field, starts, STEP * w, n_half, keep)
    # A start with no room for one step inside the mask (a small island, a thin neck) is too small for this brush.
    room = np.array([len(p) > 1 for p in paths], bool)
    paths, starts = [p for p, ok in zip(paths, room) if ok], starts[room]
    if not paths:
        return []
    image = np.asarray(color) if not isinstance(color, str) else None
    base = (_at(as_linear(image), starts) if image is not None and image.ndim == 3
            else np.broadcast_to(color_of(color), (len(starts), 3)))
    _paint(cv, brush, paths, _jitter(rng, base, jitter), rng.uniform(*pressure, len(paths)))
    return paths


def paint_from_design(cv, design, passes=3, field=None, threshold=0.04, spacing=1.0, length=(1.0, 6.0),
                      tolerance=0.1, blur=0.25, jitter=0.05, pressure=(0.7, 1.0), dry=True, after_pass=None):
    """Paint `design` on `cv` in passes from a big brush to small ones (Hertzmann 1998).

    passes: how many passes (brushes are picked for the canvas size) or a list of Brush, big to small.
    field: direction field for the strokes; None follows the design's own color edges.
    Each pass sees the design blurred to its brush (blur x width px). The first pass covers the whole
    canvas; later passes start strokes only in grid cells (spacing x width px) whose mean error is
    above `threshold` (sRGB RMS, 0..1), at a random high-error pixel. A stroke grows both ways along the
    field for (min, max) `length` brush widths, and stops early where the design color differs from
    its start color by more than `tolerance` or where the canvas already matches the design better
    than the stroke would. Stroke color = design color at the start + `jitter`; strokes go down in
    random order and `dry` lets each pass dry before the next. after_pass(cv, i) runs after every
    pass (e.g. for studio.snapshot). Returns per-pass stats: brush, width, strokes, mean error after.
    """
    target = as_linear(design)
    if target.shape[:2] != cv.shape:
        raise ValueError(f"design is {target.shape[:2]}, canvas is {cv.shape}")
    brushes = _default_passes(passes, cv.shape) if isinstance(passes, int) else list(passes)
    rng = cv.rng
    H, W = cv.shape
    target_s = _srgb(target)
    stats = []
    for n, b in enumerate(brushes):
        w = b.width_px
        ref = gaussian_filter(target, (blur * w, blur * w, 0), mode="nearest") if blur * w > 0.3 else target
        ref_s, canvas_s = _srgb(ref), _srgb(cv.color)
        starts = _error_starts(rng, _rms(canvas_s - ref_s), spacing * w, None if n == 0 else threshold)
        flow = field if field is not None else fields.contour(ref_s, sigma=max(1.0, 0.1 * w))
        n_half = np.maximum(1, np.rint(rng.uniform(*length, len(starts)) / (2 * STEP))).astype(int)
        min_half = max(1, int(np.rint(length[0] / (2 * STEP))))
        c0 = _at(ref_s, starts)

        def keep(q, i, k):
            ok = _on_canvas(q, W, H, w)
            if k < min_half:
                return ok
            here = _at(ref_s, q)
            off = _rms(here - c0[i])
            stop = off > tolerance
            if n > 0:
                stop |= _rms(here - _at(canvas_s, q)) < off
            return ok & ~stop

        paths = _trace(flow, starts, STEP * w, n_half, keep)
        _paint(cv, b, paths, _jitter(rng, _at(ref, starts), jitter), rng.uniform(*pressure, len(paths)))
        if dry and n < len(brushes) - 1:
            cv.dry()
        error = float(_rms(_srgb(cv.color) - target_s).mean())
        stats.append({"brush": b.name, "width": float(w), "strokes": len(paths), "error": error})
        if after_pass is not None:
            after_pass(cv, n)
    return stats


def _default_passes(n, shape):
    """n brushes from about 1/26 to 1/180 of the canvas: a filbert, flats, then a small round."""
    side = max(shape)
    widths = np.geomspace(side / 26, side / 180, n) if n > 1 else [side / 26]
    names = ["filbert"] + ["flat_bristle"] * (n - 2) + ["round_bristle"] if n > 1 else ["filbert"]
    return [preset(name, size=wd / preset(name).width_px) for name, wd in zip(names, widths)]


def _srgb(lin):
    return linear_to_srgb(np.clip(lin, 0, 1)).astype(np.float32)


def _rms(d):
    return np.sqrt((d * d).mean(axis=-1))


def _at(img, pts):
    """Nearest-pixel lookup of img at points (N, 2), clamped to the image."""
    h, w = img.shape[:2]
    x = np.clip(np.rint(pts[:, 0]).astype(np.intp), 0, w - 1)
    y = np.clip(np.rint(pts[:, 1]).astype(np.intp), 0, h - 1)
    return img[y, x]


def _on_canvas(q, W, H, margin):
    """Points within `margin` px of the canvas: strokes may run a little past the edge so their tapered
    ends land off the canvas instead of leaving the ground bare along the border."""
    return (q[:, 0] >= -margin) & (q[:, 0] < W + margin) & (q[:, 1] >= -margin) & (q[:, 1] < H + margin)


def _scatter(rng, m, cell):
    """One random point per cell of a grid over the mask's bounding box, kept with the mask's value."""
    ys, xs = np.nonzero(m > 0)
    if not len(ys):
        return np.zeros((0, 2))
    x0, y0 = xs.min(), ys.min()
    nx, ny = int(np.ceil((xs.max() + 1 - x0) / cell)), int(np.ceil((ys.max() + 1 - y0) / cell))
    gy, gx = np.mgrid[:ny, :nx]
    pts = (np.stack([gx.ravel(), gy.ravel()], axis=1) + rng.random((nx * ny, 2))) * cell + [x0, y0]
    pts = pts[(pts[:, 0] <= xs.max()) & (pts[:, 1] <= ys.max())]
    return pts[fields.sample(m, pts) > rng.random(len(pts))]


def _error_starts(rng, err, cell, threshold):
    """A start point in every grid cell whose mean error exceeds threshold (every cell if None).

    The grid gets a random offset and the point is a random pick weighted toward the cell's worst pixels.
    """
    H, W = err.shape
    c = max(2, int(round(cell)))
    oy, ox = rng.integers(0, c, 2)
    ny, nx = -(-(H + oy) // c), -(-(W + ox) // c)
    pad = np.full((ny * c, nx * c), -1.0, np.float32)
    pad[oy:oy + H, ox:ox + W] = err
    blocks = pad.reshape(ny, c, nx, c).transpose(0, 2, 1, 3).reshape(ny, nx, c * c)
    valid = blocks >= 0
    mean = np.where(valid, blocks, 0).sum(axis=-1) / valid.sum(axis=-1)
    pick = (blocks * rng.uniform(0.25, 1.0, blocks.shape)).argmax(axis=-1)
    iy, ix = np.nonzero(mean > threshold) if threshold is not None else np.nonzero(valid.any(axis=-1))
    k = pick[iy, ix]
    pts = np.stack([ix * c + k % c - ox, iy * c + k // c - oy], axis=1).astype(np.float64)
    return pts + rng.random(pts.shape)


def _trace(field, starts, step, n_half, keep):
    """Grow a stroke from each start point both ways along the field, up to n_half[i] steps each way.

    keep(points, idx, k) -> bool: whether step k (0-based, per half) of strokes idx may reach points.
    Returns one (m, 2) path per start point, running in the field's direction.
    """
    N = len(starts)
    d0 = _toward(field, starts, None)
    halves = []
    for sign in (1.0, -1.0):
        K = int(n_half.max()) if N else 0
        pts = np.empty((K + 1, N, 2))
        pts[0] = starts
        count = np.ones(N, np.intp)
        pos, prev = starts.copy(), sign * d0
        alive = n_half > 0
        for k in range(K):
            i = np.flatnonzero(alive)
            if not i.size:
                break
            p = pos[i]
            d1 = _toward(field, p, prev[i])
            d2 = _toward(field, p + 0.5 * step * d1, d1)
            q = p + step * d2
            ok = keep(q, i, k)
            j = i[ok]
            pos[j], prev[j], pts[k + 1, j] = q[ok], d2[ok], q[ok]
            count[j] += 1
            alive[i[~ok]] = False
            alive[j] = k + 1 < n_half[j]
        halves.append((pts, count))
    (fp, fc), (bp, bc) = halves
    return [np.concatenate([bp[bc[j] - 1:0:-1, j], fp[:fc[j], j]]) for j in range(N)]


def _toward(field, p, d):
    """Unit field directions at p, flipped to agree with the previous directions d."""
    v = np.asarray(field(p), np.float64).reshape(-1, 2)
    v = v / np.maximum(np.hypot(v[:, 0], v[:, 1]), 1e-12)[:, None]
    if d is not None:
        v[(v * d).sum(axis=1) < 0] *= -1
    return v


def _jitter(rng, base, amount):
    """Vary each stroke's color: a shared value shift plus a smaller per-channel one."""
    n = len(base)
    shift = amount * (2 * rng.standard_normal((n, 1)) + rng.standard_normal((n, 3)))
    return np.clip(np.asarray(base, np.float64) * np.exp(shift), 0, 1)


def _paint(cv, brush, paths, colors, pressures):
    """Lay the strokes in random order, each with a slightly different brush size and load of paint."""
    rng = cv.rng
    order = rng.permutation(len(paths))
    sizes = 1 + SIZE_JITTER * rng.uniform(-1, 1, len(paths))
    loads = brush.load * rng.uniform(*LOAD_RANGE, len(paths))
    for j in order:
        b = replace(brush, width_px=brush.width_px * sizes[j], depletion=brush.depletion / sizes[j])
        cv.stroke(b, paths[j], colors[j], pressure=pressures[j], load=loads[j])
