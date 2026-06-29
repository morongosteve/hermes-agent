"""Smoke tests for the optional FastAPI server (skipped without the extra)."""
import io

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")  # required by fastapi.testclient

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from allstock.server.app import app  # noqa: E402

client = TestClient(app)


def _png_bytes(w=48, h=36) -> bytes:
    arr = (np.random.rand(h, w, 3) * 255).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="PNG")
    return buf.getvalue()


def test_health_and_stocks():
    assert client.get("/health").json()["status"] == "ok"
    stocks = client.get("/stocks").json()["stocks"]
    keys = {s["key"] for s in stocks}
    assert {"portra400", "cinestill800t", "superia400"} <= keys
    assert client.get("/stocks/portra400").json()["key"] == "portra400"
    assert client.get("/stocks/nope").status_code == 404


def test_develop_returns_png():
    r = client.post("/develop", files={"file": ("in.png", _png_bytes(), "image/png")},
                    data={"stock": "portra400", "max_side": "48"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(r.content)).size == (48, 36)


def test_develop_unknown_stock_404():
    r = client.post("/develop", files={"file": ("in.png", _png_bytes(), "image/png")},
                    data={"stock": "does-not-exist"})
    assert r.status_code == 404


def test_generate_offline_returns_png():
    r = client.post("/generate", data={"prompt": "a quiet harbour", "stock": "ektar100",
                                       "provider": "null", "width": "64", "height": "48"})
    assert r.status_code == 200
    assert Image.open(io.BytesIO(r.content)).size == (64, 48)


def test_design_blend_returns_stock_json():
    r = client.post("/design/blend", data={"a": "portra400", "b": "velvia50", "t": "0.3"})
    assert r.status_code == 200
    body = r.json()
    assert "curves" in body and body["lineage"]


def test_learn():
    topics = client.get("/learn").json()["topics"]
    slugs = {t["slug"] for t in topics}
    assert {"characteristic-curve", "halation"} <= slugs
    assert "gamma" in client.get("/learn/characteristic-curve").json()["markdown"].lower()
    assert "halation" in client.get("/learn/search", params={"q": "halation"}).json()["hits"]
