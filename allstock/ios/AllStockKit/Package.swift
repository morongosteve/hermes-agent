// swift-tools-version: 5.9
// AllStockKit — a native Swift port of the AllStock film engine.
//
// This is the "Option A (native port)" core from docs/IOS_APP_STORE.md. It is
// pure Foundation (no UIKit/CoreImage), so it builds and unit-tests on macOS via
// `swift test`, and links into an iOS app target unchanged. The SwiftUI app
// files under ../App import this package. See ../README.md.
import PackageDescription

let package = Package(
    name: "AllStockKit",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "AllStockKit", targets: ["AllStockKit"]),
    ],
    targets: [
        .target(name: "AllStockKit"),
        .testTarget(name: "AllStockKitTests", dependencies: ["AllStockKit"]),
    ]
)
