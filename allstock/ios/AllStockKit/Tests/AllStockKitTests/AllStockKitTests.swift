import XCTest
@testable import AllStockKit

final class AllStockKitTests: XCTestCase {

    private func scene(_ w: Int, _ h: Int) -> FloatImage {
        var bytes = [UInt8](repeating: 0, count: w * h * 3)
        for i in 0..<bytes.count { bytes[i] = UInt8((i * 37) % 256) }
        return FloatImage.fromSRGB(bytes: bytes, width: w, height: h)
    }

    func testBuiltinCount() {
        XCTAssertEqual(BuiltinStocks.all.count, 11)
        XCTAssertNotNil(BuiltinStocks.byKey("cinestill800t"))
        XCTAssertNotNil(BuiltinStocks.byKey("Superia-400".replacingOccurrences(of: "-", with: "")))
    }

    func testDevelopColourBounded() {
        let out = FilmEngine.develop(scene(24, 18), stock: BuiltinStocks.portra400)
        XCTAssertEqual(out.width, 24); XCTAssertEqual(out.height, 18)
        XCTAssertTrue(out.pixels.allSatisfy { $0 >= 0 && $0 <= 1 && $0.isFinite })
    }

    func testDevelopBWIsGrey() {
        let out = FilmEngine.develop(scene(16, 16), stock: BuiltinStocks.trix400)
        for p in 0..<out.count {
            XCTAssertEqual(out.pixels[p * 3], out.pixels[p * 3 + 1], accuracy: 1e-5)
            XCTAssertEqual(out.pixels[p * 3 + 1], out.pixels[p * 3 + 2], accuracy: 1e-5)
        }
    }

    func testGrainSeedIsReproducible() {
        var o = DevelopOptions(); o.seed = 42
        let a = FilmEngine.develop(scene(20, 20), stock: BuiltinStocks.gold200, options: o)
        let b = FilmEngine.develop(scene(20, 20), stock: BuiltinStocks.gold200, options: o)
        XCTAssertEqual(a.pixels, b.pixels)
    }

    func testDecodeStockJSON() throws {
        // The same JSON shape the Python designer / API emits.
        let json = """
        {"name":"Forged","process_family":"color_negative",
         "print_":{"gamma":1.6,"balance":[0.98,1.03,1.0],"saturation":1.2},
         "grain":{"rms":0.024,"mono":false},"lineage":["a","b"]}
        """.data(using: .utf8)!
        let s = try FilmStock.fromJSON(json)
        XCTAssertEqual(s.name, "Forged")
        XCTAssertEqual(s.printStage.gamma, 1.6, accuracy: 1e-6)
        XCTAssertEqual(s.printStage.balance, [0.98, 1.03, 1.0])
        XCTAssertEqual(s.lineage, ["a", "b"])
    }

    func testPercentile() {
        XCTAssertEqual(FilmEngine.percentile([0, 1, 2, 3, 4], 50), 2, accuracy: 1e-6)
    }
}
