// FloatImage.swift — the working image type and low-level pixel helpers.
//
// Faithful port of allstock/imaging.py. Everything in the engine happens in
// linear, scene-referred light; these helpers move in and out of that domain
// and provide a separable Gaussian blur (used by grain, halation and optics).

import Foundation

/// An interleaved RGB image of 32-bit floats, length `width * height * 3`.
public struct FloatImage {
    public var width: Int
    public var height: Int
    public var pixels: [Float]   // [r,g,b, r,g,b, ...]

    public init(width: Int, height: Int, pixels: [Float]) {
        precondition(pixels.count == width * height * 3)
        self.width = width; self.height = height; self.pixels = pixels
    }

    public var count: Int { width * height }

    /// Build a linear-light image from interleaved sRGB bytes (0–255), RGB.
    public static func fromSRGB(bytes: [UInt8], width: Int, height: Int) -> FloatImage {
        precondition(bytes.count == width * height * 3)
        var px = [Float](repeating: 0, count: bytes.count)
        for i in 0..<bytes.count { px[i] = srgbToLinear(Float(bytes[i]) / 255.0) }
        return FloatImage(width: width, height: height, pixels: px)
    }

    /// Encode this (assumed linear) image to interleaved sRGB bytes (0–255).
    public func toSRGBBytes() -> [UInt8] {
        var out = [UInt8](repeating: 0, count: pixels.count)
        for i in 0..<pixels.count {
            let s = linearToSRGB(max(0, min(1, pixels[i])))
            out[i] = UInt8(max(0, min(255, s * 255.0 + 0.5)))
        }
        return out
    }
}

// MARK: - sRGB <-> linear (IEC 61966-2-1)

@inline(__always) public func srgbToLinear(_ x: Float) -> Float {
    let c = max(0, min(1, x))
    return c <= 0.04045 ? c / 12.92 : powf((c + 0.055) / 1.055, 2.4)
}

@inline(__always) public func linearToSRGB(_ x: Float) -> Float {
    let c = max(0, x)
    return c <= 0.0031308 ? c * 12.92 : 1.055 * powf(c, 1.0 / 2.4) - 0.055
}

// Rec.709 luminance weights (linear light).
private let kLuma: (Float, Float, Float) = (0.2126, 0.7152, 0.0722)

/// Per-pixel linear luminance, length `width*height`.
public func luminance(_ img: FloatImage) -> [Float] {
    var out = [Float](repeating: 0, count: img.count)
    for p in 0..<img.count {
        let i = p * 3
        out[p] = kLuma.0 * img.pixels[i] + kLuma.1 * img.pixels[i + 1] + kLuma.2 * img.pixels[i + 2]
    }
    return out
}

// MARK: - Separable Gaussian blur (pure Swift)

private func gaussianKernel(sigma: Float) -> [Float] {
    let radius = max(1, Int((sigma * 3.0).rounded()))
    var k = [Float](repeating: 0, count: 2 * radius + 1)
    var sum: Float = 0
    for i in -radius...radius {
        let v = expf(-Float(i * i) / (2 * sigma * sigma))
        k[i + radius] = v; sum += v
    }
    for i in 0..<k.count { k[i] /= sum }
    return k
}

/// Blur a single-channel plane (edge-padded), matching imaging.gaussian_blur.
public func blurPlane(_ src: [Float], width w: Int, height h: Int, sigma: Float) -> [Float] {
    guard sigma > 1e-4 else { return src }
    let k = gaussianKernel(sigma: sigma); let r = k.count / 2
    @inline(__always) func clamp(_ v: Int, _ hi: Int) -> Int { v < 0 ? 0 : (v >= hi ? hi - 1 : v) }

    var tmp = [Float](repeating: 0, count: src.count)   // horizontal pass
    for y in 0..<h {
        let row = y * w
        for x in 0..<w {
            var acc: Float = 0
            for t in -r...r { acc += k[t + r] * src[row + clamp(x + t, w)] }
            tmp[row + x] = acc
        }
    }
    var out = [Float](repeating: 0, count: src.count)    // vertical pass
    for y in 0..<h {
        for x in 0..<w {
            var acc: Float = 0
            for t in -r...r { acc += k[t + r] * tmp[clamp(y + t, h) * w + x] }
            out[y * w + x] = acc
        }
    }
    return out
}

/// Blur each channel of an RGB image.
public func blurRGB(_ img: FloatImage, sigma: Float) -> FloatImage {
    guard sigma > 1e-4 else { return img }
    var planes = [[Float]](repeating: [Float](repeating: 0, count: img.count), count: 3)
    for p in 0..<img.count { for c in 0..<3 { planes[c][p] = img.pixels[p * 3 + c] } }
    for c in 0..<3 { planes[c] = blurPlane(planes[c], width: img.width, height: img.height, sigma: sigma) }
    var out = img
    for p in 0..<img.count { for c in 0..<3 { out.pixels[p * 3 + c] = planes[c][p] } }
    return out
}

/// 0..1 vignette mask (1 at centre), matching imaging.radial_falloff.
public func radialFalloff(width w: Int, height h: Int, amount: Float) -> [Float] {
    var out = [Float](repeating: 0, count: w * h)
    let cy = Float(h - 1) / 2, cx = Float(w - 1) / 2
    let invRoot2: Float = 1.0 / 2.0.squareRoot()
    for y in 0..<h {
        for x in 0..<w {
            let dx = (Float(x) - cx) / (Float(w) / 2), dy = (Float(y) - cy) / (Float(h) / 2)
            var r = (dx * dx + dy * dy).squareRoot() * invRoot2
            r = max(0, min(1, r))
            out[y * w + x] = 1.0 - amount * r * r
        }
    }
    return out
}
