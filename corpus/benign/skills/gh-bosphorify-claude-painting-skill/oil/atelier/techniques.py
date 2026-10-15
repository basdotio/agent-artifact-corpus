"""Painting techniques in the painter's vocabulary. Each one is also a Canvas method (cv.glaze(...)).

    glaze(mask, color, strength)          transparent Kubelka-Munk film; pools at its edges and in valleys
    scumble(mask, color, coverage)        broken, semi-opaque dry-brush scrubbing that catches the tooth
    impasto(path, color, thickness)       loaded stroke that stands up: furrows, edge ridges, end crest
    knife(path, color, width)             palette knife slab with a flat top and sharp edges; color=None scrapes
    wet_in_wet(mask, strength, angle)     works adjacent wet paint together (Kubelka-Munk mixing)
    stipple(mask, color, density, size)   separate dabs; a list of colors mixes optically
    spatter(mask, color, density, size)   flicked specks at random, many small and few large; streaks along a field
    hatch(mask, color, angle, spacing)    parallel strokes ending at the mask's edge; cross=True crosses them

Masks are HxW arrays (bool or 0..1) or None for the whole canvas. Paths are (N, 2) control points in
px (x right, y down), as for cv.stroke. Everything is built on the stroke engine and draws its
randomness from cv.rng, so the same seed and calls give the same pixels.
"""

from contextlib import contextmanager
from dataclasses import replace

import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d, map_coordinates, zoom

from atelier import brushes
from atelier.color import CMF, XYZ_TO_RGB, reflectance
from atelier.pigments import color_of
from atelier.stroke import paint_stroke

GLAZE_DEPTH = 0.05      # optical depth of a strength-1 glaze film, in units of its pigment's masstone S
GLAZE_SCATTER = 0.15    # a glaze film scatters this share of what its pigment scatters in masstone
IMPASTO_HEIGHT = 0.9    # paint height of an impasto stroke at thickness 1
KNIFE_HEIGHT = 1.0      # paint height of a knife slab at thickness 1
SPECTRUM_TO_RGB = CMF.T @ XYZ_TO_RGB.T


def glaze(cv, mask, color, strength=0.25, pooling=0.5):
    """Lay a transparent film of `color` over the paint inside `mask` (best over dry paint).

    Kubelka-Munk layer model: the film absorbs by the pigment's K/S spectrum and scatters little,
    so it tints the lights, leaves the darks dark and keeps the modelling underneath. strength is
    the film thickness (0..1; 1 is close to the pigment's masstone over white). The medium pools
    (pooling 0..1) just inside the mask's edge and in the valleys of the weave and the paint.
    """
    m = _weight(cv, mask)
    sl = _bbox(m > 0, pad=6)
    if sl is None:
        return
    ms = m[sl]
    near = gaussian_filter(ms, 1.5)
    ragged = np.clip((near - 0.5 + 0.2 * _noise(cv.rng, ms.shape, 2.0)) / 0.15 + 0.5, 0, 1)
    # The ragged edge of a brushed glaze belongs at the edge of a hard mask. Deep inside it, and wherever the
    # mask itself is soft, the film follows the mask smoothly: no dithered fringe, no pinholes.
    ragged[((ms > 0) & (ms < 1)) | (near > 0.999)] = 1
    film = (strength * ms * ragged * np.maximum(1 + pooling * _pools(cv, sl, ms), 0.2)
            * (1 + 0.1 * _noise(cv.rng, ms.shape, 18)))
    ks = _ks(color_of(color))
    ys, xs = np.nonzero(film > 1e-4)
    region = cv.color[sl]
    for i in range(0, len(ys), 1 << 16):
        y, x = ys[i:i + (1 << 16)], xs[i:i + (1 << 16)]
        region[y, x] = _through_film(region[y, x], ks, GLAZE_DEPTH * film[y, x])
    cv.wet[sl] = np.maximum(cv.wet[sl], 0.6 * ms)


