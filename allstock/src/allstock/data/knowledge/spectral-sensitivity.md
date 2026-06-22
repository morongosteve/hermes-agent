# Spectral sensitivity

Raw silver halide responds mostly to blue/UV. **Spectral sensitisation** —
adding dyes to the emulsion (the discovery that made panchromatic and colour
film possible) — extends and shapes each layer's response so it peaks in the
blue, green or red. The exact shape of those sensitivity curves is a large part
of a stock's colour personality.

Two consequences matter for the look:

- **Bands overlap.** A "green" layer still responds somewhat to yellow and cyan
  light; a "red" layer responds into the orange and deep red. This overlap
  *binds* colours together and is part of why film colour feels cohesive rather
  than clinically separated.
- **Out-of-band quirks.** Real differences here explain things like how some
  films render foliage, skin, or skies — e.g. Fujifilm stocks are often
  characterised by their greens, Kodak by their warm skin rendering. These are
  *characterisations*, not exact spectral measurements.

## How AllStock models this

`stock.Spectral` is a **3×3 matrix** that mixes scene linear RGB into the
exposure each layer receives (`engine._spectral_mix`). The diagonal is the
in-band response; the off-diagonal terms model the overlap/cross-talk between
sensitivity bands. The engine **normalises each row** so a neutral grey scene
stays neutral in exposure — colour bias is then carried deliberately by the
curves' `speed` offsets and the print `balance`, not accidentally by the matrix.

Helper `library._spectral(diag, off)` builds a symmetric matrix: larger `off`
means more cross-talk (softer, more "bound" colour, e.g. classic B&W and
consumer stocks); smaller `off` means cleaner separation (e.g. Ektar, Velvia).
