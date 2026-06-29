// ImageBridge.swift — convert between UIImage and AllStockKit.FloatImage.
//
// Lives in the app target (needs UIKit/CoreGraphics). The engine itself
// (AllStockKit) stays platform-agnostic.

import UIKit
import AllStockKit

extension FloatImage {
    /// Decode a UIImage into a linear-light FloatImage, optionally downscaling
    /// the longest side (the CPU engine is fine for previews up to ~1600px).
    init?(uiImage: UIImage, maxSide: Int? = 1600) {
        guard var cg = uiImage.cgImage else { return nil }
        var w = cg.width, h = cg.height
        if let m = maxSide, max(w, h) > m {
            let scale = CGFloat(m) / CGFloat(max(w, h))
            let nw = max(1, Int(CGFloat(w) * scale)), nh = max(1, Int(CGFloat(h) * scale))
            UIGraphicsBeginImageContextWithOptions(CGSize(width: nw, height: nh), false, 1)
            uiImage.draw(in: CGRect(x: 0, y: 0, width: nw, height: nh))
            if let scaled = UIGraphicsGetImageFromCurrentImageContext()?.cgImage { cg = scaled; w = nw; h = nh }
            UIGraphicsEndImageContext()
        }
        var rgba = [UInt8](repeating: 0, count: w * h * 4)
        guard let ctx = CGContext(data: &rgba, width: w, height: h, bitsPerComponent: 8,
                                  bytesPerRow: w * 4, space: CGColorSpaceCreateDeviceRGB(),
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
        var rgb = [UInt8](repeating: 0, count: w * h * 3)
        for p in 0..<(w * h) { rgb[p * 3] = rgba[p * 4]; rgb[p * 3 + 1] = rgba[p * 4 + 1]; rgb[p * 3 + 2] = rgba[p * 4 + 2] }
        self = FloatImage.fromSRGB(bytes: rgb, width: w, height: h)
    }

    /// Encode a (linear) FloatImage back to a UIImage in sRGB.
    func toUIImage() -> UIImage? {
        let srgb = toSRGBBytes()
        var rgba = [UInt8](repeating: 255, count: width * height * 4)
        for p in 0..<count { rgba[p * 4] = srgb[p * 3]; rgba[p * 4 + 1] = srgb[p * 3 + 1]; rgba[p * 4 + 2] = srgb[p * 3 + 2] }
        guard let ctx = CGContext(data: &rgba, width: width, height: height, bitsPerComponent: 8,
                                  bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(),
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue),
              let cg = ctx.makeImage() else { return nil }
        return UIImage(cgImage: cg)
    }
}
