"""Access to the analog-film knowledge base.

The knowledge base is a set of grounded Markdown notes covering the real imaging
chain from emulsion to dried negative. Each note also explains *how AllStock
models that stage*, so the science and the code stay tied together. Content is
written to be accurate; where a quantity is approximate it is flagged as such.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple


def _knowledge_dir() -> Path:
    try:
        from importlib.resources import files
        p = Path(str(files("allstock"))) / "data" / "knowledge"
        if p.is_dir():
            return p
    except Exception:
        pass
    return Path(__file__).resolve().parent / "data" / "knowledge"


def _title_of(text: str, slug: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return slug


def list_topics() -> List[Tuple[str, str]]:
    """Return ``[(slug, title), ...]`` for all knowledge notes."""
    d = _knowledge_dir()
    out: List[Tuple[str, str]] = []
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*.md")):
        slug = path.stem
        out.append((slug, _title_of(path.read_text(encoding="utf-8"), slug)))
    return out


def get_topic(slug: str) -> str:
    """Return the Markdown for a topic slug (hyphen/underscore-insensitive)."""
    d = _knowledge_dir()
    norm = slug.lower().replace("_", "-")
    candidate = d / f"{norm}.md"
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    # fuzzy: prefix / substring match
    for path in sorted(d.glob("*.md")):
        if path.stem.startswith(norm) or norm in path.stem:
            return path.read_text(encoding="utf-8")
    topics = ", ".join(s for s, _ in list_topics())
    raise KeyError(f"Unknown topic {slug!r}. Available: {topics}")


def search(query: str, context: int = 1) -> Dict[str, List[str]]:
    """Substring search across notes. Returns ``{slug: [matching lines]}``."""
    q = query.lower()
    hits: Dict[str, List[str]] = {}
    for slug, _ in list_topics():
        text = get_topic(slug)
        lines = text.splitlines()
        matched = []
        for i, line in enumerate(lines):
            if q in line.lower():
                lo = max(0, i - context)
                hi = min(len(lines), i + context + 1)
                matched.append(" ".join(l.strip() for l in lines[lo:hi] if l.strip()))
        if matched:
            hits[slug] = matched
    return hits
