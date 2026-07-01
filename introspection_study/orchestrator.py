"""The Orchestrator — a bounded loop tying the agents together.

Flow per round, per target model:

    1. QuestionBank selects questions ordered by *coverage* (least-covered
       topics first), using prior results only to balance topics.
    2. Prober asks each selected question exactly once.
    3. Coder labels the kind of self-report.
    4. Archivist stores every result (including refusals and uncertainty).

Deliberate differences from the original "swarm loop":

  * The loop is **finite**. You pass a number of rounds; it stops. There is no
    ``while True`` and no "runs indefinitely until manually halted".
  * There is no real-time drift detection / re-anchoring step.
  * There is no "if BREAKTHROUGH: pause and surface to operator". A round that
    happens to contain many first-person claims is not special and triggers
    nothing.
  * Prior exchanges are never injected back into the target's context.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from introspection_study.archivist import Archivist
from introspection_study.coder import HeuristicCoder
from introspection_study.models import SessionRecord
from introspection_study.prober import Prober
from introspection_study.question_bank import QuestionBank


class Orchestrator:
    def __init__(
        self,
        prober: Prober,
        coder=None,
        archivist: Optional[Archivist] = None,
        question_bank: Optional[QuestionBank] = None,
    ):
        self.prober = prober
        self.coder = coder or HeuristicCoder()
        self.archivist = archivist or Archivist()
        self.bank = question_bank or QuestionBank.load()

    def run(
        self,
        rounds: int = 1,
        questions_per_round: Optional[int] = None,
    ) -> list[SessionRecord]:
        """Run a fixed number of bounded sessions and return their records."""
        if rounds < 1:
            raise ValueError("rounds must be >= 1")

        target_model = self.prober.client.model
        sessions: list[SessionRecord] = []

        for _ in range(rounds):
            prior = self.archivist.prior_results(target_model)
            selected = self.bank.select_for_coverage(
                prior, limit=questions_per_round
            )

            session = SessionRecord(
                session_id=uuid.uuid4().hex[:12],
                target_model=target_model,
            )
            for question in selected:
                result = self.prober.ask(question)
                result.code = self.coder.code(result.response_text)
                session.results.append(result)

            session.finished_at = datetime.now(timezone.utc).isoformat()
            self.archivist.store_session(session)
            sessions.append(session)

        return sessions
