// BuiltinStocks.swift — the 11 built-in film stocks.
// Values mirror allstock/library.py (characterisations, not datasheets).

import Foundation

public enum BuiltinStocks {

    public static let all: [FilmStock] = [
        portra400, portra160, gold200, ektar100, superia400, pro400h,
        cinestill800t, velvia50, ektachrome100, trix400, hp5,
    ]

    public static func byKey(_ key: String) -> FilmStock? {
        let norm = key.lowercased().replacingOccurrences(of: " ", with: "")
            .replacingOccurrences(of: "-", with: "").replacingOccurrences(of: "_", with: "")
        return keyed[norm]
    }

    public static let keyed: [String: FilmStock] = [
        "portra400": portra400, "portra160": portra160, "gold200": gold200,
        "ektar100": ektar100, "superia400": superia400, "pro400h": pro400h,
        "cinestill800t": cinestill800t, "velvia50": velvia50,
        "ektachrome100": ektachrome100, "trix400": trix400, "hp5": hp5,
    ]

    // MARK: builders (mirror library._spectral / _curves)

    private static func spectral(_ diag: Float, _ off: Float) -> Spectral {
        Spectral(matrix: [[diag, off, off], [off, diag, off], [off, off, diag]])
    }
    private static func curves(_ dmax: Float, _ gamma: Float, r: Float = 0, g: Float = 0, b: Float = 0,
                               toe: Float = 0.18, shoulder: Float = 0.22, dmin: Float = 0.1) -> Curves {
        Curves(red: ChannelCurve(dmin: dmin, dmax: dmax, gamma: gamma, speed: r, toe: toe, shoulder: shoulder),
               green: ChannelCurve(dmin: dmin, dmax: dmax, gamma: gamma, speed: g, toe: toe, shoulder: shoulder),
               blue: ChannelCurve(dmin: dmin, dmax: dmax, gamma: gamma, speed: b, toe: toe, shoulder: shoulder))
    }
    private static func grain(_ rms: Float, _ size: Float, chroma: Float = 0.35,
                              mono: Bool = false, mid: Float = 1.0) -> Grain {
        var x = Grain(); x.rms = rms; x.size = size; x.chroma = chroma; x.mono = mono; x.midWeight = mid; return x
    }
    private static func halation(_ strength: Float, _ radius: Float, _ threshold: Float,
                                 color: [Float] = [1.0, 0.34, 0.12]) -> Halation {
        var x = Halation(); x.strength = strength; x.radius = radius; x.threshold = threshold; x.color = color; return x
    }
    private static func optics(_ acutance: Float) -> Optics { var x = Optics(); x.acutance = acutance; return x }
    private static func print(_ gamma: Float, _ balance: [Float] = [1, 1, 1], sat: Float = 1.0) -> PrintStage {
        var x = PrintStage(); x.gamma = gamma; x.balance = balance; x.saturation = sat; return x
    }
    private static func dev(_ process: String) -> Development { var x = Development(); x.process = process; return x }

    private static func make(_ name: String, _ maker: String, iso: Int, year: Int, family: String,
                             _ desc: String, _ sp: Spectral, _ cv: Curves, _ gr: Grain, _ ha: Halation,
                             _ op: Optics, _ pr: PrintStage, _ dv: Development) -> FilmStock {
        var s = FilmStock()
        s.name = name; s.maker = maker; s.iso = iso; s.year = year; s.processFamily = family
        s.description = desc; s.spectral = sp; s.curves = cv; s.grain = gr
        s.halation = ha; s.optics = op; s.printStage = pr; s.development = dv
        return s
    }

    // MARK: the stocks

    public static let portra400 = make(
        "Kodak Portra 400", "Kodak", iso: 400, year: 2010, family: COLOR_NEGATIVE,
        "Soft contrast, warm and forgiving skin tones, wide latitude. The portrait standard.",
        spectral(0.90, 0.05), curves(2.2, 0.55, r: -0.02, b: 0.03, toe: 0.20, shoulder: 0.28),
        grain(0.016, 1.1, chroma: 0.30), halation(0.06, 10, 0.78), optics(0.20),
        print(1.50, [1.05, 1.0, 0.95], sat: 1.02), dev("C-41"))

    public static let portra160 = make(
        "Kodak Portra 160", "Kodak", iso: 160, year: 2011, family: COLOR_NEGATIVE,
        "Finer-grained, slightly cooler sibling of Portra 400 for studio/landscape.",
        spectral(0.91, 0.045), curves(2.25, 0.56, r: -0.01, b: 0.02, toe: 0.18, shoulder: 0.27),
        grain(0.011, 0.9, chroma: 0.28), halation(0.05, 9, 0.80), optics(0.22),
        print(1.55, [1.02, 1.0, 0.99], sat: 1.05), dev("C-41"))

    public static let gold200 = make(
        "Kodak Gold 200", "Kodak", iso: 200, year: 1988, family: COLOR_NEGATIVE,
        "Warm, golden, nostalgic consumer film. Sunny saturation and amber midtones.",
        spectral(0.89, 0.055), curves(2.15, 0.60, r: -0.03, g: -0.01, b: 0.05, toe: 0.20, shoulder: 0.24),
        grain(0.020, 1.05, chroma: 0.34), halation(0.08, 11, 0.74), optics(0.22),
        print(1.70, [1.08, 1.01, 0.90], sat: 1.16), dev("C-41"))

