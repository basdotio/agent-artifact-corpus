"""Surface: photograph the finished painting under a raking light (Canvas.finish).

finish() does not change the canvas. Like a photograph of the painting, it returns a new HxWx3
uint8 sRGB image (hand it to studio.save), so you can keep painting and finish again. The same
canvas always gives the same image: craquelure and grime draw on their own generators seeded by
the canvas seed, never on cv.rng. A local change of paint changes only the cracks near it: every draw is keyed
to a place in the network or to the canvas size, never to a running count that paint can shift.
"""

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import Voronoi
from scipy.special import ndtr

from atelier.color import linear_to_srgb

RELIEF = 3.0          # px of surface relief per unit of paint height
WEAVE_RELIEF = 2.5    # px of relief of the bare weave at weave=1
BURY = 0.35           # paint height that buries the weave to 1/e
AMBER = np.array([1.0, 0.8, 0.5])   # transmission of a fully aged varnish (linear RGB)
AMBIENT = 0.3         # share of the light that comes from the room, not the lamp: shadows are never black
GRIME = np.array([0.050, 0.041, 0.030], np.float32)   # old dirt (linear RGB), a warm grey-brown
CRACK = np.array([0.030, 0.024, 0.017], np.float32)   # the bottom of a crack: shadow and dirt
SUPPORTS = ("panel", "canvas", "linen", "cotton", "paper")

# Craquelure, sizes in px at 2048 px wide (times scale). The network is a coarse set of cells whose borders
# crack first, then the cells split into islands, then the islands into finer ones. On a panel it is laid
# out in a space shrunk along the grain (x here; an upright panel is drawn on its side and turned back),
# so the long cracks run with the grain and the islands are longer along it; on canvas it has no direction.
CELL = {"panel": (240, 48), "canvas": (120, 120)}     # the coarse cells (x, y) [px]
GRAIN = {"panel": 6.0, "canvas": 1.0}                 # the coarse cells' borders are laid out shrunk this much
ASPECT = {"panel": 2.4, "canvas": 1.0}                # islands this much longer along the grain
ISLAND = {"panel": (30, 16), "canvas": (50, 26)}      # islands split while longer than this (shrunk px)
OPENS = ((0.02, 0.5), (0.15, 0.55), (0.5, 0.55))      # (start, spread) of the amounts at which each stage opens
WIDTH = (0.9, 0.75, 0.6)                              # full-grown gap width per stage [px]
RIM = 0.75            # height of a cupped island's lip at a fully open crack [px]
LIP = 1.8             # how far the lip reaches into the island [px, 1/e]
PIECE = 4.0           # cracks are drawn as straight pieces this long [px]


