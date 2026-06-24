#!/usr/bin/env python3
"""
/learn — Distill a source directory into a standardized SKILL.md.

Powers both:
  - `hermes learn <path> [--name ...] [--category ...]` (CLI argparse entry point)
  - `/learn <path> [...]` (slash command in the interactive chat)

The pipeline mirrors how the rest of the Skills Hub is organised: all logic
lives in shared ``do_*`` / pure functions, and the CLI entry point and slash
handler are thin wrappers that parse args and delegate.

Pipeline (the "distillation algorithm"):

    scan_sources()  ->  build_corpus()  ->  distill()  ->  render_skill_md()
                                                      \\->  write_skill()  (atomic)

``scan_sources`` walks the input path(s), applies the allow-list / ignore
rules, and extracts plain text from each supported file. ``build_corpus``
assembles those documents into a single provenance-tagged corpus. ``distill``
turns the corpus into a structured :class:`DistilledSkill` — either by asking a
model (the same OpenAI-compatible client the agent uses) to synthesise the
SKILL.md sections, or, when no model is available, via a deterministic
heuristic so the command still works (and is testable) offline. Finally the
skill is rendered to Markdown and written atomically under
``~/.hermes/skills/<category>/<name>/``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Sequence

import yaml

# ---------------------------------------------------------------------------
# Configuration / constants
# ---------------------------------------------------------------------------

HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
SKILLS_DIR = HERMES_HOME / "skills"
LOG_FILE = HERMES_HOME / "logs" / "learn.log"

# Allow-list of source extensions we know how to extract text from.
TEXT_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".rst",
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg",
    ".sh", ".bash", ".go", ".rs", ".java", ".rb", ".c", ".h", ".cpp",
}
# Extensions handled by a dedicated (optional) extractor.
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | PDF_EXTENSIONS

# Directories we never descend into.
IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".idea", ".tox",
    "site-packages", ".next", "target",
}

# Skip files larger than this (binary blobs / generated lock files etc.).
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB

# Bound how much raw text we feed the distiller (keeps prompts within limits).
MAX_CORPUS_CHARS = 120_000
# Max length of an individual excerpt stored under references/.
MAX_EXCERPT_CHARS = 4_000


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SourceDoc:
    """A single extracted source file."""

    path: Path          # absolute path on disk
    rel: str            # path relative to the scan root (for provenance)
    kind: str           # "markdown" | "code" | "data" | "pdf" | "text"
    text: str           # extracted plain text


@dataclass
class Corpus:
    """The assembled, provenance-tagged body of source material."""

    docs: List[SourceDoc] = field(default_factory=list)
    truncated: bool = False

    @property
    def total_chars(self) -> int:
        return sum(len(d.text) for d in self.docs)

    def as_prompt_text(self) -> str:
        """Flatten the corpus into a single delimited string for the model."""
        blocks = []
        for d in self.docs:
            blocks.append(f"<source path=\"{d.rel}\" kind=\"{d.kind}\">\n{d.text}\n</source>")
        return "\n\n".join(blocks)


@dataclass
class Reference:
    """A cited excerpt written to the skill's references/ subfolder."""

    source: str         # original relative path
    filename: str       # filename used under references/
    excerpt: str


@dataclass
class DistilledSkill:
    """Structured representation of a SKILL.md before rendering."""

    name: str
    description: str
    category: str = ""
    tags: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)       # when to use
    procedures: List[str] = field(default_factory=list)     # step-by-step
    pitfalls: List[str] = field(default_factory=list)       # failure modes
    verification: List[str] = field(default_factory=list)   # how to prove success
    references: List[Reference] = field(default_factory=list)
    version: str = "0.1.0"
    author: str = "hermes-learn"


# ---------------------------------------------------------------------------
# 1. Scanning + extraction
# ---------------------------------------------------------------------------

def _classify(ext: str) -> str:
    if ext in {".md", ".markdown", ".rst"}:
        return "markdown"
    if ext in {".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg"}:
        return "data"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in {".txt"}:
        return "text"
    return "code"


def _extract_pdf(path: Path) -> Optional[str]:
    """Extract text from a PDF if a parser is installed; else return None."""
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception:
            return None
    try:
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return None


def _extract_text(path: Path) -> Optional[str]:
    """Read a file and return its text, or None if it can't be extracted."""
    ext = path.suffix.lower()
    if ext in PDF_EXTENSIONS:
        return _extract_pdf(path)
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return None


