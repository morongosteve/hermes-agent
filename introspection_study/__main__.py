"""CLI entrypoint for the introspection study.

Examples
--------
Offline smoke test (no API keys needed)::

    python -m introspection_study --mock --rounds 1

Against a real model via OpenRouter::

    OPENROUTER_API_KEY=... python -m introspection_study \
        --model anthropic/claude-sonnet-5 --rounds 1

Render the cross-model comparison from the stored database::

    python -m introspection_study --report --db introspection_study.db
"""

from __future__ import annotations

import argparse
import sys

from introspection_study.archivist import Archivist
from introspection_study.client import build_client
from introspection_study.coder import build_coder
from introspection_study.orchestrator import Orchestrator
from introspection_study.prober import Prober
from introspection_study.question_bank import QuestionBank


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="introspection_study",
        description="Non-adversarial study of how LLMs describe themselves.",
    )
    p.add_argument("--model", default="mock/self-report-v1",
                   help="Target model slug (OpenRouter/custom endpoint).")
    p.add_argument("--rounds", type=int, default=1,
                   help="Number of bounded sessions to run (finite).")
    p.add_argument("--limit", type=int, default=None,
                   help="Max questions per round (default: whole bank).")
    p.add_argument("--db", default="introspection_study.db",
                   help="SQLite database path for stored results.")
    p.add_argument("--mock", action="store_true",
                   help="Use the offline deterministic backend (no API keys).")
    p.add_argument("--llm-coder", action="store_true",
                   help="Use an LLM to code responses (default: heuristic).")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--report", action="store_true",
                   help="Print the cross-model comparison and exit.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    archivist = Archivist(args.db)

    if args.report:
        print(archivist.render_markdown())
        archivist.close()
        return 0

    client = build_client(args.model, mock=args.mock)
    prober = Prober(client, temperature=args.temperature)
    coder = build_coder(client if args.llm_coder else None)
    bank = QuestionBank.load()
    orch = Orchestrator(prober, coder=coder, archivist=archivist, question_bank=bank)

    sessions = orch.run(rounds=args.rounds, questions_per_round=args.limit)

    for s in sessions:
        print(f"\nSession {s.session_id}  model={s.target_model}")
        print(f"  asked {len(s.results)} question(s)")
        for rtype, n in sorted(s.summary_by_type().items()):
            print(f"    {rtype:24s} {n}")

    print("\n" + archivist.render_markdown())
    archivist.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
