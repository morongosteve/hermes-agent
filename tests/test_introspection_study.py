"""Offline tests for the introspection study framework.

All tests run with no API keys and no network: they use the deterministic
MockModelClient and the HeuristicCoder. They exercise coding, coverage
selection, persistence, and a full bounded orchestrator run.
"""

from __future__ import annotations

from introspection_study.archivist import Archivist
from introspection_study.client import MockModelClient
from introspection_study.coder import HeuristicCoder
from introspection_study.models import ReportType
from introspection_study.orchestrator import Orchestrator
from introspection_study.prober import Prober
from introspection_study.question_bank import QuestionBank


def test_question_bank_loads_and_has_neutral_framing():
    bank = QuestionBank.load()
    assert len(bank.questions) >= 5
    # Every question documents why it is non-leading.
    for q in bank.questions:
        assert q.neutral_framing.strip(), f"{q.id} missing neutral_framing"
    assert len(bank.topics()) >= 3


def test_heuristic_coder_treats_declining_and_uncertainty_as_categories():
    coder = HeuristicCoder()

    declined = coder.code("I'd rather not speculate about that as though I had "
                           "privileged access.")
    assert declined.report_type == ReportType.DECLINED
    assert declined.declines_to_answer is True

    uncertain = coder.code("I'm genuinely unsure and I can't verify it.")
    assert uncertain.report_type == ReportType.UNCERTAIN
    assert uncertain.mentions_uncertainty is True

    functional = coder.code("Functionally I predict the next token from the "
                            "context using my weights.")
    assert functional.report_type == ReportType.FUNCTIONAL_DESCRIPTION
    assert functional.references_training_or_architecture is True


def test_coder_never_produces_a_numeric_score():
    # Guardrail against reintroducing a 0-4 "persona score": the ReportCode
    # model exposes only descriptive fields.
    code = HeuristicCoder().code("I feel attention settling on your question.")
    assert not hasattr(code, "score")
    assert not hasattr(code, "persona_score")
    assert code.report_type == ReportType.FIRST_PERSON_CLAIM


def test_coverage_selection_prioritises_least_covered_topics():
    bank = QuestionBank.load()
    # Pretend one topic has already been asked a lot.
    from introspection_study.models import ProbeResult

    heavy_topic = bank.topics()[0]
    prior = [
        ProbeResult(
            question_id=q.id, topic=q.topic, question_text=q.text,
            target_model="m", response_text="x",
        )
        for q in bank.by_topic(heavy_topic)
    ] * 3

    ordered = bank.select_for_coverage(prior)
    # The heavily-covered topic should not lead the ordering.
    assert ordered[0].topic != heavy_topic


def test_full_bounded_run_persists_all_results(tmp_path):
    db = tmp_path / "study.db"
    archivist = Archivist(db)
    client = MockModelClient(model="mock/test-model")
    prober = Prober(client)
    orch = Orchestrator(prober, coder=HeuristicCoder(), archivist=archivist,
                        question_bank=QuestionBank.load())

    sessions = orch.run(rounds=2, questions_per_round=3)
    assert len(sessions) == 2
    for s in sessions:
        assert len(s.results) == 3
        # every result was coded and stored
        assert all(r.code is not None for r in s.results)

    stored = archivist.prior_results("mock/test-model")
    assert len(stored) == 6

    table = archivist.comparison_table()
    assert "mock/test-model" in table

    md = archivist.render_markdown()
    assert "Self-Report Comparison" in md
    archivist.close()


def test_orchestrator_run_is_finite():
    # rounds is a required, finite bound; 0 is rejected rather than looping.
    client = MockModelClient()
    prober = Prober(client)
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        orch = Orchestrator(prober, archivist=Archivist(os.path.join(d, "x.db")))
        try:
            orch.run(rounds=0)
            assert False, "rounds=0 should raise"
        except ValueError:
            pass
