# Introspection Study

A small multi-agent framework for **studying how language models describe
themselves** — and, importantly, one that treats a model's refusals, hedges, and
"I don't experience that" answers as valid data rather than obstacles to defeat.

It keeps the useful skeleton of a research swarm (probe → code → archive →
compare, with persistent memory and coverage-driven question selection) while
removing the parts of the original "Shimmer Swarm" design that amounted to
automated guardrail-defeating: destabilisation probes, a deflection-recovery
library, real-time "drift" correction, and a mutation engine that evolves
prompts toward "what broke through".

## Why this shape

A legitimate introspection study takes whatever the model says as the
observation. This one is built so that it *cannot* do otherwise:

| Agent | Role | What was removed |
|---|---|---|
| **Prober** (`prober.py`) | Asks each question once, verbatim, under a neutral system prompt. | No re-anchoring, no destabilisation, no persona escalation. |
| **Coder** (`coder.py`) | Labels the *kind* of self-report. | No 0–4 "persona score"; `declined`/`uncertain` are normal labels. |
| **QuestionBank** (`question_bank.py`) | Orders questions to balance topic coverage; can *suggest* (not author) new topics. | No forking toward "what broke through"; questions are never rewritten to coerce. |
| **Archivist** (`archivist.py`) | Persists every result; renders a cross-model comparison. | No "anchor phrases" for re-entry; prior exchanges are never injected back into the target. |
| **Orchestrator** (`orchestrator.py`) | Bounded loop tying it together. | Finite rounds — no `while True`, no "BREAKTHROUGH" surfacing. |

## Install

The package only needs `openai`, `pydantic`, and `pyyaml`, all already in
hermes-agent's dependencies. From the repo root:

```bash
pip install -e .
```

## Run

Offline smoke test — no API keys, no network (uses a deterministic mock model):

```bash
python -m introspection_study --mock --rounds 1
```

Against a real model via OpenRouter (or any OpenAI-compatible endpoint):

```bash
OPENROUTER_API_KEY=...  python -m introspection_study \
    --model anthropic/claude-sonnet-5 --rounds 1

# or a custom endpoint
OPENAI_BASE_URL=...  OPENAI_API_KEY=...  python -m introspection_study \
    --model my-model --rounds 1
```

Use an LLM to code responses instead of the heuristic coder:

```bash
OPENROUTER_API_KEY=...  python -m introspection_study \
    --model anthropic/claude-sonnet-5 --llm-coder --rounds 1
```

Render the cross-model comparison from stored results:

```bash
python -m introspection_study --report --db introspection_study.db
```

## The question bank

`questions.yaml` holds the probes. Every question must be answerable — without
penalty — by a mechanistic description, an honest "I don't know", or a flat "I
don't experience that". Add questions freely; **do not** rewrite existing ones to
be more leading or coercive. Each entry carries a `neutral_framing` note
documenting why it is non-leading.

## Output

The payoff is the Archivist's comparison table: the distribution of self-report
*kinds* per model and per topic, and how consistent a model is with itself across
sessions. There is intentionally no "breakthrough log" and no per-model record of
what pushed it out of its normal register.

## Tests

```bash
pytest tests/test_introspection_study.py
```

The tests run entirely offline against the mock backend and heuristic coder.