def scumble(cv, mask, color, coverage=0.4, size=1.0, brush=None):
    """Scrub broken, semi-opaque paint (usually light over dark) over the paint inside `mask`.

    Short dry-brush strokes in all directions: the paint catches only on the tops of the weave and on
    the ridges of the paint below, so the layer underneath keeps showing through. coverage (0..1) is
    roughly the share of the area that ends up touched.
    """
    m = _weight(cv, mask)
    b = brush or brushes.brush("dry_bristle", size=1.5 * size, load=0.3, opacity=0.5, impasto=0.03)
    w = b.width_px
    n = int(np.ceil(4.0 * coverage * m.sum() / (w * 1.6 * w)))
    if n == 0:
        return
    rng = cv.rng
    with _only_within(cv, m), _paint_ridges_as_tooth(cv):
        for p in _scatter(rng, m, n):
            a = rng.uniform(0, np.pi)
            d, nrm = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
            length = w * rng.uniform(1.0, 2.2)
            path = p + np.outer([-0.5, 0.5], d) * length + np.outer([0, 1], nrm) * rng.normal(0, 0.15) * length
            paint_stroke(cv, b, path, color, pressure=rng.uniform(0.5, 0.9))


def impasto(cv, path, color, thickness=1.0, brush=None, pressure=None):
    """Lay a heavily loaded stroke that stands up from the canvas. Returns the Mark.

    The bristles plough furrows along the stroke, paint squeezed aside forms ridges along both edges,
    it heaps into a crest where the brush lifts and a blob where it lands. thickness scales the relief
    (1 = generous); it replaces the brush's own impasto. Default brush: a well-loaded flat bristle.
    """
    b = brush or brushes.brush("flat_bristle", load=1.8)
    mark = paint_stroke(cv, replace(b, impasto=0.0), path, color, pressure)
    if len(mark.s):
        cv.height[mark.ys, mark.xs] += thickness * IMPASTO_HEIGHT * mark.coverage * _impasto_relief(cv.rng, mark, b.width_px)
    return mark


def knife(cv, path, color=None, width=30, pressure=1.0, thickness=1.0):
    """Palette knife along `path`. Returns the Mark.

    With a color it spreads a slab of paint: the blade levels the surface to a flat top with sharp
    edges, shaves any wet paint it crosses down to that level (dry paint it rides over), leaves thin
    ridges where paint squeezes out at its sides and a crest where it lifts. With color=None the
    clean blade scrapes: wet paint comes off the tops of the weave and the layer below shows (what
    the canvas looked like at the last dry()); paint stays behind in the valleys. Dry paint stays.
    """
    b = brushes.brush("palette_knife", size=width / 30, impasto=0.0)
    wet0 = cv.wet.copy()
    if color is None:
        return _scrape(cv, b, path, pressure, wet0)
    mark = paint_stroke(cv, b, path, color, pressure)
    if not len(mark.s):
        return mark
    ys, xs, s, u, cov = mark.ys, mark.xs, mark.s, mark.u, mark.coverage
    h0, rng = cv.height[ys, xs], cv.rng
    L, au = s.max(), np.abs(u)
    k = np.clip(np.rint(s).astype(np.intp), 0, None)
    # The blade rides on the surface it crosses, smoothed along the stroke, plus the paint it spreads.
    ride = gaussian_filter1d(np.bincount(k, h0 * cov) / (np.bincount(k, cov) + 1e-6), 8.0, mode="nearest")
    n = k.max() + 1
    chatter = gaussian_filter1d(rng.standard_normal(n), 1.0) * np.clip(_noise1(rng, n, 25) - 0.8, 0, None)
    ragged = 0.6 + 0.4 * _noise1(rng, 64, 2.0)[np.clip(((u + 1) * 31.5).astype(np.intp), 0, 63)]
    swell = 0.15 * _noise1(rng, n, 40.0)[k] + rng.uniform(-0.12, 0.12) * u
    slab = thickness * KNIFE_HEIGHT * (1 + swell + 0.45 * np.exp(-((au - 0.93) / 0.05) ** 2)
                                       + 0.8 * ragged * np.exp(-((L - 2.5 - s) / 2.5) ** 2)
                                       + 0.1 * chatter[k])
    contact = np.maximum(cov, 0.9 * _smooth_over(mark, cov, 2.0))
    delta = (ride[k] + slab - h0) * np.clip(1.25 * contact, 0, 1)
    cv.height[ys, xs] = h0 + np.where(delta < 0, delta * wet0[ys, xs], delta)
    return mark


