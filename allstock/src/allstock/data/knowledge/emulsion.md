# The emulsion

A photographic emulsion is a thin layer of **light-sensitive silver-halide
crystals** (mostly silver bromide, often with some iodide) suspended in
**gelatin**, coated onto a flexible **base** (historically cellulose triacetate;
most 35mm camera film today uses a polyester/PET base).

Key physical facts that shape the look:

- **Crystal size sets speed and grain.** Bigger silver-halide crystals capture
  light more efficiently — higher ISO — but develop into larger, more visible
  clumps of silver, i.e. coarser grain. This is the fundamental
  speed-versus-grain trade-off (`grain`).
- **Gelatin is not inert.** It holds the crystals in place, lets developer
  diffuse in, and hardens during processing. Its swelling/shrinking during
  wet processing and drying contributes tiny non-uniformities (`drying`).
- **The base is nearly clear but slightly reflective.** Light that passes all
  the way through the emulsion can reflect off the base back into the emulsion,
  causing **halation** (`halation`). An **anti-halation** layer (a dye coating,
  or the **rem-jet** carbon backing on motion-picture film) normally absorbs it.
- **Base + fog density (Dmin).** Even unexposed, developed film is not perfectly
  clear: the base tint plus chemical fog give a minimum density. Colour negatives
  add a deliberate orange **mask** on top of this (`color-negative`).

## How AllStock models this

The emulsion is not one parameter — it is the *whole stock*. But two leaves map
most directly to emulsion physics:

- `curves.*.dmin` is the base+fog floor of each layer.
- `grain.size` and `grain.rms` stand in for crystal size and granularity.

Multilayer colour film stacks several emulsions with different colour
sensitivities; see `layers`.
