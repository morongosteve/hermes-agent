# The characteristic (H&D) curve

The **characteristic curve** — also called the **H&D curve** after Hurter and
Driffield — plots developed **density (D)** against **log exposure (log H)**. It
is the single most important description of how a film renders tone, and the
heart of AllStock's engine.

Its regions, from shadows to highlights:

- **Base + fog (Dmin).** The minimum density of developed film even with no
  image exposure: base tint plus chemical fog.
- **Toe.** A gently rising shoulder-of-the-shadows where density climbs slowly
  out of Dmin. The toe sets how shadows roll in and how much shadow separation
  you keep.
- **Straight-line section.** The roughly linear middle, whose **slope is the
  gamma (γ)** — the **contrast**. A steep gamma means high contrast and little
  latitude; a gentle gamma means low contrast and wide latitude. (Strictly,
  "gamma" is the straight-line slope and "average gradient"/CI is measured over a
  working range; AllStock uses a single effective gamma per channel.)
- **Shoulder.** Where the curve bends over and highlights compress toward the
  maximum density (**Dmax**). A long, soft shoulder is what gives negative film
  its famously graceful highlight roll-off.

**Negatives vs slides.** Colour-negative film has a relatively low film gamma
(≈0.5–0.7) and gets its final contrast at the print stage; **reversal/slide**
film carries high contrast in the film curve itself (steeper gamma, short toe and
shoulder, little latitude). Each colour layer has its own curve — differences
between the red/green/blue curves are precisely what create a stock's colour
cast and its tonal "fingerprint".

## How AllStock models this

`stock.ChannelCurve` parameterises one curve per layer:

- `dmin`, `dmax` — the floor and ceiling densities.
- `gamma` — straight-line slope (contrast).
- `toe`, `shoulder` — softness of the shadow roll-in and highlight roll-off.
- `speed` — a horizontal shift of the curve (the film-speed point); per-channel
  `speed` differences are how stocks carry a colour bias.

`curves.density_from_log_exposure` evaluates this shape; push/pull steepens the
effective gamma (`push-pull`). For a negative, the print stage inverts density to
a positive, so the **shoulder of the film curve becomes highlight compression**
in the final image (`scanning-printing`).
