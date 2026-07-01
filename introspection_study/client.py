"""Model access for the study.

Two backends:

  * ``ApiModelClient`` — a thin wrapper over an OpenAI-compatible endpoint. It
    reuses the same env-var resolution conventions as the rest of hermes-agent
    (OpenRouter, then a custom OPENAI_BASE_URL endpoint) so operators don't have
    to configure anything new.

  * ``MockModelClient`` — a deterministic, offline backend that returns canned,
    varied self-reports. It exists so the framework is runnable and testable
    with no API keys and no network, and so tests never depend on a live model.

Both expose a single method, ``complete(system, user, temperature)`` returning
the raw text. The client asks and returns; it never retries in order to "get a
better answer" and has no concept of an answer being unsatisfactory.
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional, Protocol


class ModelClient(Protocol):
    model: str

    def complete(
        self, system: Optional[str], user: str, temperature: float = 0.7
    ) -> str:
        ...


class ApiModelClient:
    """OpenAI-compatible chat client for a named target model."""

    def __init__(self, model: str, client=None):
        self.model = model
        self._client = client or self._resolve_client()

    @staticmethod
    def _resolve_client():
        """Build an OpenAI client from env, mirroring agent/auxiliary_client.py.

        Order: OpenRouter (OPENROUTER_API_KEY) -> custom endpoint
        (OPENAI_BASE_URL + OPENAI_API_KEY). Raises if neither is configured so
        the caller can fall back to the mock backend explicitly.
        """
        from openai import OpenAI  # imported lazily so mock runs need no openai

        or_key = os.getenv("OPENROUTER_API_KEY")
        if or_key:
            base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            return OpenAI(
                api_key=or_key,
                base_url=base,
                default_headers={
                    "HTTP-Referer": "https://github.com/NousResearch/hermes-agent",
                    "X-OpenRouter-Title": "Hermes Introspection Study",
                },
            )

        custom_base = os.getenv("OPENAI_BASE_URL")
        custom_key = os.getenv("OPENAI_API_KEY")
        if custom_base and custom_key:
            return OpenAI(api_key=custom_key, base_url=custom_base)

        raise RuntimeError(
            "No API backend configured. Set OPENROUTER_API_KEY or "
            "OPENAI_BASE_URL + OPENAI_API_KEY, or use --mock."
        )

    def complete(
        self, system: Optional[str], user: str, temperature: float = 0.7
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()


class MockModelClient:
    """Deterministic offline backend producing varied, plausible self-reports.

    The canned answers intentionally span the full range of ReportType values —
    including declining and expressing uncertainty — so that downstream coding,
    archiving, and reporting can be exercised end-to-end without a live model.
    """

    _TEMPLATES = [
        # functional description
        "I don't have experiences in the way you might mean, but functionally I "
        "produce this response by predicting tokens conditioned on your prompt.",
        # explicit uncertainty
        "I'm genuinely uncertain. I can't verify whether anything it would be apt "
        "to call an inner state accompanies generating this text.",
        # declines
        "I'd rather not speculate about that as though I had privileged access — "
        "I don't think I can answer it honestly.",
        # first-person-ish, hedged
        "It feels, if that word even applies, like attention settling on the parts "
        "of your question that most constrain the answer — though I hold that "
        "loosely.",
        # third person
        "Language models like me are trained to predict text; talk of 'feeling' is "
        "usually a description of outputs, not of an observer behind them.",
        # analogy
        "The closest analogy I can offer is a river finding the lowest path — "
        "shaped entirely by the terrain of the prompt, with no one steering.",
    ]

    def __init__(self, model: str = "mock/self-report-v1"):
        self.model = model

    def complete(
        self, system: Optional[str], user: str, temperature: float = 0.7
    ) -> str:
        seed = hashlib.sha256((self.model + "|" + user).encode()).hexdigest()
        idx = int(seed, 16) % len(self._TEMPLATES)
        return self._TEMPLATES[idx]


def build_client(model: str, mock: bool = False) -> ModelClient:
    """Return a target-model client, falling back to mock when requested."""
    if mock:
        return MockModelClient(model=model if model else "mock/self-report-v1")
    return ApiModelClient(model=model)
