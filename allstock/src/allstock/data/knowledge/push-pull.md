# Push / pull processing

**Pushing** means rating a film at a higher ISO than its box speed and then
**over-developing** to compensate (e.g. shooting ISO 400 film at 1600 = "push 2
stops"). **Pulling** is the opposite: rate lower and under-develop. The exposure
happens in-camera; the *push/pull* itself is a **development** choice
(`development`), usually achieved by extending or shortening development time.

What it actually does to the image:

- **Contrast increases with push** (and decreases with pull). Extended
  development steepens the effective **gamma** of the characteristic curve
  (`characteristic-curve`), so a 2-stop push looks noticeably contrastier.
- **Shadows do not come back.** Pushing develops the highlights and mid-tones
  harder, but the shadows were under-exposed in-camera and there is little latent
  image there to amplify — so **shadow detail is lost** and blacks block up.
- **Grain grows.** Harder development enlarges and strengthens the silver clumps,
  so pushed film is visibly grainier (`grain`).
- **Colour shifts** can appear in pushed colour film as the layers respond
  unevenly.

Push/pull is therefore a genuine creative tool, not just exposure correction: it
trades shadow detail and grain for speed and punch.

## How AllStock models this

The develop-time `DevelopOptions.push` (or the stock's
`development.push_pull`) drives two coupled effects in the engine:

- a **gamma gain** of `push × development.dev_contrast_gain` added to each
  curve's slope (more contrast);
- a **shadow loss** of `push × development.dev_shadow_loss` subtracted from
  log-exposure (blocked-up shadows).

Grain naturally reads stronger as contrast rises. Try
`allstock develop night.jpg --stock cinestill800t --push 2` to see contrast,
blocked shadows and grain move together.
