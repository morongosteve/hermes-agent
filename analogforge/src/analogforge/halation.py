"""Halation and optical bloom.

When a bright highlight is imaged, some light passes straight through the
emulsion, reflects off the back of the film base and re-exposes the emulsion
from behind in a soft ring around the source. The **anti-halation** layer (or
the rem-jet backing on motion-picture stock) normally absorbs this light. Remove
it — as Cinestill does to ECN-2 stock to make 800T — and bright sources gain the
unmistakable red/orange halo, because the red-sensitive layer sits closest to
the base and is re-exposed most.

We model it as: isolate highlights above a threshold, spread them with a large
Gaussian, tint by the halation colour, and screen-composite back over the image.
"""

from __future__ import annotations

import numpy as np

from .imaging import gaussian_blur, luminance
from .stock import Halation


def apply_halation(positive_linear: np.ndarray, hal: Halation) -> np.ndarray:
    if hal.strength <= 1e-4 or hal.radius <= 1e-3:
        return positive_linear

    lum = luminance(positive_linear)
    # Smooth highlight mask above the threshold.
    denom = max(1.0 - hal.threshold, 1e-3)
    mask = np.clip((lum - hal.threshold) / denom, 0.0, 1.0)
    mask = mask ** 2  # bias toward the brightest sources

    bloom = gaussian_blur(mask, hal.radius)
    if bloom.max() > 1e-6:
        bloom = bloom / bloom.max()

    color = np.asarray(hal.color, dtype=np.float32).reshape(1, 1, 3)
    glow = np.clip(hal.strength * bloom[..., None] * color, 0.0, 1.0)

    # Screen blend keeps values bounded and reads like added light.
    base = np.clip(positive_linear, 0.0, 1.0)
    out = 1.0 - (1.0 - base) * (1.0 - glow)
    return out.astype(np.float32)
