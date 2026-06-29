// FilmEngine.swift — the film engine: turn a scene into a developed photograph.
//
// Faithful CPU port of allstock/engine.py (+ halation/grain/optics). It walks an
// image through the real imaging chain: spectral mix -> log exposure -> density
// (H&D curve, push/pull) -> print/invert -> halation -> grain -> optics.
//
// This is a clear, correct reference implementation. For production you would
// move the hot loops to Core Image / Metal — but the math here is the contract
// those shaders must reproduce.

import Foundation

public struct DevelopOptions {
    public var exposure: Float = 0       // stops
    public var push: Float? = nil        // overrides stock.development.pushPull
    public var seed: UInt64 = 0
    public var grain = true
    public var halation = true
    public var optics = true
    public init() {}
}

public enum FilmEngine {

    /// Develop a linear-light image on `stock`. Returns a linear positive (0..1).
    public static func develop(_ linear: FloatImage, stock: FilmStock,
                               options: DevelopOptions = DevelopOptions()) -> FloatImage {
        var pos = stock.isMonochrome
            ? developBW(linear, stock, options)
            : developColor(linear, stock, options)

        if options.halation { pos = applyHalation(pos, stock.halation) }
        if options.grain { pos = addGrain(pos, stock.grain, seed: options.seed) }
        if options.optics { pos = applyOptics(pos, stock.optics) }

        for i in 0..<pos.pixels.count { pos.pixels[i] = max(0, min(1, pos.pixels[i])) }
        return pos
    }

    // MARK: colour path

    private static func developColor(_ linear: FloatImage, _ s: FilmStock,
                                     _ o: DevelopOptions) -> FloatImage {
        let push = o.push ?? s.development.pushPull
        let gammaGain = push * s.development.devContrastGain
        let shadowShift = push * s.development.devShadowLoss
        let m = normalizedRows(s.spectral.matrix)
        let curves = [s.curves.red, s.curves.green, s.curves.blue]
        let pg = s.printStage.gamma

        var out = FloatImage(width: linear.width, height: linear.height,
                             pixels: [Float](repeating: 0, count: linear.pixels.count))
        for p in 0..<linear.count {
            let r = linear.pixels[p * 3], g = linear.pixels[p * 3 + 1], b = linear.pixels[p * 3 + 2]
            for j in 0..<3 {                                   // exposure = linear @ mᵀ
                let e = max(m[j][0] * r + m[j][1] * g + m[j][2] * b, 0)
                let logE = sceneToLogExposure(e, exposureStops: o.exposure) - shadowShift
                let d = densityFromLogExposure(logE, curves[j], gammaGain: gammaGain)
                out.pixels[p * 3 + j] = powf(10.0, -(pg * (curves[j].dmax - d)))   // invert
            }
        }
        return finish(out, s, monochrome: false)
    }

    // MARK: black & white path

    private static func developBW(_ linear: FloatImage, _ s: FilmStock,
                                  _ o: DevelopOptions) -> FloatImage {
        let push = o.push ?? s.development.pushPull
        let gammaGain = push * s.development.devContrastGain
        let shadowShift = push * s.development.devShadowLoss

        var w = (s.spectral.matrix.count == 3) ? s.spectral.matrix[1] : [0.2126, 0.7152, 0.0722]
        w = w.map { max($0, 0) }
        let sum = w.reduce(0, +)
        w = sum > 0 ? w.map { $0 / sum } : [0.2126, 0.7152, 0.0722]

        let curve = s.curves.green, pg = s.printStage.gamma
        var out = FloatImage(width: linear.width, height: linear.height,
                             pixels: [Float](repeating: 0, count: linear.pixels.count))
        for p in 0..<linear.count {
            let mono = max(w[0] * linear.pixels[p * 3] + w[1] * linear.pixels[p * 3 + 1]
                           + w[2] * linear.pixels[p * 3 + 2], 0)
            let logE = sceneToLogExposure(mono, exposureStops: o.exposure) - shadowShift
            let d = densityFromLogExposure(logE, curve, gammaGain: gammaGain)
            let gray = powf(10.0, -(pg * (curve.dmax - d)))
            out.pixels[p * 3] = gray; out.pixels[p * 3 + 1] = gray; out.pixels[p * 3 + 2] = gray
        }
        return finish(out, s, monochrome: true)
    }

    // MARK: finish (normalise, balance, saturation, levels)