def finish(cv, light=(-0.5, -0.6), varnish=0.2, weave=0.3, crackle=0.0, scale=1.0, grime=0.0, edge=0.0,
           support=None):
    """Light the paint relief and return the painting as an HxWx3 uint8 sRGB image. cv is unchanged.

    light: (x, y) direction towards the lamp in image coordinates (x right, y down); (-0.5, -0.6)
        is the classic upper left. Its length sets how low the lamp rakes: elevation
        z = sqrt(1 - x^2 - y^2). A 3-tuple (x, y, z) gives the direction explicitly.
    varnish: 0 = unvarnished (paint glossy, bare ground matte), 1 = thick old varnish: glossy
        everywhere, warm amber tint, deeper darks, finer texture filled in for the highlights.
    weave: 0..1, how much the canvas texture (tooth) shows in the light; thick paint buries it.
    crackle: 0..1 how far craquelure has gone. From 0.05 a few hairlines open in patches, 0.3 is a
        sparse network, 0.6 a full one, 1 heavy cracking with finer cracks between. The cracks are
        hairlines (under a pixel to about 1 px at 2048) that show mostly through the light: the
        islands between them are cupped, so a crack has a lit lip on the lamp's side and a shadow on
        the other, with a little dirt in the gap. Thick paint cracks wider and more sparsely.
    scale: the canvas size relative to 2048 px wide, the S a script multiplies its sizes by. The
        relief is lit and the craquelure drawn as on a 2048 px render, so a study at scale=900/2048
        looks about as embossed as the 2048 px final. 1 = heights lit as they lie in pixels.
    grime: 0..1 the dirt of centuries and the uneven varnish that goes with it: the amber turns
        patchy and deeper in the hollows of the paint and toward the edges, and a grey-brown veil
        settles there and in the cracks. 0 keeps the varnish even and clean.
    edge: width of the rebate band as a fraction of the shorter side (about 0.02-0.04; 0 = none):
        the strip a frame covered, its varnish less yellowed and less dirty, a line of dust along
        its inner edge.
    support: the craquelure's pattern. "panel": a roughly rectangular network with long cracks along
        the wood grain, which runs the long way of the panel as its planks do (up an upright panel);
        a canvas ("linen", "cotton", "paper" or "canvas"): an irregular polygonal network. None takes
        it from cv.ground's texture.
    """
    if support not in (None, *SUPPORTS):
        raise ValueError(f"unknown support {support!r}; choose from {SUPPORTS}")
    h = cv.height.astype(np.float32)
    # Paint relief is part stroke-sized (it shrinks with the canvas, so its slopes steepen as 1/scale) and part
    # pixel-sized (bristle furrows, anti-aliased edges: the same slopes at any size); sqrt(scale) evens out the
    # mix, measured on the starter and on a sheet of large strokes. The weave's size is set by ground() in pixels.
    z = RELIEF * np.sqrt(scale) * gaussian_filter(h, 0.6) + weave * WEAVE_RELIEF * cv.tooth * np.exp(-h / BURY)
    color = cv.color.astype(np.float32)
    crack = None
    if crackle > 0:
        crack, lip = _craquelure(cv.seed, cv, crackle, scale, support or cv.texture or "linen")
        z = z + scale * (lip - 0.15 * crack)
        color = color + (CRACK - color) * (0.7 * crack)[..., None]

    lx, ly, lz = _unit(light)
    gy, gx = np.gradient(z)
    lamp = np.clip((lz - gx * lx - gy * ly) / np.sqrt(gx * gx + gy * gy + 1), 0, None) / lz
    shade = AMBIENT + (1 - AMBIENT) * lamp
    cavity = np.clip(1 + 0.12 * (z - gaussian_filter(z, 3.0)), 0.75, 1.05)

    hx, hy, hz = _unit((lx, ly, lz + 1))
    zs = gaussian_filter(z, 0.4 + 1.5 * varnish)
    sy, sx = np.gradient(zs)
    ndoth = np.clip((hz - sx * hx - sy * hy) / np.sqrt(sx * sx + sy * sy + 1), 0, 1)
    gloss = 0.18 * np.clip(h / 0.2, 0, 1) + 0.35 * varnish
    spec = gloss * ndoth ** (30 + 90 * varnish)

    if grime > 0 or edge > 0:
        v, veil = _patina(cv.seed, z, crack, varnish, grime, edge, scale)
        tint = AMBER.astype(np.float32) ** v[..., None]
        color = color ** (1 + 0.2 * v)[..., None] * tint
        lit = (shade * cavity)[..., None]
        out = color * lit + (spec * (1 - veil))[..., None] * (0.3 + 0.7 * tint)
        out = out + (GRIME * lit - out) * veil[..., None]
    else:
        tint = AMBER ** varnish
        color = color ** (1 + 0.2 * varnish) * tint
        out = color * (shade * cavity)[..., None] + spec[..., None] * (0.3 + 0.7 * tint)
    return np.round(linear_to_srgb(np.clip(out, 0, 1)) * 255).astype(np.uint8)


def _unit(v):
    v = np.asarray(v, np.float64)
    if len(v) == 2:
        v = np.append(v, np.sqrt(max(1 - v @ v, 0.04)))
    return v / np.linalg.norm(v)


def _patina(seed, z, crack, varnish, grime, edge, scale):
    """The varnish's thickness (HxW, in the units of `varnish`) and the grime veil (HxW, 0..1)."""
    rng = np.random.default_rng([seed, 8])
    H, W = z.shape
    patches = _field_full(rng, (H, W), 260 * scale)
    hollow = np.clip((gaussian_filter(z, 3 * scale) - z) / (0.06 * np.sqrt(scale)), 0, 1)
    yy, xx = np.ogrid[:H, :W]
    reach = 0.07 * min(H, W)
    near = [np.exp(-np.minimum(a, n - 1 - a) / reach) for a, n in ((xx, W), (yy, H))]
    edges = 1 - (1 - near[0]) * (1 - near[1])                        # toward the edges, most in the corners
    in_cracks = 0 if crack is None else crack
    v = varnish * np.clip(1 + grime * (0.7 * patches + 1.2 * hollow + 1.6 * edges), 0, None)
    veil = grime * (0.08 * np.clip(1 + patches, 0, None) + 0.3 * hollow + 0.55 * edges + 0.8 * in_cracks)
    if edge > 0:
        band_w = edge * min(H, W)
        wob = [3 * scale * _field_full(rng, (H, W), 120 * scale) for _ in range(2)]
        dist = np.minimum(np.minimum(xx, W - 1 - xx) + wob[0], np.minimum(yy, H - 1 - yy) + wob[1])
        band = np.clip((band_w - dist) / (3 * scale) + 0.5, 0, 1)             # 1 under the rebate
        dust = np.exp(-(((dist - band_w) / (3 * scale)) ** 2)) * np.clip(0.5 + 0.5 * patches, 0, 1)
        v = v * (1 - 0.5 * band)
        veil = veil * (1 - 0.8 * band) + max(grime, 0.2) * 0.15 * dust        # dust along the frame's lip
    return v.astype(np.float32), np.clip(veil, 0, 0.9).astype(np.float32)


