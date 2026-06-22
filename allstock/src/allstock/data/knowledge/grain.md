# Grain

Film grain is the visible texture left by the **clumps of developed metallic
silver** (in colour film, the dye clouds that form around those silver clumps).
It is fundamentally different from digital noise in two ways that AllStock takes
seriously:

- **It is signal-dependent, not uniform.** Grain visibility depends on local
  density. It tends to be most apparent in the **mid-tones**, suppressed in clean
  shadows (few developed grains) and in blown highlights (everything saturated).
  Uniform Gaussian noise laid over an image is the classic "fake film" tell.
- **It has structure and scale.** Grains are physical clumps of a particular
  size, so grain has a spatial scale (it is correlated, slightly blurred), not
  per-pixel hash.

Datasheets quote **RMS granularity** (a standardised measure of density
fluctuation read through a 48 µm aperture) — higher means coarser grain. As a
rule, **faster films grain more** (bigger crystals) and grain grows when you
**push** processing (`push-pull`). Colour grain also has a chroma component (dye
clouds in each layer), whereas B&W grain is a single silver channel.

## How AllStock models this

`stock.Grain` (`grain.add_grain`):

- `rms` — overall amplitude (cf. RMS granularity; ~0.008 fine, ~0.03 heavy —
  approximate, perceptual units).
- `size` — grain blob radius in pixels (the spatial scale; the noise is blurred
  to this size).
- `shadow_weight`, `mid_weight`, `highlight_weight` — shape how grain rides the
  tone scale, giving the mid-tone-peaked, signal-dependent behaviour.
- `chroma` — 0 = monochrome silver grain, 1 = full per-channel colour grain.
- `mono` — force a single silver channel (used by B&W stocks).

The amplitudes are perceptual characterisations, not calibrated granularity
numbers.