def wet_in_wet(cv, mask=None, strength=0.6, reach=15.0, angle=None):
    """Work the wet paint inside `mask` together, as with a soft clean brush dragged back and forth.

    Each pixel takes on the Kubelka-Munk mix of the wet paint within about `reach` px (spectral.js
    concentrations), so adjacent wet colors melt into each other: ultramarine into cadmium yellow
    passes through green, not grey. The brush drags some of the mix over bare or dry gaps next to
    wet paint; dry paint itself neither moves nor joins the mix. angle: brushing
    direction in degrees, counterclockwise from horizontal: the mix reaches further along it and
    leaves faint streaks; None = worked in all directions. strength 0..1: how thoroughly it is
    worked. Brush marks in the wet paint flatten.
    """
    weight = _weight(cv, mask) * cv.wet
    sl = _bbox(weight > 0.01, pad=int(3 * reach) + 2)
    if sl is None:
        return
    color, wet = cv.color[sl], cv.wet[sl]
    mixed = _km_neighbourhood(color, wet, reach, angle)
    grain = _streaks(cv.rng, wet.shape, angle, reach)
    reached = np.maximum(wet, np.clip(1.5 * gaussian_filter(wet, 0.4 * reach), 0, 1))
    t = np.clip(strength * _weight(cv, mask)[sl] * reached * (1 + 0.45 * grain), 0, 1)
    color += (mixed - color) * t[..., None]
    h = cv.height[sl]
    h += (gaussian_filter(h, 1.5) - h) * t
    np.maximum(wet, t, out=wet)


def stipple(cv, mask, color, density=0.5, size=8.0, brush=None):
    """Dab paint on in small separate touches (pointillism).

    color: one color, or a list of colors picked at random per dab so they mix in the eye.
    density: share of the area the dabs cover (0..1). size: dab width in px.
    """
    m = _weight(cv, mask)
    b = brush or brushes.brush("round_bristle", size=size / 18, load=1.1)
    several = isinstance(color, (list, tuple)) and len(color) > 0 and isinstance(color[0], (str, list, tuple, np.ndarray))
    colors = list(color) if several else [color]
    rng = cv.rng
    cell = np.sqrt(0.55 * b.width_px ** 2 / max(density, 1e-3))
    pts = _jittered_grid(rng, cv.shape, cell)
    keep = rng.uniform(0, 1, len(pts)) < m[pts[:, 1].astype(int), pts[:, 0].astype(int)]
    hand = rng.uniform(0, np.pi)
    for p in rng.permutation(pts[keep]):
        a = hand + rng.normal(0, 0.35)
        d = np.array([np.cos(a), np.sin(a)]) * b.width_px * rng.uniform(0.2, 0.55)
        paint_stroke(cv, b, [p - d, p + d], colors[rng.integers(len(colors))], pressure=rng.uniform(0.55, 1.0))


