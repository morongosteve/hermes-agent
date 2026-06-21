"""Built-in film stocks.

These are *characterisations* of well-known emulsions, built from their widely
documented behaviour (ISO, contrast, colour bias, grain character, halation).
They are deliberately honest approximations — not exact datasheet transcriptions
— and they are meant as starting points to **develop with** and, more
importantly, to **combine and mutate** in the designer.

Each stock is normal Python data, so you can read exactly how it is defined and
why. Net image contrast for a negative is roughly ``film gamma * print gamma``;
reversal stocks carry their contrast in the film gamma itself.
"""

from __future__ import annotations

from typing import Dict, List

from .stock import (
    BW_NEGATIVE,
    COLOR_NEGATIVE,
    COLOR_REVERSAL,
    ChannelCurve,
    Curves,
    Development,
    FilmStock,
    Grain,
    Halation,
    Optics,
    Print,
    Spectral,
)


def _curves(dmax, gamma, *, r=0.0, g=0.0, b=0.0, toe=0.18, shoulder=0.22,
            dmin=0.1, gr=None, gg=None, gb=None) -> Curves:
    """Build a Curves triple. ``r/g/b`` shift each channel's speed (colour bias);
    ``gr/gg/gb`` optionally override per-channel gamma."""
    return Curves(
        red=ChannelCurve(dmin=dmin, dmax=dmax, gamma=gr or gamma, speed=r, toe=toe, shoulder=shoulder),
        green=ChannelCurve(dmin=dmin, dmax=dmax, gamma=gg or gamma, speed=g, toe=toe, shoulder=shoulder),
        blue=ChannelCurve(dmin=dmin, dmax=dmax, gamma=gb or gamma, speed=b, toe=toe, shoulder=shoulder),
    )


def _spectral(diag=0.92, off=0.04) -> Spectral:
    return Spectral(matrix=[
        [diag, off, off],
        [off, diag, off],
        [off, off, diag],
    ])