# ---- craquelure ----

def _craquelure(seed, cv, amount, scale, support):
    """Crack coverage (0..1) and the height of the cupped islands' lips (px at 2048 px), both HxW float32.

    The network depends on the canvas (seed, size, support, paint thickness) but not on `amount`: more
    crackle opens more of the same network, from its first cracks to its finest, and widens the open ones.
    Paint thickness decides which islands split, so a dab of paint changes the cracks around it and no others:
    nothing here draws from a stream whose position depends on how many cracks the paint left.
    """
    kind = "panel" if support == "panel" else "canvas"
    thick = np.clip(gaussian_filter(cv.height.astype(np.float32), 6 * scale), 0, 1.5)
    upright = kind == "panel" and cv.shape[0] > cv.shape[1]       # the grain runs up the panel
    if upright:
        thick = thick.T
    p0, p1, stage, dice = _network(seed, thick.shape, scale, thick, kind)
    wander = ((40, 160), (60, 60), 3.0) if kind == "panel" else ((70, 70), (70, 70), 4.5)
    crack, lip = _draw_cracks(seed, thick.shape, scale, thick, amount, p0, p1, stage, dice, wander)
    return (np.ascontiguousarray(crack.T), np.ascontiguousarray(lip.T)) if upright else (crack, lip)


def _network(seed, shape, scale, thick, kind):
    """The whole crack network as segments (ends p0, p1 and stage 0, 1, 2), laid out in shrunk space, and what
    each crack draws for itself: dice, Nx3 (a normal that ranks it, a coin for the end its opening starts at,
    a normal that thins it)."""
    H, W = shape
    grain = np.array([GRAIN[kind], 1.0])
    stretch = np.array([ASPECT[kind], 1.0])
    cell = np.array(CELL[kind], float) * scale
    gy, gx = np.mgrid[-2 * cell[1]:H + 2 * cell[1]:cell[1], -2 * cell[0]:W + 2 * cell[0]:cell[0]]
    rng = np.random.default_rng([seed, 7])
    pts = np.column_stack([gx.ravel(), gy.ravel()]) + rng.uniform(-0.5, 0.5, (gx.size, 2)) * cell
    vor = Voronoi(pts / grain)
    V = vor.vertices * grain
    lo, hi = -cell, np.array([W, H]) + cell
    inside = lambda q: ((q > lo) & (q < hi)).all(-1)
    ridges = np.array([r for r in vor.ridge_vertices if -1 not in r])
    a, b = V[ridges[:, 0]], V[ridges[:, 1]]
    keep = inside(a) | inside(b)
    cells = []
    for i, region in enumerate(vor.regions[r] for r in vor.point_region):      # i: the seed point, fixed by the grid
        if not region or -1 in region:
            continue
        Q = V[region]
        c = Q.mean(0)
        if inside(c):
            cells.append((i, Q[np.argsort(np.arctan2(Q[:, 1] - c[1], Q[:, 0] - c[0]))] / stretch))
    q0, q1, st, dice = _split(seed, cells, stretch, np.array(ISLAND[kind], float) * scale, thick)
    m = keep.sum()
    rng = np.random.default_rng([seed, 7, 2])
    ridge_dice = np.column_stack([rng.standard_normal(m), rng.random(m), rng.standard_normal(m)])
    return (np.vstack([a[keep], q0 * stretch]), np.vstack([b[keep], q1 * stretch]),
            np.concatenate([np.zeros(m, int), st]), np.vstack([ridge_dice, dice]))