    private static func finish(_ img: FloatImage, _ s: FilmStock, monochrome: Bool) -> FloatImage {
        var pos = img
        let peak = percentile(pos.pixels, 99.5)
        if peak > 1e-6 { for i in 0..<pos.pixels.count { pos.pixels[i] /= peak } }

        if !monochrome {
            let bal = s.printStage.balance
            for p in 0..<pos.count {
                pos.pixels[p * 3] *= bal[0]; pos.pixels[p * 3 + 1] *= bal[1]; pos.pixels[p * 3 + 2] *= bal[2]
            }
            let om = s.printStage.orangeMask
            if om > 1e-4 {
                let g: [Float] = [1.0 - 0.10 * om, 1.0, 1.0 + 0.06 * om]
                for p in 0..<pos.count { for c in 0..<3 { pos.pixels[p * 3 + c] *= g[c] } }
            }
            let sat = s.printStage.saturation
            if abs(sat - 1.0) > 1e-4 {
                for p in 0..<pos.count {
                    let i = p * 3
                    let lum = 0.2126 * pos.pixels[i] + 0.7152 * pos.pixels[i + 1] + 0.0722 * pos.pixels[i + 2]
                    for c in 0..<3 { pos.pixels[i + c] = lum + (pos.pixels[i + c] - lum) * sat }
                }
            }
        }
        let bp = s.printStage.blackPoint, wp = s.printStage.whitePoint
        if wp - bp > 1e-4 { for i in 0..<pos.pixels.count { pos.pixels[i] = (pos.pixels[i] - bp) / (wp - bp) } }
        for i in 0..<pos.pixels.count { pos.pixels[i] = max(0, pos.pixels[i]) }
        return pos
    }

    // MARK: halation / grain / optics

    static func applyHalation(_ img: FloatImage, _ h: Halation) -> FloatImage {
        guard h.strength > 1e-4, h.radius > 1e-3 else { return img }
        let lum = luminance(img)
        let denom = max(1.0 - h.threshold, 1e-3)
        var mask = lum.map { v -> Float in let m = max(0, min(1, (v - h.threshold) / denom)); return m * m }
        mask = blurPlane(mask, width: img.width, height: img.height, sigma: h.radius)
        let mx = mask.max() ?? 0
        if mx > 1e-6 { for i in 0..<mask.count { mask[i] /= mx } }
        var out = img
        for p in 0..<img.count {
            for c in 0..<3 {
                let glow = max(0, min(1, h.strength * mask[p] * h.color[c]))
                let base = max(0, min(1, img.pixels[p * 3 + c]))
                out.pixels[p * 3 + c] = 1.0 - (1.0 - base) * (1.0 - glow)   // screen
            }
        }
        return out
    }

    static func addGrain(_ img: FloatImage, _ grain: Grain, seed: UInt64) -> FloatImage {
        guard grain.rms > 1e-5 else { return img }
        var rng = SeededRNG(seed: seed)
        let sigma = max(grain.size * 0.6, 0)
        let lum = luminance(img)

        @inline(__always) func toneWeight(_ l: Float) -> Float {
            if l < 0.5 { return grain.shadowWeight + (grain.midWeight - grain.shadowWeight) * max(0, min(1, l / 0.5)) }
            return grain.midWeight + (grain.highlightWeight - grain.midWeight) * max(0, min(1, (l - 0.5) / 0.5))
        }

        let mono = unitNoise(width: img.width, height: img.height, sigma: sigma, rng: &rng)
        var chroma: [[Float]] = []
        if !grain.mono && grain.chroma > 1e-3 {
            chroma = (0..<3).map { _ in unitNoise(width: img.width, height: img.height, sigma: sigma, rng: &rng) }
        }
        var out = img
        for p in 0..<img.count {
            let wgt = toneWeight(max(0, min(1, lum[p])))
            for c in 0..<3 {
                let n: Float
                if chroma.isEmpty { n = mono[p] }
                else { n = (1 - grain.chroma) * mono[p] + grain.chroma * chroma[c][p] }
                let i = p * 3 + c
                let perc = powf(max(img.pixels[i], 0), 1.0 / 2.2) + n * (grain.rms * wgt)
                out.pixels[i] = powf(max(perc, 0), 2.2)
            }
        }
        return out
    }

    static func applyOptics(_ img: FloatImage, _ o: Optics) -> FloatImage {
        var out = img
        if o.blur > 1e-3 { out = blurRGB(out, sigma: o.blur) }
        if o.acutance > 1e-4 {
            let low = blurRGB(out, sigma: 1.4)
            for i in 0..<out.pixels.count { out.pixels[i] = out.pixels[i] + o.acutance * (out.pixels[i] - low.pixels[i]) }
        }
        if o.vignette > 1e-4 {
            let mask = radialFalloff(width: out.width, height: out.height, amount: o.vignette)
            for p in 0..<out.count { for c in 0..<3 { out.pixels[p * 3 + c] *= mask[p] } }
        }
        for i in 0..<out.pixels.count { out.pixels[i] = max(0, out.pixels[i]) }
        return out
    }

    // MARK: small numeric helpers

    private static func normalizedRows(_ m: [[Float]]) -> [[Float]] {
        m.map { row in
            let s = row.reduce(0, +)
            let d = s == 0 ? 1 : s
            return row.map { $0 / d }
        }
    }

    /// Linear-interpolated percentile over a flat array (matches numpy default).
    static func percentile(_ values: [Float], _ q: Float) -> Float {
        guard !values.isEmpty else { return 0 }
        let sorted = values.sorted()
        let pos = (q / 100.0) * Float(sorted.count - 1)
        let lo = Int(pos.rounded(.down)), hi = Int(pos.rounded(.up))
        if lo == hi { return sorted[lo] }
        let frac = pos - Float(lo)
        return sorted[lo] * (1 - frac) + sorted[hi] * frac
    }
}
