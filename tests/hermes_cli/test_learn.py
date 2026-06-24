"""Tests for the /learn command (hermes_cli.learn)."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli import learn as L


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def source_tree(tmp_path: Path) -> Path:
    """A small source directory with mixed content + noise to be ignored."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "guide.md").write_text(
        "# Payments Guide\n"
        "This guide explains how to issue refunds.\n\n"
        "## Refund a charge\n"
        "Call the refund endpoint.\n\n"
        "## Verify the refund\n"
        "Check the dashboard.\n\n"
        "## Common Pitfalls\n"
        "Do not double-refund.\n"
    )
    (src / "config.json").write_text(json.dumps({"api": "v1", "currency": "usd"}))
    (src / "helper.py").write_text("def refund(charge_id):\n    return True\n")
    # Noise that must be ignored.
    noise = src / "node_modules" / "pkg"
    noise.mkdir(parents=True)
    (noise / "index.js").write_text("module.exports = 1;")
    (src / "big.txt").write_text("x" * (L.MAX_FILE_BYTES + 10))
    (src / "image.png").write_bytes(b"\x89PNG\r\n")
    return src


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

class TestScanSources:
    def test_collects_supported_files(self, source_tree):
        docs = L.scan_sources([source_tree])
        rels = {d.rel for d in docs}
        assert "guide.md" in rels
        assert "config.json" in rels
        assert "helper.py" in rels

    def test_ignores_node_modules(self, source_tree):
        docs = L.scan_sources([source_tree])
        assert not any("node_modules" in d.rel for d in docs)

    def test_skips_oversized_and_binary(self, source_tree):
        docs = L.scan_sources([source_tree])
        rels = {d.rel for d in docs}
        assert "big.txt" not in rels   # exceeds size cap
        assert "image.png" not in rels  # unsupported extension

    def test_single_file_path(self, source_tree):
        docs = L.scan_sources([source_tree / "guide.md"])
        assert len(docs) == 1
        assert docs[0].kind == "markdown"

    def test_missing_path_is_safe(self, tmp_path):
        assert L.scan_sources([tmp_path / "nope"]) == []


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

class TestBuildCorpus:
    def test_truncates_to_budget(self, source_tree):
        docs = L.scan_sources([source_tree])
        corpus = L.build_corpus(docs, max_chars=20)
        assert corpus.truncated is True
        assert corpus.total_chars <= 20

    def test_prompt_text_has_provenance(self, source_tree):
        corpus = L.build_corpus(L.scan_sources([source_tree]))
        text = corpus.as_prompt_text()
        assert 'path="guide.md"' in text


# ---------------------------------------------------------------------------
# Distillation
# ---------------------------------------------------------------------------

class TestDistill:
    def test_heuristic_fallback_no_model(self, source_tree):
        corpus = L.build_corpus(L.scan_sources([source_tree]))
        skill = L.distill(corpus)
        assert skill.name  # produced something
        assert skill.procedures  # harvested headings
        # Pitfall / verification headings routed to the right buckets.
        assert any("pitfall" in p.lower() for p in skill.pitfalls)
        assert any("verify" in v.lower() for v in skill.verification)

    def test_model_caller_used_when_provided(self, source_tree):
        corpus = L.build_corpus(L.scan_sources([source_tree]))
        payload = {
            "name": "Stripe Refunds",
            "description": "Issue refunds via the API.",
            "category": "payments",
            "tags": ["stripe", "payments"],
            "triggers": ["When a customer asks for a refund."],
            "procedures": ["Find the charge id.", "Call refund."],
            "pitfalls": ["Avoid double refunds."],
            "verification": ["Confirm status=refunded."],
        }
        calls = []

        def fake_caller(messages):
            calls.append(messages)
            return "```json\n" + json.dumps(payload) + "\n```"

        skill = L.distill(corpus, model_caller=fake_caller)
        assert calls, "model_caller should have been invoked"
        assert skill.name == "stripe-refunds"  # slugified
        assert skill.procedures == ["Find the charge id.", "Call refund."]
        assert skill.tags == ["stripe", "payments"]

    def test_falls_back_when_model_returns_garbage(self, source_tree):
        corpus = L.build_corpus(L.scan_sources([source_tree]))
        skill = L.distill(corpus, model_caller=lambda m: "not json at all")
        assert skill.name  # heuristic still produced a skill

    def test_category_override(self, source_tree):
        corpus = L.build_corpus(L.scan_sources([source_tree]))
        skill = L.distill(corpus, category="payments")
        assert skill.category == "payments"


class TestParseJson:
    def test_strips_code_fence(self):
        assert L._parse_distillation_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_extracts_embedded_object(self):
        assert L._parse_distillation_json('blah {"a": 2} trailing') == {"a": 2}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

