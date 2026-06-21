import numpy as np
import pytest

from allstock import library
from allstock.curves import density_from_log_exposure, scene_to_log_exposure
from allstock.engine import DevelopOptions, develop_array
from allstock.imaging import linear_to_srgb, srgb_to_linear
from allstock.stock import ChannelCurve


def _scene(h=48, w=64):
    """A linear test scene: horizontal luminance ramp + colour variation + a hotspot."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = (xx / (w - 1))[..., None]
    rgb = base * np.array([1.0, 0.8, 0.6], dtype=np.float32)
    rgb[2:6, 2:6] = 1.5  # clipped highlight to exercise shoulder + halation
    return np.clip(rgb, 0, None)


def test_srgb_roundtrip():
    x = np.linspace(0, 1, 256).astype(np.float32)
    back = linear_to_srgb(srgb_to_linear(x))
    assert np.allclose(x, back, atol=1e-4)


def test_characteristic_curve_monotonic_and_bounded():
    c = ChannelCurve(dmin=0.1, dmax=2.2, gamma=0.6, toe=0.18, shoulder=0.22)
    log_e = np.linspace(-4, 2, 500)
    d = density_from_log_exposure(log_e, c)
    assert np.all(np.diff(d) >= -1e-6)          # non-decreasing
    assert d.min() >= c.dmin - 1e-6
    assert d.max() <= c.dmax + 1e-6


def test_push_increases_contrast():
    c = ChannelCurve()
    log_e = np.linspace(-2, 1, 200)
    base = density_from_log_exposure(log_e, c, gamma_gain=0.0)
    pushed = density_from_log_exposure(log_e, c, gamma_gain=0.3)
    # Pushed curve should span a larger density range in the straight section.
    assert (pushed.max() - pushed.min()) >= (base.max() - base.min())


def test_scene_to_log_exposure_orders_brightness():
    le = scene_to_log_exposure(np.array([0.01, 0.18, 1.0], dtype=np.float32))
    assert le[0] < le[1] < le[2]


@pytest.mark.parametrize("key", library.list_stocks())
def test_every_stock_develops(key):
    scene = _scene()
    stock = library.get_stock(key)
    out = develop_array(scene, stock, DevelopOptions(seed=1))
    assert out.shape == scene.shape
    assert np.isfinite(out).all()
    assert out.min() >= 0.0 and out.max() <= 1.0 + 1e-5


def test_bw_output_is_neutral():
    scene = _scene()
    out = develop_array(scene, library.get_stock("trix400"),
                        DevelopOptions(grain=False))
    # All three channels should be (near) equal for a B&W stock.
    assert np.allclose(out[..., 0], out[..., 1], atol=1e-3)
    assert np.allclose(out[..., 1], out[..., 2], atol=1e-3)


def test_negative_and_reversal_differ():
    scene = _scene()
    neg = develop_array(scene, library.get_stock("portra400"), DevelopOptions(grain=False))
    rev = develop_array(scene, library.get_stock("velvia50"), DevelopOptions(grain=False))
    assert not np.allclose(neg, rev, atol=0.02)


def test_halation_brightens_around_hotspot():
    scene = _scene()
    cs = library.get_stock("cinestill800t")
    with_hal = develop_array(scene, cs, DevelopOptions(grain=False, halation=True))
    no_hal = develop_array(scene, cs, DevelopOptions(grain=False, halation=False))
    # Region just outside the hotspot should be brighter (redder) with halation on.
    ring = (slice(6, 10), slice(6, 10))
    assert with_hal[ring][..., 0].mean() >= no_hal[ring][..., 0].mean()


def test_grain_adds_variation():
    scene = np.full((40, 40, 3), 0.3, dtype=np.float32)  # flat mid-grey
    stock = library.get_stock("trix400")
    clean = develop_array(scene, stock, DevelopOptions(grain=False))
    grainy = develop_array(scene, stock, DevelopOptions(grain=True, seed=3))
    assert grainy.std() > clean.std()
