# Designing your own stocks

The point of describing a film as **legible numeric data** (`stock.FilmStock`) is
that you are not limited to the built-in emulsions — you can **forge your own**.
Because every stock shares the same parameter groups (spectral, curves, grain,
halation, optics, print, development), any two can be combined mathematically to
make a third. This is the creative control closed generators withhold.

The combination operations (`allstock.designer`, CLI `allstock design`):

- **`blend(a, b, t)`** — interpolate *every* numeric parameter between two
  stocks. `t = 0` is `a`, `t = 1` is `b`, `t = 0.3` is 30% of the way toward `b`.
  *"Portra, nudged 30% toward Velvia's saturation and contrast."*
- **`mix([...], weights)`** — a weighted average of several stocks at once.
- **`cross(base, grain=…, halation=…, curves=…)`** — keep one stock's body but
  **splice in a subsystem** from another: e.g. Ektachrome tone with Tri-X grain
  and CineStill halation ("frankenfilm").
- **`mutate(stock, amount, seed)`** — randomly perturb parameters to **explore
  nearby looks**; the `seed` makes a mutation reproducible.
- **`adjust(stock, "grain.rms"=…)`** — set any single parameter by its dotted
  path.

Two things keep forged stocks sane:

- **Lineage.** Every forged stock records the `lineage` it was derived from, so a
  look is traceable (shown by `allstock stocks --show my_stock.json`).
- **Clamping.** Parameters are clamped to physically sensible ranges, so a blend
  or mutation cannot produce a nonsensical negative-gamma or out-of-range stock.

## Try it

```bash
allstock design blend portra400 velvia50 -t 0.3 -o my_stock.json
allstock design cross ektachrome100 --grain trix400 --halation cinestill800t -o frankenfilm.json
allstock design mutate portra400 --amount 0.2 --seed 42 -o mutant.json
allstock develop photo.jpg --stock my_stock.json -o result.jpg
```

A stock is just JSON: open it, read it, edit a number, develop again.
