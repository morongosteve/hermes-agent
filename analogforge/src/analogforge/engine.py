"""The film engine: turn a scene into a developed, printed photograph.

This is the orchestrator that walks an image through the whole imaging chain in
physically-meaningful order. Every step corresponds to a real stage documented
in the knowledge base:

    1. spectral sensitivity   – mix scene RGB into the three layer exposures
    2. exposure               – place the scene on the log-exposure axis
    3. development            – build density via the H&D curve (+ push/pull)
    4. print / scan           – invert the negative to a positive, balance colour
    5. grain                  – signal-dependent silver texture
    6. halation               – highlight glow reflected from the base
    7. optics                 – acutance, softness, vignette

Negative, reversal (slide) and black-and-white films all flow through the same
code; their differences live entirely in the :class:`~analogforge.stock.FilmStock`
parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from . import curves as _curves
from .grain import add_grain
from .halation import apply_halation
from .imaging import load_image, luminance, save_image
from .optics import apply_optics
from .stock import BW_NEGATIVE, FilmStock


@dataclass
class DevelopOptions:
    """Choices made at *develop* time (overrides on top of the stock)."""

    exposure: float = 0.0           # exposure compensation in stops
    push: Optional[float] = None    # override the stock's push/pull (stops)
    seed: int = 0                   # grain RNG seed
    grain: bool = True
    halation: bool = True
    optics: bool = True
    max_side: Optional[int] = None  # downscale longest side for speed/preview


def _spectral_mix(linear: np.ndarray, stock: FilmStock) -> np.ndarray:
    """Mix scene RGB into the exposure each emulsion layer receives."""
    m = np.asarray(stock.spectral.matrix, dtype=np.float32)
    # Normalise rows so a neutral scene stays neutral in exposure.
    row_sums = m.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    m = m / row_sums
    mixed = linear @ m.T
    return np.clip(mixed, 0.0, None)


def _develop_color(linear: np.ndarray, stock: FilmStock, opts: DevelopOptions):
    push = stock.development.push_pull if opts.push is None else opts.push
    gamma_gain = push * stock.development.dev_contrast_gain
    shadow_shift = push * stock.development.dev_shadow_loss

    exposure = _spectral_mix(linear, stock)
    log_e = _curves.scene_to_log_exposure(exposure, opts.exposure)
    log_e = log_e - shadow_shift  # pushing loses shadow exposure

    chans = (stock.curves.red, stock.curves.green, stock.curves.blue)
    pos = np.empty_like(linear)
    pg = float(stock.print_.gamma)
    for i, curve in enumerate(chans):
        d = _curves.density_from_log_exposure(log_e[..., i], curve, gamma_gain)
        # Print/scan: invert the negative. Bright scene -> high density ->
        # small (dmax-d) -> bright positive. The curve's shoulder thus becomes
        # highlight compression in the final image.
        pos_density = pg * (float(curve.dmax) - d)
        pos[..., i] = np.power(10.0, -pos_density)

    return _finish(pos, stock)


def _develop_bw(linear: np.ndarray, stock: FilmStock, opts: DevelopOptions):
    push = stock.development.push_pull if opts.push is None else opts.push
    gamma_gain = push * stock.development.dev_contrast_gain
    shadow_shift = push * stock.development.dev_shadow_loss

    # Panchromatic response: weight scene by the spectral matrix's green row
    # (a reasonable B&W sensitivity) falling back to luminance.
    m = np.asarray(stock.spectral.matrix, dtype=np.float32)
    weights = m[1] if m.shape == (3, 3) else np.array([0.2126, 0.7152, 0.0722])
    weights = np.clip(weights, 0, None)
    if weights.sum() <= 0:
        weights = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    weights = weights / weights.sum()

    mono_exposure = np.clip(linear @ weights, 0.0, None)
    log_e = _curves.scene_to_log_exposure(mono_exposure, opts.exposure) - shadow_shift

    curve = stock.curves.green  # master tone curve for the silver image
    d = _curves.density_from_log_exposure(log_e, curve, gamma_gain)
    pos_density = float(stock.print_.gamma) * (float(curve.dmax) - d)
    gray = np.power(10.0, -pos_density)
    pos = np.repeat(gray[..., None], 3, axis=2)
    return _finish(pos, stock, monochrome=True)


def _finish(pos: np.ndarray, stock: FilmStock, monochrome: bool = False) -> np.ndarray:
    """Normalise, balance colour and apply saturation / black-white points."""
    # Normalise so the brightest reachable value maps to ~1.
    peak = float(np.percentile(pos, 99.5))
    if peak > 1e-6:
        pos = pos / peak

    if not monochrome:
        balance = np.asarray(stock.print_.balance, dtype=np.float32).reshape(1, 1, 3)
        pos = pos * balance
        # Orange-mask removal nudges the colour balance cooler when enabled.
        if stock.print_.orange_mask > 1e-4:
            om = stock.print_.orange_mask
            pos = pos * np.array([1.0 - 0.10 * om, 1.0, 1.0 + 0.06 * om], dtype=np.float32)
        # Saturation around luminance.
        if abs(stock.print_.saturation - 1.0) > 1e-4:
            lum = luminance(pos)[..., None]
            pos = lum + (pos - lum) * stock.print_.saturation

    # Black / white point.
    bp, wp = stock.print_.black_point, stock.print_.white_point
    if wp - bp > 1e-4:
        pos = (pos - bp) / (wp - bp)

    return np.clip(pos, 0.0, None).astype(np.float32)


def develop_array(linear: np.ndarray, stock: FilmStock,
                  opts: Optional[DevelopOptions] = None) -> np.ndarray:
    """Develop a linear-light HxWx3 array with ``stock``. Returns linear positive."""
    opts = opts or DevelopOptions()

    if opts.max_side:
        linear = _maybe_downscale(linear, opts.max_side)

    if stock.process_family == BW_NEGATIVE:
        pos = _develop_bw(linear, stock, opts)
    else:
        pos = _develop_color(linear, stock, opts)

    if opts.halation:
        pos = apply_halation(pos, stock.halation)
    if opts.grain:
        pos = add_grain(pos, stock.grain, seed=opts.seed)
    if opts.optics:
        pos = apply_optics(pos, stock.optics)

    return np.clip(pos, 0.0, 1.0)


def develop_file(in_path: str | Path, out_path: str | Path, stock: FilmStock,
                 opts: Optional[DevelopOptions] = None) -> Path:
    """Develop an image file and write the result. Returns the output path."""
    linear = load_image(in_path)
    pos = develop_array(linear, stock, opts)
    return save_image(pos, out_path)


def _maybe_downscale(linear: np.ndarray, max_side: int) -> np.ndarray:
    from PIL import Image

    from .imaging import linear_to_srgb, srgb_to_linear

    h, w = linear.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return linear
    scale = max_side / longest
    new = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    srgb = linear_to_srgb(np.clip(linear, 0, 1))
    img = Image.fromarray((srgb * 255 + 0.5).astype(np.uint8), "RGB").resize(new, Image.LANCZOS)
    return srgb_to_linear(np.asarray(img, dtype=np.float32) / 255.0)
