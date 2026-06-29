// FilmStock.swift — the film-stock data model.
//
// Mirrors allstock/stock.py and decodes the *same* JSON: a stock saved by the
// Python designer (or returned by the /design endpoints, or /stocks/{key}) can
// be decoded straight into this type. All fields default, so partial documents
// (e.g. a forged stock) still decode.

import Foundation

public struct ChannelCurve: Codable, Equatable, Hashable {
    public var dmin: Float = 0.10
    public var dmax: Float = 2.20
    public var gamma: Float = 0.62
    public var speed: Float = 0.0
    public var toe: Float = 0.18
    public var shoulder: Float = 0.22

    public init(dmin: Float = 0.10, dmax: Float = 2.20, gamma: Float = 0.62,
                speed: Float = 0.0, toe: Float = 0.18, shoulder: Float = 0.22) {
        self.dmin = dmin; self.dmax = dmax; self.gamma = gamma
        self.speed = speed; self.toe = toe; self.shoulder = shoulder
    }
    public init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        dmin = try c.decodeIfPresent(Float.self, forKey: .dmin) ?? dmin
        dmax = try c.decodeIfPresent(Float.self, forKey: .dmax) ?? dmax
        gamma = try c.decodeIfPresent(Float.self, forKey: .gamma) ?? gamma
        speed = try c.decodeIfPresent(Float.self, forKey: .speed) ?? speed
        toe = try c.decodeIfPresent(Float.self, forKey: .toe) ?? toe
        shoulder = try c.decodeIfPresent(Float.self, forKey: .shoulder) ?? shoulder
    }
}

public struct Curves: Codable, Equatable, Hashable {
    public var red = ChannelCurve()
    public var green = ChannelCurve()
    public var blue = ChannelCurve()
    public init(red: ChannelCurve = .init(), green: ChannelCurve = .init(), blue: ChannelCurve = .init()) {
        self.red = red; self.green = green; self.blue = blue
    }
}

public struct Spectral: Codable, Equatable, Hashable {
    public var matrix: [[Float]] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    public init(matrix: [[Float]] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]) { self.matrix = matrix }
}

public struct Grain: Codable, Equatable, Hashable {
    public var rms: Float = 0.018
    public var size: Float = 1.1
    public var chroma: Float = 0.35
    public var shadowWeight: Float = 0.6
    public var midWeight: Float = 1.0
    public var highlightWeight: Float = 0.4
    public var mono: Bool = false
    enum CodingKeys: String, CodingKey {
        case rms, size, chroma, mono
        case shadowWeight = "shadow_weight", midWeight = "mid_weight", highlightWeight = "highlight_weight"
    }
    public init() {}
    public init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        rms = try c.decodeIfPresent(Float.self, forKey: .rms) ?? rms
        size = try c.decodeIfPresent(Float.self, forKey: .size) ?? size
        chroma = try c.decodeIfPresent(Float.self, forKey: .chroma) ?? chroma
        shadowWeight = try c.decodeIfPresent(Float.self, forKey: .shadowWeight) ?? shadowWeight
        midWeight = try c.decodeIfPresent(Float.self, forKey: .midWeight) ?? midWeight
        highlightWeight = try c.decodeIfPresent(Float.self, forKey: .highlightWeight) ?? highlightWeight
        mono = try c.decodeIfPresent(Bool.self, forKey: .mono) ?? mono
    }
}

public struct Halation: Codable, Equatable, Hashable {
    public var strength: Float = 0.10
    public var radius: Float = 12.0
    public var threshold: Float = 0.72
    public var color: [Float] = [1.0, 0.34, 0.12]
    public init() {}
    public init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        strength = try c.decodeIfPresent(Float.self, forKey: .strength) ?? strength
        radius = try c.decodeIfPresent(Float.self, forKey: .radius) ?? radius
        threshold = try c.decodeIfPresent(Float.self, forKey: .threshold) ?? threshold
        color = try c.decodeIfPresent([Float].self, forKey: .color) ?? color
    }
}

public struct Optics: Codable, Equatable, Hashable {
    public var acutance: Float = 0.25
    public var blur: Float = 0.0
    public var vignette: Float = 0.0
    public init() {}
    public init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        acutance = try c.decodeIfPresent(Float.self, forKey: .acutance) ?? acutance
        blur = try c.decodeIfPresent(Float.self, forKey: .blur) ?? blur
        vignette = try c.decodeIfPresent(Float.self, forKey: .vignette) ?? vignette
    }
}

