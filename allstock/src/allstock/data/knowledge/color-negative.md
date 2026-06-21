# Colour negative & the orange mask

A colour **negative** records the scene inverted both in tone and in colour: a
bright red subject becomes a dark cyan patch on the developed film. During
development, oxidised developer reacts with **dye couplers** in each layer to form
**cyan, magenta and yellow** dyes alongside (and then in place of) the silver,
which is bleached and fixed away.

The distinctive **orange cast** of a colour negative is deliberate. It is an
**integral coloured mask**: the cyan and magenta dyes are imperfect — they absorb
some light they should transmit — so the film builds in orange-tinted coupler
layers that **compensate for those unwanted absorptions**. The mask makes
unexposed negative look orange, but it lets the printing/scanning stage recover
cleaner, more accurate colour. Slide (reversal) film has **no** orange mask.

Because the negative's contrast is intentionally low (film gamma ≈ 0.5–0.7), the
**print or scan supplies the rest of the contrast and the colour balance**
(`scanning-printing`). This two-stage "print-through" is why the same negative can
yield very different looks, and why real film character is *negative character ×
paper/scanner character*.

## How AllStock models this

The engine develops each layer to density via its characteristic curve, then the
print stage **inverts** it (`engine._develop_color`: a bright scene → high density
→ bright positive). `stock.Print` then applies:

- `balance` — the print/scan white-balance gains (the colour-correction the
  orange mask is designed to enable);
- `orange_mask` — an optional explicit mask-removal term that nudges balance
  cooler;
- `gamma`, `saturation`, `black_point`/`white_point` — the rest of the print
  contrast and colour.

See `development` for the C-41 chemistry and `scanning-printing` for the
inversion.
