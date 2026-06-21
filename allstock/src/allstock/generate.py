"""Analog-aware image generation.

Reve and its peers can *generate* but they cannot give you real analog control,
and their output is often described as flat and literal. AllStock closes both
gaps:

1. **Analog intent.** :func:`build_analog_prompt` turns a subject plus a chosen
   film stock into a film-aware prompt — the "intent -> representation" idea, but
   pointed at photographic reality (stock name, ISO, process, palette, grain,
   halation). This already biases the generator toward a film look.
2. **Physical truth.** :func:`generate_and_develop` then runs the generated image
   through the real :mod:`allstock.engine`, so the result carries genuine
   characteristic-curve tonality, signal-dependent grain and halation — not a
   baked-in "filter".

Generation is provider-agnostic. The featured provider is **Z.ai (Zhipu)**,
whose flagship text-to-image family is **CogView** (default model ``cogview-4``);
the model id and endpoint are configurable so you can point at the newest Z.ai
image model as it ships. OpenAI, Stability, Replicate and Hugging Face providers
are also included, plus an offline synthetic provider so the pipeline always
runs without network access or keys.
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from .engine import DevelopOptions, develop_array
from .imaging import srgb_to_linear
from .stock import COLOR_REVERSAL, FilmStock


# --------------------------------------------------------------------------
# analog-aware prompt construction
# --------------------------------------------------------------------------
def _palette_words(stock: FilmStock) -> List[str]:
    words: List[str] = []
    p = stock.print_
    r, g, b = p.balance
    if r > 1.03 or (g + b) / 2 < r - 0.03:
        words.append("warm amber tones")
    if b > 1.05:
        words.append("cool blue cast")
    if g > r and g >= b:
        words.append("soft green-leaning palette")
    if p.saturation >= 1.3:
        words.append("vivid saturated colour")
    elif p.saturation <= 0.97:
        words.append("muted pastel colour")
    return words


def build_analog_prompt(subject: str, stock: FilmStock,
                        extra: Optional[str] = None) -> str:
    """Compose a film-aware generation prompt from a subject and a stock."""
    avg_gamma = (stock.curves.red.gamma + stock.curves.green.gamma
                 + stock.curves.blue.gamma) / 3.0
    bits: List[str] = [subject.strip().rstrip(".")]

    if stock.is_monochrome:
        bits.append(f"black and white photograph on {stock.name}")
    elif stock.process_family == COLOR_REVERSAL:
        bits.append(f"shot on {stock.name} slide film")
    else:
        bits.append(f"shot on {stock.name}")

    bits.append(f"ISO {stock.iso}, {stock.development.process} process")
    bits.extend(_palette_words(stock))

    # Contrast / latitude language.
    net = avg_gamma * stock.print_.gamma
    if net <= 0.95:
        bits.append("gentle contrast, soft highlight roll-off, wide dynamic range")
    elif net >= 1.3:
        bits.append("punchy contrast, deep blacks")

    # Grain language.
    if stock.grain.rms >= 0.026:
        bits.append("visible film grain")
    elif stock.grain.rms <= 0.012:
        bits.append("fine grain")

    if stock.halation.strength >= 0.3:
        bits.append("red halation glow around highlights")

    bits.append("analog film photograph, photographic, natural light")
    if extra:
        bits.append(extra.strip())
    return ", ".join([b for b in bits if b])


# --------------------------------------------------------------------------
# providers
# --------------------------------------------------------------------------
@dataclass
class GenerationResult:
    image: Image.Image
    provider: str
    model: str
    prompt: str
    seed: int = 0
    meta: Dict[str, str] = field(default_factory=dict)


class Provider:
    """Base class. Subclasses return a PIL RGB image for a text prompt."""

    name = "base"

    def generate(self, prompt: str, width: int = 1024, height: int = 1024,
                 seed: int = 0) -> GenerationResult:  # pragma: no cover - abstract
        raise NotImplementedError


def _requests():
    try:
        import requests  # noqa
        return requests
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Network image generation needs the 'requests' package. "
            "Install with: pip install 'allstock[generate]'"
        ) from e


def _image_from_url(url: str) -> Image.Image:
    r = _requests().get(url, timeout=120)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def _image_from_b64(data: str) -> Image.Image:
    if data.startswith("data:"):
        data = data.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")


class ZaiProvider(Provider):
    """Z.ai / Zhipu image generation (featured). Flagship family: CogView.

    Set ``ZAI_API_KEY`` (or ``ZHIPUAI_API_KEY``). The OpenAI-style images
    endpoint and model are configurable; defaults target Z.ai CogView-4.
    """

    name = "zai"

    def __init__(self, api_key: Optional[str] = None, model: str = "cogview-4",
                 base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("ZAI_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
        self.model = model or os.getenv("ZAI_IMAGE_MODEL", "cogview-4")
        self.base_url = (base_url or os.getenv("ZAI_BASE_URL")
                         or "https://api.z.ai/api/paas/v4/images/generations")

    def generate(self, prompt: str, width: int = 1024, height: int = 1024,
                 seed: int = 0) -> GenerationResult:
        if not self.api_key:
            raise RuntimeError("Z.ai key missing: set ZAI_API_KEY or ZHIPUAI_API_KEY.")
        payload = {"model": self.model, "prompt": prompt, "size": f"{width}x{height}"}
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        r = _requests().post(self.base_url, json=payload, headers=headers, timeout=180)
        r.raise_for_status()
        data = r.json()
        item = data["data"][0]
        img = _image_from_url(item["url"]) if item.get("url") else _image_from_b64(item["b64_json"])
        return GenerationResult(img, self.name, self.model, prompt, seed)


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-image-1"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def generate(self, prompt: str, width: int = 1024, height: int = 1024,
                 seed: int = 0) -> GenerationResult:
        if not self.api_key:
            raise RuntimeError("OpenAI key missing: set OPENAI_API_KEY.")
        payload = {"model": self.model, "prompt": prompt, "size": f"{width}x{height}"}
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        r = _requests().post("https://api.openai.com/v1/images/generations",
                             json=payload, headers=headers, timeout=180)
        r.raise_for_status()
        item = r.json()["data"][0]
        img = _image_from_b64(item["b64_json"]) if item.get("b64_json") else _image_from_url(item["url"])
        return GenerationResult(img, self.name, self.model, prompt, seed)


class StabilityProvider(Provider):
    name = "stability"

    def __init__(self, api_key: Optional[str] = None,
                 model: str = "sd3.5-large"):
        self.api_key = api_key or os.getenv("STABILITY_API_KEY")
        self.model = model

    def generate(self, prompt: str, width: int = 1024, height: int = 1024,
                 seed: int = 0) -> GenerationResult:
        if not self.api_key:
            raise RuntimeError("Stability key missing: set STABILITY_API_KEY.")
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "image/*"}
        files = {"none": ""}
        data = {"prompt": prompt, "model": self.model, "output_format": "png", "seed": seed}
        r = _requests().post("https://api.stability.ai/v2beta/stable-image/generate/core",
                             headers=headers, files=files, data=data, timeout=180)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        return GenerationResult(img, self.name, self.model, prompt, seed)


class HuggingFaceProvider(Provider):
    name = "huggingface"

    def __init__(self, api_key: Optional[str] = None,
                 model: str = "black-forest-labs/FLUX.1-schnell"):
        self.api_key = api_key or os.getenv("HF_API_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        self.model = model

    def generate(self, prompt: str, width: int = 1024, height: int = 1024,
                 seed: int = 0) -> GenerationResult:
        if not self.api_key:
            raise RuntimeError("Hugging Face token missing: set HF_API_TOKEN.")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        r = _requests().post(f"https://api-inference.huggingface.co/models/{self.model}",
                             headers=headers, json={"inputs": prompt}, timeout=180)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        return GenerationResult(img, self.name, self.model, prompt, seed)


class ReplicateProvider(Provider):
    name = "replicate"

    def __init__(self, api_key: Optional[str] = None,
                 model: str = "black-forest-labs/flux-1.1-pro"):
        self.api_key = api_key or os.getenv("REPLICATE_API_TOKEN")
        self.model = model

    def generate(self, prompt: str, width: int = 1024, height: int = 1024,
                 seed: int = 0) -> GenerationResult:
        if not self.api_key:
            raise RuntimeError("Replicate token missing: set REPLICATE_API_TOKEN.")
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json", "Prefer": "wait"}
        body = {"input": {"prompt": prompt, "width": width, "height": height, "seed": seed}}
        r = _requests().post(f"https://api.replicate.com/v1/models/{self.model}/predictions",
                             headers=headers, json=body, timeout=300)
        r.raise_for_status()
        out = r.json().get("output")
        url = out[0] if isinstance(out, list) else out
        return GenerationResult(_image_from_url(url), self.name, self.model, prompt, seed)


class NullProvider(Provider):
    """Offline synthetic 'scene'. Lets the whole pipeline run with no key/network
    — used for tests, demos and previews. Produces a lit scene with a bright
    source (so halation is visible) and smooth tonal gradients."""

    name = "null"

    def __init__(self, model: str = "synthetic"):
        self.model = model

    def generate(self, prompt: str, width: int = 1024, height: int = 1024,
                 seed: int = 0) -> GenerationResult:
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        nx, ny = xx / max(width - 1, 1), yy / max(height - 1, 1)
        sky = np.clip(0.95 - 0.7 * ny, 0, 1)
        ground = np.clip(0.5 - 0.4 * (ny - 0.6), 0, 1) * (ny > 0.6)
        base = sky + ground
        r = base * (0.7 + 0.3 * nx)
        g = base * (0.6 + 0.2 * (1 - nx))
        b = base * (0.8 - 0.2 * nx)
        # A bright sun disc to exercise halation.
        cx, cy = 0.72 * width, 0.28 * height
        rad = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        sun = np.clip(1.0 - rad / (0.06 * max(width, height)), 0, 1) ** 2
        r = np.clip(r + sun, 0, 1.2)
        g = np.clip(g + sun, 0, 1.2)
        b = np.clip(b + 0.8 * sun, 0, 1.2)
        img = np.clip(np.stack([r, g, b], -1) * 255, 0, 255).astype(np.uint8)
        return GenerationResult(Image.fromarray(img, "RGB"), self.name, self.model,
                                prompt, seed, meta={"note": "offline synthetic scene"})


_PROVIDERS = {
    "zai": ZaiProvider,
    "zhipu": ZaiProvider,
    "cogview": ZaiProvider,
    "openai": OpenAIProvider,
    "stability": StabilityProvider,
    "huggingface": HuggingFaceProvider,
    "hf": HuggingFaceProvider,
    "replicate": ReplicateProvider,
    "null": NullProvider,
    "offline": NullProvider,
}


def get_provider(name: str = "zai", **kwargs) -> Provider:
    """Return a provider by name (default Z.ai). Unknown names raise."""
    key = name.lower()
    if key not in _PROVIDERS:
        raise KeyError(f"Unknown provider {name!r}. "
                       f"Choose from: {', '.join(sorted(set(_PROVIDERS)))}")
    return _PROVIDERS[key](**kwargs)


# --------------------------------------------------------------------------
# the headline: generate, then truly develop on film
# --------------------------------------------------------------------------
def generate_and_develop(subject: str, stock: FilmStock, *,
                         provider: str = "zai", width: int = 1024, height: int = 1024,
                         seed: int = 0, raw_prompt: bool = False,
                         extra: Optional[str] = None,
                         develop: Optional[DevelopOptions] = None,
                         provider_kwargs: Optional[Dict] = None):
    """Generate an image for ``subject`` then develop it on ``stock``.

    Returns ``(linear_positive, GenerationResult)``. With ``raw_prompt=True`` the
    subject is used verbatim; otherwise it is expanded by
    :func:`build_analog_prompt` into film-aware language.
    """
    prompt = subject if raw_prompt else build_analog_prompt(subject, stock, extra)
    prov = get_provider(provider, **(provider_kwargs or {}))
    result = prov.generate(prompt, width=width, height=height, seed=seed)

    arr = np.asarray(result.image.convert("RGB"), dtype=np.float32) / 255.0
    linear = srgb_to_linear(arr)
    opts = develop or DevelopOptions(seed=seed)
    positive = develop_array(linear, stock, opts)
    return positive, result
