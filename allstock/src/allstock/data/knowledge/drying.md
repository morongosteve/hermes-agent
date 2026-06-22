# Washing & drying

After the image-forming chemistry, film is **washed** to remove residual
processing chemicals, usually passed through a **final rinse / stabiliser**
(a wetting agent that helps it dry evenly and, in some colour processes, helps
preserve the dyes), and then **dried**. Only after it is dry is the negative
stable, handleable and ready to print or scan.

It is a humble stage, but it leaves real fingerprints:

- **Drying marks and water spots** from uneven drying or hard water.
- **Curl.** The gelatin emulsion and the base shrink by slightly different
  amounts as they dry, so film tends to **curl** (usually toward the emulsion
  side). This is mostly a handling nuisance, but on a scanner it can cause subtle
  **focus and illumination non-uniformity** across the frame.
- **Reticulation** in extreme cases — a crazed texture from large temperature
  swings between processing baths (rare with modern hardened emulsions).

These are second-order cosmetic effects, not part of the tone or colour
rendering, so AllStock treats them as optional flavour rather than core physics.

## How AllStock models this

`stock.Development.dry_curl` is a small **cosmetic** term reserved for residual
drying non-uniformity. It defaults to `0.0` and is deliberately understated:
honest film emulation should not lean on dust-and-scratches gimmicks to look
"analog". The substance of the look comes from the curve, grain, halation and
print stages, not from simulated water spots.
