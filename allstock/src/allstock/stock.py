"""The film-stock data model.

A :class:`FilmStock` is a *complete, physically-motivated parameterisation* of a
photographic film. Every stock — whether a faithful model of a real emulsion
(Portra 400, Tri-X...) or one a user *forges* from scratch — is described by the
same set of parameters. Because the description is fully numeric and structured,
two stocks can be blended, crossed, or mutated to create new ones (see
:mod:`allstock.designer`). This is the customisation freedom that closed
generators deliberately withhold.

The parameter groups follow the real imaging chain:

    scene light
       -> spectral sensitivity of the three emulsion layers      (``spectral``)
       -> exposure placed on each layer's characteristic curve   (``curves``)
       -> silver/dye density built up during development          (``curves``, ``development``)
       -> grain (signal-dependent silver clumping)               (``grain``)
       -> halation (light reflected from the film base)          (``halation``)
       -> optical MTF / acutance of lens+emulsion                (``optics``)
       -> print / scan transform back to a positive image        (``print_``)

Nothing here is a magic "filter": each field maps to a documented effect in the
:mod:`allstock.knowledge` base.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Film process families. These pick the broad mathematical behaviour of the
# transfer (a negative inverts and has a long highlight shoulder; a reversal /
# slide film is positive-working with steep contrast and little latitude).
COLOR_NEGATIVE = "color_negative"
COLOR_REVERSAL = "color_reversal"  # slide / transparency (E-6)
BW_NEGATIVE = "bw_negative"

PROCESS_FAMILIES = (COLOR_NEGATIVE, COLOR_REVERSAL, BW_NEGATIVE)


@dataclass
class ChannelCurve:
    """Hurter-Driffield (characteristic) curve for one emulsion layer.

    Density is built as a function of log-exposure with a soft *toe*, a
    straight-line section whose slope is ``gamma`` (the contrast), and a soft
    *shoulder* that rolls highlights off toward ``dmax``. Differences between the
    red/green/blue channel curves are what give a stock its colour signature and
    its tonal "fingerprint".
    """

    dmin: float = 0.10          # base + fog density (floor)
    dmax: float = 2.20          # maximum density (ceiling)
    gamma: float = 0.62         # slope of the straight-line region (contrast)
    speed: float = 0.0          # horizontal shift of the curve (film speed point)
    toe: float = 0.18           # softness of the toe (shadow roll-in)
    shoulder: float = 0.22      # softness of the shoulder (highlight roll-off)

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class Curves:
    """The three layer curves. Equal curves => neutral; offsets => colour cast."""

    red: ChannelCurve = field(default_factory=ChannelCurve)
    green: ChannelCurve = field(default_factory=ChannelCurve)
    blue: ChannelCurve = field(default_factory=ChannelCurve)


@dataclass
class Spectral:
    """Spectral sensitivity crosstalk between scene RGB and the film layers.

    A 3x3 matrix mixing scene linear RGB into the exposure each layer receives.
    The identity matrix means perfectly separated layers; off-diagonal terms
    model the real overlap of the sensitising-dye sensitivity bands, which
    softens and "binds" colour the way film does.
    """

    matrix: List[List[float]] = field(
        default_factory=lambda: [
            [1.00, 0.00, 0.00],
            [0.00, 1.00, 0.00],
            [0.00, 0.00, 1.00],
        ]
    )


@dataclass
class Grain:
    """Signal-dependent silver grain.

    Real grain is *not* uniform Gaussian noise: it is the clumping of developed
    silver, so its visibility depends on local density (it peaks in the
    mid-tones and is suppressed in clean shadows and blown highlights). ``rms``
    sets the overall amplitude (cf. RMS granularity on datasheets), ``size`` the
    physical grain scale in pixels, and the three ``*_weight`` terms shape how
    grain rides the tone scale.
    """

    rms: float = 0.018          # overall amplitude (0 = clean, ~0.05 = heavy)
    size: float = 1.1           # grain blob radius in pixels (ISO/format scaled)
    chroma: float = 0.35        # 0 = monochrome grain, 1 = full per-channel chroma
    shadow_weight: float = 0.6
    mid_weight: float = 1.0
    highlight_weight: float = 0.4
    mono: bool = False          # force single-channel grain (B&W silver)


@dataclass
class Halation:
    """Halation: light that passes through the emulsion, reflects off the base
    and re-exposes the film around bright sources. The anti-halation layer (or
    rem-jet on motion film) normally suppresses it; remove it (CineStill 800T)
    and you get the signature red/orange glow around highlights."""

    strength: float = 0.10      # 0 = none, 1 = strong glow
    radius: float = 12.0        # spread in pixels
    threshold: float = 0.72     # only highlights brighter than this bloom
    color: Tuple[float, float, float] = (1.0, 0.34, 0.12)  # red-orange


@dataclass
class Optics:
    """Lens + emulsion MTF and edge effects."""

    acutance: float = 0.25      # adjacency/edge enhancement (the "film sharpness")
    blur: float = 0.0           # gentle low-pass (softness), in pixels
    vignette: float = 0.0       # corner falloff, 0..1


@dataclass
class Print:
    """Print / scan transform that returns the (inverted) negative to a viewable
    positive. Real film looks are a *print-through*: camera-negative character
    plus paper/scanner character. ``gamma`` is the paper/scan contrast,
    ``balance`` the colour-balance (white-point) gains applied at print time,
    ``orange_mask`` models removal of the colour-negative integral mask."""

    gamma: float = 1.0
    balance: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    saturation: float = 1.0
    black_point: float = 0.0
    white_point: float = 1.0
    orange_mask: float = 0.0    # strength of the negative's orange mask removal


@dataclass
class Development:
    """Process state that the user can change at *develop* time. These are not
    fixed properties of the emulsion but choices made in the darkroom."""

    process: str = "C-41"       # C-41 / E-6 / ECN-2 / B&W
    push_pull: float = 0.0      # stops of push (+) or pull (-)
    dev_contrast_gain: float = 0.18   # how strongly push/pull steepens gamma
    dev_shadow_loss: float = 0.12     # shadow density lost per stop of push
    dry_curl: float = 0.0       # cosmetic: residual non-uniformity from drying


@dataclass
class FilmStock:
    """A complete film stock. See module docstring for the parameter groups."""

    name: str = "Custom Stock"
    maker: str = "AllStock"
    iso: int = 400
    process_family: str = COLOR_NEGATIVE
    year: Optional[int] = None
    description: str = ""
    # The physical chain
    spectral: Spectral = field(default_factory=Spectral)
    curves: Curves = field(default_factory=Curves)
    grain: Grain = field(default_factory=Grain)
    halation: Halation = field(default_factory=Halation)
    optics: Optics = field(default_factory=Optics)
    print_: Print = field(default_factory=Print)
    development: Development = field(default_factory=Development)
    # Provenance: which stocks this one was forged from (for the designer).
    lineage: List[str] = field(default_factory=list)

    # -- serialisation -----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        # Convert tuples (e.g. colour, balance) to lists so the structure is
        # JSON-friendly *and* mutable for the designer's parameter editing.
        return _tuples_to_lists(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FilmStock":
        return _build_dataclass(cls, data)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "FilmStock":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def copy(self) -> "FilmStock":
        return FilmStock.from_dict(self.to_dict())

    @property
    def is_monochrome(self) -> bool:
        return self.process_family == BW_NEGATIVE

    @property
    def is_reversal(self) -> bool:
        return self.process_family == COLOR_REVERSAL

    # -- numeric view for the designer ------------------------------------
    def flatten(self) -> Dict[str, float]:
        """Return every numeric leaf as a flat ``dotted.key -> float`` mapping.

        This lets the designer blend/mutate stocks generically without having to
        know about every individual parameter.
        """
        out: Dict[str, float] = {}
        _flatten(self.to_dict(), "", out)
        return out

    def with_values(self, flat: Dict[str, float]) -> "FilmStock":
        """Return a new stock with numeric leaves replaced from ``flat``."""
        data = self.to_dict()
        for key, value in flat.items():
            _set_path(data, key.split("."), value)
        return FilmStock.from_dict(data)

    def summary(self) -> str:
        c = self.curves
        avg_gamma = (c.red.gamma + c.green.gamma + c.blue.gamma) / 3.0
        bits = [
            f"{self.name}  [{self.maker}, ISO {self.iso}, {self.process_family}]",
            f"  contrast (avg gamma): {avg_gamma:.2f}",
            f"  grain rms/size:       {self.grain.rms:.3f} / {self.grain.size:.2f}px",
            f"  halation:             {self.halation.strength:.2f} @ {self.halation.radius:.0f}px",
            f"  process:              {self.development.process}",
        ]
        if self.lineage:
            bits.append(f"  forged from:          {', '.join(self.lineage)}")
        if self.description:
            bits.append(f"  {self.description}")
        return "\n".join(bits)


# --------------------------------------------------------------------------
# helpers for (de)serialisation and the flat numeric view
# --------------------------------------------------------------------------
def _tuples_to_lists(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _tuples_to_lists(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_tuples_to_lists(v) for v in obj]
    return obj


def _build_dataclass(cls: type, data: Dict[str, Any]) -> Any:
    """Recursively rebuild nested dataclasses from a plain dict."""
    kwargs: Dict[str, Any] = {}
    type_hints = {f.name: f.type for f in fields(cls)}
    for f in fields(cls):
        if f.name not in data:
            continue
        value = data[f.name]
        ftype = f.type
        # Resolve nested dataclasses by their default factory type where possible.
        nested = _nested_dataclass_type(cls, f.name)
        if nested is not None and isinstance(value, dict):
            kwargs[f.name] = _build_dataclass(nested, value)
        elif isinstance(value, list) and f.name == "color":
            kwargs[f.name] = tuple(value)
        elif isinstance(value, list) and f.name == "balance":
            kwargs[f.name] = tuple(value)
        else:
            kwargs[f.name] = value
    _ = type_hints  # kept for clarity / future strictness
    return cls(**kwargs)


_NESTED_TYPES = {
    "spectral": Spectral,
    "curves": Curves,
    "grain": Grain,
    "halation": Halation,
    "optics": Optics,
    "print_": Print,
    "development": Development,
    "red": ChannelCurve,
    "green": ChannelCurve,
    "blue": ChannelCurve,
}


def _nested_dataclass_type(parent: type, field_name: str) -> Optional[type]:
    t = _NESTED_TYPES.get(field_name)
    if t is not None and is_dataclass(t):
        return t
    return None


_SKIP_FLATTEN = {"matrix"}  # handled, but kept out of scalar blending by default


def _flatten(obj: Any, prefix: str, out: Dict[str, float]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            _flatten(v, key, out)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            key = f"{prefix}.{i}"
            _flatten(v, key, out)
    elif isinstance(obj, bool):
        # booleans are not blended numerically
        return
    elif isinstance(obj, (int, float)):
        out[prefix] = float(obj)


def _set_path(data: Any, path: List[str], value: float) -> None:
    key = path[0]
    if isinstance(data, list):
        idx = int(key)
        if len(path) == 1:
            # preserve int-ness for things like iso
            data[idx] = value
        else:
            _set_path(data[idx], path[1:], value)
        return
    if len(path) == 1:
        # preserve int for integer-typed leaves
        if isinstance(data.get(key), int) and float(value).is_integer():
            data[key] = int(value)
        else:
            data[key] = value
    else:
        _set_path(data[key], path[1:], value)
