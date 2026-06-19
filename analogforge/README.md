# AnalogForge

**Physically-grounded analog film emulation, a film-stock designer, an analog
knowledge base, and analog-aware image generation — in one Python engine.**

Replicate film *from the emulsion to the dried negative*, and **forge your own
film stocks** by combining the ones you love.

---

## Why this exists

Modern generators (e.g. Reve) are remarkable at turning intent into pixels, but
two limitations come up again and again in their own analyses:

1. **No real customization** — you cannot fine-tune, you cannot build your own
   looks; you take what the model gives you.
2. **Flat, literal rendering** — outputs are often described as lacking the
   tonal depth and "physics" of real photography.

AnalogForge is built as the deliberate inverse of those gaps, specialised for
**analog film**:

- **Physical truth instead of filters.** Every effect comes from simulating a
  real stage of the photographic process — spectral sensitivity, the
  characteristic (H&D) curve with its highlight shoulder, signal-dependent
  grain, halation, and the negative→print inversion. See the built-in
  [`knowledge base`](#learn-the-craft).
- **Total creative control.** A film stock is a fully numeric, legible
  description. You can **blend, mix, cross-breed and mutate** stocks to create —
  and keep — your own.
- **Analog-aware generation.** Generate an image (Z.ai / CogView by default, plus
  OpenAI, Stability, Hugging Face, Replicate), then run it through the *real*
  film engine so it inherits genuine film tonality — not a baked-in LUT.

It is also built in the spirit of a second piece of the brief: **don't fabricate
knowledge.** The film science here is grounded and, where a number is
approximate, it says so.

---

## Install

```bash
pip install -e .            # core engine + CLI (numpy + pillow)
pip install -e ".[generate]"  # add networked image generation (requests)
pip install -e ".[dev]"       # add pytest
```

Python ≥ 3.9. Core dependencies are just **NumPy** and **Pillow**.

---

## Quick start (CLI)

```bash
# Develop a photo on Kodak Portra 400
analogforge develop photo.jpg -o portra.jpg --stock portra400

# Push CineStill 800T two stops and watch the halation bloom
analogforge develop night.jpg --stock cinestill800t --push 2

# List and inspect stocks
analogforge stocks
analogforge stocks --show velvia50

# Forge your own stock: 30% of the way from Portra toward Velvia
analogforge design blend portra400 velvia50 -t 0.3 -o my_stocks/portra_velvia.json
analogforge develop photo.jpg --stock my_stocks/portra_velvia.json

# Cross-breed: Ektachrome tone, Tri-X grain, CineStill halation
analogforge design cross ektachrome100 --grain trix400 --halation cinestill800t -o frankenfilm.json

# Generate an image and truly develop it on film (Z.ai by default)
export ZAI_API_KEY=...        # or run offline with: --provider null
analogforge generate "a rain-slick neon alley at midnight" --stock cinestill800t -o alley.png

# Learn the craft
analogforge learn                       # list topics
analogforge learn characteristic-curve  # read one
analogforge learn --search halation
```

---

## Quick start (Python)

```python
from analogforge import library, engine, designer

# Develop
stock = library.get_stock("portra400")
engine.develop_file("in.jpg", "out.jpg", stock,
                    engine.DevelopOptions(exposure=+0.5, push=1))

# Forge a new stock and keep it
custom = designer.blend(library.get_stock("gold200"),
                        library.get_stock("ektar100"), 0.5,
                        name="Golden Ektar")
custom = designer.adjust(custom, **{"halation.strength": 0.2})
custom.save("my_stocks/golden_ektar.json")

# Generate + develop
from analogforge import generate
positive, info = generate.generate_and_develop(
    "a misty harbour at dawn", stock, provider="zai")   # or provider="null" offline
```

See `examples/demo.py` for a contact sheet across every stock (runs offline).

---

## How the engine works

The pipeline follows the real imaging chain (full detail in `analogforge learn`):

| Stage | Module | Knowledge note |
|------|--------|----------------|
| sRGB → linear light | `imaging` | `overview` |
| spectral sensitivity (layer mixing) | `engine`, `stock.Spectral` | `spectral-sensitivity` |
| exposure → log exposure | `curves` | `latent-image` |
| development → density (H&D curve, push/pull) | `curves`, `stock.Development` | `characteristic-curve`, `development`, `push-pull` |
| print / scan (invert, balance, contrast) | `engine`, `stock.Print` | `scanning-printing`, `color-negative` |
| halation (highlight glow) | `halation` | `halation` |
| grain (signal-dependent) | `grain` | `grain` |
| optics (acutance, softness, vignette) | `optics` | `digital-emulation` |

Negative, reversal (slide) and black-and-white films all flow through the same
code; the differences live entirely in the stock's parameters.

---

## The film-stock model

Everything about a stock is data you can read and edit:

```
FilmStock
├── spectral      3×3 colour band-overlap matrix
├── curves        R / G / B characteristic curves (dmin, dmax, gamma, speed, toe, shoulder)
├── grain         rms, size, chroma, tone weighting, mono
├── halation      strength, radius, threshold, colour
├── optics        acutance, blur, vignette
├── print_        gamma, balance, saturation, black/white point, orange-mask
└── development   process, push/pull
```

Built-in stocks include **Portra 400/160, Gold 200, Ektar 100, Pro 400H,
CineStill 800T, Velvia 50, Ektachrome E100, Tri-X 400, HP5 Plus** — honest
characterisations to start from.

### Combination edits (the point)

- **blend(a, b, t)** — interpolate everything between two stocks
- **mix([...], weights)** — weighted average of several
- **cross(base, grain=…, halation=…, curves=…)** — splice subsystems
- **mutate(stock, amount, seed)** — explore nearby looks
- **adjust(stock, "grain.rms"=…)** — set any parameter

Every forged stock records its **lineage** and is clamped to physically sensible
ranges.

---

## Learn the craft

A grounded knowledge base ships with the package and is readable from the CLI
(`analogforge learn`) or `analogforge.knowledge`:

`overview · emulsion · layers · spectral-sensitivity · latent-image ·
characteristic-curve · grain · halation · color-negative · development ·
push-pull · drying · scanning-printing · digital-emulation · designing-stocks`

---

## Generation providers

Default is **Z.ai (Zhipu)**, whose flagship text-to-image family is **CogView**
(default model `cogview-4`; set `ZAI_IMAGE_MODEL` / `ZAI_BASE_URL` to target a
newer one). Also supported: `openai`, `stability`, `huggingface`, `replicate`,
and `null` (offline synthetic, for testing the pipeline with no key).

Set the relevant key: `ZAI_API_KEY` (or `ZHIPUAI_API_KEY`), `OPENAI_API_KEY`,
`STABILITY_API_KEY`, `HF_API_TOKEN`, `REPLICATE_API_TOKEN`.

---

## Tests

```bash
pytest
```

---

## Status & honesty

AnalogForge models the **perceptual consequences** of the photographic process —
a faithful, *editable* approximation, not a molecular simulation of emulsion
chemistry. Built-in stock parameters are characterisations, not exact datasheet
transcriptions; the knowledge notes flag where figures are approximate. This is
deliberate: the brief asked for a stronger, real base of analog knowledge, not
confident-sounding fabrication.

## License

MIT — see [LICENSE](LICENSE).
