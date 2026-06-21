# Digital emulation: acutance, MTF & honesty

This note is about *how* a digital pipeline can emulate film honestly, and where
the limits are.

**Sharpness is not one number.** A lens-plus-emulsion system has a **modulation
transfer function (MTF)** — how much contrast survives at each spatial frequency.
Film also shows **adjacency (edge) effects**: during development, exhausted
developer at a dense edge and fresh developer at a light edge exaggerate the
boundary, creating **acutance** — the crisp "bite" at edges that can make film
look sharper than its raw resolution. Emulating film therefore means shaping
*both* gentle low-pass softness and edge enhancement, not just adding a sharpen
filter.

**Why a real engine beats a LUT.** A 3D LUT or a single "film" preset maps colour
to colour, but it cannot know about your highlights (so it cannot bloom them with
**halation**), cannot make grain ride the mid-tones (signal-dependent **grain**),
and cannot respond to a **push**. Driving the look from the actual imaging stages
— curve, halation, grain, optics, print — keeps those behaviours intact.

## Honesty

AllStock models the **perceptual consequences** of the photographic process: a
faithful, *editable* approximation, not a molecular simulation of emulsion
chemistry. Specifically:

- Built-in stock parameters are **characterisations**, not exact datasheet
  transcriptions; the knowledge notes flag where a figure is approximate.
- Effects like reciprocity-failure colour shifts, dye fading over time, and
  scanner-specific quirks are **not** modelled by default.
- The goal is a stronger, real base of analog understanding you can build on —
  not confident-sounding fabrication.

## How AllStock models this

`stock.Optics` (`optics.apply_optics`) provides `acutance` (edge enhancement),
`blur` (low-pass softness) and `vignette` (corner falloff). Combined with the
curve, grain, halation and print stages, the result is a process-driven look
rather than a baked-in filter.