def _split(seed, cells, stretch, sizes, thick):
    """Crack convex islands (in shrunk space) across their longest axis until each is shorter than its own
    limit; a crack runs from border to border of its island (T-junctions). Thick paint keeps its islands
    bigger. Every island draws from its own generator, keyed by its coarse cell and its place among that cell's
    splits, so paint that changes one island's fate leaves every other island's draws alone. Returns the
    cracks' ends (shrunk space), their stage (1, or 2 for the fine ones) and their dice."""
    H, W = thick.shape
    big, small = sizes
    tilt = 0.2 / stretch[0]
    stack = [(cell, 1, Q) for cell, Q in cells]
    ends0, ends1, stage, dice = [], [], [], []
    while stack:
        cell, place, Q = stack.pop()
        rng = np.random.default_rng([seed, 7, 3, cell, place])
        c = Q.mean(0)
        d = Q - c
        ang, extent = _long_axis(d)
        x, y = np.clip(c * stretch, 0, [W - 1, H - 1]).astype(int)
        grow = 1 + 0.8 * thick[y, x]
        jitter = rng.standard_normal(3)
        if extent < small * grow * np.exp(0.25 * jitter[0]):
            continue
        n = np.array([np.cos(ang + tilt * jitter[1]), np.sin(ang + tilt * jitter[1])])
        f = d @ n - np.clip(0.12 * jitter[2], -0.25, 0.25) * extent
        side = f > 0
        nxt = np.roll(np.arange(len(Q)), -1)
        cross = side != side[nxt]
        k = np.nonzero(cross)[0]
        if len(k) != 2:
            continue
        cut = Q[k] + (Q[nxt[k]] - Q[k]) * (f[k] / (f[k] - f[nxt[k]]))[:, None]
        halves = ([], [])
        for i in range(len(Q)):
            halves[0 if side[i] else 1].append(Q[i])
            if cross[i]:
                p = cut[0 if i == k[0] else 1]
                halves[0].append(p)
                halves[1].append(p)
        stack.extend((cell, 2 * place + s, np.array(hv)) for s, hv in enumerate(halves))
        ends0.append(cut[0])
        ends1.append(cut[1])
        stage.append(1 if extent >= big * grow else 2)
        dice.append((rng.standard_normal(), rng.random(), rng.standard_normal()))
    empty = np.zeros((0, 2))
    return ((np.array(ends0) if ends0 else empty), (np.array(ends1) if ends1 else empty), np.array(stage, int),
            np.array(dice) if dice else np.zeros((0, 3)))


def _long_axis(d):
    """Direction (angle) and length of the long side of a convex polygon's smallest bounding rectangle."""
    e = np.roll(d, -1, axis=0) - d
    ang = np.arctan2(e[:, 1], e[:, 0])
    u = np.stack([np.cos(ang), np.sin(ang)])
    along, across = np.ptp(d @ u, axis=0), np.ptp(d @ np.stack([-u[1], u[0]]), axis=0)
    i = np.argmin(along * across)
    return (ang[i], along[i]) if along[i] >= across[i] else (ang[i] + np.pi / 2, across[i])


def _draw_cracks(seed, shape, scale, thick, amount, p0, p1, stage, dice, wander):
    """Cut the cracks into short pieces that wander a little, give each point the amount at which it opens, and
    rasterize the open ones: the gap's coverage (a box-filtered line of sub-pixel width) and the lips' height."""
    H, W = shape
    n = len(p0)
    rank = dice[:, 0]
    backwards = dice[:, 1] < 0.5
    thin = np.exp(0.3 * dice[:, 2])
    rng = np.random.default_rng([seed, 7, 1])          # the fields depend on the canvas size only, never on the paint
    patches = _field(rng, shape, 260 * scale)          # where the paint gives way first
    local = _field(rng, shape, 45 * scale)             # and along each crack
    reach = wander[2] * scale
    wander = [_field(rng, shape, np.multiply(f, scale)) for f in wander[:2]]
    jag = _field(rng, shape, 6 * scale)
    fine = rng.standard_normal(shape, dtype=np.float32)      # the roughness of single points, read by position

    length = np.hypot(*(p1 - p0).T)
    k = np.maximum(1, np.ceil(length / (PIECE * scale))).astype(int)
    seg = np.repeat(np.arange(n), k + 1)
    first = np.repeat(np.cumsum(k + 1) - (k + 1), k + 1)
    frac = (np.arange(seg.size) - first) / k[seg]
    P = p0[seg] + (p1 - p0)[seg] * frac[:, None]
    P = P + reach * np.column_stack([_at(wander[1], P), _at(wander[0], P)])
    normal = np.column_stack([-(p1 - p0)[:, 1], (p1 - p0)[:, 0]]) / np.maximum(length, 1e-6)[:, None]
    inner = (frac > 0) & (frac < 1)                    # the ends stay on the cracks they meet
    px, py = np.rint(P[inner]).astype(int).T
    kink = 0.6 * _at(jag, P[inner]) + 0.15 * fine[np.clip(py, 0, H - 1), np.clip(px, 0, W - 1)]
    P[inner] += normal[seg][inner] * (scale * kink)[:, None]

    th = map_coordinates(thick, [P[:, 1], P[:, 0]], order=1, mode="nearest")
    start = np.array([o[0] for o in OPENS])[stage][seg]
    spread = np.array([o[1] for o in OPENS])[stage][seg]
    q = ndtr(0.8 * _at(patches, P) + 0.45 * _at(local, P) + 0.4 * rank[seg])     # uniform 0..1, low in patches
    along = np.where(backwards[seg], 1 - frac, frac) * 0.07 * np.minimum(1, length / (50 * scale))[seg]
    opens = start + spread * q + along + 0.1 * th
    width = np.array(WIDTH)[stage][seg] * thin[seg] * (1 + 0.7 * th) * scale

    last = np.cumsum(k + 1) - 1
    a = np.setdiff1d(np.arange(seg.size), last)
    b = a + 1
    live = np.minimum(opens[a], opens[b]) < amount
    return _splat(shape, P[a[live]], P[b[live]], opens[a[live]], opens[b[live]], width[a[live]], width[b[live]],
                  amount, scale)