def _build() -> Dict[str, FilmStock]:
    stocks: Dict[str, FilmStock] = {}

    # ---- Colour negative -------------------------------------------------
    stocks["portra400"] = FilmStock(
        name="Kodak Portra 400", maker="Kodak", iso=400, year=2010,
        process_family=COLOR_NEGATIVE,
        description="Soft contrast, warm and forgiving skin tones, wide latitude. The portrait standard.",
        spectral=_spectral(0.90, 0.05),
        curves=_curves(2.2, 0.55, r=-0.02, b=0.03, toe=0.20, shoulder=0.28),
        grain=Grain(rms=0.016, size=1.1, chroma=0.30),
        halation=Halation(strength=0.06, radius=10, threshold=0.78),
        optics=Optics(acutance=0.20),
        print_=Print(gamma=1.50, balance=(1.05, 1.0, 0.95), saturation=1.02),
        development=Development(process="C-41"),
    )

    stocks["portra160"] = FilmStock(
        name="Kodak Portra 160", maker="Kodak", iso=160, year=2011,
        process_family=COLOR_NEGATIVE,
        description="Finer-grained, slightly cooler sibling of Portra 400 for studio/landscape.",
        spectral=_spectral(0.91, 0.045),
        curves=_curves(2.25, 0.56, r=-0.01, b=0.02, toe=0.18, shoulder=0.27),
        grain=Grain(rms=0.011, size=0.9, chroma=0.28),
        halation=Halation(strength=0.05, radius=9, threshold=0.80),
        optics=Optics(acutance=0.22),
        print_=Print(gamma=1.55, balance=(1.02, 1.0, 0.99), saturation=1.05),
        development=Development(process="C-41"),
    )

    stocks["gold200"] = FilmStock(
        name="Kodak Gold 200", maker="Kodak", iso=200, year=1988,
        process_family=COLOR_NEGATIVE,
        description="Warm, golden, nostalgic consumer film. Sunny saturation and amber midtones.",
        spectral=_spectral(0.89, 0.055),
        curves=_curves(2.15, 0.60, r=-0.03, g=-0.01, b=0.05, toe=0.20, shoulder=0.24),
        grain=Grain(rms=0.020, size=1.05, chroma=0.34),
        halation=Halation(strength=0.08, radius=11, threshold=0.74),
        optics=Optics(acutance=0.22),
        print_=Print(gamma=1.70, balance=(1.08, 1.01, 0.90), saturation=1.16),
        development=Development(process="C-41"),
    )

    stocks["ektar100"] = FilmStock(
        name="Kodak Ektar 100", maker="Kodak", iso=100, year=2008,
        process_family=COLOR_NEGATIVE,
        description="World's finest-grain colour negative; vivid, punchy saturation rivaling slide film.",
        spectral=_spectral(0.93, 0.03),
        curves=_curves(2.3, 0.65, r=-0.01, b=0.01, toe=0.16, shoulder=0.22),
        grain=Grain(rms=0.008, size=0.8, chroma=0.25),
        halation=Halation(strength=0.05, radius=9, threshold=0.80),
        optics=Optics(acutance=0.26),
        print_=Print(gamma=1.72, balance=(1.02, 1.0, 0.99), saturation=1.30),
        development=Development(process="C-41"),
    )

    stocks["superia400"] = FilmStock(
        name="Fujifilm Superia X-TRA 400", maker="Fujifilm", iso=400, year=1998,
        process_family=COLOR_NEGATIVE,
        description="Punchy consumer Fuji negative: signature vivid greens, cooler "
                    "slightly cyan shadows, more contrast and grain than the pro stocks.",
        spectral=_spectral(0.90, 0.05),
        curves=_curves(2.2, 0.60, r=-0.02, g=0.02, b=0.02, toe=0.18, shoulder=0.24),
        grain=Grain(rms=0.024, size=1.25, chroma=0.36),
        halation=Halation(strength=0.07, radius=11, threshold=0.76),
        optics=Optics(acutance=0.24),
        print_=Print(gamma=1.62, balance=(0.98, 1.03, 1.0), saturation=1.22),
        development=Development(process="C-41"),
    )

    stocks["pro400h"] = FilmStock(
        name="Fujifilm Pro 400H", maker="Fujifilm", iso=400, year=2004,
        process_family=COLOR_NEGATIVE,
        description="Airy, pastel palette with signature soft greens and cyans. Beloved for weddings.",
        spectral=_spectral(0.90, 0.05),
        curves=_curves(2.2, 0.55, r=0.02, g=-0.01, b=-0.01, toe=0.20, shoulder=0.30),
        grain=Grain(rms=0.015, size=1.1, chroma=0.30),
        halation=Halation(strength=0.05, radius=10, threshold=0.80),
        optics=Optics(acutance=0.18),
        print_=Print(gamma=1.48, balance=(0.97, 1.02, 1.02), saturation=0.96),
        development=Development(process="C-41"),
    )

    stocks["cinestill800t"] = FilmStock(
        name="CineStill 800T", maker="CineStill", iso=800, year=2012,
        process_family=COLOR_NEGATIVE,
        description="Tungsten-balanced ECN-2 stock with the rem-jet removed: cool daylight cast and "
                    "the famous red halation glow around lights.",
        spectral=_spectral(0.90, 0.05),
        curves=_curves(2.15, 0.60, r=0.04, b=-0.06, toe=0.22, shoulder=0.26),
        grain=Grain(rms=0.030, size=1.4, chroma=0.40),
        halation=Halation(strength=0.55, radius=20, threshold=0.66, color=(1.0, 0.28, 0.10)),
        optics=Optics(acutance=0.20),
        print_=Print(gamma=1.55, balance=(0.90, 1.0, 1.22), saturation=1.05),
        development=Development(process="ECN-2"),
    )

    # ---- Colour reversal / slide ----------------------------------------
    stocks["velvia50"] = FilmStock(
        name="Fujifilm Velvia 50", maker="Fujifilm", iso=50, year=1990,
        process_family=COLOR_REVERSAL,
        description="Legendary landscape slide film: extreme saturation, vivid greens/blues, high "
                    "contrast and very little latitude.",
        spectral=_spectral(0.95, 0.02),
        curves=_curves(3.0, 1.60, g=-0.02, b=-0.03, toe=0.10, shoulder=0.10),
        grain=Grain(rms=0.007, size=0.7, chroma=0.22),
        halation=Halation(strength=0.04, radius=8, threshold=0.82),
        optics=Optics(acutance=0.30),
        print_=Print(gamma=1.0, balance=(1.0, 1.02, 1.03), saturation=1.55),
        development=Development(process="E-6"),
    )

    stocks["ektachrome100"] = FilmStock(
        name="Kodak Ektachrome E100", maker="Kodak", iso=100, year=2018,
        process_family=COLOR_REVERSAL,
        description="Clean, accurate, slightly cool slide film with fine grain and moderate slide contrast.",
        spectral=_spectral(0.94, 0.025),
        curves=_curves(2.9, 1.35, r=-0.01, b=0.02, toe=0.12, shoulder=0.14),
        grain=Grain(rms=0.008, size=0.8, chroma=0.22),
        halation=Halation(strength=0.04, radius=8, threshold=0.82),
        optics=Optics(acutance=0.28),
        print_=Print(gamma=1.0, balance=(0.99, 1.0, 1.02), saturation=1.20),
        development=Development(process="E-6"),
    )

    # ---- Black & white ---------------------------------------------------
    stocks["trix400"] = FilmStock(
        name="Kodak Tri-X 400", maker="Kodak", iso=400, year=1954,
        process_family=BW_NEGATIVE,
        description="The photojournalist's classic: gritty, structured grain, gutsy midtone contrast.",
        spectral=_spectral(0.85, 0.075),
        curves=_curves(2.2, 0.62, toe=0.16, shoulder=0.24),
        grain=Grain(rms=0.032, size=1.4, mono=True, chroma=0.0, mid_weight=1.1),
        halation=Halation(strength=0.04, radius=9, threshold=0.80, color=(1.0, 1.0, 1.0)),
        optics=Optics(acutance=0.32),
        print_=Print(gamma=1.55),
        development=Development(process="B&W"),
    )

    stocks["hp5"] = FilmStock(
        name="Ilford HP5 Plus 400", maker="Ilford", iso=400, year=1989,
        process_family=BW_NEGATIVE,
        description="Smooth, wide-latitude B&W workhorse; softer and more forgiving than Tri-X.",
        spectral=_spectral(0.85, 0.075),
        curves=_curves(2.15, 0.58, toe=0.20, shoulder=0.28),
        grain=Grain(rms=0.027, size=1.5, mono=True, chroma=0.0),
        halation=Halation(strength=0.03, radius=9, threshold=0.82, color=(1.0, 1.0, 1.0)),
        optics=Optics(acutance=0.28),
        print_=Print(gamma=1.50),
        development=Development(process="B&W"),
    )

    return stocks


_STOCKS = _build()


def list_stocks() -> List[str]:
    """Return the sorted keys of all built-in stocks."""
    return sorted(_STOCKS.keys())


def get_stock(key: str) -> FilmStock:
    """Look up a built-in stock by key (case/space/hyphen-insensitive)."""
    norm = key.lower().replace(" ", "").replace("-", "").replace("_", "")
    for k, v in _STOCKS.items():
        if k == norm:
            return v.copy()
    # Fall back to matching display names.
    for v in _STOCKS.values():
        if v.name.lower().replace(" ", "").replace("-", "") == norm:
            return v.copy()
    raise KeyError(
        f"Unknown stock {key!r}. Available: {', '.join(list_stocks())}"
    )


def all_stocks() -> Dict[str, FilmStock]:
    return {k: v.copy() for k, v in _STOCKS.items()}
