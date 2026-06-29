// RNG.swift — a small seedable PRNG so grain is reproducible from a seed,
// mirroring numpy's seeded default_rng in the Python engine.

import Foundation

/// SplitMix64 — tiny, fast, deterministic. Good enough for grain noise.
public struct SeededRNG: RandomNumberGenerator {
    private var state: UInt64
    public init(seed: UInt64) { state = seed &+ 0x9E3779B97F4A7C15 }

    public mutating func next() -> UInt64 {
        state = state &+ 0x9E3779B97F4A7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }

    /// Uniform Float in [0, 1).
    public mutating func nextUnit() -> Float {
        Float(next() >> 40) * (1.0 / 16777216.0)   // 24 random bits
    }

    /// Standard-normal sample via Box–Muller.
    public mutating func nextGaussian() -> Float {
        let u1 = max(nextUnit(), 1e-7), u2 = nextUnit()
        return (-2 * logf(u1)).squareRoot() * cosf(2 * .pi * u2)
    }
}

/// Band-limited noise plane normalised to ~unit standard deviation.
func unitNoise(width w: Int, height h: Int, sigma: Float, rng: inout SeededRNG) -> [Float] {
    var n = [Float](repeating: 0, count: w * h)
    for i in 0..<n.count { n[i] = rng.nextGaussian() }
    if sigma > 1e-3 { n = blurPlane(n, width: w, height: h, sigma: sigma) }
    let mean = n.reduce(0, +) / Float(n.count)
    var varSum: Float = 0
    for v in n { varSum += (v - mean) * (v - mean) }
    let std = (varSum / Float(n.count)).squareRoot()
    if std > 1e-6 { for i in 0..<n.count { n[i] /= std } }
    return n
}
