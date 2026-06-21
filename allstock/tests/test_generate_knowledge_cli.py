import numpy as np

from allstock import knowledge, library
from allstock.cli import main
from allstock.generate import build_analog_prompt, generate_and_develop, get_provider


# ---- generation (offline) ------------------------------------------------
def test_null_provider_generate_and_develop():
    stock = library.get_stock("cinestill800t")
    positive, info = generate_and_develop(
        "a neon street at night", stock, provider="null",
        width=96, height=64, seed=2,
    )
    assert positive.shape == (64, 96, 3)
    assert np.isfinite(positive).all()
    assert 0.0 <= positive.min() and positive.max() <= 1.0 + 1e-5
    assert info.provider == "null"


def test_build_analog_prompt_mentions_stock():
    p = build_analog_prompt("a portrait", library.get_stock("portra400"))
    assert "Portra" in p
    assert "analog film photograph" in p


def test_provider_registry_has_zai_default():
    prov = get_provider("zai")
    assert prov.name == "zai"
    # default model targets Z.ai CogView family
    assert "cogview" in prov.model.lower()


def test_unknown_provider_raises():
    import pytest
    with pytest.raises(KeyError):
        get_provider("does-not-exist")


# ---- knowledge base ------------------------------------------------------
def test_knowledge_topics_present():
    topics = dict(knowledge.list_topics())
    assert "characteristic-curve" in topics
    assert "halation" in topics
    assert "emulsion" in topics
    body = knowledge.get_topic("characteristic-curve")
    assert "gamma" in body.lower()


def test_knowledge_search():
    hits = knowledge.search("halation")
    assert "halation" in hits


# ---- CLI smoke tests -----------------------------------------------------
def test_cli_stocks_and_learn():
    assert main(["stocks"]) == 0
    assert main(["stocks", "--show", "portra400"]) == 0
    assert main(["learn"]) == 0
    assert main(["learn", "grain"]) == 0
    assert main(["learn", "--search", "shoulder"]) == 0
    assert main(["--version"]) == 0


def test_cli_develop_roundtrip(tmp_path):
    from PIL import Image
    src = tmp_path / "in.png"
    Image.fromarray((np.random.rand(40, 50, 3) * 255).astype("uint8"), "RGB").save(src)
    out = tmp_path / "out.jpg"
    rc = main(["develop", str(src), "-o", str(out), "--stock", "portra400", "--max-side", "40"])
    assert rc == 0 and out.is_file()


def test_cli_design_blend_saves(tmp_path):
    out = tmp_path / "blend.json"
    rc = main(["design", "blend", "portra400", "velvia50", "-t", "0.3", "-o", str(out)])
    assert rc == 0 and out.is_file()


def test_cli_generate_offline(tmp_path):
    out = tmp_path / "g.png"
    rc = main(["generate", "a quiet harbour", "--stock", "ektar100",
               "--provider", "null", "--size", "64x48", "-o", str(out)])
    assert rc == 0 and out.is_file()