def _splat(shape, A, B, ta, tb, wa, wb, amount, scale):
    """Rasterize crack pieces A->B (opening amounts ta->tb, widths wa->wb along them); the max over pieces."""
    H, W = shape
    crack = np.zeros(H * W, np.float32)
    lip = np.zeros(H * W, np.float32)
    reach = 3 * LIP * scale
    far = np.exp(-reach / (LIP * scale))
    K = int(np.ceil(PIECE * scale * 1.42 + 2 * reach)) + 4
    oy, ox = [o.ravel() for o in np.mgrid[:K, :K]]
    chunk = max(256, 1_500_000 // (K * K))          # about 1.5M pixel-piece pairs at a time
    for c0 in range(0, len(A), chunk):
        c = slice(c0, c0 + chunk)
        a, b = A[c], B[c]
        x0 = np.floor(np.minimum(a[:, 0], b[:, 0]) - reach).astype(int)
        y0 = np.floor(np.minimum(a[:, 1], b[:, 1]) - reach).astype(int)
        px = (x0[:, None] + ox).astype(np.float32)
        py = (y0[:, None] + oy).astype(np.float32)
        ab = (b - a).astype(np.float32)
        L2 = np.maximum((ab * ab).sum(1), 1e-6)[:, None]
        s = np.clip(((px - a[:, :1]) * ab[:, :1] + (py - a[:, 1:]) * ab[:, 1:]) / L2, 0, 1)
        d = np.hypot(px - a[:, :1] - s * ab[:, :1], py - a[:, 1:] - s * ab[:, 1:])
        t = ta[c, None] + (tb[c] - ta[c])[:, None] * s
        w = wa[c, None] + (wb[c] - wa[c])[:, None] * s
        grown = np.clip((amount - t) / 0.3, 0, 1)
        opened = np.clip((amount - t) / 0.05, 0, 1)
        half = 0.5 * w * (0.45 + 0.55 * grown)
        cover = opened * np.clip(np.minimum(d + 0.5, half) - np.maximum(d - 0.5, -half), 0, 1)
        height = opened * RIM * (0.45 + 0.55 * grown) * np.clip((np.exp(-d / (LIP * scale)) - far) / (1 - far), 0, 1)
        ok = (d < reach) & (opened > 0) & (px >= 0) & (px < W) & (py >= 0) & (py < H)
        idx = (py[ok].astype(np.int64) * W + px[ok].astype(np.int64))
        np.maximum.at(crack, idx, cover[ok].astype(np.float32))
        np.maximum.at(lip, idx, height[ok].astype(np.float32))
    return crack.reshape(H, W), lip.reshape(H, W)


def _field(rng, shape, feature):
    """Smooth unit-variance noise with blobs about `feature` px across ((fy, fx) for stretched ones), on a grid
    just fine enough for them; read it anywhere with _at."""
    fy, fx = np.broadcast_to(np.asarray(feature, float), 2)
    step = max(1.0, min(fy, fx) / 6)
    H, W = shape
    g = rng.standard_normal((int(H / step) + 8, int(W / step) + 8)).astype(np.float32)
    g = gaussian_filter(g, (fy / step / 3, fx / step / 3), mode="wrap")
    return g / (g.std() + 1e-9), step


def _at(field, pts):
    g, step = field
    return map_coordinates(g, [pts[:, 1] / step + 4, pts[:, 0] / step + 4], order=1, mode="nearest")


def _field_full(rng, shape, feature):
    H, W = shape
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    return _at(_field(rng, shape, feature), np.column_stack([xx.ravel(), yy.ravel()])).reshape(H, W)
