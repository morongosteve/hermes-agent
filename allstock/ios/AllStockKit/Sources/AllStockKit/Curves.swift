// Curves.swift — characteristic (Hurter-Driffield) curve evaluation.
// Faithful port of allstock/curves.py. See the `characteristic-curve` note.

import Foundation

/// Numerically-stable soft-plus with softness `k` (rounds the toe/shoulder).
@inline(__always) func softplus(_ x: Float, _ k: Float) -> Float {
    let kk = max(k, 1e-4)
    let z = x / kk
    return kk * (max(z, 0) + log1pf(expf(-abs(z))))
}

/// Map a single log-exposure value to developed density for one layer.
@inline(__always)
func densityFromLogExposure(_ logE: Float, _ c: ChannelCurve, gammaGain: Float = 0) -> Float {
    let dmin = c.dmin, dmax = c.dmax
    let gamma = max(c.gamma + gammaGain, 1e-3)
    let dRange = max(dmax - dmin, 1e-3)
    let x = (logE - c.speed) * gamma
    let t = softplus(x, c.toe)                       // soft toe
    var d = t - softplus(t - dRange, c.shoulder)     // soft shoulder
    d = max(0, min(dRange, d))
    return dmin + d
}

/// Convert a linear scene value to log10 exposure on the film.
/// `midGray` (0.184) anchors 18% grey near the straight-line centre.
@inline(__always)
func sceneToLogExposure(_ linear: Float, exposureStops: Float = 0, midGray: Float = 0.184) -> Float {
    let gain = powf(2.0, exposureStops)
    let e = max(linear * gain, 1e-6) / midGray
    return log10f(e)
}
