import numpy as np

from analogforge import designer, library
from analogforge.stock import FilmStock


def test_blend_endpoints_and_midpoint():
    a = library.get_stock("portra400")
    b = library.get_stock("velvia50")

    at0 = designer.blend(a, b, 0.0)
    at1 = designer.blend(a, b, 1.0)
    mid = designer.blend(a, b, 0.5)

    fa, fb = a.flatten(), b.flatten()
    # shared key: print saturation
    k = "print_.saturation"
    assert abs(at0.flatten()[k] - fa[k]) < 1e-6
    assert abs(at1.flatten()[k] - fb[k]) < 1e-6
    assert abs(mid.flatten()[k] - 0.5 * (fa[k] + fb[k])) < 1e-6
    assert mid.lineage == [a.name, b.name]


def test_blend_picks_process_family_by_t():
    a = library.get_stock("portra400")     # color_negative
    b = library.get_stock("velvia50")      # color_reversal
    assert designer.blend(a, b, 0.2).process_family == a.process_family
    assert designer.blend(a, b, 0.8).process_family == b.process_family


def test_mix_weighted_average():
    a = library.get_stock("portra400")
    b = library.get_stock("ektar100")
    out = designer.mix([a, b], [3.0, 1.0])
    k = "print_.saturation"
    expect = (3 * a.flatten()[k] + 1 * b.flatten()[k]) / 4.0
    assert abs(out.flatten()[k] - expect) < 1e-6


def test_cross_swaps_subsystems():
    base = library.get_stock("ektachrome100")
    grain_src = library.get_stock("trix400")
    hal_src = library.get_stock("cinestill800t")
    out = designer.cross(base, grain=grain_src, halation=hal_src)
    assert abs(out.grain.rms - grain_src.grain.rms) < 1e-6
    assert abs(out.halation.strength - hal_src.halation.strength) < 1e-6
    # curves untouched -> still base's
    assert abs(out.curves.green.gamma - base.curves.green.gamma) < 1e-6


def test_mutate_is_valid_and_different():
    a = library.get_stock("gold200")
    m = designer.mutate(a, amount=0.2, seed=7)
    # sanitised into valid ranges
    assert 0.05 <= m.curves.green.gamma <= 3.0
    assert 0.0 <= m.grain.rms <= 0.12
    # actually changed something
    assert m.flatten() != a.flatten()


def test_adjust_named_param():
    a = library.get_stock("portra400")
    out = designer.adjust(a, name="Tweaked", **{"grain.rms": 0.04})
    assert abs(out.grain.rms - 0.04) < 1e-9
    assert out.name == "Tweaked"


def test_stock_json_roundtrip(tmp_path):
    a = library.get_stock("cinestill800t")
    p = a.save(tmp_path / "cs.json")
    b = FilmStock.load(p)
    assert a.flatten() == b.flatten()
    assert a.name == b.name and a.process_family == b.process_family


def test_flatten_with_values_roundtrip():
    a = library.get_stock("hp5")
    flat = a.flatten()
    rebuilt = a.with_values(flat)
    assert rebuilt.flatten() == flat
