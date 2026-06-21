# Scanning & printing

A developed colour **negative** is not a viewable picture — it is inverted in
tone and colour and veiled by the orange mask (`color-negative`). Turning it into
a positive happens at the **print or scan** stage, and this stage carries a large
share of the final "look".

Two classic paths:

- **Optical (darkroom) printing.** The negative is projected onto colour
  photographic **paper**, which has its own characteristic curve (a contrast
  boost) and its own colour balance set by the enlarger's filtration. Paper
  contrast is why a low-contrast negative becomes a normal-contrast print.
- **Scanning.** A sensor digitises the negative; software **inverts** it, removes
  the orange mask, and sets the white balance and contrast. Different scanner
  software (and operator choices) can make the *same* negative look quite
  different — this is a real source of variation, not a flaw.

Either way the principle is the same: **invert, remove the mask, balance colour,
and apply an output contrast.** For reversal (slide) film there is no inversion —
the developed film is already a positive — so "printing" is mostly a balance and
contrast pass.

## How AllStock models this

The engine inverts each developed layer to a positive
(`engine._develop_color`: high scene → high density → bright positive), then
`stock.Print` applies the print/scan transform:

- `gamma` — the paper/scan output contrast (negatives need ~1.5; reversal ~1.0
  because the contrast is already in the film);
- `balance` — the colour-balance gains (the enlarger filtration / scanner white
  balance);
- `saturation`, `black_point`, `white_point` — final colour and level shaping;
- `orange_mask` — optional explicit mask-removal nudge.

So a finished AllStock image is a true **print-through**: negative character
shaped by an editable print stage.