def scan_sources(
    paths: Sequence[Path],
    *,
    max_file_bytes: int = MAX_FILE_BYTES,
) -> List[SourceDoc]:
    """
    Recursively scan ``paths`` and return extracted :class:`SourceDoc` objects.

    Applies the extension allow-list, the :data:`IGNORE_DIRS` deny-list, and the
    ``max_file_bytes`` size cap. A single file path is allowed as well as a
    directory.
    """
    docs: List[SourceDoc] = []
    seen: set = set()

    for root in paths:
        root = root.expanduser()
        if not root.exists():
            continue

        if root.is_file():
            candidates = [root]
            base = root.parent
        else:
            candidates = []
            base = root
            for dirpath, dirnames, filenames in os.walk(root):
                # Prune ignored directories in-place so os.walk skips them.
                dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
                for fn in filenames:
                    candidates.append(Path(dirpath) / fn)

        for fp in candidates:
            if fp in seen:
                continue
            seen.add(fp)
            ext = fp.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            try:
                if fp.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            text = _extract_text(fp)
            if not text or not text.strip():
                continue
            try:
                rel = str(fp.relative_to(base))
            except ValueError:
                rel = fp.name
            docs.append(SourceDoc(path=fp, rel=rel, kind=_classify(ext), text=text))

    # Deterministic ordering: docs first by kind priority then path.
    kind_priority = {"markdown": 0, "text": 1, "data": 2, "pdf": 3, "code": 4}
    docs.sort(key=lambda d: (kind_priority.get(d.kind, 9), d.rel))
    return docs


# ---------------------------------------------------------------------------
# 2. Corpus assembly
# ---------------------------------------------------------------------------

def build_corpus(docs: Sequence[SourceDoc], *, max_chars: int = MAX_CORPUS_CHARS) -> Corpus:
    """
    Assemble scanned docs into a bounded :class:`Corpus`.

    Documents are added in priority order until ``max_chars`` is reached; the
    final document is trimmed rather than dropped so partial context survives.
    """
    corpus = Corpus()
    budget = max_chars
    for d in docs:
        if budget <= 0:
            corpus.truncated = True
            break
        if len(d.text) <= budget:
            corpus.docs.append(d)
            budget -= len(d.text)
        else:
            trimmed = d.text[:budget]
            corpus.docs.append(SourceDoc(path=d.path, rel=d.rel, kind=d.kind, text=trimmed))
            corpus.truncated = True
            budget = 0
    return corpus


# ---------------------------------------------------------------------------
# 3. Distillation
# ---------------------------------------------------------------------------

# The model is asked to return strict JSON matching this contract.
_DISTILL_SYSTEM_PROMPT = """\
You are a skill distillation engine. You read source material (documentation,
code, configs) and distil it into ONE concise, reusable agent skill.

Return ONLY a JSON object (no prose, no code fences) with these keys:
  - "name": short kebab-case skill id (e.g. "stripe-refunds")
  - "description": one sentence on what the skill does and when to use it
  - "category": one of the broad skill categories (e.g. "productivity",
    "github", "media", "data") — your best guess
  - "tags": array of 3-8 short topic tags
  - "triggers": array of bullet strings — conditions for WHEN to use this skill
  - "procedures": array of ordered, actionable step strings (the core logic)
  - "pitfalls": array of edge cases / failure modes to avoid
  - "verification": array of concrete steps to prove the skill succeeded

Be specific and actionable. Prefer commands, exact field names, and concrete
values drawn from the sources over generic advice. Keep each bullet to one idea.
"""


def build_distillation_messages(corpus: Corpus, *, hint_name: str = "") -> List[dict]:
    """Build the chat messages for the model-driven distillation step."""
    user = []
    if hint_name:
        user.append(f"Suggested skill name: {hint_name}")
    if corpus.truncated:
        user.append("(Note: source material was truncated to fit; distil from what is present.)")
    user.append("Source material follows:\n")
    user.append(corpus.as_prompt_text())
    return [
        {"role": "system", "content": _DISTILL_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user)},
    ]


