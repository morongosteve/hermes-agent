// DevelopView.swift — pick a photo, choose a stock, develop it on-device.

import SwiftUI
import PhotosUI
import AllStockKit

struct DevelopView: View {
    @State private var pickerItem: PhotosPickerItem?
    @State private var sourceImage: UIImage?
    @State private var developedImage: UIImage?
    @State private var stock: FilmStock = BuiltinStocks.portra400
    @State private var push: Double = 0
    @State private var isWorking = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    PhotosPicker(selection: $pickerItem, matching: .images) {
                        Label(sourceImage == nil ? "Choose a photo" : "Choose a different photo",
                              systemImage: "photo.on.rectangle")
                    }
                    .buttonStyle(.borderedProminent)

                    if let img = developedImage ?? sourceImage {
                        Image(uiImage: img)
                            .resizable().scaledToFit()
                            .frame(maxHeight: 360)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }

                    if sourceImage != nil {
                        controls
                    }
                }
                .padding()
            }
            .navigationTitle("Develop")
            .toolbar {
                if let dev = developedImage {
                    ToolbarItem(placement: .topBarTrailing) {
                        ShareLink(item: Image(uiImage: dev), preview: .init("Developed", image: Image(uiImage: dev))) {
                            Image(systemName: "square.and.arrow.up")
                        }
                    }
                }
            }
        }
        .onChange(of: pickerItem) { _, newValue in Task { await load(newValue) } }
    }

    private var controls: some View {
        VStack(spacing: 12) {
            Picker("Film stock", selection: $stock) {
                ForEach(BuiltinStocks.all) { s in Text(s.name).tag(s) }
            }
            .pickerStyle(.menu)

            VStack(alignment: .leading) {
                Text("Push / pull: \(push, specifier: "%.0f") stop(s)").font(.caption)
                Slider(value: $push, in: -2...2, step: 1)
            }

            Button {
                Task { await develop() }
            } label: {
                if isWorking { ProgressView() } else { Text("Develop on \(stock.name)") }
            }
            .buttonStyle(.borderedProminent)
            .disabled(isWorking || sourceImage == nil)

            if developedImage != nil {
                Button("Save to Photos") { saveToPhotos() }   // needs NSPhotoLibraryAddUsageDescription
            }
        }
    }

    private func load(_ item: PhotosPickerItem?) async {
        guard let item, let data = try? await item.loadTransferable(type: Data.self),
              let img = UIImage(data: data) else { return }
        sourceImage = img
        developedImage = nil
    }

    private func develop() async {
        guard let source = sourceImage else { return }
        isWorking = true
        let chosen = stock, pushStops = Float(push)
        let result: UIImage? = await Task.detached(priority: .userInitiated) {
            guard let linear = FloatImage(uiImage: source) else { return nil }
            var opts = DevelopOptions(); opts.push = pushStops == 0 ? nil : pushStops
            return FilmEngine.develop(linear, stock: chosen, options: opts).toUIImage()
        }.value
        developedImage = result
        isWorking = false
    }

    private func saveToPhotos() {
        guard let dev = developedImage else { return }
        UIImageWriteToSavedPhotosAlbum(dev, nil, nil, nil)
    }
}