class TestRender:
    def test_frontmatter_and_sections(self):
        skill = L.DistilledSkill(
            name="demo",
            description="A demo skill.",
            tags=["a", "b"],
            triggers=["When demoing."],
            procedures=["Step one."],
            pitfalls=["Watch out."],
            verification=["It works."],
        )
        md = L.render_skill_md(skill, source_summary="2 files")
        assert md.startswith("---\n")
        # Round-trips as valid YAML frontmatter.
        fm_text = md.split("---", 2)[1]
        fm = __import__("yaml").safe_load(fm_text)
        assert fm["name"] == "demo"
        assert fm["metadata"]["hermes"]["tags"] == ["a", "b"]
        for section in ("When to Use", "Procedure", "Pitfalls", "Verification"):
            assert section in md


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------

class TestWriteSkill:
    def test_writes_skill_and_references(self, tmp_path):
        skill = L.DistilledSkill(
            name="demo", description="d", category="cat",
            references=[L.Reference(source="a.md", filename="a.md", excerpt="hello")],
        )
        md = L.render_skill_md(skill)
        dest = L.write_skill(skill, md, skills_dir=tmp_path)
        assert (dest / "SKILL.md").is_file()
        assert (dest / "references" / "a.md").read_text() == "hello"
        assert dest == tmp_path / "cat" / "demo"

    def test_refuses_overwrite_without_force(self, tmp_path):
        skill = L.DistilledSkill(name="demo", description="d")
        md = L.render_skill_md(skill)
        L.write_skill(skill, md, skills_dir=tmp_path)
        with pytest.raises(FileExistsError):
            L.write_skill(skill, md, skills_dir=tmp_path)

    def test_force_overwrites_and_no_leftover_staging(self, tmp_path):
        skill = L.DistilledSkill(name="demo", description="first")
        L.write_skill(skill, L.render_skill_md(skill), skills_dir=tmp_path)
        skill2 = L.DistilledSkill(name="demo", description="second")
        dest = L.write_skill(skill2, L.render_skill_md(skill2), skills_dir=tmp_path, force=True)
        assert "second" in (dest / "SKILL.md").read_text()
        # No staging or backup dirs left behind.
        leftovers = [p.name for p in tmp_path.iterdir()]
        assert leftovers == ["demo"]

    def test_rollback_restores_original_on_failure(self, tmp_path, monkeypatch):
        skill = L.DistilledSkill(name="demo", description="original")
        L.write_skill(skill, L.render_skill_md(skill), skills_dir=tmp_path)

        # Force the final rename to blow up, after the original is displaced.
        real_rename = os.rename
        state = {"calls": 0}

        def flaky_rename(a, b):
            state["calls"] += 1
            # First rename displaces original -> backup; let it through.
            # Second rename moves staging -> dest; make it fail.
            if state["calls"] == 2:
                raise OSError("boom")
            return real_rename(a, b)

        monkeypatch.setattr(os, "rename", flaky_rename)
        skill2 = L.DistilledSkill(name="demo", description="new")
        with pytest.raises(OSError):
            L.write_skill(skill2, L.render_skill_md(skill2), skills_dir=tmp_path, force=True)

        monkeypatch.setattr(os, "rename", real_rename)
        # Original content survived the failed write.
        assert "original" in (tmp_path / "demo" / "SKILL.md").read_text()


# ---------------------------------------------------------------------------
# Orchestrator + arg parsing
# ---------------------------------------------------------------------------

class TestDoLearn:
    def test_end_to_end_offline(self, source_tree, tmp_path):
        out = tmp_path / "skills"
        dest = L.do_learn(
            str(source_tree), name="payments-helper", category="payments",
            use_model=False, skills_dir=out,
        )
        assert (dest / "SKILL.md").is_file()
        assert (dest / "references").is_dir()
        assert dest == out / "payments" / "payments-helper"

    def test_empty_path_raises(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ValueError):
            L.do_learn(str(empty), use_model=False, skills_dir=tmp_path / "skills")

    def test_logs_written(self, source_tree, tmp_path):
        with patch.object(L, "LOG_FILE", tmp_path / "logs" / "learn.log"):
            L.do_learn(str(source_tree), name="x", use_model=False,
                       skills_dir=tmp_path / "skills")
            assert (tmp_path / "logs" / "learn.log").read_text().strip()


class TestParseArgs:
    def test_flags_and_paths(self):
        opts = L._parse_learn_args(
            ["./a", "./b", "--name", "foo", "--category", "bar", "--force", "--offline"]
        )
        assert opts["path"] == "./a ./b"
        assert opts["name"] == "foo"
        assert opts["category"] == "bar"
        assert opts["force"] is True
        assert opts["use_model"] is False

    def test_defaults(self):
        opts = L._parse_learn_args(["./docs"])
        assert opts["path"] == "./docs"
        assert opts["use_model"] is True
        assert opts["force"] is False
