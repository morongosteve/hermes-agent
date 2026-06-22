# Development

Development is the chemical amplification that turns the invisible **latent
image** (`latent-image`) into real, visible density. A developing agent
selectively reduces the *exposed* silver-halide crystals to metallic silver; the
gain is enormous (a few silver atoms in a crystal trigger the reduction of the
whole crystal), which is why film is sensitive at all.

The standard processes:

- **C-41** — the colour-negative process. Colour developer forms dye at the
  couplers; a bleach + fixer ("blix") then removes the silver, leaving only the
  cyan/magenta/yellow dye image. Run at a closely controlled **≈37.8 °C / 100 °F**.
- **E-6** — the colour-**reversal** (slide) process: a first (black-and-white)
  developer, a reversal step, then a colour developer, producing a positive
  transparency.
- **ECN-2** — the motion-picture colour-negative process (Kodak Vision3 etc.),
  which includes a **rem-jet** removal step. CineStill 800T is ECN-2 stock
  adapted to run in C-41 (`halation`).
- **B&W** — develop, stop, fix; enormous creative latitude in developer choice,
  dilution, time and agitation.

Three controls dominate the result: **time, temperature and agitation**. More of
any of them generally means more density and more contrast — the basis of
**push/pull** processing (`push-pull`). Temperature control is critical for
colour (off-temperature C-41 shifts colour and contrast).

## How AllStock models this

`stock.Development` carries the **process choices**, not fixed emulsion
properties:

- `process` — "C-41" / "E-6" / "ECN-2" / "B&W" (descriptive label).
- `push_pull` — stops of push (+) / pull (−), settable at develop time.
- `dev_contrast_gain` — how strongly a stop of push steepens gamma.
- `dev_shadow_loss` — shadow density lost per stop of push.

The engine reads these in `engine._develop_color` / `_develop_bw`; see
`push-pull` for the tonal trade-offs.
