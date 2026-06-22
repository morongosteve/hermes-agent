# Halation

**Halation** is the glow you see around bright light sources on film. Light from
a highlight passes through the emulsion, hits the film **base**, and a fraction
**reflects back** into the emulsion from the far surface — re-exposing a ring
*around* the original highlight. Because the base is slightly thick, the reflected
light spreads before it returns, so the glow has a soft radius.

Why it is usually faint, and sometimes famous:

- Most films carry an **anti-halation** layer — a dye coating or, on
  motion-picture stock, the black carbon **rem-jet** backing — that absorbs the
  through-light before it can reflect. With it, halation is subtle.
- **CineStill 800T** is motion-picture Kodak Vision3 500T with the **rem-jet
  removed** so it can run in standard C-41. Without that backing, bright lights
  bloom with the signature **red/orange halation** — the layer nearest the base
  is the red-sensitive one, so the reflected light re-exposes red most, giving
  the warm halo around streetlights and neon.

Halation is strongest around the **brightest** highlights (point lights, specular
reflections, the sun), which is why it reads as a threshold effect.

## How AllStock models this

`stock.Halation` (`halation.apply_halation`):

- `threshold` — only highlights brighter than this bloom.
- `strength` — how much reflected light is added back (0 = none; CineStill ≈
  0.55).
- `radius` — the spread of the glow in pixels (the base-thickness blur).
- `color` — the tint of the glow; red-orange ≈ `(1.0, 0.28, 0.10)` for the
  CineStill look, neutral white for B&W.

The effect is computed by isolating highlights above `threshold`, blurring them
by `radius`, tinting by `color`, and adding the result back — a faithful analogue
of light reflecting from the base.
