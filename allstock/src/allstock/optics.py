"""Optical character: acutance (edge effects), softness and vignetting.

Film does not simply low-pass an image. Development chemistry exhausts faster at
high-contrast boundaries, producing the classic **adjacency / Eberhard effect**:
a slight overshoot at edges that the eye reads as crispness ("acutance") even
when fine-detail MTF is modest. We approximate it with a controlled unsharp
mask. ``blur`` adds overall softness (limited MTF) and ``vignette`` darkens the
corners the way real lenses and film holders do.
"""

from __future__ import annotations

import numpy as np

from .imaging import gaussian_blur, radial_falloff
from .stock import Optics


def apply_optics(positive_linear: np.ndarray, optics: Optics) -> np.ndarray:
    out = positive_linear

    if optics.blur > 1e-3:
        out = gaussian_blur(out, optics.blur)

    if optics.acutance > 1e-4:
        # Unsharp mask: out + amount * (out - blurred).
        low = gaussian_blur(out, 1.4)
        out = out + optics.acutance * (out - low)

    if optics.vignette > 1e-4:
        mask = radial_falloff(out.shape[:2], optics.vignette)
        out = out * mask[..., None]

    return np.clip(out, 0.0, None).astype(np.float32)
