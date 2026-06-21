"""Forge your own film stocks by combination edits.

This is the capability closed generators deliberately withhold: real, granular
control over the *look*, expressed as new film stocks you own and reuse. Because
a :class:`~analogforge.stock.FilmStock` is a fully numeric description, we can:

* **blend** two stocks along a continuum (``t`` from 0..1);
* **mix** several stocks with arbitrary weights;
* **cross** stocks by taking whole subsystems (curves from one, grain from
  another, halation from a third) — like splicing emulsion recipes;
* **mutate** a stock to explore nearby looks;
* **adjust** any named parameter directly.

Every forged stock records its ``lineage`` so its ancestry stays legible.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from .stock import FilmStock


# --------------------------------------------------------------------------
# validity clamping
# --------------------------------------------------------------------------
def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def sanitize(stock: FilmStock) -> FilmStock:
    """Clamp parameters into physically sensible ranges after editing."""
    for cc in (stock.curves.red, stock.curves.green, stock.curves.blue):
        cc.dmin = _clamp(cc.dmin, 0.0, 0.5)
        cc.dmax = _clamp(cc.dmax, cc.dmin + 0.3, 4.0)
        cc.gamma = _clamp(cc.gamma, 0.05, 3.0)
        cc.toe = _clamp(cc.toe, 0.01, 1.2)
        cc.shoulder = _clamp(cc.shoulder, 0.01, 1.2)
        cc.speed = _clamp(cc.speed, -0.6, 0.6)
    g = stock.grain
    g.rms = _clamp(g.rms, 0.0, 0.12)
    g.size = _clamp(g.size, 0.2, 5.0)
    g.chroma = _clamp(g.chroma, 0.0, 1.0)
    h = stock.halation
    h.strength = _clamp(h.strength, 0.0, 1.0)
    h.radius = _clamp(h.radius, 0.0, 60.0)
    h.threshold = _clamp(h.threshold, 0.2, 0.99)
    o = stock.optics
    o.acutance = _clamp(o.acutance, 0.0, 1.5)
    o.blur = _clamp(o.blur, 0.0, 8.0)
    o.vignette = _clamp(o.vignette, 0.0, 1.0)
    p = stock.print_
    p.gamma = _clamp(p.gamma, 0.2, 3.0)
    p.saturation = _clamp(p.saturation, 0.0, 3.0)
    stock.iso = int(_clamp(stock.iso, 1, 1_000_000))
    return stock


# --------------------------------------------------------------------------
# combination operations
# --------------------------------------------------------------------------
def blend(a: FilmStock, b: FilmStock, t: float = 0.5,
          name: Optional[str] = None) -> FilmStock:
    """Linearly interpolate every numeric parameter between ``a`` and ``b``.

    ``t = 0`` returns ``a``; ``t = 1`` returns ``b``; ``0.5`` is the midpoint.
    Process family and maker follow whichever side ``t`` is closer to.
    """
    t = float(t)
    fa, fb = a.flatten(), b.flatten()
    keys = set(fa) | set(fb)
    blended = {k: (1 - t) * fa.get(k, fb.get(k, 0.0)) + t * fb.get(k, fa.get(k, 0.0))
               for k in keys}
    base = (a if t < 0.5 else b)
    out = base.with_values(blended)
    out.process_family = (a if t < 0.5 else b).process_family
    out.name = name or f"{a.name} x {b.name} ({int(round(t * 100))}%)"
    out.maker = "AnalogForge"
    out.year = None
    out.lineage = [a.name, b.name]
    out.description = f"Blend of {a.name} and {b.name} at t={t:.2f}."
    return sanitize(out)


def mix(stocks: List[FilmStock], weights: Optional[List[float]] = None,
        name: Optional[str] = None) -> FilmStock:
    """Weighted average of several stocks across all numeric parameters."""
    if not stocks:
        raise ValueError("mix() needs at least one stock")
    if weights is None:
        weights = [1.0] * len(stocks)
    if len(weights) != len(stocks):
        raise ValueError("weights must match number of stocks")
    total = float(sum(weights)) or 1.0
    w = [x / total for x in weights]

    flats = [s.flatten() for s in stocks]
    keys = set().union(*flats)
    acc: Dict[str, float] = {k: 0.0 for k in keys}
    for wi, fi in zip(w, flats):
        for k in keys:
            acc[k] += wi * fi.get(k, 0.0)

    base = stocks[int(np.argmax(w))]
    out = base.with_values(acc)
    out.process_family = base.process_family
    out.name = name or "Mixed Stock"
    out.maker = "AnalogForge"
    out.year = None
    out.lineage = [s.name for s in stocks]
    out.description = "Weighted mix of " + ", ".join(
        f"{s.name} ({wi:.0%})" for s, wi in zip(stocks, w)
    )
    return sanitize(out)


def cross(base: FilmStock, *, curves: Optional[FilmStock] = None,
          grain: Optional[FilmStock] = None, halation: Optional[FilmStock] = None,
          optics: Optional[FilmStock] = None, print_: Optional[FilmStock] = None,
          spectral: Optional[FilmStock] = None, development: Optional[FilmStock] = None,
          name: Optional[str] = None) -> FilmStock:
    """Splice subsystems from different stocks onto ``base``.

    Example: tonal curves of Velvia, grain of Tri-X, halation of CineStill.
    """
    out = base.copy()
    sources = []
    if curves is not None:
        out.curves = curves.copy().curves
        sources.append(f"curves:{curves.name}")
    if grain is not None:
        out.grain = grain.copy().grain
        sources.append(f"grain:{grain.name}")
    if halation is not None:
        out.halation = halation.copy().halation
        sources.append(f"halation:{halation.name}")
    if optics is not None:
        out.optics = optics.copy().optics
        sources.append(f"optics:{optics.name}")
    if print_ is not None:
        out.print_ = print_.copy().print_
        sources.append(f"print:{print_.name}")
    if spectral is not None:
        out.spectral = spectral.copy().spectral
        sources.append(f"spectral:{spectral.name}")
    if development is not None:
        out.development = development.copy().development
        sources.append(f"development:{development.name}")

    out.name = name or f"Cross of {base.name}"
    out.maker = "AnalogForge"
    out.year = None
    out.lineage = [base.name] + sources
    out.description = "Crossed " + base.name + " with " + ", ".join(sources)
    return sanitize(out)


def mutate(stock: FilmStock, amount: float = 0.15, seed: int = 0,
           name: Optional[str] = None) -> FilmStock:
    """Randomly perturb numeric parameters to explore nearby looks.

    ``amount`` is the relative jitter (0.15 = up to ~15%). Small additive jitter
    is also applied so parameters that sit at zero (e.g. colour speed offsets)
    can still move.
    """
    rng = np.random.default_rng(seed)
    flat = stock.flatten()
    mutated = {}
    for k, v in flat.items():
        # Spectral matrix is left mostly alone to preserve colour integrity.
        scale = 0.3 if k.startswith("spectral") else 1.0
        rel = 1.0 + rng.uniform(-amount, amount) * scale
        absol = rng.normal(0.0, amount * 0.05) * scale
        mutated[k] = v * rel + absol
    out = stock.with_values(mutated)
    out.name = name or f"{stock.name} (mutation {seed})"
    out.maker = "AnalogForge"
    out.year = None
    out.lineage = [stock.name]
    out.description = f"Mutation of {stock.name} (amount={amount}, seed={seed})."
    return sanitize(out)


def adjust(stock: FilmStock, name: Optional[str] = None, **overrides) -> FilmStock:
    """Set named dotted parameters, e.g. ``adjust(s, **{'grain.rms': 0.03})``."""
    flat = stock.flatten()
    for key, value in overrides.items():
        dotted = key.replace("__", ".")
        if dotted not in flat:
            raise KeyError(f"Unknown parameter {dotted!r}. Try one of: "
                           f"{', '.join(sorted(flat)[:12])} ...")
        flat[dotted] = float(value)
    out = stock.with_values(flat)
    if name:
        out.name = name
    return sanitize(out)