public struct PrintStage: Codable, Equatable, Hashable {
    public var gamma: Float = 1.0
    public var balance: [Float] = [1, 1, 1]
    public var saturation: Float = 1.0
    public var blackPoint: Float = 0.0
    public var whitePoint: Float = 1.0
    public var orangeMask: Float = 0.0
    enum CodingKeys: String, CodingKey {
        case gamma, balance, saturation
        case blackPoint = "black_point", whitePoint = "white_point", orangeMask = "orange_mask"
    }
    public init() {}
    public init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        gamma = try c.decodeIfPresent(Float.self, forKey: .gamma) ?? gamma
        balance = try c.decodeIfPresent([Float].self, forKey: .balance) ?? balance
        saturation = try c.decodeIfPresent(Float.self, forKey: .saturation) ?? saturation
        blackPoint = try c.decodeIfPresent(Float.self, forKey: .blackPoint) ?? blackPoint
        whitePoint = try c.decodeIfPresent(Float.self, forKey: .whitePoint) ?? whitePoint
        orangeMask = try c.decodeIfPresent(Float.self, forKey: .orangeMask) ?? orangeMask
    }
}

public struct Development: Codable, Equatable, Hashable {
    public var process: String = "C-41"
    public var pushPull: Float = 0.0
    public var devContrastGain: Float = 0.18
    public var devShadowLoss: Float = 0.12
    public var dryCurl: Float = 0.0
    enum CodingKeys: String, CodingKey {
        case process
        case pushPull = "push_pull", devContrastGain = "dev_contrast_gain"
        case devShadowLoss = "dev_shadow_loss", dryCurl = "dry_curl"
    }
    public init() {}
    public init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        process = try c.decodeIfPresent(String.self, forKey: .process) ?? process
        pushPull = try c.decodeIfPresent(Float.self, forKey: .pushPull) ?? pushPull
        devContrastGain = try c.decodeIfPresent(Float.self, forKey: .devContrastGain) ?? devContrastGain
        devShadowLoss = try c.decodeIfPresent(Float.self, forKey: .devShadowLoss) ?? devShadowLoss
        dryCurl = try c.decodeIfPresent(Float.self, forKey: .dryCurl) ?? dryCurl
    }
}

public let COLOR_NEGATIVE = "color_negative"
public let COLOR_REVERSAL = "color_reversal"
public let BW_NEGATIVE = "bw_negative"

public struct FilmStock: Codable, Equatable, Hashable, Identifiable {
    public var name: String = "Custom Stock"
    public var maker: String = "AllStock"
    public var iso: Int = 400
    public var processFamily: String = COLOR_NEGATIVE
    public var year: Int?
    public var description: String = ""
    public var spectral = Spectral()
    public var curves = Curves()
    public var grain = Grain()
    public var halation = Halation()
    public var optics = Optics()
    public var printStage = PrintStage()
    public var development = Development()
    public var lineage: [String] = []

    public var id: String { name }
    public var isMonochrome: Bool { processFamily == BW_NEGATIVE }
    public var isReversal: Bool { processFamily == COLOR_REVERSAL }

    enum CodingKeys: String, CodingKey {
        case name, maker, iso, year, description, spectral, curves, grain
        case halation, optics, development, lineage
        case processFamily = "process_family"
        case printStage = "print_"
    }

    public init() {}
    public init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? name
        maker = try c.decodeIfPresent(String.self, forKey: .maker) ?? maker
        iso = try c.decodeIfPresent(Int.self, forKey: .iso) ?? iso
        processFamily = try c.decodeIfPresent(String.self, forKey: .processFamily) ?? processFamily
        year = try c.decodeIfPresent(Int.self, forKey: .year)
        description = try c.decodeIfPresent(String.self, forKey: .description) ?? description
        spectral = try c.decodeIfPresent(Spectral.self, forKey: .spectral) ?? spectral
        curves = try c.decodeIfPresent(Curves.self, forKey: .curves) ?? curves
        grain = try c.decodeIfPresent(Grain.self, forKey: .grain) ?? grain
        halation = try c.decodeIfPresent(Halation.self, forKey: .halation) ?? halation
        optics = try c.decodeIfPresent(Optics.self, forKey: .optics) ?? optics
        printStage = try c.decodeIfPresent(PrintStage.self, forKey: .printStage) ?? printStage
        development = try c.decodeIfPresent(Development.self, forKey: .development) ?? development
        lineage = try c.decodeIfPresent([String].self, forKey: .lineage) ?? lineage
    }

    /// Decode a stock from JSON (e.g. a file saved by the Python designer).
    public static func fromJSON(_ data: Data) throws -> FilmStock {
        try JSONDecoder().decode(FilmStock.self, from: data)
    }
}