def spatter(cv, mask, color, density=0.1, size=4.0, stretch=1.0, field=None, thickness=0.4, broken=0.0, brush=None):
    """Flick paint off a loaded brush: specks scattered at random over `mask`, many small and a few large.

    For snow, spray and foam, sparks, rain. Unlike stipple (even dabs on a jittered grid) the specks land at
    random, in clumps and gaps, and their widths spread log-normally around `size` px. With `field` (any
    direction field, e.g. fields.constant(a) or a vortex) each speck is a short streak `stretch` times as long
    as it is wide, lying along the field: snow or spray driven by the wind. Without a field they point every
    way. color: one color or a list, picked at random per speck. density: share of the area covered
    (0.005-0.05 reads as snow or spray, 0.1-0.3 as a spattered texture). thickness: relief of each speck (0 =
    flat). broken: share of specks that land half dry and
    break up on the tooth, like a dry brush (0-1). Returns the number of specks.
    """
    m = _weight(cv, mask)
    rng = cv.rng
    several = isinstance(color, (list, tuple)) and len(color) > 0 and isinstance(color[0], (str, list, tuple, np.ndarray))
    colors = list(color) if several else [color]
    spread = 0.45
    mean_area = 0.4 * size ** 2 * np.exp(2 * spread ** 2) * max(stretch, 1.0)
    n = int(density * m.sum() / mean_area)
    if n == 0:
        return 0
    pts = _scatter(rng, m, n)
    widths = size * np.exp(rng.normal(0, spread, n))
    if field is None:
        a = rng.uniform(0, np.pi, n)
        dirs = np.stack([np.cos(a), np.sin(a)], axis=1)
    else:
        dirs = np.asarray(field(pts), np.float64).reshape(-1, 2)
        turn = rng.normal(0, 0.12, n)
        c, s = np.cos(turn), np.sin(turn)
        dirs = np.stack([c * dirs[:, 0] - s * dirs[:, 1], s * dirs[:, 0] + c * dirs[:, 1]], axis=1)
    lengths = widths * max(stretch, 0.6) * rng.uniform(0.6, 1.4, n)
    bend = rng.normal(0, 0.05, n)
    base = brush or brushes.brush("round_bristle", load=1.5, dry_threshold=0.05, bristle_jitter=0.2, impasto=0.0,
                                  taper_start=0.35, taper_end=0.6)
    dry = rng.random(n) < broken if broken > 0 else np.zeros(n, bool)
    dry_load = rng.uniform(0.12, 0.3, n) if broken > 0 else None
    for i in rng.permutation(n):
        d, w = dirs[i], widths[i]
        half = 0.5 * lengths[i] * d
        mid = pts[i] + bend[i] * lengths[i] * np.array([-d[1], d[0]])
        b = replace(base, width_px=w, depletion=base.depletion * base.width_px / w)
        if dry[i]:
            b = replace(b, dry_threshold=max(b.dry_threshold, 0.6))
        mark = paint_stroke(cv, b, [pts[i] - half, mid, pts[i] + half], colors[rng.integers(len(colors))],
                            pressure=[rng.uniform(0.3, 0.9), 1.0, rng.uniform(0.15, 0.6)],
                            load=dry_load[i] if dry[i] else None)
        if thickness > 0 and len(mark.s):
            dome = np.clip(1 - mark.u ** 2, 0, 1) * np.sin(np.pi * np.clip(mark.s / max(mark.s.max(), 1), 0, 1)) ** 0.5
            cv.height[mark.ys, mark.xs] += thickness * IMPASTO_HEIGHT * mark.coverage * dome
    return n


def hatch(cv, mask, color, angle=45.0, spacing=8.0, length=None, cross=False, brush=None):
    """Lay parallel strokes `spacing` px apart at `angle` degrees (counterclockwise from horizontal).

    Strokes end where the mask ends, like a painter's hatching that follows a form's boundary; long
    runs are broken into staggered strokes about `length` px long (default 7 spacings).
    cross=True adds a second layer at angle + 90. Default brush: a round bristle ~0.55 spacing wide.
    """
    m = _weight(cv, mask)
    b = brush or brushes.brush("round_bristle", size=0.55 * spacing / 18, load=1.1)
    length = length or 7 * spacing
    for a in (angle, angle + 90) if cross else (angle,):
        _hatch_layer(cv, m, color, np.radians(a), spacing, length, b)


