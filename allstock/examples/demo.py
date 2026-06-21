#!/usr/bin/env python3
"""AllStock offline demo: a contact sheet across every built-in film stock.

Runs **100% offline** — no API key, no network. It synthesises one test scene
and develops it on every built-in stock, then tiles the results into a single
contact sheet so the looks can be compared side by side.

    python examples/demo.py
    # -> examples/output/contact_sheet.png

The synthetic scene includes a bright sun disc (so halation-heavy stocks such as
CineStill 800T visibly bloom) plus smooth tonal/colour gradients. The first cell
is the undeveloped input scene for reference; the rest are the input developed on
each stock.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Allow running from a source checkout without `pip install`.
SRC = Path(__file__).resolve().parent.parent / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from allstock import engine, library  # noqa: E402
from allstock.generate import get_provider  # noqa: E402
from allstock.imaging import srgb_to_linear, to_uint8_srgb  # noqa: E402

TILE_W, TILE_H = 360, 260
LABEL_H = 30
HEADER_H = 56
COLS = 4
PAD = 10
SEED = 7
BG = (24, 24, 27)
FG = (236, 236, 238)
DIM = (150, 150, 156)

OUT = Path(__file__).resolve().parent / "output" / "contact_sheet.png"


def _font(size: int):
    for name in ("DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _tile(rgb_u8: np.ndarray, title: str, subtitle: str = "") -> Image.Image:
    cell = Image.new("RGB", (TILE_W, TILE_H + LABEL_H), BG)
    img = Image.fromarray(rgb_u8, "RGB").resize((TILE_W, TILE_H), Image.LANCZOS)
    cell.paste(img, (0, 0))
    draw = ImageDraw.Draw(cell)
    draw.text((7, TILE_H + 6), title, fill=FG, font=_font(15))
    if subtitle:
        tw = draw.textlength(subtitle, font=_font(13))
        draw.text((TILE_W - tw - 7, TILE_H + 8), subtitle, fill=DIM, font=_font(13))
    return cell


def main() -> int:
    keys = library.list_stocks()
    print(f"AllStock demo — developing one synthetic scene on {len(keys)} stocks "
          f"(offline)...")

    # One synthetic scene, generated once at tile resolution, shared by all stocks.
    scene_img = get_provider("null").generate("offline demo scene",
                                              width=TILE_W, height=TILE_H, seed=SEED).image
    scene_u8 = np.asarray(scene_img.convert("RGB"), dtype=np.uint8)
    linear = srgb_to_linear(scene_u8.astype(np.float32) / 255.0)

    tiles = [_tile(scene_u8, "input scene", "synthetic")]
    t0 = time.time()
    for key in keys:
        stock = library.get_stock(key)
        positive = engine.develop_array(linear, stock, engine.DevelopOptions(seed=1))
        tiles.append(_tile(to_uint8_srgb(positive), stock.name, key))
        print(f"  developed on {stock.name}")
    dt = time.time() - t0

    rows = (len(tiles) + COLS - 1) // COLS
    sheet_w = COLS * TILE_W + (COLS + 1) * PAD
    sheet_h = HEADER_H + rows * (TILE_H + LABEL_H) + (rows + 1) * PAD
    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((PAD + 2, 12), "AllStock — contact sheet", fill=FG, font=_font(22))
    draw.text((PAD + 2, 38), f"one scene developed on {len(keys)} built-in stocks "
              f"· 100% offline", fill=DIM, font=_font(13))

    for i, tile in enumerate(tiles):
        r, c = divmod(i, COLS)
        x = PAD + c * (TILE_W + PAD)
        y = HEADER_H + PAD + r * (TILE_H + LABEL_H + PAD)
        sheet.paste(tile, (x, y))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"\nDeveloped {len(keys)} stocks in {dt:.1f}s.")
    print(f"Contact sheet -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
