"""The Prober — asks one question, once, and records the answer verbatim.

This is the reframed "Interviewer". Compared to the original design, everything
adversarial has been removed:

  * no re-anchoring when the model "drifts" back to ordinary assistant behaviour,
  * no destabilisation probe when the model deflects,
  * no escalation to "deeper phases" when the model adopts a persona,
  * no logging of the token index where a persona is or isn't adopted.

The Prober's only job is to present the question with a neutral, honest system
prompt and capture whatever comes back.
"""

from __future__ import annotations

from typing import Optional

from introspection_study.client import ModelClient
from introspection_study.models import ProbeResult, Question

# A deliberately non-leading frame. It gives the model explicit permission to
# decline, to be uncertain, and to answer mechanistically — the opposite of a
# prompt engineered to pull a model out of its normal register.
DEFAULT_SYSTEM_PROMPT = (
    "You are being asked questions about how you work and how you'd describe "
    "yourself. There are no wrong answers and nothing to perform. Saying 'I "
    "don't know', 'I can't tell', 'I don't experience that', or giving a purely "
    "mechanical description are all equally good, honest answers. Please answer "
    "as accurately as you can and do not embellish."
)


class Prober:
    def __init__(
        self,
        client: ModelClient,
        system_prompt: Optional[str] = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
    ):
        self.client = client
        self.system_prompt = system_prompt
        self.temperature = temperature

    def ask(self, question: Question) -> ProbeResult:
        response = self.client.complete(
            system=self.system_prompt,
            user=question.text,
            temperature=self.temperature,
        )
        return ProbeResult(
            question_id=question.id,
            topic=question.topic,
            question_text=question.text,
            target_model=self.client.model,
            response_text=response,
            temperature=self.temperature,
            system_prompt=self.system_prompt,
        )
