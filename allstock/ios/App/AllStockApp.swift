// AllStockApp.swift — app entry point and tab layout.

import SwiftUI

@main
struct AllStockApp: App {
    var body: some Scene {
        WindowGroup {
            TabView {
                DevelopView()
                    .tabItem { Label("Develop", systemImage: "camera.filters") }
                StocksView()
                    .tabItem { Label("Stocks", systemImage: "film") }
                LearnView()
                    .tabItem { Label("Learn", systemImage: "book") }
            }
        }
    }
}
