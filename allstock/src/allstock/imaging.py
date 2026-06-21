"""Low-level image helpers.

Everything in the film engine happens in *linear, scene-referred* light, because
that is the domain where exposure, density and optical effects are physically
meaningful. These helpers move images in and out of that domain and provide a
fast Gaussian blur (used by grain, halation and MTF) without a SciPy dependency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image


# --------------------------------------------------------------------------
# sRGB <-> linear  (IEC 61966-2-1 transfer function)
# --------------------------------------------------------------------------
def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    """Decode display-referred sRGB (0..1) to linear light."""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    """Encode linear light back to sRGB (0..1)."""
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------
def load_image(path: str | Path) -> np.ndarray:
    """Load an image as an HxWx3 float array in linear light (0..1+)."""
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return srgb_to_linear(arr).astype(np.float32)


def save_image(arr: np.ndarray, path: str | Path) -> Path:
    """Save a linear-light float array to an 8-bit sRGB file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    srgb = linear_to_srgb(np.clip(arr, 0.0, 1.0))
    out = np.clip(srgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(out, mode="RGB").save(path)
    return path


def to_uint8_srgb(arr: np.ndarray) -> np.ndarray:
    srgb = linear_to_srgb(np.clip(arr, 0.0, 1.0))
    return np.clip(srgb * 255.0 + 0.5, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------
# luminance / blur
# --------------------------------------------------------------------------
# Rec.709 luminance weights (linear light).
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def luminance(arr: np.ndarray) -> np.ndarray:
    """Linear-light luminance, HxW."""
    return arr @ LUMA


def _gaussian_kernel1d(sigma: float) -> np.ndarray:
    radius = max(1, int(round(sigma * 3.0)))
    x = np.arange(-radius, radius + 1, dtype=np.float32)
    k = np.exp(-(x ** 2) / (2.0 * sigma * sigma))
    k /= k.sum()
    return k


def _blur1d(arr: np.ndarray, kernel: np.ndarray, axis: int) -> np.ndarray:
    """Convolve ``arr`` with a 1-D kernel along ``axis`` (edge-padded)."""
    pad = len(kernel) // 2
    pad_width = [(pad, pad) if i == axis else (0, 0) for i in range(arr.ndim)]
    padded = np.pad(arr, pad_width, mode="edge")
    out = np.zeros_like(arr, dtype=np.float32)
    n = arr.shape[axis]
    for i, w in enumerate(kernel):
        sl = [slice(None)] * arr.ndim
        sl[axis] = slice(i, i + n)
        out += w * padded[tuple(sl)]
    return out


def gaussian_blur(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Separable Gaussian blur in pure NumPy (keeps linear-light float precision).

    Works on 2-D (HxW) and 3-D (HxWxC) arrays. ``sigma`` <= 0 is a no-op. We use
    NumPy rather than Pillow's filter because Pillow's GaussianBlur does not
    accept 32-bit float ("F") images.
    """
    if sigma is None or sigma <= 1e-4:
        return arr
    arr = arr.astype(np.float32, copy=False)
    kernel = _gaussian_kernel1d(float(sigma))
    out = _blur1d(arr, kernel, axis=1)
    out = _blur1d(out, kernel, axis=0)
    return out


def radial_falloff(shape: Tuple[int, int], amount: float) -> np.ndarray:
    """A 0..1 vignette mask (1 at centre). ``amount`` 0 = none, 1 = strong."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    r = np.sqrt(((xx - cx) / (w / 2.0)) ** 2 + ((yy - cy) / (h / 2.0)) ** 2)
    r = np.clip(r / np.sqrt(2.0), 0.0, 1.0)
    return 1.0 - amount * (r ** 2)
