// StocksView.swift — browse the built-in film stocks.

import SwiftUI
import AllStockKit

struct StocksView: View {
    var body: some View {
        NavigationStack {
            List(BuiltinStocks.all) { stock in
                NavigationLink {
                    StockDetail(stock: stock)
                } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(stock.name).font(.headline)
                        Text("\(stock.maker) · ISO \(stock.iso) · \(family(stock))")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Stocks")
        }
    }

    private func family(_ s: FilmStock) -> String {
        s.isMonochrome ? "B&W" : (s.isReversal ? "slide" : "colour negative")
    }
}

struct StockDetail: View {
    let stock: FilmStock
    private var avgGamma: Float {
        (stock.curves.red.gamma + stock.curves.green.gamma + stock.curves.blue.gamma) / 3
    }
    var body: some View {
        List {
            Section(stock.name) { Text(stock.description).font(.callout) }
            Section("Character") {
                row("Contrast (avg γ)", String(format: "%.2f", avgGamma))
                row("Grain rms / size", String(format: "%.3f / %.2fpx", stock.grain.rms, stock.grain.size))
                row("Halation", String(format: "%.2f @ %.0fpx", stock.halation.strength, stock.halation.radius))
                row("Saturation", String(format: "%.2f", stock.printStage.saturation))
                row("Process", stock.development.process)
            }
        }
        .navigationTitle(stock.name)
        .navigationBarTitleDisplayMode(.inline)
    }
    private func row(_ k: String, _ v: String) -> some View {
        HStack { Text(k); Spacer(); Text(v).foregroundStyle(.secondary) }
    }
}
