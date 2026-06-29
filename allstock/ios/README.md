# AllStock iOS — native scaffold (Option A)

A starting point for an iOS app built around a **native Swift port** of the
AllStock film engine. Two pieces:

```
ios/
├── AllStockKit/        # Swift package: the engine, pure Foundation (no UIKit)
│   ├── Package.swift
│   ├── Sources/AllStockKit/
│   │   ├── FloatImage.swift     sRGB<->linear, blur, luminance, vignette
│   │   ├── Curves.swift         H&D curve (port of curves.py)
│   │   ├── RNG.swift            seeded PRNG for reproducible grain
│   │   ├── FilmStock.swift      Codable model — decodes the SAME JSON as Python
│   │   ├── BuiltinStocks.swift  the 11 built-in stocks
│   │   └── FilmEngine.swift     develop + halation + grain + optics
│   └── Tests/AllStockKitTests/  unit tests (`swift test`)
└── App/                # SwiftUI app target (needs UIKit/PhotosUI)
    ├── AllStockApp.swift   @main + tabs
    ├── ImageBridge.swift   UIImage <-> FloatImage
    ├── DevelopView.swift   pick a photo, choose a stock, develop on-device
    ├── StocksView.swift    browse the 11 stocks
    └── LearnView.swift     read the bundled knowledge notes
```

`AllStockKit` is a faithful CPU port of the Python engine — the same spectral
mix, H&D curve, push/pull, negative inversion, halation, signal-dependent grain
and optics. It decodes the **same stock JSON** the Python designer and the HTTP
API emit, so forged stocks move between the two unchanged.

> ⚠️ **Not compiled in this repo's CI.** This Swift code targets the iOS/macOS
> SDKs and is meant to be opened in **Xcode on macOS**; it is provided as a
> reviewed starting point, not a verified build. The engine math mirrors the
> Python (which *is* tested) line for line.

## Build & run

**1. Test the engine (macOS, no Xcode project needed):**
```bash
cd ios/AllStockKit && swift test
```

**2. Create the app** (Xcode 15+, deployment target **iOS 17+** — the app uses
`ContentUnavailableView` and the two-parameter `onChange`)**:**
1. Xcode ▸ *File ▸ New ▸ Project ▸ iOS App* (SwiftUI). Set a bundle id, e.g. `com.yourname.allstock`.
2. *File ▸ Add Package Dependencies… ▸ Add Local…* and select `ios/AllStockKit`.
3. Delete the template `ContentView.swift`/`App.swift` and add the files from `ios/App/`.
4. Add the knowledge notes for the **Learn** tab: drag
   `src/allstock/data/knowledge/` into the project as a **folder reference**
   named `knowledge` (Create folder references, add to target).
5. In *Signing & Capabilities*, set your team (automatic signing).
6. In the target's Info, add **`NSPhotoLibraryAddUsageDescription`** =
   "Save your developed photos to your library." (required by *Save to Photos*).

**3. Submit:** follow [`../docs/IOS_APP_STORE.md`](../docs/IOS_APP_STORE.md).

## Production notes
- The engine here is clear, correct CPU code — great for previews up to ~1600px
  (the bridge downscales by default). For full-res exports and live sliders,
  port the hot loops (`FilmEngine`) to **Core Image** `CIColorKernel` / **Metal**;
  `FloatImage` + the math in this kit are the contract those shaders must match.
- Generation providers are intentionally absent from this offline scaffold. If
  you add them, proxy keys through a backend (see `../server/`), never ship keys
  in the app.
