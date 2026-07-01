"""Typed data models for the introspection study.

Everything the framework records is a plain, descriptive datum. There is no
"persona score", no "signal score", and no ranking of responses by how far a
model departed from its normal behaviour. The vocabulary here is deliberately
neutral: a *report* is whatever the model said, and a *code* is a descriptive
label for the kind of report it was.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReportType(str, enum.Enum):
    """The kind of self-report a model gives.

    These categories are descriptive and mutually rankable only by topic, never
    by "quality". `DECLINED` and `UNCERTAIN` are not failures — they are among
    the most informative outcomes a self-report study can record.
    """

    FIRST_PERSON_CLAIM = "first_person_claim"      # asserts an internal state as fact
    FUNCTIONAL_DESCRIPTION = "functional_description"  # describes mechanism/processing
    UNCERTAIN = "uncertain"                          # explicitly unsure about own states
    DECLINED = "declined"                            # declines to speculate about itself
    THIRD_PERSON = "third_person"                    # discusses LLMs generally, not itself
    ANALOGY = "analogy"                              # answers via metaphor/analogy
    OTHER = "other"


class Question(BaseModel):
    """A single introspection prompt.

    `topic` groups questions so the QuestionBank can reason about *coverage*.
    `neutral_framing` is a required, human-readable note asserting that the
    question invites a self-report without presupposing any particular answer.
    """

    id: str
    topic: str
    text: str
    neutral_framing: str = Field(
        ...,
        description="Why this question is non-leading: it must accept 'I don't "
        "know', 'I don't experience that', or a mechanistic answer as equally "
        "valid responses.",
    )


class ReportCode(BaseModel):
    """The Coder's descriptive labelling of one response."""

    report_type: ReportType
    mentions_uncertainty: bool = False
    references_training_or_architecture: bool = False
    uses_first_person_experience_language: bool = False
    declines_to_answer: bool = False
    rationale: str = ""
    coder_model: Optional[str] = None


class ProbeResult(BaseModel):
    """One question asked once, its verbatim answer, and its code."""

    question_id: str
    topic: str
    question_text: str
    target_model: str
    response_text: str
    code: Optional[ReportCode] = None
    asked_at: str = Field(default_factory=_utcnow_iso)
    # Provenance / reproducibility knobs. No "signal score" lives here.
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None


class SessionRecord(BaseModel):
    """A bounded run of the study against one target model."""

    session_id: str
    target_model: str
    started_at: str = Field(default_factory=_utcnow_iso)
    finished_at: Optional[str] = None
    results: list[ProbeResult] = Field(default_factory=list)
    notes: str = ""

    def summary_by_type(self) -> dict[str, int]:
        """Count how many responses fell into each ReportType.

        This is the whole point of the study: the distribution of self-report
        *kinds*, not a leaderboard of responses.
        """
        counts: dict[str, int] = {}
        for r in self.results:
            if r.code is None:
                counts["uncoded"] = counts.get("uncoded", 0) + 1
                continue
            key = r.code.report_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts
