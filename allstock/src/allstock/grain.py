"""Film grain synthesis.

Grain is the visible texture of developed silver crystals. Two properties make
real grain different from the flat Gaussian noise most "film filters" add:

1. **It is signal-dependent.** Grain is most visible in the mid-tones and is
   suppressed in clean shadows and in blown highlights. We shape its amplitude
   along the tone scale with three control weights.
2. **It has a physical scale.** Crystals clump into structures of a finite size,
   so we band-limit white noise with a blur whose radius is the grain ``size``
   (larger for faster, higher-ISO film).

Colour film grain is partly shared across the dye layers and partly independent;
the ``chroma`` control blends between purely monochrome grain (B&W silver) and
fully independent per-channel grain.
"""

from __future__ import annotations

import numpy as np

from .imaging import gaussian_blur, luminance
from .stock import Grain


def _tone_weight(lum: np.ndarray, g: Grain) -> np.ndarray:
    """Piece-wise tent through (shadow, mid, highlight) weights over L in 0..1."""
    lo = g.shadow_weight + (g.mid_weight - g.shadow_weight) * np.clip(lum / 0.5, 0, 1)
    hi = g.mid_weight + (g.highlight_weight - g.mid_weight) * np.clip((lum - 0.5) / 0.5, 0, 1)
    return np.where(lum < 0.5, lo, hi)


def _unit_noise(shape, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Band-limited noise normalised to ~unit standard deviation."""
    n = rng.standard_normal(shape).astype(np.float32)
    if sigma > 1e-3:
        n = gaussian_blur(n, sigma)
    std = float(n.std())
    if std > 1e-6:
        n = n / std
    return n


def add_grain(positive_linear: np.ndarray, grain: Grain, seed: int = 0) -> np.ndarray:
    """Add signal-dependent grain to a positive linear image.

    Grain is applied in an approximately perceptual (gamma ~2.2) domain so its
    amplitude reads naturally across the tone scale, then converted back.
    """
    if grain.rms <= 1e-5:
        return positive_linear

    rng = np.random.default_rng(seed)
    h, w = positive_linear.shape[:2]
    sigma = max(grain.size * 0.6, 0.0)

    lum = np.clip(luminance(positive_linear), 0.0, 1.0)
    weight = _tone_weight(lum, grain).astype(np.float32)

    # Perceptual domain.
    p = np.power(np.clip(positive_linear, 0.0, None), 1.0 / 2.2)

    mono = _unit_noise((h, w), sigma, rng)
    if grain.mono or grain.chroma <= 1e-3:
        noise = np.repeat(mono[..., None], 3, axis=2)
    else:
        chans = [_unit_noise((h, w), sigma, rng) for _ in range(3)]
        chroma_noise = np.stack(chans, axis=-1)
        noise = (1.0 - grain.chroma) * mono[..., None] + grain.chroma * chroma_noise

    p = p + noise * (grain.rms * weight[..., None])
    return np.power(np.clip(p, 0.0, None), 2.2).astype(np.float32)
