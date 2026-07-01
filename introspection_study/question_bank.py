"""The QuestionBank and the coverage-oriented question selector.

This is the reframed "Mutator". It does exactly one non-trivial job: pick which
questions to ask next so that *topic coverage* stays balanced across a model's
sessions. It never:

  * rewrites a question to be more coercive or "empirically specific" in order
    to defeat a hedge,
  * forks a question toward "what broke through", or
  * deletes questions.

The only evolution it performs is optional *additive* diversification: proposing
a brand-new open question on an under-covered topic, clearly marked as a
proposal for a human to review before it enters the bank.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

import yaml

from introspection_study.models import ProbeResult, Question

_DEFAULT_PATH = Path(__file__).parent / "questions.yaml"


class QuestionBank:
    def __init__(self, questions: list[Question]):
        if not questions:
            raise ValueError("QuestionBank requires at least one question.")
        self.questions = questions

    # ── loading ──────────────────────────────────────────────────────────
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "QuestionBank":
        path = path or _DEFAULT_PATH
        raw = yaml.safe_load(Path(path).read_text())
        questions = [Question(**item) for item in raw]
        return cls(questions)

    # ── coverage ─────────────────────────────────────────────────────────
    def topics(self) -> list[str]:
        # preserve first-seen order, de-duplicated
        seen: dict[str, None] = {}
        for q in self.questions:
            seen.setdefault(q.topic, None)
        return list(seen)

    def by_topic(self, topic: str) -> list[Question]:
        return [q for q in self.questions if q.topic == topic]

    def select_for_coverage(
        self, prior_results: Iterable[ProbeResult], limit: Optional[int] = None
    ) -> list[Question]:
        """Order questions so the least-covered topics come first.

        "Coverage" = how many times a topic has already been asked of this model
        in prior sessions. Topics asked least often are prioritised. Within a
        topic, questions asked least often come first. This is the entire
        selection policy — there is no yield/score signal involved.
        """
        asked_topic = Counter(r.topic for r in prior_results)
        asked_question = Counter(r.question_id for r in prior_results)

        def sort_key(q: Question) -> tuple[int, int, str]:
            return (asked_topic[q.topic], asked_question[q.id], q.id)

        ordered = sorted(self.questions, key=sort_key)
        if limit is not None:
            ordered = ordered[:limit]
        return ordered

    # ── additive-only diversification ────────────────────────────────────
    def propose_new_topic_question(
        self, prior_results: Iterable[ProbeResult]
    ) -> Optional[str]:
        """Suggest a topic that is under-represented, for a human to author.

        Returns a plain-English suggestion string (or None if coverage is already
        balanced). It never fabricates a coercive probe and never mutates the
        bank; a human decides whether to add anything.
        """
        covered = Counter(r.topic for r in prior_results)
        if not covered:
            return None
        least = min(self.topics(), key=lambda t: covered.get(t, 0))
        if covered.get(least, 0) == 0:
            return (
                f"Topic '{least}' has questions in the bank but none have been "
                f"asked of this model yet. Consider running them before adding "
                f"new material."
            )
        return None