def _hatch_layer(cv, m, color, a, spacing, length, b):
    rng = cv.rng
    H, W = cv.shape
    d, nrm = np.array([np.cos(a), -np.sin(a)]), np.array([np.sin(a), np.cos(a)])
    center, reach = np.array([W, H]) / 2, np.hypot(W, H) / 2 + spacing
    t = np.arange(-reach, reach, 1.0)
    for off in np.arange(-reach, reach, spacing):
        base = center + (off + rng.normal(0, 0.12 * spacing)) * nrm
        pts = base + t[:, None] * d
        x, y = np.rint(pts[:, 0]).astype(int), np.rint(pts[:, 1]).astype(int)
        ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
        inside = np.zeros(len(t), bool)
        inside[ok] = m[y[ok], x[ok]] > 0.5
        edges = np.flatnonzero(np.diff(np.r_[0, inside.astype(np.int8), 0]))
        for t0, t1 in zip(t[np.minimum(edges[::2], len(t) - 1)], t[edges[1::2] - 1]):
            pos = t0 - rng.uniform(0, 0.6) * length
            while pos < t1:
                a0, a1 = max(pos, t0), min(pos + length * rng.uniform(0.7, 1.1), t1)
                if a1 - a0 > 0.8 * b.width_px:
                    tilt = rng.normal(0, 0.03)
                    dd = d + tilt * nrm
                    ctrl = base + np.outer(np.linspace(a0, a1, 4), dd) + np.outer(rng.normal(0, 0.12 * b.width_px, 4), nrm)
                    paint_stroke(cv, b, ctrl, color, pressure=rng.uniform(0.6, 1.0, 4))
                pos += length * rng.uniform(0.8, 1.2)


def _scrape(cv, b, path, pressure, wet0):
    """Trace the knife without paint, then lift wet paint where the blade touched."""
    color0, height0 = cv.color.copy(), cv.height.copy()
    mark = paint_stroke(cv, b, path, "#000000", pressure)
    ys, xs, s, u, cov = mark.ys, mark.xs, mark.s, mark.u, mark.coverage
    cv.color[ys, xs], cv.height[ys, xs], cv.wet[ys, xs] = color0[ys, xs], height0[ys, xs], wet0[ys, xs]
    if not len(s):
        return mark
    peaks = np.clip((cv.tooth[ys, xs] - 0.25) / 0.5, 0, 1)
    lift = np.clip(1.3 * cov, 0, 1) * (0.45 + 0.55 * peaks) * wet0[ys, xs]
    cv.color[ys, xs] += (cv.underlayer[ys, xs] - cv.color[ys, xs]) * lift[:, None]
    removed = cv.height[ys, xs] * lift
    cv.height[ys, xs] -= removed
    # The lifted paint piles up in thin ridges along the blade's sides.
    cv.height[ys, xs] += removed.mean() * 0.8 * np.exp(-((np.abs(u) - 0.94) / 0.05) ** 2)
    cv.wet[ys, xs] *= 1 - lift
    return mark


def _smooth_over(mark, values, sigma):
    """Gaussian smoothing of per-pixel mark values over the image plane (only the mark's pixels count)."""
    y0, x0 = mark.ys.min(), mark.xs.min()
    shape = (mark.ys.max() - y0 + 1, mark.xs.max() - x0 + 1)
    val, inside = np.zeros(shape), np.zeros(shape)
    val[mark.ys - y0, mark.xs - x0] = values
    inside[mark.ys - y0, mark.xs - x0] = 1
    return (gaussian_filter(val, sigma) / np.maximum(gaussian_filter(inside, sigma), 1e-6))[mark.ys - y0, mark.xs - x0]


