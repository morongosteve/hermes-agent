"""AllStock HTTP API (FastAPI).

A thin, stateless web service that exposes the existing AllStock engine over
HTTP so a native client — for example the iOS app scaffold in ``allstock/ios`` —
can develop photos, browse and forge stocks, and read the knowledge base without
re-implementing the engine.

This is the "Option B (backend)" path from ``docs/IOS_APP_STORE.md``: keep the
Python engine on a server, make the app a thin client.

Run it::

    pip install -e ".[server,generate]"
    allstock-server                      # or: uvicorn allstock.server.app:app --reload

Then, e.g.::

    curl localhost:8000/stocks
    curl -F file=@photo.jpg -F stock=portra400 localhost:8000/develop -o out.png

The service is intentionally stateless (no database, no auth). Add your own
auth/rate-limiting/hosting before shipping it to real users.
"""

from __future__ import annotations

import io
import json
from typing import List, Optional

import numpy as np
from PIL import Image

try:
    from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
    from fastapi.responses import JSONResponse, StreamingResponse
except ImportError as exc:  # pragma: no cover - clear message if extra missing
    raise ImportError(
        "The API server needs FastAPI. Install with:  pip install 'allstock[server]'"
    ) from exc

from .. import designer, knowledge, library
from ..engine import DevelopOptions, develop_array
from ..imaging import srgb_to_linear, to_uint8_srgb
from ..stock import FilmStock

app = FastAPI(
    title="AllStock API",
    version="0.1.0",
    summary="Physically-grounded analog film emulation, stock designer and "
            "knowledge base over HTTP.",
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _resolve_stock(stock: Optional[str], stock_json: Optional[str]) -> FilmStock:
    """Resolve a stock from a built-in key or an inline JSON document."""
    if stock_json:
        try:
            return FilmStock.from_dict(json.loads(stock_json))
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(400, f"Invalid stock_json: {exc}")
    if stock:
        try:
            return library.get_stock(stock)
        except KeyError as exc:
            raise HTTPException(404, str(exc))
    raise HTTPException(400, "Provide a 'stock' key or a 'stock_json' document.")


def _read_linear(data: bytes) -> np.ndarray:
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:  # noqa: BLE001 - any decode error is a 400
        raise HTTPException(400, f"Could not read image: {exc}")
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return srgb_to_linear(arr)


def _png_response(linear: np.ndarray) -> StreamingResponse:
    buf = io.BytesIO()
    Image.fromarray(to_uint8_srgb(linear), "RGB").save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


# --------------------------------------------------------------------------
# meta
# --------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "name": "AllStock API",
        "version": "0.1.0",
        "endpoints": ["/stocks", "/stocks/{key}", "/develop", "/generate",
                      "/design/blend", "/design/cross", "/design/mutate",
                      "/learn", "/learn/{slug}", "/learn/search"],
    }


@app.get("/health")
def health():
    return {"status": "ok", "stocks": len(library.list_stocks())}


# --------------------------------------------------------------------------
# stocks
# --------------------------------------------------------------------------
@app.get("/stocks")
def list_stocks():
    out = []
    for key in library.list_stocks():
        s = library.get_stock(key)
        out.append({"key": key, "name": s.name, "maker": s.maker, "iso": s.iso,
                    "process_family": s.process_family, "description": s.description})
    return {"stocks": out}


@app.get("/stocks/{key}")
def get_stock(key: str):
    try:
        s = library.get_stock(key)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    return {"key": key, "summary": s.summary(), "stock": s.to_dict()}


