# Shipping AllStock to the iOS App Store

AllStock is a **Python engine + CLI** — you can't upload that to the App Store.
Apple only accepts native iOS apps built and signed with Xcode, and rejects
command-line/utility-only submissions (Guideline 4.2). So the work is two halves:

1. **Build an iOS app** around the engine, then
2. **Submit that app.**

This repo ships starting points for half 1:

- **`../ios/`** — *Option A (native port):* a Swift package (`AllStockKit`) that
  re-implements the engine on-device, plus a SwiftUI app scaffold.
- **`../server/`** (i.e. `src/allstock/server/`) — *Option B (backend):* a FastAPI
  service exposing the existing Python engine over HTTP for a thin client.

---

## Step 0 — Decide how the engine runs on iOS

| Option | What it means | Effort | Best when |
|---|---|---|---|
| **A. Native port** | Engine reimplemented in Swift (`ios/AllStockKit`); move hot loops to Core Image/Metal later. | High | A real, fast, **offline** product |
| **B. Backend API** | Python engine stays on a server (`src/allstock/server`); app is a thin HTTPS client. | Low–Med | Fastest testable MVP |
| **C. Embed Python** | Ship CPython+NumPy+Pillow via BeeWare/Briefcase. | Med–High, fragile | You must reuse the Python verbatim |

**Recommendation:** **A** for the store (clean review, offline, no hosting), or
**B** to get something on a device this week. C works but NumPy/Pillow on iOS and
the "interpreted code" gray area (Guideline 2.5.2) add friction.

The submission steps below are identical whichever you pick.

---

## Part 1 — Build the app

Using the native scaffold:

1. `cd ios/AllStockKit && swift test` to validate the engine on macOS.
2. New Xcode iOS App (SwiftUI); add `ios/AllStockKit` as a local Swift package;
   add the `ios/App/*.swift` screens; add `src/allstock/data/knowledge/` as a
   `knowledge` folder reference for the **Learn** tab. (Full steps in
   [`../ios/README.md`](../ios/README.md).)
3. Screens map to today's CLI: **Develop** (PhotoPicker → stock → develop →
   save/share), **Stocks** (the 11 built-ins), **Learn** (the 15 notes). Add a
   **Design** screen (blend/cross/mutate) when ready.

Permissions (Info.plist usage strings — empty/missing ones get rejected):
- `NSPhotoLibraryAddUsageDescription` — saving developed photos.
- `NSPhotoLibraryUsageDescription` — only if you read beyond the system picker.
- `NSCameraUsageDescription` — only if you add in-app capture.

---

## Part 2 — One-time Apple setup

1. **Apple Developer Program** — <https://developer.apple.com/programs/>, **$99/yr**.
   (Organization enrollment needs a D-U-N-S number; allow extra days.)
2. **Bundle ID / App ID** — usually created automatically when Xcode signs.
3. **Signing** — Xcode ▸ *Signing & Capabilities* ▸ **Automatically manage
   signing** ▸ select your team. Xcode handles the distribution cert + profile.

---

## Part 3 — App Store Connect listing

1. **Create the app** — [App Store Connect](https://appstoreconnect.apple.com) ▸
   *Apps ▸ +*, pick the bundle ID, name **"AllStock"** (check availability),
   **category: Photo & Video**.
2. **Metadata** — subtitle, description, keywords, support + marketing URLs.
   (Reuse the README framing.)
3. **Screenshots** — required for the largest iPhone (currently **6.9"**); add
   **13" iPad** if supported. Tip: `examples/demo.py`'s contact sheet is great
   source material.
4. **App Privacy** — fill the nutrition label. **Option A/C, fully offline →
   declare *no data collected*** (a selling point). Option B → declare photo upload.
5. **Age rating**, **pricing/availability**, and **export compliance**
   (`ITSAppUsesNonExemptEncryption = NO` if you only use standard HTTPS).

---

## Part 4 — Build, test, submit

1. **Archive** — destination *Any iOS Device (arm64)* ▸ *Product ▸ Archive*.
2. **Upload** — Organizer ▸ *Distribute App ▸ App Store Connect ▸ Upload*
   (or `xcodebuild -exportArchive` / Transporter in CI).
3. **TestFlight** — test on real devices, invite beta testers, fix crashes here.
4. **Submit for Review** — attach the build to the version and submit.
   First reviews are typically ~24–48h.

---

## Part 5 — After submission

1. **Respond to App Review** in the Resolution Center; make sure a reviewer can
   reach real functionality without a login wall (have a demo flow ready).
2. **Release** — automatic on approval, or manual/phased.
3. **Iterate** — bump build/version and repeat Part 4 for each update.

---

## AllStock-specific pitfalls

- **Guideline 4.2 (minimum functionality):** ship a real touch-native
  experience (live preview, the stock designer, the Learn notes) — not a thin
  CLI-port file utility.
- **NumPy/Pillow on iOS (Option C):** the hardest part — budget time for
  cross-compiled wheels. Main reason to prefer the native port.
- **Generation providers:** if you ship `generate`, never embed API keys; omit
  it from v1 or proxy through your backend (`src/allstock/server`).
- **Already done for you:** the **15 knowledge notes** and the **stock JSONs**
  bundle straight into the app, so *Learn*, *Stocks* and *Design* are mostly UI
  over data that already exists and is tested.