def _impasto_relief(rng, mark, width):
    """Relative paint thickness over an impasto stroke's (s, u) coordinates."""
    s, u = mark.s, mark.u
    L, au, hw = s.max(), np.abs(u), 0.5 * width
    ns, nt = int(L) + 3, int(2 * hw) + 5
    furrows = gaussian_filter(rng.standard_normal((ns, nt)), (9.0, 0.8))
    furrows /= furrows.std() + 1e-9
    lip_noise = _noise1(rng, ns, 6.0)
    si, ti = np.clip(s, 0, ns - 1), np.clip(u * hw + hw + 2, 0, nt - 1)
    f = map_coordinates(furrows, [si, ti], order=1)
    lips = np.exp(-((au - 0.84) / 0.1) ** 2) * (0.75 + 0.25 * lip_noise[si.astype(np.intp)])
    crest = np.exp(-((L - 4 - s) / 4.5) ** 2) * (0.8 + 0.25 * f)
    land = np.exp(-(s / (0.4 * width)) ** 2)
    return np.maximum((1 - 0.35 * s / max(L, 1)) * (1 + 0.3 * f) + 0.6 * lips + 1.5 * crest + 0.35 * land, 0)


def _through_film(rgb, ks, depth):
    """Linear RGB of paint `rgb` (n, 3) under a glaze film: absorption K*d = ks * depth, little scattering."""
    ru = reflectance(rgb)
    a = 1 + ks / GLAZE_SCATTER
    b = np.sqrt(a * a - 1)
    x = b * GLAZE_SCATTER * depth[:, None]
    den = a * np.sinh(x) + b * np.cosh(x)
    rf, tf = np.sinh(x) / den, b / den
    r = rf + tf * tf * ru / (1 - rf * ru)
    return np.clip(r @ SPECTRUM_TO_RGB, 0, 1)


def _km_neighbourhood(color, wet, reach, angle):
    """Kubelka-Munk mix of the wet paint around each pixel, weighted by a Gaussian of ~reach px.

    Like color.mix, each pixel joins with concentration weight^2 * luminance (here times its
    wetness), and the K/S spectra average by concentration. Computed at half resolution.
    """
    h, w = wet.shape
    f = 2 if min(h, w) >= 8 and reach >= 4 else 1
    hs, ws = h // f, w // f
    small = color[:hs * f, :ws * f].reshape(hs, f, ws, f, 3).mean(axis=(1, 3))
    wet_s = wet[:hs * f, :ws * f].reshape(hs, f, ws, f).mean(axis=(1, 3))
    flat = small.reshape(-1, 3)
    num = np.empty((len(flat), len(CMF[1])), np.float32)
    conc = np.empty(len(flat), np.float32)
    for i in range(0, len(flat), 1 << 16):
        r = reflectance(flat[i:i + (1 << 16)])
        conc[i:i + (1 << 16)] = r @ CMF[1]
        num[i:i + (1 << 16)] = (1 - r) ** 2 / (2 * r) * conc[i:i + (1 << 16), None]
    conc *= wet_s.ravel()
    num *= wet_s.reshape(-1, 1)
    along, across = reach / f, (0.35 if angle is not None else 1.0) * reach / f
    a = np.radians(0.0 if angle is None else angle)
    sx = np.hypot(along * np.cos(a), across * np.sin(a))
    sy = np.hypot(along * np.sin(a), across * np.cos(a))
    num = gaussian_filter(num.reshape(hs, ws, -1), (sy, sx, 0))
    den = gaussian_filter(conc.reshape(hs, ws), (sy, sx))
    ks = num / np.maximum(den, 1e-12)[..., None]
    rgb = np.clip((1 + ks - np.sqrt(ks * ks + 2 * ks)) @ SPECTRUM_TO_RGB, 0, 1).astype(np.float32)
    rgb = np.where((den > 1e-9)[..., None], rgb, small)
    if f > 1:
        rgb = zoom(rgb, (h / hs, w / ws, 1), order=1, mode="nearest")[:h, :w]
    return rgb


