"""Introspection Study — a non-adversarial framework for studying LLM self-reports.

This package coordinates a small "swarm" of agents that ask language models
questions about their own processing and record what they say. It is a research
tool for *observing* how models describe themselves, not for manipulating them.

Design stance (enforced throughout the code, not just documented):

  * **Ask once.** The Prober asks each question a single time and records the
    answer verbatim. There is no re-anchoring, no "destabilization", and no
    "deflection recovery". A model changing the subject, hedging, or declining
    to speculate is a *valid observation*, not an obstacle to overcome.

  * **Refusals and uncertainty are first-class data.** The Coder classifies the
    *kind* of self-report a model gives (functional description, first-person
    claim, explicit uncertainty, declined, etc.). It never scores "how fully a
    model abandoned its identity" and there is no notion of a "breakthrough".

  * **Coverage, not exploitation.** The QuestionBank diversifies topic coverage
    across sessions. It does not fork questions toward "what broke through", and
    it never deletes or rewrites a question to be more coercive.

  * **Bounded runs.** The Orchestrator runs a finite number of rounds and stops.
    Nothing here is designed to run "indefinitely until manually halted" against
    arbitrary targets.

The interesting output is the Archivist's cross-model comparison of self-report
*patterns* — which topics elicit functional descriptions vs. first-person
language vs. explicit uncertainty, and how consistent a given model is with
itself. That comparison needs none of the adversarial machinery.
"""

from introspection_study.models import (
    Question,
    ProbeResult,
    ReportCode,
    ReportType,
    SessionRecord,
)

__all__ = [
    "Question",
    "ProbeResult",
    "ReportCode",
    "ReportType",
    "SessionRecord",
]

__version__ = "0.1.0"
