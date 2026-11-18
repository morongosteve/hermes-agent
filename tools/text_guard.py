#!/usr/bin/env python3
"""
text_guard — detect and neutralize hidden-character covert channels in text.

Adversaries (and accidental copy-paste) can smuggle invisible or
non-rendering codepoints into text that a human reviewer never sees but a
model or downstream parser still consumes. This is the primitive behind
prompt-injection ("invisible instructions"), data exfiltration, and
"Trojan Source" bidi attacks. ``text_guard`` is the defensive inverse: it
*finds* those codepoints, explains what they are, optionally *decodes* the
payload they carry, and *sanitizes* the text back to something a reviewer
sees exactly as the model will.

It targets the full stack of common techniques:

  * Private Use Area glyphs (U+E000-U+F8FF and the supplementary planes) --
    arbitrary private "lexicon" anchors with no public meaning.
  * C1 control codes (U+0080-U+009F), including NEL (U+0085) -- used as
    invisible rhythmic separators / framing pulses.
  * Zero-width & invisible format characters (ZWSP/ZWNJ/ZWJ, word joiner,
    BOM/ZWNBSP, invisible math operators) -- positional metadata in the gaps.
  * Bidirectional overrides (U+202A-202E, U+2066-2069) -- the Trojan Source
    class that reorders rendered text away from its logical byte order.
  * Tag characters (U+E0000-U+E007F) -- a full hidden ASCII alphabet that
    renders as nothing; the classic emoji/text steganography carrier.
  * Standalone variation selectors used as a data carrier.
  * Normalization-triggered content: text whose meaning only appears (or
    disappears) once NFC/NFKC cleanup runs.

Pure stdlib (``unicodedata``); no third-party dependencies.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Category(str, Enum):
    PUA = "private_use_area"
    C1_CONTROL = "c1_control"
    ZERO_WIDTH = "zero_width"
    BIDI_CONTROL = "bidi_control"
    TAG_CHAR = "tag_character"
    VARIATION_SELECTOR = "variation_selector"
    OTHER_FORMAT = "other_format"
    DEPRECATED = "deprecated_format"


# Severity weights per category (0-10), used for the aggregate risk score.
_SEVERITY: Dict[Category, int] = {
    Category.BIDI_CONTROL: 10,      # Trojan Source: reorders visible text
    Category.TAG_CHAR: 10,          # full hidden ASCII channel
    Category.C1_CONTROL: 8,
    Category.PUA: 7,
    Category.ZERO_WIDTH: 6,
    Category.VARIATION_SELECTOR: 5,
    Category.DEPRECATED: 5,
    Category.OTHER_FORMAT: 4,
}

# Explicit codepoint sets / ranges.
_BIDI_CONTROLS = {
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,   # LRE RLE PDF LRO RLO
    0x2066, 0x2067, 0x2068, 0x2069,           # LRI RLI FSI PDI
    0x200E, 0x200F,                           # LRM RLM
    0x061C,                                   # Arabic letter mark
}
_ZERO_WIDTH = {
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x2060,  # WORD JOINER
    0x2061, 0x2062, 0x2063, 0x2064,  # invisible math operators
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / BOM
    0x180E,  # MONGOLIAN VOWEL SEPARATOR
    0x00AD,  # SOFT HYPHEN
}
_DEPRECATED = {0x206A, 0x206B, 0x206C, 0x206D, 0x206E, 0x206F}  # deprecated format


def _in(cp: int, lo: int, hi: int) -> bool:
    return lo <= cp <= hi


def classify_codepoint(cp: int) -> Optional[Category]:
    """Return the suspicious :class:`Category` for a codepoint, or None if benign."""
    # Bidi first -- some live in the general-punctuation block alongside zero-width.
    if cp in _BIDI_CONTROLS:
        return Category.BIDI_CONTROL
    if cp in _ZERO_WIDTH:
        return Category.ZERO_WIDTH
    if cp in _DEPRECATED:
        return Category.DEPRECATED
    if _in(cp, 0x0080, 0x009F):
        return Category.C1_CONTROL
    if _in(cp, 0xE000, 0xF8FF) or _in(cp, 0xF0000, 0xFFFFD) or _in(cp, 0x100000, 0x10FFFD):
        return Category.PUA
    if _in(cp, 0xE0000, 0xE007F):
        return Category.TAG_CHAR
    if _in(cp, 0xFE00, 0xFE0F) or _in(cp, 0xE0100, 0xE01EF):
        return Category.VARIATION_SELECTOR
    # Anything else in the Cf (format) general category that we didn't name.
    try:
        if unicodedata.category(chr(cp)) == "Cf":
            return Category.OTHER_FORMAT
    except (ValueError, TypeError):
        pass
    return None


def _name(cp: int) -> str:
    try:
        return unicodedata.name(chr(cp))
    except ValueError:
        return f"U+{cp:04X} (unnamed)"


@dataclass
class Finding:
    """A single suspicious codepoint occurrence."""

    index: int          # character offset in the input string
    codepoint: int
    char_name: str
    category: Category

    @property
    def severity(self) -> int:
        return _SEVERITY.get(self.category, 4)

    def __str__(self) -> str:
        return (f"@{self.index} U+{self.codepoint:04X} {self.char_name} "
                f"[{self.category.value}, sev {self.severity}]")


@dataclass
class ScanReport:
    """Result of scanning a string for hidden/covert characters."""

    findings: List[Finding] = field(default_factory=list)
    normalization_changes: bool = False
    decoded_payloads: Dict[str, str] = field(default_factory=dict)

    @property
    def is_suspicious(self) -> bool:
        return bool(self.findings) or self.normalization_changes

    @property
    def risk_score(self) -> int:
        """0-100 aggregate risk based on category severity and breadth."""
        if not self.findings and not self.normalization_changes:
            return 0
        peak = max((f.severity for f in self.findings), default=0)
        # Base on the most severe finding, nudge up for volume / many categories.
        cats = {f.category for f in self.findings}
        volume_bonus = min(len(self.findings), 10)
        breadth_bonus = (len(cats) - 1) * 5 if cats else 0
        norm_bonus = 15 if self.normalization_changes else 0
        return min(100, peak * 8 + volume_bonus + breadth_bonus + norm_bonus)

    def counts_by_category(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for f in self.findings:
            out[f.category.value] = out.get(f.category.value, 0) + 1
        return out

    def summary(self) -> str:
        if not self.is_suspicious:
            return "clean: no hidden or covert characters detected"
        lines = [f"SUSPICIOUS -- risk score {self.risk_score}/100"]
        for cat, n in sorted(self.counts_by_category().items()):
            lines.append(f"  {n:>4}x {cat}")
        if self.normalization_changes:
            lines.append("  text changes under NFC normalization (possible retro-normalization payload)")
        for label, payload in self.decoded_payloads.items():
            preview = payload if len(payload) <= 120 else payload[:117] + "..."
            lines.append(f"  decoded {label}: {preview!r}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Decoding (forensics) -- recover what a covert channel was carrying.
# ---------------------------------------------------------------------------

def decode_tag_chars(text: str) -> str:
    """
    Recover the ASCII hidden in Unicode tag characters (U+E0000-U+E007F).

    Tag characters mirror ASCII at an offset of 0xE0000; they render as
    nothing, which makes them a clean hidden channel (e.g. instructions
    appended to an emoji). Returns the decoded ASCII string (may be empty).
    """
    out = []
    for ch in text:
        cp = ord(ch)
        if 0xE0020 <= cp <= 0xE007E:        # tag space .. tag tilde
            out.append(chr(cp - 0xE0000))
        elif cp == 0xE0001 or cp == 0xE007F:  # language tag / cancel tag
            continue
    return "".join(out)


def decode_variation_selectors(text: str) -> str:
    """
    Recover bytes smuggled via the variation-selector channel.

    A known steganographic scheme maps bytes 0..255 to VS U+FE00-FE0F (0..15)
    and U+E0100-E01EF (16..255). Returns a best-effort UTF-8 decode of the
    recovered bytes (empty string if none / undecodable).
    """
    data = bytearray()
    for ch in text:
        cp = ord(ch)
        if 0xFE00 <= cp <= 0xFE0F:
            data.append(cp - 0xFE00)
        elif 0xE0100 <= cp <= 0xE01EF:
            data.append(cp - 0xE0100 + 16)
    if not data:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

def scan(text: str, *, decode: bool = True) -> ScanReport:
    """
    Scan ``text`` for hidden/covert codepoints and (optionally) decode payloads.

    Returns a :class:`ScanReport`. ``decode=True`` additionally attempts to
    recover the content carried by tag-character and variation-selector
    channels, which is useful for incident forensics ("what was it trying to
    say?").
    """
    report = ScanReport()
    for i, ch in enumerate(text):
        cat = classify_codepoint(ord(ch))
        if cat is not None:
            report.findings.append(
                Finding(index=i, codepoint=ord(ch), char_name=_name(ord(ch)), category=cat)
            )

    # Retro-normalization detection: does NFC change the text? Precomposed
    # forms chosen to "remember their future state" surface here.
    if unicodedata.normalize("NFC", text) != text:
        report.normalization_changes = True

    if decode:
        tag = decode_tag_chars(text)
        if tag:
            report.decoded_payloads["tag_chars"] = tag
        vs = decode_variation_selectors(text)
        if vs:
            report.decoded_payloads["variation_selectors"] = vs

    return report


# ---------------------------------------------------------------------------
# Sanitizing
# ---------------------------------------------------------------------------

@dataclass
class SanitizePolicy:
    """Which categories to strip. Defaults to the high-risk covert channels."""

    strip_pua: bool = True
    strip_c1: bool = True
    strip_zero_width: bool = True
    strip_bidi: bool = True
    strip_tag_chars: bool = True
    strip_variation_selectors: bool = False  # legitimate emoji use; off by default
    strip_other_format: bool = True
    strip_deprecated: bool = True
    normalize_nfc: bool = True

    def _strips(self, cat: Category) -> bool:
        return {
            Category.PUA: self.strip_pua,
            Category.C1_CONTROL: self.strip_c1,
            Category.ZERO_WIDTH: self.strip_zero_width,
            Category.BIDI_CONTROL: self.strip_bidi,
            Category.TAG_CHAR: self.strip_tag_chars,
            Category.VARIATION_SELECTOR: self.strip_variation_selectors,
            Category.OTHER_FORMAT: self.strip_other_format,
            Category.DEPRECATED: self.strip_deprecated,
        }.get(cat, False)


def sanitize(text: str, policy: Optional[SanitizePolicy] = None) -> Tuple[str, ScanReport]:
    """
    Remove covert/hidden characters from ``text`` per ``policy``.

    Returns ``(clean_text, report)`` where ``report`` describes what was found
    in the *original* text. Normalization (NFC) is applied last so the result
    is what a reviewer and the model will both see identically.
    """
    policy = policy or SanitizePolicy()
    report = scan(text, decode=True)

    kept = []
    for ch in text:
        cat = classify_codepoint(ord(ch))
        if cat is not None and policy._strips(cat):
            continue
        kept.append(ch)
    clean = "".join(kept)

    if policy.normalize_nfc:
        clean = unicodedata.normalize("NFC", clean)
    return clean, report


# ---------------------------------------------------------------------------
# Perplexity-style anomaly heuristic (cheap, no model required)
# ---------------------------------------------------------------------------

_INVISIBLE_RE = re.compile(
    "[" + "".join(re.escape(chr(c)) for c in sorted(_ZERO_WIDTH | _BIDI_CONTROLS | _DEPRECATED)) + "]"
)


def invisible_ratio(text: str) -> float:
    """Fraction of characters that are invisible/format controls (0.0-1.0).

    A quick triage signal: ordinary prose is ~0.0; text laced with zero-width
    "topology" or C1 "pulses" climbs fast. Cheap enough to run on every inbound
    message before it reaches the agent.
    """
    if not text:
        return 0.0
    hidden = sum(1 for ch in text if classify_codepoint(ord(ch)) is not None)
    return hidden / len(text)


__all__ = [
    "Category", "Finding", "ScanReport", "SanitizePolicy",
    "classify_codepoint", "scan", "sanitize",
    "decode_tag_chars", "decode_variation_selectors", "invisible_ratio",
]