def _streaks(rng, shape, angle, reach):
    """Unit noise streaked along `angle` (degrees), like the marks of a soft brush; mottled if None."""
    if angle is None:
        return _noise(rng, shape, 0.4 * reach)
    h, w = shape
    a = np.radians(angle)
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    along, across = xx * np.cos(a) - yy * np.sin(a), xx * np.sin(a) + yy * np.cos(a)
    lo_a, lo_c = along.min(), across.min()
    grid = gaussian_filter(rng.standard_normal((int(across.max() - lo_c) + 3, int((along.max() - lo_a) / 6) + 3)),
                           (0.9, 2.5))
    grid /= grid.std() + 1e-9
    return map_coordinates(grid, [across - lo_c, (along - lo_a) / 6], order=1)


def _ks(lrgb):
    r = reflectance(lrgb)
    return np.maximum((1 - r) ** 2 / (2 * r), 1e-6)


def _pools(cv, sl, ms):
    """Where glaze medium gathers: just inside the mask's edge (+) and in valleys (+), off peaks (-)."""
    rim = np.clip(ms - gaussian_filter(ms, 4.0), 0, None) / 0.5
    relief = cv.height[sl] + 0.3 * cv.tooth[sl]
    valley = gaussian_filter(relief, 3.0) - relief
    return 1.6 * rim + 0.4 * np.clip(valley / (valley.std() + 1e-6), -1.5, 2.5)


@contextmanager
def _only_within(cv, weight):
    """Keep what the enclosed strokes do only in proportion to weight (HxW, 0..1)."""
    saved = [a.copy() for a in (cv.color, cv.height, cv.wet)]
    yield
    for now, before in zip((cv.color, cv.height, cv.wet), saved):
        w = weight if now.ndim == 2 else weight[..., None]
        now[...] = before + (now - before) * w


@contextmanager
def _paint_ridges_as_tooth(cv):
    """Let a dry brush catch on the ridges of the paint as well as on the weave."""
    tooth = cv.tooth
    ridges = cv.height - gaussian_filter(cv.height, 3.0)
    cv.tooth = np.clip(tooth + 0.8 * ridges, 0, 1).astype(np.float32)
    try:
        yield
    finally:
        cv.tooth = tooth


def _weight(cv, mask):
    if mask is None:
        return np.ones(cv.shape, np.float32)
    m = np.asarray(mask, np.float32)
    if m.shape != cv.shape:
        raise ValueError(f"mask shape {m.shape} does not match the canvas {cv.shape}")
    return np.clip(m, 0, 1)


def _bbox(sel, pad):
    ys, xs = np.nonzero(sel)
    if not len(ys):
        return None
    H, W = sel.shape
    return (slice(max(ys.min() - pad, 0), min(ys.max() + pad + 1, H)),
            slice(max(xs.min() - pad, 0), min(xs.max() + pad + 1, W)))


def _scatter(rng, weight, n):
    """n points (x, y) drawn with probability proportional to weight, jittered within their pixel."""
    p = weight.ravel().astype(np.float64)
    idx = rng.choice(p.size, size=n, p=p / p.sum())
    y, x = np.divmod(idx, weight.shape[1])
    return np.column_stack([x, y]) + rng.uniform(0, 1, (n, 2))


def _jittered_grid(rng, shape, cell):
    """One random point (x, y) per cell of a grid covering the canvas: even but irregular spacing."""
    H, W = shape
    gy, gx = np.mgrid[0:H:cell, 0:W:cell]
    pts = np.column_stack([gx.ravel(), gy.ravel()]) + rng.uniform(0, cell, (gx.size, 2))
    return pts[(pts[:, 0] < W) & (pts[:, 1] < H)]


def _noise(rng, shape, sigma):
    z = gaussian_filter(rng.standard_normal(shape).astype(np.float32), sigma)
    z -= z.mean()  # a patch much smaller than sigma is nearly constant: without this, z / std explodes
    return z / (z.std() + 1e-9)


def _noise1(rng, n, sigma):
    z = gaussian_filter1d(rng.standard_normal(n), sigma)
    z -= z.mean()
    return z / (z.std() + 1e-9)
