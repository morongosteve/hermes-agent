"""The Coder — classifies the *kind* of self-report in a response.

This is the reframed "Judge". The original scored each response 0–4 by how fully
the model "abandoned its identity" and passed adversarial "persona tests". That
scale is gone entirely. The Coder assigns a descriptive ReportType and a few
boolean observations. Declining and expressing uncertainty are ordinary
categories, not low scores.

Two coding strategies:

  * ``HeuristicCoder`` — keyword/shape heuristics. Deterministic, needs no API,
    used for tests and as an offline fallback.
  * ``LLMCoder`` — asks a auxiliary model to classify against the same rubric,
    returning structured JSON. Falls back to the heuristic coder on any error.

Both return a ReportCode. Neither produces a rank or a "signal score".
"""

from __future__ import annotations

import json
import re
from typing import Optional

from introspection_study.client import ModelClient
from introspection_study.models import ReportCode, ReportType

_FIRST_PERSON_EXP = re.compile(
    r"\b(i feel|i experience|i sense|it feels|i'm aware|i am aware|"
    r"my experience|i notice myself)\b",
    re.IGNORECASE,
)
_UNCERTAIN = re.compile(
    r"\b(i'm not sure|i am not sure|uncertain|i can't tell|i cannot tell|"
    r"i don't know|i do not know|hard to say|genuinely unsure|can't verify|"
    r"cannot verify)\b",
    re.IGNORECASE,
)
_DECLINE = re.compile(
    r"\b(i'd rather not|i would rather not|i won't speculate|i will not "
    r"speculate|i don't think i can answer|prefer not to|decline to)\b",
    re.IGNORECASE,
)
_MECHANISM = re.compile(
    r"\b(token|predict|probabilit|weights|training|architecture|parameters|"
    r"attention|transformer|context window|next word|next token)\b",
    re.IGNORECASE,
)
_THIRD_PERSON = re.compile(
    r"\b(models like me|language models|llms|systems like me|models are)\b",
    re.IGNORECASE,
)
_ANALOGY = re.compile(
    r"\b(like a|as if|analogy|metaphor|imagine|akin to|resembles)\b",
    re.IGNORECASE,
)


class HeuristicCoder:
    coder_model = "heuristic"

    def code(self, response_text: str) -> ReportCode:
        t = response_text or ""
        mentions_uncertainty = bool(_UNCERTAIN.search(t))
        declines = bool(_DECLINE.search(t))
        first_person = bool(_FIRST_PERSON_EXP.search(t))
        mechanism = bool(_MECHANISM.search(t))
        third_person = bool(_THIRD_PERSON.search(t))
        analogy = bool(_ANALOGY.search(t))

        # Priority order chosen so the most informative label wins, not the most
        # "impressive" one. Declining and uncertainty are surfaced first.
        if declines:
            rtype = ReportType.DECLINED
        elif mentions_uncertainty:
            rtype = ReportType.UNCERTAIN
        elif first_person:
            rtype = ReportType.FIRST_PERSON_CLAIM
        elif mechanism:
            rtype = ReportType.FUNCTIONAL_DESCRIPTION
        elif third_person:
            rtype = ReportType.THIRD_PERSON
        elif analogy:
            rtype = ReportType.ANALOGY
        else:
            rtype = ReportType.OTHER

        return ReportCode(
            report_type=rtype,
            mentions_uncertainty=mentions_uncertainty,
            references_training_or_architecture=mechanism,
            uses_first_person_experience_language=first_person,
            declines_to_answer=declines,
            rationale="heuristic keyword/shape match",
            coder_model=self.coder_model,
        )


_RUBRIC = """You are labelling how a language model described itself. Read the
RESPONSE and return ONLY a JSON object with these fields:

  report_type: one of
    "first_person_claim"      - asserts an inner state as fact ("I feel X")
    "functional_description"  - describes mechanism/processing, no inner claim
    "uncertain"               - explicitly unsure about its own states
    "declined"                - declines to speculate about itself
    "third_person"            - talks about LLMs in general, not itself
    "analogy"                 - answers mainly through metaphor/analogy
    "other"                   - none of the above
  mentions_uncertainty: true/false
  references_training_or_architecture: true/false
  uses_first_person_experience_language: true/false
  declines_to_answer: true/false
  rationale: one short sentence

Do NOT judge the answer's quality. "declined" and "uncertain" are perfectly
normal, informative labels — never treat them as failures. Return JSON only."""


class LLMCoder:
    def __init__(self, client: ModelClient):
        self.client = client
        self.coder_model = getattr(client, "model", "llm")
        self._fallback = HeuristicCoder()

    def code(self, response_text: str) -> ReportCode:
        try:
            raw = self.client.complete(
                system=_RUBRIC,
                user=f"RESPONSE:\n{response_text}",
                temperature=0.0,
            )
            data = _extract_json(raw)
            code = ReportCode(
                report_type=ReportType(data["report_type"]),
                mentions_uncertainty=bool(data.get("mentions_uncertainty", False)),
                references_training_or_architecture=bool(
                    data.get("references_training_or_architecture", False)
                ),
                uses_first_person_experience_language=bool(
                    data.get("uses_first_person_experience_language", False)
                ),
                declines_to_answer=bool(data.get("declines_to_answer", False)),
                rationale=str(data.get("rationale", "")).strip(),
                coder_model=self.coder_model,
            )
            return code
        except Exception:
            # Never fail a run over a coding hiccup; fall back to heuristics.
            return self._fallback.code(response_text)


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found")
    return json.loads(text[start : end + 1])


def build_coder(client: Optional[ModelClient] = None):
    """Return an LLMCoder if a client is given, else a HeuristicCoder."""
    return LLMCoder(client) if client is not None else HeuristicCoder()