    public static let ektar100 = make(
        "Kodak Ektar 100", "Kodak", iso: 100, year: 2008, family: COLOR_NEGATIVE,
        "World's finest-grain colour negative; vivid, punchy saturation rivaling slide film.",
        spectral(0.93, 0.03), curves(2.3, 0.65, r: -0.01, b: 0.01, toe: 0.16, shoulder: 0.22),
        grain(0.008, 0.8, chroma: 0.25), halation(0.05, 9, 0.80), optics(0.26),
        print(1.72, [1.02, 1.0, 0.99], sat: 1.30), dev("C-41"))

    public static let superia400 = make(
        "Fujifilm Superia X-TRA 400", "Fujifilm", iso: 400, year: 1998, family: COLOR_NEGATIVE,
        "Punchy consumer Fuji negative: signature vivid greens, cooler slightly cyan shadows.",
        spectral(0.90, 0.05), curves(2.2, 0.60, r: -0.02, g: 0.02, b: 0.02, toe: 0.18, shoulder: 0.24),
        grain(0.024, 1.25, chroma: 0.36), halation(0.07, 11, 0.76), optics(0.24),
        print(1.62, [0.98, 1.03, 1.0], sat: 1.22), dev("C-41"))

    public static let pro400h = make(
        "Fujifilm Pro 400H", "Fujifilm", iso: 400, year: 2004, family: COLOR_NEGATIVE,
        "Airy, pastel palette with signature soft greens and cyans. Beloved for weddings.",
        spectral(0.90, 0.05), curves(2.2, 0.55, r: 0.02, g: -0.01, b: -0.01, toe: 0.20, shoulder: 0.30),
        grain(0.015, 1.1, chroma: 0.30), halation(0.05, 10, 0.80), optics(0.18),
        print(1.48, [0.97, 1.02, 1.02], sat: 0.96), dev("C-41"))

    public static let cinestill800t = make(
        "CineStill 800T", "CineStill", iso: 800, year: 2012, family: COLOR_NEGATIVE,
        "Tungsten-balanced ECN-2 stock with the rem-jet removed: cool daylight cast and red halation glow.",
        spectral(0.90, 0.05), curves(2.15, 0.60, r: 0.04, b: -0.06, toe: 0.22, shoulder: 0.26),
        grain(0.030, 1.4, chroma: 0.40), halation(0.55, 20, 0.66, color: [1.0, 0.28, 0.10]), optics(0.20),
        print(1.55, [0.90, 1.0, 1.22], sat: 1.05), dev("ECN-2"))

    public static let velvia50 = make(
        "Fujifilm Velvia 50", "Fujifilm", iso: 50, year: 1990, family: COLOR_REVERSAL,
        "Legendary landscape slide film: extreme saturation, vivid greens/blues, high contrast.",
        spectral(0.95, 0.02), curves(3.0, 1.60, g: -0.02, b: -0.03, toe: 0.10, shoulder: 0.10),
        grain(0.007, 0.7, chroma: 0.22), halation(0.04, 8, 0.82), optics(0.30),
        print(1.0, [1.0, 1.02, 1.03], sat: 1.55), dev("E-6"))

    public static let ektachrome100 = make(
        "Kodak Ektachrome E100", "Kodak", iso: 100, year: 2018, family: COLOR_REVERSAL,
        "Clean, accurate, slightly cool slide film with fine grain and moderate slide contrast.",
        spectral(0.94, 0.025), curves(2.9, 1.35, r: -0.01, b: 0.02, toe: 0.12, shoulder: 0.14),
        grain(0.008, 0.8, chroma: 0.22), halation(0.04, 8, 0.82), optics(0.28),
        print(1.0, [0.99, 1.0, 1.02], sat: 1.20), dev("E-6"))

    public static let trix400 = make(
        "Kodak Tri-X 400", "Kodak", iso: 400, year: 1954, family: BW_NEGATIVE,
        "The photojournalist's classic: gritty, structured grain, gutsy midtone contrast.",
        spectral(0.85, 0.075), curves(2.2, 0.62, toe: 0.16, shoulder: 0.24),
        grain(0.032, 1.4, chroma: 0.0, mono: true, mid: 1.1),
        halation(0.04, 9, 0.80, color: [1, 1, 1]), optics(0.32), print(1.55), dev("B&W"))

    public static let hp5 = make(
        "Ilford HP5 Plus 400", "Ilford", iso: 400, year: 1989, family: BW_NEGATIVE,
        "Smooth, wide-latitude B&W workhorse; softer and more forgiving than Tri-X.",
        spectral(0.85, 0.075), curves(2.15, 0.58, toe: 0.20, shoulder: 0.28),
        grain(0.027, 1.5, chroma: 0.0, mono: true),
        halation(0.03, 9, 0.82, color: [1, 1, 1]), optics(0.28), print(1.50), dev("B&W"))
}