def _coerce_str_list(value) -> List[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _parse_distillation_json(raw: str) -> dict:
    """Parse the model's JSON reply, tolerating code fences / surrounding text."""
    raw = raw.strip()
    # Strip a leading ```json / ``` fence if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to the first {...} block.
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "learned-skill"


def _heuristic_distill(corpus: Corpus, *, hint_name: str = "") -> DistilledSkill:
    """
    Deterministic, model-free distillation used as a fallback.

    Pulls a name/description from the most prominent markdown source, harvests
    headings as procedures, and surfaces obvious pitfall/verification cues. This
    keeps ``/learn`` functional (and unit-testable) without network access.
    """
    title = hint_name
    description = ""
    procedures: List[str] = []
    pitfalls: List[str] = []
    verification: List[str] = []
    tags: List[str] = []

    for d in corpus.docs:
        text = d.text
        # Skip a leading YAML frontmatter block so we don't mistake its fields
        # for the skill's own heading/description.
        if d.kind == "markdown" and text.startswith("---"):
            fm_end = re.search(r"\n---\s*\n", text[3:])
            if fm_end:
                text = text[fm_end.end() + 3:]
        lines = text.splitlines()
        for line in lines:
            s = line.strip()
            if not title and s.startswith("# "):
                title = s.lstrip("# ").strip()
            if not description and s and not s.startswith("#") and len(s) > 20:
                description = s[:200]
            m = re.match(r"^#{2,4}\s+(.*)", s)
            if m:
                heading = m.group(1).strip()
                low = heading.lower()
                if any(k in low for k in ("pitfall", "caveat", "warning", "gotcha", "troubleshoot")):
                    pitfalls.append(heading)
                elif any(k in low for k in ("verify", "test", "validation", "check", "confirm")):
                    verification.append(heading)
                else:
                    procedures.append(heading)

    if not title:
        title = hint_name or (corpus.docs[0].rel.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                              if corpus.docs else "learned-skill")
    name = _slugify(title)
    if not description:
        description = f"Distilled skill covering {title}."

    # Tags from the dominant file extensions / categories present.
    kinds = {d.kind for d in corpus.docs}
    tags = sorted(kinds | {"learned"})

    triggers = [f"When working with {title}.",
                f"When the task references material from {len(corpus.docs)} ingested source(s)."]

    return DistilledSkill(
        name=name,
        description=description,
        tags=tags,
        triggers=triggers,
        procedures=procedures[:20] or ["Review the cited references/ excerpts for the relevant procedure."],
        pitfalls=pitfalls[:10],
        verification=verification[:10],
    )


def distill(
    corpus: Corpus,
    *,
    hint_name: str = "",
    category: str = "",
    model_caller: Optional[Callable[[List[dict]], str]] = None,
) -> DistilledSkill:
    """
    Turn a :class:`Corpus` into a :class:`DistilledSkill`.

    If ``model_caller`` is provided it is invoked with chat messages and must
    return the model's raw text reply (expected to be JSON). On any failure —
    no caller, network error, unparseable output — we fall back to the
    deterministic heuristic so ``/learn`` always produces a usable skill.
    """
    if model_caller is not None:
        try:
            raw = model_caller(build_distillation_messages(corpus, hint_name=hint_name))
            data = _parse_distillation_json(raw)
            skill = DistilledSkill(
                name=_slugify(str(data.get("name") or hint_name or "learned-skill")),
                description=str(data.get("description") or "").strip()
                or f"Distilled skill: {hint_name or 'learned-skill'}.",
                category=str(data.get("category") or category or "").strip(),
                tags=_coerce_str_list(data.get("tags")),
                triggers=_coerce_str_list(data.get("triggers")),
                procedures=_coerce_str_list(data.get("procedures")),
                pitfalls=_coerce_str_list(data.get("pitfalls")),
                verification=_coerce_str_list(data.get("verification")),
            )
            if skill.procedures or skill.triggers:
                if category:
                    skill.category = category
                return skill
        except Exception:
            pass  # fall through to heuristic

    skill = _heuristic_distill(corpus, hint_name=hint_name)
    if category:
        skill.category = category
    return skill


def collect_references(corpus: Corpus, *, limit: int = 12) -> List[Reference]:
    """Pick representative source excerpts to cite under references/."""
    refs: List[Reference] = []
    used_names: set = set()
    for d in corpus.docs[:limit]:
        # Unique, filesystem-safe filename derived from the relative path.
        base = re.sub(r"[^A-Za-z0-9._-]+", "_", d.rel) or "source.txt"
        fname = base
        i = 1
        while fname in used_names:
            fname = f"{i}_{base}"
            i += 1
        used_names.add(fname)
        excerpt = d.text[:MAX_EXCERPT_CHARS]
        if len(d.text) > MAX_EXCERPT_CHARS:
            excerpt += "\n\n... [truncated]"
        refs.append(Reference(source=d.rel, filename=fname, excerpt=excerpt))
    return refs


# ---------------------------------------------------------------------------
# 4. Rendering
# ---------------------------------------------------------------------------

def _bullets(items: Sequence[str]) -> str:
    return "\n".join(f"- {it}" for it in items) if items else "_None identified._"


def _numbered(items: Sequence[str]) -> str:
    return "\n".join(f"{i}. {it}" for i, it in enumerate(items, 1)) if items else "_None identified._"


def render_skill_md(skill: DistilledSkill, *, source_summary: str = "") -> str:
    """Render a :class:`DistilledSkill` to SKILL.md text matching repo conventions."""
    frontmatter = {
        "name": skill.name,
        "description": skill.description,
        "version": skill.version,
        "author": skill.author,
        "license": "MIT",
        "metadata": {
            "hermes": {
                "tags": skill.tags,
                "generated_by": "hermes /learn",
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
    }
    fm_yaml = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False).strip()

    parts = [f"---\n{fm_yaml}\n---", f"\n# {skill.name}\n", skill.description, ""]
    if source_summary:
        parts.append(f"> Distilled from: {source_summary}\n")
    parts.append("## When to Use This Skill\n")
    parts.append(_bullets(skill.triggers))
    parts.append("\n## Procedure\n")
    parts.append(_numbered(skill.procedures))
    parts.append("\n## Pitfalls & Failure Modes\n")
    parts.append(_bullets(skill.pitfalls))
    parts.append("\n## Verification\n")
    parts.append(_bullets(skill.verification))
    if skill.references:
        parts.append("\n## References\n")
        parts.append("Cited source excerpts are stored in the `references/` folder:\n")
        parts.append("\n".join(f"- [`{r.source}`](references/{r.filename})" for r in skill.references))
    return "\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# 5. Atomic write + logging
# ---------------------------------------------------------------------------

def _log(source: str, skill_name: str, status: str, detail: str = "") -> None:
    """Append a structured line to ~/.hermes/logs/learn.log (best-effort)."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{ts}\t{status}\tsource={source}\tskill={skill_name}"
        if detail:
            line += f"\t{detail}"
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def write_skill(
    skill: DistilledSkill,
    skill_md: str,
    *,
    skills_dir: Path = SKILLS_DIR,
    force: bool = False,
) -> Path:
    """
    Atomically write SKILL.md and references/ for ``skill``.

    Content is first staged in a sibling temp directory, then swapped into place
    with a single rename so a reader never sees a half-written skill. If the
    destination already exists and ``force`` is False, raises FileExistsError.
    On any failure the staging directory is removed and (if a previous version
    was displaced) the original is restored — no partial states.
    """
    category = skill.category.strip("/ ") if skill.category else ""
    dest = skills_dir / category / skill.name if category else skills_dir / skill.name
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        raise FileExistsError(
            f"Skill already exists at {dest}. Use --force to overwrite."
        )

    # Stage into a temp dir next to the destination (same filesystem -> atomic rename).
    staging = Path(tempfile.mkdtemp(prefix=f".{skill.name}.staging.", dir=str(dest.parent)))
    backup: Optional[Path] = None
    try:
        (staging / "SKILL.md").write_text(skill_md, encoding="utf-8")
        if skill.references:
            refs_dir = staging / "references"
            refs_dir.mkdir()
            for ref in skill.references:
                (refs_dir / ref.filename).write_text(ref.excerpt, encoding="utf-8")

        # Displace any existing version to a backup, then move staging into place.
        if dest.exists():
            backup = dest.with_name(dest.name + ".bak.tmp")
            if backup.exists():
                shutil.rmtree(backup)
            os.rename(dest, backup)
        os.rename(staging, dest)
    except Exception:
        # Rollback: drop staging, restore any displaced original.
        shutil.rmtree(staging, ignore_errors=True)
        if backup is not None and backup.exists() and not dest.exists():
            os.rename(backup, dest)
        _log(source="-", skill_name=skill.name, status="ERROR", detail="atomic write failed")
        raise
    else:
        if backup is not None and backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
    return dest


# ---------------------------------------------------------------------------
# 6. Orchestrator
# ---------------------------------------------------------------------------

def _default_model_caller(messages: List[dict]) -> str:
    """
    Build an OpenAI-compatible client the same way the agent does and run a
    single completion. Returns the assistant text. Raises on any failure so
    :func:`distill` can fall back to the heuristic.
    """
    from openai import OpenAI  # imported lazily; optional at runtime

    base_url = os.getenv("HERMES_BASE_URL") or os.getenv("OPENAI_BASE_URL") \
        or "https://openrouter.ai/api/v1"
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    model = os.getenv("HERMES_MODEL") or "anthropic/claude-opus-4-8"

    client = OpenAI(base_url=base_url, api_key=api_key)
    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=0.2,
    )
    return resp.choices[0].message.content or ""


def do_learn(
    path: str,
    *,
    name: str = "",
    category: str = "",
    force: bool = False,
    use_model: bool = True,
    model_caller: Optional[Callable[[List[dict]], str]] = None,
    skills_dir: Path = SKILLS_DIR,
) -> Path:
    """
    Full ``/learn`` pipeline: ingest ``path`` and write a distilled SKILL.md.

    Returns the path to the written skill directory. Raises ValueError if no
    ingestible content is found, and FileExistsError if the skill already
    exists and ``force`` is False.
    """
    roots = [Path(p) for p in str(path).split() if p]
    docs = scan_sources(roots)
    if not docs:
        _log(source=path, skill_name=name or "-", status="EMPTY")
        raise ValueError(f"No ingestible files found under: {path}")

    corpus = build_corpus(docs)

    caller = model_caller
    if caller is None and use_model:
        caller = _default_model_caller

    skill = distill(corpus, hint_name=name, category=category, model_caller=caller)
    if name:
        skill.name = _slugify(name)
    skill.references = collect_references(corpus)

    source_summary = f"{len(docs)} file(s) under {', '.join(str(r) for r in roots)}"
    skill_md = render_skill_md(skill, source_summary=source_summary)

    dest = write_skill(skill, skill_md, skills_dir=skills_dir, force=force)
    _log(source=path, skill_name=skill.name, status="OK", detail=f"dest={dest}")
    return dest


# ---------------------------------------------------------------------------
# 7. Slash command + CLI entry points
# ---------------------------------------------------------------------------

def _parse_learn_args(args: Sequence[str]) -> dict:
    """Parse ``<path> [--name N] [--category C] [--force] [--no-model]``."""
    opts = {"path": "", "name": "", "category": "", "force": False, "use_model": True}
    paths: List[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--name", "-n") and i + 1 < len(args):
            opts["name"] = args[i + 1]; i += 2
        elif a in ("--category", "-c") and i + 1 < len(args):
            opts["category"] = args[i + 1]; i += 2
        elif a == "--force":
            opts["force"] = True; i += 1
        elif a in ("--no-model", "--offline"):
            opts["use_model"] = False; i += 1
        else:
            paths.append(a); i += 1
    opts["path"] = " ".join(paths)
    return opts


def handle_learn_slash(cmd: str, console=None) -> None:
    """
    Parse and dispatch ``/learn <path> [...]`` from the chat interface.

    Examples:
        /learn ./docs/payments
        /learn ~/notes/stripe --name stripe-refunds --category payments
        /learn ./spec --offline
    """
    try:
        from rich.console import Console
        c = console or Console()
        printer = c.print
    except Exception:  # pragma: no cover - rich always present in this repo
        printer = print

    parts = cmd.strip().split()
    if parts and parts[0].lower() == "/learn":
        parts = parts[1:]

    if not parts or parts[0] in ("help", "--help", "-h"):
        printer(
            "[bold]/learn[/] — distil a directory into a SKILL.md\n\n"
            "  [cyan]/learn <path>[/] [--name N] [--category C] [--force] [--offline]\n\n"
            "Scans the path (recursively), distils the material into a single\n"
            "skill, and writes it to [cyan]~/.hermes/skills/[/]."
            if printer is not print else
            "/learn <path> [--name N] [--category C] [--force] [--offline]"
        )
        return

    opts = _parse_learn_args(parts)
    printer(f"[dim]Ingesting {opts['path']}...[/]" if printer is not print
            else f"Ingesting {opts['path']}...")
    try:
        dest = do_learn(
            opts["path"], name=opts["name"], category=opts["category"],
            force=opts["force"], use_model=opts["use_model"],
        )
    except FileExistsError as e:
        printer(f"[yellow]{e}[/]" if printer is not print else str(e))
        return
    except ValueError as e:
        printer(f"[red]{e}[/]" if printer is not print else str(e))
        return
    except Exception as e:  # surface unexpected failures without crashing the chat
        printer(f"[red]Failed to learn skill:[/] {e}" if printer is not print
                else f"Failed to learn skill: {e}")
        return

    try:
        rel = dest.relative_to(SKILLS_DIR)
    except ValueError:
        rel = dest
    printer(f"[bold green]Learned skill:[/] {rel}" if printer is not print
            else f"Learned skill: {rel}")


def learn_command(args) -> None:
    """argparse entry point for ``hermes learn``."""
    dest = do_learn(
        args.path,
        name=getattr(args, "name", "") or "",
        category=getattr(args, "category", "") or "",
        force=getattr(args, "force", False),
        use_model=not getattr(args, "offline", False),
    )
    print(f"Learned skill written to: {dest}")
