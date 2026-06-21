"""AllStock — physically-grounded analog film emulation, a film-stock
designer, an analog knowledge base, and analog-aware image generation.

Replicate film from emulsion to dried negative, and forge your own stocks.

Quick start
-----------
>>> from allstock import library, engine
>>> stock = library.get_stock("portra400")
>>> engine.develop_file("in.jpg", "out.jpg", stock)            # doctest: +SKIP

Forge a new stock
-----------------
>>> from allstock import designer
>>> custom = designer.blend(library.get_stock("portra400"),
...                         library.get_stock("velvia50"), 0.3)

Generate + truly develop
------------------------
>>> from allstock import generate                            # doctest: +SKIP
>>> pos, info = generate.generate_and_develop("a misty harbour at dawn",
...     library.get_stock("cinestill800t"), provider="zai")     # doctest: +SKIP
"""

from __future__ import annotations

from . import curves, designer, engine, generate, imaging, knowledge, library
from .engine import DevelopOptions, develop_array, develop_file
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

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # modules
    "curves", "designer", "engine", "generate", "imaging", "knowledge", "library",
    # engine
    "DevelopOptions", "develop_array", "develop_file",
    # model
    "FilmStock", "ChannelCurve", "Curves", "Spectral", "Grain", "Halation",
    "Optics", "Print", "Development",
    "COLOR_NEGATIVE", "COLOR_REVERSAL", "BW_NEGATIVE",
]