# --------------------------------------------------------------------------
# develop
# --------------------------------------------------------------------------
@app.post("/develop")
def develop(
    file: UploadFile = File(..., description="JPEG/PNG to develop"),
    stock: Optional[str] = Form(None, description="built-in stock key"),
    stock_json: Optional[str] = Form(None, description="inline stock JSON"),
    exposure: float = Form(0.0),
    push: Optional[float] = Form(None),
    seed: int = Form(0),
    grain: bool = Form(True),
    halation: bool = Form(True),
    optics: bool = Form(True),
    max_side: Optional[int] = Form(None),
):
    """Develop an uploaded photo on a film stock and return a PNG."""
    film = _resolve_stock(stock, stock_json)
    linear = _read_linear(file.file.read())
    opts = DevelopOptions(exposure=exposure, push=push, seed=seed,
                          grain=grain, halation=halation, optics=optics,
                          max_side=max_side)
    return _png_response(develop_array(linear, film, opts))


# --------------------------------------------------------------------------
# generate (+ develop)
# --------------------------------------------------------------------------
@app.post("/generate")
def generate(
    prompt: str = Form(...),
    stock: Optional[str] = Form(None),
    stock_json: Optional[str] = Form(None),
    provider: str = Form("null", description="null (offline) by default"),
    width: int = Form(768),
    height: int = Form(768),
    seed: int = Form(0),
):
    """Generate an image for a prompt then develop it on a stock (PNG out).

    Defaults to the offline ``null`` provider so it works with no API keys; pass
    another provider (and set its key in the server's environment) to use it.
    """
    from ..generate import generate_and_develop  # local import: optional dep
    film = _resolve_stock(stock, stock_json)
    try:
        positive, _info = generate_and_develop(
            prompt, film, provider=provider, width=width, height=height, seed=seed)
    except (RuntimeError, KeyError) as exc:
        raise HTTPException(400, str(exc))
    return _png_response(positive)


# --------------------------------------------------------------------------
# design (forge stocks) -> JSON
# --------------------------------------------------------------------------
@app.post("/design/blend")
def design_blend(a: str = Form(...), b: str = Form(...), t: float = Form(0.5),
                 name: Optional[str] = Form(None)):
    try:
        result = designer.blend(library.get_stock(a), library.get_stock(b), t, name=name)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    return JSONResponse(result.to_dict())


@app.post("/design/cross")
def design_cross(base: str = Form(...), grain: Optional[str] = Form(None),
                 halation: Optional[str] = Form(None), curves: Optional[str] = Form(None),
                 optics: Optional[str] = Form(None), name: Optional[str] = Form(None)):
    kw = {}
    try:
        for group, ref in (("grain", grain), ("halation", halation),
                           ("curves", curves), ("optics", optics)):
            if ref:
                kw[group] = library.get_stock(ref)
        result = designer.cross(library.get_stock(base), name=name, **kw)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    return JSONResponse(result.to_dict())


@app.post("/design/mutate")
def design_mutate(stock: str = Form(...), amount: float = Form(0.15),
                  seed: int = Form(0), name: Optional[str] = Form(None)):
    try:
        result = designer.mutate(library.get_stock(stock), amount=amount, seed=seed, name=name)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    return JSONResponse(result.to_dict())


# --------------------------------------------------------------------------
# learn (knowledge base)
# --------------------------------------------------------------------------
@app.get("/learn")
def learn_list():
    return {"topics": [{"slug": s, "title": t} for s, t in knowledge.list_topics()]}


@app.get("/learn/search")
def learn_search(q: str = Query(..., min_length=1)):
    return {"query": q, "hits": knowledge.search(q)}


@app.get("/learn/{slug}")
def learn_topic(slug: str):
    try:
        return {"slug": slug, "markdown": knowledge.get_topic(slug)}
    except KeyError as exc:
        raise HTTPException(404, str(exc))


def run() -> None:  # pragma: no cover - thin uvicorn launcher
    """Console-script entry point: ``allstock-server``."""
    import os
    import uvicorn
    uvicorn.run("allstock.server.app:app",
                host=os.getenv("ALLSTOCK_HOST", "127.0.0.1"),
                port=int(os.getenv("ALLSTOCK_PORT", "8000")),
                reload=bool(os.getenv("ALLSTOCK_RELOAD")))


if __name__ == "__main__":  # pragma: no cover
    run()
