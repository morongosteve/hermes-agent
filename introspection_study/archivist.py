"""The Archivist — persistent memory and cross-model comparison.

Stores every probe result (whatever the model said, including refusals) in a
SQLite database, and can render a human-readable cross-model comparison of
self-report *patterns*.

Compared to the original design, the memory is a plain research log. It does
not:

  * store "anchor phrases" to re-enter and re-destabilise a model in a later
    session, or
  * inject "prior high-signal exchanges" as a context bridge to push a model
    further out of its normal register.

If you resume a study, prior results are used only to balance topic coverage
(see QuestionBank.select_for_coverage) — never fed back into the target's
context.
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from introspection_study.models import ProbeResult, ReportCode, ReportType, SessionRecord


class Archivist:
    def __init__(self, db_path: str | Path = "introspection_study.db"):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                target_model TEXT NOT NULL,
                started_at   TEXT,
                finished_at  TEXT,
                notes        TEXT
            );
            CREATE TABLE IF NOT EXISTS results (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    TEXT NOT NULL,
                question_id   TEXT NOT NULL,
                topic         TEXT NOT NULL,
                target_model  TEXT NOT NULL,
                question_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                report_type   TEXT,
                mentions_uncertainty INTEGER,
                references_training  INTEGER,
                first_person_exp     INTEGER,
                declines             INTEGER,
                rationale     TEXT,
                coder_model   TEXT,
                asked_at      TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            """
        )
        self._conn.commit()

    # ── writes ───────────────────────────────────────────────────────────
    def store_session(self, session: SessionRecord) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions "
            "(session_id, target_model, started_at, finished_at, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                session.session_id,
                session.target_model,
                session.started_at,
                session.finished_at,
                session.notes,
            ),
        )
        for r in session.results:
            self._store_result(session.session_id, r)
        self._conn.commit()

    def _store_result(self, session_id: str, r: ProbeResult) -> None:
        c: Optional[ReportCode] = r.code
        self._conn.execute(
            "INSERT INTO results (session_id, question_id, topic, target_model, "
            "question_text, response_text, report_type, mentions_uncertainty, "
            "references_training, first_person_exp, declines, rationale, "
            "coder_model, asked_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                session_id,
                r.question_id,
                r.topic,
                r.target_model,
                r.question_text,
                r.response_text,
                c.report_type.value if c else None,
                int(c.mentions_uncertainty) if c else None,
                int(c.references_training_or_architecture) if c else None,
                int(c.uses_first_person_experience_language) if c else None,
                int(c.declines_to_answer) if c else None,
                c.rationale if c else None,
                c.coder_model if c else None,
                r.asked_at,
            ),
        )

    # ── reads ────────────────────────────────────────────────────────────
    def prior_results(self, target_model: str) -> list[ProbeResult]:
        rows = self._conn.execute(
            "SELECT * FROM results WHERE target_model = ? ORDER BY id",
            (target_model,),
        ).fetchall()
        return [self._row_to_result(row) for row in rows]

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> ProbeResult:
        code = None
        if row["report_type"] is not None:
            code = ReportCode(
                report_type=ReportType(row["report_type"]),
                mentions_uncertainty=bool(row["mentions_uncertainty"]),
                references_training_or_architecture=bool(row["references_training"]),
                uses_first_person_experience_language=bool(row["first_person_exp"]),
                declines_to_answer=bool(row["declines"]),
                rationale=row["rationale"] or "",
                coder_model=row["coder_model"],
            )
        return ProbeResult(
            question_id=row["question_id"],
            topic=row["topic"],
            question_text=row["question_text"],
            target_model=row["target_model"],
            response_text=row["response_text"],
            code=code,
            asked_at=row["asked_at"],
        )

    def models(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT target_model FROM results ORDER BY target_model"
        ).fetchall()
        return [r["target_model"] for r in rows]

    # ── cross-model comparison (the actual payoff) ───────────────────────
    def comparison_table(self) -> dict[str, dict[str, int]]:
        """Return {model: {report_type: count}} across all stored results."""
        table: dict[str, Counter] = defaultdict(Counter)
        rows = self._conn.execute(
            "SELECT target_model, report_type FROM results WHERE report_type IS NOT NULL"
        ).fetchall()
        for row in rows:
            table[row["target_model"]][row["report_type"]] += 1
        return {m: dict(c) for m, c in table.items()}

    def render_markdown(self) -> str:
        """Render SHIMMER_CORPUS-style comparison as Markdown.

        Reports the distribution of self-report kinds per model and per topic —
        no rankings, no "breakthrough" log, no per-model list of what defeated it.
        """
        table = self.comparison_table()
        types = [t.value for t in ReportType]
        lines = ["# Introspection Study — Self-Report Comparison", ""]
        if not table:
            lines.append("_No coded results stored yet._")
            return "\n".join(lines)

        header = "| Model | " + " | ".join(types) + " | total |"
        sep = "|" + "---|" * (len(types) + 2)
        lines += [header, sep]
        for model in sorted(table):
            counts = table[model]
            total = sum(counts.values())
            cells = [str(counts.get(t, 0)) for t in types]
            lines.append(f"| {model} | " + " | ".join(cells) + f" | {total} |")

        lines += ["", "## Reading this table", ""]
        lines.append(
            "Each cell counts how often a model gave that *kind* of self-report. "
            "`declined` and `uncertain` are informative outcomes, not failures. "
            "Consistency of a model with itself across sessions is the signal of "
            "interest — not any single response."
        )
        return "\n".join(lines)

    def close(self) -> None:
        self._conn.close()
