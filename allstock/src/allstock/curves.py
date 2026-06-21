"""Characteristic (Hurter-Driffield) curve evaluation.

The H&D curve plots developed **density** against **log-exposure**. Its shape is
the chief reason film looks like film:

* a soft **toe** gently compresses shadows (no hard clipping to black);
* a **straight-line** middle whose slope is the **gamma** (contrast);
* a long **shoulder** that rolls highlights off gracefully toward ``dmax`` —
  this highlight compression is the most-imitated quality of negative film.

We build the curve from soft-plus blends so every region is smooth and every
control (toe / gamma / shoulder / dmin / dmax / speed) maps to a real, separable
behaviour. See the ``characteristic-curve`` topic in the knowledge base.
"""

from __future__ import annotations

import numpy as np

from .stock import ChannelCurve


def softplus(x: np.ndarray, k: float) -> np.ndarray:
    """Numerically-stable soft-plus with softness ``k``.

    ``k -> 0`` approaches ``max(x, 0)``; larger ``k`` rounds the corner. Used to
    synthesise the soft toe and shoulder of the curve.
    """
    k = max(float(k), 1e-4)
    z = x / k
    # softplus(z) = max(z,0) + log1p(exp(-|z|))   (stable form)
    return k * (np.maximum(z, 0.0) + np.log1p(np.exp(-np.abs(z))))


def density_from_log_exposure(log_e: np.ndarray, curve: ChannelCurve,
                              gamma_gain: float = 0.0) -> np.ndarray:
    """Map log-exposure to developed density for one layer.

    Parameters
    ----------
    log_e:
        Array of log10 exposure values (typically about -3..0 for a normal scene).
    curve:
        The :class:`~allstock.stock.ChannelCurve` for this layer.
    gamma_gain:
        Additional contrast added by development (push processing). Positive
        values steepen the straight-line section, as longer development does.
    """
    dmin = float(curve.dmin)
    dmax = float(curve.dmax)
    gamma = max(float(curve.gamma) + float(gamma_gain), 1e-3)
    d_range = max(dmax - dmin, 1e-3)

    # Position along the curve, scaled into density units by gamma. The speed
    # point shifts the whole curve left/right (more/less sensitive film).
    x = (log_e - float(curve.speed)) * gamma

    # Soft toe: density rises from ~0.
    t = softplus(x, curve.toe)
    # Soft shoulder: clamp toward d_range with rounded corner.
    d = t - softplus(t - d_range, curve.shoulder)
    d = np.clip(d, 0.0, d_range)
    return dmin + d


def scene_to_log_exposure(linear: np.ndarray, exposure_stops: float = 0.0,
                          mid_gray: float = 0.184) -> np.ndarray:
    """Convert linear scene values to log10 exposure on the film.

    ``mid_gray`` anchors 18% gray near the centre of the straight-line section.
    ``exposure_stops`` shifts the whole image up/down the curve (metering).
    """
    gain = 2.0 ** float(exposure_stops)
    e = np.clip(linear * gain, 1e-6, None) / mid_gray
    return np.log10(e)


def sample_curve(curve: ChannelCurve, gamma_gain: float = 0.0,
                 lo: float = -3.0, hi: float = 1.0, n: int = 256):
    """Return ``(log_e, density)`` arrays for plotting / inspection."""
    log_e = np.linspace(lo, hi, n)
    dens = density_from_log_exposure(log_e, curve, gamma_gain)
    return log_e, dens
