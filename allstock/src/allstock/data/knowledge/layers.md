# Layer structure

Silver halide is inherently sensitive mainly to **blue and ultraviolet** light.
To record full colour, colour film stacks several emulsion layers, each
**spectrally sensitised** to a different band, in a specific order.

A classic colour-negative stack, top (light enters here) to bottom:

1. **Blue-sensitive layer** (forms **yellow** dye).
2. **Yellow filter layer** — absorbs blue so it cannot leak into the layers
   below. (Because all silver halide is blue-sensitive, the green and red layers
   must be shielded from blue.)
3. **Green-sensitive layer** (forms **magenta** dye).
4. **Red-sensitive layer** (forms **cyan** dye).
5. **Base**, usually with an **anti-halation** backing.

Each layer is often coated as **fast + slow sub-layers** to extend latitude.
The complementary dye assignment (yellow/magenta/cyan) is what makes a colour
*negative*: the image is both tonally and chromatically inverted until printed
(`color-negative`).

Black-and-white film is the simple case: a single panchromatic emulsion that
records all visible light as one silver image — no colour layers, no yellow
filter.

## How AllStock models this

AllStock does not literally coat layers; it represents the **three colour
records** as the three channel curves in `stock.Curves` (`red`, `green`,
`blue`), each a full characteristic curve (`characteristic-curve`). The overlap
and cross-talk between layer sensitivities is captured by the 3×3
`stock.Spectral` matrix (`spectral-sensitivity`). Black-and-white stocks
(`process_family = bw_negative`) collapse to a single panchromatic tone curve in
the engine (`engine._develop_bw`), weighted by the green row of the spectral
matrix.
