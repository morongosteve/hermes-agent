# The latent image

When light strikes a silver-halide crystal, absorbed photons free electrons that
reduce a few silver ions to metallic silver atoms. A crystal that accumulates a
small cluster of silver atoms (a **sensitivity speck**, around the order of a few
atoms — an approximate threshold) becomes **developable**. This invisible,
sub-microscopic pattern of "switched-on" crystals is the **latent image**. The
Gurney–Mott mechanism is the standard description of this electron-then-ion
process.

Crucial properties:

- **It is a threshold, statistical process.** Whether a given crystal becomes
  developable depends on how many photons it caught — so exposure maps to
  *probability of development*, which is the microscopic origin of the smooth
  **characteristic curve** and of **grain** (`characteristic-curve`, `grain`).
- **Reciprocity and its failure.** Over normal shutter speeds, exposure ≈
  intensity × time (the **reciprocity law**). At very long or very short
  exposures the law **fails**: film loses effective speed and colour layers can
  shift unevenly, causing colour casts in, say, multi-second night exposures.
- **Logarithmic by nature.** Vision and film both work over a huge range of
  intensities, so exposure is described on a **base-10 log axis** (log-H).

## How AllStock models this

The scene is converted to a **log-exposure** value per layer
(`curves.scene_to_log_exposure`), with the develop-time `exposure` (stops) added
there. This log-H value is the input to the characteristic curve. AllStock models
the *consequences* of the latent-image statistics (the curve shape and
signal-dependent grain) rather than simulating individual crystals; classical
reciprocity-failure colour shifts are not modelled by default.
