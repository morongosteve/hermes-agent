# Overview: from emulsion to dried negative

Photographic film turns light into a stable image through a chain of physical
and chemical stages. AllStock models the **perceptual consequences** of each
stage, in the same order film does, so that a "look" emerges from process rather
than from an arbitrary filter.

The chain, and where each stage lives in the code:

1. **Scene light** reaches the film. We work in *linear, scene-referred* light
   (`imaging.srgb_to_linear`), because exposure and density are only meaningful
   there.
2. **Spectral sensitivity** — sensitising dyes decide how strongly each emulsion
   layer responds to the scene's colours (`spectral-sensitivity`,
   `stock.Spectral`).
3. **Latent image** — exposure deposits a sub-visible pattern of activated
   silver-halide crystals (`latent-image`); we place the scene on a
   log-exposure axis (`curves.scene_to_log_exposure`).
4. **Development** — chemistry amplifies the latent image into real silver/dye
   density, following the **characteristic (H&D) curve** (`characteristic-curve`,
   `development`, `push-pull`).
5. **Halation** — light that passed through the emulsion reflects off the base
   and re-exposes the film around highlights (`halation`).
6. **Grain** — developed silver is clumpy, so density carries
   signal-dependent texture (`grain`).
7. **Print / scan** — the negative is inverted and balanced into a viewable
   positive (`scanning-printing`, `color-negative`, `stock.Print`).
8. **Optics** — the lens+emulsion MTF sets sharpness, acutance and any vignette
   (`digital-emulation`, `stock.Optics`).

Colour-negative, colour-reversal (slide) and black-and-white films all flow
through this same engine (`engine.develop_array`); the differences live entirely
in the numeric `FilmStock` parameters, which is exactly what lets you blend,
cross and mutate stocks (`designing-stocks`).

**Honesty note.** This is a faithful, *editable* approximation of how film
behaves to the eye — not a molecular simulation of emulsion chemistry. Where a
figure below is approximate, the note says so.
