import numpy as np
import pytest

from atelier import fields


def ring(center, r, n=72):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([center[0] + r * np.cos(a), center[1] + r * np.sin(a)], axis=1)


def follow(field, p, step=1.0, n=2000):
    """Streamline through p (RK2), keeping the direction continuous for orientation-only fields."""
    pts = [np.asarray(p, float)]
    prev = field(pts[0][None])[0]
    for _ in range(n):
        d1 = field(pts[-1][None])[0]
        d1 = d1 if d1 @ prev >= 0 else -d1
        d2 = field((pts[-1] + 0.5 * step * d1)[None])[0]
        d2 = d2 if d2 @ d1 >= 0 else -d2
        pts.append(pts[-1] + step * d2)
        prev = d2
    return np.array(pts)


def winding(pts, c):
    a = np.unwrap(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))
    return a[-1] - a[0]


@pytest.mark.parametrize("field", [
    fields.constant(30),
    fields.radial((40, 50)),
    fields.vortex((40, 50), twist=0.7),
    fields.noise(80, 1),
    fields.combine((fields.constant(0), 1.0), (fields.noise(50, 2), 0.5)),
])
def test_fields_give_unit_vectors_for_any_point_shape(field):
    pts = np.random.default_rng(0).uniform(0, 100, (5, 7, 2))
    d = field(pts)
    assert d.shape == (5, 7, 2)
    np.testing.assert_allclose(np.hypot(d[..., 0], d[..., 1]), 1, atol=1e-9)


def test_constant_angle_is_in_degrees_with_y_down():
    np.testing.assert_allclose(fields.constant(0)(np.zeros((2, 2))), [[1, 0], [1, 0]], atol=1e-12)
    np.testing.assert_allclose(fields.constant(90)(np.zeros((1, 2))), [[0, 1]], atol=1e-12)


def test_radial_points_away_from_the_center():
    c = (120.0, 80.0)
    p = ring(c, 30)
    np.testing.assert_allclose(fields.radial(c)(p), (p - c) / 30, atol=1e-9)


def test_vortex_rotates_around_the_center():
    c = np.array([200.0, 150.0])
    f = fields.vortex(c, twist=1.0)
    for r in (15, 60, 140):
        p = ring(c, r)
        d = f(p)
        rhat = (p - c) / r
        assert np.abs((d * rhat).sum(1)).max() < 1e-9
        turn = rhat[:, 0] * d[:, 1] - rhat[:, 1] * d[:, 0]
        assert (turn > 0.999).all() or (turn < -0.999).all()
    path = follow(f, c + [80, 0], step=1.0, n=1100)
    radius = np.hypot(*(path - c).T)
    assert abs(winding(path, c)) > 2 * np.pi
    assert np.ptp(radius) < 2


def test_vortex_twist_spirals_inward_and_negative_twist_outward():
    c = np.array([300.0, 300.0])
    for twist, grows in ((0.6, False), (-0.6, True)):
        f = fields.vortex(c, twist=twist)
        p = ring(c, 100)
        d = f(p)
        rhat = (p - c) / 100
        # 40% of the way from pure rotation to pure radial: 36 degrees off the tangent
        np.testing.assert_allclose(np.abs((d * rhat).sum(1)), np.sin(np.radians(36)), atol=1e-9)
        path = follow(f, c + [100, 0], step=1.0, n=120)
        radius = np.hypot(*(path - c).T)
        assert (np.diff(radius) > 0).all() if grows else (np.diff(radius) < 0).all()
        assert abs(winding(path, c)) > 0.5


def test_contour_is_tangent_to_a_circle_mask_edge():
    h, w, c, R = 260, 340, np.array([170.0, 130.0]), 80
    y, x = np.mgrid[:h, :w]
    mask = np.hypot(x - c[0], y - c[1]) < R
    f = fields.contour(mask)
    for r in (R, R - 12, R + 12, R - 40):
        p = ring(c, r)
        d = f(p)
        rhat = (p - c) / r
        assert np.abs((d * rhat).sum(1)).max() < 0.1, r


def test_contour_of_a_ramp_image_runs_across_the_gradient():
    img = np.tile(np.linspace(0, 1, 200), (120, 1))
    d = fields.contour(img)(np.random.default_rng(1).uniform(20, 100, (30, 2)))
    np.testing.assert_allclose(np.abs(d[:, 1]), 1, atol=1e-6)


def test_noise_is_deterministic_smooth_and_varied():
    rng_pts = np.random.default_rng(0).uniform(0, 1000, (400, 2))
    a = fields.noise(150, 7)(rng_pts)
    np.testing.assert_array_equal(a, fields.noise(150, np.random.default_rng(7))(rng_pts))
    assert not np.allclose(a, fields.noise(150, 8)(rng_pts))
    near = fields.noise(150, 7)(rng_pts + [2, 0])
    assert (a * near).sum(1).min() > 0.97
    angles = np.degrees(np.arctan2(a[:, 1], a[:, 0]))
    assert np.ptp(angles) > 180
    calm = fields.noise(150, 7, angle=90, spread=10)(rng_pts)
    assert np.abs(calm[:, 1]).min() > np.cos(np.radians(45))


def test_combine_by_weight_and_by_mask():
    pts = np.array([[20.0, 50.0], [180.0, 50.0], [100.0, 50.0]])
    east, south = fields.constant(0), fields.constant(90)
    np.testing.assert_allclose(fields.combine((east, 1), (south, 0))(pts), [[1, 0]] * 3, atol=1e-12)
    # opposite vectors are the same brush direction: they reinforce instead of cancelling
    d = fields.combine((east, 1), (fields.constant(180), 1))(pts)
    np.testing.assert_allclose(np.abs(d), [[1, 0]] * 3, atol=1e-12)
    d = fields.combine((east, 1), (fields.constant(60), 1))(pts)
    np.testing.assert_allclose(np.abs(d), [[np.cos(np.radians(30)), 0.5]] * 3, atol=1e-12)
    # region blend: a soft mask sampled at the points
    mask = np.clip((np.arange(200) - 60) / 80, 0, 1)[None].repeat(100, 0)
    d = fields.combine((east, 1 - mask), (south, mask))(pts)
    np.testing.assert_allclose(np.abs(d[:2]), [[1, 0], [0, 1]], atol=1e-9)
    # no seams: along a line where a weak field crosses a strong one at right angles, the blend turns smoothly
    line = np.stack([np.linspace(0, 400, 801), np.full(801, 50.0)], axis=1)
    d = fields.combine((fields.radial((200, -1000)), 1.0), (east, 0.3))(line)
    assert np.abs((d[1:] * d[:-1]).sum(1)).min() > 0.99
    # a callable weight
    d = fields.combine((east, lambda p: (p[:, 0] < 100).astype(float)), (south, 0.01))(pts)
    assert abs(d[0, 0]) > 0.99 and abs(d[1, 1]) > 0.99
